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

from PyQt6.QtCore import (
    QEvent,
    QRect,
    QSettings,
    QSize,
    Qt,
    QThreadPool,
    QTimer,
    QUrl,
)
from PyQt6.QtGui import (
    QColor,
    QDesktopServices,
    QFont,
    QFontMetrics,
    QGuiApplication,
    QIcon,
    QKeySequence,
    QPainter,
    QPalette,
    QPen,
    QShortcut,
)
from PyQt6.QtWidgets import (
    QApplication,
    QDialog,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMainWindow,
    QPushButton,
    QSplitter,
    QStackedWidget,
    QStyle,
    QStyledItemDelegate,
    QStyleOptionViewItem,
    QTableView,
    QVBoxLayout,
    QWidget,
)

from ..artifacts import (
    safe_filename,
    unique_artifact_path,
    write_text_artifact,
)
from ..conferences import available_conferences
from ..datasets import move_dataset_to_trash, scan_datasets
from ..filtering import FilterConfig
from ..storage import PaperStorage
from ..workspace_service import (
    DownloadBatchResult,
    PaperLoadResult,
    WorkspaceService,
    paper_from_row,
)
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
    AUTHORS_ROLE,
    CHECK_COLUMN,
    PAPER_COLUMN,
    PDF_COLUMN,
    PaperTableModel,
)
from .settings_dialog import SettingsDialog
from .theme import apply_theme, selected_theme
from .workspace_view_helpers import paper_id_for_row, reconcile_selected_ids
from .workspace_widgets import (
    AppSidebar,
    CollapsibleLogPanel,
    DetailsPanel,
    EmptyStateWidget,
    WorkspaceHeader,
)
from .workers import CancelToken, Worker


def _checkbox_rect(cell_rect: QRect) -> QRect:
    size = min(18, max(12, cell_rect.width() - 10), max(12, cell_rect.height() - 10))
    rect = QRect(0, 0, size, size)
    rect.moveCenter(cell_rect.center())
    return rect


def _draw_checkbox(
    painter,
    cell_rect: QRect,
    state: Qt.CheckState,
    accent: QColor,
    muted: QColor,
) -> None:
    box = _checkbox_rect(cell_rect)
    checked = state == Qt.CheckState.Checked
    partial = state == Qt.CheckState.PartiallyChecked
    painter.save()
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    painter.setPen(QPen(accent if (checked or partial) else muted, 1.3))
    painter.setBrush(accent if (checked or partial) else Qt.BrushStyle.NoBrush)
    painter.drawRoundedRect(box.adjusted(1, 1, -1, -1), 4, 4)
    if checked or partial:
        check_color = (
            QColor("#ffffff")
            if accent.lightness() < 150
            else QColor("#101712")
        )
        pen = QPen(check_color, 2)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)
        if checked:
            painter.drawLine(
                box.left() + 5,
                box.center().y(),
                box.left() + 8,
                box.bottom() - 5,
            )
            painter.drawLine(
                box.left() + 8,
                box.bottom() - 5,
                box.right() - 4,
                box.top() + 5,
            )
        else:
            painter.drawLine(
                box.left() + 5,
                box.center().y(),
                box.right() - 5,
                box.center().y(),
            )
    painter.restore()


