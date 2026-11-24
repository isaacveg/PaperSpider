from __future__ import annotations

import os
import unittest
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("PAPERSPIDER_LANG", "en")

from PyQt6.QtCore import QPoint, Qt
from PyQt6.QtWidgets import QApplication, QFrame, QWidget

from paper_spider.filtering import FilterConfig
from paper_spider.ui.theme import Appearance, appearance_from_values, apply_theme, build_stylesheet
from paper_spider.ui.workspace_widgets import (
    SIDEBAR_MIN_WIDTH,
    SIDEBAR_RAIL_WIDTH,
    AppSidebar,
    conference_badge_label,
    CollapsibleLogPanel,
    DetailsPanel,
    WorkspaceHeader,
)


_APPLICATION = QApplication.instance() or QApplication([])


def app() -> QApplication:
    return _APPLICATION


class WorkspaceWidgetsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.app = app()

    def test_details_panel_handles_empty_and_populated_rows(self) -> None:
        widget = DetailsPanel()
        widget.set_row(None)
        self.assertFalse(widget.placeholder.isHidden())
        self.assertTrue(widget.content_widget.isHidden())

        widget.set_row(
            {
                "title": "A Useful Paper",
                "authors_text": "Alice, Bob",
                "category_text": "main / conference",
                "keywords_text": "cache, systems",
                "abstract": "Detailed abstract",
                "pdf_path": "/tmp/paper.pdf",
                "bib_path": "/tmp/paper.bib",
                "conf": "iclr",
                "year": 2025,
            }
        )

        self.assertEqual("A Useful Paper", widget.title_label.text())
        self.assertIn("Alice, Bob", widget.authors_label.text())
        self.assertIn("ICLR 2025", widget.breadcrumb_label.text())
        self.assertIn("Detailed abstract", widget.abstract_text.toPlainText())
        self.assertTrue(widget.placeholder.isHidden())
        self.assertFalse(widget.reveal_pdf_btn.isHidden())
        chips = widget.findChildren(QFrame, "tagChip")
        self.assertEqual(2, len(chips))

    def test_details_panel_action_buttons_use_theme_roles(self) -> None:
        widget = DetailsPanel()

        self.assertEqual("primaryButton", widget.open_pdf_btn.objectName())
        self.assertEqual("secondaryButton", widget.copy_bib_btn.objectName())
        self.assertEqual("sectionAction", widget.abstract_action_btn.objectName())
        self.assertEqual("secondaryButton", widget.reveal_pdf_btn.objectName())

    def test_details_panel_switches_abstract_action_between_copy_and_download(self) -> None:
        widget = DetailsPanel()
        widget.set_row(
            {
                "title": "A Useful Paper",
                "authors_text": "Alice",
                "category_text": "main / conference",
                "abstract": "Detailed abstract",
                "abstract_status": 1,
            }
        )
        self.assertEqual("Copy", widget.abstract_action_btn.text())
        self.assertTrue(widget.abstract_action_btn.isEnabled())

        widget.set_feedback("Abstract copied to clipboard.")
        self.assertIn("copied", widget.feedback_label.text())

        widget.set_row(
            {
                "title": "No Abstract Yet",
                "authors_text": "Alice",
                "category_text": "main / conference",
                "abstract": "",
                "abstract_status": 0,
            }
        )
        self.assertEqual("Download", widget.abstract_action_btn.text())

    def test_sidebar_lists_datasets_and_emits_selection(self) -> None:
        widget = AppSidebar()
        selected: list[tuple[str, int]] = []
        widget.dataset_clicked.connect(lambda conf, year: selected.append((conf, year)))
        widget.set_datasets(
            [
                {"conf": "iclr", "name": "ICLR", "year": 2025, "papers": 10, "selected": False},
                {"conf": "osdi", "name": "OSDI", "year": 2024, "papers": 48, "selected": True},
            ]
        )

        self.assertEqual(2, len(widget._dataset_items))
        second = widget._dataset_items[1]
        self.assertTrue(second.main_btn.toolTip().startswith("OSDI 2024"))
        self.assertTrue(second.property("active"))
        self.assertFalse(second.menu_btn.isHidden())
        self.assertFalse(second.refresh_btn.isHidden())

        widget._dataset_items[0].main_btn.click()
        self.assertEqual([("iclr", 2025)], selected)

    def test_sidebar_refresh_action_emits_dataset(self) -> None:
        widget = AppSidebar()
        widget.set_datasets(
            [
                {
                    "conf": "iclr",
                    "name": "ICLR",
                    "year": 2025,
                    "papers": 10,
                    "selected": True,
                }
            ]
        )
        refreshed: list[tuple[str, int]] = []
        widget.refresh_dataset.connect(
            lambda conf, year: refreshed.append((conf, year))
        )
        widget._dataset_items[0].refresh_btn.click()
        self.assertEqual([("iclr", 2025)], refreshed)

    def test_sidebar_switches_between_expanded_and_icon_rail(self) -> None:
        widget = AppSidebar()
        widget.set_datasets(
            [
                {
                    "conf": "usenix_security",
                    "name": "USENIX Security",
                    "year": 2025,
                    "papers": 10,
                    "selected": True,
                }
            ]
        )
        widget.resize(SIDEBAR_RAIL_WIDTH, 600)
        widget.show()
        self.app.processEvents()

        item = widget._dataset_items[0]
        self.assertTrue(widget.is_compact())
        self.assertTrue(widget.brand_label.isHidden())
        self.assertTrue(widget.section_label.isHidden())
        self.assertFalse(widget.expand_btn.isHidden())
        self.assertEqual("", widget.all_papers_btn.text())
        self.assertEqual("All papers", widget.all_papers_btn.toolTip())
        self.assertFalse(item.badge_btn.isHidden())
        self.assertTrue(item.main_btn.isHidden())
        self.assertTrue(item.menu_btn.isHidden())

        widget.resize(SIDEBAR_MIN_WIDTH, 600)
        self.app.processEvents()

        self.assertFalse(widget.is_compact())
        self.assertFalse(widget.brand_label.isHidden())
        self.assertFalse(widget.section_label.isHidden())
        self.assertEqual("All papers", widget.all_papers_btn.text())
        self.assertTrue(item.badge_btn.isHidden())
        self.assertFalse(item.menu_btn.isHidden())
        widget.close()

    def test_dataset_text_does_not_reflow_when_hover_actions_appear(self) -> None:
        widget = AppSidebar()
        widget.set_datasets(
            [
                {"conf": "neurips", "name": "NeurIPS", "year": 2024, "papers": 1, "selected": False},
            ]
        )
        widget.resize(SIDEBAR_MIN_WIDTH, 600)
        widget.show()
        self.app.processEvents()
        item = widget._dataset_items[0]
        before = (item.main_btn.width(), item.main_btn.text())

        item._hovered = True
        item._update_menu_visibility()
        self.app.processEvents()

        self.assertFalse(item.menu_btn.isHidden())
        self.assertEqual(before, (item.main_btn.width(), item.main_btn.text()))
        widget.close()

    def test_conference_badge_label_is_short(self) -> None:
        self.assertEqual("NeurIPS", conference_badge_label("NeurIPS"))
        self.assertEqual("US", conference_badge_label("USENIX Security"))

    def test_dataset_menu_emits_open_and_delete_actions(self) -> None:
        widget = AppSidebar()
        events: list[tuple[str, str, int]] = []
        widget.open_dataset_folder.connect(
            lambda conf, year: events.append(("open", conf, year))
        )
        widget.delete_dataset.connect(
            lambda conf, year: events.append(("delete", conf, year))
        )

        with patch("paper_spider.ui.workspace_widgets.QMenu") as menu_class:
            menu = menu_class.return_value
            open_action = object()
            delete_action = object()
            menu.addAction.side_effect = [open_action, delete_action]
            menu.exec.return_value = open_action
            widget._show_dataset_menu("iclr", 2025, QPoint(0, 0))

            menu.addAction.side_effect = [open_action, delete_action]
            menu.exec.return_value = delete_action
            widget._show_dataset_menu("iclr", 2025, QPoint(0, 0))

        self.assertEqual(
            [
                ("open", "iclr", 2025),
                ("delete", "iclr", 2025),
            ],
            events,
        )

    def test_sidebar_navigation_signals(self) -> None:
        widget = AppSidebar()
        events: list[str] = []
        widget.all_papers_clicked.connect(lambda: events.append("all"))
        widget.filters_clicked.connect(lambda: events.append("filters"))
        widget.add_dataset_clicked.connect(lambda: events.append("add"))
        widget.settings_clicked.connect(lambda: events.append("settings"))
        widget.toggle_compact_clicked.connect(lambda: events.append("toggle"))

        widget.all_papers_btn.click()
        widget.filters_btn.click()
        widget.add_dataset_btn.click()
        widget.settings_btn.click()
        widget.collapse_btn.click()

        self.assertEqual(
            ["all", "filters", "add", "settings", "toggle"], events
        )

    def test_details_panel_close_button_emits(self) -> None:
        widget = DetailsPanel()
        events: list[str] = []
        widget.close_clicked.connect(lambda: events.append("close"))
        widget.close_btn.click()
        self.assertEqual(["close"], events)

    def test_sidebar_shows_filter_count(self) -> None:
        widget = AppSidebar()
        widget.set_filter_count(2)
        self.assertIn("2", widget.filters_btn.text())

    def test_header_sets_title_counts_and_filter_chips(self) -> None:
        widget = WorkspaceHeader()
        removed: list[int] = []
        widget.filter_removed.connect(removed.append)
        widget.set_dataset("ICLR 2025", "")
        widget.set_counts(10, 6)
        configs = [
            FilterConfig(True, "all", "contains", "must", "inference"),
            FilterConfig(True, "all", "contains", "must not", "training"),
        ]
        widget.set_filters(configs)

        self.assertEqual("ICLR 2025", widget.title_label.text())
        self.assertEqual("10 papers · 6 matches", widget.subtitle_label.text())
        self.assertIn("(2)", widget.filter_btn.text())
        self.assertFalse(widget.chips_container.isHidden())
        chips = widget.findChildren(QFrame, "filterChip")
        self.assertEqual(2, len(chips))
        close_buttons = [
            button
            for chip in chips
            for button in chip.findChildren(QWidget, "chipClose")
        ]
        self.assertEqual(2, len(close_buttons))
        close_buttons[0].click()
        self.assertEqual([0], removed)

    def test_header_search_field_exposes_shortcut_hint(self) -> None:
        widget = WorkspaceHeader()
        self.assertEqual("Search in results", widget.quick_filter_edit.placeholderText())
        self.assertTrue(widget.search_field.shortcut_label.text())

    def test_task_bar_shows_progress_and_cancel(self) -> None:
        widget = CollapsibleLogPanel()
        widget.set_busy("Downloading PDFs...", 2, 10)

        self.assertEqual("Downloading PDFs...", widget.status_label.text())
        self.assertFalse(widget.progress_bar.isHidden())
        self.assertEqual(10, widget.progress_bar.maximum())
        self.assertEqual(2, widget.progress_bar.value())
        self.assertEqual("2 / 10", widget.progress_count_label.text())
        self.assertFalse(widget.cancel_btn.isHidden())

        widget.set_ready()
        self.assertTrue(widget.progress_bar.isHidden())
        self.assertTrue(widget.cancel_btn.isHidden())

    def test_task_bar_keeps_log_text_and_toggles(self) -> None:
        widget = CollapsibleLogPanel()
        widget.append_log("Downloading PDFs...")

        self.assertIn("Downloading PDFs...", widget.log_view.toPlainText())
        self.assertEqual("logToggleButton", widget.toggle_btn.objectName())
        self.assertEqual(Qt.ArrowType.NoArrow, widget.toggle_btn.arrowType())
        self.assertFalse(widget.toggle_btn.property("expanded"))
        widget.toggle_btn.click()
        self.assertTrue(widget.toggle_btn.property("expanded"))
        self.assertFalse(widget.log_view.isHidden())

    def test_apply_theme_sets_stylesheet(self) -> None:
        widget = QWidget()

        apply_theme(widget)

        self.assertTrue(widget.styleSheet())

    def test_dark_theme_styles_disabled_and_secondary_buttons(self) -> None:
        dark = Appearance(
            theme="Dark",
            accent="Blue",
            accent_color="#4d94ff",
            background="#1b1c1b",
            surface="#242624",
            surface_alt="#2c2f2c",
            border="#3b3f3b",
            text="#f1f0e9",
            muted="#b1b3aa",
        )

        stylesheet = build_stylesheet(dark)

        self.assertIn("QPushButton:disabled", stylesheet)
        self.assertIn("QPushButton#secondaryButton", stylesheet)
        self.assertIn("QPushButton#secondaryButton:disabled", stylesheet)

    def test_theme_styles_modern_comboboxes_and_workspace_components(self) -> None:
        dark = Appearance(
            theme="Dark",
            accent="Green",
            accent_color="#4ade80",
            background="#1b1c1b",
            surface="#242624",
            surface_alt="#2c2f2c",
            border="#3b3f3b",
            text="#f1f0e9",
            muted="#b1b3aa",
        )

        stylesheet = build_stylesheet(dark)

        self.assertIn("QComboBox::drop-down", stylesheet)
        self.assertIn("QWidget#appSidebar", stylesheet)
        self.assertIn("QFrame#filterChip[role=\"must\"]", stylesheet)
        self.assertIn("QWidget#taskBar", stylesheet)

    def test_theme_preserves_native_checkbox_and_table_indicators(self) -> None:
        for theme in ("Light", "Dark"):
            with self.subTest(theme=theme):
                stylesheet = build_stylesheet(appearance_from_values(theme, "Forest"))

                self.assertNotIn("QCheckBox::indicator", stylesheet)
                self.assertNotIn("QTableView::indicator", stylesheet)


if __name__ == "__main__":
    unittest.main()