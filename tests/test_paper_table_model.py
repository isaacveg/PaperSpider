from __future__ import annotations

import os
import unittest
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("PAPERSPIDER_LANG", "en")

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QApplication

from paper_spider.ui.paper_table_model import (
    ABSTRACT_COLUMN,
    AUTHORS_ROLE,
    CHECK_COLUMN,
    PAPER_COLUMN,
    PDF_COLUMN,
    PaperTableModel,
)


_APPLICATION = QApplication.instance() or QApplication([])


def app() -> QApplication:
    return _APPLICATION


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

    def test_model_exposes_title_and_author_metadata(self) -> None:
        model = PaperTableModel()
        model.set_rows(self.rows, selected_ids={"p2"})

        self.assertEqual(4, model.rowCount())
        self.assertEqual(4, model.columnCount())
        self.assertEqual("", model.headerData(0, Qt.Orientation.Horizontal))
        self.assertEqual(
            "Papers / authors",
            model.headerData(PAPER_COLUMN, Qt.Orientation.Horizontal),
        )
        self.assertEqual(
            "Abstract",
            model.headerData(ABSTRACT_COLUMN, Qt.Orientation.Horizontal),
        )
        self.assertEqual(
            "PDF", model.headerData(PDF_COLUMN, Qt.Orientation.Horizontal)
        )
        self.assertEqual(
            "First Paper",
            model.data(model.index(0, PAPER_COLUMN), Qt.ItemDataRole.DisplayRole),
        )
        self.assertEqual(
            "Alice, Bob",
            model.data(model.index(0, PAPER_COLUMN), AUTHORS_ROLE),
        )
        self.assertEqual(
            "First Paper\nAlice, Bob",
            model.data(model.index(0, PAPER_COLUMN), Qt.ItemDataRole.ToolTipRole),
        )
        self.assertEqual(
            Qt.CheckState.Unchecked,
            model.data(model.index(0, CHECK_COLUMN), Qt.ItemDataRole.CheckStateRole),
        )
        self.assertEqual(
            Qt.CheckState.Checked,
            model.data(model.index(1, CHECK_COLUMN), Qt.ItemDataRole.CheckStateRole),
        )
        self.assertEqual(
            Qt.CheckState.PartiallyChecked,
            model.headerData(
                CHECK_COLUMN,
                Qt.Orientation.Horizontal,
                Qt.ItemDataRole.CheckStateRole,
            ),
        )

    def test_abstract_and_pdf_columns_expose_check_or_dash_icons(self) -> None:
        model = PaperTableModel()
        model.set_rows(self.rows, selected_ids=set())

        for row in range(model.rowCount()):
            for column in (ABSTRACT_COLUMN, PDF_COLUMN):
                decoration = model.data(
                    model.index(row, column), Qt.ItemDataRole.DecorationRole
                )
                self.assertIsInstance(decoration, QIcon)
                self.assertFalse(decoration.isNull())
                self.assertEqual(
                    "",
                    model.data(
                        model.index(row, column), Qt.ItemDataRole.DisplayRole
                    ),
                )

        self.assertEqual(
            "Abstract available",
            model.data(
                model.index(0, ABSTRACT_COLUMN),
                Qt.ItemDataRole.AccessibleTextRole,
            ),
        )
        self.assertEqual(
            "No PDF available",
            model.data(
                model.index(1, PDF_COLUMN), Qt.ItemDataRole.AccessibleTextRole
            ),
        )
        self.assertEqual(
            "No abstract available",
            model.data(
                model.index(3, ABSTRACT_COLUMN),
                Qt.ItemDataRole.ToolTipRole,
            ),
        )
        self.assertEqual(
            "PDF available",
            model.data(model.index(2, PDF_COLUMN), Qt.ItemDataRole.ToolTipRole),
        )

    def test_status_icons_are_cached_until_theme_refresh(self) -> None:
        model = PaperTableModel()
        model.set_rows(self.rows, selected_ids=set())

        with patch("paper_spider.ui.paper_table_model.availability_icon") as loader:
            for _ in range(20):
                model.data(
                    model.index(0, ABSTRACT_COLUMN),
                    Qt.ItemDataRole.DecorationRole,
                )
            loader.assert_not_called()

            model.refresh_icons()

            self.assertEqual(2, loader.call_count)

    def test_header_check_state_covers_unchecked_partial_and_checked(self) -> None:
        model = PaperTableModel()
        model.set_rows(self.rows[:2], selected_ids=set())

        self.assertEqual(
            Qt.CheckState.Unchecked,
            model.headerData(
                CHECK_COLUMN,
                Qt.Orientation.Horizontal,
                Qt.ItemDataRole.CheckStateRole,
            ),
        )

        model.set_selected_ids({"p1"})
        self.assertEqual(
            Qt.CheckState.PartiallyChecked,
            model.headerData(
                CHECK_COLUMN,
                Qt.Orientation.Horizontal,
                Qt.ItemDataRole.CheckStateRole,
            ),
        )

        model.set_selected_ids({"p1", "p2"})
        self.assertEqual(
            Qt.CheckState.Checked,
            model.headerData(
                CHECK_COLUMN,
                Qt.Orientation.Horizontal,
                Qt.ItemDataRole.CheckStateRole,
            ),
        )

    def test_model_updates_selected_ids_from_checkbox_state(self) -> None:
        model = PaperTableModel()
        model.set_rows(self.rows, selected_ids=set())

        self.assertTrue(
            model.setData(
                model.index(0, CHECK_COLUMN),
                Qt.CheckState.Checked.value,
                Qt.ItemDataRole.CheckStateRole,
            )
        )
        self.assertEqual({"p1"}, model.selected_ids())

        self.assertTrue(
            model.setData(
                model.index(0, CHECK_COLUMN),
                Qt.CheckState.Unchecked,
                Qt.ItemDataRole.CheckStateRole,
            )
        )
        self.assertEqual(set(), model.selected_ids())

    def test_column_alignment_keeps_titles_left_and_status_centered(self) -> None:
        model = PaperTableModel()
        model.set_rows(self.rows, selected_ids=set())

        self.assertEqual(
            Qt.AlignmentFlag.AlignCenter,
            model.data(
                model.index(0, CHECK_COLUMN), Qt.ItemDataRole.TextAlignmentRole
            ),
        )
        self.assertEqual(
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
            model.data(
                model.index(0, PAPER_COLUMN), Qt.ItemDataRole.TextAlignmentRole
            ),
        )
        self.assertEqual(
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
            model.headerData(
                PAPER_COLUMN,
                Qt.Orientation.Horizontal,
                Qt.ItemDataRole.TextAlignmentRole,
            ),
        )

    def test_model_reconciles_selection_against_visible_rows(self) -> None:
        model = PaperTableModel()
        model.set_rows([self.rows[0]], selected_ids={"p1", "p2"})

        self.assertEqual({"p1"}, model.selected_ids())
        self.assertEqual(
            Qt.CheckState.Checked,
            model.data(model.index(0, CHECK_COLUMN), Qt.ItemDataRole.CheckStateRole),
        )

    def test_model_notifies_status_updates_for_specific_papers(self) -> None:
        model = PaperTableModel()
        model.set_rows(self.rows, selected_ids=set())
        changed: list[tuple[int, int, list[int]]] = []
        model.dataChanged.connect(
            lambda top, bottom, roles: changed.append((top.row(), bottom.row(), roles))
        )

        model.notify_rows_changed({"p1"})

        self.assertEqual([(0, 0)], [(top, bottom) for top, bottom, _roles in changed])
        self.assertIn(Qt.ItemDataRole.AccessibleTextRole, changed[0][2])
        self.assertIn(Qt.ItemDataRole.DecorationRole, changed[0][2])


if __name__ == "__main__":
    unittest.main()