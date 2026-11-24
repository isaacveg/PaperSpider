# Copyright 2026 Isaacveg
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#     http://www.apache.org/licenses/LICENSE-2.0

"""Paper table view, header, and cell delegates."""

from __future__ import annotations

from PyQt6.QtCore import QRect, QSize, Qt, pyqtSignal
from PyQt6.QtGui import (
    QColor,
    QFont,
    QFontMetrics,
    QIcon,
    QKeySequence,
    QPainter,
    QPalette,
    QPen,
)
from PyQt6.QtWidgets import (
    QApplication,
    QHeaderView,
    QStyle,
    QStyledItemDelegate,
    QStyleOptionViewItem,
    QTableView,
)

from .paper_table_model import AUTHORS_ROLE, CHECK_COLUMN

TITLE_SCALE = 14 / 13
AUTHOR_SCALE = 12 / 13
MIN_ROW_HEIGHT = 50


def _checkbox_rect(cell_rect: QRect) -> QRect:
    size = min(18, max(12, cell_rect.width() - 10), max(12, cell_rect.height() - 10))
    rect = QRect(0, 0, size, size)
    rect.moveCenter(cell_rect.center())
    return rect


def _draw_checkbox(
    painter,
    cell_rect: QRect,
    state: Qt.CheckState,
    accent: QColor,
    muted: QColor,
) -> None:
    box = _checkbox_rect(cell_rect)
    checked = state == Qt.CheckState.Checked
    partial = state == Qt.CheckState.PartiallyChecked
    painter.save()
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    painter.setPen(QPen(accent if (checked or partial) else muted, 1.3))
    painter.setBrush(accent if (checked or partial) else Qt.BrushStyle.NoBrush)
    painter.drawRoundedRect(box.adjusted(1, 1, -1, -1), 4, 4)
    if checked or partial:
        check_color = (
            QColor("#ffffff")
            if accent.lightness() < 150
            else QColor("#101712")
        )
        pen = QPen(check_color, 2)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)
        if checked:
            painter.drawLine(
                box.left() + 5,
                box.center().y(),
                box.left() + 8,
                box.bottom() - 5,
            )
            painter.drawLine(
                box.left() + 8,
                box.bottom() - 5,
                box.right() - 4,
                box.top() + 5,
            )
        else:
            painter.drawLine(
                box.left() + 5,
                box.center().y(),
                box.right() - 5,
                box.center().y(),
            )
    painter.restore()


class CenteredCheckBoxDelegate(QStyledItemDelegate):
    """Draw a theme-aware checkbox at the exact center of its table cell."""

    def paint(self, painter, option, index) -> None:
        view_option = QStyleOptionViewItem(option)
        self.initStyleOption(view_option, index)
        state = view_option.checkState
        view_option.features &= ~QStyleOptionViewItem.ViewItemFeature.HasCheckIndicator
        style = option.widget.style() if option.widget else QApplication.style()
        style.drawControl(
            QStyle.ControlElement.CE_ItemViewItem,
            view_option,
            painter,
            option.widget,
        )
        if option.state & QStyle.StateFlag.State_Selected:
            painter.fillRect(
                QRect(option.rect.left(), option.rect.top(), 3, option.rect.height()),
                option.palette.color(QPalette.ColorRole.Link),
            )
        _draw_checkbox(
            painter,
            option.rect,
            state,
            option.palette.color(QPalette.ColorRole.Link),
            option.palette.color(QPalette.ColorRole.PlaceholderText),
        )

    def editorEvent(self, event, model, option, index) -> bool:
        return False


def paper_title_fonts(base: QFont) -> tuple[QFont, QFont]:
    """Return the title and author fonts derived from the table's font."""

    title_font = QFont(base)
    title_font.setWeight(QFont.Weight.DemiBold)
    author_font = QFont(base)
    if base.pixelSize() > 0:
        title_font.setPixelSize(round(base.pixelSize() * TITLE_SCALE))
        author_font.setPixelSize(round(base.pixelSize() * AUTHOR_SCALE))
    else:
        size = base.pointSizeF() if base.pointSizeF() > 0 else 13.0
        title_font.setPointSizeF(size * TITLE_SCALE)
        author_font.setPointSizeF(size * AUTHOR_SCALE)
    return title_font, author_font


def paper_row_height(base: QFont) -> int:
    title_font, author_font = paper_title_fonts(base)
    content = QFontMetrics(title_font).height() + QFontMetrics(author_font).height()
    return max(MIN_ROW_HEIGHT, content + 14)


