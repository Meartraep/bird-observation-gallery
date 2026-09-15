# -*- coding: utf-8 -*-
"""
图片托管与缩略图生成。

内存策略（防止大量大图挤占内存）:
  - 用户导入的原图被复制进应用托管目录，缩略图由 Pillow 离线生成一次后落盘；
  - 相册列表只加载磁盘上的小缩略图（长边 500px），原图绝不预读；
  - 仅当用户点击缩略图时，原图查看器才按需读取原图并缩放到屏幕尺寸。

导入在 QThread 后台执行（JPEG 解码 + 缩放是 CPU/IO 密集操作），
通过信号回报进度，主线程只负责把结果写入 DB 并刷新界面。
"""

import hashlib
import re
import shutil
import time
import uuid
from pathlib import Path

from PIL import Image, ImageOps, UnidentifiedImageError

from PySide6.QtCore import QObject, QThread, Signal

from . import config, settings

_INVALID_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


# ---------------------------------------------------------------------------
# 路径工具
# ---------------------------------------------------------------------------
def absolute_path(rel_path: str) -> Path:
    """数据库中保存的路径还原为绝对路径。

    全量复制模式存相对 DATA_DIR 的相对路径；
    引用模式的原图是用户目录里的绝对路径，原样返回。
    """
    p = Path(rel_path)
    if p.is_absolute():
        return p
    return config.DATA_DIR / rel_path


def _sanitize(name: str) -> str:
    name = _INVALID_CHARS.sub("_", name).strip().strip(".")
    return name or "photo"


def _unique_path(folder: Path, filename: str) -> Path:
    """同名文件自动避让: name.jpg -> name (2).jpg。"""
    target = folder / filename
    if not target.exists():
        return target
    stem, suffix = Path(filename).stem, Path(filename).suffix
    for i in range(2, 10000):
        candidate = folder / f"{stem} ({i}){suffix}"
        if not candidate.exists():
            return candidate
    return folder / f"{stem}_{uuid.uuid4().hex[:8]}{suffix}"


# ---------------------------------------------------------------------------
# 缩略图
# ---------------------------------------------------------------------------
def _flatten_to_rgb(im: Image.Image) -> Image.Image:
    """JPEG 无透明通道，统一转 RGB；带透明的图先合成到白底，避免透明区发黑。"""
    if im.mode == "RGB":
        return im
    has_alpha = im.mode in ("RGBA", "LA") or (
        im.mode == "P" and "transparency" in im.info
    )
    if not has_alpha:
        return im.convert("RGB")
    rgba = im.convert("RGBA")
    background = Image.new("RGB", rgba.size, (255, 255, 255))
    background.paste(rgba, mask=rgba.getchannel("A"))
    return background


def generate_thumbnail(src: Path, dst: Path) -> None:
    """按 EXIF 方向校正后等比缩放到 THUMB_MAX_EDGE，存为 JPEG。"""
    dst.parent.mkdir(parents=True, exist_ok=True)
    with Image.open(src) as im:
        im = ImageOps.exif_transpose(im)
        im.thumbnail(
            (config.THUMB_MAX_EDGE, config.THUMB_MAX_EDGE),
            Image.Resampling.LANCZOS,
        )
        _flatten_to_rgb(im).save(
            dst, "JPEG", quality=config.THUMB_JPEG_QUALITY, optimize=True
        )


def is_supported(path: Path) -> bool:
    return path.suffix.lower() in config.SUPPORTED_IMAGE_EXTS


def sha256_file(path: Path) -> str:
    """分块计算文件 SHA-256（用于重复图片检测）。"""
    digest = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


