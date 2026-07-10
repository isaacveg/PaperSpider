# Copyright 2026 Isaacveg
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#     http://www.apache.org/licenses/LICENSE-2.0

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from PyQt6.QtCore import QSettings
from PyQt6.QtWidgets import QWidget

from .window_chrome import apply_window_chrome


THEMES = ("Light", "Dark")
ACCENTS = {
    "Blue": "#0b6bff",
    "Green": "#16a34a",
    "Purple": "#7c3aed",
    "Orange": "#ea580c",
    "Slate": "#475569",
}


@dataclass(frozen=True)
class Appearance:
    theme: str
    accent: str
    accent_color: str
    background: str
    surface: str
    surface_alt: str
    border: str
    text: str
    muted: str


def appearance_from_values(theme: str, accent: str) -> Appearance:
    if theme not in THEMES:
        theme = "Light"
    if accent not in ACCENTS:
        accent = "Blue"
    dark = theme == "Dark"
    return Appearance(
        theme=theme,
        accent=accent,
        accent_color=ACCENTS[accent],
        background="#111827" if dark else "#f8fafc",
        surface="#1f2937" if dark else "#ffffff",
        surface_alt="#273244" if dark else "#f1f5f9",
        border="#374151" if dark else "#dbe3ec",
        text="#f9fafb" if dark else "#111827",
        muted="#cbd5e1" if dark else "#64748b",
    )


def load_appearance(settings: QSettings) -> Appearance:
    theme = str(settings.value("appearance/theme", "Light"))
    accent = str(settings.value("appearance/accent", "Blue"))
    return appearance_from_values(theme, accent)


