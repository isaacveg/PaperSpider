# Copyright 2026 Isaacveg
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#     http://www.apache.org/licenses/LICENSE-2.0

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from typing import List, Optional

from PyQt6.QtCore import Qt, QThreadPool, QUrl
from PyQt6.QtGui import QDesktopServices, QGuiApplication
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QHBoxLayout,
    QDialog,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from ..conferences import available_conferences
from ..models import PaperMeta
from ..storage import PaperStorage
from .export_dialog import ExportDialog
from .settings_dialog import SettingsDialog
from .workers import CancelToken, Worker


@dataclass
class FilterConfig:
    enabled: bool
    field: str
    mode: str
    role: str
    value: str


class FilterRow(QWidget):
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)

        self.enable_checkbox = QCheckBox()
        self.enable_checkbox.setChecked(True)

        self.field_combo = QComboBox()
        self.field_combo.addItems(["All", "Title", "Authors", "Abstract", "Keywords"])

        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["contains", "not contains"])

        self.role_combo = QComboBox()
        self.role_combo.addItems(["Must", "Should", "Must not"])
        self.role_combo.setToolTip("Must = required, Should = optional, Must not = excluded")

        self.text_edit = QLineEdit()

        self.remove_btn = QPushButton("Remove")

        layout.addWidget(self.enable_checkbox)
        layout.addWidget(self.field_combo)
        layout.addWidget(self.mode_combo)
        layout.addWidget(self.role_combo)
        layout.addWidget(self.text_edit)
        layout.addWidget(self.remove_btn)
        self.setLayout(layout)

    def config(self) -> FilterConfig:
        return FilterConfig(
            enabled=self.enable_checkbox.isChecked(),
            field=self.field_combo.currentText().lower(),
            mode=self.mode_combo.currentText().replace(" ", "_"),
            role=self.role_combo.currentText().lower(),
            value=self.text_edit.text().strip(),
        )


