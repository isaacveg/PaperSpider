# Copyright 2026 Isaacveg
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#     http://www.apache.org/licenses/LICENSE-2.0

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from PyQt6.QtCore import QSettings, Qt
from PyQt6.QtGui import QColor, QGuiApplication, QIcon, QPalette
from PyQt6.QtWidgets import QWidget

THEMES = ("System", "Light", "Dark")
RESOLVED_THEMES = ("Light", "Dark")
DEFAULT_THEME = "Light"
DEFAULT_ACCENT = "Forest"
ACCENTS = {
    "Forest": "#1f5c3a",
    "Blue": "#0b6bff",
    "Green": "#16a34a",
    "Purple": "#7c3aed",
    "Orange": "#ea580c",
    "Slate": "#475569",
}
_DARK_ACCENTS = {
    "Forest": "#5fa87d",
    "Blue": "#4d94ff",
    "Green": "#4ade80",
    "Purple": "#a78bfa",
    "Orange": "#fb923c",
    "Slate": "#94a3b8",
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


def system_theme() -> str:
    """Return the current system color scheme as Light or Dark."""

    app = QGuiApplication.instance()
    if app is None:
        return "Light"
    scheme = app.styleHints().colorScheme()
    if scheme == Qt.ColorScheme.Dark:
        return "Dark"
    if scheme == Qt.ColorScheme.Light:
        return "Light"
    window = app.palette().color(QPalette.ColorRole.Window)
    return "Dark" if window.lightness() < 128 else "Light"


def resolve_theme(theme: str, system_theme_name: Optional[str] = None) -> str:
    """Resolve a theme setting, following the system for System."""

    if theme == "System":
        resolved = (
            system_theme_name
            if system_theme_name in RESOLVED_THEMES
            else system_theme()
        )
    else:
        resolved = theme
    return resolved if resolved in RESOLVED_THEMES else "Light"


def selected_theme(settings: QSettings) -> str:
    """Return the saved theme choice, defaulting to Light."""

    theme = str(settings.value("appearance/theme", DEFAULT_THEME))
    return theme if theme in THEMES else DEFAULT_THEME


def appearance_from_values(
    theme: str,
    accent: str,
    system_theme_name: Optional[str] = None,
) -> Appearance:
    if theme not in THEMES:
        theme = DEFAULT_THEME
    if accent not in ACCENTS:
        accent = DEFAULT_ACCENT
    resolved = resolve_theme(theme, system_theme_name)
    dark = resolved == "Dark"
    return Appearance(
        theme=resolved,
        accent=accent,
        accent_color=(
            _DARK_ACCENTS[accent] if dark else ACCENTS[accent]
        ),
        background="#1b1c1b" if dark else "#f8f8fa",
        surface="#242624" if dark else "#ffffff",
        surface_alt="#2c2f2c" if dark else "#f2f2f5",
        border="#3b3f3b" if dark else "#e4e4e8",
        text="#f1f0e9" if dark else "#202024",
        muted="#b1b3aa" if dark else "#6c6e74",
    )


def load_appearance(settings: QSettings) -> Appearance:
    theme = selected_theme(settings)
    accent = str(settings.value("appearance/accent", DEFAULT_ACCENT))
    return appearance_from_values(theme, accent)


def current_appearance() -> Appearance:
    """Return the appearance currently saved for the application."""

    return load_appearance(QSettings("PaperSpider", "PaperSpider"))


def themed_icon(name: str, theme: str | None = None) -> QIcon:
    """Load a light or dark line icon from the UI assets folder."""

    resolved = theme if theme in RESOLVED_THEMES else current_appearance().theme
    suffix = "dark" if resolved == "Dark" else "light"
    path = Path(__file__).with_name("assets") / f"{name}-{suffix}.svg"
    return QIcon(path.as_posix())


def availability_icon(available: bool, theme: str | None = None) -> QIcon:
    """Return a check or dash icon for abstract/PDF availability."""

    return themed_icon("check" if available else "dash", theme)


def build_stylesheet(appearance: Appearance) -> str:
    dark = appearance.theme == "Dark"
    selection_bg = "#34343a" if dark else "#e3e3e8"
    hover_bg = "#2b2b2e" if dark else "#f2f2f5"
    secondary_bg = appearance.surface
    secondary_hover_bg = "#2e2e32" if dark else "#f2f2f5"
    disabled_bg = "#202023" if dark else "#eeeef1"
    disabled_text = "#7d7d82" if dark else "#9b9da3"
    disabled_border = "#343438" if dark else "#dedee3"
    scrollbar_handle = "#66666b" if dark else "#c7c8cd"
    scrollbar_hover = "#8b8b90" if dark else "#a9abb1"
    status_fetched = "#8fd3a3" if dark else "#2e7d4f"
    sidebar_bg = "#202022" if dark else appearance.background
    sidebar_hover = "#2b2b2e" if dark else "#ececef"
    sidebar_selected = "#34343a" if dark else "#e2e2e7"
    sidebar_selected_text = appearance.text
    chip_must = "#2e2e32" if dark else "#ededf0"
    chip_should = "#34343a" if dark else "#e4e4e9"
    chip_must_not = "#3a3a3d" if dark else "#e9e9ed"
    primary_text = "#101712" if dark else "#ffffff"
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
        combobox-popup: 0;
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
    QLineEdit#quickFilterEdit {{
        min-width: 210px;
        border-radius: 8px;
        padding-left: 12px;
    }}
    QComboBox#filterRoleCombo {{
        color: {appearance.accent_color};
        font-size: 12px;
        font-weight: 700;
        padding-left: 5px;
        padding-right: 19px;
    }}
    QComboBox#filterRoleCombo::drop-down {{
        width: 18px;
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
    QComboBoxPrivateContainer {{
        background: {appearance.surface};
        border: 1px solid {appearance.border};
        border-radius: 7px;
        padding: 0;
    }}
    QComboBox#filterFieldCombo, QComboBox#filterModeCombo {{
        padding-left: 6px;
        padding-right: 22px;
    }}
    QComboBox#filterFieldCombo::drop-down,
    QComboBox#filterModeCombo::drop-down {{
        width: 22px;
    }}
    QComboBox#filterModeCombo {{
        font-size: 12px;
        padding-left: 5px;
        padding-right: 19px;
    }}
    QComboBox#filterModeCombo::drop-down {{
        width: 18px;
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
        color: {primary_text};
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
    QPushButton#datasetRefreshButton {{
        background: transparent;
        color: {appearance.text};
        border: 1px solid {appearance.border};
        border-radius: 12px;
        padding: 1px 10px;
        min-height: 18px;
        max-height: 20px;
        font-weight: 500;
    }}
    QPushButton#datasetRefreshButton:hover {{
        background: {hover_bg};
        border-color: {appearance.accent_color};
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
    QWidget#minPreferredRow {{
        background: transparent;
        border: 0;
    }}
    QLabel#detailsFeedbackLabel {{
        color: {appearance.accent_color};
        background: transparent;
        border: 0;
    }}
    QLabel#datasetStatusFetched {{
        color: {status_fetched};
        background: transparent;
        border: 0;
        padding: 0 4px;
        font-weight: 600;
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
    QSplitter::handle:hover {{
        background: {appearance.accent_color};
    }}
    QFrame#filterRuleCard {{
        border: 1px solid {appearance.border};
        border-radius: 6px;
        background: {appearance.surface};
        margin-top: 4px;
    }}
    QWidget#workspaceActionBar QPushButton {{
        padding-left: 8px;
        padding-right: 8px;
    }}
    QFrame#newDatasetPanel {{
        background: {appearance.surface_alt};
        border: 1px solid {appearance.border};
        border-radius: 8px;
    }}
    QLabel#newDatasetLabel {{
        color: {appearance.text};
        font-weight: 700;
    }}
    QDialog#utilityDialog, QMessageBox#messageDialog {{
        background: {appearance.background};
        border: 1px solid {appearance.border};
        border-radius: 10px;
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
    QFrame#settingsFieldDivider {{
        background: {appearance.border};
        border: 0;
        min-height: 1px;
        max-height: 1px;
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
    QWidget#appSidebar {{
        background: {sidebar_bg};
        border: 0;
    }}
    QScrollArea#sidebarScroll, QScrollArea#sidebarScroll QWidget,
    QWidget#sidebarScrollContent {{
        background: transparent;
        border: 0;
    }}
    QScrollArea#sidebarScroll > QWidget > QWidget {{
        background: transparent;
    }}
    QLabel#brandLabel {{
        font-size: 20px;
        font-weight: 700;
        color: {appearance.text};
    }}
    QPushButton#sidebarItem, QPushButton#sidebarSettings {{
        background: transparent;
        border: 0;
        border-radius: 9px;
        padding: 8px 10px;
        text-align: left;
        color: {appearance.text};
        font-weight: 500;
        min-height: 22px;
    }}
    QPushButton#sidebarItem:hover, QPushButton#sidebarSettings:hover {{
        background: {sidebar_hover};
    }}
    QPushButton#sidebarItem:checked {{
        background: {sidebar_selected};
        color: {sidebar_selected_text};
        font-weight: 700;
    }}
    QWidget#datasetItem {{
        background: transparent;
        border: 0;
        border-radius: 9px;
    }}
    QWidget#datasetItem:hover {{
        background: {sidebar_hover};
    }}
    QWidget#datasetItem[active="true"] {{
        background: {sidebar_selected};
    }}
    QWidget#datasetItem QPushButton#sidebarItem,
    QWidget#datasetItem QPushButton#sidebarItem:hover {{
        background: transparent;
    }}
    QWidget#datasetItem[active="true"] QPushButton#sidebarItem {{
        color: {sidebar_selected_text};
        font-weight: 700;
    }}
    QToolButton#datasetMenuButton {{
        background: transparent;
        border: 0;
        padding: 0;
    }}
    QToolButton#datasetMenuButton:hover {{
        background: transparent;
    }}
    QToolButton#datasetRefreshAction {{
        background: transparent;
        border: 0;
        padding: 0;
    }}
    QToolButton#datasetRefreshAction:hover {{
        background: transparent;
    }}
    QMenu {{
        background: {appearance.surface};
        border: 1px solid {appearance.border};
        border-radius: 8px;
        padding: 4px;
    }}
    QMenu::item {{
        padding: 6px 18px;
        border-radius: 5px;
    }}
    QMenu::item:selected {{
        background: {hover_bg};
        color: {appearance.text};
    }}
    QLabel#sidebarSection {{
        color: {appearance.muted};
        font-size: 11px;
        font-weight: 700;
        padding: 0 8px;
    }}
    QToolButton#sidebarAddButton {{
        background: transparent;
        border: 0;
        border-radius: 6px;
        color: {appearance.muted};
        font-size: 18px;
        min-width: 24px;
        min-height: 24px;
        padding: 0;
    }}
    QToolButton#sidebarAddButton:hover {{
        background: {sidebar_hover};
        color: {appearance.text};
    }}
    QFrame#sidebarDivider {{
        background: {appearance.border};
        border: 0;
        max-height: 1px;
    }}
    QWidget#rightPanel {{
        background: {appearance.background};
        border: 0;
    }}
    QFrame#workspaceHeader {{
        background: transparent;
        border: 0;
    }}
    QLabel#datasetTitle {{
        color: {appearance.text};
        font-size: 26px;
        font-weight: 700;
    }}
    QLabel#datasetSubtitle {{
        color: {appearance.muted};
        font-size: 12px;
    }}
    QLabel#emptyTitle {{
        color: {appearance.text};
        font-size: 18px;
        font-weight: 700;
    }}
    QToolButton#iconButton {{
        background: transparent;
        border: 0;
        border-radius: 8px;
        padding: 6px;
    }}
    QToolButton#iconButton:hover {{
        background: {hover_bg};
    }}
    QFrame#searchField {{
        background: {appearance.surface};
        border: 1px solid {appearance.border};
        border-radius: 12px;
    }}
    QFrame#searchField QLineEdit {{
        background: transparent;
        border: 0;
        padding: 0;
        min-height: 22px;
    }}
    QLabel#searchHint {{
        color: {appearance.muted};
        font-size: 11px;
        padding-right: 8px;
    }}
    QPushButton#filterButton {{
        background: {appearance.surface};
        border: 1px solid {appearance.border};
        border-radius: 11px;
        padding: 7px 12px;
        color: {appearance.text};
    }}
    QPushButton#filterButton:hover {{
        border-color: {appearance.accent_color};
    }}
    QFrame#filterChip {{
        border: 0;
        border-radius: 10px;
        padding: 4px 6px;
    }}
    QFrame#filterChip[role="must"] {{
        background: {chip_must};
    }}
    QFrame#filterChip[role="should"] {{
        background: {chip_should};
    }}
    QFrame#filterChip[role="must not"] {{
        background: {chip_must_not};
    }}
    QLabel#filterChipLabel {{
        background: transparent;
        color: {appearance.text};
        font-size: 11px;
    }}
    QToolButton#chipClose {{
        background: transparent;
        border: 0;
        color: {appearance.muted};
        padding: 0 2px;
    }}
    QToolButton#chipClose:hover {{
        color: {appearance.text};
    }}
    QTableView {{
        background: {appearance.surface};
        alternate-background-color: {appearance.surface_alt};
        selection-background-color: {selection_bg};
        selection-color: {appearance.text};
        gridline-color: transparent;
        border: 0;
        border-radius: 0;
        outline: 0;
    }}
    QTableView::item {{
        border: 0;
        outline: 0;
    }}
    QHeaderView {{
        background: transparent;
        border: 0;
        border-radius: 0;
    }}
    QHeaderView::section {{
        background: transparent;
        color: {appearance.muted};
        border: 0;
        border-bottom: 1px solid {appearance.border};
        padding: 8px 4px;
        font-weight: 600;
        font-size: 12px;
    }}
    QWidget#workspaceActionBar {{
        background: {appearance.background};
        border: 0;
        border-top: 1px solid {appearance.border};
    }}
    QPushButton#actionButton {{
        background: {appearance.surface};
        color: {appearance.text};
        border: 1px solid {appearance.border};
        border-radius: 10px;
        padding: 7px 12px;
    }}
    QPushButton#actionButton:hover {{
        border-color: {appearance.accent_color};
    }}
    QStackedWidget#tableStack {{
        background: transparent;
        border: 0;
        border-radius: 0;
    }}
    QSplitter#mainSplitter::handle {{
        background: transparent;
        border: 0;
    }}
    QSplitter#mainSplitter::handle:hover {{
        background: {appearance.accent_color};
    }}
    QWidget#detailsPanel {{
        background: {appearance.background};
        border: 0;
        border-left: 1px solid {appearance.border};
    }}
    QLabel#detailsBreadcrumb {{
        color: {appearance.muted};
        font-size: 11px;
    }}
    QLabel#paperTitle {{
        color: {appearance.text};
        font-family: Georgia, "Times New Roman", "Songti SC", serif;
        font-size: 26px;
        font-weight: 700;
    }}
    QLabel#paperAuthors {{
        color: {appearance.muted};
        font-size: 13px;
    }}
    QFrame#tagChip {{
        background: {appearance.surface_alt};
        border: 0;
        border-radius: 10px;
        padding: 4px 9px;
    }}
    QLabel#tagText {{
        background: transparent;
        color: {appearance.muted};
        font-size: 11px;
    }}
    QLabel#sectionTitle {{
        color: {appearance.text};
        font-size: 15px;
        font-weight: 700;
    }}
    QToolButton#sectionAction {{
        background: transparent;
        border: 0;
        color: {appearance.muted};
        padding: 2px;
    }}
    QToolButton#sectionAction:hover {{
        color: {appearance.accent_color};
    }}
    QTextEdit#abstractText {{
        background: transparent;
        border: 0;
        color: {appearance.text};
        font-size: 13px;
    }}
    QWidget#taskBar {{
        background: {appearance.background};
        border: 0;
        border-top: 1px solid {appearance.border};
    }}
    QLabel#taskStatus {{
        color: {appearance.text};
        font-size: 12px;
    }}
    QLabel#taskProgressCount {{
        color: {appearance.muted};
        font-size: 11px;
    }}
    QPushButton#taskCancel {{
        background: {appearance.surface};
        border: 1px solid {appearance.border};
        border-radius: 8px;
        padding: 4px 12px;
    }}
    QToolButton#logToggleButton {{
        background: transparent;
        border: 0;
        color: {appearance.muted};
        font-weight: 500;
        padding: 4px 6px;
    }}
    QToolButton#logToggleButton:hover,
    QToolButton#logToggleButton[expanded="true"] {{
        color: {appearance.text};
        font-weight: 600;
    }}
    QProgressBar {{
        background: {appearance.surface_alt};
        border: 0;
        border-radius: 2px;
        min-height: 4px;
        max-height: 4px;
    }}
    QProgressBar::chunk {{
        background: {appearance.accent_color};
        border-radius: 2px;
    }}
    """


def apply_theme(widget: QWidget, settings: QSettings | None = None) -> Appearance:
    appearance = load_appearance(settings or QSettings("PaperSpider", "PaperSpider"))
    widget.setStyleSheet(build_stylesheet(appearance))
    palette = widget.palette()
    dark = appearance.theme == "Dark"
    highlight = QColor("#34343a" if dark else "#e3e3e8")
    palette.setColor(QPalette.ColorRole.Window, QColor(appearance.background))
    palette.setColor(QPalette.ColorRole.WindowText, QColor(appearance.text))
    palette.setColor(QPalette.ColorRole.Base, QColor(appearance.surface))
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor(appearance.surface_alt))
    palette.setColor(QPalette.ColorRole.Text, QColor(appearance.text))
    palette.setColor(QPalette.ColorRole.Button, QColor(appearance.surface))
    palette.setColor(QPalette.ColorRole.ButtonText, QColor(appearance.text))
    palette.setColor(QPalette.ColorRole.Highlight, highlight)
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor(appearance.text))
    palette.setColor(QPalette.ColorRole.PlaceholderText, QColor(appearance.muted))
    palette.setColor(QPalette.ColorRole.ToolTipBase, QColor(appearance.surface))
    palette.setColor(QPalette.ColorRole.ToolTipText, QColor(appearance.text))
    palette.setColor(QPalette.ColorRole.Link, QColor(appearance.accent_color))
    widget.setPalette(palette)
    return appearance