def build_stylesheet(appearance: Appearance) -> str:
    dark = appearance.theme == "Dark"
    selection_bg = "#244365" if dark else "#eaf3ff"
    hover_bg = "#26364a" if dark else "#f6faff"
    secondary_bg = "#1f2937" if dark else "#ffffff"
    secondary_hover_bg = "#273244" if dark else "#f8fbff"
    disabled_bg = "#182231" if dark else "#eef2f6"
    disabled_text = "#718096" if dark else "#9aa6b2"
    disabled_border = "#2b3748" if dark else "#d8e0e8"
    scrollbar_handle = "#64748b" if dark else "#cbd5e1"
    scrollbar_hover = "#94a3b8" if dark else "#94a3b8"
    arrow_icon = (
        Path(__file__).with_name("assets") / ("chevron-down-dark.svg" if dark else "chevron-down-light.svg")
    ).as_posix()
    return f"""
    QWidget {{
        background: {appearance.background};
        color: {appearance.text};
        font-size: 13px;
    }}
    QLabel {{
        background: transparent;
        border: 0;
    }}
    QFrame, QGroupBox, QListWidget, QTableView, QTextEdit {{
        background: {appearance.surface};
        border: 1px solid {appearance.border};
        border-radius: 8px;
    }}
    QLabel {{
        background: transparent;
        border: 0;
        border-radius: 0;
    }}
    QTableView {{
        alternate-background-color: {appearance.surface_alt};
        gridline-color: {appearance.border};
        selection-background-color: {selection_bg};
        selection-color: {appearance.text};
    }}
    QTableView::item {{
        background: transparent;
    }}
    QCheckBox::indicator, QTableView::indicator {{
        width: 14px;
        height: 14px;
        border: 1px solid {appearance.border};
        border-radius: 3px;
        background: {appearance.surface};
    }}
    QCheckBox::indicator:checked, QTableView::indicator:checked {{
        background: {appearance.accent_color};
        border-color: {appearance.accent_color};
    }}
    QGroupBox {{
        margin-top: 12px;
        padding: 14px 10px 10px 10px;
        font-weight: 600;
    }}
    QGroupBox::title {{
        subcontrol-origin: margin;
        left: 12px;
        padding: 0 4px;
    }}
    QLineEdit, QComboBox, QSpinBox {{
        background: {appearance.surface};
        color: {appearance.text};
        border: 1px solid {appearance.border};
        border-radius: 6px;
        padding: 5px 10px;
        min-height: 24px;
    }}
    QComboBox {{
        padding-right: 30px;
    }}
    QComboBox::drop-down {{
        subcontrol-origin: padding;
        subcontrol-position: top right;
        width: 28px;
        border: 0;
        border-top-right-radius: 6px;
        border-bottom-right-radius: 6px;
        background: transparent;
    }}
    QComboBox::down-arrow {{
        image: url({arrow_icon});
        width: 14px;
        height: 14px;
    }}
    QComboBox:on, QSpinBox:focus, QLineEdit:focus {{
        border-color: {appearance.accent_color};
    }}
    QComboBox QAbstractItemView {{
        background: {appearance.surface};
        color: {appearance.text};
        border: 1px solid {appearance.border};
        border-radius: 8px;
        padding: 4px;
        outline: 0;
        selection-background-color: {selection_bg};
        selection-color: {appearance.text};
    }}
    QSpinBox {{
        padding-right: 22px;
    }}
    QSpinBox::up-button, QSpinBox::down-button {{
        subcontrol-origin: border;
        width: 20px;
        border: 0;
        background: transparent;
    }}
    QSpinBox::up-button {{
        subcontrol-position: top right;
        border-top-right-radius: 6px;
    }}
    QSpinBox::down-button {{
        subcontrol-position: bottom right;
        border-bottom-right-radius: 6px;
    }}
    QPushButton {{
        background: {appearance.surface};
        color: {appearance.text};
        border: 1px solid {appearance.border};
        border-radius: 6px;
        padding: 5px 12px;
    }}
    QPushButton:hover {{
        border-color: {appearance.accent_color};
    }}
    QPushButton:disabled {{
        background: {disabled_bg};
        color: {disabled_text};
        border-color: {disabled_border};
    }}
    QPushButton#primaryButton {{
        background: {appearance.accent_color};
        color: white;
        border-color: {appearance.accent_color};
        font-weight: 600;
    }}
    QPushButton#primaryButton:hover {{
        background: {appearance.accent_color};
        border-color: {appearance.accent_color};
    }}
    QPushButton#primaryButton:disabled {{
        background: {disabled_bg};
        color: {disabled_text};
        border-color: {disabled_border};
        font-weight: 600;
    }}
    QPushButton#secondaryButton {{
        background: {secondary_bg};
        color: {appearance.text};
        border: 1px solid {appearance.border};
        border-radius: 6px;
        padding: 5px 12px;
        font-weight: 500;
    }}
    QPushButton#secondaryButton:hover {{
        background: {secondary_hover_bg};
        border-color: {appearance.accent_color};
    }}
    QPushButton#secondaryButton:disabled {{
        background: {disabled_bg};
        color: {disabled_text};
        border-color: {disabled_border};
    }}
    QPushButton#toolbarButton {{
        background: {secondary_bg};
        color: {appearance.text};
        border: 1px solid {appearance.border};
        border-radius: 6px;
        padding: 5px 10px;
    }}
    QPushButton#datasetButton {{
        background: {appearance.surface};
        color: {appearance.text};
        border: 1px solid {appearance.border};
        border-radius: 7px;
        padding: 5px 12px;
        text-align: left;
        font-weight: 600;
        min-height: 24px;
    }}
    QPushButton#datasetButton:hover {{
        background: {hover_bg};
        border-color: {appearance.accent_color};
    }}
    QPushButton#linkButton {{
        border-color: transparent;
        background: transparent;
        color: {appearance.accent_color};
        font-weight: 600;
    }}
    QPushButton#datasetDeleteButton, QPushButton#compactDeleteButton {{
        padding: 0;
        min-width: 22px;
        max-width: 24px;
        min-height: 22px;
        color: {appearance.muted};
    }}
    QLabel#brandLabel {{
        background: transparent;
        border: 0;
        font-size: 15px;
        font-weight: 700;
    }}
    QLabel#mutedLabel {{
        color: {appearance.muted};
    }}
    QLabel#filterTitleLabel {{
        background: transparent;
        border: 0;
        padding: 0;
        font-weight: 700;
        font-size: 15px;
    }}
    QLabel#filterHintLabel {{
        background: transparent;
        border: 0;
        padding: 0;
        color: {appearance.muted};
        line-height: 1.25;
    }}
    QLabel#summaryCard {{
        background: {appearance.surface};
        color: {appearance.text};
        border: 1px solid {appearance.border};
        border-radius: 8px;
        padding: 7px 10px;
    }}
    QFrame#summaryStatsCard {{
        background: {appearance.surface};
        border: 1px solid {appearance.border};
        border-radius: 8px;
    }}
    QWidget#summaryStat {{
        background: transparent;
        border: 0;
    }}
    QLabel#summaryStatLabel {{
        background: transparent;
        border: 0;
        color: {appearance.muted};
        font-size: 11px;
    }}
    QLabel#summaryStatValue {{
        background: transparent;
        border: 0;
        color: {appearance.text};
        font-size: 14px;
        font-weight: 700;
    }}
    QLabel#detailsFeedbackLabel {{
        color: {appearance.accent_color};
        background: transparent;
        border: 0;
    }}
    QLabel#datasetStatusFetched {{
        color: #15803d;
        background: #dcfce7;
        border: 1px solid #bbf7d0;
        border-radius: 6px;
        padding: 3px 8px;
    }}
    QLabel#datasetStatusUnfetched {{
        color: #92400e;
        background: #fef3c7;
        border: 1px solid #fde68a;
        border-radius: 6px;
        padding: 3px 8px;
    }}
    QHeaderView::section {{
        background: {appearance.surface_alt};
        color: {appearance.text};
        border: 0;
        border-bottom: 1px solid {appearance.border};
        padding: 6px;
        font-weight: 600;
    }}
    QListWidget::item:selected, QTableView::item:selected,
    QTableView::item:selected:active, QTableView::item:selected:!active {{
        background: {selection_bg};
        color: {appearance.text};
    }}
    QSplitter::handle {{
        background: {appearance.border};
    }}
    QFrame#filterSidebar {{
        border: 0;
        border-right: 1px solid {appearance.border};
        background: {appearance.surface_alt};
    }}
    QFrame#filterRuleCard {{
        border: 1px solid {appearance.border};
        border-radius: 6px;
        background: {appearance.surface};
        margin-top: 4px;
    }}
    QWidget#selectionControls QPushButton {{
        background: {secondary_bg};
        border: 1px solid {appearance.border};
    }}
    QFrame#settingsSidebar {{
        background: {appearance.surface};
        border: 0;
        border-right: 1px solid {appearance.border};
        border-radius: 0;
    }}
    QPushButton#settingsNavButton {{
        background: transparent;
        color: {appearance.text};
        border: 0;
        border-left: 3px solid transparent;
        border-radius: 0;
        padding: 10px 14px;
        text-align: left;
        font-size: 14px;
        font-weight: 500;
    }}
    QPushButton#settingsNavButton:hover {{
        background: {hover_bg};
        border-left-color: {appearance.border};
    }}
    QPushButton#settingsNavButton[active="true"] {{
        background: {selection_bg};
        color: {appearance.accent_color};
        border-left-color: {appearance.accent_color};
        font-weight: 700;
    }}
    QFrame#settingsContentArea {{
        background: {appearance.background};
        border: 0;
        border-radius: 0;
    }}
    QFrame#settingsContentCard {{
        background: {appearance.surface};
        border: 1px solid {appearance.border};
        border-radius: 8px;
    }}
    QFrame#settingsFieldGroup {{
        background: {appearance.surface};
        border: 1px solid {appearance.border};
        border-radius: 8px;
    }}
    QFrame#settingsFieldRow {{
        background: {appearance.surface};
        border: 0;
        border-radius: 0;
    }}
    QWidget#settingsTextBlock, QWidget#settingsInlineControls {{
        background: transparent;
        border: 0;
    }}
    QFrame#settingsFooter {{
        background: {appearance.surface};
        border: 0;
        border-top: 1px solid {appearance.border};
        border-radius: 0;
    }}
    QLabel#settingsCardTitle, QLabel#settingsFieldTitle {{
        background: transparent;
        border: 0;
        color: {appearance.text};
        font-weight: 700;
    }}
    QLabel#settingsCardTitle {{
        font-size: 15px;
    }}
    QLabel#settingsFieldDescription {{
        background: transparent;
        border: 0;
        color: {appearance.muted};
    }}
    QLabel#settingsIcon {{
        background: transparent;
        border: 0;
        color: {appearance.accent_color};
    }}
    QLabel#settingsUnitLabel {{
        background: transparent;
        border: 0;
        color: {appearance.text};
        padding: 0 6px;
        font-weight: 600;
        min-width: 28px;
    }}
    QFrame#framelessTitleBar {{
        background: {appearance.surface};
        border: 0;
        border-bottom: 1px solid {appearance.border};
        border-radius: 0;
    }}
    QLabel#framelessTitleLabel {{
        background: transparent;
        border: 0;
        color: {appearance.text};
        font-weight: 700;
    }}
    QWidget#windowControls {{
        background: transparent;
        border: 0;
    }}
    QToolButton#trafficCloseButton,
    QToolButton#trafficMinimizeButton,
    QToolButton#trafficZoomButton {{
        border: 0;
        border-radius: 6px;
        min-width: 12px;
        max-width: 12px;
        min-height: 12px;
        max-height: 12px;
        padding: 0;
    }}
    QToolButton#trafficCloseButton {{
        background: #ff5f57;
    }}
    QToolButton#trafficMinimizeButton {{
        background: #ffbd2e;
    }}
    QToolButton#trafficZoomButton {{
        background: #28c840;
    }}
    QToolButton#windowMinimizeButton,
    QToolButton#windowMaximizeButton,
    QToolButton#windowCloseButton {{
        background: transparent;
        color: {appearance.text};
        border: 0;
        border-radius: 5px;
        min-width: 34px;
        min-height: 26px;
        padding: 0;
        font-weight: 600;
    }}
    QToolButton#windowMinimizeButton:hover,
    QToolButton#windowMaximizeButton:hover {{
        background: {hover_bg};
    }}
    QToolButton#windowCloseButton:hover {{
        background: #dc2626;
        color: white;
    }}
    QProgressBar {{
        background: {appearance.surface};
        color: {appearance.muted};
        border: 1px solid {appearance.border};
        border-radius: 5px;
        min-height: 8px;
        max-height: 10px;
        text-align: center;
    }}
    QProgressBar::chunk {{
        background: {appearance.accent_color};
        border-radius: 4px;
    }}
    QScrollBar:vertical {{
        background: transparent;
        border: 0;
        width: 8px;
        margin: 2px;
    }}
    QScrollBar::handle:vertical {{
        background: {scrollbar_handle};
        border-radius: 4px;
        min-height: 28px;
    }}
    QScrollBar::handle:vertical:hover {{
        background: {scrollbar_hover};
    }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
        background: transparent;
        border: 0;
        height: 0;
    }}
    QScrollBar::up-arrow:vertical, QScrollBar::down-arrow:vertical {{
        background: transparent;
        border: 0;
        width: 0;
        height: 0;
        image: none;
    }}
    QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
        background: transparent;
    }}
    QScrollBar:horizontal {{
        background: transparent;
        border: 0;
        height: 8px;
        margin: 2px;
    }}
    QScrollBar::handle:horizontal {{
        background: {scrollbar_handle};
        border-radius: 4px;
        min-width: 28px;
    }}
    QScrollBar::handle:horizontal:hover {{
        background: {scrollbar_hover};
    }}
    QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
        background: transparent;
        border: 0;
        width: 0;
    }}
    QScrollBar::left-arrow:horizontal, QScrollBar::right-arrow:horizontal {{
        background: transparent;
        border: 0;
        width: 0;
        height: 0;
        image: none;
    }}
    QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{
        background: transparent;
    }}
    """


def apply_theme(widget: QWidget, settings: QSettings | None = None) -> Appearance:
    appearance = load_appearance(settings or QSettings("PaperSpider", "PaperSpider"))
    apply_window_chrome(widget)
    widget.setStyleSheet(build_stylesheet(appearance))
    return appearance
