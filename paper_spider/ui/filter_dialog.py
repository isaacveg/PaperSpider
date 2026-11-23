# Copyright 2026 Isaacveg
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#     http://www.apache.org/licenses/LICENSE-2.0

"""Filter rule editor used by the workspace filter dialog."""

from __future__ import annotations

from typing import List, Optional

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from ..filtering import FilterConfig
from .dialog_utils import configure_utility_dialog
from .i18n import current_language, tr
from .theme import apply_theme

_ROLE_LABELS = {
    "must": "Include",
    "should": "Prefer",
    "must not": "Exclude",
}
_FIELD_LABELS = {
    "all": "Any field",
    "title": "Title",
    "category": "Category",
    "authors": "Authors",
    "abstract": "Abstract",
    "keywords": "Keywords",
}
_MODE_LABELS = {
    "contains": "contains",
    "not_contains": "does not contain",
}


def filter_role_label(role: str) -> str:
    return tr(_ROLE_LABELS.get(role, role))


class FilterRow(QFrame):
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("filterRuleCard")
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        layout = QHBoxLayout()
        layout.setContentsMargins(12, 5, 8, 5)
        layout.setSpacing(8)

        self.enable_checkbox = QCheckBox()
        self.enable_checkbox.setChecked(True)
        self.enable_checkbox.setFixedWidth(24)

        self.role_combo = QComboBox()
        for value, label in _ROLE_LABELS.items():
            self.role_combo.addItem(tr(label), value)
        self.role_combo.setObjectName("filterRoleCombo")
        self.role_combo.setFixedWidth(96)
        self.role_combo.setToolTip(
            tr("Include = required, Prefer = optional, Exclude = remove matches")
        )

        self.field_combo = QComboBox()
        for value, label in _FIELD_LABELS.items():
            self.field_combo.addItem(tr(label), value)
        self.field_combo.setObjectName("filterFieldCombo")
        self.field_combo.setMinimumWidth(96)
        self.field_combo.setSizePolicy(
            QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed
        )

        self.mode_combo = QComboBox()
        for value, label in _MODE_LABELS.items():
            self.mode_combo.addItem(tr(label), value)
        self.mode_combo.setObjectName("filterModeCombo")
        self.mode_combo.setMinimumWidth(
            100 if current_language() == "zh" else 146
        )
        self.mode_combo.setSizePolicy(
            QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed
        )

        self.text_edit = QLineEdit()
        self.text_edit.setPlaceholderText(tr("keyword, author, title..."))
        self.text_edit.setMinimumWidth(100)
        self.text_edit.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )

        self.remove_btn = QPushButton("×")
        self.remove_btn.setObjectName("compactDeleteButton")
        self.remove_btn.setToolTip(tr("Remove this rule"))
        self.remove_btn.setFixedWidth(22)

        layout.addWidget(self.enable_checkbox)
        layout.addWidget(self.role_combo)
        layout.addWidget(self.field_combo)
        layout.addWidget(self.mode_combo)
        layout.addWidget(self.text_edit, stretch=1)
        layout.addWidget(self.remove_btn)
        self.setLayout(layout)

    def set_config(self, config: FilterConfig) -> None:
        self.enable_checkbox.setChecked(config.enabled)
        role_index = self.role_combo.findData(config.role)
        if role_index >= 0:
            self.role_combo.setCurrentIndex(role_index)
        field_index = self.field_combo.findData(config.field)
        if field_index >= 0:
            self.field_combo.setCurrentIndex(field_index)
        mode_index = self.mode_combo.findData(config.mode)
        if mode_index >= 0:
            self.mode_combo.setCurrentIndex(mode_index)
        self.text_edit.setText(config.value)

    def config(self) -> FilterConfig:
        return FilterConfig(
            enabled=self.enable_checkbox.isChecked(),
            field=str(self.field_combo.currentData()),
            mode=str(self.mode_combo.currentData()),
            role=str(self.role_combo.currentData()),
            value=self.text_edit.text().strip(),
        )


