# Copyright 2026 Isaacveg
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#     http://www.apache.org/licenses/LICENSE-2.0

from __future__ import annotations

from typing import Optional

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QTextEdit,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from .workspace_view_helpers import WorkspaceSummary


def _panel_frame() -> QFrame:
    frame = QFrame()
    frame.setFrameShape(QFrame.Shape.StyledPanel)
    return frame


class TopBar(QWidget):
    settings_clicked = pyqtSignal()
    dataset_clicked = pyqtSignal()

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        summary_widget: Optional[QWidget] = None,
        search_widget: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        layout = QHBoxLayout()
        layout.setContentsMargins(8, 6, 8, 6)

        self.app_label = QLabel("PaperSpider")
        self.app_label.setObjectName("brandLabel")
        self.dataset_btn = QPushButton("No dataset selected")
        self.dataset_btn.setObjectName("datasetButton")
        self.dataset_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.dataset_btn.setToolTip("Choose or manage datasets")
        self.dataset_btn.clicked.connect(self.dataset_clicked.emit)

        self.settings_btn = QPushButton("Settings")
        self.settings_btn.setObjectName("secondaryButton")
        self.settings_btn.clicked.connect(self.settings_clicked.emit)

        layout.addWidget(self.app_label)
        layout.addSpacing(16)
        layout.addWidget(self.dataset_btn)
        if summary_widget is not None or search_widget is not None:
            layout.addStretch(1)
        if search_widget is not None:
            layout.addWidget(search_widget)
        if summary_widget is not None:
            layout.addWidget(summary_widget)
        layout.addStretch()
        layout.addWidget(self.settings_btn)
        self.setLayout(layout)

    def set_dataset(self, text: str) -> None:
        self.dataset_btn.setText(f"{text} \u25be")


class SummaryStrip(QWidget):
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        card = QFrame()
        card.setObjectName("summaryStatsCard")
        card_layout = QHBoxLayout()
        card_layout.setContentsMargins(14, 6, 14, 6)
        card_layout.setSpacing(18)

        self.total_value = self._stat(card_layout, "Total")
        self.filtered_value = self._stat(card_layout, "Filtered")
        self.abstracts_value = self._stat(card_layout, "Abstracts")
        self.pdfs_value = self._stat(card_layout, "PDFs")
        self.bib_value = self._stat(card_layout, "Bib")
        card.setLayout(card_layout)

        layout.addWidget(card)
        self.setLayout(layout)

    def _stat(self, layout: QHBoxLayout, label: str) -> QLabel:
        container = QWidget()
        container.setObjectName("summaryStat")
        stat_layout = QVBoxLayout()
        stat_layout.setContentsMargins(0, 0, 0, 0)
        stat_layout.setSpacing(1)
        label_widget = QLabel(label)
        label_widget.setObjectName("summaryStatLabel")
        value_widget = QLabel("0")
        value_widget.setObjectName("summaryStatValue")
        stat_layout.addWidget(label_widget)
        stat_layout.addWidget(value_widget)
        container.setLayout(stat_layout)
        layout.addWidget(container)
        return value_widget

    def set_summary(
        self,
        summary: WorkspaceSummary,
        selected_count: int,
        filtered_count: Optional[int] = None,
        visible_count: Optional[int] = None,
    ) -> None:
        del selected_count
        filtered_value = visible_count if visible_count is not None else filtered_count
        if filtered_value is None:
            filtered_value = summary.total
        self.total_value.setText(f"{summary.total:,}")
        self.filtered_value.setText(f"{filtered_value:,}")
        self.abstracts_value.setText(f"{summary.abstracts:,}")
        self.pdfs_value.setText(f"{summary.pdfs:,}")
        self.bib_value.setText(f"{summary.bibs:,}")


