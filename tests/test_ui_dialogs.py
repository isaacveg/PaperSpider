from __future__ import annotations

import os
import tempfile
import unittest
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtCore import Qt
from PyQt6.QtTest import QTest
from PyQt6.QtWidgets import (
    QApplication,
    QComboBox,
    QDialog,
    QGroupBox,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QWidget,
)

from paper_spider.ui.dataset_dialog import (
    CONFERENCE_TEXT_INSET,
    DatasetConferenceDelegate,
    DatasetDialog,
    DatasetEntry,
)
from paper_spider.ui.export_dialog import ExportDialog
from paper_spider.ui.settings_dialog import SettingsDialog


_APPLICATION = QApplication.instance() or QApplication([])


def app() -> QApplication:
    return _APPLICATION


class FakeSettings:
    def __init__(self, *args, **kwargs) -> None:
        self.values: dict[str, object] = {}

    def value(self, key: str, default=None):
        return self.values.get(key, default)

    def setValue(self, key: str, value) -> None:
        self.values[key] = value


class SharedFakeSettings:
    values: dict[str, object] = {}

    def __init__(self, *args, **kwargs) -> None:
        pass

    def value(self, key: str, default=None):
        return self.values.get(key, default)

    def setValue(self, key: str, value) -> None:
        self.values[key] = value


class SettingsDialogTests(unittest.TestCase):
    def setUp(self) -> None:
        self.app = app()

    def test_settings_uses_grouped_sections(self) -> None:
        with patch("paper_spider.ui.settings_dialog.QSettings", FakeSettings):
            dialog = SettingsDialog()

        self.assertEqual("PaperSpider - Settings", dialog.windowTitle())
        self.assertEqual((640, 440), (dialog.minimumWidth(), dialog.minimumHeight()))
        self.assertEqual((720, 520), (dialog.width(), dialog.height()))
        self.assertEqual([], dialog.findChildren(QGroupBox))
        section_titles = {
            label.text()
            for label in dialog.findChildren(QLabel)
            if label.objectName() == "settingsCardTitle"
        }
        self.assertIn("Request Interval", section_titles)
        self.assertIn("Appearance", section_titles)
        self.assertFalse(hasattr(dialog, "base_dir_edit"))
        self.assertFalse(hasattr(dialog, "existing_list"))
        self.assertTrue(dialog.windowFlags() & Qt.WindowType.FramelessWindowHint)
        self.assertEqual([], dialog.findChildren(QWidget, "framelessTitleBar"))
        self.assertFalse(hasattr(dialog, "title_bar"))
        self.assertNotIn("framelessTitleBar", dialog.styleSheet())
        self.assertNotIn("windowCloseButton", dialog.styleSheet())
        self.assertFalse(hasattr(dialog, "sidebar"))
        self.assertFalse(hasattr(dialog, "nav_buttons"))

    def test_settings_topic_cards_are_vertically_separated_with_internal_dividers(self) -> None:
        with patch("paper_spider.ui.settings_dialog.QSettings", FakeSettings):
            dialog = SettingsDialog()

        cards = dialog.findChildren(QWidget, "settingsContentCard")

        self.assertEqual(2, len(cards))
        self.assertGreaterEqual(dialog.content_cards_layout.spacing(), 24)
        self.assertEqual(1, len(dialog.appearance_card.findChildren(QWidget, "settingsFieldDivider")))

    def test_settings_exposes_appearance_theme_and_accent_color(self) -> None:
        SharedFakeSettings.values = {
            "appearance/theme": "Dark",
            "appearance/accent": "Green",
        }
        with patch("paper_spider.ui.settings_dialog.QSettings", SharedFakeSettings):
            dialog = SettingsDialog()

        self.assertEqual("Dark", dialog.theme_combo.currentText())
        self.assertEqual("Green", dialog.accent_combo.currentText())

        dialog.theme_combo.setCurrentText("Light")
        dialog.accent_combo.setCurrentText("Purple")

        self.assertEqual("Dark", SharedFakeSettings.values["appearance/theme"])
        self.assertEqual("Green", SharedFakeSettings.values["appearance/accent"])
        self.assertIn("#7c3aed", dialog.styleSheet())
        dialog.save_btn.click()

        self.assertEqual("Light", SharedFakeSettings.values["appearance/theme"])
        self.assertEqual("Purple", SharedFakeSettings.values["appearance/accent"])

    def test_settings_cancel_does_not_save_pending_changes(self) -> None:
        SharedFakeSettings.values = {
            "request_delay_ms": 300,
            "appearance/theme": "Dark",
            "appearance/accent": "Green",
        }
        with patch("paper_spider.ui.settings_dialog.QSettings", SharedFakeSettings):
            dialog = SettingsDialog()

        dialog.delay_spin.setValue(600)
        dialog.theme_combo.setCurrentText("Light")
        dialog.accent_combo.setCurrentText("Purple")
        dialog.cancel_btn.click()

        self.assertEqual(300, SharedFakeSettings.values["request_delay_ms"])
        self.assertEqual("Dark", SharedFakeSettings.values["appearance/theme"])
        self.assertEqual("Green", SharedFakeSettings.values["appearance/accent"])

    def test_settings_footer_and_rows_match_reference_structure(self) -> None:
        with patch("paper_spider.ui.settings_dialog.QSettings", FakeSettings):
            dialog = SettingsDialog()

        self.assertEqual("secondaryButton", dialog.restore_defaults_btn.objectName())
        self.assertEqual("secondaryButton", dialog.cancel_btn.objectName())
        self.assertEqual("primaryButton", dialog.save_btn.objectName())
        self.assertEqual("Save / Close", dialog.save_btn.text())
        self.assertEqual("ms", dialog.delay_unit_label.text())
        self.assertFalse(hasattr(dialog, "delay_unit_combo"))
        self.assertGreaterEqual(len(dialog.findChildren(QWidget, "settingsFieldRow")), 3)

    def test_settings_escape_rejects_frameless_dialog(self) -> None:
        with patch("paper_spider.ui.settings_dialog.QSettings", FakeSettings):
            dialog = SettingsDialog()

        dialog.show()
        QTest.keyClick(dialog, Qt.Key.Key_Escape)

        self.assertEqual(QDialog.DialogCode.Rejected.value, dialog.result())


