# Copyright 2026 Isaacveg
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#     http://www.apache.org/licenses/LICENSE-2.0

from __future__ import annotations

import os
from typing import Optional

from PyQt6.QtCore import QThreadPool
from PyQt6.QtWidgets import (
    QFileDialog,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QWidget,
    QComboBox,
)

from ..conferences import available_conferences
from ..storage import PaperStorage
from .workers import Worker
from .workspace_window import WorkspaceWindow


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("PaperSpider")
        self.thread_pool = QThreadPool()
        self.conferences = available_conferences()
        self.workspace_window: Optional[WorkspaceWindow] = None
        self._build_ui()

    def _build_ui(self) -> None:
        root = QWidget()
        layout = QGridLayout()

        self.conf_combo = QComboBox()
        for conf in self.conferences:
            self.conf_combo.addItem(conf.name, conf)

        self.year_spin = QSpinBox()
        self.year_spin.setRange(1980, 2100)
        self.year_spin.setValue(2024)

        self.base_dir_edit = QLineEdit()
        browse_btn = QPushButton("Browse")
        browse_btn.clicked.connect(self._choose_dir)

        self.status_label = QLabel("No data loaded")

        fetch_btn = QPushButton("Fetch paper list")
        fetch_btn.clicked.connect(self._fetch_list)

        open_btn = QPushButton("Open workspace")
        open_btn.clicked.connect(self._open_workspace)

        layout.addWidget(QLabel("Conference"), 0, 0)
        layout.addWidget(self.conf_combo, 0, 1)
        layout.addWidget(QLabel("Year"), 1, 0)
        layout.addWidget(self.year_spin, 1, 1)
        layout.addWidget(QLabel("Output folder"), 2, 0)
        layout.addWidget(self.base_dir_edit, 2, 1)
        layout.addWidget(browse_btn, 2, 2)
        layout.addWidget(self.status_label, 3, 0, 1, 3)

        btn_layout = QHBoxLayout()
        btn_layout.addWidget(fetch_btn)
        btn_layout.addWidget(open_btn)

        layout.addLayout(btn_layout, 4, 0, 1, 3)

        root.setLayout(layout)
        self.setCentralWidget(root)

        self.conf_combo.currentIndexChanged.connect(self._check_existing_data)
        self.year_spin.valueChanged.connect(self._check_existing_data)
        self.base_dir_edit.textChanged.connect(self._check_existing_data)

    def _choose_dir(self) -> None:
        directory = QFileDialog.getExistingDirectory(self, "Select output directory")
        if directory:
            self.base_dir_edit.setText(directory)

    def _current_conf(self):
        return self.conf_combo.currentData()

    def _check_existing_data(self) -> None:
        base_dir = self.base_dir_edit.text().strip()
        conf = self._current_conf()
        year = self.year_spin.value()
        if not base_dir or not conf:
            self.status_label.setText("No data loaded")
            return
        db_path = os.path.join(base_dir, conf.slug, str(year), "papers.sqlite")
        if os.path.exists(db_path):
            self.status_label.setText("Existing data found")
        else:
            self.status_label.setText("No data loaded")

    def _fetch_list(self) -> None:
        base_dir = self.base_dir_edit.text().strip()
        if not base_dir:
            QMessageBox.warning(self, "Missing folder", "Please choose an output folder first.")
            return
        conf = self._current_conf()
        year = self.year_spin.value()
        storage = PaperStorage(base_dir, conf.slug, year)

        worker = Worker(self._fetch_list_task, conf, year, storage)
        worker.signals.finished.connect(self._on_fetch_done)
        worker.signals.error.connect(self._on_worker_error)
        self.thread_pool.start(worker)
        self.status_label.setText("Fetching paper list...")

    def _fetch_list_task(self, conf, year: int, storage: PaperStorage, log=None) -> dict:
        papers = conf.list_papers(year)
        storage.upsert_papers(papers)
        return {"count": len(papers), "conf": conf, "year": year, "storage": storage}

    def _on_fetch_done(self, result: dict) -> None:
        count = result.get("count", 0)
        self.status_label.setText(f"Loaded {count} papers")
        QMessageBox.information(self, "Done", f"Loaded {count} papers")

    def _on_worker_error(self, message: str) -> None:
        QMessageBox.critical(self, "Error", message)
        self.status_label.setText("Error")

    def _open_workspace(self) -> None:
        base_dir = self.base_dir_edit.text().strip()
        if not base_dir:
            QMessageBox.warning(self, "Missing folder", "Please choose an output folder first.")
            return
        conf = self._current_conf()
        year = self.year_spin.value()
        storage = PaperStorage(base_dir, conf.slug, year)
        self.workspace_window = WorkspaceWindow(conf, storage)
        self.workspace_window.show()
