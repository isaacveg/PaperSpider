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

from .app_settings import app_settings

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

    return load_appearance(app_settings())


def themed_icon(name: str, theme: str | None = None) -> QIcon:
    """Load a light or dark line icon from the UI assets folder."""

    resolved = theme if theme in RESOLVED_THEMES else current_appearance().theme
    suffix = "dark" if resolved == "Dark" else "light"
    path = Path(__file__).with_name("assets") / f"{name}-{suffix}.svg"
    return QIcon(path.as_posix())


def availability_icon(available: bool, theme: str | None = None) -> QIcon:
    """Return a check or dash icon for abstract/PDF availability."""

    return themed_icon("check" if available else "dash", theme)


def mix_colors(foreground: str, background: str, amount: float) -> str:
    """Blend ``amount`` of ``foreground`` over ``background`` and return a hex color."""

    fg, bg = QColor(foreground), QColor(background)
    return QColor(
        round(fg.red() * amount + bg.red() * (1 - amount)),
        round(fg.green() * amount + bg.green() * (1 - amount)),
        round(fg.blue() * amount + bg.blue() * (1 - amount)),
    ).name()


def selection_color(appearance: Appearance) -> str:
    """Accent-tinted background for the current table row."""

    return mix_colors(
        appearance.accent_color,
        appearance.surface,
        0.18 if appearance.theme == "Dark" else 0.10,
    )