class FilterDialog(QDialog):
    def __init__(
        self,
        parent: Optional[QWidget] = None,
        configs: Optional[List[FilterConfig]] = None,
        min_should_match: int = 0,
    ) -> None:
        super().__init__(parent)
        configure_utility_dialog(self)
        self.setWindowTitle(tr("Filter papers"))
        self.resize(760, 620)
        self._rows: List[FilterRow] = []
        self._build_ui()
        for config in configs or []:
            self._add_row(config)
        if not self._rows:
            self._add_row()
        self.should_spin.setValue(min_should_match)
        self._update_min_row()
        apply_theme(self)

    def _build_ui(self) -> None:
        layout = QVBoxLayout()
        layout.setContentsMargins(22, 18, 22, 16)
        layout.setSpacing(12)

        self.title_label = QLabel(tr("Filter papers"))
        self.title_label.setObjectName("filterTitleLabel")
        self.hint_label = QLabel(
            tr(
                "Include rules must match. Prefer rules can contribute to a minimum. "
                "Exclude rules remove matches."
            )
        )
        self.hint_label.setObjectName("filterHintLabel")
        self.hint_label.setWordWrap(True)

        toolbar = QHBoxLayout()
        self.add_filter_btn = QPushButton(tr("Add rule"))
        self.add_filter_btn.setObjectName("secondaryButton")
        self.add_filter_btn.setToolTip(tr("Add an Include rule"))
        self.add_filter_btn.clicked.connect(lambda: self._add_row())
        toolbar.addWidget(self.add_filter_btn)
        toolbar.addStretch(1)

        self.min_preferred_row = QWidget()
        self.min_preferred_row.setObjectName("minPreferredRow")
        min_layout = QHBoxLayout()
        min_layout.setContentsMargins(0, 0, 0, 0)
        self.min_preferred_label = QLabel(tr("Minimum preferred matches"))
        self.should_spin = QSpinBox()
        self.should_spin.setRange(0, 10)
        self.should_spin.setValue(0)
        self.should_spin.setToolTip(
            tr("Require at least N Prefer rules to match")
        )
        min_layout.addWidget(self.min_preferred_label)
        min_layout.addWidget(self.should_spin)
        self.min_preferred_row.setLayout(min_layout)
        toolbar.addWidget(self.min_preferred_row)
        layout.addWidget(self.title_label)
        layout.addWidget(self.hint_label)
        layout.addLayout(toolbar)

        container = QWidget()
        self.filter_layout = QVBoxLayout()
        self.filter_layout.setContentsMargins(0, 0, 0, 0)
        self.filter_layout.setSpacing(8)
        self.filter_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        container.setLayout(self.filter_layout)
        self.filter_scroll = QScrollArea()
        self.filter_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.filter_scroll.setWidgetResizable(True)
        self.filter_scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self.filter_scroll.setWidget(container)
        layout.addWidget(self.filter_scroll, stretch=1)

        footer = QHBoxLayout()
        self.clear_filter_btn = QPushButton(tr("Clear"))
        self.clear_filter_btn.setObjectName("secondaryButton")
        self.clear_filter_btn.clicked.connect(self._clear_filters)
        self.cancel_btn = QPushButton(tr("Cancel"))
        self.cancel_btn.setObjectName("secondaryButton")
        self.cancel_btn.clicked.connect(self.reject)
        self.apply_filter_btn = QPushButton(tr("Apply"))
        self.apply_filter_btn.setObjectName("primaryButton")
        self.apply_filter_btn.clicked.connect(self.accept)
        footer.addWidget(self.clear_filter_btn)
        footer.addStretch(1)
        footer.addWidget(self.cancel_btn)
        footer.addWidget(self.apply_filter_btn)
        layout.addLayout(footer)
        self.setLayout(layout)

    def _add_row(self, config: Optional[FilterConfig] = None) -> FilterRow:
        row = FilterRow(self)
        if config is not None:
            row.set_config(config)
        row.remove_btn.clicked.connect(lambda: self._remove_row(row))
        row.enable_checkbox.toggled.connect(self._update_min_row)
        row.role_combo.currentIndexChanged.connect(self._update_min_row)
        row.text_edit.textChanged.connect(self._update_min_row)
        self._rows.append(row)
        self.filter_layout.addWidget(row)
        self._update_min_row()
        return row

    def _remove_row(self, row: FilterRow) -> None:
        if row in self._rows:
            self._rows.remove(row)
        row.setParent(None)
        row.deleteLater()
        self._update_min_row()

    def _clear_filters(self) -> None:
        for row in list(self._rows):
            self._remove_row(row)
        self._add_row()

    def _should_count(self) -> int:
        return sum(
            1
            for row in self._rows
            if row.enable_checkbox.isChecked()
            and row.role_combo.currentData() == "should"
            and row.text_edit.text().strip()
        )

    def _update_min_row(self) -> None:
        count = self._should_count()
        self.should_spin.setRange(0, count)
        if self.should_spin.value() > count:
            self.should_spin.setValue(count)
        self.min_preferred_row.setVisible(count > 0)

    def filter_configs(self) -> List[FilterConfig]:
        return [
            row.config()
            for row in self._rows
            if row.enable_checkbox.isChecked() and row.text_edit.text().strip()
        ]

    def min_should_match(self) -> int:
        return min(self.should_spin.value(), self._should_count())