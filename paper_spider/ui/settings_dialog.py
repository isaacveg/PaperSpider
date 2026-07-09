# Copyright 2026 Isaacveg
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#     http://www.apache.org/licenses/LICENSE-2.0

from __future__ import annotations

from typing import Optional

from PyQt6.QtCore import QSettings, Qt
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

from .theme import ACCENTS, THEMES, appearance_from_values, build_stylesheet
from .window_chrome import apply_window_chrome


class SettingsDialog(QDialog):
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("PaperSpider - Settings")
        self.setMinimumSize(940, 600)
        self.resize(1040, 680)
        self._settings = QSettings("PaperSpider", "PaperSpider")
        apply_window_chrome(self)
        self._build_ui()
        self._load_previous_state()

    def _build_ui(self) -> None:
        root_layout = QVBoxLayout()
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        body = QHBoxLayout()
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(0)

        self.sidebar = self._build_sidebar()
        body.addWidget(self.sidebar)

        content_area = QFrame()
        content_area.setObjectName("settingsContentArea")
        content_layout = QVBoxLayout()
        content_layout.setContentsMargins(20, 18, 28, 18)
        content_layout.setSpacing(14)

        self.content_scroll = QScrollArea()
        self.content_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.content_scroll.setWidgetResizable(True)
        scroll_content = QWidget()
        self.content_cards_layout = QVBoxLayout()
        self.content_cards_layout.setContentsMargins(0, 0, 0, 0)
        self.content_cards_layout.setSpacing(14)

        self.delay_spin = QSpinBox()
        self.delay_spin.setRange(0, 10000)
        self.delay_spin.setValue(100)
        self.delay_spin.setFixedWidth(120)
        self.delay_unit_combo = QComboBox()
        self.delay_unit_combo.addItem("ms")
        self.delay_unit_combo.setMinimumWidth(96)
        request_card = self._settings_card(
            "Request Interval",
            self._field_group(
                [
                    self._setting_row(
                        "Delay Between Requests",
                        "Time to wait between consecutive requests to the server.",
                        self._inline_controls(self.delay_spin, self.delay_unit_combo),
                    )
                ]
            ),
            "◷",
        )
        self.content_cards_layout.addWidget(request_card)

        self.theme_combo = QComboBox()
        self.theme_combo.addItems(THEMES)
        self.theme_combo.currentTextChanged.connect(self._preview_theme)
        self.accent_combo = QComboBox()
        self.accent_combo.addItems(ACCENTS.keys())
        self.accent_combo.currentTextChanged.connect(self._preview_theme)
        appearance_card = self._settings_card(
            "Appearance",
            self._field_group(
                [
                    self._setting_row(
                        "Theme",
                        "Choose the light or dark interface.",
                        self.theme_combo,
                    ),
                    self._setting_row(
                        "Theme Color",
                        "Choose the accent color for buttons and highlights.",
                        self.accent_combo,
                    ),
                ]
            ),
            "◉",
        )
        self.content_cards_layout.addWidget(appearance_card)
        self.content_cards_layout.addStretch()
        scroll_content.setLayout(self.content_cards_layout)
        self.content_scroll.setWidget(scroll_content)

        content_layout.addWidget(self.content_scroll)
        content_area.setLayout(content_layout)
        body.addWidget(content_area, stretch=1)
        root_layout.addLayout(body, stretch=1)
        root_layout.addWidget(self._build_footer())

        self.setLayout(root_layout)

    def _build_sidebar(self) -> QFrame:
        sidebar = QFrame()
        sidebar.setObjectName("settingsSidebar")
        sidebar.setFixedWidth(220)
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 18, 12, 18)
        layout.setSpacing(8)

        self.nav_buttons = [
            self._nav_button("General", active=True),
            self._nav_button("Appearance", active=False),
        ]
        self.nav_buttons[0].clicked.connect(lambda: self._scroll_to_top())
        self.nav_buttons[1].clicked.connect(lambda: self._scroll_to_appearance())
        for button in self.nav_buttons:
            layout.addWidget(button)
        layout.addStretch()
        sidebar.setLayout(layout)
        return sidebar

    def _nav_button(self, text: str, active: bool) -> QPushButton:
        button = QPushButton(text)
        button.setObjectName("settingsNavButton")
        button.setCheckable(False)
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        button.setProperty("active", "true" if active else "false")
        return button

    def _settings_card(self, title: str, body: QWidget, icon_text: str) -> QFrame:
        card = QFrame()
        card.setObjectName("settingsContentCard")
        layout = QVBoxLayout()
        layout.setContentsMargins(18, 16, 18, 18)
        layout.setSpacing(12)

        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 0)
        icon = QLabel(icon_text)
        icon.setObjectName("settingsIcon")
        icon.setFixedWidth(24)
        title_label = QLabel(title)
        title_label.setObjectName("settingsCardTitle")
        header.addWidget(icon)
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
        for row in rows:
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

        self.restore_defaults_btn = QPushButton("Restore Defaults")
        self.restore_defaults_btn.setObjectName("secondaryButton")
        self.restore_defaults_btn.clicked.connect(self._restore_defaults)
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setObjectName("secondaryButton")
        self.cancel_btn.clicked.connect(self.reject)
        self.save_btn = QPushButton("Save / Close")
        self.save_btn.setObjectName("primaryButton")
        self.save_btn.clicked.connect(self._save_and_accept)

        layout.addWidget(self.restore_defaults_btn)
        layout.addStretch()
        layout.addWidget(self.cancel_btn)
        layout.addWidget(self.save_btn)
        footer.setLayout(layout)
        return footer

    def _load_previous_state(self) -> None:
        delay_ms = self._settings.value("request_delay_ms", 100)
        try:
            self.delay_spin.setValue(int(delay_ms))
        except (TypeError, ValueError):
            self.delay_spin.setValue(100)
        theme = str(self._settings.value("appearance/theme", "Light"))
        if theme not in THEMES:
            theme = "Light"
        accent = str(self._settings.value("appearance/accent", "Blue"))
        if accent not in ACCENTS:
            accent = "Blue"
        self.theme_combo.setCurrentText(theme)
        self.accent_combo.setCurrentText(accent)
        self._preview_theme()

    def _preview_theme(self) -> None:
        appearance = appearance_from_values(
            self.theme_combo.currentText(),
            self.accent_combo.currentText(),
        )
        self.setStyleSheet(build_stylesheet(appearance))

    def _restore_defaults(self) -> None:
        self.delay_spin.setValue(100)
        self.theme_combo.setCurrentText("Light")
        self.accent_combo.setCurrentText("Blue")
        self._preview_theme()

    def _save_and_accept(self) -> None:
        self._settings.setValue("request_delay_ms", self.delay_spin.value())
        self._settings.setValue("appearance/theme", self.theme_combo.currentText())
        self._settings.setValue("appearance/accent", self.accent_combo.currentText())
        self.accept()

    def _scroll_to_top(self) -> None:
        self.content_scroll.verticalScrollBar().setValue(0)

    def _scroll_to_appearance(self) -> None:
        self.content_scroll.verticalScrollBar().setValue(
            self.content_scroll.verticalScrollBar().maximum()
        )

    def request_delay_ms(self) -> int:
        return self.delay_spin.value()
