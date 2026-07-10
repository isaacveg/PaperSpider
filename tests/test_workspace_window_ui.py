from __future__ import annotations

import os
import tempfile
import unittest
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QGuiApplication
from PyQt6.QtWidgets import QApplication, QFrame, QHeaderView, QPushButton, QScrollArea, QTableView

from paper_spider.storage import PaperStorage
from paper_spider.ui.dataset_dialog import SelectionResult
from paper_spider.ui.workers import CancelToken
from paper_spider.ui.workspace_window import FilterRow, WorkspaceWindow
from paper_spider.workspace_service import DownloadBatchResult


def app() -> QApplication:
    existing = QApplication.instance()
    if existing is not None:
        return existing
    return QApplication([])


class _FakeConference:
    name = "ICLR"
    slug = "iclr"


class _DialogResult:
    def __init__(self, selection: SelectionResult, code=None) -> None:
        self._selection = selection
        self._code = code

    def exec(self):
        from PyQt6.QtWidgets import QDialog

        return self._code or QDialog.DialogCode.Accepted

    def selection(self):
        return self._selection


class _SettingsDialogResult:
    def __init__(self, code) -> None:
        self._code = code

    def exec(self):
        return self._code

    def request_delay_ms(self) -> int:
        return 100


class WorkspaceWindowUiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.app = app()
        self.temp_dir = tempfile.TemporaryDirectory()
        self.storage = PaperStorage(self.temp_dir.name, "iclr", 2025)
        self.window = WorkspaceWindow(_FakeConference(), self.storage)

    def tearDown(self) -> None:
        self.window.close()
        self.temp_dir.cleanup()

    def _rows(self) -> list[dict]:
        return [
            {
                "paper_id": "p1",
                "title": "First Paper",
                "authors_text": "Alice",
                "category_text": "main / conference",
                "keywords_text": "systems",
                "abstract": "An abstract",
                "abstract_status": 1,
                "has_pdf": True,
                "pdf_status": 1,
                "pdf_path": "/tmp/first.pdf",
                "has_bib": True,
                "bibtex": "@inproceedings{p1}",
                "bib_path": "/tmp/first.bib",
            },
            {
                "paper_id": "p2",
                "title": "Second Paper",
                "authors_text": "Bob",
                "category_text": "main / conference",
                "keywords_text": "",
                "abstract": "",
                "abstract_status": 0,
                "has_pdf": False,
                "pdf_status": 0,
                "pdf_path": None,
                "has_bib": False,
                "bibtex": None,
                "bib_path": None,
            },
        ]

    def test_fresh_window_shows_fetch_empty_state_for_selected_dataset(self) -> None:
        self.assertIs(self.window.table_stack.currentWidget(), self.window.empty_state)
        self.assertIn("Fetch", self.window.empty_state.title_label.text())

    def test_workspace_window_uses_frameless_theme_aware_chrome(self) -> None:
        self.assertTrue(
            self.window.windowFlags() & Qt.WindowType.FramelessWindowHint
        )
        self.assertIsNotNone(self.window.top_bar.window_controls)

    def test_render_rows_keeps_artifact_actions_out_of_table(self) -> None:
        rows = self._rows()
        self.window._all_rows = rows
        self.window._filtered_rows = rows
        self.window._render_rows(rows)

        self.assertIs(self.window.table_stack.currentWidget(), self.window.table)
        self.assertIsInstance(self.window.table, QTableView)
        self.assertEqual(6, self.window.paper_model.columnCount())
        headers = [
            self.window.paper_model.headerData(index, Qt.Orientation.Horizontal)
            for index in range(self.window.paper_model.columnCount())
        ]
        self.assertEqual(["", "", "Title", "Category", "Authors", "Status"], headers)
        self.assertEqual(
            "1",
            self.window.paper_model.data(
                self.window.paper_model.index(0, 0),
                Qt.ItemDataRole.DisplayRole,
            ),
        )
        self.assertEqual(
            "First Paper",
            self.window.paper_model.data(
                self.window.paper_model.index(0, 2),
                Qt.ItemDataRole.DisplayRole,
            ),
        )
        self.assertEqual(
            "💬 📄",
            self.window.paper_model.data(
                self.window.paper_model.index(0, 5),
                Qt.ItemDataRole.DisplayRole,
            ),
        )
        self.assertEqual("2", self.window.summary_strip.total_value.text())
        self.assertEqual("1", self.window.summary_strip.pdfs_value.text())

    def test_table_gives_title_priority_over_authors(self) -> None:
        header = self.window.table.horizontalHeader()

        self.assertEqual(QHeaderView.ResizeMode.Stretch, header.sectionResizeMode(2))
        self.assertEqual(QHeaderView.ResizeMode.Fixed, header.sectionResizeMode(4))
        self.assertEqual(QHeaderView.ResizeMode.ResizeToContents, header.sectionResizeMode(5))
        self.assertLessEqual(self.window.table.columnWidth(4), 260)

    def test_quick_filter_searches_current_filtered_rows_and_updates_count(self) -> None:
        rows = self._rows()
        self.window._all_rows = rows
        self.window._filtered_rows = rows
        self.window._render_rows(rows)

        self.window.quick_filter_edit.setText("Bob")
        self.window._apply_quick_filter()

        self.assertEqual(1, self.window.paper_model.rowCount())
        self.assertEqual(
            "Second Paper",
            self.window.paper_model.data(
                self.window.paper_model.index(0, 2),
                Qt.ItemDataRole.DisplayRole,
            ),
        )
        self.assertEqual("1", self.window.summary_strip.filtered_value.text())

    def test_empty_filter_result_does_not_fall_back_to_all_rows(self) -> None:
        rows = self._rows()
        self.window._all_rows = rows
        self.window._filtered_rows = []

        self.window._render_rows(self.window._quick_filtered_rows())

        self.assertEqual(0, self.window.paper_model.rowCount())
        self.assertEqual("0", self.window.summary_strip.filtered_value.text())

    def test_quick_filter_is_debounced_and_precomputes_search_text(self) -> None:
        rows = self._rows()
        self.window._prepare_quick_search(rows)

        self.assertIn("_quick_search", rows[0])
        self.assertTrue(self.window.quick_filter_timer.isSingleShot())
        self.assertGreaterEqual(self.window.quick_filter_timer.interval(), 100)

    def test_select_controls_move_below_table_before_download_actions(self) -> None:
        summary_buttons = self.window.summary_strip.findChildren(QPushButton)

        self.assertEqual([], summary_buttons)
        self.assertIs(self.window.invert_btn.parent(), self.window.selection_controls)
        self.assertEqual(
            ["Invert"],
            [button.text() for button in self.window.selection_controls.findChildren(QPushButton)],
        )
        self.assertLess(
            self.window.action_layout.indexOf(self.window.selection_controls),
            self.window.action_layout.indexOf(self.window.abstract_btn),
        )

    def test_select_header_toggles_visible_selection(self) -> None:
        rows = self._rows()
        self.window._all_rows = rows
        self.window._filtered_rows = rows
        self.window._render_rows(rows)

        self.window._toggle_header_selection(1)
        self.assertEqual({"p1", "p2"}, self.window.paper_model.selected_ids())
        self.assertEqual(
            Qt.CheckState.Checked,
            self.window.paper_model.headerData(
                1,
                Qt.Orientation.Horizontal,
                Qt.ItemDataRole.CheckStateRole,
            ),
        )

        self.window._toggle_header_selection(1)
        self.assertEqual(set(), self.window.paper_model.selected_ids())

    def test_main_buttons_have_readable_theme_roles(self) -> None:
        secondary_buttons = [
            self.window.invert_btn,
            self.window.abstract_btn,
            self.window.bib_btn,
        ]

        self.assertTrue(
            all(button.objectName() == "secondaryButton" for button in secondary_buttons)
        )
        self.assertEqual("primaryButton", self.window.pdf_btn.objectName())
        self.assertEqual("primaryButton", self.window.export_btn.objectName())
        self.assertNotIn("#edf2f7", self.window.selection_controls.styleSheet().lower())

    def test_dataset_dialog_fetch_intent_uses_existing_fetch_flow(self) -> None:
        calls: list[str] = []
        self.window._fetch_list = lambda: calls.append("fetch")
        self.window._load_papers = lambda force_refresh=False: calls.append(f"load:{force_refresh}")
        selection = SelectionResult(
            base_dir=self.temp_dir.name,
            conf_slug="iclr",
            year=2025,
            request_delay_ms=100,
            fetch_after_select=True,
        )

        with patch(
            "paper_spider.ui.workspace_window.DatasetDialog",
            lambda _parent: _DialogResult(selection),
        ):
            self.window._open_dataset_dialog()

        self.assertEqual(["fetch"], calls)
        self.assertEqual("iclr", self.window.conf.slug)
        self.assertEqual(2025, self.window.storage.year)

    def test_dataset_dialog_plain_selection_loads_papers_without_fetching(self) -> None:
        calls: list[str] = []
        self.window._fetch_list = lambda: calls.append("fetch")
        self.window._load_papers = lambda force_refresh=False: calls.append(f"load:{force_refresh}")
        selection = SelectionResult(
            base_dir=self.temp_dir.name,
            conf_slug="iclr",
            year=2025,
            request_delay_ms=100,
            fetch_after_select=False,
        )

        with patch(
            "paper_spider.ui.workspace_window.DatasetDialog",
            lambda _parent: _DialogResult(selection),
        ):
            self.window._open_dataset_dialog()

        self.assertEqual(["load:True"], calls)

    def test_settings_reapplies_theme_even_when_dialog_is_closed_without_accept(self) -> None:
        from PyQt6.QtWidgets import QDialog

        calls: list[str] = []

        with patch(
            "paper_spider.ui.workspace_window.SettingsDialog",
            lambda _parent: _SettingsDialogResult(QDialog.DialogCode.Rejected),
        ), patch("paper_spider.ui.workspace_window.apply_theme", lambda _window: calls.append("theme")):
            self.window._open_settings()

        self.assertEqual(["theme"], calls)

    def test_dark_theme_not_overridden_by_light_child_stylesheets(self) -> None:
        from paper_spider.ui.theme import Appearance, build_stylesheet

        dark = Appearance(
            theme="Dark",
            accent="Blue",
            accent_color="#0b6bff",
            background="#111827",
            surface="#1f2937",
            surface_alt="#273244",
            border="#374151",
            text="#f9fafb",
            muted="#cbd5e1",
        )

        self.assertNotIn("#ffffff", self.window.filter_rows[0].styleSheet().lower())
        self.assertNotIn("#f7f8fa", self.window.findChild(QFrame, "filterSidebar").styleSheet().lower())
        self.assertNotIn("#fbfcfd", self.window.details_panel.styleSheet().lower())
        self.assertNotIn("#edf2f7", self.window.selection_controls.styleSheet().lower())
        self.assertIn("#1f2937", build_stylesheet(dark).lower())

    def test_filter_row_is_two_line_card(self) -> None:
        row = FilterRow()

        self.assertIsInstance(row, QFrame)
        self.assertEqual("filterRuleCard", row.objectName())
        self.assertEqual(2, row.layout().count())
        self.assertIs(row.layout().itemAt(1).widget(), row.text_row)
        self.assertEqual("x", row.remove_btn.text())
        self.assertLess(row.text_row.layout().indexOf(row.text_edit), row.text_row.layout().indexOf(row.remove_btn))

    def test_filter_row_first_line_uses_adaptive_widths(self) -> None:
        row = FilterRow()
        control_layout = row.control_row.layout()

        self.assertGreaterEqual(row.role_combo.minimumWidth(), 100)
        self.assertGreaterEqual(row.field_combo.minimumWidth(), 96)
        self.assertGreaterEqual(row.mode_combo.minimumWidth(), 100)
        self.assertGreater(row.role_combo.maximumWidth(), row.role_combo.minimumWidth())
        self.assertGreater(row.field_combo.maximumWidth(), row.field_combo.minimumWidth())
        self.assertGreater(row.mode_combo.maximumWidth(), row.mode_combo.minimumWidth())
        self.assertGreater(control_layout.stretch(control_layout.indexOf(row.role_combo)), 0)
        self.assertGreater(control_layout.stretch(control_layout.indexOf(row.field_combo)), 0)
        self.assertGreater(control_layout.stretch(control_layout.indexOf(row.mode_combo)), 0)

    def test_filter_sidebar_add_buttons_are_explicit_and_rows_start_at_top(self) -> None:
        labels = {
            button.text()
            for button in self.window.findChildren(QPushButton)
            if button.text().startswith("+")
        }

        self.assertIn("+Must", labels)
        self.assertIn("+Should", labels)
        self.assertIn("+Not", labels)
        self.assertTrue(self.window.filter_layout.alignment() & Qt.AlignmentFlag.AlignTop)

    def test_filter_sidebar_scrolls_and_minimum_should_is_single_line(self) -> None:
        self.assertIsInstance(self.window.filter_scroll, QScrollArea)
        self.assertEqual("minShouldRow", self.window.min_should_row.objectName())
        self.assertEqual(2, self.window.min_should_row.layout().count())

    def test_selection_is_preserved_by_paper_id_after_rerender(self) -> None:
        rows = self._rows()
        self.window._all_rows = rows
        self.window._filtered_rows = rows
        self.window._render_rows(rows)
        self.window.paper_model.setData(
            self.window.paper_model.index(0, 1),
            Qt.CheckState.Checked,
            Qt.ItemDataRole.CheckStateRole,
        )
        self.window._capture_selected_ids()

        self.window._render_rows([rows[0]])

        self.assertEqual(
            Qt.CheckState.Checked,
            self.window.paper_model.data(
                self.window.paper_model.index(0, 1),
                Qt.ItemDataRole.CheckStateRole,
            ),
        )
        self.assertEqual({"p1"}, self.window.paper_model.selected_ids())

    def test_quick_filter_clears_selections_hidden_from_current_list(self) -> None:
        rows = self._rows()
        self.window._all_rows = rows
        self.window._filtered_rows = rows
        self.window._render_rows(rows)
        self.window.paper_model.setData(
            self.window.paper_model.index(0, 1),
            Qt.CheckState.Checked,
            Qt.ItemDataRole.CheckStateRole,
        )

        self.window.quick_filter_edit.setText("Bob")
        self.window._apply_quick_filter()
        self.window.quick_filter_edit.clear()
        self.window._apply_quick_filter()

        self.assertEqual(set(), self.window.paper_model.selected_ids())
        self.assertEqual(
            Qt.CheckState.Unchecked,
            self.window.paper_model.data(
                self.window.paper_model.index(0, 1),
                Qt.ItemDataRole.CheckStateRole,
            ),
        )

    def test_current_row_updates_details_panel(self) -> None:
        rows = self._rows()
        self.window._all_rows = rows
        self.window._filtered_rows = rows
        self.window._render_rows(rows)

        self.window.table.setCurrentIndex(self.window.paper_model.index(0, 1))
        self.window._update_details()

        self.assertEqual("First Paper", self.window.details_panel.title_label.text())
        self.assertIn("Alice", self.window.details_panel.meta_label.text())
        self.assertIn("An abstract", self.window.details_panel.abstract_text.toPlainText())

    def test_existing_abstract_action_copies_to_clipboard(self) -> None:
        rows = self._rows()
        self.window._all_rows = rows
        self.window._filtered_rows = rows
        self.window._render_rows(rows)
        self.window.table.setCurrentIndex(self.window.paper_model.index(0, 1))

        self.window._download_current_abstract()

        self.assertEqual("An abstract", QGuiApplication.clipboard().text())
        self.assertIn("copied", self.window.details_panel.feedback_label.text())

    def test_details_panel_pdf_and_bib_actions_replace_table_artifact_columns(self) -> None:
        rows = self._rows()
        self.window._all_rows = rows
        self.window._filtered_rows = rows
        self.window._render_rows(rows)

        opened: list[str] = []
        revealed: list[str] = []
        downloaded_pdf_rows: list[list[dict]] = []
        exported_bib_rows: list[list[dict]] = []
        self.window._open_file = opened.append
        self.window._reveal_in_folder = revealed.append
        self.window._download_pdfs_for_rows = downloaded_pdf_rows.append
        self.window._export_bibtex_for_rows = exported_bib_rows.append

        self.window.table.setCurrentIndex(self.window.paper_model.index(0, 1))
        self.window._open_current_pdf()
        self.window._reveal_current_pdf()
        self.window._copy_current_bibtex()
        self.window._reveal_current_bib()

        self.assertEqual(["/tmp/first.pdf"], opened)
        self.assertEqual(["/tmp/first.pdf", "/tmp/first.bib"], revealed)
        self.assertEqual("@inproceedings{p1}", QGuiApplication.clipboard().text())

        self.window.table.setCurrentIndex(self.window.paper_model.index(1, 1))
        self.window._open_current_pdf()
        self.window._copy_current_bibtex()

        self.assertEqual([[rows[1]]], downloaded_pdf_rows)
        self.assertEqual([[rows[1]]], exported_bib_rows)

    def test_double_clicking_row_with_pdf_opens_pdf_file(self) -> None:
        rows = self._rows()
        self.window._all_rows = rows
        self.window._filtered_rows = rows
        self.window._render_rows(rows)
        opened: list[str] = []
        self.window._open_file = opened.append

        self.window._on_table_double_clicked(self.window.paper_model.index(0, 1))

        self.assertEqual(["/tmp/first.pdf"], opened)

    def test_download_completion_patches_rows_without_reloading_whole_table(self) -> None:
        rows = self._rows()
        self.window._all_rows = rows
        self.window._filtered_rows = rows
        self.window._render_rows(rows)
        self.window.table.setCurrentIndex(self.window.paper_model.index(1, 1))
        self.window._selected_paper_ids = {"p2"}
        self.window.pdf_cancel_token = CancelToken()
        self.window._load_papers = lambda force_refresh=False: self.fail("unexpected full reload")
        result = DownloadBatchResult(
            succeeded=1,
            updated_rows=[
                {
                    **rows[1],
                    "abstract": "Now available",
                    "abstract_status": 1,
                    "has_pdf": True,
                    "pdf_status": 1,
                    "pdf_path": "/tmp/second.pdf",
                }
            ],
        )

        with patch("paper_spider.ui.workspace_window.QMessageBox.information"):
            self.window._on_pdfs_done(result)

        self.assertEqual({"p2"}, self.window.paper_model.selected_ids())
        self.assertEqual("Second Paper", self.window.details_panel.title_label.text())
        self.assertIn("Now available", self.window.details_panel.abstract_text.toPlainText())

    def test_quick_filter_shortcut_focuses_search_box(self) -> None:
        self.window.quick_filter_edit.setText("Agent")
        self.window.quick_filter_edit.clearFocus()

        self.window._focus_quick_filter()

        self.assertTrue(self.window.quick_filter_edit.hasSelectedText())

    def test_filter_keyword_return_applies_filters(self) -> None:
        calls: list[str] = []
        self.window._load_papers = lambda force_refresh=False: calls.append("apply")

        self.window.filter_rows[0].text_edit.returnPressed.emit()

        self.assertEqual(["apply"], calls)

    def test_finishing_one_download_keeps_other_cancel_control_visible(self) -> None:
        self.window.abstract_cancel_token = CancelToken()
        self.window.pdf_cancel_token = CancelToken()
        self.window._refresh_download_controls()

        self.assertFalse(self.window.log_panel.cancel_abstracts_btn.isHidden())
        self.assertFalse(self.window.log_panel.cancel_pdfs_btn.isHidden())

        self.window.abstract_cancel_token = None
        self.window._refresh_download_controls()

        self.assertTrue(self.window.log_panel.cancel_abstracts_btn.isHidden())
        self.assertFalse(self.window.log_panel.cancel_pdfs_btn.isHidden())
        self.assertIn("PDF", self.window.log_panel.status_label.text())


if __name__ == "__main__":
    unittest.main()