class EmptyStateWidget(QWidget):
    primary_clicked = pyqtSignal()

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.title_label = QLabel("Choose a dataset to start")
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.title_label.setStyleSheet("font-size: 18px; font-weight: 700;")
        self.message_label = QLabel("")
        self.message_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.message_label.setWordWrap(True)
        self.primary_btn = QPushButton("Choose dataset")
        self.primary_btn.clicked.connect(self.primary_clicked.emit)

        layout.addStretch()
        layout.addWidget(self.title_label)
        layout.addWidget(self.message_label)
        layout.addSpacing(8)
        layout.addWidget(self.primary_btn, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addStretch()
        self.setLayout(layout)

    def set_content(self, title: str, message: str, button_text: str) -> None:
        self.title_label.setText(title)
        self.message_label.setText(message)
        self.primary_btn.setText(button_text)


class DetailsPanel(QWidget):
    download_abstract_clicked = pyqtSignal()
    open_pdf_clicked = pyqtSignal()
    copy_bib_clicked = pyqtSignal()
    reveal_pdf_clicked = pyqtSignal()
    reveal_bib_clicked = pyqtSignal()

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        frame = _panel_frame()
        frame_layout = QVBoxLayout()

        self.title_label = QLabel("No paper selected")
        self.title_label.setWordWrap(True)
        self.title_label.setStyleSheet("font-weight: 700;")
        self.meta_label = QLabel("Select a row to preview details.")
        self.meta_label.setWordWrap(True)
        self.path_label = QLabel("")
        self.path_label.setWordWrap(True)
        self.path_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.feedback_label = QLabel("")
        self.feedback_label.setObjectName("detailsFeedbackLabel")
        self.feedback_label.setWordWrap(True)
        self.abstract_text = QTextEdit()
        self.abstract_text.setReadOnly(True)
        self.abstract_text.setPlaceholderText("Abstract will appear here when available.")

        self.download_abstract_btn = QPushButton("Download abstract")
        self.open_pdf_btn = QPushButton("Open PDF")
        self.copy_bib_btn = QPushButton("Copy Bib")
        self.reveal_pdf_btn = QPushButton("Reveal PDF")
        self.reveal_bib_btn = QPushButton("Reveal Bib")
        for button in (
            self.download_abstract_btn,
            self.open_pdf_btn,
            self.copy_bib_btn,
            self.reveal_pdf_btn,
            self.reveal_bib_btn,
        ):
            button.setObjectName("secondaryButton")

        self.download_abstract_btn.clicked.connect(self.download_abstract_clicked.emit)
        self.open_pdf_btn.clicked.connect(self.open_pdf_clicked.emit)
        self.copy_bib_btn.clicked.connect(self.copy_bib_clicked.emit)
        self.reveal_pdf_btn.clicked.connect(self.reveal_pdf_clicked.emit)
        self.reveal_bib_btn.clicked.connect(self.reveal_bib_clicked.emit)

        frame_layout.addWidget(self.title_label)
        frame_layout.addWidget(self.meta_label)
        frame_layout.addWidget(self.abstract_text, stretch=1)
        frame_layout.addWidget(self.path_label)
        frame_layout.addWidget(self.feedback_label)
        frame_layout.addWidget(self.download_abstract_btn)
        frame_layout.addWidget(self.open_pdf_btn)
        frame_layout.addWidget(self.copy_bib_btn)
        frame_layout.addWidget(self.reveal_pdf_btn)
        frame_layout.addWidget(self.reveal_bib_btn)
        frame.setLayout(frame_layout)

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(frame)
        self.setLayout(layout)
        self.set_row(None)

    def set_row(self, row: Optional[dict]) -> None:
        if not row:
            self.title_label.setText("No paper selected")
            self.meta_label.setText("Select a row to preview details.")
            self.abstract_text.clear()
            self.path_label.clear()
            self.set_feedback("")
            self._set_action_enabled(False, False, False, False, False)
            self.download_abstract_btn.setText("Download abstract")
            self.open_pdf_btn.setText("Open PDF")
            self.copy_bib_btn.setText("Copy Bib")
            return

        authors = row.get("authors_text") or "Unknown authors"
        category = row.get("category_text") or "Uncategorized"
        keywords = row.get("keywords_text") or ""
        abstract = row.get("abstract") or ""
        pdf_path = row.get("pdf_path") or ""
        bib_path = row.get("bib_path") or ""

        self.title_label.setText(str(row.get("title") or "Untitled paper"))
        meta_parts = [str(authors), str(category)]
        if keywords:
            meta_parts.append(f"Keywords: {keywords}")
        self.meta_label.setText("\n".join(meta_parts))
        self.abstract_text.setPlainText(str(abstract))
        self.set_feedback("")
        paths = []
        if pdf_path:
            paths.append(f"PDF: {pdf_path}")
        if bib_path:
            paths.append(f"Bib: {bib_path}")
        self.path_label.setText("\n".join(paths))
        self.download_abstract_btn.setText(
            "Copy abstract" if abstract else "Download abstract"
        )
        self.open_pdf_btn.setText("Open PDF" if pdf_path else "Download PDF")
        self.copy_bib_btn.setText("Copy Bib" if row.get("bibtex") or bib_path else "Export Bib")
        self._set_action_enabled(
            True,
            True,
            True,
            bool(pdf_path),
            bool(bib_path),
        )

    def set_feedback(self, message: str) -> None:
        self.feedback_label.setText(message)
        self.feedback_label.setVisible(bool(message))

    def _set_action_enabled(
        self,
        download_abstract: bool,
        open_pdf: bool,
        copy_bib: bool,
        reveal_pdf: bool,
        reveal_bib: bool,
    ) -> None:
        self.download_abstract_btn.setEnabled(download_abstract)
        self.open_pdf_btn.setEnabled(open_pdf)
        self.copy_bib_btn.setEnabled(copy_bib)
        self.reveal_pdf_btn.setEnabled(reveal_pdf)
        self.reveal_bib_btn.setEnabled(reveal_bib)


class CollapsibleLogPanel(QWidget):
    cancel_abstracts_clicked = pyqtSignal()
    cancel_pdfs_clicked = pyqtSignal()

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)

        header = QHBoxLayout()
        self.toggle_btn = QToolButton()
        self.toggle_btn.setObjectName("logToggleButton")
        self.toggle_btn.setText("Show log")
        self.toggle_btn.setArrowType(Qt.ArrowType.RightArrow)
        self.toggle_btn.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.toggle_btn.setCheckable(True)
        self.toggle_btn.toggled.connect(self._set_log_visible)
        self.status_label = QLabel("Ready")
        self.status_label.setMinimumWidth(220)
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 1)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(False)
        self.cancel_abstracts_btn = QPushButton("Cancel abstracts")
        self.cancel_pdfs_btn = QPushButton("Cancel PDFs")
        self.cancel_abstracts_btn.clicked.connect(self.cancel_abstracts_clicked.emit)
        self.cancel_pdfs_btn.clicked.connect(self.cancel_pdfs_clicked.emit)

        header.addWidget(self.toggle_btn)
        header.addWidget(self.status_label)
        header.addWidget(self.progress_bar, stretch=1)
        header.addWidget(self.cancel_abstracts_btn)
        header.addWidget(self.cancel_pdfs_btn)

        self.log_view = QTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setVisible(False)

        layout.addLayout(header)
        layout.addWidget(self.log_view)
        self.setLayout(layout)
        self.set_ready()

    def append_log(self, message: str) -> None:
        self.log_view.append(message)

    def set_busy(
        self,
        message: str,
        current: Optional[int] = None,
        total: Optional[int] = None,
    ) -> None:
        self.status_label.setText(message)
        if current is not None and total:
            self.progress_bar.setRange(0, total)
            self.progress_bar.setValue(current)
            self.progress_bar.setTextVisible(True)
        else:
            self.progress_bar.setRange(0, 0)
            self.progress_bar.setTextVisible(False)

    def set_ready(self, message: str = "Ready") -> None:
        self.status_label.setText(message)
        self.progress_bar.setRange(0, 1)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(False)
        self.cancel_abstracts_btn.setVisible(False)
        self.cancel_pdfs_btn.setVisible(False)

    def show_cancel_abstracts(self, visible: bool) -> None:
        self.cancel_abstracts_btn.setVisible(visible)

    def show_cancel_pdfs(self, visible: bool) -> None:
        self.cancel_pdfs_btn.setVisible(visible)

    def _set_log_visible(self, visible: bool) -> None:
        self.log_view.setVisible(visible)
        self.toggle_btn.setText("Hide log" if visible else "Show log")
        self.toggle_btn.setArrowType(
            Qt.ArrowType.DownArrow if visible else Qt.ArrowType.RightArrow
        )
