# Copyright 2026 Isaacveg
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#     http://www.apache.org/licenses/LICENSE-2.0

from __future__ import annotations

import os
import subprocess
import sys
from dataclasses import dataclass
from functools import partial
from typing import Callable, Dict, List, Optional

from PyQt6.QtCore import (
    QSize,
    Qt,
    QThreadPool,
    QTimer,
    QUrl,
)
from PyQt6.QtGui import (
    QDesktopServices,
    QGuiApplication,
    QKeySequence,
    QShortcut,
)
from PyQt6.QtWidgets import (
    QDialog,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMainWindow,
    QMenu,
    QPushButton,
    QSplitter,
    QStackedWidget,
    QTableView,
    QVBoxLayout,
    QWidget,
)

from ..conferences import available_conferences
from ..datasets import move_dataset_to_trash, scan_datasets
from ..filtering import FilterConfig, filter_paper_rows, matches_terms, query_terms, search_text
from ..storage import PaperStorage
from ..workspace_service import (
    DownloadBatchResult,
    PaperLoadResult,
    WorkspaceService,
)
from .app_settings import app_settings, base_dir as settings_base_dir, request_delay_ms
from .dataset_dialog import DatasetDialog
from .dialog_utils import (
    ask_confirmation,
    show_error,
    show_information,
    show_warning,
)
from .export_dialog import ExportDialog
from .filter_dialog import FilterDialog
from .i18n import selected_count, tr
from .paper_table_model import (
    ABSTRACT_COLUMN,
    CHECK_COLUMN,
    PAPER_COLUMN,
    PDF_COLUMN,
    PaperTableModel,
    row_available,
    row_title,
)
from .settings_dialog import SettingsDialog
from .table_delegates import (
    CenteredCheckBoxDelegate,
    CenteredStatusDelegate,
    PaperTableView,
    PaperTitleDelegate,
    SelectHeaderView,
    paper_row_height,
)
from .theme import apply_theme, selected_theme
from .workspace_view_helpers import paper_id_for_row, reconcile_selected_ids
from .workspace_widgets import (
    SIDEBAR_MAX_WIDTH,
    SIDEBAR_MIN_WIDTH,
    SIDEBAR_RAIL_WIDTH,
    SIDEBAR_SNAP_WIDTH,
    AppSidebar,
    CollapsibleLogPanel,
    DetailsPanel,
    EmptyStateWidget,
    WorkspaceHeader,
)
from .workers import CancelToken, Worker

CLOSE_WAIT_MS = 5000


@dataclass(frozen=True)
class _DownloadKind:
    service_method: str
    artifact: str
    busy_text: str
    already_running: str
    canceling: str


_DOWNLOADS: Dict[str, _DownloadKind] = {
    "abstracts": _DownloadKind(
        service_method="download_abstracts",
        artifact="abstracts",
        busy_text="Downloading abstracts...",
        already_running="Abstract download already running.",
        canceling="Canceling abstract download...",
    ),
    "pdfs": _DownloadKind(
        service_method="download_pdfs",
        artifact="PDFs",
        busy_text="Downloading PDFs...",
        already_running="PDF download already running.",
        canceling="Canceling PDF download...",
    ),
}


