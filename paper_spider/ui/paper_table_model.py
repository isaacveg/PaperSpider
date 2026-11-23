# Copyright 2026 Isaacveg
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#     http://www.apache.org/licenses/LICENSE-2.0

from __future__ import annotations

from typing import AbstractSet, List, Optional

from PyQt6.QtCore import QAbstractTableModel, QModelIndex, Qt, pyqtSignal

from .i18n import tr
from .theme import availability_icon
from .workspace_view_helpers import paper_id_for_row, reconcile_selected_ids

CHECK_COLUMN = 0
PAPER_COLUMN = 1
ABSTRACT_COLUMN = 2
PDF_COLUMN = 3
COLUMN_COUNT = 4
AUTHORS_ROLE = Qt.ItemDataRole.UserRole + 1
HEADERS = ("", "Papers / authors", "Abstract", "PDF")


class PaperTableModel(QAbstractTableModel):
    selection_changed = pyqtSignal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._rows: List[dict] = []
        self._row_ids: set[str] = set()
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
            return tr(HEADERS[section]) if section else ""
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
            title = str(row.get("title") or "")
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
        if column == ABSTRACT_COLUMN:
            return bool(row.get("abstract_status") or row.get("abstract"))
        return bool(row.get("has_pdf"))

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

    def set_rows(
        self,
        rows: List[dict],
        selected_ids: Optional[AbstractSet[str]] = None,
    ) -> None:
        self.beginResetModel()
        self._rows = list(rows)
        self._row_ids = {paper_id_for_row(row) for row in self._rows}
        if selected_ids is not None:
            self._selected_ids = reconcile_selected_ids(rows, selected_ids)
        self.endResetModel()

    def rows(self) -> List[dict]:
        return list(self._rows)

    def refresh_icons(self) -> None:
        self._status_icons = {
            True: availability_icon(True),
            False: availability_icon(False),
        }

    def selected_ids(self) -> set[str]:
        return set(self._selected_ids)

    def set_selected_ids(self, selected_ids: AbstractSet[str]) -> None:
        old_ids = set(self._selected_ids)
        self._selected_ids = reconcile_selected_ids(self._rows, selected_ids)
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
        if not self._row_ids:
            return Qt.CheckState.Unchecked
        selected_visible = self._row_ids & self._selected_ids
        if not selected_visible:
            return Qt.CheckState.Unchecked
        if selected_visible == self._row_ids:
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
        for row_idx, row in enumerate(self._rows):
            if paper_id_for_row(row) in paper_ids:
                self.dataChanged.emit(
                    self.index(row_idx, 0),
                    self.index(row_idx, self.columnCount() - 1),
                    roles,
                )