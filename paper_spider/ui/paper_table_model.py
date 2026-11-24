# Copyright 2026 Isaacveg
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#     http://www.apache.org/licenses/LICENSE-2.0

from __future__ import annotations

from typing import AbstractSet, List, Mapping, Optional

from PyQt6.QtCore import QAbstractTableModel, QModelIndex, Qt, pyqtSignal

from ..text_utils import display_title
from .i18n import tr
from .theme import availability_icon
from .workspace_view_helpers import paper_id_for_row

CHECK_COLUMN = 0
PAPER_COLUMN = 1
ABSTRACT_COLUMN = 2
PDF_COLUMN = 3
COLUMN_COUNT = 4
AUTHORS_ROLE = Qt.ItemDataRole.UserRole + 1
HEADERS = ("", "Papers / authors", "Abstract", "PDF")


def row_title(row: dict) -> str:
    """Readable title for display, with LaTeX markup rendered."""

    title = row.get("display_title")
    if title is None:
        title = display_title(str(row.get("title") or ""))
        row["display_title"] = title
    return str(title)


def row_available(row: Mapping[str, object], column: int) -> bool:
    """Whether the abstract or PDF shown in ``column`` is available locally."""

    if column == ABSTRACT_COLUMN:
        return bool(row.get("abstract_status") or row.get("abstract"))
    return bool(row.get("has_pdf"))


