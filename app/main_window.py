# -*- coding: utf-8 -*-
"""
主窗口。

布局:
  顶部条  [≡ 目录] [鸟类相册] [成就清单] ......... [搜索框]
  主体    QSplitter
            左: 分类树面板（可拖动分割条调宽，可完全收起）
                - 完整目录树 / 成就清单树（只含已收录照片的鸟种）双树切换
            右: 相册区
交互: 点击"成就清单"左侧树自动过滤为只有照片的鸟种；点"鸟类相册"恢复完整树。
快捷键: Ctrl+F 聚焦搜索；Ctrl+B 收起/展开目录。
"""

from PySide6.QtCore import Qt
from PySide6.QtGui import QShortcut, QKeySequence
from PySide6.QtWidgets import (
    QMainWindow,
    QWidget,
    QFrame,
    QVBoxLayout,
    QHBoxLayout,
    QSplitter,
    QLabel,
    QPushButton,
    QStackedWidget,
    QMessageBox,
)

from . import config, db
from .taxonomy_tree import TaxonomyTree
from .search_edit import SearchBox
from .album_widget import AlbumWidget
from .settings_dialog import SettingsDialog
from .ui_utils import make_label_selectable


class MainWindow(QMainWindow):
    MODE_ALBUM = "album"            # 完整目录树
    MODE_ACHIEVEMENTS = "achievements"  # 成就清单树（只有照片的鸟种）

    def __init__(self):
        super().__init__()
        self.setWindowTitle(config.APP_NAME)
        self.resize(1300, 840)
        self.setMinimumSize(900, 600)

        self._panel_visible = True
        self._last_splitter_sizes = None
        self._tree_mode = self.MODE_ALBUM

        central = QWidget()
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        root.addWidget(self._build_top_bar())

        self._splitter = QSplitter(Qt.Horizontal)
        self._splitter.setHandleWidth(7)
        self._splitter.setChildrenCollapsible(True)
        self._tree_panel = self._build_tree_panel()
        self._album = AlbumWidget()
        self._splitter.addWidget(self._tree_panel)
        self._splitter.addWidget(self._album)
        self._splitter.setStretchFactor(0, 0)
        self._splitter.setStretchFactor(1, 1)
        self._splitter.setSizes([320, 980])
        root.addWidget(self._splitter, 1)

        self.setCentralWidget(central)

        # 状态栏消息用可选中 QLabel 显示（便于复制），非瞬时 showMessage
        self._status_label = make_label_selectable(QLabel(""))
        self.statusBar().addWidget(self._status_label, 1)
        self._update_status()

        # 信号联动
        self._tree.speciesSelected.connect(self._on_species_selected)
        self._tree_achv.speciesSelected.connect(self._on_species_selected)
        self._search.speciesChosen.connect(self._on_search_chosen)
        self._album.statusMessage.connect(self._status_label.setText)
        self._album.photosChanged.connect(self._on_photos_changed)

        # 快捷键
        QShortcut(QKeySequence("Ctrl+F"), self,
                  activated=self._focus_search)
        QShortcut(QKeySequence("Ctrl+B"), self,
                  activated=lambda: self.set_panel_visible(not self._panel_visible))

        self._album.show_hint(
            "请在左侧目录中选择一种鸟\n\n"
            "拍到满意的照片后，点击「＋ 添加照片」\n"
            "或直接把图片拖入本区域\n\n"
            "左上角可按中文名 / 英文名 / 学名搜索并直达\n"
            "右上角「成就清单」可只看已收录照片的鸟种"
        )

    # ------------------------------------------------------------------
    def _build_top_bar(self):
        bar = QFrame()
        bar.setObjectName("TopBar")
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(10, 8, 14, 8)
        layout.setSpacing(6)

        self._toggle_btn = QPushButton("≡  目录")
        self._toggle_btn.setProperty("class", "ghost")
        self._toggle_btn.setCursor(Qt.PointingHandCursor)
        self._toggle_btn.setCheckable(True)
        self._toggle_btn.setChecked(True)
        self._toggle_btn.setToolTip("收起 / 展开左侧目录（Ctrl+B）")
        self._toggle_btn.clicked.connect(self._on_toggle_clicked)
        layout.addWidget(self._toggle_btn)

        # 目录 / 成就清单 切换入口
        self._tab_album = QPushButton("鸟类相册")
        self._tab_album.setProperty("class", "navTab")
        self._tab_album.setProperty("active", True)
        self._tab_album.setCursor(Qt.PointingHandCursor)
        self._tab_album.setToolTip("显示完整鸟类目录")
        self._tab_album.clicked.connect(
            lambda: self._switch_tree(self.MODE_ALBUM)
        )
        layout.addWidget(self._tab_album)

        self._tab_achv = QPushButton("成就清单")
        self._tab_achv.setProperty("class", "navTab")
        self._tab_achv.setProperty("active", False)
        self._tab_achv.setCursor(Qt.PointingHandCursor)
        self._tab_achv.setToolTip("只显示已收录照片的鸟种")
        self._tab_achv.clicked.connect(
            lambda: self._switch_tree(self.MODE_ACHIEVEMENTS)
        )
        layout.addWidget(self._tab_achv)

        layout.addStretch(1)

        self._settings_btn = QPushButton("设置")
        self._settings_btn.setProperty("class", "ghost")
        self._settings_btn.setCursor(Qt.PointingHandCursor)
        self._settings_btn.setToolTip(
            "图片存储方式、更新数据库等设置"
        )
        self._settings_btn.clicked.connect(self._open_settings_dialog)
        layout.addWidget(self._settings_btn)

        self._search = SearchBox()
        layout.addWidget(self._search, 1)
        return bar

    # ------------------------------------------------------------------
    def _build_tree_panel(self):
        panel = QFrame()
        panel.setObjectName("TreePanel")
        panel.setMinimumWidth(220)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        head = QHBoxLayout()
        head.setContentsMargins(12, 10, 8, 8)
        self._tree_title = make_label_selectable(QLabel("鸟类目录"))
        self._tree_title.setObjectName("TreePanelTitle")
        head.addWidget(self._tree_title)
        head.addStretch(1)

        expand_btn = QPushButton("展开")
        expand_btn.setProperty("class", "ghost")
        expand_btn.setCursor(Qt.PointingHandCursor)
        expand_btn.setToolTip("展开所有科")
        expand_btn.clicked.connect(self._expand_all)
        head.addWidget(expand_btn)

        collapse_btn = QPushButton("收起")
        collapse_btn.setProperty("class", "ghost")
        collapse_btn.setCursor(Qt.PointingHandCursor)
        collapse_btn.setToolTip("收起所有科")
        collapse_btn.clicked.connect(self._collapse_all)
        head.addWidget(collapse_btn)
        layout.addLayout(head)

        # 完整目录树 + 成就清单树，切换即时（不重建 1.8 万项）
        self._tree_stack = QStackedWidget()
        self._tree = TaxonomyTree()
        self._tree_achv = TaxonomyTree(only_with_photos=True)
        self._tree_stack.addWidget(self._tree)
        self._tree_stack.addWidget(self._tree_achv)
        layout.addWidget(self._tree_stack, 1)
        return panel

    # ------------------------------------------------------------------
    # 模式切换
    # ------------------------------------------------------------------
    def _switch_tree(self, mode: str):
        self._tree_mode = mode
        achv = mode == self.MODE_ACHIEVEMENTS
        self._tree_stack.setCurrentIndex(1 if achv else 0)
        for btn, active in (
            (self._tab_album, not achv),
            (self._tab_achv, achv),
        ):
            btn.setProperty("active", active)
            btn.style().unpolish(btn)
            btn.style().polish(btn)
        if achv:
            self._update_achv_title()
        else:
            self._tree_title.setText("鸟类目录")

    def _update_achv_title(self):
        n = len(self._tree_achv._code_to_item)
        self._tree_title.setText(
            f"成就清单（{n} 种）" if n else "成就清单（暂无）"
        )

    def _current_tree(self):
        return self._tree_achv if self._tree_mode == self.MODE_ACHIEVEMENTS \
            else self._tree

    # ------------------------------------------------------------------
    # 槽
    # ------------------------------------------------------------------
    def _on_species_selected(self, code: str):
        self._album.set_species(code)

    def _on_search_chosen(self, code: str):
        # 若目录处于收起状态，搜索直达时自动展开目录
        if not self._panel_visible:
            self.set_panel_visible(True)
        if self._tree_mode == self.MODE_ACHIEVEMENTS:
            # 成就模式下优先在成就树定位；目标无照片则切回完整树
            if self._tree_achv.jump_to_code(code):
                return
            self._switch_tree(self.MODE_ALBUM)
        if not self._tree.jump_to_code(code):
            QMessageBox.information(self, "未找到", "未能在分类树中定位该鸟种。")

    def _on_photos_changed(self):
        """照片增删后：完整树标浅粉色 + 刷新成就清单树 + 状态栏计数。"""
        self._tree.update_photo_markers()
        self._tree_achv.refresh_photos()
        if self._tree_mode == self.MODE_ACHIEVEMENTS:
            self._update_achv_title()
        self._update_status()

    def _update_status(self):
        self._status_label.setText(
            f"eBird 2025 分类数据：{db.taxon_count()} 个分类单元 · "
            f"已收录照片 {db.photo_count()} 张"
        )

    def _on_toggle_clicked(self):
        self.set_panel_visible(self._toggle_btn.isChecked())

    def set_panel_visible(self, visible: bool):
        self._panel_visible = visible
        self._toggle_btn.blockSignals(True)
        self._toggle_btn.setChecked(visible)
        self._toggle_btn.blockSignals(False)
        self._toggle_btn.setText("≡  目录" if visible else "≡  显示目录")

        if visible:
            self._tree_panel.setVisible(True)
            if self._last_splitter_sizes:
                self._splitter.setSizes(self._last_splitter_sizes)
        else:
            # 完全收起左栏，整个区域只显示相册
            self._last_splitter_sizes = self._splitter.sizes()
            self._tree_panel.setVisible(False)
            self._splitter.setSizes([0, 1])

    def _expand_all(self):
        self._current_tree().expandAll()

    def _collapse_all(self):
        self._current_tree().collapse_all_families()

    def _focus_search(self):
        if not self._panel_visible:
            self.set_panel_visible(True)
        self._search.setFocus()
        self._search.selectAll()

    # ------------------------------------------------------------------
    def _open_settings_dialog(self):
        dialog = SettingsDialog(self)
        dialog.databaseUpdated.connect(self._on_database_updated)
        dialog.exec()

    def _on_database_updated(self):
        """数据库已替换：重建两棵树、恢复照片标记、刷新计数。"""
        self._tree.reload()
        self._tree.update_photo_markers()
        self._tree_achv.reload()
        if self._tree_mode == self.MODE_ACHIEVEMENTS:
            self._update_achv_title()
        self._update_status()

    def moveEvent(self, event):
        super().moveEvent(event)
        # 拖动主窗口时让搜索弹出列表跟随
        self._search.reposition_popup()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._search.reposition_popup()
