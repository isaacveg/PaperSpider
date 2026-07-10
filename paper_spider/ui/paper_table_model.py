# Copyright 2026 Isaacveg
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#     http://www.apache.org/licenses/LICENSE-2.0

from __future__ import annotations

from typing import AbstractSet, List, Optional

from PyQt6.QtCore import QAbstractTableModel, QModelIndex, Qt, pyqtSignal

from .theme import status_icon
from .workspace_view_helpers import paper_id_for_row, reconcile_selected_ids


class PaperTableModel(QAbstractTableModel):
    selection_changed = pyqtSignal()

    HEADERS = ["#", "", "Title", "Category", "Authors", "Status"]

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._rows: List[dict] = []
        self._selected_ids: set[str] = set()

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        if parent.isValid():
            return 0
        return len(self._rows)

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:
        if parent.isValid():
            return 0
        return len(self.HEADERS)

    def headerData(
        self,
        section: int,
        orientation: Qt.Orientation,
        role: int = Qt.ItemDataRole.DisplayRole,
    ):
        if orientation != Qt.Orientation.Horizontal or not 0 <= section < len(self.HEADERS):
            return None
        if role == Qt.ItemDataRole.DisplayRole:
            return self.HEADERS[section]
        if section == 1 and role == Qt.ItemDataRole.CheckStateRole:
            return self.selection_state()
        return None

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole):
        if not index.isValid() or index.row() >= len(self._rows):
            return None
        row = self._rows[index.row()]
        column = index.column()
        if role == Qt.ItemDataRole.CheckStateRole and column == 1:
            return (
                Qt.CheckState.Checked
                if paper_id_for_row(row) in self._selected_ids
                else Qt.CheckState.Unchecked
            )
        if role == Qt.ItemDataRole.TextAlignmentRole and column in (0, 5):
            return Qt.AlignmentFlag.AlignCenter
        if role == Qt.ItemDataRole.ToolTipRole and column == 5:
            return self._status_tooltip(row)
        if role == Qt.ItemDataRole.DecorationRole and column == 5:
            kinds = self._status_kinds(row)
            return status_icon(kinds) if kinds else None
        if role != Qt.ItemDataRole.DisplayRole:
            return None
        if column == 0:
            return str(index.row() + 1)
        if column == 2:
            return row.get("title") or ""
        if column == 3:
            return row.get("category_text") or ""
        if column == 4:
            return row.get("authors_text") or ""
        if column == 5:
            return ""
        return ""

    def _status_kinds(self, row: dict) -> tuple[str, ...]:
        kinds = []
        if row.get("abstract_status") or row.get("abstract"):
            kinds.append("abstract")
        if row.get("has_pdf"):
            kinds.append("pdf")
        return tuple(kinds)

    def _status_tooltip(self, row: dict) -> str:
        labels = {"abstract": "Abstract", "pdf": "PDF"}
        return ", ".join(labels[kind] for kind in self._status_kinds(row))

    def flags(self, index: QModelIndex) -> Qt.ItemFlag:
        if not index.isValid():
            return Qt.ItemFlag.NoItemFlags
        flags = Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable
        if index.column() == 1:
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
            or index.column() != 1
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
        self.headerDataChanged.emit(Qt.Orientation.Horizontal, 1, 1)
        self.selection_changed.emit()
        return True

    def set_rows(
        self,
        rows: List[dict],
        selected_ids: Optional[AbstractSet[str]] = None,
    ) -> None:
        self.beginResetModel()
        self._rows = list(rows)
        if selected_ids is not None:
            self._selected_ids = reconcile_selected_ids(rows, selected_ids)
        self.endResetModel()

    def row_at(self, row_idx: int) -> Optional[dict]:
        if 0 <= row_idx < len(self._rows):
            return self._rows[row_idx]
        return None

    def rows(self) -> List[dict]:
        return list(self._rows)

    def selected_ids(self) -> set[str]:
        return set(self._selected_ids)

    def set_selected_ids(self, selected_ids: AbstractSet[str]) -> None:
        old_ids = set(self._selected_ids)
        self._selected_ids = reconcile_selected_ids(self._rows, selected_ids)
        if self._rows:
            top_left = self.index(0, 1)
            bottom_right = self.index(len(self._rows) - 1, 1)
            self.dataChanged.emit(top_left, bottom_right, [Qt.ItemDataRole.CheckStateRole])
        self.headerDataChanged.emit(Qt.Orientation.Horizontal, 1, 1)
        if old_ids != self._selected_ids:
            self.selection_changed.emit()

    def selection_state(self) -> Qt.CheckState:
        if not self._rows:
            return Qt.CheckState.Unchecked
        visible_ids = {paper_id_for_row(row) for row in self._rows}
        selected_visible = visible_ids & self._selected_ids
        if not selected_visible:
            return Qt.CheckState.Unchecked
        if selected_visible == visible_ids:
            return Qt.CheckState.Checked
        return Qt.CheckState.PartiallyChecked

    def notify_rows_changed(self, paper_ids: AbstractSet[str]) -> None:
        roles = [
            Qt.ItemDataRole.DisplayRole,
            Qt.ItemDataRole.DecorationRole,
            Qt.ItemDataRole.ToolTipRole,
            Qt.ItemDataRole.CheckStateRole,
        ]
        for row_idx, row in enumerate(self._rows):
            if paper_id_for_row(row) in paper_ids:
                self.dataChanged.emit(
                    self.index(row_idx, 0),
                    self.index(row_idx, self.columnCount() - 1),
                    roles,
                )
