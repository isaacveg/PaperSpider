# Copyright 2026 Isaacveg
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#     http://www.apache.org/licenses/LICENSE-2.0

from __future__ import annotations

import os
import shutil
import time
from dataclasses import dataclass
from typing import List, Optional

from PyQt6.QtCore import Qt, QSettings
from PyQt6.QtWidgets import (
    QComboBox,
    QDialog,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QWidget,
    QFileDialog,
)

from ..conferences import available_conferences

YEAR_MIN = 1980
YEAR_MAX = 2100


@dataclass
class SelectionResult:
    base_dir: str
    conf_slug: str
    year: int
    request_delay_ms: int


@dataclass
class DatasetEntry:
    conf_slug: str
    year: int
    path: Optional[str]
    is_existing: bool


class DatasetItemWidget(QWidget):
    def __init__(self, conferences, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)

        self.conf_combo = QComboBox()
        for conf in conferences:
            self.conf_combo.addItem(conf.name, conf.slug)

        self.year_spin = QSpinBox()
        self.year_spin.setRange(YEAR_MIN, YEAR_MAX)
        self.year_spin.setValue(2024)

        layout.addWidget(self.conf_combo)
        layout.addWidget(self.year_spin)
        self.setLayout(layout)

    def set_values(self, conf_slug: str, year: int, editable: bool) -> None:
        index = self.conf_combo.findData(conf_slug)
        if index >= 0:
            self.conf_combo.setCurrentIndex(index)
        year = max(min(year, YEAR_MAX), YEAR_MIN)
        self.year_spin.setValue(year)
        self.conf_combo.setEnabled(editable)
        self.year_spin.setEnabled(editable)

    def selection(self) -> tuple[str, int]:
        return self.conf_combo.currentData(), self.year_spin.value()