class DatasetDialogTests(unittest.TestCase):
    def setUp(self) -> None:
        self.app = app()

    def test_dataset_dialog_uses_wide_dedicated_dataset_section(self) -> None:
        with patch("paper_spider.ui.dataset_dialog.QSettings", FakeSettings):
            dialog = DatasetDialog()

        titles = {group.title() for group in dialog.findChildren(QGroupBox)}
        self.assertIn("Base folder", titles)
        self.assertNotIn("Request interval", titles)
        self.assertIn("Datasets", titles)
        self.assertGreaterEqual(dialog.minimumWidth(), 760)
        self.assertFalse(hasattr(dialog, "delay_spin"))
        self.assertIsInstance(dialog.dataset_table, QTableWidget)
        headers = [
            dialog.dataset_table.horizontalHeaderItem(index).text()
            for index in range(dialog.dataset_table.columnCount())
        ]
        self.assertEqual(["Conference", "Year", "Status", "Papers", "Actions"], headers)
        self.assertEqual("Search datasets...", dialog.search_edit.placeholderText())
        self.assertTrue(dialog.windowFlags() & Qt.WindowType.FramelessWindowHint)
        self.assertEqual([], dialog.findChildren(QWidget, "framelessTitleBar"))
        self.assertFalse(hasattr(dialog, "title_bar"))

    def test_dataset_escape_rejects_frameless_dialog(self) -> None:
        with patch("paper_spider.ui.dataset_dialog.QSettings", FakeSettings):
            dialog = DatasetDialog()

        dialog.show()
        QTest.keyClick(dialog, Qt.Key.Key_Escape)

        self.assertEqual(QDialog.DialogCode.Rejected.value, dialog.result())

    def test_existing_dataset_row_is_table_row_with_inline_actions(self) -> None:
        with patch("paper_spider.ui.dataset_dialog.QSettings", FakeSettings):
            dialog = DatasetDialog()

        row = dialog._add_table_row(
            DatasetEntry("acl", 2025, "/tmp/acl/2025", is_existing=True, paper_count=1699)
        )

        actions = dialog.dataset_table.cellWidget(row, 4)
        self.assertIsNotNone(actions)
        buttons = [button.text() for button in actions.findChildren(QPushButton)]
        top_level_buttons = [
            button.text()
            for button in dialog.findChildren(QPushButton)
            if button.parent() is not actions
        ]

        self.assertEqual("ACL", dialog.dataset_table.item(row, 0).text())
        delegate = dialog.dataset_table.itemDelegateForColumn(0)
        self.assertIsInstance(delegate, DatasetConferenceDelegate)
        self.assertEqual(CONFERENCE_TEXT_INSET, delegate.text_inset)
        self.assertFalse(
            dialog.dataset_table.item(row, 0).flags() & Qt.ItemFlag.ItemIsUserCheckable
        )
        self.assertEqual("2025", dialog.dataset_table.item(row, 1).text())
        self.assertEqual("Fetched", dialog.dataset_table.cellWidget(row, 2).findChild(QLabel).text())
        self.assertEqual("1,699", dialog.dataset_table.item(row, 3).text())
        self.assertIn("Refresh", buttons)
        self.assertIn("x", buttons)
        status_label = dialog.dataset_table.cellWidget(row, 2).findChild(QLabel)
        refresh_button = next(
            button for button in actions.findChildren(QPushButton) if button.text() == "Refresh"
        )
        self.assertLessEqual(status_label.maximumHeight(), 22)
        self.assertEqual("datasetRefreshButton", refresh_button.objectName())
        self.assertLessEqual(refresh_button.maximumHeight(), 24)
        self.assertEqual([], dialog.dataset_table.cellWidget(row, 0).findChildren(QComboBox) if dialog.dataset_table.cellWidget(row, 0) else [])
        self.assertNotIn("Delete", top_level_buttons)

    def test_selected_row_uses_only_the_table_current_row(self) -> None:
        with patch("paper_spider.ui.dataset_dialog.QSettings", FakeSettings):
            dialog = DatasetDialog()

        dialog._add_table_row(
            DatasetEntry("acl", 2025, "/tmp/acl/2025", True, 1)
        )
        dialog._add_table_row(
            DatasetEntry("nsdi", 2025, "/tmp/nsdi/2025", True, 1)
        )
        dialog.dataset_table.item(0, 0).setCheckState(Qt.CheckState.Checked)
        dialog.dataset_table.setCurrentCell(1, 0)

        self.assertEqual(1, dialog._selected_row())

    def test_use_selected_is_enabled_only_for_a_fetched_current_row(self) -> None:
        with patch("paper_spider.ui.dataset_dialog.QSettings", FakeSettings):
            dialog = DatasetDialog()

        self.assertTrue(hasattr(dialog, "use_selected_btn"))
        self.assertFalse(dialog.use_selected_btn.isEnabled())
        fetched_row = dialog._add_table_row(
            DatasetEntry("acl", 2025, "/tmp/acl/2025", True, 1)
        )
        unfetched_row = dialog._add_table_row(
            DatasetEntry("nsdi", 2025, None, False, 0)
        )

        dialog.dataset_table.setCurrentCell(fetched_row, 0)
        self.assertTrue(dialog.use_selected_btn.isEnabled())
        dialog.dataset_table.setCurrentCell(unfetched_row, 0)
        self.assertFalse(dialog.use_selected_btn.isEnabled())
        dialog.dataset_table.setCurrentItem(None)
        self.assertFalse(dialog.use_selected_btn.isEnabled())

    def test_loading_stored_base_directory_updates_storage_summary(self) -> None:
        SharedFakeSettings.values = {"base_dir": "/tmp/papers"}
        with patch("paper_spider.ui.dataset_dialog.QSettings", SharedFakeSettings):
            dialog = DatasetDialog()

        self.assertEqual("Storage: /tmp/papers", dialog.storage_label.text())

    def test_double_clicking_fetched_dataset_uses_selected_item(self) -> None:
        with patch("paper_spider.ui.dataset_dialog.QSettings", FakeSettings):
            dialog = DatasetDialog()

        dialog.base_dir_edit.setText("/tmp")
        dialog._add_table_row(
            DatasetEntry("acl", 2025, "/tmp/acl/2025", is_existing=True, paper_count=1)
        )

        dialog.dataset_table.cellDoubleClicked.emit(0, 0)

        self.assertEqual(QDialog.DialogCode.Accepted.value, dialog.result())
        selection = dialog.selection()
        self.assertIsNotNone(selection)
        self.assertEqual("acl", selection.conf_slug)
        self.assertEqual(2025, selection.year)
        self.assertFalse(selection.fetch_after_select)

    def test_fetched_empty_dataset_can_still_be_used(self) -> None:
        with patch("paper_spider.ui.dataset_dialog.QSettings", FakeSettings):
            dialog = DatasetDialog()

        dialog.base_dir_edit.setText("/tmp")
        dialog._add_table_row(
            DatasetEntry("acl", 2025, "/tmp/acl/2025", is_existing=True, paper_count=0)
        )

        dialog.dataset_table.cellDoubleClicked.emit(0, 0)

        self.assertEqual(QDialog.DialogCode.Accepted.value, dialog.result())
        self.assertIsNotNone(dialog.selection())

    def test_add_dataset_opens_dedicated_inline_form_without_mutating_table(self) -> None:
        with patch("paper_spider.ui.dataset_dialog.QSettings", FakeSettings):
            dialog = DatasetDialog()

        initial_rows = dialog.dataset_table.rowCount()
        dialog._add_entry()

        self.assertEqual(initial_rows, dialog.dataset_table.rowCount())
        self.assertFalse(dialog.new_dataset_panel.isHidden())
        self.assertIsInstance(dialog.new_conf_combo, QComboBox)
        self.assertIsInstance(dialog.new_year_edit, QLineEdit)
        self.assertEqual([], dialog.new_dataset_panel.findChildren(QSpinBox))
        self.assertEqual("Fetch dataset", dialog.fetch_new_dataset_btn.text())
        dialog.cancel_new_dataset_btn.click()
        self.assertTrue(dialog.new_dataset_panel.isHidden())

    def test_fetch_button_returns_fetch_intent_for_selected_dataset(self) -> None:
        with patch("paper_spider.ui.dataset_dialog.QSettings", FakeSettings):
            dialog = DatasetDialog()

        dialog.base_dir_edit.setText("/tmp")
        dialog._add_entry()
        dialog.new_conf_combo.setCurrentIndex(0)
        dialog.new_year_edit.setText("2025")
        dialog.fetch_new_dataset_btn.click()

        self.assertEqual(QDialog.DialogCode.Accepted.value, dialog.result())
        selection = dialog.selection()
        self.assertIsNotNone(selection)
        self.assertTrue(selection.fetch_after_select)

    def test_double_clicking_unfetched_dataset_requires_fetch_first(self) -> None:
        with patch("paper_spider.ui.dataset_dialog.QSettings", FakeSettings):
            dialog = DatasetDialog()

        dialog.base_dir_edit.setText("/tmp")
        dialog._add_table_row(
            DatasetEntry("acl", 2025, None, is_existing=False, paper_count=0)
        )

        with patch("paper_spider.ui.dataset_dialog.show_warning") as warning:
            dialog.dataset_table.cellDoubleClicked.emit(0, 0)

        warning.assert_called_once()
        self.assertEqual(QDialog.DialogCode.Rejected.value, dialog.result())
        self.assertIsNone(dialog.selection())

    def test_dataset_search_filters_visible_rows(self) -> None:
        with patch("paper_spider.ui.dataset_dialog.QSettings", FakeSettings):
            dialog = DatasetDialog()

        dialog._add_table_row(DatasetEntry("acl", 2025, "/tmp/acl/2025", True, 1699))
        dialog._add_table_row(DatasetEntry("nsdi", 2025, "/tmp/nsdi/2025", True, 83))

        dialog.search_edit.setText("nsdi")

        self.assertTrue(dialog.dataset_table.isRowHidden(0))
        self.assertFalse(dialog.dataset_table.isRowHidden(1))

    def test_dataset_scan_skips_directories_without_read_permission(self) -> None:
        with tempfile.TemporaryDirectory() as base_dir:
            blocked_dir = os.path.join(base_dir, "blocked")
            os.makedirs(blocked_dir)
            real_listdir = os.listdir

            def listdir(path: str) -> list[str]:
                if path == blocked_dir:
                    raise PermissionError(path)
                return real_listdir(path)

            with patch("paper_spider.ui.dataset_dialog.os.listdir", side_effect=listdir):
                with patch("paper_spider.ui.dataset_dialog.QSettings", FakeSettings):
                    dialog = DatasetDialog()
                datasets = dialog._scan_datasets(base_dir)

        self.assertEqual([], datasets)

    def test_dataset_search_cannot_select_a_hidden_current_row(self) -> None:
        with patch("paper_spider.ui.dataset_dialog.QSettings", FakeSettings):
            dialog = DatasetDialog()

        dialog.base_dir_edit.setText("/tmp")
        dialog._add_table_row(
            DatasetEntry("acl", 2025, "/tmp/acl/2025", True, 1)
        )
        dialog._add_table_row(
            DatasetEntry("nsdi", 2025, "/tmp/nsdi/2025", True, 1)
        )
        dialog.dataset_table.setCurrentCell(0, 0)

        dialog.search_edit.setText("nsdi")

        self.assertTrue(dialog.dataset_table.isRowHidden(0))
        self.assertIsNone(dialog._selected_row())
        self.assertFalse(dialog.use_selected_btn.isEnabled())
        dialog._use_selected()
        self.assertEqual(QDialog.DialogCode.Rejected.value, dialog.result())
        self.assertIsNone(dialog.selection())

        dialog.search_edit.clear()

        self.assertEqual(0, dialog._selected_row())
        self.assertTrue(dialog.use_selected_btn.isEnabled())