class WorkspaceWindow(QMainWindow):
    def __init__(self, conf=None, storage: Optional[PaperStorage] = None) -> None:
        super().__init__()
        self.conf = conf
        self.storage = storage
        self.base_dir: Optional[str] = storage.base_dir if storage else None
        self.thread_pool = QThreadPool()
        self.service = WorkspaceService()
        self.available_conf_map = {conf.slug: conf for conf in available_conferences()}
        self._all_rows: List[dict] = []
        self._filtered_rows: List[dict] = []
        self._current_rows: List[dict] = []
        self._download_tokens: Dict[str, Optional[CancelToken]] = {
            kind: None for kind in _DOWNLOADS
        }
        self._download_progress: Dict[str, tuple[int, int]] = {}
        self.fetch_cancel_token: Optional[CancelToken] = None
        self._empty_action = "dataset"
        self._rows_loading = False
        self._pending_row_reload = False
        self._pending_row_refresh = False
        self._sort_column: Optional[int] = None
        self._sort_order = Qt.SortOrder.AscendingOrder
        self._sidebar_width = 280
        self._persist_session = False
        self._idle_message: Optional[str] = None
        self.setWindowTitle(tr("PaperSpider Workspace"))
        self._build_ui()
        self.resize(1480, 900)
        apply_theme(self)
        self._sync_theme_palette()
        self._style_hints = None
        app = QGuiApplication.instance()
        if app is not None:
            self._style_hints = app.styleHints()
            self._style_hints.colorSchemeChanged.connect(
                self._on_color_scheme_changed
            )
        self._refresh_status()
        if self.storage:
            self._load_papers(force_refresh=True)

    # ------------------------------------------------------------------ UI

    def _build_ui(self) -> None:
        self._applied_filters: List[FilterConfig] = []
        self._min_should_match = 0

        root = QWidget()
        root_layout = QHBoxLayout()
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        self.sidebar = AppSidebar()
        self.sidebar.settings_clicked.connect(self._open_settings)
        self.sidebar.add_dataset_clicked.connect(self._open_dataset_dialog)
        self.sidebar.dataset_clicked.connect(self._select_dataset)
        self.sidebar.filters_clicked.connect(self._open_filter_dialog)
        self.sidebar.all_papers_clicked.connect(self._show_all_papers)
        self.sidebar.toggle_compact_clicked.connect(self._toggle_sidebar_compact)
        self.sidebar.open_dataset_folder.connect(self._open_dataset_folder)
        self.sidebar.delete_dataset.connect(self._delete_dataset)
        self.sidebar.refresh_dataset.connect(self._refresh_dataset)

        right_panel = QWidget()
        right_panel.setObjectName("rightPanel")
        right_layout = QVBoxLayout()
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)

        self.header = WorkspaceHeader()
        self.header.filter_clicked.connect(self._open_filter_dialog)
        self.header.filter_removed.connect(self._remove_filter_at)
        self.header.details_toggle_clicked.connect(self._show_details)
        self.quick_filter_edit = self.header.quick_filter_edit
        self.quick_filter_shortcut = QShortcut(QKeySequence.StandardKey.Find, self)
        self.quick_filter_shortcut.activated.connect(self._focus_quick_filter)
        self.quick_filter_timer = QTimer(self)
        self.quick_filter_timer.setSingleShot(True)
        self.quick_filter_timer.setInterval(180)
        self.quick_filter_timer.timeout.connect(self._apply_quick_filter)
        self.quick_filter_edit.textChanged.connect(self._schedule_quick_filter)

        self.paper_model = PaperTableModel(self)
        self.paper_model.selection_changed.connect(self._on_model_selection_changed)
        self.table = PaperTableView()
        self.table.setModel(self.paper_model)
        self.table.setItemDelegateForColumn(
            CHECK_COLUMN, CenteredCheckBoxDelegate(self.table)
        )
        self.table.setItemDelegateForColumn(
            PAPER_COLUMN, PaperTitleDelegate(self.table)
        )
        self.table.setItemDelegateForColumn(
            ABSTRACT_COLUMN, CenteredStatusDelegate(self.table)
        )
        self.table.setItemDelegateForColumn(
            PDF_COLUMN, CenteredStatusDelegate(self.table)
        )
        self.table.verticalHeader().hide()
        self.table.setIconSize(QSize(16, 16))
        self.table.setShowGrid(False)
        self.table.setFrameShape(QFrame.Shape.NoFrame)
        self.table.setLineWidth(0)
        self.table.setMidLineWidth(0)
        self.table.setHorizontalHeader(
            SelectHeaderView(Qt.Orientation.Horizontal, self.table)
        )
        header = self.table.horizontalHeader()
        header.setStretchLastSection(False)
        header.setSectionsClickable(True)
        header.sectionClicked.connect(self._toggle_header_selection)
        header.setSectionResizeMode(CHECK_COLUMN, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(PAPER_COLUMN, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(ABSTRACT_COLUMN, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(PDF_COLUMN, QHeaderView.ResizeMode.Fixed)
        header.resizeSection(CHECK_COLUMN, 44)
        header.resizeSection(ABSTRACT_COLUMN, 58)
        header.resizeSection(PDF_COLUMN, 46)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableView.SelectionMode.SingleSelection)
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._show_table_context_menu)
        self.table.clicked.connect(self._on_table_clicked)
        self.table.doubleClicked.connect(self._on_table_double_clicked)
        self.table.row_activated.connect(self._open_row_pdf)
        self.table.select_all_requested.connect(
            lambda: self._set_selection_state(True)
        )
        self.table.selectionModel().currentRowChanged.connect(
            lambda current, _previous: self._update_details(current.row())
        )

        self.empty_state = EmptyStateWidget()
        self.empty_state.primary_clicked.connect(self._handle_empty_state_action)
        self.table_stack = QStackedWidget()
        self.table_stack.setObjectName("tableStack")
        self.table_stack.setFrameShape(QFrame.Shape.NoFrame)
        self.table_stack.setLineWidth(0)
        self.table_stack.addWidget(self.empty_state)
        self.table_stack.addWidget(self.table)

        self.action_bar = QWidget()
        self.action_bar.setObjectName("workspaceActionBar")
        self.action_layout = QHBoxLayout()
        self.action_layout.setContentsMargins(0, 10, 0, 12)
        self.action_layout.setSpacing(8)
        self.selected_label = QLabel(selected_count(0))
        self.selected_label.setObjectName("mutedLabel")
        self.invert_btn = QPushButton(tr("Invert"))
        self.invert_btn.setObjectName("linkButton")
        self.invert_btn.clicked.connect(self._invert_selection)
        self.abstract_btn = QPushButton(tr("Download abstracts"))
        self.abstract_btn.setObjectName("actionButton")
        self.abstract_btn.clicked.connect(self._download_abstracts)
        self.pdf_btn = QPushButton(tr("Download PDFs"))
        self.pdf_btn.setObjectName("actionButton")
        self.pdf_btn.clicked.connect(self._download_pdfs)
        self.export_btn = QPushButton(tr("Export"))
        self.export_btn.setObjectName("actionButton")
        self.export_btn.clicked.connect(self._open_export_dialog)
        self.action_layout.addWidget(self.selected_label)
        self.action_layout.addWidget(self.invert_btn)
        self.action_layout.addStretch(1)
        self.action_layout.addWidget(self.abstract_btn)
        self.action_layout.addWidget(self.pdf_btn)
        self.action_layout.addWidget(self.export_btn)
        self.action_bar.setLayout(self.action_layout)

        center_panel = QWidget()
        center_layout = QVBoxLayout()
        center_layout.setContentsMargins(8, 18, 8, 0)
        center_layout.setSpacing(14)
        center_layout.addWidget(self.header)
        center_layout.addWidget(self.table_stack, stretch=1)
        center_layout.addWidget(self.action_bar)
        center_panel.setLayout(center_layout)

        self.details_panel = DetailsPanel()
        self.details_panel.abstract_action_clicked.connect(
            self._download_current_abstract
        )
        self.details_panel.open_pdf_clicked.connect(self._open_current_pdf)
        self.details_panel.copy_bib_clicked.connect(self._copy_current_bibtex)
        self.details_panel.reveal_pdf_clicked.connect(self._reveal_current_pdf)
        self.details_panel.close_clicked.connect(self._hide_details)

        self.workspace_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.workspace_splitter.setHandleWidth(1)
        self.workspace_splitter.addWidget(center_panel)
        self.workspace_splitter.addWidget(self.details_panel)
        self.workspace_splitter.setCollapsible(0, False)
        self.workspace_splitter.setCollapsible(1, True)
        self.workspace_splitter.setStretchFactor(0, 1)
        self.workspace_splitter.setStretchFactor(1, 0)
        self.workspace_splitter.setSizes([760, 460])

        self.log_panel = CollapsibleLogPanel()
        self.log_panel.cancel_clicked.connect(self._cancel_active_download)
        self.log_view = self.log_panel.log_view
        self.status_label = self.log_panel.status_label

        right_layout.addWidget(self.workspace_splitter, stretch=1)
        right_layout.addWidget(self.log_panel)
        right_panel.setLayout(right_layout)

        self.main_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.main_splitter.setObjectName("mainSplitter")
        self.main_splitter.setHandleWidth(2)
        self.main_splitter.addWidget(self.sidebar)
        self.main_splitter.addWidget(right_panel)
        self.main_splitter.setCollapsible(0, False)
        self.main_splitter.setCollapsible(1, False)
        self.main_splitter.setStretchFactor(0, 0)
        self.main_splitter.setStretchFactor(1, 1)
        self.main_splitter.setSizes([280, 1200])
        self.main_splitter.splitterMoved.connect(self._on_main_splitter_moved)
        root_layout.addWidget(self.main_splitter)
        root.setLayout(root_layout)
        self.setCentralWidget(root)

        self._refresh_dataset_sidebar()
        self.header.set_filters([])
        self._update_summary()
        self._update_empty_state()
        self._refresh_status()

    # ------------------------------------------------------- session state

    def restore_session(self) -> None:
        """Restore window layout and the last dataset, and persist them on close."""

        self._persist_session = True
        settings = app_settings()
        geometry = settings.value("window/geometry")
        if geometry:
            self.restoreGeometry(geometry)
        for key, splitter in (
            ("window/main_splitter", self.main_splitter),
            ("window/workspace_splitter", self.workspace_splitter),
        ):
            state = settings.value(key)
            if state:
                splitter.restoreState(state)
        if settings.value("window/details_hidden", False, type=bool):
            self._hide_details()
        if self.storage is not None:
            return
        conf_slug, _, year_text = str(
            settings.value("session/last_dataset", "") or ""
        ).partition(":")
        base = settings_base_dir(settings)
        if not (conf_slug in self.available_conf_map and year_text.isdigit() and base):
            return
        db_path = os.path.join(base, conf_slug, year_text, "papers.sqlite")
        if os.path.exists(db_path):
            self._select_dataset(conf_slug, int(year_text), base)

    def _save_session(self) -> None:
        settings = app_settings()
        settings.setValue("window/geometry", self.saveGeometry())
        settings.setValue("window/main_splitter", self.main_splitter.saveState())
        settings.setValue(
            "window/workspace_splitter", self.workspace_splitter.saveState()
        )
        settings.setValue("window/details_hidden", self.details_panel.isHidden())
        if self.conf and self.storage:
            settings.setValue(
                "session/last_dataset", f"{self.conf.slug}:{self.storage.year}"
            )
        else:
            settings.remove("session/last_dataset")

    def closeEvent(self, event) -> None:
        if self._network_task_running() and not ask_confirmation(
            self,
            tr("Quit PaperSpider?"),
            tr("Tasks are still running. Cancel them and quit?"),
            confirm_text=tr("Quit"),
            cancel_text=tr("Keep running"),
        ):
            event.ignore()
            return
        self._cancel_all_tasks(quiet=True)
        if self._persist_session:
            self._save_session()
        self.thread_pool.waitForDone(CLOSE_WAIT_MS)
        super().closeEvent(event)

    # ------------------------------------------------------------ helpers

    def _open_file(self, path: str) -> None:
        if not os.path.exists(path):
            self._log(tr("Missing file: {path}", path=path))
            return
        QDesktopServices.openUrl(QUrl.fromLocalFile(path))

    def _reveal_in_folder(self, path: str) -> None:
        if not os.path.exists(path):
            self._log(tr("Missing file: {path}", path=path))
            return
        if sys.platform == "darwin":
            subprocess.run(["open", "-R", path], check=False)
        elif os.name == "nt":
            subprocess.run(["explorer", "/select,", path], check=False)
        else:
            subprocess.run(["xdg-open", os.path.dirname(path)], check=False)

    def _log(self, message: str) -> None:
        self.log_panel.append_log(message)

    def _notify(self, message: str) -> None:
        """Show a non-blocking result message in the task bar."""

        self._log(message)
        self._idle_message = message
        if not self._network_task_running() and not self._rows_loading:
            self.log_panel.set_ready(message)

    def _update_summary(self) -> None:
        if self.storage and self.conf:
            total = (
                len(self._all_rows) if self._all_rows else len(self._current_rows)
            )
            self.header.set_counts(total, len(self._current_rows))
        selected = len(self._selected_paper_ids)
        hidden = selected - self.paper_model.visible_selected_count()
        self.selected_label.setText(selected_count(selected, hidden))
        self._update_action_buttons()

    def _update_action_buttons(self) -> None:
        idle = not self._rows_loading
        has_selection = bool(self._selected_paper_ids)
        for button in (self.abstract_btn, self.pdf_btn, self.export_btn):
            button.setEnabled(idle and has_selection)
        self.invert_btn.setEnabled(idle and bool(self._current_rows))

    def _update_empty_state(self) -> None:
        if not self.storage or not self.conf:
            self._empty_action = "dataset"
            self.empty_state.set_content(
                tr("Choose a dataset to start"),
                tr(
                    "Select a base folder, conference, and year before fetching papers."
                ),
                tr("Choose dataset"),
            )
            self.table_stack.setCurrentWidget(self.empty_state)
            return
        if not self._all_rows:
            self._empty_action = "dataset"
            self.empty_state.set_content(
                tr("Fetch this dataset"),
                tr(
                    "Open Datasets and fetch the paper list before browsing papers."
                ),
                tr("Open datasets"),
            )
            self.table_stack.setCurrentWidget(self.empty_state)
            return
        if not self._current_rows:
            if self.quick_filter_edit.text().strip():
                self._empty_action = "clear_quick_filter"
                self.empty_state.set_content(
                    tr("No papers match the quick filter"),
                    tr("Clear the quick filter or try a broader keyword."),
                    tr("Clear search"),
                )
                self.table_stack.setCurrentWidget(self.empty_state)
                return
            self._empty_action = "clear_filters"
            self.empty_state.set_content(
                tr("No papers match the current filters"),
                tr(
                    "Try clearing filters or lowering the minimum Prefer match count."
                ),
                tr("Clear filters"),
            )
            self.table_stack.setCurrentWidget(self.empty_state)
            return
        self.table_stack.setCurrentWidget(self.table)

    def _handle_empty_state_action(self) -> None:
        if self._empty_action == "clear_filters":
            self._clear_applied_filters()
        elif self._empty_action == "clear_quick_filter":
            self.quick_filter_edit.clear()
        else:
            self._open_dataset_dialog()

    # ----------------------------------------------------------- selection

    @property
    def _selected_paper_ids(self) -> set[str]:
        return self.paper_model.selected_ids()

    @_selected_paper_ids.setter
    def _selected_paper_ids(self, paper_ids: set[str]) -> None:
        self.paper_model.set_selected_ids(paper_ids)

    def _on_model_selection_changed(self) -> None:
        self._update_summary()

    def _toggle_header_selection(self, section: int) -> None:
        if section == CHECK_COLUMN:
            checked = self.paper_model.selection_state() != Qt.CheckState.Checked
            self._set_selection_state(checked)
            return
        self._cycle_sort(section)

    def _set_selection_state(self, checked: bool) -> None:
        visible_ids = {paper_id_for_row(row) for row in self._current_rows}
        selected = self._selected_paper_ids
        if checked:
            selected |= visible_ids
        else:
            selected -= visible_ids
        self._selected_paper_ids = selected

    def _invert_selection(self) -> None:
        visible_ids = {paper_id_for_row(row) for row in self._current_rows}
        self._selected_paper_ids = self._selected_paper_ids ^ visible_ids

    def _selected_rows(self) -> List[dict]:
        selected = self._selected_paper_ids
        rows = self._all_rows or self._current_rows
        return [row for row in rows if paper_id_for_row(row) in selected]

    # ------------------------------------------------------------- sorting

    def _cycle_sort(self, column: int) -> None:
        if self._sort_column != column:
            self._sort_column = column
            self._sort_order = Qt.SortOrder.AscendingOrder
        elif self._sort_order == Qt.SortOrder.AscendingOrder:
            self._sort_order = Qt.SortOrder.DescendingOrder
        else:
            self._sort_column = None
        self.paper_model.set_sort_marker(self._sort_column, self._sort_order)
        self._render_rows(self._quick_filtered_rows())

    def _sorted(self, rows: List[dict]) -> List[dict]:
        column = self._sort_column
        if column is None:
            return rows
        descending = self._sort_order == Qt.SortOrder.DescendingOrder

        def title_key(row: dict) -> str:
            return row_title(row).casefold()

        if column == PAPER_COLUMN:
            return sorted(rows, key=title_key, reverse=descending)
        return sorted(
            rows,
            key=lambda row: (row_available(row, column) == descending, title_key(row)),
        )

    # ------------------------------------------------------------- details

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
            self.table.setCurrentIndex(self.paper_model.index(row_idx, PAPER_COLUMN))
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
                self._log(tr("Copied bibtex: {path}", path=bib_path))
            else:
                self._log(tr("Copied bibtex to clipboard"))

    def _download_current_abstract(self) -> None:
        row = self._current_row()
        abstract = row.get("abstract") if row else None
        if abstract:
            QGuiApplication.clipboard().setText(str(abstract))
            self.details_panel.set_feedback(tr("Abstract copied to clipboard."))
            self._log(tr("Copied abstract to clipboard"))
        elif row:
            self._download_abstracts_for_rows([row])

    def _open_current_pdf(self) -> None:
        row = self._current_row()
        pdf_path = row.get("pdf_path") if row else None
        if pdf_path:
            self._open_file(pdf_path)
        elif row:
            self._download_pdfs_for_rows([row])

    def _copy_current_title(self) -> None:
        row = self._current_row()
        if row:
            QGuiApplication.clipboard().setText(row_title(row))
            self._notify(tr("Copied title to clipboard"))

    def _copy_current_bibtex(self) -> None:
        row = self._current_row()
        if not row:
            return
        if row.get("bibtex") or row.get("bib_path"):
            self._copy_bibtex_for_row(row)
            self.details_panel.set_feedback(tr("BibTeX copied to clipboard."))
            return
        self.log_panel.set_busy(tr("Fetching BibTeX..."), show_cancel=False)
        self._start_worker(
            self._fetch_bibtex_task,
            self._on_bibtex_fetched,
            self._on_bibtex_fetch_error,
            row,
        )

    def _fetch_bibtex_task(self, row: dict) -> dict:
        saved = self.service.save_bibtex(self.conf, self.storage, row)
        if not saved:
            raise RuntimeError(tr("BibTeX not found"))
        bibtex, file_path = saved
        return {
            "bibtex": bibtex,
            "paper_id": row["paper_id"],
            "bib_path": file_path,
            "db_path": self.storage.paths.db_path,
        }

    def _on_bibtex_fetched(self, result: dict) -> None:
        self._refresh_download_controls()
        QGuiApplication.clipboard().setText(result["bibtex"])
        if self.storage and self.storage.paths.db_path == result["db_path"]:
            refreshed = self.storage.get_paper(result["paper_id"])
            self._apply_download_updates([refreshed] if refreshed else [])
        self.details_panel.set_feedback(tr("BibTeX copied to clipboard."))
        self._log(tr("Copied bibtex to clipboard"))

    def _on_bibtex_fetch_error(self, message: str) -> None:
        self._refresh_download_controls("Error")
        self._report_error(message)

    def _reveal_current_pdf(self) -> None:
        row = self._current_row()
        pdf_path = row.get("pdf_path") if row else None
        if pdf_path:
            self._reveal_in_folder(pdf_path)

    def _show_table_context_menu(self, pos) -> None:
        index = self.table.indexAt(pos)
        if not index.isValid() or index.row() >= len(self._current_rows):
            return
        self._focus_row(index.row())
        row = self._current_rows[index.row()]
        has_pdf = bool(row.get("pdf_path"))
        checked = paper_id_for_row(row) in self._selected_paper_ids
        menu = QMenu(self)
        actions: Dict[object, Callable[[], None]] = {}

        def add(text: str, handler: Callable[[], None], enabled: bool = True) -> None:
            action = menu.addAction(text)
            action.setEnabled(enabled)
            actions[action] = handler

        add(
            tr("Unselect paper") if checked else tr("Select paper"),
            lambda: self.paper_model.toggle_checked(index.row()),
        )
        menu.addSeparator()
        add(tr("Open PDF") if has_pdf else tr("Download PDF"), self._open_current_pdf)
        add(tr("Show in folder"), self._reveal_current_pdf, has_pdf)
        add(
            tr("Copy abstract") if row.get("abstract") else tr("Download abstract"),
            self._download_current_abstract,
        )
        menu.addSeparator()
        add(tr("Copy title"), self._copy_current_title)
        add(tr("Copy BibTeX"), self._copy_current_bibtex)
        chosen = menu.exec(self.table.viewport().mapToGlobal(pos))
        handler = actions.get(chosen)
        if handler:
            handler()

    # --------------------------------------------------------------- tasks

    @property
    def abstract_cancel_token(self) -> Optional[CancelToken]:
        return self._download_tokens["abstracts"]

    @abstract_cancel_token.setter
    def abstract_cancel_token(self, token: Optional[CancelToken]) -> None:
        self._download_tokens["abstracts"] = token

    @property
    def pdf_cancel_token(self) -> Optional[CancelToken]:
        return self._download_tokens["pdfs"]

    @pdf_cancel_token.setter
    def pdf_cancel_token(self, token: Optional[CancelToken]) -> None:
        self._download_tokens["pdfs"] = token

    def _network_task_running(self) -> bool:
        return self.fetch_cancel_token is not None or any(
            token is not None for token in self._download_tokens.values()
        )

    def _cancel_all_tasks(self, quiet: bool = False) -> None:
        if self.fetch_cancel_token:
            self.fetch_cancel_token.cancel()
            if not quiet:
                self._log(tr("Canceling paper list fetch..."))
        for kind, token in self._download_tokens.items():
            if token:
                token.cancel()
                if not quiet:
                    self._log(tr(_DOWNLOADS[kind].canceling))

    def _cancel_active_download(self) -> None:
        self._cancel_all_tasks()

    def _refresh_download_controls(self, fallback: Optional[str] = None) -> None:
        running = [kind for kind, token in self._download_tokens.items() if token]
        if self.fetch_cancel_token is not None:
            self.log_panel.set_busy(tr("Fetching paper list..."))
        elif len(running) == 2:
            self.log_panel.set_busy(tr("Downloading abstracts and PDFs..."))
        elif running:
            self.log_panel.set_busy(tr(_DOWNLOADS[running[0]].busy_text))
        else:
            self.log_panel.set_ready(
                tr(fallback) if fallback else self._idle_message or tr("Ready")
            )
            return
        self._show_download_progress()

    def _show_download_progress(self) -> None:
        if not self._download_progress or self.fetch_cancel_token is not None:
            return
        current = sum(value for value, _total in self._download_progress.values())
        total = sum(total for _value, total in self._download_progress.values())
        self.log_panel.set_busy(self.status_label.text(), current, total)

    def _on_download_progress(self, kind: str, current: int, total: int) -> None:
        if self._download_tokens.get(kind) is None:
            return
        self._download_progress[kind] = (current, total)
        self._show_download_progress()

    def _ensure_ready(self) -> bool:
        if self.storage and self.conf:
            return True
        show_warning(self, tr("Missing"), tr("Please choose a dataset first."))
        return False

    def _start_worker(self, fn, on_done, on_error, *args, on_progress=None) -> None:
        worker = Worker(fn, *args)
        worker.signals.log.connect(self._log)
        worker.signals.finished.connect(on_done)
        worker.signals.error.connect(on_error)
        if on_progress is not None:
            worker.signals.progress.connect(on_progress)
        self.thread_pool.start(worker)

    def _refresh_status(self) -> None:
        if not self.conf or not self.storage:
            self.header.set_dataset("PaperSpider", tr("No dataset selected"))
            self.status_label.setText(tr("No dataset loaded"))
            self._update_empty_state()
            self._update_summary()
            return
        self.header.set_dataset(f"{self.conf.name} {self.storage.year}", "")
        self.sidebar.set_active_dataset(self.conf.slug, self.storage.year)
        self._update_empty_state()
        self._update_summary()

    # ------------------------------------------------------ theme & layout

    def _open_settings(self) -> None:
        dialog = SettingsDialog(self)
        result = dialog.exec()
        apply_theme(self)
        self._refresh_theme_icons()
        if result != QDialog.DialogCode.Accepted:
            return
        if self.conf:
            self.conf.request_delay = dialog.request_delay_ms() / 1000.0

    def _on_color_scheme_changed(self, *_args) -> None:
        settings = app_settings()
        if selected_theme(settings) != "System":
            return
        apply_theme(self, settings)
        self._refresh_theme_icons()

    def _refresh_theme_icons(self) -> None:
        self._sync_theme_palette()
        self.sidebar.refresh_icons()
        self.header.refresh_icons()
        self.details_panel.refresh_icons()
        self.paper_model.refresh_icons()
        paper_ids = {paper_id_for_row(row) for row in self.paper_model.rows()}
        if paper_ids:
            self.paper_model.notify_rows_changed(paper_ids)

    def _on_main_splitter_moved(self, *_args) -> None:
        """Snap the sidebar to the icon rail or the minimum expanded width."""

        width = self.sidebar.width()
        if SIDEBAR_RAIL_WIDTH < width < SIDEBAR_MIN_WIDTH:
            self._set_sidebar_width(
                SIDEBAR_RAIL_WIDTH if width < SIDEBAR_SNAP_WIDTH else SIDEBAR_MIN_WIDTH
            )
        elif width >= SIDEBAR_MIN_WIDTH:
            self._sidebar_width = width

    def _set_sidebar_width(self, width: int) -> None:
        total = max(1, sum(self.main_splitter.sizes()))
        width = min(SIDEBAR_MAX_WIDTH, max(SIDEBAR_RAIL_WIDTH, width))
        self.main_splitter.setSizes([width, max(1, total - width)])

    def _toggle_sidebar_compact(self) -> None:
        if self.sidebar.is_compact():
            self._set_sidebar_width(max(SIDEBAR_MIN_WIDTH, self._sidebar_width))
        else:
            self._sidebar_width = self.sidebar.width()
            self._set_sidebar_width(SIDEBAR_RAIL_WIDTH)

    def _hide_details(self) -> None:
        self.details_panel.hide()
        self.header.set_details_hidden(True)

    def _show_details(self) -> None:
        self.details_panel.show()
        self.header.set_details_hidden(False)
        total = max(1, sum(self.workspace_splitter.sizes()))
        details_width = min(460, max(360, total // 2))
        self.workspace_splitter.setSizes(
            [max(360, total - details_width), details_width]
        )

    def _sync_theme_palette(self) -> None:
        palette = self.palette()
        self.table.setPalette(palette)
        self.table.horizontalHeader().setPalette(palette)
        self.table.ensurePolished()
        self.table.verticalHeader().setDefaultSectionSize(
            paper_row_height(self.table.font())
        )
        self.table.viewport().update()

    # ------------------------------------------------------------ datasets

    def _open_dataset_folder(self, conf_slug: str, year: int) -> None:
        base = self._dataset_base_dir()
        path = os.path.join(base, conf_slug, str(year))
        if not os.path.isdir(path):
            show_warning(self, tr("Missing"), tr("Dataset folder not found."))
            return
        QDesktopServices.openUrl(QUrl.fromLocalFile(path))

    def _delete_dataset(self, conf_slug: str, year: int) -> None:
        base = self._dataset_base_dir()
        path = os.path.join(base, conf_slug, str(year))
        if not os.path.isdir(path):
            show_warning(self, tr("Missing"), tr("Dataset folder not found."))
            return
        if not ask_confirmation(
            self,
            tr("Delete dataset"),
            tr(
                "This removes all local files for this dataset and moves it "
                "to .trash. You will need to fetch it again. Continue?"
            ),
            confirm_text=tr("Confirm"),
            cancel_text=tr("Cancel"),
        ):
            return
        if not move_dataset_to_trash(base, path):
            show_error(self, tr("Error"), tr("Failed to delete dataset."))
            return
        if self._is_active_dataset(conf_slug, year):
            self.conf = None
            self.storage = None
            self._all_rows = []
            self._filtered_rows = []
            self._current_rows = []
            self.paper_model.set_rows([], selected_ids=set())
            self.details_panel.set_row(None)
        self._refresh_dataset_sidebar(base)
        self._refresh_status()
        self._notify(tr("Dataset deleted. Fetch it again to use it."))

    def _dataset_base_dir(self) -> str:
        if self.base_dir:
            return self.base_dir
        return settings_base_dir(app_settings())

    def _refresh_dataset_sidebar(self, base_dir: Optional[str] = None) -> None:
        base = base_dir or self._dataset_base_dir()
        if not base:
            self.sidebar.set_datasets([])
            return
        active = (
            (self.conf.slug, self.storage.year)
            if self.conf and self.storage
            else None
        )
        datasets = []
        for entry in scan_datasets(base):
            conf = self.available_conf_map.get(entry.conf_slug)
            datasets.append(
                {
                    "conf": entry.conf_slug,
                    "name": conf.name if conf else entry.conf_slug,
                    "year": entry.year,
                    "papers": entry.paper_count,
                    "selected": active == (entry.conf_slug, entry.year),
                }
            )
        self.sidebar.set_datasets(datasets)

    def _is_active_dataset(self, conf_slug: str, year: int) -> bool:
        return bool(
            self.conf
            and self.storage
            and self.conf.slug == conf_slug
            and self.storage.year == year
        )

    def _select_dataset(
        self,
        conf_slug: str,
        year: int,
        base_dir: Optional[str] = None,
        load: bool = True,
    ) -> None:
        conf = self.available_conf_map.get(conf_slug)
        if conf is None:
            show_warning(self, tr("Error"), tr("Conference not available"))
            return
        base = base_dir or self._dataset_base_dir()
        if not base:
            show_warning(self, tr("Missing"), tr("Please choose a base folder first."))
            return
        if self._is_active_dataset(conf_slug, year) and base == self.base_dir:
            return
        conf.request_delay = request_delay_ms(app_settings()) / 1000.0
        base_changed = base != self.base_dir
        self.conf = conf
        self.base_dir = base
        self.storage = PaperStorage(base, conf.slug, year)
        self._all_rows = []
        self._filtered_rows = []
        self._current_rows = []
        self.paper_model.set_rows([], selected_ids=set())
        self.details_panel.set_row(None)
        if base_changed or not self.sidebar.has_dataset(conf_slug, year):
            self._refresh_dataset_sidebar(base)
        self._refresh_status()
        if load:
            self._load_papers(force_refresh=True)

    def _open_dataset_dialog(self) -> None:
        dialog = DatasetDialog(
            self, conferences=list(self.available_conf_map.values())
        )
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        selection = dialog.selection()
        if not selection:
            return
        self._select_dataset(
            selection.conf_slug,
            selection.year,
            selection.base_dir,
            load=not selection.fetch_after_select,
        )
        if selection.fetch_after_select:
            self._fetch_list()

    def _refresh_dataset(self, conf_slug: str, year: int) -> None:
        if self._rows_loading:
            return
        self._select_dataset(conf_slug, year, load=False)
        self._fetch_list()

    def _fetch_list(self) -> None:
        if not self._ensure_ready():
            return
        self.fetch_cancel_token = CancelToken()
        self._set_rows_loading(True, tr("Fetching paper list..."))
        self.log_panel.show_cancel(True)
        self._start_worker(
            self._fetch_list_task,
            self._on_fetch_done,
            self._on_fetch_error,
            self.conf,
            self.storage,
            self.fetch_cancel_token,
        )
        self._log(tr("Fetching paper list..."))

    def _fetch_list_task(
        self, conf, storage: PaperStorage, cancel: CancelToken, log=None
    ) -> int:
        return self.service.fetch_list(conf, storage, cancel.cancelled)

    def _on_fetch_done(self, count: int) -> None:
        self.fetch_cancel_token = None
        self._set_rows_loading(False)
        self._refresh_dataset_sidebar()
        self._refresh_status()
        self._notify(tr("Loaded {count} papers", count=count))
        self._load_papers(force_refresh=True)

    def _on_fetch_error(self, message: str) -> None:
        token = self.fetch_cancel_token
        self.fetch_cancel_token = None
        self._set_rows_loading(False)
        if token is not None and token.cancelled():
            self._notify(tr("Paper list fetch canceled"))
        else:
            self._refresh_download_controls("Error")
            self._report_error(message)
        self._finish_pending_row_load()

    # ------------------------------------------------------------- filters

    def _open_filter_dialog(self) -> None:
        dialog = FilterDialog(
            self,
            configs=self._applied_filters,
            min_should_match=self._min_should_match,
        )
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        self._applied_filters = dialog.filter_configs()
        self._min_should_match = dialog.min_should_match()
        self.header.set_filters(self._applied_filters)
        self.sidebar.set_filter_count(len(self._applied_filters))
        self._load_papers()

    def _remove_filter_at(self, index: int) -> None:
        if not 0 <= index < len(self._applied_filters):
            return
        self._applied_filters.pop(index)
        self.header.set_filters(self._applied_filters)
        self.sidebar.set_filter_count(len(self._applied_filters))
        self._load_papers()

    def _clear_applied_filters(self) -> None:
        self._applied_filters = []
        self._min_should_match = 0
        self.header.set_filters([])
        self.sidebar.set_filter_count(0)
        self._load_papers()

    def _show_all_papers(self) -> None:
        self.quick_filter_edit.clear()
        self._clear_applied_filters()

    def _current_filter_state(self) -> tuple[List[FilterConfig], int]:
        should_count = sum(
            1 for config in self._applied_filters if config.role == "should"
        )
        return list(self._applied_filters), min(
            self._min_should_match, should_count
        )

    # ---------------------------------------------------------------- rows

    def _set_rows_loading(self, loading: bool, message: Optional[str] = None) -> None:
        self._rows_loading = loading
        self.table.setEnabled(not loading)
        self.quick_filter_edit.setEnabled(not loading)
        self.header.filter_btn.setEnabled(not loading)
        self._update_action_buttons()
        if loading:
            text = message or tr("Loading papers...")
            self.status_label.setText(text)
            self.log_panel.set_busy(text, show_cancel=False)
        else:
            self._refresh_download_controls()
            self._refresh_status()

    def _load_papers(self, force_refresh: bool = False) -> None:
        if not self.storage:
            self._all_rows = []
            self._filtered_rows = []
            self._current_rows = []
            self.paper_model.set_rows([], selected_ids=set())
            self.details_panel.set_row(None)
            self._update_summary()
            self._update_empty_state()
            return
        if self._rows_loading:
            self._pending_row_reload = True
            self._pending_row_refresh = self._pending_row_refresh or force_refresh
            return

        configs, min_should_match = self._current_filter_state()
        if not force_refresh and self._all_rows:
            self._filtered_rows = filter_paper_rows(
                self._all_rows, configs, min_should_match
            )
            self._render_rows(self._quick_filtered_rows())
            return
        self._set_rows_loading(True, tr("Loading papers..."))
        self._start_worker(
            self._load_papers_task,
            self._on_load_papers_done,
            self._on_load_papers_error,
            self.storage,
            configs,
            min_should_match,
        )

    def _load_papers_task(
        self,
        storage: PaperStorage,
        configs: List[FilterConfig],
        min_should_match: int,
        log=None,
    ) -> PaperLoadResult:
        result = self.service.load_papers(storage, None, configs, min_should_match)
        self._prepare_quick_search(result.all_rows)
        return result

    def _schedule_quick_filter(self) -> None:
        self.quick_filter_timer.start()

    def _focus_quick_filter(self) -> None:
        self.quick_filter_edit.setFocus(Qt.FocusReason.ShortcutFocusReason)
        self.quick_filter_edit.selectAll()

    def _apply_quick_filter(self) -> None:
        self._render_rows(self._quick_filtered_rows())

    def _prepare_quick_search(self, rows: List[dict]) -> None:
        for row in rows:
            row["_quick_search"] = search_text(row)

    def _quick_filtered_rows(self) -> List[dict]:
        rows = self._filtered_rows if self._all_rows else []
        terms = query_terms(self.quick_filter_edit.text())
        if terms:
            rows = [row for row in rows if self._row_matches_quick_filter(row, terms)]
        return self._sorted(list(rows))

    def _row_matches_quick_filter(self, row: dict, terms: List[str]) -> bool:
        haystack = row.get("_quick_search")
        if not haystack:
            self._prepare_quick_search([row])
            haystack = row.get("_quick_search") or ""
        return matches_terms(haystack, terms)

    def _render_rows(self, rows: List[dict]) -> None:
        current_id = paper_id_for_row(self._current_row() or {})
        self._current_rows = rows
        self.paper_model.set_rows(rows)
        row_idx = self.paper_model.row_for_paper(current_id) if current_id else -1
        if row_idx >= 0:
            index = self.paper_model.index(row_idx, PAPER_COLUMN)
            self.table.setCurrentIndex(index)
            self.table.scrollTo(index, QTableView.ScrollHint.EnsureVisible)
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
        self._filtered_rows = result.filtered_rows
        self.paper_model.set_selected_ids(
            reconcile_selected_ids(self._all_rows, self._selected_paper_ids)
        )
        self._render_rows(self._quick_filtered_rows())
        self._log(
            tr(
                "Showing {visible} of {filtered} filtered papers ({total} total)",
                visible=len(self._current_rows),
                filtered=len(result.filtered_rows),
                total=len(result.all_rows),
            )
        )
        self._finish_pending_row_load()

    def _on_load_papers_error(self, message: str) -> None:
        self._set_rows_loading(False)
        self._report_error(message)
        self._finish_pending_row_load()

    def _open_row_pdf(self, row_idx: int) -> None:
        if not 0 <= row_idx < len(self._current_rows):
            return
        self._update_details(row_idx)
        pdf_path = self._current_rows[row_idx].get("pdf_path")
        if pdf_path:
            self._open_file(str(pdf_path))

    def _on_table_double_clicked(self, index) -> None:
        self._open_row_pdf(index.row())

    def _on_table_clicked(self, index) -> None:
        if index.column() == CHECK_COLUMN:
            self.paper_model.toggle_checked(index.row())
        self._update_details(index.row())

    def _open_export_dialog(self) -> None:
        ExportDialog(self._selected_rows(), self).exec()

    # ----------------------------------------------------------- downloads

    def _download_abstracts(self) -> None:
        self._download_selected("abstracts")

    def _download_pdfs(self) -> None:
        self._download_selected("pdfs")

    def _download_abstracts_for_rows(self, rows: List[dict]) -> None:
        self._start_download("abstracts", rows)

    def _download_pdfs_for_rows(self, rows: List[dict]) -> None:
        self._start_download("pdfs", rows)

    def _download_selected(self, kind: str) -> None:
        self._start_download(kind, self._selected_rows())

    def _start_download(self, kind: str, rows: List[dict]) -> None:
        spec = _DOWNLOADS[kind]
        if self._download_tokens[kind]:
            show_information(self, tr("Busy"), tr(spec.already_running))
            return
        token = CancelToken()
        self._download_tokens[kind] = token
        self._download_progress[kind] = (0, len(rows))
        self._refresh_download_controls()
        self.log_panel.show_cancel(True)
        self._start_worker(
            self._download_task,
            partial(self._on_download_done, kind),
            partial(self._on_download_error, kind),
            kind,
            self.conf,
            self.storage,
            rows,
            token,
            on_progress=partial(self._on_download_progress, kind),
        )
        self._log(tr(spec.busy_text))

    def _download_task(
        self,
        kind: str,
        conf,
        storage: PaperStorage,
        rows: List[dict],
        cancel: CancelToken,
        log=None,
        progress=None,
    ) -> DownloadBatchResult:
        method = getattr(self.service, _DOWNLOADS[kind].service_method)
        return method(conf, storage, rows, cancel.cancelled, log=log, progress=progress)

    def _on_download_done(self, kind: str, result: DownloadBatchResult) -> None:
        token = self._download_tokens[kind]
        cancelled = result.cancelled or (token.cancelled() if token else False)
        self._download_tokens[kind] = None
        self._download_progress.pop(kind, None)
        self._refresh_download_controls()
        self._apply_download_updates(result.updated_rows)
        self._show_download_result(kind, result, cancelled)

    def _on_download_error(self, kind: str, message: str) -> None:
        self._download_tokens[kind] = None
        self._download_progress.pop(kind, None)
        self._refresh_download_controls("Error")
        self._report_error(message)

    def _apply_download_updates(self, updated_rows: List[dict]) -> None:
        if not updated_rows:
            self._update_summary()
            self._update_details(self.table.currentIndex().row())
            return
        active_id = paper_id_for_row(self._current_row() or {})
        updates = {paper_id_for_row(row): row for row in updated_rows}
        # Filtered and visible rows reference the same dicts as _all_rows.
        for row in self._all_rows or self._current_rows:
            update = updates.get(paper_id_for_row(row))
            if update is not None:
                row.clear()
                row.update(update)
                self._prepare_quick_search([row])
        self.paper_model.notify_rows_changed(set(updates))
        self._update_summary()
        row_idx = self.paper_model.row_for_paper(active_id) if active_id else -1
        if row_idx >= 0:
            self._focus_row(row_idx)
        else:
            self._update_details(self.table.currentIndex().row())

    def _show_download_result(
        self,
        kind: str,
        result: DownloadBatchResult,
        cancelled: bool,
    ) -> None:
        if cancelled:
            title = tr("Canceled")
        elif result.failures:
            title = tr("Finished with issues")
        else:
            title = tr("Done")
        artifact = tr(_DOWNLOADS[kind].artifact)
        parts = [
            tr(
                "Downloaded {count} {artifact}",
                count=result.succeeded,
                artifact=artifact,
            )
        ]
        if result.skipped:
            parts.append(tr("Skipped {count} already available", count=result.skipped))
        if result.failures:
            parts.append(tr("Failed {count}", count=len(result.failures)))
            for failure in result.failures:
                self._log(
                    tr(
                        "Failed {artifact}: {title} ({message})",
                        artifact=artifact,
                        title=failure.title,
                        message=failure.message,
                    )
                )
            self.log_panel.expand_log()
        self._notify(f"{title}: " + " · ".join(parts))

    def _report_error(self, message: str) -> None:
        show_error(self, tr("Error"), message)
        self._log(tr("Error: {message}", message=message))
