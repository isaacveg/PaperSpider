from __future__ import annotations

import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication, QLabel, QLineEdit, QWidget

from paper_spider.ui.theme import Appearance, appearance_from_values, apply_theme, build_stylesheet
from paper_spider.ui.workspace_view_helpers import WorkspaceSummary
from paper_spider.ui.workspace_widgets import CollapsibleLogPanel, DetailsPanel, SummaryStrip, TopBar


def app() -> QApplication:
    existing = QApplication.instance()
    if existing is not None:
        return existing
    return QApplication([])


class WorkspaceWidgetsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.app = app()

    def test_summary_strip_renders_counts_and_selection(self) -> None:
        widget = SummaryStrip()
        widget.set_summary(
            WorkspaceSummary(total=10, abstracts=3, pdfs=2, bibs=1),
            4,
            filtered_count=8,
            visible_count=6,
        )

        self.assertEqual("10", widget.total_value.text())
        self.assertEqual("6", widget.filtered_value.text())
        self.assertEqual("3", widget.abstracts_value.text())
        self.assertEqual("2", widget.pdfs_value.text())
        self.assertEqual("1", widget.bib_value.text())

    def test_details_panel_handles_empty_and_populated_rows(self) -> None:
        widget = DetailsPanel()
        widget.set_row(None)
        self.assertIn("No paper selected", widget.title_label.text())

        widget.set_row(
            {
                "title": "A Useful Paper",
                "authors_text": "Alice, Bob",
                "category_text": "main / conference",
                "abstract": "Detailed abstract",
                "pdf_path": "/tmp/paper.pdf",
                "bib_path": "/tmp/paper.bib",
            }
        )

        self.assertEqual("A Useful Paper", widget.title_label.text())
        self.assertIn("Alice, Bob", widget.meta_label.text())
        self.assertIn("Detailed abstract", widget.abstract_text.toPlainText())

    def test_details_panel_action_buttons_use_theme_roles(self) -> None:
        widget = DetailsPanel()

        buttons = [
            widget.download_abstract_btn,
            widget.open_pdf_btn,
            widget.copy_bib_btn,
            widget.reveal_pdf_btn,
            widget.reveal_bib_btn,
        ]

        self.assertTrue(all(button.objectName() == "secondaryButton" for button in buttons))

    def test_details_panel_removes_header_and_copies_existing_abstracts(self) -> None:
        widget = DetailsPanel()
        widget.set_row(
            {
                "title": "A Useful Paper",
                "authors_text": "Alice, Bob",
                "category_text": "main / conference",
                "abstract": "Detailed abstract",
                "abstract_status": 1,
                "pdf_path": "/tmp/paper.pdf",
                "bibtex": "@inproceedings{paper}",
            }
        )

        label_texts = {label.text() for label in widget.findChildren(QLabel)}
        self.assertNotIn("Details", label_texts)
        self.assertEqual("Copy abstract", widget.download_abstract_btn.text())
        self.assertTrue(widget.download_abstract_btn.isEnabled())

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
        self.assertEqual("Download abstract", widget.download_abstract_btn.text())

    def test_collapsible_log_panel_keeps_log_text(self) -> None:
        widget = CollapsibleLogPanel()
        widget.append_log("Downloading PDFs...")

        self.assertIn("Downloading PDFs...", widget.log_view.toPlainText())

    def test_top_bar_dataset_name_is_clickable(self) -> None:
        widget = TopBar()
        clicks = []
        widget.dataset_clicked.connect(lambda: clicks.append("dataset"))
        widget.set_dataset("NSDI 2025")

        self.assertEqual("NSDI 2025 \u25be", widget.dataset_btn.text())
        self.assertFalse(hasattr(widget, "fetch_btn"))
        widget.dataset_btn.click()
        self.assertEqual(["dataset"], clicks)

    def test_top_bar_controls_have_reference_style_roles(self) -> None:
        widget = TopBar()

        self.assertEqual("brandLabel", widget.app_label.objectName())
        self.assertEqual("datasetButton", widget.dataset_btn.objectName())
        self.assertEqual("secondaryButton", widget.settings_btn.objectName())
        self.assertFalse(hasattr(widget, "window_controls"))

    def test_apply_theme_styles_widgets_without_changing_native_window_flags(self) -> None:
        widget = QWidget()

        apply_theme(widget)

        self.assertFalse(widget.windowFlags() & Qt.WindowType.FramelessWindowHint)
        self.assertTrue(widget.styleSheet())

    def test_top_bar_owns_search_beside_summary_strip(self) -> None:
        search = QLineEdit()
        summary = SummaryStrip()

        widget = TopBar(summary_widget=summary, search_widget=search)

        self.assertIs(search.parentWidget(), widget)
        self.assertIs(summary.parentWidget(), widget)
        self.assertGreaterEqual(widget.layout().indexOf(search), 0)
        self.assertGreaterEqual(widget.layout().indexOf(summary), 0)

    def test_dark_theme_styles_disabled_and_secondary_buttons(self) -> None:
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

        stylesheet = build_stylesheet(dark)

        self.assertIn("QPushButton:disabled", stylesheet)
        self.assertIn("QPushButton#secondaryButton", stylesheet)
        self.assertIn("QPushButton#secondaryButton:disabled", stylesheet)
        self.assertNotIn("background: #edf2f7", stylesheet)

    def test_theme_styles_modern_comboboxes_and_scrollbars(self) -> None:
        dark = Appearance(
            theme="Dark",
            accent="Green",
            accent_color="#16a34a",
            background="#111827",
            surface="#1f2937",
            surface_alt="#273244",
            border="#374151",
            text="#f9fafb",
            muted="#cbd5e1",
        )

        stylesheet = build_stylesheet(dark)

        self.assertIn("QComboBox::drop-down", stylesheet)
        self.assertIn("QComboBox::down-arrow", stylesheet)
        self.assertIn("QComboBox QAbstractItemView", stylesheet)
        self.assertIn("QScrollBar::up-arrow:vertical", stylesheet)
        self.assertIn("QScrollBar::down-arrow:vertical", stylesheet)
        self.assertIn("QScrollBar::add-page:vertical", stylesheet)
        self.assertIn("QProgressBar::chunk", stylesheet)
        self.assertIn("QLineEdit#quickFilterEdit", stylesheet)
        self.assertIn("QComboBox#filterRoleCombo", stylesheet)
        self.assertIn("QWidget#minPreferredRow", stylesheet)

    def test_theme_preserves_native_checkbox_and_table_indicators(self) -> None:
        for theme in ("Light", "Dark"):
            with self.subTest(theme=theme):
                stylesheet = build_stylesheet(appearance_from_values(theme, "Blue"))

                self.assertNotIn("QCheckBox::indicator", stylesheet)
                self.assertNotIn("QTableView::indicator", stylesheet)

    def test_theme_omits_removed_settings_sidebar_navigation_styles(self) -> None:
        stylesheet = build_stylesheet(appearance_from_values("Light", "Blue"))

        self.assertNotIn("settingsSidebar", stylesheet)
        self.assertNotIn("settingsNavButton", stylesheet)


if __name__ == "__main__":
    unittest.main()
