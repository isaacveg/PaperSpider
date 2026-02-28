# Copyright 2026 Isaacveg
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#     http://www.apache.org/licenses/LICENSE-2.0

from __future__ import annotations

from typing import List

from PyQt6.QtGui import QGuiApplication
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QTextEdit,
)

from ..export_utils import build_export_text


class ExportDialog(QDialog):
    def __init__(self, rows: List[dict], parent=None) -> None:
        super().__init__(parent)
        self.rows = rows
        self.setWindowTitle("Export Selected Papers")
        self.resize(760, 520)
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QGridLayout()

        self.format_combo = QComboBox()
        self.format_combo.addItem("CSV", "csv")
        self.format_combo.addItem("JSON", "json")
        self.format_combo.addItem("Plain text list", "txt")
        self.format_combo.currentIndexChanged.connect(self._on_format_changed)

        self.title_check = QCheckBox("Title")
        self.title_check.setChecked(True)
        self.authors_check = QCheckBox("Authors")
        self.authors_check.setChecked(True)
        self.abstract_check = QCheckBox("Abstract")
        self.abstract_check.setChecked(False)

        generate_btn = QPushButton("Generate")
        generate_btn.clicked.connect(self._generate)
        copy_btn = QPushButton("Copy")
        copy_btn.clicked.connect(self._copy)
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)

        self.output_text = QTextEdit()
        self.output_text.setPlaceholderText("Generated export content will appear here.")

        layout.addWidget(QLabel("Format"), 0, 0)
        layout.addWidget(self.format_combo, 0, 1)

        fields_layout = QHBoxLayout()
        fields_layout.addWidget(self.title_check)
        fields_layout.addWidget(self.authors_check)
        fields_layout.addWidget(self.abstract_check)
        fields_layout.addStretch()
        layout.addWidget(QLabel("Include fields"), 1, 0)
        layout.addLayout(fields_layout, 1, 1)

        buttons = QHBoxLayout()
        buttons.addWidget(generate_btn)
        buttons.addWidget(copy_btn)
        buttons.addStretch()
        buttons.addWidget(close_btn)
        layout.addLayout(buttons, 2, 0, 1, 2)

        layout.addWidget(self.output_text, 3, 0, 1, 2)
        self.setLayout(layout)

    def _on_format_changed(self) -> None:
        fmt = self.format_combo.currentData()
        enable_fields = fmt != "txt"
        self.title_check.setEnabled(enable_fields)
        self.authors_check.setEnabled(enable_fields)
        self.abstract_check.setEnabled(enable_fields)

    def _generate(self) -> None:
        try:
            content = build_export_text(
                rows=self.rows,
                export_format=self.format_combo.currentData(),
                include_title=self.title_check.isChecked(),
                include_authors=self.authors_check.isChecked(),
                include_abstract=self.abstract_check.isChecked(),
            )
        except ValueError as exc:
            QMessageBox.warning(self, "Invalid export options", str(exc))
            return
        self.output_text.setPlainText(content)

    def _copy(self) -> None:
        content = self.output_text.toPlainText()
        if not content:
            return
        QGuiApplication.clipboard().setText(content)
