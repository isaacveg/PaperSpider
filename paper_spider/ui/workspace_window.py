# Copyright 2026 Isaacveg
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#     http://www.apache.org/licenses/LICENSE-2.0

from __future__ import annotations

import os
import subprocess
import sys
from typing import List, Optional

from PyQt6.QtCore import QRect, QSize, Qt, QThreadPool, QTimer, QUrl
from PyQt6.QtGui import QDesktopServices, QGuiApplication, QKeySequence, QShortcut
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QDialog,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSplitter,
    QSpinBox,
    QStyle,
    QStyleOptionButton,
    QStackedWidget,
    QTableView,
    QVBoxLayout,
    QWidget,
)

from ..conferences import available_conferences
from ..filtering import FilterConfig
from ..storage import PaperStorage
from ..workspace_service import DownloadBatchResult, PaperLoadResult, WorkspaceService
from .dataset_dialog import DatasetDialog
from .export_dialog import ExportDialog
from .paper_table_model import PaperTableModel
from .settings_dialog import SettingsDialog
from .theme import apply_theme
from .workspace_view_helpers import (
    paper_id_for_row,
    reconcile_selected_ids,
    summarize_rows,
)
from .workspace_widgets import CollapsibleLogPanel, DetailsPanel, EmptyStateWidget, SummaryStrip, TopBar
from .workers import CancelToken, Worker


class FilterRow(QFrame):
    def __init__(self, parent: Optional[QWidget] = None, default_role: str = "Include") -> None:
        super().__init__(parent)
        self.setObjectName("filterRuleCard")
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        layout = QVBoxLayout()
        layout.setContentsMargins(5, 5, 5, 5)

        self.enable_checkbox = QCheckBox()
        self.enable_checkbox.setChecked(True)

        self.field_combo = QComboBox()
        for label, value in (
            ("Any field", "all"),
            ("Title", "title"),
            ("Category", "category"),
            ("Authors", "authors"),
            ("Abstract", "abstract"),
            ("Keywords", "keywords"),
        ):
            self.field_combo.addItem(label, value)
        self.field_combo.setMinimumWidth(104)
        self.field_combo.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        self.mode_combo = QComboBox()
        self.mode_combo.addItem("contains", "contains")
        self.mode_combo.addItem("does not contain", "not_contains")
        self.mode_combo.setMinimumWidth(116)
        self.mode_combo.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        self.role_combo = QComboBox()
        for label, value in (
            ("Include", "must"),
            ("Prefer", "should"),
            ("Exclude", "must not"),
        ):
            self.role_combo.addItem(label, value)
        self.role_combo.setObjectName("filterRoleCombo")
        self.role_combo.setMinimumWidth(100)
        self.role_combo.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        role_value = {
            "include": "must",
            "prefer": "should",
            "exclude": "must not",
        }.get(default_role.casefold(), default_role.casefold().replace("_", " "))
        role_index = self.role_combo.findData(role_value)
        if role_index >= 0:
            self.role_combo.setCurrentIndex(role_index)
        self.role_combo.setToolTip(
            "Include = required, Prefer = optional, Exclude = remove matches"
        )

        self.text_edit = QLineEdit()
        self.text_edit.setPlaceholderText("keyword, author, title...")
        self.text_edit.setMinimumWidth(64)

        self.remove_btn = QPushButton("x")
        self.remove_btn.setObjectName("compactDeleteButton")
        self.remove_btn.setToolTip("Remove this rule")
        self.remove_btn.setFixedWidth(22)

        self.sentence_row = QWidget()
        sentence_layout = QHBoxLayout()
        sentence_layout.setContentsMargins(0, 0, 0, 0)
        sentence_layout.setSpacing(4)
        sentence_layout.addWidget(self.enable_checkbox)
        sentence_layout.addWidget(self.role_combo)
        self.sentence_label = QLabel("papers where")
        self.sentence_label.setObjectName("filterSentenceLabel")
        sentence_layout.addWidget(self.sentence_label)
        sentence_layout.addStretch(1)
        sentence_layout.addWidget(self.remove_btn)
        self.sentence_row.setLayout(sentence_layout)

        self.criteria_row = QWidget()
        criteria_layout = QHBoxLayout()
        criteria_layout.setContentsMargins(0, 0, 0, 0)
        criteria_layout.setSpacing(4)
        criteria_layout.addWidget(self.field_combo, stretch=3)
        criteria_layout.addWidget(self.mode_combo, stretch=3)
        criteria_layout.addWidget(self.text_edit, stretch=4)
        self.criteria_row.setLayout(criteria_layout)

        layout.addWidget(self.sentence_row)
        layout.addWidget(self.criteria_row)

        self.setLayout(layout)

    def config(self) -> FilterConfig:
        return FilterConfig(
            enabled=self.enable_checkbox.isChecked(),
            field=str(self.field_combo.currentData()),
            mode=str(self.mode_combo.currentData()),
            role=str(self.role_combo.currentData()),
            value=self.text_edit.text().strip(),
        )


