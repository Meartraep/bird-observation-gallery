# -*- coding: utf-8 -*-
"""
「更新数据库」弹窗。

用户把下载的 eBird 分类 Excel（eBird_Taxonomy_*.xlsx）拖入窗口，
或通过"选择文件"按钮指定，随后在后台线程重新执行 SQLite 导出并
更新正式数据库（保留照片与搜索历史数据）。格式不符时给出具体原因。
"""

from pathlib import Path

from PySide6.QtCore import Qt, QThread, QObject, Signal, Slot, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QFileDialog,
    QMessageBox,
    QProgressBar,
    QApplication,
)

from . import db_builder
from .ui_utils import make_label_selectable


class UpdateWorker(QObject):
    progress = Signal(int, int, str)          # done, total, 阶段文本
    finished = Signal(bool, str, dict)        # 成功, 消息, 统计

    def __init__(self, xlsx_path):
        super().__init__()
        self._xlsx_path = xlsx_path

    def run(self):
        try:
            stats = db_builder.update_database(
                self._xlsx_path,
                progress_cb=lambda done, total: self.progress.emit(
                    done, total, f"正在转换分类数据 {done}/{total}"
                ),
            )
            self.finished.emit(
                True,
                f"数据库已更新（{stats['taxon_count']} 个分类单元，"
                f"保留照片 {stats['photo_count']} 张、"
                f"搜索历史 {stats['history_count']} 条）",
                stats,
            )
        except ValueError as exc:  # 格式不符
            self.finished.emit(False, str(exc), {})
        except Exception as exc:   # 其他错误
            self.finished.emit(
                False, f"更新失败：{exc}", {}
            )


EBIRD_DOWNLOAD_URL = (
    "https://cornell.app.box.com/s/zjci66divvqnz00k98r7pmmb6kpc69zs"
)