class ExportDialogTests(unittest.TestCase):
    def setUp(self) -> None:
        self.app = app()
        self.rows = [
            {
                "title": "Paper A",
                "authors": '["Alice", "Bob"]',
                "abstract": "Abstract A",
            }
        ]

    def test_export_preview_is_generated_when_dialog_opens(self) -> None:
        dialog = ExportDialog(self.rows)

        self.assertIn("Paper A", dialog.output_text.toPlainText())

    def test_copy_feedback_resets_when_options_change(self) -> None:
        dialog = ExportDialog(self.rows)
        copy_button = next(
            button for button in dialog.findChildren(QPushButton) if button.text() == "Copy"
        )

        dialog._copy()
        self.assertEqual("Copied", copy_button.text())

        dialog.abstract_check.setChecked(True)

        self.assertEqual("Copy", copy_button.text())

    def test_export_uses_shared_theme_roles_with_native_window_chrome(self) -> None:
        dialog = ExportDialog(self.rows)
        button_roles = {
            button.text(): button.objectName()
            for button in dialog.findChildren(QPushButton)
        }

        self.assertFalse(dialog.windowFlags() & Qt.WindowType.FramelessWindowHint)
        self.assertTrue(dialog.styleSheet())
        self.assertEqual("primaryButton", button_roles["Generate"])
        self.assertEqual("secondaryButton", button_roles["Copy"])
        self.assertEqual("secondaryButton", button_roles["Close"])


if __name__ == "__main__":
    unittest.main()
