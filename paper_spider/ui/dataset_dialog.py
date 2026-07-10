# Copyright 2026 Isaacveg
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#     http://www.apache.org/licenses/LICENSE-2.0

from __future__ import annotations

import os
import shutil
import sqlite3
import time
from dataclasses import dataclass
from datetime import date
from typing import List, Optional

from PyQt6.QtCore import Qt, QSettings
from PyQt6.QtGui import QIntValidator
from PyQt6.QtWidgets import (
    QComboBox,
    QAbstractItemView,
    QDialog,
    QFileDialog,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QHeaderView,
    QSizePolicy,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ..conferences import available_conferences
from .dialog_utils import ask_confirmation, configure_utility_dialog, show_warning
from .theme import apply_theme

YEAR_MIN = 1980
YEAR_MAX = 2100


@dataclass
class SelectionResult:
    base_dir: str
    conf_slug: str
    year: int
    request_delay_ms: int
    fetch_after_select: bool = False


@dataclass
class DatasetEntry:
    conf_slug: str
    year: int
    path: Optional[str]
    is_existing: bool
    paper_count: int = 0


class DatasetDialog(QDialog):
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        configure_utility_dialog(self)
        self.setWindowTitle("Datasets")
        self.setMinimumWidth(980)
        self.resize(1120, 700)
        self._conferences = available_conferences()
        self._settings = QSettings("PaperSpider", "PaperSpider")
        self._result: Optional[SelectionResult] = None
        self._entries: List[DatasetEntry] = []
        self._build_ui()
        self._load_previous_state()
        apply_theme(self, self._settings)

    def _build_ui(self) -> None:
        root_layout = QVBoxLayout()
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        content = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(12)

        base_group = QGroupBox("Base folder")
        base_layout = QGridLayout()
        base_layout.setColumnStretch(1, 1)
        self.base_dir_edit = QLineEdit()
        self.base_dir_edit.textChanged.connect(self._on_base_dir_changed)
        browse_btn = QPushButton("Browse")
        browse_btn.clicked.connect(self._choose_dir)

        base_layout.addWidget(QLabel("Folder"), 0, 0)
        base_layout.addWidget(self.base_dir_edit, 0, 1)
        base_layout.addWidget(browse_btn, 0, 2)
        base_group.setLayout(base_layout)
        layout.addWidget(base_group)

        datasets_group = QGroupBox("Datasets")
        datasets_layout = QVBoxLayout()
        toolbar_layout = QHBoxLayout()
        self.add_dataset_btn = QPushButton("+ Add Dataset")
        self.add_dataset_btn.clicked.connect(self._add_entry)
        toolbar_layout.addWidget(self.add_dataset_btn)
        self.refresh_datasets_btn = QPushButton("Refresh")
        self.refresh_datasets_btn.clicked.connect(
            lambda: self._refresh_existing(self.base_dir_edit.text().strip())
        )
        toolbar_layout.addWidget(self.refresh_datasets_btn)
        toolbar_layout.addStretch()
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Search datasets...")
        self.search_edit.setClearButtonEnabled(True)
        self.search_edit.setMaximumWidth(300)
        self.search_edit.textChanged.connect(self._apply_search)
        toolbar_layout.addWidget(self.search_edit)
        datasets_layout.addLayout(toolbar_layout)

        self.new_dataset_panel = QFrame()
        self.new_dataset_panel.setObjectName("newDatasetPanel")
        new_dataset_layout = QHBoxLayout()
        new_dataset_layout.setContentsMargins(12, 10, 12, 10)
        new_dataset_layout.setSpacing(8)
        new_dataset_label = QLabel("New dataset")
        new_dataset_label.setObjectName("newDatasetLabel")
        self.new_conf_combo = QComboBox()
        self.new_conf_combo.setObjectName("newDatasetConference")
        for conf in self._conferences:
            self.new_conf_combo.addItem(conf.name, conf.slug)
        self.new_year_edit = QLineEdit(str(date.today().year))
        self.new_year_edit.setObjectName("newDatasetYear")
        self.new_year_edit.setValidator(QIntValidator(YEAR_MIN, YEAR_MAX, self))
        self.new_year_edit.setMaximumWidth(96)
        self.new_year_edit.setPlaceholderText("Year")
        self.cancel_new_dataset_btn = QPushButton("Cancel")
        self.cancel_new_dataset_btn.setObjectName("secondaryButton")
        self.cancel_new_dataset_btn.clicked.connect(self._cancel_new_dataset)
        self.fetch_new_dataset_btn = QPushButton("Fetch dataset")
        self.fetch_new_dataset_btn.setObjectName("primaryButton")
        self.fetch_new_dataset_btn.clicked.connect(self._fetch_new_dataset)
        new_dataset_layout.addWidget(new_dataset_label)
        new_dataset_layout.addWidget(self.new_conf_combo, stretch=1)
        new_dataset_layout.addWidget(self.new_year_edit)
        new_dataset_layout.addStretch()
        new_dataset_layout.addWidget(self.cancel_new_dataset_btn)
        new_dataset_layout.addWidget(self.fetch_new_dataset_btn)
        self.new_dataset_panel.setLayout(new_dataset_layout)
        self.new_dataset_panel.setVisible(False)
        datasets_layout.addWidget(self.new_dataset_panel)

        self.dataset_table = QTableWidget(0, 5)
        self.dataset_table.setHorizontalHeaderLabels(
            ["Conference", "Year", "Status", "Papers", "Actions"]
        )
        self.dataset_table.setAlternatingRowColors(True)
        self.dataset_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.dataset_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.dataset_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.dataset_table.verticalHeader().setVisible(False)
        self.dataset_table.cellDoubleClicked.connect(self._use_row)
        self.dataset_table.currentCellChanged.connect(self._update_use_selected_state)
        header = self.dataset_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        datasets_layout.addWidget(self.dataset_table, stretch=1)
        datasets_group.setLayout(datasets_layout)
        layout.addWidget(datasets_group, 1)

        btn_layout = QHBoxLayout()
        self.storage_label = QLabel("Storage: Not selected")
        self.storage_label.setObjectName("mutedLabel")
        btn_layout.addWidget(self.storage_label)
        btn_layout.addStretch()
        self.use_selected_btn = QPushButton("Use selected")
        self.use_selected_btn.setObjectName("primaryButton")
        self.use_selected_btn.setEnabled(False)
        self.use_selected_btn.clicked.connect(self._use_selected)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)
        btn_layout.addWidget(self.use_selected_btn)
        layout.addLayout(btn_layout)

        content.setLayout(layout)
        root_layout.addWidget(content, stretch=1)
        self.setLayout(root_layout)

    def _load_previous_state(self) -> None:
        base_dir = self._settings.value("base_dir", "")
        if base_dir:
            self.base_dir_edit.blockSignals(True)
            self.base_dir_edit.setText(str(base_dir))
            self.base_dir_edit.blockSignals(False)
            self.storage_label.setText(f"Storage: {base_dir}")
            self._refresh_existing(str(base_dir))

    def _on_base_dir_changed(self, text: str) -> None:
        self._settings.setValue("base_dir", text)
        self.storage_label.setText(f"Storage: {text}" if text else "Storage: Not selected")
        self._refresh_existing(text)

    def _choose_dir(self) -> None:
        directory = QFileDialog.getExistingDirectory(self, "Select output directory")
        if directory:
            self.base_dir_edit.setText(directory)

    def _refresh_existing(self, base_dir: str) -> None:
        self.dataset_table.setRowCount(0)
        self._entries = []
        if not base_dir:
            self._update_use_selected_state()
            return
        datasets = self._scan_datasets(base_dir)
        for entry in datasets:
            self._add_table_row(entry, focus=False)
        if self.dataset_table.rowCount() > 0:
            self.dataset_table.setCurrentCell(0, 0)
        self._apply_search()

    def _add_table_row(self, entry: DatasetEntry, focus: bool = True) -> int:
        row = self.dataset_table.rowCount()
        self.dataset_table.insertRow(row)
        self._entries.insert(row, entry)

        conf_item = QTableWidgetItem(self._conference_name(entry.conf_slug))
        conf_item.setData(Qt.ItemDataRole.UserRole, entry)
        conf_item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
        self.dataset_table.setItem(row, 0, conf_item)
        year_item = QTableWidgetItem(str(entry.year))
        year_item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
        self.dataset_table.setItem(row, 1, year_item)

        status_container = QWidget()
        status_layout = QHBoxLayout()
        status_layout.setContentsMargins(0, 0, 0, 0)
        status_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        status_label = QLabel("Fetched" if entry.is_existing else "Unfetched")
        status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        status_label.setObjectName("datasetStatusFetched" if entry.is_existing else "datasetStatusUnfetched")
        status_label.setMaximumHeight(22)
        status_layout.addWidget(status_label)
        status_container.setLayout(status_layout)
        self.dataset_table.setCellWidget(row, 2, status_container)

        paper_item = QTableWidgetItem(f"{entry.paper_count:,}")
        paper_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        paper_item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
        self.dataset_table.setItem(row, 3, paper_item)

        actions = QWidget()
        actions_layout = QHBoxLayout()
        actions_layout.setContentsMargins(0, 0, 0, 0)
        actions_layout.setSpacing(6)
        fetch_btn = QPushButton("Refresh" if entry.is_existing else "Fetch")
        fetch_btn.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        fetch_btn.setFixedHeight(24)
        if entry.is_existing:
            fetch_btn.setObjectName("datasetRefreshButton")
        else:
            fetch_btn.setObjectName("primaryButton")
        fetch_btn.clicked.connect(lambda _checked=False, widget=actions: self._fetch_action(widget))
        delete_btn = QPushButton("x")
        delete_btn.setObjectName("datasetDeleteButton")
        delete_btn.setToolTip("Delete dataset")
        delete_btn.clicked.connect(lambda _checked=False, widget=actions: self._delete_action(widget))
        actions_layout.addWidget(fetch_btn)
        actions_layout.addWidget(delete_btn)
        actions.setLayout(actions_layout)
        self.dataset_table.setCellWidget(row, 4, actions)

        self.dataset_table.setRowHeight(row, 36)
        if focus:
            self.dataset_table.setCurrentCell(row, 0)
        else:
            self._update_use_selected_state()
        return row

    def _add_entry(self) -> None:
        self.new_dataset_panel.setVisible(True)
        self.new_conf_combo.setFocus()

    def _cancel_new_dataset(self) -> None:
        self.new_dataset_panel.setVisible(False)

    def _fetch_new_dataset(self) -> None:
        conf_slug = self.new_conf_combo.currentData()
        year_text = self.new_year_edit.text().strip()
        if conf_slug is None:
            show_warning(self, "Missing", "Please choose a conference.")
            return
        try:
            year = int(year_text)
        except ValueError:
            show_warning(self, "Invalid year", "Enter a four-digit conference year.")
            return
        if not YEAR_MIN <= year <= YEAR_MAX:
            show_warning(
                self,
                "Invalid year",
                f"Year must be between {YEAR_MIN} and {YEAR_MAX}.",
            )
            return
        self._select_dataset(str(conf_slug), year, fetch_after_select=True)

    def _delete_selected(self) -> None:
        row = self._selected_row()
        if row is None:
            return
        self._delete_row(row)

    def _delete_row(self, row: int) -> None:
        if row < 0 or row >= self.dataset_table.rowCount():
            return
        entry = self._entries[row]
        if entry and entry.is_existing and entry.path:
            if not ask_confirmation(
                self, "Delete", "This will move the dataset folder to .trash. Continue?"
            ):
                return
            if not self._move_to_trash(entry.path):
                return
        self.dataset_table.removeRow(row)
        self._entries.pop(row)
        self._update_use_selected_state()

    def _delete_action(self, widget: QWidget) -> None:
        row = self._row_for_widget(widget)
        if row is not None:
            self._delete_row(row)

    def _move_to_trash(self, path: str) -> bool:
        base_dir = self.base_dir_edit.text().strip()
        if not base_dir:
            return False
        trash_root = os.path.join(base_dir, ".trash")
        os.makedirs(trash_root, exist_ok=True)
        stamp = int(time.time())
        name = os.path.relpath(path, base_dir).replace(os.sep, "_")
        dest = os.path.join(trash_root, f"{name}_{stamp}")
        try:
            shutil.move(path, dest)
        except (OSError, shutil.Error):
            show_warning(self, "Error", "Failed to move dataset to .trash")
            return False
        return True

    def _scan_datasets(self, base_dir: str) -> List[DatasetEntry]:
        datasets: List[DatasetEntry] = []
        if not os.path.isdir(base_dir):
            return datasets
        for conf_slug in sorted(os.listdir(base_dir)):
            if conf_slug.startswith("."):
                continue
            conf_path = os.path.join(base_dir, conf_slug)
            if not os.path.isdir(conf_path):
                continue
            for year_name in sorted(os.listdir(conf_path), reverse=True):
                year_path = os.path.join(conf_path, year_name)
                if not os.path.isdir(year_path):
                    continue
                db_path = os.path.join(year_path, "papers.sqlite")
                if not os.path.exists(db_path):
                    continue
                try:
                    year = int(year_name)
                except ValueError:
                    continue
                if year < YEAR_MIN or year > YEAR_MAX:
                    continue
                datasets.append(
                    DatasetEntry(
                        conf_slug=conf_slug,
                        year=year,
                        path=year_path,
                        is_existing=True,
                        paper_count=self._paper_count(db_path, conf_slug, year),
                    )
                )
        return datasets

    def _paper_count(self, db_path: str, conf_slug: str, year: int) -> int:
        try:
            with sqlite3.connect(db_path) as conn:
                row = conn.execute(
                    "SELECT COUNT(*) FROM papers WHERE conf = ? AND year = ?",
                    (conf_slug, year),
                ).fetchone()
        except sqlite3.Error:
            return 0
        return int(row[0]) if row else 0

    def _use_selected(self) -> None:
        row = self._selected_row()
        if row is None:
            return
        self._use_row(row, 0)

    def _use_row(self, row: int, _column: int = 0) -> None:
        if not self._row_is_fetched(row):
            show_warning(
                self,
                "Fetch required",
                "Please fetch this dataset before using it.",
            )
            return
        self._select_row(row, fetch_after_select=False)

    def _fetch_row(self, row: int) -> None:
        self._select_row(row, fetch_after_select=True)

    def _fetch_action(self, widget: QWidget) -> None:
        row = self._row_for_widget(widget)
        if row is not None:
            self._fetch_row(row)

    def _select_row(self, row: int, fetch_after_select: bool) -> None:
        if row < 0 or row >= self.dataset_table.rowCount():
            return
        conf_slug, year = self._row_selection(row)
        self._select_dataset(conf_slug, year, fetch_after_select)

    def _select_dataset(
        self, conf_slug: str, year: int, fetch_after_select: bool
    ) -> None:
        base_dir = self.base_dir_edit.text().strip()
        if not base_dir:
            show_warning(self, "Missing", "Please choose a base folder first.")
            return
        self._result = SelectionResult(
            base_dir=base_dir,
            conf_slug=conf_slug,
            year=year,
            request_delay_ms=self._request_delay_ms(),
            fetch_after_select=fetch_after_select,
        )
        self.accept()

    def _row_selection(self, row: int) -> tuple[str, int]:
        entry = self._entries[row]
        return entry.conf_slug, entry.year

    def _row_is_fetched(self, row: int) -> bool:
        return 0 <= row < len(self._entries) and self._entries[row].is_existing

    def _selected_row(self) -> Optional[int]:
        row = self.dataset_table.currentRow()
        return row if row >= 0 and not self.dataset_table.isRowHidden(row) else None

    def _update_use_selected_state(self, *_args) -> None:
        row = self._selected_row()
        self.use_selected_btn.setEnabled(row is not None and self._row_is_fetched(row))

    def _row_for_widget(self, widget: QWidget) -> Optional[int]:
        for row in range(self.dataset_table.rowCount()):
            if self.dataset_table.cellWidget(row, 4) is widget:
                return row
        return None

    def _apply_search(self) -> None:
        query = self.search_edit.text().strip().casefold() if hasattr(self, "search_edit") else ""
        for row, entry in enumerate(self._entries):
            text = f"{self._conference_name(entry.conf_slug)} {entry.year} {'fetched' if entry.is_existing else 'unfetched'}".casefold()
            self.dataset_table.setRowHidden(row, bool(query and query not in text))
        self._update_use_selected_state()

    def _conference_name(self, conf_slug: str) -> str:
        for conf in self._conferences:
            if conf.slug == conf_slug:
                return conf.name
        return conf_slug.upper()

    def selection(self) -> Optional[SelectionResult]:
        return self._result

    def _request_delay_ms(self) -> int:
        delay_ms = self._settings.value("request_delay_ms", 100)
        try:
            return int(delay_ms)
        except (TypeError, ValueError):
            return 100