class CenteredCheckBoxDelegate(QStyledItemDelegate):
    """Draw a theme-aware checkbox at the exact center of its table cell."""

    def paint(self, painter, option, index) -> None:
        view_option = QStyleOptionViewItem(option)
        self.initStyleOption(view_option, index)
        state = view_option.checkState
        view_option.features &= ~QStyleOptionViewItem.ViewItemFeature.HasCheckIndicator
        style = option.widget.style() if option.widget else QApplication.style()
        style.drawControl(
            QStyle.ControlElement.CE_ItemViewItem,
            view_option,
            painter,
            option.widget,
        )
        if option.state & QStyle.StateFlag.State_Selected:
            painter.fillRect(
                QRect(
                    option.rect.left(),
                    option.rect.top(),
                    3,
                    option.rect.height(),
                ),
                option.palette.color(QPalette.ColorRole.PlaceholderText),
            )
        _draw_checkbox(
            painter,
            option.rect,
            state,
            option.palette.color(QPalette.ColorRole.Link),
            option.palette.color(QPalette.ColorRole.PlaceholderText),
        )

    def editorEvent(self, event, model, option, index) -> bool:
        if not index.flags() & Qt.ItemFlag.ItemIsUserCheckable:
            return False
        if event.type() != QEvent.Type.KeyPress or event.key() not in (
            Qt.Key.Key_Space,
            Qt.Key.Key_Select,
        ):
            return False

        state = index.data(Qt.ItemDataRole.CheckStateRole)
        next_state = (
            Qt.CheckState.Unchecked
            if state == Qt.CheckState.Checked
            else Qt.CheckState.Checked
        )
        return model.setData(index, next_state, Qt.ItemDataRole.CheckStateRole)


class PaperTitleDelegate(QStyledItemDelegate):
    """Paint a bold paper title with a muted author line below it."""

    def sizeHint(self, option, index) -> QSize:
        hint = super().sizeHint(option, index)
        hint.setHeight(max(50, hint.height() + 18))
        return hint

    def paint(self, painter, option, index) -> None:
        view_option = QStyleOptionViewItem(option)
        self.initStyleOption(view_option, index)
        view_option.text = ""
        style = option.widget.style() if option.widget else QApplication.style()
        style.drawControl(
            QStyle.ControlElement.CE_ItemViewItem,
            view_option,
            painter,
            option.widget,
        )
        title = str(index.data(Qt.ItemDataRole.DisplayRole) or "")
        authors = str(index.data(AUTHORS_ROLE) or "")
        selected = bool(option.state & QStyle.StateFlag.State_Selected)
        text_color = option.palette.color(
            QPalette.ColorRole.HighlightedText
            if selected
            else QPalette.ColorRole.Text
        )
        muted_color = QColor(text_color)
        muted_color.setAlpha(190)
        rect = option.rect.adjusted(10, 5, -10, -5)
        title_font = QFont(option.font)
        title_font.setBold(True)
        title_font.setPixelSize(16)
        author_font = QFont(option.font)
        author_font.setPixelSize(12)
        metrics = QFontMetrics(title_font)
        painter.save()
        painter.setFont(title_font)
        painter.setPen(text_color)
        title_text = metrics.elidedText(
            title, Qt.TextElideMode.ElideRight, rect.width()
        )
        painter.drawText(
            QRect(rect.left(), rect.top(), rect.width(), 22),
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
            title_text,
        )
        if authors:
            painter.setFont(author_font)
            painter.setPen(muted_color)
            author_metrics = QFontMetrics(author_font)
            author_text = author_metrics.elidedText(
                authors, Qt.TextElideMode.ElideRight, rect.width()
            )
            painter.drawText(
                QRect(rect.left(), rect.top() + 22, rect.width(), 18),
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                author_text,
            )
        painter.restore()


class CenteredStatusDelegate(QStyledItemDelegate):
    """Center the abstract/PDF availability icon in its column."""

    def paint(self, painter, option, index) -> None:
        view_option = QStyleOptionViewItem(option)
        self.initStyleOption(view_option, index)
        view_option.text = ""
        view_option.icon = QIcon()
        style = option.widget.style() if option.widget else QApplication.style()
        style.drawControl(
            QStyle.ControlElement.CE_ItemViewItem,
            view_option,
            painter,
            option.widget,
        )
        icon = index.data(Qt.ItemDataRole.DecorationRole)
        if not isinstance(icon, QIcon) or icon.isNull():
            return
        size = icon.actualSize(QSize(16, 16))
        rect = QRect(0, 0, size.width(), size.height())
        rect.moveCenter(option.rect.center())
        icon.paint(painter, rect)