class UpdateDialog(QDialog):
    databaseUpdated = Signal()  # 更新成功后发出（主窗口据此刷新树）

    def __init__(self, parent=None, first_run: bool = False):
        super().__init__(parent)
        self._first_run = first_run
        self.setWindowTitle(
            "首次使用 · 导入 eBird 分类表" if first_run else "更新数据库"
        )
        self.setModal(True)
        self.setMinimumWidth(520)
        self.setAcceptDrops(True)
        self._thread = None
        self._worker = None

        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 20)
        root.setSpacing(14)

        title = make_label_selectable(QLabel(
            "首次使用 · 导入 eBird 分类表" if first_run
            else "更新 eBird 分类数据库"
        ))
        title.setObjectName("BirdNameZh")
        root.addWidget(title)

        if first_run:
            hint = make_label_selectable(QLabel(
                "本程序使用康奈尔鸟类学实验室免费提供的 eBird 分类数据，"
                "该数据需自行下载（免费、官方）。\n\n"
                "下载后，把表格（eBird_Taxonomy_*.xlsx）拖到下方区域，"
                "或点击「选择文件」导入；导入成功后才能进入程序。"
            ))
        else:
            hint = make_label_selectable(QLabel(
                "把下载的 eBird 分类表（eBird_Taxonomy_*.xlsx）拖入下方区域，\n"
                "或点击「选择文件」指定位置。转换完成后会自动更新左侧分类目录，\n"
                "已收录的照片和搜索历史会原样保留。"
            ))
        hint.setWordWrap(True)
        hint.setObjectName("PhotoCount")
        root.addWidget(hint)

        if first_run:
            # 官方下载地址行：可复制、可打开
            link_row = QHBoxLayout()
            link_label = make_label_selectable(QLabel(EBIRD_DOWNLOAD_URL))
            link_label.setObjectName("LinkText")
            link_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
            link_row.addWidget(link_label, 1)
            open_btn = QPushButton("打开下载页")
            open_btn.setProperty("class", "ghost")
            open_btn.setCursor(Qt.PointingHandCursor)
            open_btn.clicked.connect(
                lambda: QDesktopServices.openUrl(QUrl(EBIRD_DOWNLOAD_URL))
            )
            link_row.addWidget(open_btn)
            copy_btn = QPushButton("复制链接")
            copy_btn.setProperty("class", "ghost")
            copy_btn.setCursor(Qt.PointingHandCursor)
            copy_btn.clicked.connect(
                lambda: QApplication.clipboard().setText(EBIRD_DOWNLOAD_URL)
            )
            link_row.addWidget(copy_btn)
            root.addLayout(link_row)

        # 拖放区域
        self._drop_zone = QLabel(
            "\n把 eBird Excel 文件拖到这里\n\n或者\n"
        )
        self._drop_zone.setObjectName("DropZone")
        self._drop_zone.setAlignment(Qt.AlignCenter)
        self._drop_zone.setMinimumHeight(120)
        self._drop_zone.setWordWrap(True)
        root.addWidget(self._drop_zone)

        self._file_label = make_label_selectable(QLabel(""))
        self._file_label.setObjectName("PhotoCount")
        self._file_label.setWordWrap(True)
        root.addWidget(self._file_label)

        # 进度
        self._progress_bar = QProgressBar()
        self._progress_bar.setVisible(False)
        self._progress_bar.setRange(0, 100)
        root.addWidget(self._progress_bar)

        btn_row = QHBoxLayout()
        btn_row.addStretch(1)
        self._pick_btn = QPushButton("选择文件…")
        self._pick_btn.setProperty("class", "primary")
        self._pick_btn.setCursor(Qt.PointingHandCursor)
        self._pick_btn.clicked.connect(self._choose_file)
        btn_row.addWidget(self._pick_btn)

        self._close_btn = QPushButton("退出" if first_run else "关闭")
        self._close_btn.clicked.connect(self.reject)
        btn_row.addWidget(self._close_btn)
        root.addLayout(btn_row)

    # ------------------------------------------------------------------
    def _choose_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "选择 eBird 分类表",
            "",
            "Excel 文件 (*.xlsx)",
        )
        if file_path:
            self._start_update(file_path)

    def _start_update(self, file_path: str):
        if self._worker is not None:
            return  # 已有任务进行中
        path = Path(file_path)
        self._file_label.setText(f"已选择：{path.name}")
        self._progress_bar.setVisible(True)
        self._progress_bar.setValue(0)
        self._pick_btn.setEnabled(False)
        self._drop_zone.setText("正在处理，请稍候…")

        # 先创建并连好信号，再启动线程（回调必须是本 QObject 的 @Slot）
        self._thread = QThread(self)
        self._worker = UpdateWorker(path)
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.progress.connect(
            self._on_progress, Qt.QueuedConnection
        )
        self._worker.finished.connect(
            self._on_done, Qt.QueuedConnection
        )
        self._thread.finished.connect(self._worker.deleteLater)
        self._thread.finished.connect(self._thread.deleteLater)
        self._thread.start()

    # ------------------------------------------------------------------
    @Slot(int, int, str)
    def _on_progress(self, done, total, text):
        if total > 0:
            self._progress_bar.setRange(0, total)
            self._progress_bar.setValue(done)
        self._drop_zone.setText(text)

    @Slot(bool, str, dict)
    def _on_done(self, ok, message, _stats):
        self._thread = None
        self._worker = None
        self._pick_btn.setEnabled(True)
        self._progress_bar.setVisible(False)
        self._drop_zone.setText(
            "\n把 eBird Excel 文件拖到这里\n\n或者\n"
        )
        if ok:
            QMessageBox.information(self, "更新成功", message)
            self.databaseUpdated.emit()
            self.accept()
        else:
            QMessageBox.warning(self, "更新失败", message)

    # ------------------------------------------------------------------
    # 拖放
    # ------------------------------------------------------------------
    def dragEnterEvent(self, event):
        if self._worker is None and event.mimeData().hasUrls():
            if any(u.isLocalFile() for u in event.mimeData().urls()):
                event.acceptProposedAction()
                return
        event.ignore()

    def dragMoveEvent(self, event):
        if self._worker is None and event.mimeData().hasUrls():
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
            self._start_update(paths[0])
            event.acceptProposedAction()
        else:
            event.ignore()
