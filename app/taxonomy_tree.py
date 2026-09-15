# -*- coding: utf-8 -*-
"""
左侧鸟类分类树（真正的树形控件，不是平铺列表）。

层级: 目(order, 45) -> 科(family, 251) -> 分类单元(species/issf/...，17891)
  - 默认展开"目"，显示各科；科默认收起；
  - 叶子行双行显示: 第一行中文名优先(缺失回退英文名)+类别标记，
    第二行拉丁学名；目/科行右侧显示下属数量；
  - 自定义 QStyledItemDelegate 绘制，避免为近 1.8 万行创建独立 widget。
"""

from PySide6.QtCore import Qt, QSize, Signal, QRect
from PySide6.QtGui import QFont, QFontMetrics, QColor
from PySide6.QtWidgets import (
    QTreeWidget,
    QTreeWidgetItem,
    QStyledItemDelegate,
    QStyle,
    QStyleOptionViewItem,
)

from . import db

# 自定义数据角色
ROLE_LEVEL = Qt.UserRole + 1       # 0=目 1=科 2=叶子
ROLE_CODE = Qt.UserRole + 2        # 叶子: species_code
ROLE_SECONDARY = Qt.UserRole + 3   # 副文本(科英文名 / 叶子学名)
ROLE_COUNT = Qt.UserRole + 4       # 目/科下属数量
ROLE_CATEGORY = Qt.UserRole + 5    # 叶子的 eBird category
ROLE_HAS_PHOTO = Qt.UserRole + 6   # 叶子是否已有照片（完整树中标注浅粉色）

CATEGORY_TAGS = {
    "issf": "亚种",
    "hybrid": "杂交",
    "slash": "组合",
    "spuh": "类群",
    "form": "型",
    "domestic": "家养",
    "intergrade": "渐变",
}

_LEVEL_ORDER, _LEVEL_FAMILY, _LEVEL_TAXON = 0, 1, 2


def _px_font(px: int, bold: bool = False, italic: bool = False) -> QFont:
    """按像素尺寸构造字体。

    点值字体在本应用里实际按 13px 光栅化，QFontMetrics 测得的宽度比真实绘制
    宽度小约 6%（20 多个字符累计可差 10px 以上）。而本代理的排版（主名 +
    类别标记、科名的副文本）依赖"测量宽度 == 绘制宽度"，于是标记会压到鸟名
    最后一个字上。像素尺寸字体的测量值与绘制宽度一致（各缩放比下均验证过）。
    """
    font = QFont()
    font.setPixelSize(px)
    font.setBold(bold)
    font.setItalic(italic)
    return font


def display_name(row) -> str:
    """树叶子显示名: 中文名优先，无中文名则用英文名。"""
    return row["name_zh"] or row["name_en"]


