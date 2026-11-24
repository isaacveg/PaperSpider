# Copyright 2026 Isaacveg
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#     http://www.apache.org/licenses/LICENSE-2.0

from __future__ import annotations

from typing import Optional

from PyQt6.QtCore import QSettings, Qt
from PyQt6.QtGui import QGuiApplication
from PyQt6.QtWidgets import (
    QComboBox,
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from .app_settings import APPLICATION, ORGANIZATION, request_delay_ms
from .i18n import tr
from .theme import (
    ACCENTS,
    DEFAULT_ACCENT,
    DEFAULT_THEME,
    THEMES,
    appearance_from_values,
    build_stylesheet,
    selected_theme,
    themed_icon,
)
from .dialog_utils import configure_utility_dialog, finish_utility_dialog


class SettingsDialog(QDialog):
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        configure_utility_dialog(self)
        self.setWindowTitle(tr("PaperSpider - Settings"))
        self.setMinimumSize(640, 440)
        self.resize(720, 520)
        self._settings = QSettings(ORGANIZATION, APPLICATION)
        self._style_hints = None
        self._build_ui()
        self._load_previous_state()
        app = QGuiApplication.instance()
        if app is not None:
            self._style_hints = app.styleHints()
            self._style_hints.colorSchemeChanged.connect(
                self._on_system_color_scheme_changed
            )

    def done(self, result: int) -> None:
        if self._style_hints is not None:
            try:
                self._style_hints.colorSchemeChanged.disconnect(
                    self._on_system_color_scheme_changed
                )
            except (TypeError, RuntimeError):
                pass
            self._style_hints = None
        super().done(result)

    def _build_ui(self) -> None:
        root_layout = QVBoxLayout()
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        content_area = QFrame()
        content_area.setObjectName("settingsContentArea")
        content_layout = QVBoxLayout()
        content_layout.setContentsMargins(24, 20, 24, 20)
        content_layout.setSpacing(14)

        self.content_scroll = QScrollArea()
        self.content_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.content_scroll.setWidgetResizable(True)
        scroll_content = QWidget()
        self.content_cards_layout = QVBoxLayout()
        self.content_cards_layout.setContentsMargins(0, 0, 0, 0)
        self.content_cards_layout.setSpacing(24)

        self.delay_spin = QSpinBox()
        self.delay_spin.setRange(0, 10000)
        self.delay_spin.setValue(100)
        self.delay_spin.setFixedWidth(120)
        self.delay_unit_label = QLabel("ms")
        self.delay_unit_label.setObjectName("settingsUnitLabel")
        self.delay_unit_label.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        self.request_card = self._settings_card(
            tr("Request Interval"),
            self._field_group(
                [
                    self._setting_row(
                        tr("Delay Between Requests"),
                        tr(
                            "Time to wait between consecutive requests to the server."
                        ),
                        self._inline_controls(self.delay_spin, self.delay_unit_label),
                    )
                ]
            ),
            "refresh",
        )
        self.content_cards_layout.addWidget(self.request_card)

        self.theme_combo = QComboBox()
        for theme in THEMES:
            self.theme_combo.addItem(tr(theme), theme)
        self.theme_combo.currentIndexChanged.connect(self._preview_theme)
        self.accent_combo = QComboBox()
        for accent in ACCENTS:
            self.accent_combo.addItem(tr(accent), accent)
        self.accent_combo.currentIndexChanged.connect(self._preview_theme)
        self.appearance_card = self._settings_card(
            tr("Appearance"),
            self._field_group(
                [
                    self._setting_row(
                        tr("Theme"),
                        tr("Follow the system appearance or choose light or dark."),
                        self.theme_combo,
                    ),
                    self._setting_row(
                        tr("Theme Color"),
                        tr("Choose the accent color for buttons and highlights."),
                        self.accent_combo,
                    ),
                ]
            ),
            "appearance",
        )
        self.content_cards_layout.addWidget(self.appearance_card)
        self.content_cards_layout.addStretch()
        scroll_content.setLayout(self.content_cards_layout)
        self.content_scroll.setWidget(scroll_content)
        scroll_content.setAutoFillBackground(False)

        content_layout.addWidget(self.content_scroll)
        content_area.setLayout(content_layout)
        root_layout.addWidget(content_area, stretch=1)
        root_layout.addWidget(self._build_footer())

        finish_utility_dialog(self, root_layout)

    def _settings_card(self, title: str, body: QWidget, icon: str) -> QFrame:
        card = QFrame()
        card.setObjectName("settingsContentCard")
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 0)
        icon_label = QLabel()
        icon_label.setObjectName("settingsIcon")
        icon_label.setFixedSize(20, 20)
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_label.setPixmap(themed_icon(icon).pixmap(18, 18))
        title_label = QLabel(title)
        title_label.setObjectName("settingsCardTitle")
        header.addWidget(icon_label)
        header.addWidget(title_label)
        header.addStretch()

        layout.addLayout(header)
        layout.addWidget(body)
        card.setLayout(layout)
        return card

    def _field_group(self, rows: list[QWidget]) -> QFrame:
        group = QFrame()
        group.setObjectName("settingsFieldGroup")
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        for index, row in enumerate(rows):
            if index:
                divider = QFrame()
                divider.setObjectName("settingsFieldDivider")
                divider.setFrameShape(QFrame.Shape.HLine)
                layout.addWidget(divider)
            layout.addWidget(row)
        group.setLayout(layout)
        return group

    def _setting_row(self, title: str, description: str, control: QWidget) -> QFrame:
        row = QFrame()
        row.setObjectName("settingsFieldRow")
        layout = QHBoxLayout()
        layout.setContentsMargins(18, 14, 18, 14)
        layout.setSpacing(18)

        text_block = QWidget()
        text_block.setObjectName("settingsTextBlock")
        text_layout = QVBoxLayout()
        text_layout.setContentsMargins(0, 0, 0, 0)
        text_layout.setSpacing(3)
        title_label = QLabel(title)
        title_label.setObjectName("settingsFieldTitle")
        description_label = QLabel(description)
        description_label.setObjectName("settingsFieldDescription")
        description_label.setWordWrap(True)
        text_layout.addWidget(title_label)
        text_layout.addWidget(description_label)
        text_block.setLayout(text_layout)

        layout.addWidget(text_block, stretch=1)
        layout.addWidget(control, alignment=Qt.AlignmentFlag.AlignVCenter)
        row.setLayout(layout)
        return row

    def _inline_controls(self, *controls: QWidget) -> QWidget:
        container = QWidget()
        container.setObjectName("settingsInlineControls")
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)
        for control in controls:
            layout.addWidget(control)
        container.setLayout(layout)
        return container

    def _build_footer(self) -> QFrame:
        footer = QFrame()
        footer.setObjectName("settingsFooter")
        layout = QHBoxLayout()
        layout.setContentsMargins(28, 18, 28, 18)
        layout.setSpacing(12)

        self.restore_defaults_btn = QPushButton(tr("Restore Defaults"))
        self.restore_defaults_btn.setObjectName("secondaryButton")
        self.restore_defaults_btn.clicked.connect(self._restore_defaults)
        self.cancel_btn = QPushButton(tr("Cancel"))
        self.cancel_btn.setObjectName("secondaryButton")
        self.cancel_btn.clicked.connect(self.reject)
        self.save_btn = QPushButton(tr("Save / Close"))
        self.save_btn.setObjectName("primaryButton")
        self.save_btn.clicked.connect(self._save_and_accept)

        layout.addWidget(self.restore_defaults_btn)
        layout.addStretch()
        layout.addWidget(self.cancel_btn)
        layout.addWidget(self.save_btn)
        footer.setLayout(layout)
        return footer

    def _load_previous_state(self) -> None:
        self.delay_spin.setValue(request_delay_ms(self._settings))
        theme = selected_theme(self._settings)
        accent = str(self._settings.value("appearance/accent", DEFAULT_ACCENT))
        if accent not in ACCENTS:
            accent = DEFAULT_ACCENT
        self.theme_combo.setCurrentIndex(
            max(0, self.theme_combo.findData(theme))
        )
        self.accent_combo.setCurrentIndex(
            max(0, self.accent_combo.findData(accent))
        )
        self._preview_theme()

    def _preview_theme(self) -> None:
        appearance = appearance_from_values(
            str(self.theme_combo.currentData() or DEFAULT_THEME),
            str(self.accent_combo.currentData() or DEFAULT_ACCENT),
        )
        self.setStyleSheet(build_stylesheet(appearance))

    def _on_system_color_scheme_changed(self, *_args) -> None:
        if self.theme_combo.currentData() == "System":
            self._preview_theme()

    def _restore_defaults(self) -> None:
        self.delay_spin.setValue(100)
        self.theme_combo.setCurrentIndex(
            max(0, self.theme_combo.findData(DEFAULT_THEME))
        )
        self.accent_combo.setCurrentIndex(
            max(0, self.accent_combo.findData(DEFAULT_ACCENT))
        )
        self._preview_theme()

    def _save_and_accept(self) -> None:
        self._settings.setValue("request_delay_ms", self.delay_spin.value())
        self._settings.setValue(
            "appearance/theme",
            str(self.theme_combo.currentData() or DEFAULT_THEME),
        )
        self._settings.setValue(
            "appearance/accent",
            str(self.accent_combo.currentData() or DEFAULT_ACCENT),
        )
        self.accept()

    def request_delay_ms(self) -> int:
        return self.delay_spin.value()