class WorkspaceWindow(QMainWindow):
    def __init__(self, conf=None, storage: Optional[PaperStorage] = None) -> None:
        super().__init__()
        self.conf = conf
        self.storage = storage
        self.base_dir: Optional[str] = None
        self.thread_pool = QThreadPool()
        self.available_conf_map = {conf.slug: conf for conf in available_conferences()}
        self._current_rows: List[dict] = []
        self.filter_rows: List[FilterRow] = []
        self.abstract_cancel_token: Optional[CancelToken] = None
        self.pdf_cancel_token: Optional[CancelToken] = None
        self.setWindowTitle("PaperSpider Workspace")
        self._build_ui()
        self._refresh_status()
        if self.storage:
            self._load_papers()

    def _build_ui(self) -> None:
        root = QWidget()
        layout = QVBoxLayout()

        header_layout = QHBoxLayout()
        self.status_label = QLabel("No conference loaded. Click Settings.")
        settings_btn = QPushButton("Settings")
        settings_btn.clicked.connect(self._open_settings)
        self.fetch_btn = QPushButton("Fetch paper list")
        self.fetch_btn.clicked.connect(self._fetch_list)
        header_layout.addWidget(self.status_label)
        header_layout.addStretch()
        header_layout.addWidget(self.fetch_btn)
        header_layout.addWidget(settings_btn)
        layout.addLayout(header_layout)

        filter_container = QWidget()
        filter_layout = QVBoxLayout()
        filter_container.setLayout(filter_layout)
        self.filter_layout = filter_layout

        filter_header = QHBoxLayout()
        add_filter_btn = QPushButton("Add filter")
        add_filter_btn.clicked.connect(self._add_filter)
        apply_filter_btn = QPushButton("Apply filter")
        apply_filter_btn.clicked.connect(self._load_papers)
        clear_filter_btn = QPushButton("Clear filters")
        clear_filter_btn.clicked.connect(self._clear_filters)
        self.should_spin = QSpinBox()
        self.should_spin.setRange(0, 10)
        self.should_spin.setValue(0)
        self.should_spin.setToolTip("Require at least N 'Should' filters to match")
        filter_header.addWidget(add_filter_btn)
        filter_header.addWidget(apply_filter_btn)
        filter_header.addWidget(clear_filter_btn)
        filter_header.addWidget(QLabel("Min should match"))
        filter_header.addWidget(self.should_spin)
        filter_header.addStretch()
        layout.addLayout(filter_header)
        layout.addWidget(filter_container)

        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(
            ["Select", "Title", "Authors", "Abstract", "PDF", "Bibtex"]
        )
        self.table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.table)
        self.table.cellClicked.connect(self._on_table_clicked)
        self.table.cellDoubleClicked.connect(self._on_table_double_clicked)

        select_layout = QHBoxLayout()
        select_all_btn = QPushButton("Select all")
        select_all_btn.clicked.connect(lambda: self._set_selection_state(True))
        select_none_btn = QPushButton("Select none")
        select_none_btn.clicked.connect(lambda: self._set_selection_state(False))
        select_invert_btn = QPushButton("Invert")
        select_invert_btn.clicked.connect(self._invert_selection)
        select_layout.addWidget(select_all_btn)
        select_layout.addWidget(select_none_btn)
        select_layout.addWidget(select_invert_btn)
        select_layout.addStretch()
        layout.addLayout(select_layout)

        action_layout = QHBoxLayout()
        self.abstract_btn = QPushButton("Download abstracts")
        self.abstract_btn.clicked.connect(self._download_abstracts)
        self.pdf_btn = QPushButton("Download PDFs")
        self.pdf_btn.clicked.connect(self._download_pdfs)
        self.bib_btn = QPushButton("Export bibtex")
        self.bib_btn.clicked.connect(self._export_bibtex)
        self.export_btn = QPushButton("Export selected")
        self.export_btn.clicked.connect(self._open_export_dialog)

        action_layout.addWidget(self.abstract_btn)
        action_layout.addWidget(self.pdf_btn)
        action_layout.addWidget(self.bib_btn)
        action_layout.addWidget(self.export_btn)
        layout.addLayout(action_layout)

        self.log_view = QTextEdit()
        self.log_view.setReadOnly(True)
        layout.addWidget(self.log_view)

        root.setLayout(layout)
        self.setCentralWidget(root)

        self._add_filter()

    def _safe_filename(self, title: str, fallback: str) -> str:
        name = title.strip().replace(" ", "_").replace("$", "")
        name = re.sub(r"[\\/:*?\"<>|]", "", name)
        name = re.sub(r"[^A-Za-z0-9._-]+", "_", name)
        name = re.sub(r"_+", "_", name).strip("._-")
        if not name:
            name = fallback
        if len(name) > 120:
            name = name[:120].rstrip("._-")
        return name

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
        self.log_view.append(message)

    def _ensure_ready(self) -> bool:
        if self.storage and self.conf:
            return True
        QMessageBox.warning(self, "Missing", "Please open Settings first.")
        return False

    def _start_worker(self, fn, on_done, on_error, *args) -> None:
        worker = Worker(fn, *args)
        worker.signals.log.connect(self._log)
        worker.signals.finished.connect(on_done)
        worker.signals.error.connect(on_error)
        self.thread_pool.start(worker)

    def _refresh_status(self) -> None:
        if not self.conf or not self.storage:
            self.status_label.setText("No conference loaded. Click Settings.")
            self.fetch_btn.setEnabled(False)
            return
        count = self.storage.count_papers()
        self.status_label.setText(
            f"Loaded: {self.conf.name} {self.storage.year} (papers: {count})"
        )
        self.fetch_btn.setEnabled(True)

    def _open_settings(self) -> None:
        dialog = SettingsDialog(self)
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
        self._refresh_status()
        self._load_papers()

    def _fetch_list(self) -> None:
        if not self._ensure_ready():
            return
        self._start_worker(
            self._fetch_list_task,
            self._on_fetch_done,
            self._on_worker_error,
            self.conf,
            self.storage,
        )
        self._log("Fetching paper list...")

    def _fetch_list_task(self, conf, storage: PaperStorage, log=None) -> int:
        papers = conf.list_papers(storage.year)
        storage.upsert_papers(papers)
        return len(papers)

    def _on_fetch_done(self, count: int) -> None:
        self._log(f"Loaded {count} papers")
        QMessageBox.information(self, "Done", f"Loaded {count} papers")
        self._refresh_status()
        self._load_papers()

    def _add_filter(self) -> None:
        row = FilterRow()
        row.remove_btn.clicked.connect(lambda: self._remove_filter(row))
        self.filter_rows.append(row)
        self.filter_layout.addWidget(row)

    def _remove_filter(self, row: FilterRow) -> None:
        if row in self.filter_rows:
            self.filter_rows.remove(row)
        row.setParent(None)
        row.deleteLater()

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

    def _load_papers(self) -> None:
        if not self.storage:
            self.table.setRowCount(0)
            self._current_rows = []
            return
        rows = self.storage.list_papers()
        filtered = self._apply_filters(rows)
        self._current_rows = filtered
        self.table.setRowCount(0)
        for row in filtered:
            row_idx = self.table.rowCount()
            self.table.insertRow(row_idx)
            select_item = QTableWidgetItem()
            select_item.setFlags(
                select_item.flags() | Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled
            )
            select_item.setCheckState(Qt.CheckState.Unchecked)

            authors = ", ".join(json.loads(row["authors"] or "[]"))
            abstract_status = "Yes" if row["abstract_status"] else "No"
            pdf_status_value = row.get("pdf_status") or 0
            pdf_path = row.get("pdf_path")
            if pdf_status_value and not pdf_path:
                self.storage.mark_pdf_missing(row["paper_id"])
                row["pdf_status"] = 0
                row["pdf_path"] = None
                pdf_status_value = 0
            elif pdf_status_value and pdf_path and not os.path.exists(pdf_path):
                self.storage.mark_pdf_missing(row["paper_id"])
                row["pdf_status"] = 0
                row["pdf_path"] = None
                pdf_status_value = 0
            pdf_status = "Yes" if pdf_status_value and pdf_path else "No"
            bib_path = row.get("bib_path")
            if bib_path and not os.path.exists(bib_path):
                self.storage.mark_bib_missing(row["paper_id"])
                row["bib_path"] = None
                bib_path = None
            bib_status = "Yes" if bib_path else "No"
            self.table.setItem(row_idx, 0, select_item)
            self.table.setItem(row_idx, 1, QTableWidgetItem(row["title"]))
            self.table.setItem(row_idx, 2, QTableWidgetItem(authors))
            abstract_item = QTableWidgetItem(abstract_status)
            if row["abstract_status"]:
                abstract_text = row.get("abstract") or ""
                abstract_item.setToolTip(abstract_text)
            else:
                abstract_item.setToolTip("Click to download abstract")
            self.table.setItem(row_idx, 3, abstract_item)
            pdf_item = QTableWidgetItem(pdf_status)
            if pdf_path:
                pdf_item.setToolTip(f"Double-click to open\nCtrl+Click to reveal\n{pdf_path}")
            else:
                pdf_item.setToolTip("Click to download PDF")
            self.table.setItem(row_idx, 4, pdf_item)
            bib_item = QTableWidgetItem(bib_status)
            if bib_path:
                bib_item.setToolTip(f"Double-click to copy bibtex\nCtrl+Click to reveal\n{bib_path}")
            else:
                bib_item.setToolTip("Click to download bibtex")
            self.table.setItem(row_idx, 5, bib_item)
        self._log(f"Loaded {len(filtered)} papers")

    def _apply_filters(self, rows: List[dict]) -> List[dict]:
        configs = self._filter_configs()
        if not configs:
            return rows

        must = [cfg for cfg in configs if cfg.role == "must"]
        should = [cfg for cfg in configs if cfg.role == "should"]
        must_not = [cfg for cfg in configs if cfg.role == "must not"]
        should_count = len(should)
        self.should_spin.setRange(0, should_count)
        if self.should_spin.value() > should_count:
            self.should_spin.setValue(should_count)
        min_should_match = self.should_spin.value()

        def matches(row: dict, cfg: FilterConfig) -> bool:
            value = cfg.value.lower()
            title = (row.get("title") or "").lower()
            abstract = (row.get("abstract") or "").lower()
            authors = ", ".join(json.loads(row.get("authors") or "[]")).lower()
            keywords = ", ".join(json.loads(row.get("keywords") or "[]")).lower()

            if cfg.field == "title":
                haystack = title
            elif cfg.field == "authors":
                haystack = authors
            elif cfg.field == "abstract":
                haystack = abstract
            elif cfg.field == "keywords":
                haystack = keywords
            else:
                haystack = " ".join([title, authors, abstract, keywords])

            contains = value in haystack
            if cfg.mode == "contains":
                return contains
            return not contains

        filtered = []
        for row in rows:
            if any(matches(row, cfg) for cfg in must_not):
                continue
            if must and not all(matches(row, cfg) for cfg in must):
                continue
            if should and min_should_match > 0:
                match_count = sum(1 for cfg in should if matches(row, cfg))
                if match_count < min_should_match:
                    continue
            filtered.append(row)
        return filtered

    def _on_table_clicked(self, row_idx: int, column: int) -> None:
        if row_idx >= len(self._current_rows):
            return
        row = self._current_rows[row_idx]
        modifiers = QGuiApplication.keyboardModifiers()
        if column == 3:
            if row.get("abstract_status"):
                return
            self._download_abstracts_for_rows([row])
        elif column == 4:
            pdf_path = row.get("pdf_path")
            if modifiers & Qt.KeyboardModifier.ControlModifier and pdf_path:
                self._reveal_in_folder(pdf_path)
                return
            if row.get("pdf_status") and pdf_path:
                return
            self._download_pdfs_for_rows([row])
        elif column == 5:
            bib_path = row.get("bib_path")
            if modifiers & Qt.KeyboardModifier.ControlModifier and bib_path:
                self._reveal_in_folder(bib_path)
                return
            if bib_path:
                return
            self._export_bibtex_for_rows([row])

    def _on_table_double_clicked(self, row_idx: int, column: int) -> None:
        if row_idx >= len(self._current_rows):
            return
        row = self._current_rows[row_idx]
        if column == 4:
            pdf_path = row.get("pdf_path")
            if pdf_path:
                self._open_file(pdf_path)
        elif column == 5:
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

    def _set_selection_state(self, checked: bool) -> None:
        state = Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked
        for row_idx in range(self.table.rowCount()):
            item = self.table.item(row_idx, 0)
            if item:
                item.setCheckState(state)

    def _invert_selection(self) -> None:
        for row_idx in range(self.table.rowCount()):
            item = self.table.item(row_idx, 0)
            if not item:
                continue
            item.setCheckState(
                Qt.CheckState.Unchecked
                if item.checkState() == Qt.CheckState.Checked
                else Qt.CheckState.Checked
            )

    def _selected_rows(self) -> List[dict]:
        selected = []
        for row_idx, row in enumerate(self._current_rows):
            item = self.table.item(row_idx, 0)
            if item and item.checkState() == Qt.CheckState.Checked:
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
            self.abstract_cancel_token.cancel()
            self._log("Canceling abstract download...")
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
        self.abstract_btn.setText("Cancel Download")
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
    ) -> int:
        total = len(rows)
        downloaded = 0
        for idx, row in enumerate(rows, start=1):
            if cancel.cancelled():
                break
            if row.get("abstract_status"):
                continue
            paper = PaperMeta(
                paper_id=row["paper_id"],
                title=row["title"],
                conf=conf.slug,
                year=storage.year,
                detail_url=row.get("detail_url"),
            )
            updated = conf.fetch_details(paper)
            storage.update_details(
                updated.paper_id,
                updated.abstract,
                updated.authors,
                updated.keywords,
                updated.pdf_url,
                updated.bibtex_url,
                updated.bibtex,
            )
            downloaded += 1
            if log:
                log(f"[{idx}/{total}] {updated.title}")
        return downloaded

    def _on_abstracts_done(self, count: int) -> None:
        cancelled = self.abstract_cancel_token.cancelled() if self.abstract_cancel_token else False
        self.abstract_cancel_token = None
        self.abstract_btn.setText("Download abstracts")
        if cancelled:
            QMessageBox.information(self, "Canceled", f"Downloaded {count} abstracts")
        else:
            QMessageBox.information(self, "Done", f"Downloaded {count} abstracts")
        self._load_papers()

    def _download_pdfs(self) -> None:
        if self.pdf_cancel_token:
            self.pdf_cancel_token.cancel()
            self._log("Canceling PDF download...")
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
        self.pdf_btn.setText("Cancel Download")
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
    ) -> int:
        total = len(rows)
        downloaded = 0
        for idx, row in enumerate(rows, start=1):
            if cancel.cancelled():
                break
            if row.get("pdf_status"):
                continue
            paper = PaperMeta(
                paper_id=row["paper_id"],
                title=row.get("title") or "",
                conf=conf.slug,
                year=storage.year,
                detail_url=row.get("detail_url"),
                pdf_url=row.get("pdf_url"),
            )
            data = conf.fetch_pdf(paper)
            base_name = self._safe_filename(row.get("title") or "", paper.paper_id)
            file_path = os.path.join(storage.paths.pdf_dir, f"{base_name}.pdf")
            if os.path.exists(file_path):
                file_path = os.path.join(
                    storage.paths.pdf_dir,
                    f"{base_name}_{paper.paper_id}.pdf",
                )
            with open(file_path, "wb") as f:
                f.write(data)
            storage.mark_pdf_downloaded(paper.paper_id, file_path)
            downloaded += 1
            if log:
                log(f"[{idx}/{total}] {paper.paper_id}")
        return downloaded

    def _on_pdfs_done(self, count: int) -> None:
        cancelled = self.pdf_cancel_token.cancelled() if self.pdf_cancel_token else False
        self.pdf_cancel_token = None
        self.pdf_btn.setText("Download PDFs")
        if cancelled:
            QMessageBox.information(self, "Canceled", f"Downloaded {count} PDFs")
        else:
            QMessageBox.information(self, "Done", f"Downloaded {count} PDFs")
        self._load_papers()

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
        total = len(rows)
        exported = 0
        for idx, row in enumerate(rows, start=1):
            bibtex = row.get("bibtex")
            if not bibtex:
                paper = PaperMeta(
                    paper_id=row["paper_id"],
                    title=row["title"],
                    conf=conf.slug,
                    year=storage.year,
                    detail_url=row.get("detail_url"),
                    bibtex_url=row.get("bibtex_url"),
                )
                try:
                    bibtex = conf.fetch_bibtex(paper)
                except RuntimeError:
                    bibtex = None
            if bibtex:
                base_name = self._safe_filename(row.get("title") or "", row["paper_id"])
                file_path = os.path.join(storage.paths.bib_dir, f"{base_name}.bib")
                if os.path.exists(file_path):
                    file_path = os.path.join(
                        storage.paths.bib_dir,
                        f"{base_name}_{row['paper_id']}.bib",
                    )
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(bibtex)
                storage.mark_bib_exported(row["paper_id"], bibtex, file_path)
                exported += 1
                if log:
                    log(f"[{idx}/{total}] saved bibtex: {row['paper_id']}")
            elif log:
                log(f"[{idx}/{total}] missing bibtex: {row['paper_id']}")
        return exported

    def _on_bibtex_done(self, count: int) -> None:
        QMessageBox.information(self, "Done", f"Exported {count} bibtex files")
        self._load_papers()

    def _on_worker_error(self, message: str) -> None:
        QMessageBox.critical(self, "Error", message)
        self._log(f"Error: {message}")

    def _on_abstracts_error(self, message: str) -> None:
        if self.abstract_cancel_token:
            self.abstract_cancel_token = None
            self.abstract_btn.setText("Download abstracts")
        QMessageBox.critical(self, "Error", message)
        self._log(f"Error: {message}")

    def _on_pdfs_error(self, message: str) -> None:
        if self.pdf_cancel_token:
            self.pdf_cancel_token = None
            self.pdf_btn.setText("Download PDFs")
        QMessageBox.critical(self, "Error", message)
        self._log(f"Error: {message}")
