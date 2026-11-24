from __future__ import annotations

import os
import tempfile
import unittest
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("PAPERSPIDER_LANG", "en")

from PyQt6.QtCore import QSettings, QSize, Qt
from PyQt6.QtGui import QGuiApplication, QKeySequence
from PyQt6.QtTest import QTest
from PyQt6.QtWidgets import (
    QApplication,
    QFrame,
    QHeaderView,
    QPushButton,
    QStyle,
    QStyleOptionComboBox,
    QTableView,
)

from paper_spider.storage import PaperStorage
from paper_spider.ui.dataset_dialog import SelectionResult
from paper_spider.ui.filter_dialog import FilterDialog, FilterRow
from paper_spider.ui.paper_table_model import (
    ABSTRACT_COLUMN,
    CHECK_COLUMN,
    PAPER_COLUMN,
    PDF_COLUMN,
)
from paper_spider.ui.workers import CancelToken
from paper_spider.ui.workspace_widgets import SIDEBAR_MIN_WIDTH, SIDEBAR_RAIL_WIDTH
from paper_spider.ui.table_delegates import CenteredStatusDelegate
from paper_spider.ui.workspace_window import WorkspaceWindow
from paper_spider.workspace_service import (
    DownloadBatchResult,
    DownloadFailure,
    PaperLoadResult,
)


_APPLICATION = QApplication.instance() or QApplication([])


def app() -> QApplication:
    return _APPLICATION


