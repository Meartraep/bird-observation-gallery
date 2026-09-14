# -*- coding: utf-8 -*-
"""
左上角搜索框。

  - 输入 180ms 防抖后查询（中文名 / 英文名 / 拉丁学名 / eBird 代码）；
  - 结果以不抢焦点的弹出列表双行展示，点击或回车即"直达"
    （左侧树自动展开并定位到该鸟，右侧切换相册）；
  - ↑/↓ 选择，Enter 确认，Esc 关闭。
"""

from PySide6.QtCore import Qt, QTimer, QSize, QRect, Signal
from PySide6.QtGui import QFont, QFontMetrics, QColor
from PySide6.QtWidgets import (
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QStyledItemDelegate,
    QStyle,
    QStyleOptionViewItem,
)

from . import db

ROLE_RESULT = Qt.UserRole + 1


class SearchResultDelegate(QStyledItemDelegate):
    """双行结果: 第一行中文名+英文名；第二行学名 · 科 · 目。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._title_font = QFont()
        self._title_font.setBold(True)
        self._title_fm = QFontMetrics(self._title_font)

        self._aux_font = QFont()
        self._aux_fm = QFontMetrics(self._aux_font)

        self._sci_font = QFont()
        self._sci_font.setItalic(True)
        if self._sci_font.pointSize() > 0:
            self._sci_font.setPointSize(self._sci_font.pointSize() - 1)
        self._sci_fm = QFontMetrics(self._sci_font)

    def sizeHint(self, option, index):
        data = index.data(ROLE_RESULT)
        if data:
            if data.get("action") == "header":
                # 弹窗顶部"搜索历史"标题行
                return QSize(option.rect.width(), 24)
            if data.get("history"):
                return QSize(option.rect.width(), self._title_fm.height() + 14)
            if data.get("action") == "clear":
                return QSize(option.rect.width(), 30)
        return QSize(option.rect.width(),
                     self._title_fm.height() + self._sci_fm.height() + 12)

    def paint(self, painter, option, index):
        opt = QStyleOptionViewItem(option)
        opt.text = ""
        option.widget.style().drawControl(
            QStyle.CE_ItemViewItem, opt, painter, option.widget
        )
        r = opt.rect.adjusted(10, 5, -10, -5)
        data = index.data(ROLE_RESULT)
        if not data:
            return

        painter.save()

        line1 = QRect(r.left(), r.top(), r.width(), self._title_fm.height())

        # 弹窗顶部"搜索历史"标题行（独立行，不与词混排）
        if data.get("action") == "header":
            painter.setFont(self._aux_font)
            painter.setPen(QColor("#9aa39b"))
            painter.drawText(
                line1, Qt.AlignLeft | Qt.AlignTop,
                data.get("text") or "",
            )
            painter.restore()
            return

        # 历史词: 词占满整行（标签已独立成行，不再挤压词）
        if data.get("history"):
            term = data.get("term") or ""
            painter.setFont(self._title_font)
            painter.setPen(QColor("#27332a"))
            term_show = self._title_fm.elidedText(
                term, Qt.ElideRight, max(20, line1.width())
            )
            painter.drawText(line1, Qt.AlignLeft | Qt.AlignTop, term_show)
            painter.restore()
            return

        # 清空项: 一行灰色提示
        if data.get("action") == "clear":
            painter.setFont(self._aux_font)
            painter.setPen(QColor("#9aa39b"))
            painter.drawText(
                line1, Qt.AlignLeft | Qt.AlignTop,
                "清空搜索历史",
            )
            painter.restore()
            return

        # 第一行: 中文名(粗体) + 英文名(灰)
        zh = data.get("name_zh")
        en = data.get("name_en") or ""
        if zh:
            painter.setFont(self._title_font)
            painter.setPen(QColor("#27332a"))
            zh_show = self._title_fm.elidedText(
                zh, Qt.ElideRight, max(30, int(line1.width() * 0.62))
            )
            painter.drawText(line1, Qt.AlignLeft | Qt.AlignTop, zh_show)
            x = line1.left() + self._title_fm.horizontalAdvance(zh_show) + 12
            painter.setFont(self._aux_font)
            painter.setPen(QColor("#7c867e"))
            painter.drawText(
                QRect(x, line1.top() + 1, line1.right() - x, self._aux_fm.height()),
                Qt.AlignLeft | Qt.AlignTop,
                self._aux_fm.elidedText(en, Qt.ElideRight, line1.right() - x),
            )
        else:
            painter.setFont(self._title_font)
            painter.setPen(QColor("#27332a"))
            painter.drawText(
                line1, Qt.AlignLeft | Qt.AlignTop,
                self._title_fm.elidedText(en, Qt.ElideRight, line1.width()),
            )

        # 第二行: 学名 · 科 · 目
        parts = [data.get("sci_name") or "",
                 data.get("family_sci") or "",
                 data.get("order_name") or "未分类"]
        line2_text = " · ".join(p for p in parts if p)
        painter.setFont(self._sci_font)
        painter.setPen(QColor("#93a097"))
        line2 = QRect(r.left(), line1.bottom() + 3,
                      r.width(), self._sci_fm.height())
        painter.drawText(
            line2, Qt.AlignLeft | Qt.AlignTop,
            self._sci_fm.elidedText(line2_text, Qt.ElideRight, line2.width()),
        )
        painter.restore()


class SearchBox(QLineEdit):
    speciesChosen = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("SearchBox")
        self.setPlaceholderText("搜索中文名、英文名或拉丁学名…（Ctrl+F 聚焦）")
        self.setClearButtonEnabled(True)
        self.setMinimumWidth(300)
        self.setMaximumWidth(460)

        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.setInterval(180)
        self._timer.timeout.connect(self._do_search)
        self.textChanged.connect(self._on_text_changed)
        self._last_term = ""  # 最近一次实际执行搜索的词，用于写入历史

        # 不抢焦点的弹出层：输入焦点始终留在输入框，键盘逻辑自控
        self._popup = QListWidget(self)
        self._popup.setObjectName("SearchPopup")
        self._popup.setWindowFlags(
            Qt.ToolTip | Qt.FramelessWindowHint
        )
        self._popup.setAttribute(Qt.WA_ShowWithoutActivating)
        self._popup.setItemDelegate(SearchResultDelegate(self._popup))
        self._popup.setVerticalScrollMode(QListWidget.ScrollPerPixel)
        self._popup.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._popup.setUniformItemSizes(True)
        self._popup.setMouseTracking(True)
        self._popup.itemClicked.connect(self._choose_item)
        self._popup.hide()

    # ------------------------------------------------------------------
    def _on_text_changed(self, text):
        if text.strip():
            self._timer.start()
        else:
            self._timer.stop()
            # 输入被清空：改为展示搜索历史
            self._show_history()

    def focusInEvent(self, event):
        super().focusInEvent(event)
        if not self.text().strip():
            self._show_history()

    def _show_history(self):
        """输入为空时：弹出搜索历史（顶部"搜索历史"标题行 + 词列表 + 清空项）。"""
        terms = db.list_search_history(limit=20)
        self._popup.clear()
        if terms:
            header = QListWidgetItem()
            header.setData(ROLE_RESULT, {"action": "header", "text": "搜索历史"})
            header.setSizeHint(QSize(0, 24))
            header.setFlags(Qt.NoItemFlags)  # 标题行不可选中
            self._popup.addItem(header)
            for term in terms:
                item = QListWidgetItem()
                item.setData(ROLE_RESULT, {"history": True, "term": term})
                item.setSizeHint(QSize(0, 38))
                self._popup.addItem(item)
            item = QListWidgetItem()
            item.setData(ROLE_RESULT, {"action": "clear"})
            item.setSizeHint(QSize(0, 30))
            self._popup.addItem(item)
            self._popup.setCurrentRow(1)  # 默认选中第一个词
            self._show_popup()
        else:
            self._popup.hide()

    def _do_search(self):
        term = self.text().strip()
        if len(term) < 1:
            self._show_history()
            return

        results = db.search_taxa(term, limit=20)
        self._last_term = term
        self._popup.clear()
        for row in results:
            item = QListWidgetItem()
            item.setData(ROLE_RESULT, row)
            item.setSizeHint(QSize(0, 52))
            self._popup.addItem(item)

        if results:
            self._popup.setCurrentRow(0)
            self._show_popup()
        else:
            self._popup.hide()

    def _show_popup(self):
        width = max(self.width(), 460)
        total = sum(
            self._popup.sizeHintForRow(i) for i in range(self._popup.count())
        ) + 10
        self._popup.setFixedWidth(width)
        self._popup.setFixedHeight(min(total, 380))
        self.reposition_popup()
        self._popup.show()
        self.reposition_popup()  # show 后再定位一次，确保不被系统重置

    def reposition_popup(self):
        """把弹出列表对齐到搜索框正下方。窗口拖动/缩放后由外部调用保持跟随。"""
        pos = self.mapToGlobal(self.rect().bottomLeft())
        self._popup.move(pos)

    def moveEvent(self, event):
        super().moveEvent(event)
        if self._popup.isVisible():
            self.reposition_popup()

    # ------------------------------------------------------------------
    def _choose_item(self, item):
        data = item.data(ROLE_RESULT)
        if not data:
            return

        if data.get("action") in ("header", "clear"):
            if data.get("action") == "clear":
                db.clear_search_history()
                self._show_history()  # 清空后无历史自动隐藏
            return

        if data.get("history"):
            self._choose_history(data.get("term") or "")
            return

        # 物种结果：记录本次输入词到历史，然后直达
        db.add_search_history(self._last_term or data.get("name_en") or "")
        code = data["species_code"]
        # 直达后保留目标名称并全选，方便继续输入下一次搜索
        self.blockSignals(True)
        self.setText(data.get("name_zh") or data.get("name_en") or code)
        self.blockSignals(False)
        self.selectAll()
        self._popup.hide()
        self.speciesChosen.emit(code)

    def _choose_history(self, term: str):
        """点击历史词：填入输入框 → 立即物种搜索 → 直达第一条。"""
        self.blockSignals(True)
        self.setText(term)
        self.blockSignals(False)
        self._timer.stop()
        self._do_search()
        self.choose_current()

    def choose_current(self):
        item = self._popup.currentItem()
        if item is not None:
            self._choose_item(item)

    # ------------------------------------------------------------------
    def keyPressEvent(self, event):
        key = event.key()
        popup_visible = self._popup.isVisible()

        if popup_visible and key in (Qt.Key_Down, Qt.Key_Up):
            row = self._popup.currentRow()
            count = self._popup.count()
            if count:
                row = (row + (1 if key == Qt.Key_Down else -1)) % count
                self._popup.setCurrentRow(row)
            event.accept()
            return
        if popup_visible and key in (Qt.Key_Return, Qt.Key_Enter):
            self.choose_current()
            event.accept()
            return
        if key == Qt.Key_Escape and popup_visible:
            self._popup.hide()
            event.accept()
            return
        super().keyPressEvent(event)

    def focusOutEvent(self, event):
        # 稍候再关，避免点击弹出项的瞬间先收到失焦导致列表消失
        QTimer.singleShot(120, self._maybe_hide_popup)
        super().focusOutEvent(event)

    def _maybe_hide_popup(self):
        if not self._popup.underMouse():
            self._popup.hide()