class SelectHeaderView(QHeaderView):
    def partial_mark_color(self) -> QColor:
        return self.palette().color(QPalette.ColorRole.Link)

    def paintSection(self, painter, rect: QRect, logicalIndex: int) -> None:
        super().paintSection(painter, rect, logicalIndex)
        if logicalIndex != CHECK_COLUMN or self.model() is None:
            return
        state = self.model().headerData(
            CHECK_COLUMN,
            Qt.Orientation.Horizontal,
            Qt.ItemDataRole.CheckStateRole,
        )
        _draw_checkbox(
            painter,
            rect,
            state,
            self.partial_mark_color(),
            self.palette().color(QPalette.ColorRole.PlaceholderText),
        )


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
        self.abstract_cancel_token: Optional[CancelToken] = None
        self.pdf_cancel_token: Optional[CancelToken] = None
        self._selected_paper_ids: set[str] = set()
        self._rendering_rows = False
        self._empty_action = "dataset"
        self._rows_loading = False
        self._pending_row_reload = False
        self._pending_row_refresh = False
        self._sidebar_width = 280
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
        self.sidebar.collapse_clicked.connect(self._hide_sidebar)
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
        self.header.sidebar_toggle_clicked.connect(self._show_sidebar)
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
        self.table = QTableView()
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
        self.table.verticalHeader().setDefaultSectionSize(50)
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
        self.table.clicked.connect(self._on_table_clicked)
        self.table.doubleClicked.connect(self._on_table_double_clicked)
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
        self.details_panel.download_abstract_clicked.connect(
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
        root_layout.addWidget(self.main_splitter)
        root.setLayout(root_layout)
        self.setCentralWidget(root)

        self._refresh_dataset_sidebar()
        self.header.set_filters([])
        self._update_summary()
        self._update_empty_state()
        self._refresh_status()

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
        return len(self._selected_paper_ids)

    def _update_summary(self) -> None:
        if self.storage and self.conf:
            total = (
                len(self._all_rows) if self._all_rows else len(self._current_rows)
            )
            self.header.set_counts(total, len(self._current_rows))
        self.selected_label.setText(selected_count(self._selected_count()))

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
        if self._empty_action == "fetch":
            self._fetch_list()
        elif self._empty_action == "clear_filters":
            self._clear_applied_filters()
        elif self._empty_action == "clear_quick_filter":
            self.quick_filter_edit.clear()
        else:
            self._open_dataset_dialog()

    def _capture_selected_ids(self) -> None:
        self._selected_paper_ids = self.paper_model.selected_ids()

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
                self._log(
                    tr("Copied bibtex: {path}", path=bib_path)
                )
            else:
                self._log(tr("Copied bibtex to clipboard"))

    def _download_current_abstract(self) -> None:
        row = self._current_row()
        abstract = row.get("abstract") if row else None
        if abstract:
            QGuiApplication.clipboard().setText(str(abstract))
            self.details_panel.set_feedback(
                tr("Abstract copied to clipboard.")
            )
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

    def _copy_current_bibtex(self) -> None:
        row = self._current_row()
        if not row:
            return
        if row.get("bibtex") or row.get("bib_path"):
            self._copy_bibtex_for_row(row)
            self.details_panel.set_feedback(
                tr("BibTeX copied to clipboard.")
            )
            return
        self.log_panel.set_busy(tr("Fetching BibTeX..."), show_cancel=False)
        self._start_worker(
            self._fetch_bibtex_task,
            self._on_bibtex_fetched,
            self._on_bibtex_fetch_error,
            row,
        )

    def _fetch_bibtex_task(self, row: dict) -> dict:
        paper = paper_from_row(row, self.conf.slug, self.storage.year)
        bibtex = self.conf.fetch_bibtex(paper)
        if not bibtex or not bibtex.strip():
            raise RuntimeError(tr("BibTeX not found"))
        bibtex = bibtex.strip()
        base_name = safe_filename(row.get("title") or "", paper.paper_id)
        file_path = unique_artifact_path(
            self.storage.paths.bib_dir,
            base_name,
            "bib",
            paper.paper_id,
        )
        write_text_artifact(file_path, bibtex)
        self.storage.mark_bib_exported(
            paper.paper_id, bibtex, file_path
        )
        return {
            "bibtex": bibtex,
            "paper_id": paper.paper_id,
            "bib_path": file_path,
            "db_path": self.storage.paths.db_path,
        }

    def _on_bibtex_fetched(self, result: dict) -> None:
        self._refresh_download_controls()
        bibtex = result["bibtex"]
        QGuiApplication.clipboard().setText(bibtex)
        if self.storage and self.storage.paths.db_path == result["db_path"]:
            refreshed = self.storage.get_paper(result["paper_id"])
            row = self._current_row()
            if (
                row is not None
                and paper_id_for_row(row) == result["paper_id"]
            ):
                if refreshed:
                    row.clear()
                    row.update(refreshed)
                    self._prepare_quick_search([row])
                else:
                    row["bibtex"] = bibtex
                    row["bib_path"] = result["bib_path"]
                self.paper_model.notify_rows_changed(
                    {result["paper_id"]}
                )
                self._update_details(self.table.currentIndex().row())
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

    def _cancel_abstract_download(self) -> None:
        if self.abstract_cancel_token:
            self.abstract_cancel_token.cancel()
            self._log(tr("Canceling abstract download..."))

    def _cancel_pdf_download(self) -> None:
        if self.pdf_cancel_token:
            self.pdf_cancel_token.cancel()
            self._log(tr("Canceling PDF download..."))

    def _cancel_active_download(self) -> None:
        if self.abstract_cancel_token:
            self._cancel_abstract_download()
        elif self.pdf_cancel_token:
            self._cancel_pdf_download()

    def _refresh_download_controls(self, fallback: str = "Ready") -> None:
        abstract_running = self.abstract_cancel_token is not None
        pdf_running = self.pdf_cancel_token is not None
        self.log_panel.show_cancel(abstract_running or pdf_running)
        if abstract_running and pdf_running:
            self.log_panel.set_busy(tr("Downloading abstracts and PDFs..."))
        elif abstract_running:
            self.log_panel.set_busy(tr("Downloading abstracts..."))
        elif pdf_running:
            self.log_panel.set_busy(tr("Downloading PDFs..."))
        else:
            self.log_panel.set_ready(tr(fallback))

    def _ensure_ready(self) -> bool:
        if self.storage and self.conf:
            return True
        show_warning(self, tr("Missing"), tr("Please choose a dataset first."))
        return False

    def _start_worker(self, fn, on_done, on_error, *args) -> None:
        worker = Worker(fn, *args)
        worker.signals.log.connect(self._log)
        worker.signals.finished.connect(on_done)
        worker.signals.error.connect(on_error)
        self.thread_pool.start(worker)

    def _refresh_status(self) -> None:
        if not self.conf or not self.storage:
            self.header.set_dataset("PaperSpider", tr("No dataset selected"))
            self.status_label.setText(tr("No dataset loaded"))
            self._update_empty_state()
            self._update_summary()
            return
        self.header.set_dataset(
            f"{self.conf.name} {self.storage.year}", ""
        )
        self.sidebar.set_active_dataset(self.conf.slug, self.storage.year)
        self.paper_model.set_selected_ids(self._selected_paper_ids)
        self._update_empty_state()
        self._update_summary()

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
        settings = QSettings("PaperSpider", "PaperSpider")
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

    def _hide_sidebar(self) -> None:
        self._sidebar_width = self.sidebar.width()
        self.sidebar.hide()
        self.header.set_sidebar_hidden(True)

    def _show_sidebar(self) -> None:
        self.sidebar.show()
        total = max(1, sum(self.main_splitter.sizes()))
        width = min(440, max(160, self._sidebar_width))
        self.main_splitter.setSizes([width, max(1, total - width)])
        self.header.set_sidebar_hidden(False)

    def _open_dataset_folder(self, conf_slug: str, year: int) -> None:
        base = self._dataset_base_dir()
        path = os.path.join(base, conf_slug, str(year))
        if not os.path.isdir(path):
            show_warning(
                self, tr("Missing"), tr("Dataset folder not found.")
            )
            return
        QDesktopServices.openUrl(QUrl.fromLocalFile(path))

    def _delete_dataset(self, conf_slug: str, year: int) -> None:
        base = self._dataset_base_dir()
        path = os.path.join(base, conf_slug, str(year))
        if not os.path.isdir(path):
            show_warning(
                self, tr("Missing"), tr("Dataset folder not found.")
            )
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
        if (
            self.conf
            and self.storage
            and self.conf.slug == conf_slug
            and self.storage.year == year
        ):
            self.conf = None
            self.storage = None
            self._all_rows = []
            self._filtered_rows = []
            self._current_rows = []
            self._selected_paper_ids.clear()
            self.paper_model.set_rows([])
            self.details_panel.set_row(None)
        self._refresh_dataset_sidebar(base)
        self._refresh_status()
        show_information(
            self,
            tr("Done"),
            tr("Dataset deleted. Fetch it again to use it."),
        )

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
        self.table.viewport().update()

    def _dataset_base_dir(self) -> str:
        if self.base_dir:
            return self.base_dir
        settings = QSettings("PaperSpider", "PaperSpider")
        return str(settings.value("base_dir", "")).strip()

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
            show_warning(
                self, tr("Missing"), tr("Please choose a base folder first.")
            )
            return
        settings = QSettings("PaperSpider", "PaperSpider")
        try:
            delay_ms = int(settings.value("request_delay_ms", 100))
        except (TypeError, ValueError):
            delay_ms = 100
        conf.request_delay = delay_ms / 1000.0
        self.conf = conf
        self.base_dir = base
        self.storage = PaperStorage(base, conf.slug, year)
        self._all_rows = []
        self._filtered_rows = []
        self._current_rows = []
        self._selected_paper_ids.clear()
        self.details_panel.set_row(None)
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
        if (
            not self.conf
            or not self.storage
            or self.conf.slug != conf_slug
            or self.storage.year != year
        ):
            self._select_dataset(conf_slug, year, load=False)
        self._fetch_list()

    def _fetch_list(self) -> None:
        if not self._ensure_ready():
            return
        self._set_rows_loading(True, tr("Fetching paper list..."))
        self._start_worker(
            self._fetch_list_task,
            self._on_fetch_done,
            self._on_worker_error,
            self.conf,
            self.storage,
        )
        self._log(tr("Fetching paper list..."))

    def _fetch_list_task(self, conf, storage: PaperStorage, log=None) -> int:
        return self.service.fetch_list(conf, storage)

    def _on_fetch_done(self, count: int) -> None:
        self._log(tr("Loaded {count} papers", count=count))
        show_information(
            self,
            tr("Done"),
            tr("Loaded {count} papers", count=count),
        )
        self._set_rows_loading(False)
        self._refresh_dataset_sidebar()
        self._refresh_status()
        self._load_papers(force_refresh=True)

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

    def _set_rows_loading(self, loading: bool, message: Optional[str] = None) -> None:
        self._rows_loading = loading
        self.table.setEnabled(not loading)
        self.abstract_btn.setEnabled(not loading)
        self.pdf_btn.setEnabled(not loading)
        self.export_btn.setEnabled(not loading)
        self.quick_filter_edit.setEnabled(not loading)
        self.invert_btn.setEnabled(not loading)
        self.header.filter_btn.setEnabled(not loading)
        if loading:
            text = message or tr("Loading papers...")
            self.status_label.setText(text)
            self.log_panel.set_busy(text, show_cancel=False)
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
        action = (
            tr("Loading papers...")
            if cached_rows is None
            else tr("Applying filters...")
        )
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
        show_error(self, tr("Error"), message)
        self._log(tr("Error: {message}", message=message))
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

    def _on_table_clicked(self, index) -> None:
        if index.column() == CHECK_COLUMN:
            state = index.data(Qt.ItemDataRole.CheckStateRole)
            next_state = (
                Qt.CheckState.Unchecked
                if state == Qt.CheckState.Checked
                else Qt.CheckState.Checked
            )
            self.paper_model.setData(
                index,
                next_state,
                Qt.ItemDataRole.CheckStateRole,
            )
        self._update_details(index.row())

    def _toggle_header_selection(self, section: int) -> None:
        if section != CHECK_COLUMN:
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
            show_information(self, tr("Select"), tr("Please select papers first."))
            return
        dialog = ExportDialog(selected, self)
        dialog.exec()

    def _download_abstracts(self) -> None:
        if self.abstract_cancel_token:
            show_information(
                self,
                tr("Busy"),
                tr(
                    "Abstract download already running. Use the cancel control in the status bar."
                ),
            )
            return
        if not self._ensure_ready():
            return
        selected = self._selected_rows()
        if not selected:
            show_information(self, tr("Select"), tr("Please select papers first."))
            return
        self._download_abstracts_for_rows(selected)

    def _download_abstracts_for_rows(self, rows: List[dict]) -> None:
        if not self._ensure_ready():
            return
        if self.abstract_cancel_token:
            show_information(
                self, tr("Busy"), tr("Abstract download already running.")
            )
            return
        self.abstract_cancel_token = CancelToken()
        self._refresh_download_controls()
        self.log_panel.set_busy(
            tr("Downloading abstracts..."), 0, len(rows)
        )
        self.log_panel.show_cancel(True)
        self._start_worker(
            self._download_abstracts_task,
            self._on_abstracts_done,
            self._on_abstracts_error,
            self.conf,
            self.storage,
            rows,
            self.abstract_cancel_token,
        )
        self._log(tr("Downloading abstracts..."))

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
            show_information(
                self,
                tr("Busy"),
                tr(
                    "PDF download already running. Use the cancel control in the status bar."
                ),
            )
            return
        if not self._ensure_ready():
            return
        selected = self._selected_rows()
        if not selected:
            show_information(self, tr("Select"), tr("Please select papers first."))
            return
        self._download_pdfs_for_rows(selected)

    def _download_pdfs_for_rows(self, rows: List[dict]) -> None:
        if not self._ensure_ready():
            return
        if self.pdf_cancel_token:
            show_information(
                self, tr("Busy"), tr("PDF download already running.")
            )
            return
        self.pdf_cancel_token = CancelToken()
        self._refresh_download_controls()
        self.log_panel.set_busy(tr("Downloading PDFs..."), 0, len(rows))
        self.log_panel.show_cancel(True)
        self._start_worker(
            self._download_pdfs_task,
            self._on_pdfs_done,
            self._on_pdfs_error,
            self.conf,
            self.storage,
            rows,
            self.pdf_cancel_token,
        )
        self._log(tr("Downloading PDFs..."))

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
            title = tr("Canceled")
        elif result.failures:
            title = tr("Finished with issues")
        else:
            title = tr("Done")
        artifact = tr("abstracts") if artifact_name == "abstracts" else tr("PDFs")
        parts = [
            tr(
                "Downloaded {count} {artifact}",
                count=result.succeeded,
                artifact=artifact,
            )
        ]
        if result.skipped:
            parts.append(
                tr("Skipped {count} already available", count=result.skipped)
            )
        if result.failures:
            parts.append(tr("Failed {count}", count=len(result.failures)))
            for failure in result.failures[:5]:
                self._log(
                    tr(
                        "Failed {artifact}: {title} ({message})",
                        artifact=artifact,
                        title=failure.title,
                        message=failure.message,
                    )
                )
        show_information(self, title, "\n".join(parts))

    def _report_error(self, message: str) -> None:
        show_error(self, tr("Error"), message)
        self._log(tr("Error: {message}", message=message))

    def _on_worker_error(self, message: str) -> None:
        self._set_rows_loading(False)
        self._refresh_download_controls("Error")
        self._report_error(message)

    def _on_abstracts_error(self, message: str) -> None:
        self.abstract_cancel_token = None
        self._refresh_download_controls("Error")
        self._report_error(message)

    def _on_pdfs_error(self, message: str) -> None:
        self.pdf_cancel_token = None
        self._refresh_download_controls("Error")
        self._report_error(message)
