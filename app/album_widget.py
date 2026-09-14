# -*- coding: utf-8 -*-
"""
右侧相册区。

  - 选定具体鸟种后显示其相册: 鸟名信息头 +「添加照片」入口；
  - 照片为竖排卡片（上图下注），QScrollArea 承载，鼠标滚轮滚动；
  - 卡片图片宽度随窗口大小动态变化，尽量增大屏占比；
  - 支持按钮选择多张 / 直接把图片文件拖进来；
  - 导入在后台线程复制原图 + 生成缩略图，带进度对话框，不卡界面；
    完成信号在主线程"先批量写库、后统一刷新"，导入立即可见；
  - 点击图片调用系统默认照片应用查看全尺寸原图；
  - 未选鸟种 / 相册为空 各有独立占位状态。
"""

import os
from pathlib import Path

from PySide6.QtCore import Qt, QTimer, QUrl, Signal, Slot, QEvent
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QWidget,
    QFrame,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QStackedWidget,
    QFileDialog,
    QMessageBox,
    QProgressBar,
)

from . import config, db
from . import image_store
from . import settings
from .photo_card import PhotoCard
from .ui_utils import make_label_selectable


class AlbumWidget(QWidget):
    statusMessage = Signal(str)
    photosChanged = Signal()  # 照片新增/删除后发出（成就清单树需刷新）

    # 页面: 未选择鸟种 / 空相册 / 卡片列表
    PAGE_HINT = 0
    PAGE_ALBUM = 1

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)

        self._code = None
        self._bird = None
        self._cards = []
        self._thread = None
        self._worker = None

        # 窗口尺寸变化后防抖重排卡片图片宽度
        self._resize_timer = QTimer(self)
        self._resize_timer.setSingleShot(True)
        self._resize_timer.setInterval(180)
        self._resize_timer.timeout.connect(self._apply_card_widths)

        # 切页/导入完成后几何可能尚未就绪，用自有短延时定时器在布局稳定后重排
        # （不用静态 singleShot：其临时 QTimer 在嵌套事件循环边界可能被回收）
        self._relayout_timer = QTimer(self)
        self._relayout_timer.setSingleShot(True)
        self._relayout_timer.setInterval(50)
        self._relayout_timer.timeout.connect(self._apply_card_widths)

        self._build_ui()

    # ------------------------------------------------------------------
    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # -- 鸟名信息头 ------------------------------------------------
        self._header = QFrame()
        self._header.setObjectName("AlbumHeader")
        header_layout = QVBoxLayout(self._header)
        header_layout.setContentsMargins(22, 14, 22, 14)
        header_layout.setSpacing(4)

        title_row = QHBoxLayout()
        self._name_zh = make_label_selectable(QLabel(""))
        self._name_zh.setObjectName("BirdNameZh")
        title_row.addWidget(self._name_zh)
        title_row.addStretch(1)
        self._add_btn = QPushButton("＋ 添加照片")
        self._add_btn.setProperty("class", "primary")
        self._add_btn.setCursor(Qt.PointingHandCursor)
        self._add_btn.clicked.connect(self._choose_files)
        title_row.addWidget(self._add_btn)
        header_layout.addLayout(title_row)

        sub_row = QHBoxLayout()
        self._name_sci = make_label_selectable(QLabel(""))
        self._name_sci.setObjectName("BirdNameSci")
        sub_row.addWidget(self._name_sci)
        sub_row.addSpacing(16)
        self._count_label = make_label_selectable(QLabel(""))
        self._count_label.setObjectName("PhotoCount")
        sub_row.addWidget(self._count_label)
        sub_row.addStretch(1)
        header_layout.addLayout(sub_row)
        root.addWidget(self._header)

        # -- 导入进度条（内嵌、非模态，不阻塞主线程）--------------------
        self._progress_bar = QProgressBar()
        self._progress_bar.setObjectName("ImportProgress")
        self._progress_bar.setVisible(False)
        self._progress_bar.setFormat("正在导入照片 %v/%m")
        self._progress_label = make_label_selectable(QLabel(""))
        self._progress_label.setObjectName("PhotoCount")
        bar_row = QHBoxLayout()
        bar_row.setContentsMargins(22, 8, 22, 0)
        bar_row.addWidget(self._progress_bar, 1)
        bar_row.addWidget(self._progress_label)
        root.addLayout(bar_row)

        # -- 主体: 占位 / 相册 两页切换 --------------------------------
        self._stack = QStackedWidget()

        self._hint_label = make_label_selectable(QLabel(
            "请在左侧目录中选择一种鸟\n\n"
            "拍到满意的照片后，点击「＋ 添加照片」\n"
            "或直接把图片拖入本区域"
        ))
        self._hint_label.setObjectName("EmptyHint")
        self._hint_label.setAlignment(Qt.AlignCenter)
        self._stack.addWidget(self._hint_label)

        self._scroll = QScrollArea()
        self._scroll.setObjectName("AlbumScroll")
        self._scroll.setWidgetResizable(True)
        self._scroll.setAlignment(Qt.AlignTop | Qt.AlignHCenter)

        self._container = QWidget()
        self._container.setObjectName("CardsContainer")
        self._cards_layout = QVBoxLayout(self._container)
        self._cards_layout.setContentsMargins(24, 20, 24, 40)
        self._cards_layout.setSpacing(18)
        self._cards_layout.addStretch(1)
        self._scroll.setWidget(self._container)
        self._stack.addWidget(self._scroll)
        # 视口尺寸变化（窗口缩放 / 拖动分割条 / 首次布局）即防抖重排卡片
        self._scroll.viewport().installEventFilter(self)

        root.addWidget(self._stack, 1)
        self._header.setVisible(False)

    # ------------------------------------------------------------------
    def show_hint(self, text: str):
        self._code = None
        self._bird = None
        self._header.setVisible(False)
        self._hint_label.setText(text)
        self._stack.setCurrentIndex(self.PAGE_HINT)

    def set_species(self, code: str):
        bird = db.get_taxon(code)
        if bird is None:
            self.show_hint("未找到该鸟类条目")
            return
        self._code = code
        self._bird = bird
        self._header.setVisible(True)

        zh, en, sci = bird["name_zh"], bird["name_en"], bird["sci_name"]
        self._name_zh.setText(zh if zh else en)
        if zh:
            self._name_sci.setText(f"{sci}    {en}")
        else:
            self._name_sci.setText(sci)

        self._reload_cards()

    # ------------------------------------------------------------------
    def _card_image_width(self) -> int:
        """根据滚动区可视宽度计算卡片图片宽度（扣除卡片边框/内边距/滚动条）。"""
        avail = self._scroll.viewport().width() - 24 * 2 - 14 * 2 - 24
        width = int(avail * config.CARD_WIDTH_RATIO)
        return max(config.CARD_WIDTH_MIN, min(config.CARD_WIDTH_MAX, width))

    def _apply_card_widths(self):
        width = self._card_image_width()
        for card in self._cards:
            card.set_display_width(width)

    def eventFilter(self, obj, event):
        if obj is self._scroll.viewport() and event.type() == QEvent.Resize:
            if self._cards:
                self._resize_timer.start()
        return super().eventFilter(obj, event)

    # ------------------------------------------------------------------
    def _reload_cards(self):
        for card in self._cards:
            card.setParent(None)
            card.deleteLater()
        self._cards.clear()

        photos = db.list_photos(self._code) if self._code else []

        display_width = self._card_image_width()
        n = len(photos)
        for i, photo in enumerate(photos):
            card = PhotoCard(
                photo, display_width, self._container,
                can_up=i > 0, can_down=i < n - 1,
            )
            card.openRequested.connect(self._open_external)
            card.noteChanged.connect(db.update_note)
            card.moveRequested.connect(self._move_photo)
            card.deleteRequested.connect(self._delete_photo)
            card.show()  # 父级此刻可能正处在切页过渡，显式 show 保证可见
            # 插在 stretch 之前
            self._cards_layout.insertWidget(
                self._cards_layout.count() - 1, card
            )
            self._cards.append(card)

        # 切页放在建卡之后：切到相册页时整棵卡片子树随容器一起显示。
        # 注意 QStackedLayout 只给当前页分配全宽，建卡时读到的可能是非当前页
        # 的窄几何，故再用短延时定时器按切页后的真实宽度重排一次
        self._count_label.setText(f"共 {len(photos)} 张照片")
        if photos:
            self._stack.setCurrentIndex(self.PAGE_ALBUM)
            self._relayout_timer.start()
        else:
            self._hint_label.setText(
                f"「{self._bird_title()}」的相册还是空的\n\n"
                "点击右上角「＋ 添加照片」，或把图片直接拖入本区域"
            )
            self._stack.setCurrentIndex(self.PAGE_HINT)

    # ------------------------------------------------------------------
    def _bird_title(self) -> str:
        if not self._bird:
            return ""
        return self._bird["name_zh"] or self._bird["name_en"]

    # ------------------------------------------------------------------
    # 导入
    # ------------------------------------------------------------------
    def _choose_files(self):
        if not self._code:
            return
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "选择要添加的照片（可多选）",
            self._default_import_dir(),
            "图片文件 (*.jpg *.jpeg *.png *.webp *.bmp *.tif *.tiff *.gif)",
        )
        if files:
            self._start_import(files)

    def _default_import_dir(self) -> str:
        """引用模式下默认打开设置里选择的原图目录，方便挑图。"""
        if settings.get_storage_mode() == settings.STORAGE_REFERENCE:
            d = settings.get_reference_dir()
            if d and os.path.isdir(d):
                return d
        return ""

    def _start_import(self, file_paths):
        if not self._code or not file_paths:
            return
        supported = [p for p in file_paths if image_store.is_supported(Path(p))]
        skipped = len(file_paths) - len(supported)
        if not supported:
            QMessageBox.information(
                self, "无法导入", "所选文件不是支持的图片格式（jpg/png/webp/bmp/tif/gif）。"
            )
            return

        # 锁定本次导入的目标鸟种：导入期间用户可自由切换页面，
        # 照片仍归入发起导入的鸟，且只在仍停留在该鸟页时刷新
        target_code = self._code
        target_title = self._bird_title()
        self._import_ctx = {
            "target_code": target_code,
            "target_title": target_title,
            "skipped": skipped,
            "total": len(supported),
        }

        self._add_btn.setEnabled(False)
        self._progress_bar.setRange(0, len(supported))
        self._progress_bar.setValue(0)
        self._progress_bar.setVisible(True)
        self._progress_label.setText(f"0/{len(supported)}")

        # 先创建并连好全部信号，最后再 start()，杜绝信号早于连接发出。
        # 关键：回调必须是本 QObject 的 @Slot 方法 + QueuedConnection，
        # 否则 PySide6 对普通 Python 函数会直连，在子线程执行 GUI 操作导致崩溃
        self._thread, self._worker = image_store.create_import_worker(
            self, target_code, supported
        )
        self._worker.progress.connect(
            self._on_import_progress, Qt.QueuedConnection
        )
        self._worker.finished.connect(
            self._on_import_done, Qt.QueuedConnection
        )
        self._thread.start()

    @Slot(int, int, str)
    def _on_import_progress(self, done, total, name):
        """主线程槽：更新内嵌进度条（仅 GUI 操作，线程安全）。"""
        self._progress_bar.setValue(done)
        self._progress_label.setText(f"{done}/{total}")
        self._progress_label.setToolTip(name)

    @staticmethod
    def _split_duplicates(results, existing_hashes: set):
        """
        划分重复与非重复。results 元素为 (rel_orig, rel_thumb, file_hash)。
        不仅与相册已有照片比对，同一批内的重复也只会保留第一张。
        返回 (keep, skipped)，skipped 为应删除文件的重复项。
        """
        seen = set(existing_hashes)
        keep, skipped = [], []
        for rel_orig, rel_thumb, file_hash in results:
            if file_hash in seen:
                skipped.append((rel_orig, rel_thumb))
            else:
                seen.add(file_hash)
                keep.append((rel_orig, rel_thumb, file_hash))
        return keep, skipped

    @Slot(list, int, int)
    def _on_import_done(self, results, ok, fail):
        """主线程槽：查重 → 弹窗确认 → 写库 → 刷新界面。"""
        ctx = self._import_ctx
        target_code = ctx["target_code"]
        existing = db.get_photo_hashes(target_code)
        keep, skipped = self._split_duplicates(results, existing)

        skip_count = 0
        if skipped:
            box = QMessageBox(self)
            box.setIcon(QMessageBox.Question)
            box.setWindowTitle("发现重复图片")
            box.setText(
                f"有 {len(skipped)} 张图片与「{ctx['target_title']}」"
                "相册中已有的图片完全相同（同一张）。"
            )
            box.setInformativeText("要继续导入这些重复图片吗？")
            keep_all = box.addButton("仍要导入", QMessageBox.YesRole)
            skip_dup = box.addButton("跳过重复", QMessageBox.NoRole)
            box.setDefaultButton(skip_dup)
            box.exec()
            if box.clickedButton() is keep_all:
                keep = results
            else:
                for rel_orig, rel_thumb in skipped:
                    image_store.delete_files(rel_orig, rel_thumb)
                skip_count = len(skipped)

        for rel_orig, rel_thumb, file_hash in keep:
            db.add_photo(target_code, rel_orig, rel_thumb, file_hash)
        self._progress_bar.setVisible(False)
        self._add_btn.setEnabled(True)
        if self._code == target_code:
            self._reload_cards()
        msg = f"已导入 {len(keep)} 张照片到「{ctx['target_title']}」"
        if skip_count:
            msg += f"，跳过 {skip_count} 张重复图片"
        if fail:
            msg += f"，{fail} 张无法读取已跳过"
        if ctx["skipped"]:
            msg += f"，{ctx['skipped']} 个非图片文件已忽略"
        self.statusMessage.emit(msg)
        self.photosChanged.emit()

    # ------------------------------------------------------------------
    def _move_photo(self, photo_id: int, direction: int):
        """上移/下移照片，成功后刷新顺序（首尾方向由按钮禁用，此处兜底）。"""
        if db.move_photo(photo_id, direction):
            self._reload_cards()

    def _delete_photo(self, photo_id: int):
        photo = db.get_photo(photo_id)
        if photo is None:
            return
        # 按该照片本身的存储方式判定：引用模式的原图是用户目录里的绝对路径
        is_reference = Path(photo["file_path"]).is_absolute()

        box = QMessageBox(self)
        box.setWindowTitle("删除照片")
        if is_reference:
            box.setText("确定从相册中移除这张照片吗？")
            box.setInformativeText(
                "引用模式下只会删除程序生成的缩略图，"
                "你目录中的原图不受影响，此操作不可撤销。"
            )
        else:
            box.setText("确定删除这张照片吗？")
            box.setInformativeText("将同时删除应用托管的原图和缩略图，此操作不可撤销。")
        box.setStandardButtons(QMessageBox.Yes | QMessageBox.Cancel)
        box.button(QMessageBox.Yes).setText("删除")
        box.button(QMessageBox.Cancel).setText("取消")
        if box.exec() != QMessageBox.Yes:
            return

        paths = db.delete_photo(photo_id)
        if paths:
            image_store.delete_files(*paths)
        self._reload_cards()
        self.statusMessage.emit("照片已删除")
        self.photosChanged.emit()

    # ------------------------------------------------------------------
    def _open_external(self, image_path: str):
        """打开全尺寸原图：存在则调系统默认照片应用；丢失则提示并允许打开所在目录。"""
        path = Path(image_path)

        if path.is_file():
            url = QUrl.fromLocalFile(str(path))
            if not QDesktopServices.openUrl(url):
                QMessageBox.warning(
                    self, "无法打开",
                    "未能调用系统照片查看器，请检查系统的图片默认应用设置。",
                )
            return

        # 原图丢失：缩略图仍在、成就清单不动，仅提示用户，并提供打开所在目录
        folder = str(path.parent)
        box = QMessageBox(self)
        box.setWindowTitle("原图已丢失")
        box.setText(
            "找不到这张照片的原图，已改为打开原图所在目录。\n"
            "（程序里保存的只是缩略图，成就清单不受影响）"
        )
        if folder:
            box.setInformativeText(f"原图所在目录：\n{folder}")
        open_folder = box.addButton("打开所在目录", QMessageBox.AcceptRole)
        box.addButton("知道了", QMessageBox.RejectRole)
        box.exec()
        if box.clickedButton() is open_folder and folder:
            QDesktopServices.openUrl(QUrl.fromLocalFile(folder))

    # ------------------------------------------------------------------
    # 拖放
    # ------------------------------------------------------------------
    def dragEnterEvent(self, event):
        if self._code and event.mimeData().hasUrls():
            if any(u.isLocalFile() for u in event.mimeData().urls()):
                event.acceptProposedAction()
                return
        event.ignore()

    def dragMoveEvent(self, event):
        if self._code and event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event):
        paths = [
            u.toLocalFile()
            for u in event.mimeData().urls()
            if u.isLocalFile()
        ]
        if paths:
            self._start_import(paths)
            event.acceptProposedAction()
        else:
            event.ignore()
