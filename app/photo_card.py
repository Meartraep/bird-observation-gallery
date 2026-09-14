# -*- coding: utf-8 -*-
"""
单张照片卡片（上图下注的一图一注结构）。

  - 图像区只加载磁盘缩略图(1000px)，不触碰原图；
    显示宽度由相册区统一计算并下发，尽量占满可视宽度；
  - 点击图片交给系统默认照片应用打开全尺寸原图；
  - 备注为多行输入框，输入停顿或失焦后自动保存。
"""

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QPixmap, QIcon
from PySide6.QtWidgets import (
    QFrame,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QPlainTextEdit,
)

from .image_store import absolute_path
from .ui_utils import make_label_selectable


class NoteEdit(QPlainTextEdit):
    """失焦时发信号，配合输入防抖实现自动保存。"""

    focusLost = Signal()

    def focusOutEvent(self, event):
        self.focusLost.emit()
        super().focusOutEvent(event)


class PhotoCard(QFrame):
    openRequested = Signal(str)         # 原图绝对路径（交系统照片应用打开）
    noteChanged = Signal(int, str)      # photo_id, 备注文本
    moveRequested = Signal(int, int)    # photo_id, direction(-1上移/1下移)
    deleteRequested = Signal(int)       # photo_id

    def __init__(self, photo: dict, display_width: int, parent=None,
                 can_up: bool = True, can_down: bool = True):
        super().__init__(parent)
        self.setObjectName("PhotoCard")
        self._photo = photo
        self._display_width = display_width
        self._pixmap = None  # 磁盘缩略图原始 QPixmap

        outer = QVBoxLayout(self)
        outer.setContentsMargins(14, 12, 14, 14)
        outer.setSpacing(8)

        # 顶栏: 日期 + 删除
        top = QHBoxLayout()
        date_label = make_label_selectable(QLabel(photo.get("created_at") or ""))
        date_label.setObjectName("CardDate")
        top.addWidget(date_label)
        top.addStretch(1)
        self._saved_hint = make_label_selectable(QLabel(""))
        self._saved_hint.setObjectName("SavedHint")
        top.addWidget(self._saved_hint)

        # 顺序调整按钮（首/尾对应方向自动禁用）
        up_btn = QPushButton("↑")
        up_btn.setProperty("class", "moveBtn")
        up_btn.setToolTip("上移这张照片")
        up_btn.setCursor(Qt.PointingHandCursor)
        up_btn.setEnabled(can_up)
        up_btn.clicked.connect(
            lambda: self.moveRequested.emit(self._photo["id"], -1)
        )
        top.addWidget(up_btn)

        down_btn = QPushButton("↓")
        down_btn.setProperty("class", "moveBtn")
        down_btn.setToolTip("下移这张照片")
        down_btn.setCursor(Qt.PointingHandCursor)
        down_btn.setEnabled(can_down)
        down_btn.clicked.connect(
            lambda: self.moveRequested.emit(self._photo["id"], 1)
        )
        top.addWidget(down_btn)

        del_btn = QPushButton("删除")
        del_btn.setProperty("class", "dangerText")
        del_btn.setCursor(Qt.PointingHandCursor)
        del_btn.clicked.connect(
            lambda: self.deleteRequested.emit(self._photo["id"])
        )
        top.addWidget(del_btn)
        outer.addLayout(top)

        # 缩略图按钮
        self._thumb_btn = QPushButton()
        self._thumb_btn.setObjectName("ThumbButton")
        self._thumb_btn.setCursor(Qt.PointingHandCursor)
        self._thumb_btn.setFlat(True)
        self._orig_abs = absolute_path(photo["file_path"])
        self._thumb_btn.setToolTip(
            "点击使用系统照片查看器打开原图\n"
            f"{self._orig_abs}"
        )
        self._load_thumbnail()
        self._thumb_btn.clicked.connect(self._open_original)
        outer.addWidget(self._thumb_btn, 0, Qt.AlignHCenter)

        # 备注
        self._note_edit = NoteEdit()
        self._note_edit.setObjectName("NoteEdit")
        self._note_edit.setPlaceholderText("为这张照片添加说明备注…（自动保存）")
        self._note_edit.setPlainText(photo.get("note") or "")
        self._note_edit.setFixedHeight(72)
        outer.addWidget(self._note_edit)

        # 自动保存: 输入停顿 700ms，或失焦
        self._save_timer = QTimer(self)
        self._save_timer.setSingleShot(True)
        self._save_timer.setInterval(700)
        self._save_timer.timeout.connect(self._save_note)
        self._note_edit.textChanged.connect(self._on_text_changed)
        self._note_edit.focusLost.connect(self._save_note)

        self._loaded_note = photo.get("note") or ""

    # ------------------------------------------------------------------
    def _load_thumbnail(self):
        """仅读取缩略图文件一次，缩放交给 _apply_pixmap。"""
        thumb_abs = absolute_path(self._photo["thumb_path"])
        self._pixmap = QPixmap(str(thumb_abs))
        if self._pixmap.isNull():
            self._pixmap = None
            self._thumb_btn.setText("缩略图丢失")
            self._thumb_btn.setFixedSize(self._display_width, 120)
            return
        self._apply_pixmap()

    def _apply_pixmap(self):
        if self._pixmap is None:
            return
        # 不放大超过缩略图自身分辨率，避免模糊；竖图按宽度等比缩小
        target_w = min(self._display_width, self._pixmap.width())
        pm = self._pixmap
        if pm.width() != target_w:
            pm = pm.scaledToWidth(target_w, Qt.SmoothTransformation)
        self._thumb_btn.setFixedSize(pm.size())
        self._thumb_btn.setIcon(QIcon(pm))
        self._thumb_btn.setIconSize(pm.size())

    def set_display_width(self, width: int):
        """相册区宽度变化时由父级下发，实时重排图片大小。"""
        if width == self._display_width:
            return
        self._display_width = width
        self._apply_pixmap()

    def _open_original(self):
        self.openRequested.emit(str(self._orig_abs))

    # ------------------------------------------------------------------
    def _on_text_changed(self):
        self._saved_hint.setText("编辑中…")
        self._save_timer.start()

    def _save_note(self):
        text = self._note_edit.toPlainText().strip()
        if text == self._loaded_note:
            self._saved_hint.setText("")
            return
        self.noteChanged.emit(self._photo["id"], text)
        self._loaded_note = text
        self._saved_hint.setText("✓ 已保存")
        QTimer.singleShot(2000, lambda: self._saved_hint.setText(""))