class SelectHeaderView(QHeaderView):
    def paintSection(self, painter, rect: QRect, logicalIndex: int) -> None:
        super().paintSection(painter, rect, logicalIndex)
        if logicalIndex != 1 or self.model() is None:
            return
        state = self.model().headerData(
            1,
            Qt.Orientation.Horizontal,
            Qt.ItemDataRole.CheckStateRole,
        )
        option = QStyleOptionButton()
        option.state = QStyle.StateFlag.State_Enabled
        if state == Qt.CheckState.Checked:
            option.state |= QStyle.StateFlag.State_On
        elif state == Qt.CheckState.PartiallyChecked:
            option.state |= QStyle.StateFlag.State_NoChange
        else:
            option.state |= QStyle.StateFlag.State_Off
        indicator = self.style().subElementRect(
            QStyle.SubElement.SE_CheckBoxIndicator,
            option,
            self,
        )
        option.rect = QRect(
            rect.center().x() - indicator.width() // 2,
            rect.center().y() - indicator.height() // 2,
            indicator.width(),
            indicator.height(),
        )
        self.style().drawControl(QStyle.ControlElement.CE_CheckBox, option, painter, self)


class WorkspaceWindow(QMainWindow):
    def __init__(self, conf=None, storage: Optional[PaperStorage] = None) -> None:
        super().__init__()
        self.conf = conf
        self.storage = storage
        self.base_dir: Optional[str] = None
        self.thread_pool = QThreadPool()
        self.service = WorkspaceService()
        self.available_conf_map = {conf.slug: conf for conf in available_conferences()}
        self._all_rows: List[dict] = []
        self._filtered_rows: List[dict] = []
        self._current_rows: List[dict] = []
        self.filter_rows: List[FilterRow] = []
        self.abstract_cancel_token: Optional[CancelToken] = None
        self.pdf_cancel_token: Optional[CancelToken] = None
        self._selected_paper_ids: set[str] = set()
        self._rendering_rows = False
        self._empty_action = "dataset"
        self._rows_loading = False
        self._pending_row_reload = False
        self._pending_row_refresh = False
        self.setWindowTitle("PaperSpider Workspace")
        self._build_ui()
        apply_theme(self)
        self._refresh_status()
        if self.storage:
            self._load_papers(force_refresh=True)

    def _build_ui(self) -> None:
        root = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(8, 8, 8, 8)

        self.quick_filter_edit = QLineEdit()
        self.quick_filter_edit.setObjectName("quickFilterEdit")
        self.quick_filter_edit.setClearButtonEnabled(True)
        self.quick_filter_edit.setPlaceholderText("Search papers")
        self.quick_filter_edit.setMaximumWidth(280)
        self.summary_strip = SummaryStrip()
        self.top_bar = TopBar(
            self,
            include_window_controls=True,
            summary_widget=self.summary_strip,
            search_widget=self.quick_filter_edit,
        )
        self.top_bar.settings_clicked.connect(self._open_settings)
        self.top_bar.dataset_clicked.connect(self._open_dataset_dialog)
        self.quick_filter_shortcut = QShortcut(QKeySequence.StandardKey.Find, self)
        self.quick_filter_shortcut.activated.connect(self._focus_quick_filter)
        self.quick_filter_timer = QTimer(self)
        self.quick_filter_timer.setSingleShot(True)
        self.quick_filter_timer.setInterval(180)
        self.quick_filter_timer.timeout.connect(self._apply_quick_filter)
        self.quick_filter_edit.textChanged.connect(self._schedule_quick_filter)
        layout.addWidget(self.top_bar)

        filter_panel = QFrame()
        filter_panel.setObjectName("filterSidebar")
        filter_panel.setFrameShape(QFrame.Shape.StyledPanel)
        filter_panel.setMinimumWidth(340)
        filter_panel.setMaximumWidth(400)
        filter_panel_layout = QVBoxLayout()
        filter_panel_layout.setContentsMargins(8, 0, 12, 0)
        filter_title = QLabel("Filters")
        filter_title.setObjectName("filterTitleLabel")
        filter_panel_layout.addWidget(filter_title)

        self.filter_hint_label = QLabel(
            "Include rules must match. Prefer rules can contribute to a minimum. "
            "Exclude rules remove matches."
        )
        self.filter_hint_label.setObjectName("filterHintLabel")
        self.filter_hint_label.setWordWrap(True)
        filter_panel_layout.addWidget(self.filter_hint_label)

        self.add_filter_btn = QPushButton("Add rule")
        self.add_filter_btn.setObjectName("secondaryButton")
        self.add_filter_btn.setToolTip("Add an Include rule")
        self.add_filter_btn.clicked.connect(lambda: self._add_filter())
        self.apply_filter_btn = QPushButton("Apply")
        self.apply_filter_btn.setObjectName("primaryButton")
        self.apply_filter_btn.clicked.connect(self._load_papers)
        self.clear_filter_btn = QPushButton("Clear")
        self.clear_filter_btn.setObjectName("secondaryButton")
        self.clear_filter_btn.clicked.connect(self._clear_filters)
        self.should_spin = QSpinBox()
        self.should_spin.setRange(0, 10)
        self.should_spin.setValue(0)
        self.should_spin.setToolTip("Require at least N Prefer rules to match")
        filter_panel_layout.addWidget(self.add_filter_btn)
        self.min_preferred_row = QWidget()
        self.min_preferred_row.setObjectName("minPreferredRow")
        self.min_should_row = self.min_preferred_row
        min_should_layout = QHBoxLayout()
        min_should_layout.setContentsMargins(0, 0, 0, 0)
        self.min_preferred_label = QLabel("Minimum preferred matches")
        min_should_layout.addWidget(self.min_preferred_label)
        min_should_layout.addWidget(self.should_spin)
        self.min_preferred_row.setLayout(min_should_layout)
        filter_panel_layout.addWidget(self.min_preferred_row)

        filter_buttons = QHBoxLayout()
        filter_buttons.addWidget(self.apply_filter_btn)
        filter_buttons.addWidget(self.clear_filter_btn)
        filter_panel_layout.addLayout(filter_buttons)

        filter_container = QWidget()
        self.filter_layout = QVBoxLayout()
        self.filter_layout.setContentsMargins(0, 0, 0, 0)
        self.filter_layout.setSpacing(6)
        self.filter_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        filter_container.setLayout(self.filter_layout)
        self.filter_scroll = QScrollArea()
        self.filter_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.filter_scroll.setWidgetResizable(True)
        self.filter_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.filter_scroll.setWidget(filter_container)
        filter_panel_layout.addWidget(self.filter_scroll, stretch=1)
        filter_panel.setLayout(filter_panel_layout)

        self.paper_model = PaperTableModel(self)
        self.paper_model.selection_changed.connect(self._on_model_selection_changed)
        self.table = QTableView()
        self.table.setModel(self.paper_model)
        self.table.verticalHeader().hide()
        self.table.setIconSize(QSize(35, 16))
        self.table.setHorizontalHeader(SelectHeaderView(Qt.Orientation.Horizontal, self.table))
        header = self.table.horizontalHeader()
        header.setStretchLastSection(False)
        header.setSectionsClickable(True)
        header.sectionClicked.connect(self._toggle_header_selection)
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        self.table.setColumnWidth(4, 220)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableView.SelectionMode.SingleSelection)
        self.table.clicked.connect(lambda index: self._update_details(index.row()))
        self.table.doubleClicked.connect(self._on_table_double_clicked)
        self.table.selectionModel().currentRowChanged.connect(
            lambda current, _previous: self._update_details(current.row())
        )

        self.empty_state = EmptyStateWidget()
        self.empty_state.primary_clicked.connect(self._handle_empty_state_action)
        self.table_stack = QStackedWidget()
        self.table_stack.addWidget(self.empty_state)
        self.table_stack.addWidget(self.table)

        self.action_layout = QHBoxLayout()
        self.selection_controls = QWidget()
        self.selection_controls.setObjectName("selectionControls")
        selection_layout = QHBoxLayout()
        selection_layout.setContentsMargins(0, 0, 0, 0)
        selection_layout.setSpacing(4)
        self.invert_btn = QPushButton("Invert")
        self.invert_btn.setObjectName("secondaryButton")
        self.invert_btn.clicked.connect(self._invert_selection)
        selection_layout.addWidget(self.invert_btn)
        self.selection_controls.setLayout(selection_layout)
        self.abstract_btn = QPushButton("Download abstracts")
        self.abstract_btn.setObjectName("secondaryButton")
        self.abstract_btn.clicked.connect(self._download_abstracts)
        self.pdf_btn = QPushButton("Download PDFs")
        self.pdf_btn.setObjectName("primaryButton")
        self.pdf_btn.clicked.connect(self._download_pdfs)
        self.bib_btn = QPushButton("Export Bib")
        self.bib_btn.setObjectName("secondaryButton")
        self.bib_btn.clicked.connect(self._export_bibtex)
        self.export_btn = QPushButton("Export selected")
        self.export_btn.setObjectName("primaryButton")
        self.export_btn.clicked.connect(self._open_export_dialog)

        self.action_layout.addWidget(self.selection_controls)
        self.action_layout.addSpacing(12)
        self.action_layout.addWidget(self.abstract_btn)
        self.action_layout.addWidget(self.pdf_btn)
        self.action_layout.addWidget(self.bib_btn)
        self.action_layout.addWidget(self.export_btn)
        self.action_layout.addStretch()

        center_panel = QWidget()
        center_layout = QVBoxLayout()
        center_layout.setContentsMargins(0, 0, 0, 0)
        center_layout.addWidget(self.table_stack, stretch=1)
        center_layout.addLayout(self.action_layout)
        center_panel.setLayout(center_layout)

        self.details_panel = DetailsPanel()
        self.details_panel.setMinimumWidth(360)
        self.details_panel.download_abstract_clicked.connect(self._download_current_abstract)
        self.details_panel.open_pdf_clicked.connect(self._open_current_pdf)
        self.details_panel.copy_bib_clicked.connect(self._copy_current_bibtex)
        self.details_panel.reveal_pdf_clicked.connect(self._reveal_current_pdf)
        self.details_panel.reveal_bib_clicked.connect(self._reveal_current_bib)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(8)
        splitter.addWidget(filter_panel)
        splitter.addWidget(center_panel)
        splitter.addWidget(self.details_panel)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setStretchFactor(2, 0)
        splitter.setSizes([360, 780, 420])
        layout.addWidget(splitter, stretch=1)

        self.log_panel = CollapsibleLogPanel()
        self.log_panel.cancel_abstracts_clicked.connect(self._cancel_abstract_download)
        self.log_panel.cancel_pdfs_clicked.connect(self._cancel_pdf_download)
        self.log_view = self.log_panel.log_view
        self.status_label = self.log_panel.status_label
        layout.addWidget(self.log_panel)

        root.setLayout(layout)
        self.setCentralWidget(root)

        self._add_filter()
        self._update_summary()
        self._update_empty_state()

    def _open_file(self, path: str) -> None:
        if not os.path.exists(path):
            self._log(f"Missing file: {path}")
            return
        QDesktopServices.openUrl(QUrl.fromLocalFile(path))

    def _reveal_in_folder(self, path: str) -> None:
        if not os.path.exists(path):
            self._log(f"Missing file: {path}")
            return
        if sys.platform == "darwin":
            subprocess.run(["open", "-R", path], check=False)
        elif os.name == "nt":
            subprocess.run(["explorer", "/select,", path], check=False)
        else:
            subprocess.run(["xdg-open", os.path.dirname(path)], check=False)

    def _log(self, message: str) -> None:
        self.log_panel.append_log(message)
        progress = self._parse_progress_message(message)
        if progress:
            current, total = progress
            self.log_panel.set_busy(self.status_label.text(), current, total)

    def _parse_progress_message(self, message: str) -> Optional[tuple[int, int]]:
        if not message.startswith("[") or "/" not in message:
            return None
        prefix = message.split("]", 1)[0].lstrip("[")
        parts = prefix.split("/", 1)
        if len(parts) != 2:
            return None
        try:
            current = int(parts[0])
            total = int(parts[1])
        except ValueError:
            return None
        return current, total

    def _selected_count(self) -> int:
        return len(reconcile_selected_ids(self._current_rows, self._selected_paper_ids))

    def _update_summary(self) -> None:
        rows_for_summary = self._all_rows if self._all_rows else self._current_rows
        filtered_count = None
        visible_count = None
        if self._all_rows:
            filtered_count = len(self._filtered_rows)
            visible_count = len(self._current_rows)
        self.summary_strip.set_summary(
            summarize_rows(rows_for_summary),
            self._selected_count(),
            filtered_count=filtered_count,
            visible_count=visible_count,
        )

    def _update_empty_state(self) -> None:
        if not self.storage or not self.conf:
            self._empty_action = "dataset"
            self.empty_state.set_content(
                "Choose a dataset to start",
                "Select a base folder, conference, and year before fetching papers.",
                "Choose dataset",
            )
            self.table_stack.setCurrentWidget(self.empty_state)
            return
        if not self._all_rows:
            self._empty_action = "dataset"
            self.empty_state.set_content(
                "Fetch this dataset",
                "Open Datasets and fetch the paper list before browsing papers.",
                "Open datasets",
            )
            self.table_stack.setCurrentWidget(self.empty_state)
            return
        if not self._current_rows:
            if self.quick_filter_edit.text().strip():
                self._empty_action = "clear_quick_filter"
                self.empty_state.set_content(
                    "No papers match the quick filter",
                    "Clear the quick filter or try a broader keyword.",
                    "Clear search",
                )
                self.table_stack.setCurrentWidget(self.empty_state)
                return
            self._empty_action = "clear_filters"
            self.empty_state.set_content(
                "No papers match the current filters",
                "Try clearing filters or lowering the minimum Prefer match count.",
                "Clear filters",
            )
            self.table_stack.setCurrentWidget(self.empty_state)
            return
        self.table_stack.setCurrentWidget(self.table)

    def _handle_empty_state_action(self) -> None:
        if self._empty_action == "fetch":
            self._fetch_list()
        elif self._empty_action == "clear_filters":
            self._clear_filters()
        elif self._empty_action == "clear_quick_filter":
            self.quick_filter_edit.clear()
        else:
            self._open_dataset_dialog()

    def _capture_selected_ids(self) -> None:
        self._selected_paper_ids = self.paper_model.selected_ids()
        self._selected_paper_ids = reconcile_selected_ids(
            self._current_rows,
            self._selected_paper_ids,
        )

    def _on_model_selection_changed(self) -> None:
        if self._rendering_rows:
            return
        self._selected_paper_ids = self.paper_model.selected_ids()
        self._update_summary()

    def _current_row(self) -> Optional[dict]:
        row_idx = self.table.currentIndex().row()
        if row_idx < 0 or row_idx >= len(self._current_rows):
            return None
        return self._current_rows[row_idx]

    def _update_details(self, row_idx: Optional[int] = None) -> None:
        if row_idx is None:
            row = self._current_row()
        elif 0 <= row_idx < len(self._current_rows):
            row = self._current_rows[row_idx]
        else:
            row = None
        self.details_panel.set_row(row)

    def _focus_row(self, row_idx: int) -> None:
        if 0 <= row_idx < len(self._current_rows):
            self.table.setCurrentIndex(self.paper_model.index(row_idx, 1))
            self._update_details(row_idx)

    def _copy_bibtex_for_row(self, row: dict) -> None:
        bibtex = row.get("bibtex")
        bib_path = row.get("bib_path")
        if not bibtex and bib_path and os.path.exists(bib_path):
            with open(bib_path, "r", encoding="utf-8") as f:
                bibtex = f.read()
        if bibtex:
            QGuiApplication.clipboard().setText(bibtex)
            if bib_path:
                self._log(f"Copied bibtex: {bib_path}")
            else:
                self._log("Copied bibtex to clipboard")

    def _download_current_abstract(self) -> None:
        row = self._current_row()
        abstract = row.get("abstract") if row else None
        if abstract:
            QGuiApplication.clipboard().setText(str(abstract))
            self.details_panel.set_feedback("Abstract copied to clipboard.")
            self._log("Copied abstract to clipboard")
        elif row:
            self._download_abstracts_for_rows([row])

    def _open_current_pdf(self) -> None:
        row = self._current_row()
        pdf_path = row.get("pdf_path") if row else None
        if pdf_path:
            self._open_file(pdf_path)
        elif row:
            self._download_pdfs_for_rows([row])

    def _copy_current_bibtex(self) -> None:
        row = self._current_row()
        if row:
            if row.get("bibtex") or row.get("bib_path"):
                self._copy_bibtex_for_row(row)
                self.details_panel.set_feedback("BibTeX copied to clipboard.")
            else:
                self._export_bibtex_for_rows([row])

    def _reveal_current_pdf(self) -> None:
        row = self._current_row()
        pdf_path = row.get("pdf_path") if row else None
        if pdf_path:
            self._reveal_in_folder(pdf_path)

    def _reveal_current_bib(self) -> None:
        row = self._current_row()
        bib_path = row.get("bib_path") if row else None
        if bib_path:
            self._reveal_in_folder(bib_path)

    def _cancel_abstract_download(self) -> None:
        if self.abstract_cancel_token:
            self.abstract_cancel_token.cancel()
            self._log("Canceling abstract download...")

    def _cancel_pdf_download(self) -> None:
        if self.pdf_cancel_token:
            self.pdf_cancel_token.cancel()
            self._log("Canceling PDF download...")

    def _refresh_download_controls(self, fallback: str = "Ready") -> None:
        abstract_running = self.abstract_cancel_token is not None
        pdf_running = self.pdf_cancel_token is not None
        self.log_panel.show_cancel_abstracts(abstract_running)
        self.log_panel.show_cancel_pdfs(pdf_running)
        if abstract_running and pdf_running:
            self.log_panel.set_busy("Downloading abstracts and PDFs...")
        elif abstract_running:
            self.log_panel.set_busy("Downloading abstracts...")
        elif pdf_running:
            self.log_panel.set_busy("Downloading PDFs...")
        else:
            self.log_panel.set_ready(fallback)

    def _ensure_ready(self) -> bool:
        if self.storage and self.conf:
            return True
        QMessageBox.warning(self, "Missing", "Please choose a dataset first.")
        return False

    def _start_worker(self, fn, on_done, on_error, *args) -> None:
        worker = Worker(fn, *args)
        worker.signals.log.connect(self._log)
        worker.signals.finished.connect(on_done)
        worker.signals.error.connect(on_error)
        self.thread_pool.start(worker)

    def _refresh_status(self) -> None:
        if not self.conf or not self.storage:
            self.top_bar.set_dataset("No dataset selected")
            self.status_label.setText("No dataset loaded")
            self._update_empty_state()
            self._update_summary()
            return
        count = self.storage.count_papers()
        self.top_bar.set_dataset(f"{self.conf.name} {self.storage.year}")
        self.status_label.setText(
            f"Loaded: {self.conf.name} {self.storage.year} (papers: {count})"
        )
        self._update_empty_state()
        self._update_summary()

    def _open_settings(self) -> None:
        dialog = SettingsDialog(self)
        result = dialog.exec()
        apply_theme(self)
        if result != QDialog.DialogCode.Accepted:
            return
        if self.conf:
            self.conf.request_delay = dialog.request_delay_ms() / 1000.0

    def _open_dataset_dialog(self) -> None:
        dialog = DatasetDialog(self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        selection = dialog.selection()
        if not selection:
            return
        conf = self.available_conf_map.get(selection.conf_slug)
        if not conf:
            QMessageBox.warning(self, "Error", "Conference not available")
            return
        conf.request_delay = selection.request_delay_ms / 1000.0
        self.conf = conf
        self.base_dir = selection.base_dir
        self.storage = PaperStorage(self.base_dir, conf.slug, selection.year)
        self._all_rows = []
        self._filtered_rows = []
        self._current_rows = []
        self._selected_paper_ids.clear()
        self.details_panel.set_row(None)
        self._refresh_status()
        if selection.fetch_after_select:
            self._fetch_list()
        else:
            self._load_papers(force_refresh=True)

    def _fetch_list(self) -> None:
        if not self._ensure_ready():
            return
        self._set_rows_loading(True, "Fetching paper list...")
        self._start_worker(
            self._fetch_list_task,
            self._on_fetch_done,
            self._on_worker_error,
            self.conf,
            self.storage,
        )
        self._log("Fetching paper list...")

    def _fetch_list_task(self, conf, storage: PaperStorage, log=None) -> int:
        return self.service.fetch_list(conf, storage)

    def _on_fetch_done(self, count: int) -> None:
        self._log(f"Loaded {count} papers")
        QMessageBox.information(self, "Done", f"Loaded {count} papers")
        self._set_rows_loading(False)
        self._refresh_status()
        self._load_papers(force_refresh=True)

    def _add_filter(self, default_role: str = "Include") -> None:
        row = FilterRow(default_role=default_role)
        row.remove_btn.clicked.connect(lambda: self._remove_filter(row))
        row.text_edit.returnPressed.connect(lambda: self._load_papers())
        row.enable_checkbox.toggled.connect(
            lambda _checked: self._update_min_preferred_visibility()
        )
        row.role_combo.currentIndexChanged.connect(
            lambda _index: self._update_min_preferred_visibility()
        )
        row.text_edit.textChanged.connect(
            lambda _text: self._update_min_preferred_visibility()
        )
        self.filter_rows.append(row)
        self.filter_layout.addWidget(row)
        self._update_min_preferred_visibility()

    def _remove_filter(self, row: FilterRow) -> None:
        if row in self.filter_rows:
            self.filter_rows.remove(row)
        row.setParent(None)
        row.deleteLater()
        self._update_min_preferred_visibility()

    def _clear_filters(self) -> None:
        for row in list(self.filter_rows):
            self._remove_filter(row)
        self._add_filter()
        self._load_papers()

    def _filter_configs(self) -> List[FilterConfig]:
        configs = []
        for row in self.filter_rows:
            config = row.config()
            if not config.enabled or not config.value:
                continue
            configs.append(config)
        return configs

    def _current_filter_state(self) -> tuple[List[FilterConfig], int]:
        configs = self._filter_configs()
        should_count = sum(1 for cfg in configs if cfg.role == "should")
        self.should_spin.setRange(0, should_count)
        if self.should_spin.value() > should_count:
            self.should_spin.setValue(should_count)
        return configs, self.should_spin.value()

    def _update_min_preferred_visibility(self) -> None:
        prefer_count = sum(
            1 for config in self._filter_configs() if config.role == "should"
        )
        self.should_spin.setRange(0, prefer_count)
        self.min_preferred_row.setVisible(prefer_count > 0)

    def _set_rows_loading(self, loading: bool, message: Optional[str] = None) -> None:
        self._rows_loading = loading
        self.table.setEnabled(not loading)
        self.apply_filter_btn.setEnabled(not loading)
        self.clear_filter_btn.setEnabled(not loading)
        self.abstract_btn.setEnabled(not loading)
        self.pdf_btn.setEnabled(not loading)
        self.bib_btn.setEnabled(not loading)
        self.export_btn.setEnabled(not loading)
        self.quick_filter_edit.setEnabled(not loading)
        self.invert_btn.setEnabled(not loading)
        if loading:
            self.status_label.setText(message or "Loading papers...")
            self.log_panel.set_busy(message or "Loading papers...")
        else:
            self._refresh_download_controls()
            self._refresh_status()

    def _load_papers(self, force_refresh: bool = False) -> None:
        self._capture_selected_ids()
        if not self.storage:
            self._all_rows = []
            self._filtered_rows = []
            self.paper_model.set_rows([], selected_ids=set())
            self._current_rows = []
            self._selected_paper_ids.clear()
            self.details_panel.set_row(None)
            self._update_summary()
            self._update_empty_state()
            return
        if self._rows_loading:
            self._pending_row_reload = True
            self._pending_row_refresh = self._pending_row_refresh or force_refresh
            return

        configs, min_should_match = self._current_filter_state()
        cached_rows = None if force_refresh or not self._all_rows else self._all_rows
        action = "Loading papers..." if cached_rows is None else "Applying filters..."
        self._set_rows_loading(True, action)
        self._start_worker(
            self._load_papers_task,
            self._on_load_papers_done,
            self._on_load_papers_error,
            self.storage,
            cached_rows,
            configs,
            min_should_match,
        )

    def _load_papers_task(
        self,
        storage: PaperStorage,
        cached_rows: Optional[List[dict]],
        configs: List[FilterConfig],
        min_should_match: int,
        log=None,
    ) -> PaperLoadResult:
        return self.service.load_papers(storage, cached_rows, configs, min_should_match)

    def _schedule_quick_filter(self) -> None:
        self.quick_filter_timer.start()

    def _focus_quick_filter(self) -> None:
        self.quick_filter_edit.setFocus(Qt.FocusReason.ShortcutFocusReason)
        self.quick_filter_edit.selectAll()

    def _apply_quick_filter(self) -> None:
        self._capture_selected_ids()
        self._render_rows(self._quick_filtered_rows())

    def _prepare_quick_search(self, rows: List[dict]) -> None:
        for row in rows:
            row["_quick_search"] = " ".join(
                str(row.get(key) or "")
                for key in (
                    "title",
                    "category_text",
                    "authors_text",
                    "abstract",
                    "keywords_text",
                )
            ).casefold()

    def _quick_filtered_rows(self) -> List[dict]:
        rows = self._filtered_rows if self._all_rows else []
        query = self.quick_filter_edit.text().strip().casefold()
        if not query:
            return list(rows)
        terms = query.split()
        return [row for row in rows if self._row_matches_quick_filter(row, terms)]

    def _row_matches_quick_filter(self, row: dict, terms: List[str]) -> bool:
        haystack = row.get("_quick_search")
        if not haystack:
            self._prepare_quick_search([row])
            haystack = row.get("_quick_search") or ""
        return all(term in haystack for term in terms)

    def _render_rows(self, rows: List[dict]) -> None:
        self._selected_paper_ids = reconcile_selected_ids(
            rows,
            self._selected_paper_ids,
        )
        self._current_rows = rows
        self._rendering_rows = True
        try:
            self.paper_model.set_rows(
                rows,
                selected_ids=self._selected_paper_ids,
            )
        finally:
            self._rendering_rows = False
        self._update_summary()
        self._update_empty_state()
        self._update_details(self.table.currentIndex().row())

    def _finish_pending_row_load(self) -> None:
        if not self._pending_row_reload:
            return
        force_refresh = self._pending_row_refresh
        self._pending_row_reload = False
        self._pending_row_refresh = False
        self._load_papers(force_refresh=force_refresh)

    def _on_load_papers_done(self, result: PaperLoadResult) -> None:
        self._set_rows_loading(False)
        if not self.storage or result.storage_key != self.storage.paths.db_path:
            self._finish_pending_row_load()
            return
        self._all_rows = result.all_rows
        self._prepare_quick_search(self._all_rows)
        self._filtered_rows = result.filtered_rows
        self._render_rows(self._quick_filtered_rows())
        self._log(
            f"Showing {len(self._current_rows)} of {len(result.filtered_rows)} filtered papers "
            f"({len(result.all_rows)} total)"
        )
        self._finish_pending_row_load()

    def _on_load_papers_error(self, message: str) -> None:
        self._set_rows_loading(False)
        QMessageBox.critical(self, "Error", message)
        self._log(f"Error: {message}")
        self._finish_pending_row_load()

    def _on_table_double_clicked(self, index) -> None:
        row_idx = index.row()
        if row_idx >= len(self._current_rows):
            return
        self._update_details(row_idx)
        row = self._current_rows[row_idx]
        pdf_path = row.get("pdf_path")
        if pdf_path:
            self._open_file(str(pdf_path))

    def _toggle_header_selection(self, section: int) -> None:
        if section != 1:
            return
        checked = self.paper_model.selection_state() != Qt.CheckState.Checked
        self._set_selection_state(checked)

    def _set_selection_state(self, checked: bool) -> None:
        visible_ids = {paper_id_for_row(row) for row in self._current_rows}
        if checked:
            self._selected_paper_ids.update(visible_ids)
        else:
            self._selected_paper_ids.difference_update(visible_ids)
        self.paper_model.set_selected_ids(self._selected_paper_ids)
        self._update_summary()

    def _invert_selection(self) -> None:
        for row in self._current_rows:
            paper_id = paper_id_for_row(row)
            if paper_id in self._selected_paper_ids:
                self._selected_paper_ids.discard(paper_id)
            else:
                self._selected_paper_ids.add(paper_id)
        self.paper_model.set_selected_ids(self._selected_paper_ids)
        self._update_summary()

    def _selected_rows(self) -> List[dict]:
        self._capture_selected_ids()
        selected = []
        for row in self._current_rows:
            if paper_id_for_row(row) in self._selected_paper_ids:
                selected.append(row)
        return selected

    def _open_export_dialog(self) -> None:
        selected = self._selected_rows()
        if not selected:
            QMessageBox.information(self, "Select", "Please select papers first.")
            return
        dialog = ExportDialog(selected, self)
        dialog.exec()

    def _download_abstracts(self) -> None:
        if self.abstract_cancel_token:
            QMessageBox.information(
                self,
                "Busy",
                "Abstract download already running. Use the cancel control in the status bar.",
            )
            return
        if not self._ensure_ready():
            return
        selected = self._selected_rows()
        if not selected:
            QMessageBox.information(self, "Select", "Please select papers first.")
            return
        self._download_abstracts_for_rows(selected)

    def _download_abstracts_for_rows(self, rows: List[dict]) -> None:
        if not self._ensure_ready():
            return
        if self.abstract_cancel_token:
            QMessageBox.information(self, "Busy", "Abstract download already running.")
            return
        self.abstract_cancel_token = CancelToken()
        self._refresh_download_controls()
        self.log_panel.set_busy("Downloading abstracts...", 0, len(rows))
        self.log_panel.show_cancel_abstracts(True)
        self._start_worker(
            self._download_abstracts_task,
            self._on_abstracts_done,
            self._on_abstracts_error,
            self.conf,
            self.storage,
            rows,
            self.abstract_cancel_token,
        )
        self._log("Downloading abstracts...")

    def _download_abstracts_task(
        self,
        conf,
        storage: PaperStorage,
        rows: List[dict],
        cancel: CancelToken,
        log=None,
    ) -> DownloadBatchResult:
        return self.service.download_abstracts(conf, storage, rows, cancel.cancelled, log=log)

    def _on_abstracts_done(self, result: DownloadBatchResult) -> None:
        cancelled = result.cancelled or (
            self.abstract_cancel_token.cancelled() if self.abstract_cancel_token else False
        )
        self.abstract_cancel_token = None
        self._refresh_download_controls()
        self._apply_download_updates(result.updated_rows)
        self._show_download_result("abstracts", result, cancelled)

    def _download_pdfs(self) -> None:
        if self.pdf_cancel_token:
            QMessageBox.information(
                self,
                "Busy",
                "PDF download already running. Use the cancel control in the status bar.",
            )
            return
        if not self._ensure_ready():
            return
        selected = self._selected_rows()
        if not selected:
            QMessageBox.information(self, "Select", "Please select papers first.")
            return
        self._download_pdfs_for_rows(selected)

    def _download_pdfs_for_rows(self, rows: List[dict]) -> None:
        if not self._ensure_ready():
            return
        if self.pdf_cancel_token:
            QMessageBox.information(self, "Busy", "PDF download already running.")
            return
        self.pdf_cancel_token = CancelToken()
        self._refresh_download_controls()
        self.log_panel.set_busy("Downloading PDFs...", 0, len(rows))
        self.log_panel.show_cancel_pdfs(True)
        self._start_worker(
            self._download_pdfs_task,
            self._on_pdfs_done,
            self._on_pdfs_error,
            self.conf,
            self.storage,
            rows,
            self.pdf_cancel_token,
        )
        self._log("Downloading PDFs...")

    def _download_pdfs_task(
        self,
        conf,
        storage: PaperStorage,
        rows: List[dict],
        cancel: CancelToken,
        log=None,
    ) -> DownloadBatchResult:
        return self.service.download_pdfs(conf, storage, rows, cancel.cancelled, log=log)

    def _on_pdfs_done(self, result: DownloadBatchResult) -> None:
        cancelled = result.cancelled or (
            self.pdf_cancel_token.cancelled() if self.pdf_cancel_token else False
        )
        self.pdf_cancel_token = None
        self._refresh_download_controls()
        self._apply_download_updates(result.updated_rows)
        self._show_download_result("PDFs", result, cancelled)

    def _export_bibtex(self) -> None:
        if not self._ensure_ready():
            return
        selected = self._selected_rows()
        if not selected:
            QMessageBox.information(self, "Select", "Please select papers first.")
            return
        self._export_bibtex_for_rows(selected)

    def _export_bibtex_for_rows(self, rows: List[dict]) -> None:
        if not self._ensure_ready():
            return
        self.log_panel.set_busy("Exporting bibtex...", 0, len(rows))
        self._start_worker(
            self._export_bibtex_task,
            self._on_bibtex_done,
            self._on_worker_error,
            self.conf,
            self.storage,
            rows,
        )
        self._log("Exporting bibtex...")

    def _export_bibtex_task(self, conf, storage: PaperStorage, rows: List[dict], log=None) -> int:
        return self.service.export_bibtex(conf, storage, rows, log=log)

    def _on_bibtex_done(self, count: int) -> None:
        self._refresh_download_controls()
        QMessageBox.information(self, "Done", f"Exported {count} bibtex files")
        self._load_papers(force_refresh=True)

    def _apply_download_updates(self, updated_rows: List[dict]) -> None:
        if not updated_rows:
            self._update_summary()
            self._update_details(self.table.currentIndex().row())
            return
        active_id = paper_id_for_row(self._current_row() or {})
        updates = {paper_id_for_row(row): row for row in updated_rows if paper_id_for_row(row)}
        for rows in (self._all_rows, self._filtered_rows, self._current_rows):
            for row in rows:
                paper_id = paper_id_for_row(row)
                if paper_id in updates:
                    row.clear()
                    row.update(updates[paper_id])
                    self._prepare_quick_search([row])
        self.paper_model.notify_rows_changed(set(updates))
        self.paper_model.set_selected_ids(self._selected_paper_ids)
        self._update_summary()
        if active_id:
            for row_idx, row in enumerate(self._current_rows):
                if paper_id_for_row(row) == active_id:
                    self._focus_row(row_idx)
                    break
            else:
                self._update_details(self.table.currentIndex().row())
        else:
            self._update_details(self.table.currentIndex().row())

    def _show_download_result(
        self,
        artifact_name: str,
        result: DownloadBatchResult,
        cancelled: bool,
    ) -> None:
        if cancelled:
            title = "Canceled"
        elif result.failures:
            title = "Finished with issues"
        else:
            title = "Done"
        parts = [f"Downloaded {result.succeeded} {artifact_name}"]
        if result.skipped:
            parts.append(f"Skipped {result.skipped} already available")
        if result.failures:
            parts.append(f"Failed {len(result.failures)}")
            for failure in result.failures[:5]:
                self._log(f"Failed {artifact_name}: {failure.title} ({failure.message})")
        QMessageBox.information(self, title, "\n".join(parts))

    def _on_worker_error(self, message: str) -> None:
        self._set_rows_loading(False)
        self._refresh_download_controls("Error")
        QMessageBox.critical(self, "Error", message)
        self._log(f"Error: {message}")

    def _on_abstracts_error(self, message: str) -> None:
        if self.abstract_cancel_token:
            self.abstract_cancel_token = None
        self._refresh_download_controls("Error")
        QMessageBox.critical(self, "Error", message)
        self._log(f"Error: {message}")

    def _on_pdfs_error(self, message: str) -> None:
        if self.pdf_cancel_token:
            self.pdf_cancel_token = None
        self._refresh_download_controls("Error")
        QMessageBox.critical(self, "Error", message)
        self._log(f"Error: {message}")