class SettingsDialog(QDialog):
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self._conferences = available_conferences()
        self._settings = QSettings("PaperSpider", "PaperSpider")
        self._result: Optional[SelectionResult] = None
        self._build_ui()
        self._load_previous_state()

    def _build_ui(self) -> None:
        layout = QGridLayout()

        self.base_dir_edit = QLineEdit()
        self.base_dir_edit.textChanged.connect(self._on_base_dir_changed)
        browse_btn = QPushButton("Browse")
        browse_btn.clicked.connect(self._choose_dir)

        layout.addWidget(QLabel("Base folder"), 0, 0)
        layout.addWidget(self.base_dir_edit, 0, 1)
        layout.addWidget(browse_btn, 0, 2)

        self.delay_spin = QSpinBox()
        self.delay_spin.setRange(0, 10000)
        self.delay_spin.setValue(100)
        self.delay_spin.setSuffix(" ms")
        self.delay_spin.valueChanged.connect(self._on_delay_changed)
        layout.addWidget(QLabel("Request interval"), 1, 0)
        layout.addWidget(self.delay_spin, 1, 1)

        self.existing_list = QListWidget()
        layout.addWidget(QLabel("Datasets"), 2, 0)
        layout.addWidget(self.existing_list, 2, 1, 1, 2)

        list_btn_layout = QHBoxLayout()
        add_btn = QPushButton("Add")
        add_btn.clicked.connect(self._add_entry)
        delete_btn = QPushButton("Delete")
        delete_btn.clicked.connect(self._delete_selected)
        list_btn_layout.addWidget(add_btn)
        list_btn_layout.addWidget(delete_btn)
        list_btn_layout.addStretch()
        layout.addLayout(list_btn_layout, 3, 0, 1, 3)

        btn_layout = QHBoxLayout()
        use_selected_btn = QPushButton("Use selected")
        use_selected_btn.clicked.connect(self._use_selected)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(use_selected_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout, 4, 0, 1, 3)

        self.setLayout(layout)

    def _load_previous_state(self) -> None:
        base_dir = self._settings.value("base_dir", "")
        delay_ms = self._settings.value("request_delay_ms", 100)
        try:
            self.delay_spin.setValue(int(delay_ms))
        except (TypeError, ValueError):
            self.delay_spin.setValue(100)
        if base_dir:
            self.base_dir_edit.setText(base_dir)
            self._refresh_existing(base_dir)

    def _on_base_dir_changed(self, text: str) -> None:
        self._settings.setValue("base_dir", text)
        self._refresh_existing(text)

    def _on_delay_changed(self, value: int) -> None:
        self._settings.setValue("request_delay_ms", value)

    def _choose_dir(self) -> None:
        directory = QFileDialog.getExistingDirectory(self, "Select output directory")
        if directory:
            self.base_dir_edit.setText(directory)

    def _refresh_existing(self, base_dir: str) -> None:
        self.existing_list.clear()
        if not base_dir:
            return
        datasets = self._scan_datasets(base_dir)
        for entry in datasets:
            self._add_list_item(entry, editable=False)

    def _add_list_item(self, entry: DatasetEntry, editable: bool) -> None:
        item = QListWidgetItem()
        item.setData(Qt.ItemDataRole.UserRole, entry)
        widget = DatasetItemWidget(self._conferences)
        widget.set_values(entry.conf_slug, entry.year, editable=editable)
        item.setSizeHint(widget.sizeHint())
        self.existing_list.addItem(item)
        self.existing_list.setItemWidget(item, widget)

    def _add_entry(self) -> None:
        conf_slug = self._conferences[0].slug if self._conferences else "unknown"
        year = 2024
        entry = DatasetEntry(
            conf_slug=conf_slug,
            year=year,
            path=None,
            is_existing=False,
        )
        self._add_list_item(entry, editable=True)
        self.existing_list.setCurrentRow(self.existing_list.count() - 1)

    def _delete_selected(self) -> None:
        item = self.existing_list.currentItem()
        if not item:
            return
        entry: DatasetEntry = item.data(Qt.ItemDataRole.UserRole)
        if entry and entry.is_existing and entry.path:
            confirm = QMessageBox.question(
                self,
                "Delete",
                "This will move the dataset folder to .trash. Continue?",
            )
            if confirm != QMessageBox.StandardButton.Yes:
                return
            if not self._move_to_trash(entry.path):
                return
        row = self.existing_list.row(item)
        self.existing_list.takeItem(row)

    def _move_to_trash(self, path: str) -> bool:
        base_dir = self.base_dir_edit.text().strip()
        if not base_dir:
            return False
        trash_root = os.path.join(base_dir, ".trash")
        os.makedirs(trash_root, exist_ok=True)
        stamp = int(time.time())
        name = os.path.basename(path)
        dest = os.path.join(trash_root, f"{name}_{stamp}")
        try:
            shutil.move(path, dest)
        except (OSError, shutil.Error):
            QMessageBox.warning(self, "Error", "Failed to move dataset to .trash")
            return False
        return True

    def _scan_datasets(self, base_dir: str) -> List[DatasetEntry]:
        datasets: List[DatasetEntry] = []
        if not os.path.isdir(base_dir):
            return datasets
        conf_map = {conf.slug: conf.name for conf in self._conferences}
        for conf_slug in os.listdir(base_dir):
            if conf_slug.startswith("."):
                continue
            conf_path = os.path.join(base_dir, conf_slug)
            if not os.path.isdir(conf_path):
                continue
            for year_name in os.listdir(conf_path):
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
                    )
                )
        return datasets

    def _use_selected(self) -> None:
        item = self.existing_list.currentItem()
        if not item:
            return
        widget = self.existing_list.itemWidget(item)
        if not widget:
            return
        conf_slug, year = widget.selection()
        base_dir = self.base_dir_edit.text().strip()
        if not base_dir:
            return
        delay_ms = self.delay_spin.value()
        self._result = SelectionResult(
            base_dir=base_dir,
            conf_slug=conf_slug,
            year=year,
            request_delay_ms=delay_ms,
        )
        self.accept()

    def selection(self) -> Optional[SelectionResult]:
        return self._result
