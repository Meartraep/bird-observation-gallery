# -*- coding: utf-8 -*-
"""文本选择小工具：让 QLabel 文本可拖选复制。"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel


def make_label_selectable(label: QLabel) -> QLabel:
    """返回同一个 QLabel（便于链式创建），文本可用鼠标拖选复制。"""
    label.setTextInteractionFlags(Qt.TextSelectableByMouse)
    return label


def apply_text_selectable(root) -> None:
    """递归设置 root 下所有已存在的 QLabel 可拖选复制。"""
    for label in root.findChildren(QLabel):
        label.setTextInteractionFlags(Qt.TextSelectableByMouse)
