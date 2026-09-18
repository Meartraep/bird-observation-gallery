# -*- coding: utf-8 -*-
"""
集中式路径与常量配置。

所有"文件放在哪里"的决定都收敛在本模块，后续 PyInstaller 打包 /
安装器阶段只需修改这里（例如打包后把可写数据切换到 %APPDATA%）。
"""

import os
import sys
from pathlib import Path

APP_NAME = "鸟类相册"
APP_ORG = "BirdAlbum"

# ---------------------------------------------------------------------------
# 路径
# ---------------------------------------------------------------------------
def _base_dir() -> Path:
    """程序目录：开发态为项目根；PyInstaller 打包后为 exe 所在目录。"""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


BASE_DIR = _base_dir()


def _resource_dir() -> Path:
    """
    随包只读资源目录：开发态为项目根；打包后为 sys._MEIPASS
    （PyInstaller 6 的 onedir 模式下即 exe 同级的 _internal/，
    与 BASE_DIR 不是同一个目录，spec 里 datas 的落点以这里为准）。
    """
    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parent.parent


RESOURCE_DIR = _resource_dir()


def _data_dir() -> Path:
    """
    运行数据（数据库、照片）目录。
    打包后放在 %APPDATA%\\BirdAlbum（可写、持久，升级/移动 exe 不丢数据）；
    开发态直接用项目内 data/。
    """
    if getattr(sys, "frozen", False):
        return Path(os.environ.get("APPDATA", BASE_DIR)) / "BirdAlbum"
    return BASE_DIR / "data"


DATA_DIR = _data_dir()
DB_PATH = DATA_DIR / "birds.db"

# 应用托管的图片目录（用户导入时复制原图进来，避免移动/删除源文件后失联）
PHOTOS_DIR = DATA_DIR / "photos"
ORIGINALS_DIR = PHOTOS_DIR / "originals"
THUMBS_DIR = PHOTOS_DIR / "thumbs"

# 注意：eBird 分类表及其演绎产物不允许直接分发，程序不随附任何数据库种子文件。
# 首次运行必须由用户从官方地址免费下载表格并导入后才能进入程序。

# 第三方中文名补充包（鸟有记 Chinese-bird-name-bridge 的 ioc-species-db.json，
# 独立按 CC BY-NC 4.0 授权，不属于 GPL-3.0 范围）。它不是 eBird 数据，
# 不含分类层级，只用于给 taxon 补中文别名与繁中（台湾/香港）名。
# 见 third_party/chinese-bird-name-bridge/NOTICE.md。
NAME_BRIDGE_PATH = (
    RESOURCE_DIR / "third_party" / "chinese-bird-name-bridge"
    / "ioc-species-db.json"
)


def ensure_data() -> None:
    """确保运行数据目录存在。数据库由首次运行引导用户导入生成。"""
    DATA_DIR.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# 图片参数
# ---------------------------------------------------------------------------
# 缩略图长边像素（1000px JPEG 约 150~350KB / 张，兼顾清晰度与内存）
THUMB_MAX_EDGE = 1000
THUMB_JPEG_QUALITY = 88

# 支持导入的图片格式
SUPPORTED_IMAGE_EXTS = {
    ".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff", ".gif",
}

# 相册卡片图片显示宽度策略：随相册区宽度变化，尽量增大屏占比
CARD_WIDTH_MIN = 520
CARD_WIDTH_MAX = 960
CARD_WIDTH_RATIO = 0.82   # 取相册区可视宽度的 82%（留出边距与滚动条）