class PaperTitleDelegate(QStyledItemDelegate):
    """Paint a bold paper title with a muted author line below it."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._font_cache: dict[str, tuple[QFont, QFont, QFontMetrics, QFontMetrics]] = {}

    def _fonts(self, base: QFont) -> tuple[QFont, QFont, QFontMetrics, QFontMetrics]:
        key = base.key()
        cached = self._font_cache.get(key)
        if cached is None:
            title_font, author_font = paper_title_fonts(base)
            cached = (
                title_font,
                author_font,
                QFontMetrics(title_font),
                QFontMetrics(author_font),
            )
            self._font_cache[key] = cached
        return cached

    def paint(self, painter, option, index) -> None:
        view_option = QStyleOptionViewItem(option)
        self.initStyleOption(view_option, index)
        view_option.text = ""
        style = option.widget.style() if option.widget else QApplication.style()
        style.drawControl(
            QStyle.ControlElement.CE_ItemViewItem,
            view_option,
            painter,
            option.widget,
        )
        title = str(index.data(Qt.ItemDataRole.DisplayRole) or "")
        authors = str(index.data(AUTHORS_ROLE) or "")
        selected = bool(option.state & QStyle.StateFlag.State_Selected)
        text_color = option.palette.color(
            QPalette.ColorRole.HighlightedText
            if selected
            else QPalette.ColorRole.Text
        )
        muted_color = option.palette.color(QPalette.ColorRole.PlaceholderText)
        title_font, author_font, title_metrics, author_metrics = self._fonts(
            option.font
        )
        rect = option.rect.adjusted(10, 0, -10, 0)
        title_height = title_metrics.height()
        author_height = author_metrics.height() if authors else 0
        top = rect.top() + max(0, (rect.height() - title_height - author_height) // 2)
        painter.save()
        painter.setFont(title_font)
        painter.setPen(text_color)
        painter.drawText(
            QRect(rect.left(), top, rect.width(), title_height),
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
            title_metrics.elidedText(title, Qt.TextElideMode.ElideRight, rect.width()),
        )
        if authors:
            painter.setFont(author_font)
            painter.setPen(muted_color)
            painter.drawText(
                QRect(rect.left(), top + title_height, rect.width(), author_height),
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                author_metrics.elidedText(
                    authors, Qt.TextElideMode.ElideRight, rect.width()
                ),
            )
        painter.restore()


class CenteredStatusDelegate(QStyledItemDelegate):
    """Center the abstract/PDF availability icon in its column."""

    def paint(self, painter, option, index) -> None:
        view_option = QStyleOptionViewItem(option)
        self.initStyleOption(view_option, index)
        view_option.text = ""
        view_option.icon = QIcon()
        style = option.widget.style() if option.widget else QApplication.style()
        style.drawControl(
            QStyle.ControlElement.CE_ItemViewItem,
            view_option,
            painter,
            option.widget,
        )
        icon = index.data(Qt.ItemDataRole.DecorationRole)
        if not isinstance(icon, QIcon) or icon.isNull():
            return
        size = icon.actualSize(QSize(16, 16))
        rect = QRect(0, 0, size.width(), size.height())
        rect.moveCenter(option.rect.center())
        icon.paint(painter, rect)


class SelectHeaderView(QHeaderView):
    def partial_mark_color(self) -> QColor:
        return self.palette().color(QPalette.ColorRole.Link)

    def paintSection(self, painter, rect: QRect, logicalIndex: int) -> None:
        super().paintSection(painter, rect, logicalIndex)
        if logicalIndex != CHECK_COLUMN or self.model() is None:
            return
        state = self.model().headerData(
            CHECK_COLUMN,
            Qt.Orientation.Horizontal,
            Qt.ItemDataRole.CheckStateRole,
        )
        _draw_checkbox(
            painter,
            rect,
            state,
            self.partial_mark_color(),
            self.palette().color(QPalette.ColorRole.PlaceholderText),
        )


class PaperTableView(QTableView):
    """Table view with row-level keyboard actions for papers."""

    row_activated = pyqtSignal(int)
    select_all_requested = pyqtSignal()

    def keyPressEvent(self, event) -> None:
        current = self.currentIndex()
        plain = not (
            event.modifiers()
            & ~(Qt.KeyboardModifier.KeypadModifier | Qt.KeyboardModifier.ShiftModifier)
        )
        if (
            current.isValid()
            and plain
            and event.key() in (Qt.Key.Key_Space, Qt.Key.Key_Select)
        ):
            self.model().toggle_checked(current.row())
            event.accept()
            return
        if current.isValid() and event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self.row_activated.emit(current.row())
            event.accept()
            return
        if event.matches(QKeySequence.StandardKey.SelectAll):
            self.select_all_requested.emit()
            event.accept()
            return
        super().keyPressEvent(event)