class TaxonomyDelegate(QStyledItemDelegate):
    """目/科: 单行；叶子: 主名 + 学名双行。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._order_font = _px_font(14, bold=True)
        self._family_font = _px_font(13, bold=True)
        self._family_aux_font = _px_font(13, italic=True)
        self._leaf_font = _px_font(13)
        self._sci_font = _px_font(10, italic=True)
        self._tag_font = _px_font(10)

        self._order_fm = QFontMetrics(self._order_font)
        self._family_fm = QFontMetrics(self._family_font)
        self._family_aux_fm = QFontMetrics(self._family_aux_font)
        self._leaf_fm = QFontMetrics(self._leaf_font)
        self._sci_fm = QFontMetrics(self._sci_font)
        self._tag_fm = QFontMetrics(self._tag_font)

    # ------------------------------------------------------------------
    def sizeHint(self, option, index):
        level = index.data(ROLE_LEVEL)
        if level == _LEVEL_ORDER:
            return QSize(option.rect.width(), self._order_fm.height() + 12)
        if level == _LEVEL_FAMILY:
            return QSize(option.rect.width(), self._family_fm.height() + 10)
        return QSize(
            option.rect.width(),
            self._leaf_fm.height() + self._sci_fm.height() + 12,
        )

    # ------------------------------------------------------------------
    def paint(self, painter, option, index):
        # 先让 Qt 画好背景(选中/悬停/分支缩进)，再覆盖文字
        opt = QStyleOptionViewItem(option)
        opt.text = ""
        option.widget.style().drawControl(
            QStyle.CE_ItemViewItem, opt, painter, option.widget
        )

        level = index.data(ROLE_LEVEL)
        rect = opt.rect.adjusted(6, 0, -10, 0)
        painter.save()

        if level == _LEVEL_ORDER:
            self._paint_order_family(
                painter, rect, index,
                font=self._order_font, fm=self._order_fm,
                aux_font=None, aux_fm=None,
                primary_color=QColor("#2f5d3a"),
            )
        elif level == _LEVEL_FAMILY:
            self._paint_order_family(
                painter, rect, index,
                font=self._family_font, fm=self._family_fm,
                aux_font=self._family_aux_font, aux_fm=self._family_aux_fm,
                primary_color=QColor("#374a3c"),
            )
        else:
            self._paint_leaf(painter, rect, index)

        painter.restore()

    # ------------------------------------------------------------------
    def _paint_order_family(self, painter, rect, index,
                            font, fm, aux_font, aux_fm, primary_color):
        """目/科行: 粗体主名 [+ 灰色斜体副名] + 右侧数量。"""
        top = rect.top() + (rect.height() - fm.height()) // 2
        count = index.data(ROLE_COUNT)
        count_text = str(count) if count is not None else ""
        count_w = fm.horizontalAdvance(count_text) if count_text else 0
        right_limit = rect.right() - (count_w + 12 if count_w else 0)

        x = rect.left()
        painter.setFont(font)
        painter.setPen(primary_color)
        primary = fm.elidedText(
            index.data(Qt.DisplayRole), Qt.ElideRight,
            max(40, right_limit - x),
        )
        painter.drawText(QRect(x, top, right_limit - x, fm.height()),
                         Qt.AlignLeft | Qt.AlignTop, primary)
        x += fm.horizontalAdvance(primary)

        secondary = index.data(ROLE_SECONDARY) if aux_font else None
        if secondary and x + 60 < right_limit:
            painter.setFont(aux_font)
            painter.setPen(QColor("#8a968c"))
            sec = aux_fm.elidedText(
                "  ·  " + secondary, Qt.ElideRight,
                max(0, right_limit - x),
            )
            painter.drawText(QRect(x, top, right_limit - x, aux_fm.height()),
                             Qt.AlignLeft | Qt.AlignTop, sec)

        if count_w:
            painter.setFont(font)
            painter.setPen(QColor("#9aa39b"))
            painter.drawText(
                QRect(rect.right() - count_w, top, count_w, fm.height()),
                Qt.AlignLeft | Qt.AlignTop,
                count_text,
            )

    # ------------------------------------------------------------------
    def _paint_leaf(self, painter, rect, index):
        primary = index.data(Qt.DisplayRole)
        sci = index.data(ROLE_SECONDARY) or ""
        category = index.data(ROLE_CATEGORY)
        tag = CATEGORY_TAGS.get(category) if category else None

        # 主名颜色：有照片 -> 浅粉色（选中与否均保持，选中由绿色背景表达）；
        # 无照片 -> 深灰
        if index.data(ROLE_HAS_PHOTO):
            name_color = QColor("#eba0ab")
        else:
            name_color = QColor("#2f3430")

        # 第一行: 主名 + 类别标记
        line1 = QRect(rect.left(), rect.top() + 4,
                      rect.width(), self._leaf_fm.height())
        painter.setFont(self._leaf_font)
        painter.setPen(name_color)
        tag_w = 0
        if tag:
            tag_w = self._tag_fm.horizontalAdvance(tag) + 14
        primary = self._leaf_fm.elidedText(
            primary, Qt.ElideRight, max(20, line1.width() - tag_w)
        )
        painter.drawText(line1, Qt.AlignLeft | Qt.AlignTop, primary)

        if tag:
            painter.setFont(self._tag_font)
            painter.setPen(QColor("#9c7a3c"))
            tx = line1.left() + self._leaf_fm.horizontalAdvance(primary) + 8
            painter.drawText(
                QRect(tx, line1.top() + 2, tag_w, self._tag_fm.height()),
                Qt.AlignLeft | Qt.AlignTop, tag,
            )

        # 第二行: 拉丁学名
        painter.setFont(self._sci_font)
        painter.setPen(QColor("#8a968c"))
        line2 = QRect(rect.left(), line1.bottom() + 2,
                      rect.width(), self._sci_fm.height())
        painter.drawText(
            line2, Qt.AlignLeft | Qt.AlignTop,
            self._sci_fm.elidedText(sci, Qt.ElideRight, line2.width()),
        )


class TaxonomyTree(QTreeWidget):
    speciesSelected = Signal(str)  # 选中具体鸟类条目时发出 species_code

    def __init__(self, parent=None, only_with_photos: bool = False):
        super().__init__(parent)
        self.setHeaderHidden(True)
        self.setRootIsDecorated(True)
        self.setUniformRowHeights(False)
        self.setVerticalScrollMode(QTreeWidget.ScrollPerPixel)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setEditTriggers(QTreeWidget.NoEditTriggers)
        self.setSelectionMode(QTreeWidget.SingleSelection)
        self.setItemDelegate(TaxonomyDelegate(self))

        self._only_with_photos = only_with_photos
        self._code_to_item = {}
        self._order_items = {}   # order_name -> item
        self._family_items = {}  # (order_name, family_sci) -> item

        self._populate()
        self.currentItemChanged.connect(self._on_current_changed)

    # ------------------------------------------------------------------
    def _populate(self):
        self.clear()
        self._code_to_item = {}
        self._order_items = {}
        self._family_items = {}
        order_counts = {}
        family_counts = {}

        # 成就清单模式：只保留已有照片的鸟种，祖先目/科随叶子一并纳入
        photo_codes = db.photo_species_codes() if self._only_with_photos else None

        for row in db.iter_taxonomy():
            if photo_codes is not None and row["species_code"] not in photo_codes:
                continue
            order_name = row["order_name"] or "（未分类）"
            family_key = row["family_sci"] or "（未分类）"

            order_item = self._order_items.get(order_name)
            if order_item is None:
                order_item = QTreeWidgetItem(self)
                order_item.setData(0, Qt.DisplayRole, order_name)
                order_item.setData(0, ROLE_LEVEL, _LEVEL_ORDER)
                order_item.setData(0, ROLE_COUNT, 0)
                self._order_items[order_name] = order_item
                order_counts[order_name] = 0

            fkey = (order_name, family_key)
            family_item = self._family_items.get(fkey)
            if family_item is None:
                family_item = QTreeWidgetItem(order_item)
                family_item.setData(0, Qt.DisplayRole, family_key)
                family_item.setData(0, ROLE_SECONDARY, row["family_en"] or "")
                family_item.setData(0, ROLE_LEVEL, _LEVEL_FAMILY)
                family_item.setData(0, ROLE_COUNT, 0)
                self._family_items[fkey] = family_item
                family_counts[fkey] = 0

            leaf = QTreeWidgetItem(family_item)
            leaf.setData(0, Qt.DisplayRole, display_name(row))
            leaf.setData(0, ROLE_SECONDARY, row["sci_name"])
            leaf.setData(0, ROLE_LEVEL, _LEVEL_TAXON)
            leaf.setData(0, ROLE_CODE, row["species_code"])
            leaf.setData(0, ROLE_CATEGORY, row["category"])
            leaf.setToolTip(
                0,
                f"{display_name(row)}\n{row['sci_name']}\n{row['name_en']}",
            )
            self._code_to_item[row["species_code"]] = leaf

            order_counts[order_name] += 1
            family_counts[fkey] += 1

        # 回填数量并默认展开"目"这一层
        for name, item in self._order_items.items():
            item.setData(0, ROLE_COUNT, order_counts[name])
            item.setExpanded(True)
        for key, item in self._family_items.items():
            item.setData(0, ROLE_COUNT, family_counts[key])

    # ------------------------------------------------------------------
    def _on_current_changed(self, current, _previous):
        if current is None:
            return
        code = current.data(0, ROLE_CODE)
        if code:
            self.speciesSelected.emit(code)

    # ------------------------------------------------------------------
    def reload(self):
        """数据库更新后重建整树（保留当前模式）。"""
        self._populate()

    def refresh_photos(self):
        """照片增删后重建成就清单树（仅在 only_with_photos 模式有意义）。"""
        if self._only_with_photos:
            self._populate()

    def species_count(self) -> int:
        """当前树中分类单元（叶子）的数量（成就清单标题用）。"""
        return len(self._code_to_item)

    def update_photo_markers(self):
        """完整树：将有照片的叶子标为浅粉色，增量更新、不重建整树。
        只对发生变化的节点写入数据，随后触发整片视口重绘。"""
        photo_codes = db.photo_species_codes()
        changed = False
        for code, item in self._code_to_item.items():
            has = code in photo_codes
            if bool(item.data(0, ROLE_HAS_PHOTO)) != has:
                item.setData(0, ROLE_HAS_PHOTO, has)
                changed = True
        if changed:
            self.viewport().update()

    def jump_to_code(self, species_code: str) -> bool:
        """搜索直达: 展开父级 -> 选中并滚动到目标鸟种。"""
        item = self._code_to_item.get(species_code)
        if item is None:
            return False
        parent = item.parent()
        if parent is not None:
            parent.setExpanded(True)
            if parent.parent() is not None:
                parent.parent().setExpanded(True)
        self.setCurrentItem(item)
        self.scrollToItem(item, QTreeWidget.PositionAtCenter)
        self.setFocus()
        return True

    def expand_all_families(self):
        for item in self._family_items.values():
            item.setExpanded(True)

    def collapse_all_families(self):
        for item in self._family_items.values():
            item.setExpanded(False)