# ---------------------------------------------------------------------------
# 单张导入（线程内调用）
# ---------------------------------------------------------------------------
def import_one(species_code: str, src_path: Path):
    """
    按当前存储方式导入一张图片，返回 (原图路径, 缩略图相对路径, sha256)：
      - 全量复制: 复制原图到托管目录，file_path 存相对路径；
      - 引用模式: 不复制原图，file_path 存原图绝对路径（打开时定位到原目录）。
    无法识别的图片抛异常。
    """
    file_hash = sha256_file(src_path)

    timestamp = time.strftime("%Y%m%d_%H%M%S")
    safe_code = _sanitize(species_code)
    base_name = f"{timestamp}_{_sanitize(src_path.stem)[:80]}"

    thumb_folder = config.THUMBS_DIR / safe_code
    thumb_folder.mkdir(parents=True, exist_ok=True)

    if settings.get_storage_mode() == settings.STORAGE_REFERENCE:
        # 引用模式：只生成缩略图，不复制原图
        thumb_dst = _unique_path(thumb_folder, base_name + ".jpg")
        try:
            generate_thumbnail(src_path, thumb_dst)
        except (UnidentifiedImageError, OSError):
            thumb_dst.unlink(missing_ok=True)
            raise
        rel_thumb = thumb_dst.relative_to(config.DATA_DIR).as_posix()
        return str(src_path.resolve()), rel_thumb, file_hash

    # 全量复制：复制原图 + 生成缩略图
    orig_folder = config.ORIGINALS_DIR / safe_code
    orig_folder.mkdir(parents=True, exist_ok=True)
    orig_dst = _unique_path(orig_folder, base_name + src_path.suffix.lower())
    shutil.copy2(src_path, orig_dst)

    # 先验证 Pillow 能解码，避免把损坏文件复制进来
    thumb_dst = thumb_folder / orig_dst.with_suffix(".jpg").name
    try:
        generate_thumbnail(orig_dst, thumb_dst)
    except (UnidentifiedImageError, OSError):
        orig_dst.unlink(missing_ok=True)
        raise

    rel_orig = orig_dst.relative_to(config.DATA_DIR).as_posix()
    rel_thumb = thumb_dst.relative_to(config.DATA_DIR).as_posix()
    return rel_orig, rel_thumb, file_hash


def delete_files(rel_orig: str, rel_thumb: str) -> None:
    """删除照片文件。引用模式下原图是用户目录里的绝对路径，绝不删除用户文件。"""
    for rel in (rel_orig, rel_thumb):
        if Path(rel).is_absolute():
            continue
        try:
            absolute_path(rel).unlink()
        except OSError:
            pass


# ---------------------------------------------------------------------------
# 后台批量导入线程
# ---------------------------------------------------------------------------
class ImportWorker(QObject):
    progress = Signal(int, int, str)             # done, total, 当前文件名
    # 全部成功项的 (原图相对路径, 缩略图相对路径) 随完成信号一次带回，
    # 由主线程统一写库后再刷新界面，保证"导入即可见"，不存在跨线程时序竞态
    finished = Signal(list, int, int)            # results, 成功数, 失败数

    def __init__(self, species_code: str, file_paths):
        super().__init__()
        self._species_code = species_code
        self._file_paths = [Path(p) for p in file_paths]
        self._stop = False

    def stop(self):
        self._stop = True

    def run(self):
        results = []
        fail = 0
        total = len(self._file_paths)
        for i, src in enumerate(self._file_paths, start=1):
            if self._stop:
                break
            self.progress.emit(i, total, src.name)
            try:
                results.append(import_one(self._species_code, src))
            except Exception:
                fail += 1
        self.finished.emit(results, len(results), fail)


def create_import_worker(parent, species_code: str, file_paths):
    """
    创建后台导入线程，但【不启动】。
    调用方先连接 progress/finished 信号，再调用返回线程的 start()，
    避免线程跑起来后信号尚未连接导致的事件丢失。
    """
    thread = QThread(parent)
    worker = ImportWorker(species_code, file_paths)
    worker.moveToThread(thread)
    thread.started.connect(worker.run)
    worker.finished.connect(thread.quit)
    thread.finished.connect(worker.deleteLater)
    thread.finished.connect(thread.deleteLater)
    return thread, worker
