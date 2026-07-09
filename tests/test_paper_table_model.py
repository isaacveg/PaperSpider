from __future__ import annotations

import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication

from paper_spider.ui.paper_table_model import PaperTableModel


def app() -> QApplication:
    existing = QApplication.instance()
    if existing is not None:
        return existing
    return QApplication([])


class PaperTableModelTests(unittest.TestCase):
    def setUp(self) -> None:
        self.app = app()
        self.rows = [
            {
                "paper_id": "p1",
                "title": "First Paper",
                "category_text": "main / conference",
                "authors_text": "Alice, Bob",
                "abstract_status": 1,
                "has_pdf": True,
            },
            {
                "paper_id": "p2",
                "title": "Second Paper",
                "category_text": "workshop",
                "authors_text": "Carol",
                "abstract_status": 1,
                "has_pdf": False,
            },
        ]

    def test_model_exposes_metadata_without_creating_table_items(self) -> None:
        model = PaperTableModel()
        model.set_rows(self.rows, selected_ids={"p2"})

        self.assertEqual(2, model.rowCount())
        self.assertEqual(5, model.columnCount())
        self.assertEqual("Select", model.headerData(0, Qt.Orientation.Horizontal))
        self.assertEqual("Title", model.headerData(1, Qt.Orientation.Horizontal))
        self.assertEqual("Status", model.headerData(4, Qt.Orientation.Horizontal))
        self.assertEqual("First Paper", model.data(model.index(0, 1), Qt.ItemDataRole.DisplayRole))
        self.assertEqual("main / conference", model.data(model.index(0, 2), Qt.ItemDataRole.DisplayRole))
        self.assertEqual("Alice, Bob", model.data(model.index(0, 3), Qt.ItemDataRole.DisplayRole))
        self.assertEqual("PDF", model.data(model.index(0, 4), Qt.ItemDataRole.DisplayRole))
        self.assertEqual("Abstract", model.data(model.index(1, 4), Qt.ItemDataRole.DisplayRole))
        self.assertEqual(Qt.CheckState.Unchecked, model.data(model.index(0, 0), Qt.ItemDataRole.CheckStateRole))
        self.assertEqual(Qt.CheckState.Checked, model.data(model.index(1, 0), Qt.ItemDataRole.CheckStateRole))

    def test_model_updates_selected_ids_from_checkbox_state(self) -> None:
        model = PaperTableModel()
        model.set_rows(self.rows, selected_ids=set())

        self.assertTrue(model.setData(model.index(0, 0), Qt.CheckState.Checked.value, Qt.ItemDataRole.CheckStateRole))
        self.assertEqual({"p1"}, model.selected_ids())

        self.assertTrue(model.setData(model.index(0, 0), Qt.CheckState.Unchecked, Qt.ItemDataRole.CheckStateRole))
        self.assertEqual(set(), model.selected_ids())

    def test_model_reconciles_selection_against_visible_rows(self) -> None:
        model = PaperTableModel()
        model.set_rows([self.rows[0]], selected_ids={"p1", "p2"})

        self.assertEqual({"p1"}, model.selected_ids())
        self.assertEqual(Qt.CheckState.Checked, model.data(model.index(0, 0), Qt.ItemDataRole.CheckStateRole))


if __name__ == "__main__":
    unittest.main()
