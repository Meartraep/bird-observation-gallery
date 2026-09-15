# -*- coding: utf-8 -*-
"""
「设置」弹窗。

包含两部分：
  1. 图片存储方式：全量复制 或 引用模式（只存缩略图，原图留在用户目录）；
  2. 「更新数据库」入口：复用 UpdateDialog 的更新逻辑，成功后再刷新本窗口
     及主界面（缩略图仍显示、成就清单不动，本地模式可打开原图目录）。
"""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QButtonGroup,
    QRadioButton,
    QFileDialog,
    QFrame,
)

from . import settings
from .update_dialog import UpdateDialog
from .ui_utils import make_label_selectable


class SettingsDialog(QDialog):
    storageChanged = Signal()
    databaseUpdated = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("设置")
        self.setModal(True)
        self.setMinimumWidth(560)

        data = settings.load()

        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 16)
        root.setSpacing(14)

        # --- 图片存储方式 ---------------------------------------------
        title = make_label_selectable(QLabel("图片存储方式"))
        title.setObjectName("BirdNameZh")
        root.addWidget(title)

        copy_radio = QRadioButton("全量复制")
        copy_radio.setToolTip(
            "导入照片时把原图复制进程序托管目录\n"
            "原图移动或删除后应用内仍可查看，双份备份占用磁盘空间"
        )
        reference_radio = QRadioButton("引用模式（只存缩略图）")
        reference_radio.setToolTip(
            "原图留在你的目录里，程序只生成缩略图存储\n"
            "点击照片时到原目录查看原图；原图丢失时仅提示丢失，缩略图与成就清单不受影响"
        )

        group = QButtonGroup(self)
        group.addButton(copy_radio, 0)
        group.addButton(reference_radio, 1)
        if data.get("storage_mode") == settings.STORAGE_REFERENCE:
            copy_radio.setChecked(False)
            reference_radio.setChecked(True)
        else:
            copy_radio.setChecked(True)
            reference_radio.setChecked(False)

        group.idClicked.connect(self._on_mode_clicked)
        root.addWidget(copy_radio)
        root.addWidget(reference_radio)

        # 引用模式：原图目录选择行
        self._dir_container = QFrame()
        dir_row = QHBoxLayout(self._dir_container)
        dir_row.setContentsMargins(0, 0, 0, 0)
        self._dir_label = make_label_selectable(QLabel("原图目录："))
        self._dir_label.setObjectName("PhotoCount")
        dir_row.addWidget(self._dir_label, 1)
        self._dir_input = make_label_selectable(QLabel(
            data.get("reference_dir") or ""
        ))
        self._dir_input.setObjectName("LinkText")
        self._dir_input.setToolTip("原图所在目录")
        self._dir_input.setTextInteractionFlags(Qt.TextSelectableByMouse)
        dir_row.addWidget(self._dir_input, 1)
        self._pick_dir_btn = QPushButton("选择目录…")
        self._pick_dir_btn.setProperty("class", "ghost")
        self._pick_dir_btn.setCursor(Qt.PointingHandCursor)
        self._pick_dir_btn.clicked.connect(self._choose_dir)
        dir_row.addWidget(self._pick_dir_btn)
        root.addWidget(self._dir_container)

        note = make_label_selectable(QLabel(
            "提示：切换存储方式只影响之后新增的照片，已有照片保持不变。"
        ))
        note.setObjectName("PhotoCount")
        root.addWidget(note)

        # --- 分隔线 --------------------------------------------------
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        root.addWidget(line)

        # --- 数据库更新 ------------------------------------------------
        db_title = make_label_selectable(QLabel("数据库"))
        db_title.setObjectName("BirdNameZh")
        root.addWidget(db_title)

        self._update_btn = QPushButton("更新数据库…")
        self._update_btn.setCursor(Qt.PointingHandCursor)
        self._update_btn.clicked.connect(self._open_update_dialog)
        root.addWidget(self._update_btn)

        # --- 底部按钮 ------------------------------------------------
        btn_row = QHBoxLayout()
        btn_row.addStretch(1)
        close_btn = QPushButton("关闭")
        close_btn.clicked.connect(self.accept)
        btn_row.addWidget(close_btn)
        root.addLayout(btn_row)

        # 初始状态
        self._mode = data.get("storage_mode", settings.STORAGE_COPY)
        self._dir_row_visible()

    # ------------------------------------------------------------------
    def _dir_row_visible(self):
        ref = self._mode == settings.STORAGE_REFERENCE
        self._dir_container.setVisible(ref)

    def _on_mode_clicked(self, id_: int):
        self._mode = (
            settings.STORAGE_COPY if id_ == 0 else settings.STORAGE_REFERENCE
        )
        self._dir_row_visible()
        # 立即保存选择；引用模式下需要用户确认或选择目录
        if self._mode == settings.STORAGE_REFERENCE:
            settings.set_storage_mode(self._mode, self._current_dir())
        else:
            settings.set_storage_mode(self._mode)
        self.storageChanged.emit()

    def _current_dir(self) -> str:
        return self._dir_input.text().strip()

    def _choose_dir(self):
        d = QFileDialog.getExistingDirectory(
            self, "选择原图所在目录", self._current_dir()
        )
        if not d:
            return
        self._dir_input.setText(d)
        settings.set_storage_mode(settings.STORAGE_REFERENCE, d)
        self.storageChanged.emit()

    # ------------------------------------------------------------------
    def _open_update_dialog(self):
        dialog = UpdateDialog(self, first_run=False)
        dialog.databaseUpdated.connect(self.databaseUpdated)
        dialog.exec()