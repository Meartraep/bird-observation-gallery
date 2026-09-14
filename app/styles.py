# -*- coding: utf-8 -*-
"""
全局 QSS 主题 —— 整个应用唯一的样式来源。

业务代码只通过 objectName / dynamic property 切换外观，
不写内联 setStyleSheet（避免"改一处不生效、被别处覆盖"）。
配色: 纸质米白 + 森林绿，无任何外部图片/图标资源依赖。
"""

APP_QSS = """
* {
    font-family: "Microsoft YaHei UI", "Microsoft YaHei", "Segoe UI", sans-serif;
    font-size: 13px;
    color: #2f3430;
}

QMainWindow, QDialog {
    background: #f4f2ec;
}

/* ---------- 顶部条 ---------- */
QFrame#TopBar {
    background: #ffffff;
    border-bottom: 1px solid #e3ddd0;
}
QLabel#AppTitle {
    font-size: 15px;
    font-weight: 600;
    color: #2f5d3a;
    padding-left: 4px;
}

/* ---------- 目录 / 成就清单 切换 tab ---------- */
QPushButton[class="navTab"] {
    border: none;
    background: transparent;
    padding: 5px 12px;
    font-size: 14px;
    font-weight: 600;
    color: #6f7a71;
    border-bottom: 2px solid transparent;
    border-radius: 0px;
}
QPushButton[class="navTab"]:hover { color: #2f5d3a; }
QPushButton[class="navTab"][active="true"] {
    color: #2f5d3a;
    border-bottom: 2px solid #3a7d44;
}

/* ---------- 搜索框 ---------- */
QLineEdit#SearchBox {
    border: 1px solid #d4cdbd;
    border-radius: 16px;
    padding: 7px 14px;
    background: #faf8f3;
    selection-background-color: #b8d4bf;
}
QLineEdit#SearchBox:focus {
    border: 1px solid #5a8f63;
    background: #ffffff;
}

/* ---------- 按钮 ---------- */
QPushButton {
    border: 1px solid #d4cdbd;
    border-radius: 6px;
    padding: 6px 14px;
    background: #ffffff;
}
QPushButton:hover { border-color: #8aae90; }
QPushButton:pressed { background: #eef3ee; }

QPushButton[class="primary"] {
    background: #3a7d44;
    border: 1px solid #3a7d44;
    color: #ffffff;
    font-weight: 600;
}
QPushButton[class="primary"]:hover { background: #33703c; }
QPushButton[class="primary"]:pressed { background: #2c6134; }

QPushButton[class="ghost"] {
    border-color: transparent;
    background: transparent;
    text-align: left;
}
QPushButton[class="ghost"]:hover { background: #eef3ee; }

QPushButton[class="dangerText"] {
    border-color: transparent;
    background: transparent;
    color: #b04a3f;
    padding: 3px 8px;
}
QPushButton[class="dangerText"]:hover { background: #f7e9e7; }

QPushButton[class="moveBtn"] {
    border: 1px solid #d4cdbd;
    border-radius: 4px;
    padding: 1px 8px;
    font-size: 12px;
    background: #faf8f3;
}
QPushButton[class="moveBtn"]:hover { border-color: #8aae90; }
QPushButton[class="moveBtn"]:pressed { background: #eef3ee; }
QPushButton[class="moveBtn"]:disabled {
    color: #c9c2b2;
    border-color: #e8e2d5;
    background: #f6f4ee;
}

/* ---------- 左侧目录树 ---------- */
QFrame#TreePanel {
    background: #ffffff;
    border-right: 1px solid #e3ddd0;
}
QLabel#TreePanelTitle {
    font-weight: 600;
    color: #2f5d3a;
}
QTreeWidget {
    border: none;
    background: #ffffff;
    outline: none;
    show-decoration-selected: 1;
}
QTreeWidget::item {
    padding: 3px 2px;
}
QTreeWidget::item:hover {
    background: #f1f5f1;
}
QTreeWidget::item:selected {
    background: #dcebe0;
}
QTreeWidget::branch {
    background: #ffffff;
}

/* ---------- 右侧相册 ---------- */
QFrame#AlbumHeader {
    background: #faf8f3;
    border-bottom: 1px solid #e8e2d5;
}
QLabel#BirdNameZh {
    font-size: 19px;
    font-weight: 700;
    color: #27332a;
}
QLabel#BirdNameSci {
    color: #6f7a71;
    font-style: italic;
}
QLabel#PhotoCount {
    color: #7c867e;
}
QLabel#EmptyHint {
    color: #9aa39b;
    font-size: 15px;
}

QScrollArea#AlbumScroll {
    background: #f4f2ec;
    border: none;
}
QWidget#CardsContainer { background: #f4f2ec; }

QFrame#PhotoCard {
    background: #ffffff;
    border: 1px solid #e6e0d3;
    border-radius: 10px;
}
QFrame#PhotoCard:hover { border-color: #c8d8cb; }

QPushButton#ThumbButton {
    border: none;
    background: transparent;
}
QPushButton#ThumbButton:hover { background: #f4f7f4; }

QPlainTextEdit#NoteEdit {
    border: 1px solid #e6e0d3;
    border-radius: 6px;
    background: #fbfaf6;
    padding: 4px 6px;
}
QPlainTextEdit#NoteEdit:focus {
    border-color: #8aae90;
    background: #ffffff;
}

QLabel#CardDate { color: #9aa39b; font-size: 11px; }
QLabel#SavedHint { color: #8aa68f; font-size: 11px; }

/* ---------- 搜索弹出结果 ---------- */
QListWidget#SearchPopup {
    border: 1px solid #c9c2b2;
    border-radius: 8px;
    background: #ffffff;
    outline: none;
    padding: 4px;
}
QListWidget#SearchPopup::item {
    border-radius: 6px;
    padding: 0px 8px;
}
QListWidget#SearchPopup::item:selected,
QListWidget#SearchPopup::item:hover {
    background: #dcebe0;
}

/* ---------- 分割条 ---------- */
QSplitter::handle {
    background: #e3ddd0;
}
QSplitter::handle:horizontal { width: 7px; }
QSplitter::handle:horizontal:hover { background: #9cbf9f; }

/* ---------- 滚动条 ---------- */
QScrollBar:vertical {
    background: transparent;
    width: 11px;
    margin: 2px;
}
QScrollBar::handle:vertical {
    background: #c9c2b2;
    border-radius: 4px;
    min-height: 30px;
}
QScrollBar::handle:vertical:hover { background: #9fa89e; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QScrollBar:horizontal { height: 11px; background: transparent; }
QScrollBar::handle:horizontal {
    background: #c9c2b2;
    border-radius: 4px;
    min-width: 30px;
}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0; }

/* ---------- 其他 ---------- */
QProgressDialog QLabel { color: #2f3430; }
QProgressBar {
    border: 1px solid #d4cdbd;
    border-radius: 6px;
    background: #faf8f3;
    height: 14px;
    text-align: center;
}
QProgressBar::chunk { background: #5a8f63; border-radius: 5px; }

QToolTip {
    background: #2f3a31;
    color: #f4f2ec;
    border: none;
    padding: 4px 8px;
}

/* ---------- 更新数据库弹窗 ---------- */
QLabel#DropZone {
    border: 2px dashed #c9c2b2;
    border-radius: 10px;
    background: #faf8f3;
    color: #7c867e;
    font-size: 14px;
}
QLabel#DropZone:hover { border-color: #8aae90; }
QLabel#LinkText { color: #3a7d44; font-size: 12px; }

/* ---------- 设置弹窗 ---------- */
QRadioButton {
    spacing: 8px;
    padding: 3px 0;
}
QRadioButton::indicator {
    width: 15px;
    height: 15px;
}
QFrame[frameShape="4"] {  /* HLine 分隔线 */
    color: #e3ddd0;
    background: #e3ddd0;
    max-height: 1px;
    border: none;
}

"""
