from __future__ import annotations

import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtCore import QSize, Qt
from PyQt6.QtGui import QIcon
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
            {
                "paper_id": "p3",
                "title": "Third Paper",
                "category_text": "workshop",
                "authors_text": "Dana",
                "abstract_status": 0,
                "abstract": "",
                "has_pdf": True,
            },
            {
                "paper_id": "p4",
                "title": "Fourth Paper",
                "category_text": "workshop",
                "authors_text": "Eve",
                "abstract_status": 0,
                "abstract": "",
                "has_pdf": False,
            },
        ]

    def test_model_exposes_metadata_without_creating_table_items(self) -> None:
        model = PaperTableModel()
        model.set_rows(self.rows, selected_ids={"p2"})

        self.assertEqual(4, model.rowCount())
        self.assertEqual(6, model.columnCount())
        self.assertEqual("#", model.headerData(0, Qt.Orientation.Horizontal))
        self.assertEqual("", model.headerData(1, Qt.Orientation.Horizontal))
        self.assertEqual("Title", model.headerData(2, Qt.Orientation.Horizontal))
        self.assertEqual("Status", model.headerData(5, Qt.Orientation.Horizontal))
        self.assertEqual("1", model.data(model.index(0, 0), Qt.ItemDataRole.DisplayRole))
        self.assertEqual("First Paper", model.data(model.index(0, 2), Qt.ItemDataRole.DisplayRole))
        self.assertEqual("main / conference", model.data(model.index(0, 3), Qt.ItemDataRole.DisplayRole))
        self.assertEqual("Alice, Bob", model.data(model.index(0, 4), Qt.ItemDataRole.DisplayRole))
        self.assertEqual(
            "Abstract, PDF",
            model.data(model.index(0, 5), Qt.ItemDataRole.ToolTipRole),
        )
        self.assertIsNone(model.data(model.index(0, 0), Qt.ItemDataRole.CheckStateRole))
        self.assertEqual(Qt.CheckState.Unchecked, model.data(model.index(0, 1), Qt.ItemDataRole.CheckStateRole))
        self.assertEqual(Qt.CheckState.Checked, model.data(model.index(1, 1), Qt.ItemDataRole.CheckStateRole))
        self.assertEqual(
            Qt.CheckState.PartiallyChecked,
            model.headerData(1, Qt.Orientation.Horizontal, Qt.ItemDataRole.CheckStateRole),
        )

    def test_status_display_uses_no_emoji(self) -> None:
        model = PaperTableModel()
        model.set_rows(self.rows, selected_ids=set())

        for row in range(model.rowCount()):
            status_text = model.data(
                model.index(row, 5),
                Qt.ItemDataRole.DisplayRole,
            )
            self.assertNotIn("💬", status_text)
            self.assertNotIn("📄", status_text)

    def test_status_decorations_and_tooltips_cover_every_availability_state(self) -> None:
        model = PaperTableModel()
        model.set_rows(self.rows, selected_ids=set())

        decorations = [
            model.data(model.index(row, 5), Qt.ItemDataRole.DecorationRole)
            for row in range(model.rowCount())
        ]

        self.assertTrue(all(isinstance(icon, QIcon) for icon in decorations[:3]))
        self.assertTrue(all(not icon.isNull() for icon in decorations[:3]))
        self.assertIsNone(decorations[3])
        self.assertNotEqual(decorations[1].cacheKey(), decorations[2].cacheKey())
        self.assertGreater(
            decorations[0].actualSize(QSize(64, 16)).width(),
            max(
                decorations[1].actualSize(QSize(64, 16)).width(),
                decorations[2].actualSize(QSize(64, 16)).width(),
            ),
        )
        self.assertEqual(
            ["Abstract, PDF", "Abstract", "PDF", ""],
            [
                model.data(model.index(row, 5), Qt.ItemDataRole.ToolTipRole)
                for row in range(model.rowCount())
            ],
        )

    def test_header_check_state_covers_unchecked_partial_and_checked(self) -> None:
        model = PaperTableModel()
        model.set_rows(self.rows[:2], selected_ids=set())

        self.assertEqual(
            Qt.CheckState.Unchecked,
            model.headerData(1, Qt.Orientation.Horizontal, Qt.ItemDataRole.CheckStateRole),
        )

        model.set_selected_ids({"p1"})
        self.assertEqual(
            Qt.CheckState.PartiallyChecked,
            model.headerData(1, Qt.Orientation.Horizontal, Qt.ItemDataRole.CheckStateRole),
        )

        model.set_selected_ids({"p1", "p2"})
        self.assertEqual(
            Qt.CheckState.Checked,
            model.headerData(1, Qt.Orientation.Horizontal, Qt.ItemDataRole.CheckStateRole),
        )

    def test_model_updates_selected_ids_from_checkbox_state(self) -> None:
        model = PaperTableModel()
        model.set_rows(self.rows, selected_ids=set())

        self.assertTrue(model.setData(model.index(0, 1), Qt.CheckState.Checked.value, Qt.ItemDataRole.CheckStateRole))
        self.assertEqual({"p1"}, model.selected_ids())

        self.assertTrue(model.setData(model.index(0, 1), Qt.CheckState.Unchecked, Qt.ItemDataRole.CheckStateRole))
        self.assertEqual(set(), model.selected_ids())

    def test_model_reconciles_selection_against_visible_rows(self) -> None:
        model = PaperTableModel()
        model.set_rows([self.rows[0]], selected_ids={"p1", "p2"})

        self.assertEqual({"p1"}, model.selected_ids())
        self.assertEqual(Qt.CheckState.Checked, model.data(model.index(0, 1), Qt.ItemDataRole.CheckStateRole))

    def test_model_notifies_status_updates_for_specific_papers(self) -> None:
        model = PaperTableModel()
        model.set_rows(self.rows, selected_ids=set())
        changed: list[tuple[int, int]] = []
        model.dataChanged.connect(lambda top, bottom, _roles: changed.append((top.row(), bottom.row())))

        model.notify_rows_changed({"p1"})

        self.assertEqual([(0, 0)], changed)


if __name__ == "__main__":
    unittest.main()