def required_combo_text_width(combo) -> int:
    option = QStyleOptionComboBox()
    option.initFrom(combo)
    option.currentText = combo.currentText()
    metrics = combo.fontMetrics()
    text_size = QSize(metrics.horizontalAdvance(option.currentText), metrics.height())
    return combo.style().sizeFromContents(
        QStyle.ContentsType.CT_ComboBox,
        option,
        text_size,
        combo,
    ).width()


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
        settings_path = os.path.join(self.temp_dir.name, "settings.ini")
        self.settings_patch = patch(
            "paper_spider.ui.workspace_window.app_settings",
            lambda: QSettings(settings_path, QSettings.Format.IniFormat),
        )
        self.settings_patch.start()
        self.storage = PaperStorage(self.temp_dir.name, "iclr", 2025)
        self.window = WorkspaceWindow(_FakeConference(), self.storage)

    def tearDown(self) -> None:
        self.window._download_tokens = dict.fromkeys(self.window._download_tokens)
        self.window.fetch_cancel_token = None
        self.window.thread_pool.waitForDone()
        self.app.processEvents()
        self.window.close()
        self.settings_patch.stop()
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

    def test_sidebar_button_toggles_between_expanded_and_rail(self) -> None:
        self.window.resize(1400, 800)
        self.window.show()
        self.app.processEvents()

        self.window.sidebar.collapse_btn.click()
        self.app.processEvents()
        self.assertEqual(SIDEBAR_RAIL_WIDTH, self.window.sidebar.width())
        self.assertTrue(self.window.sidebar.is_compact())
        self.assertFalse(self.window.sidebar.isHidden())

        self.window.sidebar.expand_btn.click()
        self.app.processEvents()
        self.assertEqual(280, self.window.sidebar.width())
        self.assertFalse(self.window.sidebar.is_compact())

    def test_reselecting_active_dataset_keeps_rows_and_selection(self) -> None:
        rows = self._show_rows()
        self.window._selected_paper_ids = {"p1"}
        self.window._start_worker = lambda *args, **kwargs: self.fail("unexpected reload")

        self.window._select_dataset("iclr", 2025, self.temp_dir.name)

        self.assertIs(rows, self.window._all_rows)
        self.assertEqual({"p1"}, self.window._selected_paper_ids)
        self.assertEqual(2, self.window.paper_model.rowCount())

    def test_details_panel_can_be_hidden_and_restored(self) -> None:
        self.window._hide_details()
        self.assertTrue(self.window.details_panel.isHidden())
        self.assertFalse(self.window.header.details_toggle_btn.isHidden())

        self.window._show_details()
        self.assertFalse(self.window.details_panel.isHidden())
        self.assertTrue(self.window.header.details_toggle_btn.isHidden())

    def test_open_dataset_folder_opens_the_dataset_directory(self) -> None:
        opened = []
        with patch(
            "paper_spider.ui.workspace_window.QDesktopServices.openUrl",
            side_effect=opened.append,
        ):
            self.window._open_dataset_folder("iclr", 2025)

        self.assertEqual(1, len(opened))
        self.assertEqual(
            os.path.join(self.temp_dir.name, "iclr", "2025"),
            opened[0].toLocalFile(),
        )

    def test_delete_active_dataset_moves_it_to_trash_and_clears_state(self) -> None:
        dataset_path = os.path.join(self.temp_dir.name, "iclr", "2025")
        self.assertTrue(os.path.isdir(dataset_path))

        with patch(
            "paper_spider.ui.workspace_window.ask_confirmation",
            return_value=True,
        ), patch("paper_spider.ui.workspace_window.show_information"):
            self.window._delete_dataset("iclr", 2025)

        self.assertFalse(os.path.exists(dataset_path))
        trash = os.path.join(self.temp_dir.name, ".trash")
        self.assertTrue(os.path.isdir(trash))
        self.assertTrue(os.listdir(trash))
        self.assertIsNone(self.window.storage)
        self.assertIsNone(self.window.conf)
        self.assertEqual(0, self.window.paper_model.rowCount())

    def test_sidebar_drag_snaps_to_rail_or_minimum_width(self) -> None:
        self.window.resize(1400, 800)
        self.window.show()
        self.app.processEvents()

        for dragged, expected, compact in (
            (120, SIDEBAR_RAIL_WIDTH, True),
            (170, SIDEBAR_MIN_WIDTH, False),
            (320, 320, False),
        ):
            with self.subTest(dragged=dragged):
                self.window.main_splitter.setSizes([dragged, 1400 - dragged])
                self.window._on_main_splitter_moved(dragged, 1)
                self.app.processEvents()
                self.assertEqual(expected, self.window.sidebar.width())
                self.assertEqual(compact, self.window.sidebar.is_compact())

        self.window.main_splitter.setSizes([120, 1280])
        self.window._on_main_splitter_moved(120, 1)
        self.app.processEvents()
        self.window.sidebar.expand_btn.click()
        self.app.processEvents()
        self.assertEqual(320, self.window.sidebar.width())

    def test_header_keeps_search_and_filter_on_the_title_row(self) -> None:
        self.assertIs(
            self.window.header.search_field.parentWidget(),
            self.window.header,
        )
        self.assertIs(
            self.window.header.filter_btn.parentWidget(),
            self.window.header,
        )

    def test_refresh_dataset_reuses_active_dataset_or_switches(self) -> None:
        self.window.thread_pool.waitForDone()
        self.app.processEvents()
        calls: list[str] = []
        self.window._fetch_list = lambda: calls.append("fetch")
        self.window._refresh_dataset("iclr", 2025)
        self.assertEqual(["fetch"], calls)

        calls.clear()
        self.window._select_dataset = (
            lambda conf, year, base_dir=None, load=True: calls.append(
                f"select:{conf}:{year}"
            )
        )
        self.window._refresh_dataset("osdi", 2024)
        self.assertEqual(["select:osdi:2024", "fetch"], calls)

    def test_paper_rows_use_compact_height(self) -> None:
        self.assertEqual(
            50, self.window.table.verticalHeader().defaultSectionSize()
        )

    def test_workspace_resizes_to_laptop_width_without_clipping_controls(self) -> None:
        self.window.thread_pool.waitForDone()
        self.app.processEvents()
        self.window.resize(1200, 720)
        self.window.show()
        self.app.processEvents()

        self.assertLessEqual(self.window.minimumSizeHint().width(), 1200)
        self.assertLessEqual(self.window.width(), 1200)
        self.assertEqual(280, self.window.sidebar.width())
        splitter_sizes = self.window.workspace_splitter.sizes()
        self.assertEqual(2, len(splitter_sizes))
        self.assertGreater(splitter_sizes[0], splitter_sizes[1])
        self.assertGreater(splitter_sizes[1], 0)

        action_bounds = self.window.action_bar.contentsRect()
        for button in (
            self.window.invert_btn,
            self.window.abstract_btn,
            self.window.pdf_btn,
            self.window.export_btn,
        ):
            top_left = button.mapTo(self.window.action_bar, button.rect().topLeft())
            bottom_right = button.mapTo(
                self.window.action_bar, button.rect().bottomRight()
            )
            self.assertGreaterEqual(top_left.x(), action_bounds.left())
            self.assertGreaterEqual(top_left.y(), action_bounds.top())
            self.assertLessEqual(bottom_right.x(), action_bounds.right())
            self.assertLessEqual(bottom_right.y(), action_bounds.bottom())

    def test_render_rows_keeps_artifact_actions_out_of_table(self) -> None:
        rows = self._rows()
        self.window._all_rows = rows
        self.window._filtered_rows = rows
        self.window._render_rows(rows)

        self.assertIs(self.window.table_stack.currentWidget(), self.window.table)
        self.assertIsInstance(self.window.table, QTableView)
        self.assertEqual(4, self.window.paper_model.columnCount())
        headers = [
            self.window.paper_model.headerData(index, Qt.Orientation.Horizontal)
            for index in range(self.window.paper_model.columnCount())
        ]
        self.assertEqual(
            ["", "Papers / authors", "Abstract", "PDF"], headers
        )
        self.assertEqual(
            "First Paper",
            self.window.paper_model.data(
                self.window.paper_model.index(0, PAPER_COLUMN),
                Qt.ItemDataRole.DisplayRole,
            ),
        )
        self.assertFalse(
            self.window.paper_model.data(
                self.window.paper_model.index(0, ABSTRACT_COLUMN),
                Qt.ItemDataRole.DecorationRole,
            ).isNull()
        )
        self.assertIn("2 papers", self.window.header.subtitle_label.text())
        self.assertEqual("0 selected", self.window.selected_label.text())

    def test_table_hides_implicit_vertical_header(self) -> None:
        self.assertTrue(self.window.table.verticalHeader().isHidden())

    def test_centered_paper_checkbox_remains_clickable(self) -> None:
        self.window.thread_pool.waitForDone()
        self.app.processEvents()
        self.window._render_rows(self._rows())
        self.window.show()
        self.app.processEvents()
        index = self.window.paper_model.index(0, CHECK_COLUMN)

        QTest.mouseClick(
            self.window.table.viewport(),
            Qt.MouseButton.LeftButton,
            pos=self.window.table.visualRect(index).center(),
        )

        self.assertEqual({"p1"}, self.window.paper_model.selected_ids())

    def test_table_gives_title_priority_over_authors(self) -> None:
        header = self.window.table.horizontalHeader()

        self.assertEqual(
            QHeaderView.ResizeMode.Stretch,
            header.sectionResizeMode(PAPER_COLUMN),
        )
        self.assertEqual(
            QHeaderView.ResizeMode.Fixed,
            header.sectionResizeMode(ABSTRACT_COLUMN),
        )
        self.assertEqual(
            QHeaderView.ResizeMode.Fixed,
            header.sectionResizeMode(PDF_COLUMN),
        )
        self.assertLessEqual(header.sectionSize(ABSTRACT_COLUMN), 58)
        self.assertLessEqual(header.sectionSize(PDF_COLUMN), 46)
        self.assertIsInstance(
            self.window.table.itemDelegateForColumn(ABSTRACT_COLUMN),
            CenteredStatusDelegate,
        )
        self.assertIsInstance(
            self.window.table.itemDelegateForColumn(PDF_COLUMN),
            CenteredStatusDelegate,
        )

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
                self.window.paper_model.index(0, PAPER_COLUMN),
                Qt.ItemDataRole.DisplayRole,
            ),
        )
        self.assertIn("1 match", self.window.header.subtitle_label.text())

    def test_empty_filter_result_does_not_fall_back_to_all_rows(self) -> None:
        rows = self._rows()
        self.window._all_rows = rows
        self.window._filtered_rows = []

        self.window._render_rows(self.window._quick_filtered_rows())

        self.assertEqual(0, self.window.paper_model.rowCount())
        self.assertIn("0 matches", self.window.header.subtitle_label.text())

    def test_quick_filter_is_debounced_and_precomputes_search_text(self) -> None:
        rows = self._rows()
        self.window._prepare_quick_search(rows)

        self.assertIn("_quick_search", rows[0])
        self.assertIs(
            self.window.quick_filter_edit.parentWidget(),
            self.window.header.search_field,
        )
        self.assertFalse(
            self.window.table.isAncestorOf(self.window.quick_filter_edit)
        )
        self.assertTrue(self.window.quick_filter_timer.isSingleShot())
        self.assertGreaterEqual(self.window.quick_filter_timer.interval(), 100)
        self.assertEqual(
            QKeySequence.SequenceMatch.ExactMatch,
            self.window.quick_filter_shortcut.key().matches(
                QKeySequence.StandardKey.Find
            ),
        )

    def test_select_and_download_controls_share_one_action_row(self) -> None:
        self.assertEqual("workspaceActionBar", self.window.action_bar.objectName())
        self.assertTrue(
            all(
                button.parentWidget() is self.window.action_bar
                for button in (
                    self.window.invert_btn,
                    self.window.abstract_btn,
                    self.window.pdf_btn,
                    self.window.export_btn,
                )
            )
        )
        self.assertLess(
            self.window.action_layout.indexOf(self.window.invert_btn),
            self.window.action_layout.indexOf(self.window.abstract_btn),
        )

    def test_select_header_toggles_visible_selection(self) -> None:
        rows = self._rows()
        self.window._all_rows = rows
        self.window._filtered_rows = rows
        self.window._render_rows(rows)

        self.window._toggle_header_selection(CHECK_COLUMN)
        self.assertEqual({"p1", "p2"}, self.window.paper_model.selected_ids())
        self.assertEqual(
            Qt.CheckState.Checked,
            self.window.paper_model.headerData(
                CHECK_COLUMN,
                Qt.Orientation.Horizontal,
                Qt.ItemDataRole.CheckStateRole,
            ),
        )

        self.window._toggle_header_selection(CHECK_COLUMN)
        self.assertEqual(set(), self.window.paper_model.selected_ids())

    def test_main_buttons_have_readable_theme_roles(self) -> None:
        self.assertEqual("linkButton", self.window.invert_btn.objectName())
        self.assertEqual("actionButton", self.window.abstract_btn.objectName())
        self.assertEqual("actionButton", self.window.pdf_btn.objectName())
        self.assertEqual("actionButton", self.window.export_btn.objectName())

    def test_dataset_dialog_fetch_intent_uses_existing_fetch_flow(self) -> None:
        calls: list[str] = []
        self.window._fetch_list = lambda: calls.append("fetch")
        self.window._load_papers = lambda force_refresh=False: calls.append(f"load:{force_refresh}")
        selection = SelectionResult(
            base_dir=self.temp_dir.name,
            conf_slug="iclr",
            year=2025,
            fetch_after_select=True,
        )

        with patch(
            "paper_spider.ui.workspace_window.DatasetDialog",
            lambda _parent, **_kwargs: _DialogResult(selection),
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
            conf_slug="osdi",
            year=2024,
            fetch_after_select=False,
        )

        with patch(
            "paper_spider.ui.workspace_window.DatasetDialog",
            lambda _parent, **_kwargs: _DialogResult(selection),
        ):
            self.window._open_dataset_dialog()

        self.assertEqual(["load:True"], calls)
        self.assertEqual("osdi", self.window.conf.slug)

    def test_settings_reapplies_theme_even_when_dialog_is_closed_without_accept(self) -> None:
        from PyQt6.QtWidgets import QDialog

        calls: list[str] = []

        with patch(
            "paper_spider.ui.workspace_window.SettingsDialog",
            lambda _parent: _SettingsDialogResult(QDialog.DialogCode.Rejected),
        ), patch("paper_spider.ui.workspace_window.apply_theme", lambda _window: calls.append("theme")):
            self.window._open_settings()

        self.assertEqual(["theme"], calls)

    def test_system_scheme_change_refreshes_theme_only_when_following_system(self) -> None:
        self.window.paper_model.set_rows(self._rows())

        with patch(
            "paper_spider.ui.workspace_window.selected_theme",
            return_value="Dark",
        ), patch(
            "paper_spider.ui.workspace_window.apply_theme"
        ) as apply_theme, patch.object(
            self.window.paper_model, "notify_rows_changed"
        ) as notify:
            self.window._on_color_scheme_changed()
            apply_theme.assert_not_called()
            notify.assert_not_called()

        with patch(
            "paper_spider.ui.workspace_window.selected_theme",
            return_value="System",
        ), patch(
            "paper_spider.ui.workspace_window.apply_theme"
        ) as apply_theme, patch.object(
            self.window.paper_model, "notify_rows_changed"
        ) as notify:
            self.window._on_color_scheme_changed()
            apply_theme.assert_called_once()
            notify.assert_called_once()
            self.assertEqual({"p1", "p2"}, notify.call_args.args[0])

    def test_child_widgets_do_not_override_window_stylesheet(self) -> None:
        self.assertEqual("", self.window.sidebar.styleSheet())
        self.assertEqual("", self.window.header.styleSheet())
        self.assertEqual("", self.window.details_panel.styleSheet())
        self.assertEqual("", self.window.action_bar.styleSheet())

    def test_filter_row_reads_as_a_single_compact_line(self) -> None:
        row = FilterRow()

        self.assertIsInstance(row, QFrame)
        self.assertEqual("filterRuleCard", row.objectName())
        layout = row.layout()
        self.assertEqual(6, layout.count())
        self.assertIs(layout.itemAt(0).widget(), row.enable_checkbox)
        self.assertIs(layout.itemAt(1).widget(), row.role_combo)
        self.assertIs(layout.itemAt(2).widget(), row.field_combo)
        self.assertIs(layout.itemAt(3).widget(), row.mode_combo)
        self.assertIs(layout.itemAt(4).widget(), row.text_edit)
        self.assertIs(layout.itemAt(5).widget(), row.remove_btn)
        self.assertEqual("×", row.remove_btn.text())
        self.assertLessEqual(row.role_combo.maximumWidth(), 104)

    def test_filter_row_preserves_full_mode_label_at_dialog_width(self) -> None:
        from paper_spider.ui.theme import appearance_from_values, build_stylesheet

        for theme in ("Light", "Dark"):
            with self.subTest(theme=theme):
                row = FilterRow()
                row.setStyleSheet(
                    build_stylesheet(appearance_from_values(theme, "Forest"))
                )
                row.mode_combo.setCurrentText("does not contain")
                row.resize(760, row.sizeHint().height())
                row.show()
                self.app.processEvents()

                self.assertEqual(760, row.width())
                self.assertEqual("Any field", row.field_combo.currentText())
                self.assertEqual("does not contain", row.mode_combo.currentText())
                for combo in (row.role_combo, row.field_combo, row.mode_combo):
                    self.assertGreaterEqual(
                        combo.width(), required_combo_text_width(combo)
                    )
                for control in (row.field_combo, row.mode_combo, row.text_edit):
                    right_edge = control.mapTo(row, control.rect().bottomRight()).x()
                    self.assertLessEqual(right_edge, row.contentsRect().right())

    def test_filter_row_roles_use_plain_language_with_legacy_config_values(self) -> None:
        row = FilterRow()

        self.assertEqual(
            ["Include", "Prefer", "Exclude"],
            [row.role_combo.itemText(index) for index in range(row.role_combo.count())],
        )
        self.assertEqual("Include", row.role_combo.currentText())
        for label, internal_value in (
            ("Include", "must"),
            ("Prefer", "should"),
            ("Exclude", "must not"),
        ):
            row.role_combo.setCurrentIndex(row.role_combo.findText(label))
            self.assertEqual(internal_value, row.config().role)

    def test_filter_dialog_has_one_add_rule_entry_and_defaults_to_include(self) -> None:
        dialog = FilterDialog()
        add_rule_buttons = [
            button
            for button in dialog.findChildren(QPushButton)
            if button.text() == "Add rule"
        ]

        self.assertEqual([dialog.add_filter_btn], add_rule_buttons)
        self.assertEqual(1, len(dialog._rows))
        self.assertEqual("Include", dialog._rows[0].role_combo.currentText())
        self.assertEqual("must", dialog._rows[0].config().role)
        self.assertIn("Include", dialog.hint_label.text())
        self.assertIn("Prefer", dialog.hint_label.text())
        self.assertIn("Exclude", dialog.hint_label.text())
        self.assertTrue(
            dialog.filter_layout.alignment() & Qt.AlignmentFlag.AlignTop
        )
        dialog.add_filter_btn.click()
        self.assertEqual(2, len(dialog._rows))
        self.assertEqual("Include", dialog._rows[-1].role_combo.currentText())
        self.assertEqual("must", dialog._rows[-1].config().role)

    def test_minimum_preferred_controls_require_an_active_valid_prefer_rule(self) -> None:
        dialog = FilterDialog()
        self.assertEqual("minPreferredRow", dialog.min_preferred_row.objectName())
        self.assertEqual(2, dialog.min_preferred_row.layout().count())
        self.assertEqual(
            "Minimum preferred matches", dialog.min_preferred_label.text()
        )
        self.assertTrue(dialog.min_preferred_row.isHidden())

        row = dialog._rows[0]
        row.role_combo.setCurrentIndex(row.role_combo.findText("Prefer"))
        self.assertTrue(dialog.min_preferred_row.isHidden())

        row.text_edit.setText("systems")
        self.assertFalse(dialog.min_preferred_row.isHidden())

        row.enable_checkbox.setChecked(False)
        self.assertTrue(dialog.min_preferred_row.isHidden())

    def test_empty_filter_copy_uses_prefer_language(self) -> None:
        self.window._all_rows = self._rows()
        self.window._current_rows = []

        self.window._update_empty_state()

        self.assertIn("minimum Prefer match count", self.window.empty_state.message_label.text())

    def test_selection_is_preserved_by_paper_id_after_rerender(self) -> None:
        rows = self._rows()
        self.window._all_rows = rows
        self.window._filtered_rows = rows
        self.window._render_rows(rows)
        self.window.paper_model.setData(
            self.window.paper_model.index(0, CHECK_COLUMN),
            Qt.CheckState.Checked,
            Qt.ItemDataRole.CheckStateRole,
        )

        self.window._render_rows([rows[0]])

        self.assertEqual(
            Qt.CheckState.Checked,
            self.window.paper_model.data(
                self.window.paper_model.index(0, CHECK_COLUMN),
                Qt.ItemDataRole.CheckStateRole,
            ),
        )
        self.assertEqual({"p1"}, self.window.paper_model.selected_ids())

    def _show_rows(self) -> list[dict]:
        self.window.thread_pool.waitForDone()
        self.app.processEvents()
        rows = self._rows()
        self.window._all_rows = rows
        self.window._filtered_rows = rows
        self.window._render_rows(rows)
        return rows

    def test_quick_filter_keeps_selections_hidden_from_current_list(self) -> None:
        self._show_rows()
        self.window.paper_model.setData(
            self.window.paper_model.index(0, CHECK_COLUMN),
            Qt.CheckState.Checked,
            Qt.ItemDataRole.CheckStateRole,
        )

        self.window.quick_filter_edit.setText("Bob")
        self.window._apply_quick_filter()

        self.assertEqual({"p1"}, self.window.paper_model.selected_ids())
        self.assertEqual("1 selected · 1 not shown", self.window.selected_label.text())
        self.assertEqual(["p1"], [row["paper_id"] for row in self.window._selected_rows()])

        self.window.quick_filter_edit.clear()
        self.window._apply_quick_filter()

        self.assertEqual(
            Qt.CheckState.Checked,
            self.window.paper_model.data(
                self.window.paper_model.index(0, CHECK_COLUMN),
                Qt.ItemDataRole.CheckStateRole,
            ),
        )
        self.assertEqual("1 selected", self.window.selected_label.text())

    def test_select_all_and_invert_only_affect_visible_rows(self) -> None:
        self._show_rows()
        self.window._selected_paper_ids = {"p1"}
        self.window.quick_filter_edit.setText("Bob")
        self.window._apply_quick_filter()

        self.window._set_selection_state(True)
        self.assertEqual({"p1", "p2"}, self.window._selected_paper_ids)

        self.window._invert_selection()
        self.assertEqual({"p1"}, self.window._selected_paper_ids)

    def test_reloading_from_storage_drops_selections_for_missing_papers(self) -> None:
        self._show_rows()
        self.window._selected_paper_ids = {"p1", "gone"}
        result = PaperLoadResult(
            storage_key=self.storage.paths.db_path,
            all_rows=self._rows(),
            filtered_rows=self._rows(),
        )

        self.window._on_load_papers_done(result)

        self.assertEqual({"p1"}, self.window._selected_paper_ids)

    def test_applying_cached_filters_is_synchronous(self) -> None:
        from paper_spider.filtering import FilterConfig

        self._show_rows()
        self.window._start_worker = lambda *args, **kwargs: self.fail("unexpected worker")
        self.window._applied_filters = [
            FilterConfig(True, "authors", "contains", "must", "bob")
        ]

        self.window._load_papers()

        self.assertTrue(self.window.table.isEnabled())
        self.assertEqual(["p2"], [row["paper_id"] for row in self.window._current_rows])

    def test_rerender_keeps_current_paper_focused(self) -> None:
        self._show_rows()
        self.window.table.setCurrentIndex(self.window.paper_model.index(1, 1))

        self.window.quick_filter_edit.setText("paper")
        self.window._apply_quick_filter()

        self.assertEqual(1, self.window.table.currentIndex().row())
        self.assertEqual("Second Paper", self.window.details_panel.title_label.text())

    def test_header_click_cycles_sort_order(self) -> None:
        self._show_rows()

        def titles() -> list[str]:
            return [row["title"] for row in self.window._current_rows]

        self.window._toggle_header_selection(PDF_COLUMN)
        self.assertEqual(["First Paper", "Second Paper"], titles())
        self.window._toggle_header_selection(PDF_COLUMN)
        self.assertEqual(["Second Paper", "First Paper"], titles())
        self.window._toggle_header_selection(PDF_COLUMN)
        self.assertIsNone(self.window._sort_column)
        self.window._toggle_header_selection(PAPER_COLUMN)
        self.window._toggle_header_selection(PAPER_COLUMN)
        self.assertEqual(["Second Paper", "First Paper"], titles())
        self.assertEqual(
            "Papers / authors ↓",
            self.window.paper_model.headerData(PAPER_COLUMN, Qt.Orientation.Horizontal),
        )
        self.assertEqual(
            "PDF", self.window.paper_model.headerData(PDF_COLUMN, Qt.Orientation.Horizontal)
        )

    def test_keyboard_space_toggles_row_and_select_all_checks_visible(self) -> None:
        self._show_rows()
        self.window.show()
        self.window.table.setFocus()
        self.window.table.setCurrentIndex(self.window.paper_model.index(1, PAPER_COLUMN))

        QTest.keyClick(self.window.table, Qt.Key.Key_Space)
        self.assertEqual({"p2"}, self.window._selected_paper_ids)

        QTest.keySequence(self.window.table, QKeySequence.StandardKey.SelectAll)
        self.assertEqual({"p1", "p2"}, self.window._selected_paper_ids)

    def test_enter_opens_current_pdf(self) -> None:
        self._show_rows()
        opened: list[str] = []
        self.window._open_file = opened.append
        self.window.show()
        self.window.table.setFocus()
        self.window.table.setCurrentIndex(self.window.paper_model.index(0, PAPER_COLUMN))

        QTest.keyClick(self.window.table, Qt.Key.Key_Return)

        self.assertEqual(["/tmp/first.pdf"], opened)

    def test_cancel_button_cancels_every_running_task(self) -> None:
        tokens = [CancelToken(), CancelToken(), CancelToken()]
        self.window.abstract_cancel_token = tokens[0]
        self.window.pdf_cancel_token = tokens[1]
        self.window.fetch_cancel_token = tokens[2]

        self.window.log_panel.cancel_btn.click()

        self.assertTrue(all(token.cancelled() for token in tokens))
        self.window.abstract_cancel_token = None
        self.window.pdf_cancel_token = None
        self.window.fetch_cancel_token = None

    def test_close_asks_before_cancelling_running_tasks(self) -> None:
        token = CancelToken()
        self.window.pdf_cancel_token = token

        with patch(
            "paper_spider.ui.workspace_window.ask_confirmation", return_value=False
        ) as ask:
            self.assertFalse(self.window.close())
        ask.assert_called_once()
        self.assertFalse(token.cancelled())

        with patch(
            "paper_spider.ui.workspace_window.ask_confirmation", return_value=True
        ):
            self.assertTrue(self.window.close())
        self.assertTrue(token.cancelled())
        self.window.pdf_cancel_token = None

    def test_download_result_is_reported_without_modal_dialog(self) -> None:
        self._show_rows()
        self.window.abstract_cancel_token = CancelToken()
        result = DownloadBatchResult(
            succeeded=1,
            failures=[DownloadFailure("p2", "Second Paper", "HTTP 404")],
        )

        with patch("paper_spider.ui.workspace_window.show_information") as info:
            self.window._on_download_done("abstracts", result)

        info.assert_not_called()
        self.assertIn("Failed 1", self.window.status_label.text())
        self.assertFalse(self.window.log_view.isHidden())
        self.assertIn("HTTP 404", self.window.log_view.toPlainText())

    def test_download_progress_signal_updates_progress_bar(self) -> None:
        self.window._download_tokens["pdfs"] = CancelToken()
        self.window._download_progress["pdfs"] = (0, 4)
        self.window._refresh_download_controls()

        self.window._on_download_progress("pdfs", 3, 4)

        self.assertEqual(3, self.window.log_panel.progress_bar.value())
        self.assertEqual("3 / 4", self.window.log_panel.progress_count_label.text())
        self.window._download_tokens["pdfs"] = None

    def test_session_state_round_trips_through_settings(self) -> None:
        from paper_spider.ui import workspace_window

        workspace_window.app_settings().setValue("base_dir", self.temp_dir.name)
        self.window.restore_session()
        self.window._hide_details()
        self.window.close()

        restored = WorkspaceWindow()
        try:
            restored.restore_session()
            self.assertEqual("iclr", restored.conf.slug)
            self.assertEqual(2025, restored.storage.year)
            self.assertTrue(restored.details_panel.isHidden())
        finally:
            restored.thread_pool.waitForDone()
            restored._persist_session = False
            restored.close()

    def test_current_row_updates_details_panel(self) -> None:
        rows = self._rows()
        self.window._all_rows = rows
        self.window._filtered_rows = rows
        self.window._render_rows(rows)

        self.window.table.setCurrentIndex(self.window.paper_model.index(0, 1))
        self.window._update_details()

        self.assertEqual("First Paper", self.window.details_panel.title_label.text())
        self.assertIn("Alice", self.window.details_panel.authors_label.text())
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
        fetched_bib_rows: list[dict] = []
        self.window._open_file = opened.append
        self.window._reveal_in_folder = revealed.append
        self.window._download_pdfs_for_rows = downloaded_pdf_rows.append
        self.window._fetch_bibtex_task = lambda row: (
            fetched_bib_rows.append(row)
            or {
                "bibtex": "@inproceedings{p2}",
                "paper_id": "p2",
                "bib_path": "/tmp/p2.bib",
                "db_path": self.window.storage.paths.db_path,
            }
        )
        self.window._start_worker = (
            lambda fn, on_done, on_error, *args: on_done(fn(*args))
        )

        self.window.table.setCurrentIndex(self.window.paper_model.index(0, 1))
        self.window._open_current_pdf()
        self.window._reveal_current_pdf()
        self.window._copy_current_bibtex()

        self.assertEqual(["/tmp/first.pdf"], opened)
        self.assertEqual(["/tmp/first.pdf"], revealed)
        self.assertEqual("@inproceedings{p1}", QGuiApplication.clipboard().text())

        self.window.table.setCurrentIndex(self.window.paper_model.index(1, 1))
        self.window._open_current_pdf()
        self.window._copy_current_bibtex()

        self.assertEqual([[rows[1]]], downloaded_pdf_rows)
        self.assertEqual([rows[1]], fetched_bib_rows)
        self.assertEqual("@inproceedings{p2}", QGuiApplication.clipboard().text())

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

        with patch("paper_spider.ui.workspace_window.show_information"):
            self.window._on_download_done("pdfs", result)

        self.assertEqual({"p2"}, self.window.paper_model.selected_ids())
        self.assertEqual("Second Paper", self.window.details_panel.title_label.text())
        self.assertIn("Now available", self.window.details_panel.abstract_text.toPlainText())

    def test_quick_filter_shortcut_focuses_search_box(self) -> None:
        self.window.quick_filter_edit.setText("Agent")
        self.window.quick_filter_edit.clearFocus()

        self.window._focus_quick_filter()

        self.assertTrue(self.window.quick_filter_edit.hasSelectedText())

    def test_filter_dialog_apply_reloads_papers_and_updates_chips(self) -> None:
        from PyQt6.QtWidgets import QDialog

        from paper_spider.filtering import FilterConfig

        calls: list[str] = []
        self.window._load_papers = lambda force_refresh=False: calls.append("apply")
        configs = [
            FilterConfig(True, "all", "contains", "must", "systems")
        ]

        with patch(
            "paper_spider.ui.workspace_window.FilterDialog"
        ) as dialog_class:
            dialog_class.return_value.exec.return_value = (
                QDialog.DialogCode.Accepted
            )
            dialog_class.return_value.filter_configs.return_value = configs
            dialog_class.return_value.min_should_match.return_value = 0
            self.window._open_filter_dialog()

        self.assertEqual(["apply"], calls)
        self.assertEqual(configs, self.window._applied_filters)
        self.assertIn("(1)", self.window.header.filter_btn.text())

    def test_finishing_one_download_keeps_cancel_control_visible(self) -> None:
        self.window.abstract_cancel_token = CancelToken()
        self.window.pdf_cancel_token = CancelToken()
        self.window._refresh_download_controls()

        self.assertFalse(self.window.log_panel.cancel_btn.isHidden())
        self.assertIn("abstracts", self.window.log_panel.status_label.text().lower())
        self.assertIn("PDF", self.window.log_panel.status_label.text())

        self.window.abstract_cancel_token = None
        self.window._refresh_download_controls()

        self.assertFalse(self.window.log_panel.cancel_btn.isHidden())
        self.assertIn("PDF", self.window.log_panel.status_label.text())

        self.window.pdf_cancel_token = None
        self.window._refresh_download_controls()
        self.assertTrue(self.window.log_panel.cancel_btn.isHidden())


if __name__ == "__main__":
    unittest.main()