def build_stylesheet(appearance: Appearance) -> str:
    dark = appearance.theme == "Dark"
    a = appearance
    selection_bg = selection_color(a)
    hover_bg = "#2e302e" if dark else "#f0f0f3"
    row_alt = "#272927" if dark else "#fafafb"
    sidebar_bg = "#1f201f" if dark else "#f3f3f6"
    sidebar_hover = "#2a2c2a" if dark else "#e9e9ed"
    sidebar_selected = "#323532" if dark else "#e2e2e8"
    disabled_bg = "#232523" if dark else "#f1f1f4"
    disabled_text = "#73766f" if dark else "#a3a5ab"
    disabled_border = "#323532" if dark else "#e4e4e8"
    scrollbar_handle = "#555955" if dark else "#c9cace"
    scrollbar_hover = "#7a7e78" if dark else "#a9abb1"
    chip_must = mix_colors(a.accent_color, a.surface, 0.16 if dark else 0.10)
    chip_should = "#30333a" if dark else "#e8eaf2"
    chip_must_not = "#3a2f2f" if dark else "#f4e9e9"
    primary_text = "#101712" if dark else "#ffffff"
    primary_hover = mix_colors("#ffffff" if dark else "#000000", a.accent_color, 0.12)
    log_bg = "#1d1e1d" if dark else "#fbfbfc"
    arrow_icon = (
        Path(__file__).with_name("assets")
        / ("chevron-down-dark.svg" if dark else "chevron-down-light.svg")
    ).as_posix()
    return f"""
    /* ---- base ---- */
    QWidget {{
        color: {a.text};
        font-size: 13px;
    }}
    QMainWindow, QWidget#rightPanel {{
        background: {a.surface};
    }}
    QDialog, QMessageBox {{
        background: {a.background};
    }}
    QDialog#utilityDialog, QMessageBox#messageDialog {{
        background: {a.background};
        border: 1px solid {a.border};
    }}
    QLabel {{
        background: transparent;
        border: 0;
    }}
    QFrame {{
        border: 0;
    }}
    QToolTip {{
        background: {a.surface};
        color: {a.text};
        border: 1px solid {a.border};
        border-radius: 6px;
        padding: 4px 8px;
    }}
    QScrollArea {{
        background: transparent;
        border: 0;
    }}
    QScrollArea > QWidget#qt_scrollarea_viewport {{
        background: transparent;
    }}
    QGroupBox {{
        background: {a.surface};
        border: 1px solid {a.border};
        border-radius: 10px;
        margin-top: 22px;
        padding: 14px 12px 12px 12px;
    }}
    QGroupBox::title {{
        subcontrol-origin: margin;
        subcontrol-position: top left;
        left: 2px;
        padding: 0 0 6px 0;
        color: {a.muted};
        font-size: 12px;
        font-weight: 600;
    }}
    QTextEdit, QPlainTextEdit {{
        background: {a.surface};
        border: 1px solid {a.border};
        border-radius: 8px;
        padding: 6px;
        selection-background-color: {selection_bg};
        selection-color: {a.text};
    }}

    /* ---- inputs ---- */
    QLineEdit, QComboBox, QSpinBox {{
        background: {a.surface};
        color: {a.text};
        border: 1px solid {a.border};
        border-radius: 7px;
        padding: 5px 10px;
        min-height: 22px;
        selection-background-color: {selection_bg};
        selection-color: {a.text};
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
        background: transparent;
    }}
    QComboBox::down-arrow {{
        image: url({arrow_icon});
        width: 14px;
        height: 14px;
    }}
    QComboBox:on, QSpinBox:focus, QLineEdit:focus {{
        border-color: {a.accent_color};
    }}
    QComboBox QAbstractItemView {{
        background: {a.surface};
        color: {a.text};
        border: 1px solid {a.border};
        border-radius: 8px;
        padding: 4px;
        outline: 0;
        selection-background-color: {hover_bg};
        selection-color: {a.text};
    }}
    QComboBoxPrivateContainer {{
        background: {a.surface};
        border: 1px solid {a.border};
        border-radius: 8px;
        padding: 0;
    }}
    QComboBox#filterRoleCombo {{
        color: {a.accent_color};
        font-size: 12px;
        font-weight: 700;
        padding-left: 6px;
        padding-right: 19px;
    }}
    QComboBox#filterRoleCombo::drop-down, QComboBox#filterModeCombo::drop-down {{
        width: 18px;
    }}
    QComboBox#filterFieldCombo {{
        padding-left: 6px;
        padding-right: 22px;
    }}
    QComboBox#filterFieldCombo::drop-down {{
        width: 22px;
    }}
    QComboBox#filterModeCombo {{
        font-size: 12px;
        padding-left: 6px;
        padding-right: 19px;
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
    }}
    QSpinBox::down-button {{
        subcontrol-position: bottom right;
    }}

    /* ---- buttons ---- */
    QPushButton {{
        background: {a.surface};
        color: {a.text};
        border: 1px solid {a.border};
        border-radius: 7px;
        padding: 6px 14px;
    }}
    QPushButton:hover {{
        background: {hover_bg};
    }}
    QPushButton:disabled {{
        background: {disabled_bg};
        color: {disabled_text};
        border-color: {disabled_border};
    }}
    QPushButton#primaryButton {{
        background: {a.accent_color};
        color: {primary_text};
        border-color: {a.accent_color};
        font-weight: 600;
    }}
    QPushButton#primaryButton:hover {{
        background: {primary_hover};
        border-color: {primary_hover};
    }}
    QPushButton#primaryButton:disabled {{
        background: {disabled_bg};
        color: {disabled_text};
        border-color: {disabled_border};
    }}
    QPushButton#secondaryButton {{
        background: {a.surface};
        color: {a.text};
        border: 1px solid {a.border};
        font-weight: 500;
    }}
    QPushButton#secondaryButton:hover {{
        background: {hover_bg};
    }}
    QPushButton#secondaryButton:disabled {{
        background: {disabled_bg};
        color: {disabled_text};
        border-color: {disabled_border};
    }}
    QPushButton#linkButton {{
        background: transparent;
        border-color: transparent;
        color: {a.accent_color};
        font-weight: 600;
        padding: 6px 8px;
    }}
    QPushButton#linkButton:hover {{
        background: {hover_bg};
    }}
    QPushButton#linkButton:disabled {{
        background: transparent;
        border-color: transparent;
        color: {disabled_text};
    }}
    QPushButton#compactDeleteButton {{
        background: transparent;
        border: 0;
        color: {a.muted};
        padding: 0;
        min-width: 22px;
        max-width: 24px;
        min-height: 22px;
        font-size: 15px;
    }}
    QPushButton#compactDeleteButton:hover {{
        background: {hover_bg};
        color: {a.text};
    }}
    QToolButton#iconButton, QToolButton#rowIconButton {{
        background: transparent;
        border: 0;
        border-radius: 7px;
        padding: 5px;
    }}
    QToolButton#iconButton:hover, QToolButton#rowIconButton:hover {{
        background: {hover_bg};
    }}
    QToolButton#sectionAction {{
        background: transparent;
        border: 0;
        border-radius: 6px;
        color: {a.accent_color};
        font-weight: 600;
        padding: 3px 8px;
    }}
    QToolButton#sectionAction:hover {{
        background: {hover_bg};
    }}

    /* ---- menus & scrollbars ---- */
    QMenu {{
        background: {a.surface};
        border: 1px solid {a.border};
        border-radius: 8px;
        padding: 4px;
    }}
    QMenu::item {{
        padding: 6px 18px;
        border-radius: 5px;
    }}
    QMenu::item:selected {{
        background: {hover_bg};
        color: {a.text};
    }}
    QMenu::item:disabled {{
        color: {disabled_text};
    }}
    QMenu::separator {{
        height: 1px;
        background: {a.border};
        margin: 4px 6px;
    }}
    QScrollBar:vertical {{
        background: transparent;
        border: 0;
        width: 10px;
        margin: 2px;
    }}
    QScrollBar::handle:vertical {{
        background: {scrollbar_handle};
        border-radius: 3px;
        min-height: 28px;
        margin: 0 1px;
    }}
    QScrollBar:horizontal {{
        background: transparent;
        border: 0;
        height: 10px;
        margin: 2px;
    }}
    QScrollBar::handle:horizontal {{
        background: {scrollbar_handle};
        border-radius: 3px;
        min-width: 28px;
        margin: 1px 0;
    }}
    QScrollBar::handle:hover {{
        background: {scrollbar_hover};
    }}
    QScrollBar::add-line, QScrollBar::sub-line,
    QScrollBar::add-page, QScrollBar::sub-page {{
        background: transparent;
        border: 0;
        width: 0;
        height: 0;
    }}
    QSplitter::handle {{
        background: {a.border};
    }}
    QSplitter#mainSplitter::handle {{
        background: transparent;
    }}
    QSplitter::handle:hover, QSplitter#mainSplitter::handle:hover {{
        background: {a.accent_color};
    }}
    QProgressBar {{
        background: {a.surface_alt};
        border: 0;
        border-radius: 2px;
        min-height: 4px;
        max-height: 4px;
    }}
    QProgressBar::chunk {{
        background: {a.accent_color};
        border-radius: 2px;
    }}

    /* ---- sidebar ---- */
    QWidget#appSidebar {{
        background: {sidebar_bg};
        border: 0;
        border-right: 1px solid {a.border};
    }}
    QLabel#brandLabel {{
        font-size: 17px;
        font-weight: 700;
        color: {a.text};
    }}
    QPushButton#sidebarItem, QPushButton#sidebarSettings {{
        background: transparent;
        border: 0;
        border-radius: 8px;
        padding: 7px 10px;
        text-align: left;
        color: {a.text};
        font-weight: 500;
        min-height: 20px;
    }}
    QPushButton#sidebarItem:hover, QPushButton#sidebarSettings:hover {{
        background: {sidebar_hover};
    }}
    QPushButton#sidebarItem[compact="true"], QPushButton#sidebarSettings[compact="true"] {{
        text-align: center;
        padding: 7px 0;
    }}
    QWidget#datasetItem {{
        background: transparent;
        border-radius: 8px;
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
        font-weight: 700;
    }}
    QToolButton#datasetMenuButton, QToolButton#datasetRefreshAction {{
        background: transparent;
        border: 0;
        border-radius: 6px;
        padding: 0;
    }}
    QToolButton#datasetMenuButton:hover, QToolButton#datasetRefreshAction:hover {{
        background: {sidebar_selected};
    }}
    QToolButton#datasetBadge {{
        background: transparent;
        border: 0;
        border-radius: 8px;
        color: {a.text};
        font-size: 11px;
        font-weight: 700;
        padding: 4px 0;
    }}
    QToolButton#datasetBadge:hover {{
        background: {sidebar_hover};
    }}
    QToolButton#datasetBadge[active="true"] {{
        background: {sidebar_selected};
        color: {a.accent_color};
    }}
    QLabel#sidebarSection {{
        color: {a.muted};
        font-size: 11px;
        font-weight: 700;
        padding: 0 10px;
    }}
    QToolButton#sidebarAddButton {{
        background: transparent;
        border: 0;
        border-radius: 6px;
        padding: 3px;
    }}
    QToolButton#sidebarAddButton:hover {{
        background: {sidebar_hover};
    }}
    QFrame#sidebarDivider {{
        background: {a.border};
        border: 0;
        min-height: 1px;
        max-height: 1px;
    }}

    /* ---- workspace header ---- */
    QFrame#workspaceHeader {{
        background: transparent;
    }}
    QLabel#datasetTitle {{
        color: {a.text};
        font-size: 22px;
        font-weight: 700;
    }}
    QLabel#datasetSubtitle, QLabel#mutedLabel {{
        color: {a.muted};
        font-size: 12px;
    }}
    QFrame#searchField {{
        background: {a.surface};
        border: 1px solid {a.border};
        border-radius: 9px;
    }}
    QFrame#searchField QLineEdit {{
        background: transparent;
        border: 0;
        padding: 0;
        min-height: 20px;
    }}
    QLabel#searchHint {{
        color: {a.muted};
        background: {a.surface_alt};
        border-radius: 4px;
        font-size: 11px;
        padding: 1px 6px;
    }}
    QPushButton#filterButton {{
        background: {a.surface};
        border: 1px solid {a.border};
        border-radius: 9px;
        padding: 7px 12px;
        color: {a.text};
    }}
    QPushButton#filterButton:hover {{
        background: {hover_bg};
    }}
    QPushButton#filterButton[active="true"] {{
        border-color: {a.accent_color};
        color: {a.accent_color};
        font-weight: 600;
    }}
    QFrame#filterChip {{
        border: 0;
        border-radius: 12px;
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
        color: {a.text};
        font-size: 12px;
    }}
    QToolButton#chipClose {{
        background: transparent;
        border: 0;
        border-radius: 8px;
        color: {a.muted};
        padding: 0 4px;
    }}
    QToolButton#chipClose:hover {{
        color: {a.text};
    }}
    QLabel#emptyTitle {{
        color: {a.text};
        font-size: 17px;
        font-weight: 700;
    }}

    /* ---- paper table ---- */
    QStackedWidget#tableStack {{
        background: transparent;
    }}
    QTableView {{
        background: {a.surface};
        alternate-background-color: {row_alt};
        selection-background-color: {selection_bg};
        selection-color: {a.text};
        gridline-color: transparent;
        border: 0;
        outline: 0;
    }}
    QTableView::item {{
        border: 0;
    }}
    QTableView::item:selected, QTableView::item:selected:active,
    QTableView::item:selected:!active {{
        background: {selection_bg};
        color: {a.text};
    }}
    QHeaderView {{
        background: transparent;
        border: 0;
    }}
    QHeaderView::section {{
        background: transparent;
        color: {a.muted};
        border: 0;
        border-bottom: 1px solid {a.border};
        padding: 8px 4px;
        font-weight: 600;
        font-size: 12px;
    }}
    QHeaderView::section:hover {{
        color: {a.text};
    }}
    QWidget#workspaceActionBar {{
        background: transparent;
        border: 0;
        border-top: 1px solid {a.border};
    }}
    QPushButton#actionButton {{
        background: {a.surface};
        color: {a.text};
        border: 1px solid {a.border};
        border-radius: 8px;
        padding: 6px 12px;
    }}
    QPushButton#actionButton:hover {{
        background: {hover_bg};
    }}
    QPushButton#actionButton:disabled {{
        background: transparent;
        color: {disabled_text};
        border-color: {disabled_border};
    }}

    /* ---- details panel ---- */
    QWidget#detailsPanel {{
        background: {a.surface};
        border: 0;
        border-left: 1px solid {a.border};
    }}
    QLabel#detailsBreadcrumb {{
        color: {a.muted};
        font-size: 11px;
        font-weight: 600;
    }}
    QLabel#paperTitle {{
        color: {a.text};
        font-size: 19px;
        font-weight: 700;
    }}
    QLabel#paperAuthors {{
        color: {a.muted};
        font-size: 13px;
    }}
    QFrame#tagChip {{
        background: {a.surface_alt};
        border-radius: 10px;
    }}
    QLabel#tagText {{
        color: {a.muted};
        font-size: 11px;
    }}
    QLabel#sectionTitle {{
        color: {a.text};
        font-size: 14px;
        font-weight: 700;
    }}
    QTextEdit#abstractText {{
        background: transparent;
        border: 0;
        padding: 0;
        color: {a.text};
        font-size: 13px;
    }}
    QLabel#detailsFeedbackLabel {{
        color: {a.accent_color};
    }}
    QLabel#placeholderTitle {{
        color: {a.text};
        font-size: 15px;
        font-weight: 600;
    }}
    QLabel#placeholderText {{
        color: {a.muted};
    }}

    /* ---- task bar ---- */
    QWidget#taskBar {{
        background: {sidebar_bg};
        border: 0;
        border-top: 1px solid {a.border};
    }}
    QTextEdit#taskLog {{
        background: {log_bg};
        border: 0;
        border-bottom: 1px solid {a.border};
        border-radius: 0;
        padding: 8px 14px;
        color: {a.muted};
        font-family: "SF Mono", Menlo, Consolas, monospace;
        font-size: 12px;
    }}
    QLabel#taskStatus {{
        color: {a.text};
        font-size: 12px;
    }}
    QLabel#taskProgressCount {{
        color: {a.muted};
        font-size: 11px;
    }}
    QPushButton#taskCancel {{
        border-radius: 7px;
        padding: 3px 12px;
    }}
    QToolButton#logToggleButton {{
        background: transparent;
        border: 0;
        border-radius: 6px;
        color: {a.muted};
        font-weight: 500;
        padding: 3px 8px;
    }}
    QToolButton#logToggleButton:hover,
    QToolButton#logToggleButton[expanded="true"] {{
        background: {sidebar_hover};
        color: {a.text};
    }}

    /* ---- dialogs ---- */
    QWidget#dialogTitleBar {{
        background: {a.background};
        border: 0;
        border-bottom: 1px solid {a.border};
    }}
    QLabel#dialogTitle {{
        color: {a.text};
        font-size: 13px;
        font-weight: 700;
    }}
    QLabel#filterHintLabel {{
        color: {a.muted};
    }}
    QFrame#filterRuleCard {{
        background: {a.surface};
        border: 1px solid {a.border};
        border-radius: 8px;
    }}
    QFrame#newDatasetPanel {{
        background: {a.surface_alt};
        border: 1px solid {a.border};
        border-radius: 8px;
    }}
    QLabel#newDatasetLabel {{
        font-weight: 700;
    }}
    QTableWidget {{
        background: {a.surface};
        alternate-background-color: {row_alt};
        border: 0;
        gridline-color: transparent;
        selection-background-color: {selection_bg};
        selection-color: {a.text};
    }}
    QFrame#settingsContentArea, QFrame#settingsContentCard {{
        background: transparent;
        border: 0;
    }}
    QFrame#settingsFieldGroup {{
        background: {a.surface};
        border: 1px solid {a.border};
        border-radius: 10px;
    }}
    QFrame#settingsFieldRow, QWidget#settingsTextBlock, QWidget#settingsInlineControls {{
        background: transparent;
        border: 0;
    }}
    QFrame#settingsFieldDivider {{
        background: {a.border};
        border: 0;
        min-height: 1px;
        max-height: 1px;
    }}
    QFrame#settingsFooter {{
        background: {a.background};
        border: 0;
        border-top: 1px solid {a.border};
    }}
    QLabel#settingsCardTitle {{
        font-size: 14px;
        font-weight: 700;
    }}
    QLabel#settingsFieldTitle {{
        font-weight: 600;
    }}
    QLabel#settingsFieldDescription {{
        color: {a.muted};
        font-size: 12px;
    }}
    QLabel#settingsUnitLabel {{
        color: {a.muted};
        padding: 0 4px;
        min-width: 24px;
    }}
    QTextEdit#exportOutput {{
        font-family: "SF Mono", Menlo, Consolas, monospace;
        font-size: 12px;
    }}
    QMessageBox QLabel#qt_msgbox_label {{
        font-size: 14px;
        font-weight: 700;
        min-width: 300px;
    }}
    QMessageBox QLabel#qt_msgbox_informativelabel {{
        color: {a.muted};
        min-width: 300px;
    }}
    """


def apply_theme(widget: QWidget, settings: QSettings | None = None) -> Appearance:
    appearance = load_appearance(settings or app_settings())
    widget.setStyleSheet(build_stylesheet(appearance))
    palette = widget.palette()
    highlight = QColor(selection_color(appearance))
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
