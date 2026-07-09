from __future__ import annotations

import os
import unittest
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QApplication,
    QComboBox,
    QDialog,
    QGroupBox,
    QLabel,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QWidget,
)

from paper_spider.ui.dataset_dialog import DatasetDialog, DatasetEntry
from paper_spider.ui.export_dialog import ExportDialog
from paper_spider.ui.settings_dialog import SettingsDialog


def app() -> QApplication:
    existing = QApplication.instance()
    if existing is not None:
        return existing
    return QApplication([])


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
        self.assertGreaterEqual(dialog.minimumWidth(), 900)
        self.assertGreaterEqual(dialog.minimumHeight(), 560)
        self.assertEqual([], dialog.findChildren(QGroupBox))
        nav_labels = [button.text() for button in dialog.nav_buttons]
        self.assertEqual(["General", "Appearance"], nav_labels)
        section_titles = {
            label.text()
            for label in dialog.findChildren(QLabel)
            if label.objectName() == "settingsCardTitle"
        }
        self.assertIn("Request Interval", section_titles)
        self.assertIn("Appearance", section_titles)
        self.assertFalse(hasattr(dialog, "base_dir_edit"))
        self.assertFalse(hasattr(dialog, "existing_list"))
        self.assertTrue(dialog.windowFlags() & Qt.WindowType.NoTitleBarBackgroundHint)

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
        self.assertEqual("ms", dialog.delay_unit_combo.currentText())
        self.assertGreaterEqual(dialog.delay_unit_combo.minimumWidth(), 96)
        self.assertEqual("settingsSidebar", dialog.sidebar.objectName())
        self.assertGreaterEqual(len(dialog.findChildren(QWidget, "settingsFieldRow")), 3)


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
        self.assertEqual(["", "Conference", "Year", "Status", "Papers", "Actions"], headers)
        self.assertEqual("Search datasets...", dialog.search_edit.placeholderText())
        self.assertTrue(dialog.windowFlags() & Qt.WindowType.NoTitleBarBackgroundHint)

    def test_existing_dataset_row_is_table_row_with_inline_actions(self) -> None:
        with patch("paper_spider.ui.dataset_dialog.QSettings", FakeSettings):
            dialog = DatasetDialog()

        row = dialog._add_table_row(
            DatasetEntry("acl", 2025, "/tmp/acl/2025", is_existing=True, paper_count=1699),
            editable=False,
        )

        actions = dialog.dataset_table.cellWidget(row, 5)
        buttons = [button.text() for button in actions.findChildren(QPushButton)]
        top_level_buttons = [
            button.text()
            for button in dialog.findChildren(QPushButton)
            if button.parent() is not actions
        ]

        self.assertEqual("ACL", dialog.dataset_table.item(row, 1).text())
        self.assertEqual("2025", dialog.dataset_table.item(row, 2).text())
        self.assertEqual("Fetched", dialog.dataset_table.cellWidget(row, 3).findChild(QLabel).text())
        self.assertEqual("1,699", dialog.dataset_table.item(row, 4).text())
        self.assertIn("Refresh", buttons)
        self.assertIn("x", buttons)
        self.assertEqual([], dialog.dataset_table.cellWidget(row, 1).findChildren(QComboBox) if dialog.dataset_table.cellWidget(row, 1) else [])
        self.assertNotIn("Delete", top_level_buttons)

    def test_double_clicking_fetched_dataset_uses_selected_item(self) -> None:
        with patch("paper_spider.ui.dataset_dialog.QSettings", FakeSettings):
            dialog = DatasetDialog()

        dialog.base_dir_edit.setText("/tmp")
        dialog._add_table_row(
            DatasetEntry("acl", 2025, "/tmp/acl/2025", is_existing=True, paper_count=1),
            editable=False,
        )

        dialog.dataset_table.cellDoubleClicked.emit(0, 1)

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
            DatasetEntry("acl", 2025, "/tmp/acl/2025", is_existing=True, paper_count=0),
            editable=False,
        )

        dialog.dataset_table.cellDoubleClicked.emit(0, 1)

        self.assertEqual(QDialog.DialogCode.Accepted.value, dialog.result())
        self.assertIsNotNone(dialog.selection())

    def test_new_dataset_row_indicates_it_is_not_fetched_yet(self) -> None:
        with patch("paper_spider.ui.dataset_dialog.QSettings", FakeSettings):
            dialog = DatasetDialog()

        dialog._add_entry()

        row = dialog.dataset_table.rowCount() - 1
        actions = dialog.dataset_table.cellWidget(row, 5)
        buttons = [button.text() for button in actions.findChildren(QPushButton)]
        self.assertEqual("Unfetched", dialog.dataset_table.cellWidget(row, 3).findChild(QLabel).text())
        self.assertIsInstance(dialog.dataset_table.cellWidget(row, 1), QComboBox)
        self.assertIn("Fetch", buttons)

    def test_fetch_button_returns_fetch_intent_for_selected_dataset(self) -> None:
        with patch("paper_spider.ui.dataset_dialog.QSettings", FakeSettings):
            dialog = DatasetDialog()

        dialog.base_dir_edit.setText("/tmp")
        dialog._add_entry()
        actions = dialog.dataset_table.cellWidget(0, 5)
        fetch_btn = next(button for button in actions.findChildren(QPushButton) if button.text() == "Fetch")

        fetch_btn.click()

        self.assertEqual(QDialog.DialogCode.Accepted.value, dialog.result())
        selection = dialog.selection()
        self.assertIsNotNone(selection)
        self.assertTrue(selection.fetch_after_select)

    def test_double_clicking_unfetched_dataset_requires_fetch_first(self) -> None:
        with patch("paper_spider.ui.dataset_dialog.QSettings", FakeSettings):
            dialog = DatasetDialog()

        dialog.base_dir_edit.setText("/tmp")
        dialog._add_table_row(
            DatasetEntry("acl", 2025, None, is_existing=False, paper_count=0),
            editable=True,
        )

        with patch("paper_spider.ui.dataset_dialog.QMessageBox.warning") as warning:
            dialog.dataset_table.cellDoubleClicked.emit(0, 1)

        warning.assert_called_once()
        self.assertEqual(QDialog.DialogCode.Rejected.value, dialog.result())
        self.assertIsNone(dialog.selection())

    def test_dataset_search_filters_visible_rows(self) -> None:
        with patch("paper_spider.ui.dataset_dialog.QSettings", FakeSettings):
            dialog = DatasetDialog()

        dialog._add_table_row(DatasetEntry("acl", 2025, "/tmp/acl/2025", True, 1699), editable=False)
        dialog._add_table_row(DatasetEntry("nsdi", 2025, "/tmp/nsdi/2025", True, 83), editable=False)

        dialog.search_edit.setText("nsdi")

        self.assertTrue(dialog.dataset_table.isRowHidden(0))
        self.assertFalse(dialog.dataset_table.isRowHidden(1))


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


if __name__ == "__main__":
    unittest.main()