class PaperTableModel(QAbstractTableModel):
    selection_changed = pyqtSignal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._rows: List[dict] = []
        self._row_index: dict[str, int] = {}
        self._sort_column: Optional[int] = None
        self._sort_order = Qt.SortOrder.AscendingOrder
        self._selected_ids: set[str] = set()
        self._status_icons = {
            True: availability_icon(True),
            False: availability_icon(False),
        }

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        if parent.isValid():
            return 0
        return len(self._rows)

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:
        if parent.isValid():
            return 0
        return COLUMN_COUNT

    def headerData(
        self,
        section: int,
        orientation: Qt.Orientation,
        role: int = Qt.ItemDataRole.DisplayRole,
    ):
        if orientation != Qt.Orientation.Horizontal or not 0 <= section < COLUMN_COUNT:
            return None
        if role == Qt.ItemDataRole.DisplayRole:
            if not section:
                return ""
            label = tr(HEADERS[section])
            if section == self._sort_column:
                arrow = "↓" if self._sort_order == Qt.SortOrder.DescendingOrder else "↑"
                return f"{label} {arrow}"
            return label
        if section == CHECK_COLUMN and role == Qt.ItemDataRole.CheckStateRole:
            return self.selection_state()
        if role == Qt.ItemDataRole.TextAlignmentRole:
            if section == PAPER_COLUMN:
                return Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
            return Qt.AlignmentFlag.AlignCenter
        return None

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole):
        if not index.isValid() or index.row() >= len(self._rows):
            return None
        row = self._rows[index.row()]
        column = index.column()
        if column == CHECK_COLUMN:
            if role == Qt.ItemDataRole.CheckStateRole:
                return (
                    Qt.CheckState.Checked
                    if paper_id_for_row(row) in self._selected_ids
                    else Qt.CheckState.Unchecked
                )
            if role == Qt.ItemDataRole.TextAlignmentRole:
                return Qt.AlignmentFlag.AlignCenter
            return None
        if column == PAPER_COLUMN:
            title = row_title(row)
            authors = str(row.get("authors_text") or "")
            if role == Qt.ItemDataRole.DisplayRole:
                return title
            if role == Qt.ItemDataRole.ToolTipRole:
                return f"{title}\n{authors}" if authors else title
            if role == Qt.ItemDataRole.AccessibleTextRole:
                return f"{title} — {authors}" if authors else title
            if role == AUTHORS_ROLE:
                return authors
            if role == Qt.ItemDataRole.TextAlignmentRole:
                return Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
            return None
        if column in (ABSTRACT_COLUMN, PDF_COLUMN):
            available = self._available(row, column)
            if role == Qt.ItemDataRole.DecorationRole:
                return self._status_icons[available]
            if role == Qt.ItemDataRole.ToolTipRole:
                return self._availability_text(column, available)
            if role == Qt.ItemDataRole.AccessibleTextRole:
                return self._availability_text(column, available)
            if role == Qt.ItemDataRole.TextAlignmentRole:
                return Qt.AlignmentFlag.AlignCenter
            if role == Qt.ItemDataRole.DisplayRole:
                return ""
        return None

    def _available(self, row: dict, column: int) -> bool:
        return row_available(row, column)

    def _availability_text(self, column: int, available: bool) -> str:
        if column == ABSTRACT_COLUMN:
            return tr("Abstract available") if available else tr(
                "No abstract available"
            )
        return tr("PDF available") if available else tr("No PDF available")

    def flags(self, index: QModelIndex) -> Qt.ItemFlag:
        if not index.isValid():
            return Qt.ItemFlag.NoItemFlags
        flags = Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable
        if index.column() == CHECK_COLUMN:
            flags |= Qt.ItemFlag.ItemIsUserCheckable
        return flags

    def setData(
        self,
        index: QModelIndex,
        value,
        role: int = Qt.ItemDataRole.EditRole,
    ) -> bool:
        if (
            not index.isValid()
            or index.column() != CHECK_COLUMN
            or index.row() >= len(self._rows)
            or role != Qt.ItemDataRole.CheckStateRole
        ):
            return False
        paper_id = paper_id_for_row(self._rows[index.row()])
        if value in (Qt.CheckState.Checked, Qt.CheckState.Checked.value):
            self._selected_ids.add(paper_id)
        else:
            self._selected_ids.discard(paper_id)
        self.dataChanged.emit(index, index, [Qt.ItemDataRole.CheckStateRole])
        self.headerDataChanged.emit(
            Qt.Orientation.Horizontal, CHECK_COLUMN, CHECK_COLUMN
        )
        self.selection_changed.emit()
        return True

    def toggle_checked(self, row: int) -> bool:
        index = self.index(row, CHECK_COLUMN)
        if not index.isValid():
            return False
        checked = (
            self.data(index, Qt.ItemDataRole.CheckStateRole) == Qt.CheckState.Checked
        )
        return self.setData(
            index,
            Qt.CheckState.Unchecked if checked else Qt.CheckState.Checked,
            Qt.ItemDataRole.CheckStateRole,
        )

    def set_rows(
        self,
        rows: List[dict],
        selected_ids: Optional[AbstractSet[str]] = None,
    ) -> None:
        """Replace visible rows; selections of hidden rows are kept."""

        self.beginResetModel()
        self._rows = list(rows)
        self._row_index = {
            paper_id_for_row(row): idx for idx, row in enumerate(self._rows)
        }
        if selected_ids is not None:
            self._selected_ids = set(selected_ids)
        self.endResetModel()

    def rows(self) -> List[dict]:
        return list(self._rows)

    def set_sort_marker(self, column: Optional[int], order: Qt.SortOrder) -> None:
        self._sort_column = column
        self._sort_order = order
        self.headerDataChanged.emit(
            Qt.Orientation.Horizontal, PAPER_COLUMN, COLUMN_COUNT - 1
        )

    def row_for_paper(self, paper_id: str) -> int:
        return self._row_index.get(paper_id, -1)

    def refresh_icons(self) -> None:
        self._status_icons = {
            True: availability_icon(True),
            False: availability_icon(False),
        }

    def selected_ids(self) -> set[str]:
        return set(self._selected_ids)

    def visible_selected_count(self) -> int:
        return sum(1 for paper_id in self._row_index if paper_id in self._selected_ids)

    def set_selected_ids(self, selected_ids: AbstractSet[str]) -> None:
        old_ids = set(self._selected_ids)
        self._selected_ids = set(selected_ids)
        if self._rows:
            top_left = self.index(0, CHECK_COLUMN)
            bottom_right = self.index(len(self._rows) - 1, CHECK_COLUMN)
            self.dataChanged.emit(
                top_left, bottom_right, [Qt.ItemDataRole.CheckStateRole]
            )
        self.headerDataChanged.emit(
            Qt.Orientation.Horizontal, CHECK_COLUMN, CHECK_COLUMN
        )
        if old_ids != self._selected_ids:
            self.selection_changed.emit()

    def selection_state(self) -> Qt.CheckState:
        selected_visible = self.visible_selected_count()
        if not selected_visible:
            return Qt.CheckState.Unchecked
        if selected_visible == len(self._row_index):
            return Qt.CheckState.Checked
        return Qt.CheckState.PartiallyChecked

    def notify_rows_changed(self, paper_ids: AbstractSet[str]) -> None:
        roles = [
            Qt.ItemDataRole.DisplayRole,
            Qt.ItemDataRole.DecorationRole,
            Qt.ItemDataRole.ToolTipRole,
            Qt.ItemDataRole.AccessibleTextRole,
            Qt.ItemDataRole.CheckStateRole,
        ]
        rows = sorted(
            self._row_index[paper_id]
            for paper_id in paper_ids
            if paper_id in self._row_index
        )
        last_column = self.columnCount() - 1
        start = previous = None
        for row in rows + [None]:
            if start is not None and (row is None or row != previous + 1):
                self.dataChanged.emit(
                    self.index(start, 0), self.index(previous, last_column), roles
                )
                start = None
            if row is not None and start is None:
                start = row
            previous = row
