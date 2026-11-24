# Copyright 2026 Isaacveg
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#     http://www.apache.org/licenses/LICENSE-2.0

"""Workspace widgets: sidebar, header, details panel, and task bar."""

from __future__ import annotations

from pathlib import Path
from typing import List, Optional, Sequence

from PyQt6.QtCore import QPoint, QRect, QSize, Qt, pyqtSignal
from PyQt6.QtGui import (
    QColor,
    QFont,
    QFontMetrics,
    QGuiApplication,
    QKeySequence,
    QPainter,
    QPalette,
    QPixmap,
)
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMenu,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QTextEdit,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from ..filtering import FilterConfig
from .filter_dialog import filter_role_label
from .i18n import display_category, tr
from .paper_table_model import row_title
from .theme import themed_icon


SIDEBAR_RAIL_WIDTH = 64
SIDEBAR_MIN_WIDTH = 232
SIDEBAR_MAX_WIDTH = 440
SIDEBAR_SNAP_WIDTH = (SIDEBAR_RAIL_WIDTH + SIDEBAR_MIN_WIDTH) // 2


def _repolish(widget: QWidget) -> None:
    widget.style().unpolish(widget)
    widget.style().polish(widget)


def conference_badge_label(name: str) -> str:
    """Short label shown for a conference in the compact sidebar rail."""

    words = name.split()
    if len(words) > 1:
        return "".join(word[0] for word in words).upper()[:4]
    return name


class SidebarButton(QPushButton):
    def __init__(
        self,
        text: str,
        icon_name: Optional[str] = None,
        parent: Optional[QWidget] = None,
        elide: bool = False,
    ) -> None:
        super().__init__(text, parent)
        self.icon_name = icon_name
        self._full_text = text
        self._elide = elide
        self._compact = False
        self.setObjectName("sidebarItem")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip(text)
        self.setAccessibleName(text)
        if icon_name:
            self.refresh_icon()

    def set_full_text(self, text: str) -> None:
        self._full_text = text
        self.setToolTip(text)
        self.setAccessibleName(text)
        self._refresh_text()

    def set_compact(self, compact: bool) -> None:
        if compact == self._compact:
            return
        self._compact = compact
        self.setProperty("compact", compact)
        _repolish(self)
        self._refresh_text()

    def _text_width(self) -> int:
        reserved = 22
        if not self.icon().isNull():
            reserved += self.iconSize().width() + 6
        return max(12, self.width() - reserved)

    def _refresh_text(self) -> None:
        if self._compact:
            text = ""
        elif self._elide:
            text = self.fontMetrics().elidedText(
                self._full_text, Qt.TextElideMode.ElideRight, self._text_width()
            )
        else:
            text = self._full_text
        if self.text() != text:
            super().setText(text)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._refresh_text()

    def refresh_icon(self) -> None:
        if self.icon_name:
            self.setIcon(themed_icon(self.icon_name))
            self.setIconSize(QSize(18, 18))


class DatasetMenuButton(QToolButton):
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("datasetMenuButton")
        self.setFixedSize(24, 24)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip(tr("Dataset options"))
        self.setAccessibleName(tr("Dataset options"))

    def paintEvent(self, event) -> None:
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        role = (
            QPalette.ColorRole.Text
            if self.underMouse()
            else QPalette.ColorRole.PlaceholderText
        )
        painter.setBrush(self.palette().color(role))
        painter.setPen(Qt.PenStyle.NoPen)
        center = self.rect().center()
        for offset in (-5, 0, 5):
            painter.drawEllipse(center.x() + offset - 2, center.y() - 2, 4, 4)

    def enterEvent(self, event) -> None:
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:
        self.update()
        super().leaveEvent(event)


class DatasetBadge(QToolButton):
    """Compact conference/year button shown in the sidebar rail."""

    def __init__(self, label: str, year: int, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("datasetBadge")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(40)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._label = label
        self._year = f"’{year % 100:02d}"

    def paintEvent(self, event) -> None:
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)
        rect = self.rect().adjusted(3, 4, -3, -4)
        label_font = QFont(self.font())
        label_font.setBold(True)
        size = 11
        label_font.setPixelSize(size)
        while size > 8 and QFontMetrics(label_font).horizontalAdvance(self._label) > rect.width():
            size -= 1
            label_font.setPixelSize(size)
        text_color = self.palette().color(QPalette.ColorRole.ButtonText)
        painter.setFont(label_font)
        painter.setPen(text_color)
        half = rect.height() // 2
        painter.drawText(
            QRect(rect.left(), rect.top(), rect.width(), half + 2),
            Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignBottom,
            self._label,
        )
        year_font = QFont(self.font())
        year_font.setPixelSize(10)
        painter.setFont(year_font)
        year_color = QColor(text_color)
        year_color.setAlphaF(0.55)
        painter.setPen(year_color)
        painter.drawText(
            QRect(rect.left(), rect.top() + half + 2, rect.width(), half - 2),
            Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop,
            self._year,
        )


class DatasetSidebarItem(QWidget):
    activated = pyqtSignal(str, int)
    menu_requested = pyqtSignal(str, int, QPoint)
    refresh_requested = pyqtSignal(str, int)
    context_menu_requested = pyqtSignal(str, int, QPoint)

    def __init__(
        self,
        conf_slug: str,
        year: int,
        text: str,
        paper_count: int,
        parent: Optional[QWidget] = None,
        badge_label: Optional[str] = None,
    ) -> None:
        super().__init__(parent)
        self.conf_slug = conf_slug
        self.year = year
        self.setObjectName("datasetItem")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_Hover, True)
        tooltip = f"{text} · {tr('{count} papers', count=f'{paper_count:,}')}"
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 6, 0)
        layout.setSpacing(0)
        self.main_btn = SidebarButton(text, "nav-dataset", self, elide=True)
        self.main_btn.setToolTip(tooltip)
        self.main_btn.clicked.connect(self._activate)
        self.refresh_btn = QToolButton()
        self.refresh_btn.setObjectName("datasetRefreshAction")
        self.refresh_btn.setIcon(themed_icon("refresh"))
        self.refresh_btn.setIconSize(QSize(14, 14))
        self.refresh_btn.setFixedSize(24, 24)
        self.refresh_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.refresh_btn.setToolTip(tr("Refresh dataset"))
        self.refresh_btn.clicked.connect(self._request_refresh)
        self.menu_btn = DatasetMenuButton(self)
        self.menu_btn.clicked.connect(self._request_menu)
        for button in (self.refresh_btn, self.menu_btn):
            policy = button.sizePolicy()
            policy.setRetainSizeWhenHidden(True)
            button.setSizePolicy(policy)
        self.badge_btn = DatasetBadge(badge_label or text, year, self)
        self.badge_btn.setToolTip(tooltip)
        self.badge_btn.setAccessibleName(text)
        self.badge_btn.clicked.connect(self._activate)
        self.badge_btn.setVisible(False)
        layout.addWidget(self.main_btn, stretch=1)
        layout.addWidget(self.badge_btn, stretch=1)
        layout.addWidget(self.refresh_btn, alignment=Qt.AlignmentFlag.AlignVCenter)
        layout.addWidget(self.menu_btn, alignment=Qt.AlignmentFlag.AlignVCenter)
        self.setLayout(layout)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(
            lambda pos: self.context_menu_requested.emit(
                self.conf_slug, self.year, self.mapToGlobal(pos)
            )
        )
        for child in (self.main_btn, self.badge_btn):
            child.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
            child.customContextMenuRequested.connect(
                lambda pos, source=child: self.context_menu_requested.emit(
                    self.conf_slug, self.year, source.mapToGlobal(pos)
                )
            )
        self._active = False
        self._hovered = False
        self._compact = False
        self._update_menu_visibility()

    def _activate(self) -> None:
        self.activated.emit(self.conf_slug, self.year)

    def set_active(self, active: bool) -> None:
        self._active = active
        self.setProperty("active", active)
        self.badge_btn.setProperty("active", active)
        _repolish(self)
        _repolish(self.badge_btn)
        self.badge_btn.update()
        self._update_menu_visibility()

    def set_compact(self, compact: bool) -> None:
        self._compact = compact
        self.layout().setContentsMargins(0, 0, 0 if compact else 6, 0)
        self.main_btn.setVisible(not compact)
        self.badge_btn.setVisible(compact)
        self._update_menu_visibility()

    def enterEvent(self, event) -> None:
        self._hovered = True
        self._update_menu_visibility()
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:
        self._hovered = False
        self._update_menu_visibility()
        super().leaveEvent(event)

    def _update_menu_visibility(self) -> None:
        visible = not self._compact and (self._active or self._hovered)
        for button in (self.refresh_btn, self.menu_btn):
            policy = button.sizePolicy()
            if policy.retainSizeWhenHidden() == self._compact:
                policy.setRetainSizeWhenHidden(not self._compact)
                button.setSizePolicy(policy)
                button.updateGeometry()
            button.setVisible(visible)
        self.layout().invalidate()

    def _request_refresh(self) -> None:
        self.refresh_requested.emit(self.conf_slug, self.year)

    def _request_menu(self) -> None:
        position = self.menu_btn.mapToGlobal(QPoint(0, self.menu_btn.height()))
        self.menu_requested.emit(self.conf_slug, self.year, position)

    def refresh_icon(self) -> None:
        self.main_btn.refresh_icon()
        self.refresh_btn.setIcon(themed_icon("refresh"))
        self.refresh_btn.setIconSize(QSize(14, 14))


class AppSidebar(QWidget):
    settings_clicked = pyqtSignal()
    add_dataset_clicked = pyqtSignal()
    all_papers_clicked = pyqtSignal()
    filters_clicked = pyqtSignal()
    dataset_clicked = pyqtSignal(str, int)
    toggle_compact_clicked = pyqtSignal()
    open_dataset_folder = pyqtSignal(str, int)
    delete_dataset = pyqtSignal(str, int)
    refresh_dataset = pyqtSignal(str, int)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("appSidebar")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setMinimumWidth(SIDEBAR_RAIL_WIDTH)
        self.setMaximumWidth(SIDEBAR_MAX_WIDTH)
        self._dataset_items: List[DatasetSidebarItem] = []
        self._compact = False

        layout = QVBoxLayout()
        layout.setContentsMargins(12, 14, 12, 12)
        layout.setSpacing(2)
        self.root_layout = layout

        brand = QHBoxLayout()
        brand.setContentsMargins(4, 0, 0, 0)
        brand.setSpacing(10)
        self.icon_label = QLabel()
        icon_path = Path(__file__).with_name("assets") / "app-icon.png"
        device_ratio = 1.0
        screen = QGuiApplication.primaryScreen()
        if screen is not None:
            device_ratio = screen.devicePixelRatio()
        pixmap = QPixmap(icon_path.as_posix()).scaled(
            int(32 * device_ratio),
            int(32 * device_ratio),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        pixmap.setDevicePixelRatio(device_ratio)
        self.icon_label.setPixmap(pixmap)
        self.icon_label.setFixedSize(32, 32)
        self.brand_label = QLabel("PaperSpider")
        self.brand_label.setObjectName("brandLabel")
        self.collapse_btn = QToolButton()
        self.collapse_btn.setObjectName("iconButton")
        self.collapse_btn.setIcon(themed_icon("chevron-left"))
        self.collapse_btn.setIconSize(QSize(16, 16))
        self.collapse_btn.setToolTip(tr("Collapse sidebar"))
        self.collapse_btn.clicked.connect(self.toggle_compact_clicked.emit)
        brand.addWidget(self.icon_label)
        brand.addWidget(self.brand_label)
        brand.addStretch(1)
        brand.addWidget(self.collapse_btn)
        self.brand_layout = brand
        layout.addLayout(brand)

        self.expand_btn = QToolButton()
        self.expand_btn.setObjectName("iconButton")
        self.expand_btn.setIcon(themed_icon("chevron-right"))
        self.expand_btn.setIconSize(QSize(16, 16))
        self.expand_btn.setToolTip(tr("Expand sidebar"))
        self.expand_btn.clicked.connect(self.toggle_compact_clicked.emit)
        self.expand_btn.setVisible(False)
        layout.addWidget(self.expand_btn, alignment=Qt.AlignmentFlag.AlignHCenter)
        layout.addSpacing(14)

        self.all_papers_btn = SidebarButton(tr("All papers"), "nav-all")
        self.all_papers_btn.clicked.connect(self.all_papers_clicked.emit)
        self.filters_btn = SidebarButton(tr("Filters"), "filter")
        self.filters_btn.clicked.connect(self.filters_clicked.emit)
        layout.addWidget(self.all_papers_btn)
        layout.addWidget(self.filters_btn)
        layout.addSpacing(10)

        divider = QFrame()
        divider.setObjectName("sidebarDivider")
        divider.setFrameShape(QFrame.Shape.HLine)
        layout.addWidget(divider)
        layout.addSpacing(8)

        section = QHBoxLayout()
        section.setContentsMargins(0, 0, 0, 2)
        self.section_label = QLabel(tr("Conference datasets"))
        self.section_label.setObjectName("sidebarSection")
        self.add_dataset_btn = QToolButton()
        self.add_dataset_btn.setObjectName("sidebarAddButton")
        self.add_dataset_btn.setIcon(themed_icon("plus"))
        self.add_dataset_btn.setIconSize(QSize(16, 16))
        self.add_dataset_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.add_dataset_btn.setToolTip(tr("Add dataset"))
        self.add_dataset_btn.clicked.connect(self.add_dataset_clicked.emit)
        section.addWidget(self.section_label, stretch=1)
        section.addWidget(self.add_dataset_btn)
        self.section_layout = section
        layout.addLayout(section)

        self.dataset_layout = QVBoxLayout()
        self.dataset_layout.setContentsMargins(0, 0, 0, 0)
        self.dataset_layout.setSpacing(2)
        self.dataset_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        dataset_container = QWidget()
        dataset_container.setObjectName("sidebarScrollContent")
        dataset_container.setLayout(self.dataset_layout)
        self.dataset_scroll = QScrollArea()
        self.dataset_scroll.setObjectName("sidebarScroll")
        self.dataset_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.dataset_scroll.setWidgetResizable(True)
        self.dataset_scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self.dataset_scroll.setWidget(dataset_container)
        dataset_container.setAutoFillBackground(False)
        layout.addWidget(self.dataset_scroll, stretch=1)

        self.settings_btn = SidebarButton(tr("Settings"), "nav-settings")
        self.settings_btn.setObjectName("sidebarSettings")
        self.settings_btn.clicked.connect(self.settings_clicked.emit)
        layout.addWidget(self.settings_btn)
        self.setLayout(layout)

    def is_compact(self) -> bool:
        return self._compact

    def set_compact(self, compact: bool) -> None:
        if compact == self._compact:
            return
        self._compact = compact
        self.root_layout.setContentsMargins(*((8, 14, 8, 12) if compact else (12, 14, 12, 12)))
        rail_inset = (SIDEBAR_RAIL_WIDTH - 16 - self.icon_label.width()) // 2
        self.brand_layout.setContentsMargins(rail_inset if compact else 4, 0, 0, 0)
        self.brand_label.setVisible(not compact)
        self.collapse_btn.setVisible(not compact)
        self.expand_btn.setVisible(compact)
        self.section_label.setVisible(not compact)
        self.section_layout.setAlignment(
            self.add_dataset_btn,
            Qt.AlignmentFlag.AlignHCenter if compact else Qt.AlignmentFlag.AlignRight,
        )
        for button in (self.all_papers_btn, self.filters_btn, self.settings_btn):
            button.set_compact(compact)
        for item in self._dataset_items:
            item.set_compact(compact)

    def set_filter_count(self, count: int) -> None:
        text = tr("Filters")
        if count:
            text = f"{text} ({count})"
        self.filters_btn.set_full_text(text)

    def set_datasets(self, datasets: Sequence[dict]) -> None:
        for item in self._dataset_items:
            item.setParent(None)
            item.deleteLater()
        self._dataset_items = []
        for entry in datasets:
            item = DatasetSidebarItem(
                entry["conf"],
                entry["year"],
                f"{entry['name']} {entry['year']}",
                entry["papers"],
                self,
                badge_label=conference_badge_label(entry["name"]),
            )
            item.activated.connect(self.dataset_clicked.emit)
            item.menu_requested.connect(self._show_dataset_menu)
            item.context_menu_requested.connect(
                lambda conf, year, pos: self._show_dataset_menu(
                    conf, year, pos, include_refresh=True
                )
            )
            item.refresh_requested.connect(self.refresh_dataset.emit)
            item.set_active(bool(entry.get("selected")))
            item.set_compact(self._compact)
            self._dataset_items.append(item)
            self.dataset_layout.addWidget(item)

    def has_dataset(self, conf_slug: str, year: int) -> bool:
        return any(
            item.conf_slug == conf_slug and item.year == year
            for item in self._dataset_items
        )

    def set_active_dataset(self, conf_slug: str, year: int) -> None:
        for item in self._dataset_items:
            item.set_active(item.conf_slug == conf_slug and item.year == year)

    def refresh_icons(self) -> None:
        for button in (self.all_papers_btn, self.filters_btn, self.settings_btn):
            button.refresh_icon()
        for item in self._dataset_items:
            item.refresh_icon()
        for button, name in (
            (self.collapse_btn, "chevron-left"),
            (self.expand_btn, "chevron-right"),
            (self.add_dataset_btn, "plus"),
        ):
            button.setIcon(themed_icon(name))

    def _show_dataset_menu(
        self,
        conf_slug: str,
        year: int,
        position: QPoint,
        include_refresh: bool = False,
    ) -> None:
        menu = QMenu(self)
        refresh_action = (
            menu.addAction(tr("Refresh dataset")) if include_refresh else None
        )
        open_action = menu.addAction(tr("Open in folder"))
        delete_action = menu.addAction(tr("Delete dataset"))
        chosen = menu.exec(position)
        if chosen is None:
            return
        if chosen == refresh_action:
            self.refresh_dataset.emit(conf_slug, year)
        elif chosen == open_action:
            self.open_dataset_folder.emit(conf_slug, year)
        elif chosen == delete_action:
            self.delete_dataset.emit(conf_slug, year)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self.set_compact(self.width() < SIDEBAR_SNAP_WIDTH)


class SearchField(QFrame):
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("searchField")
        layout = QHBoxLayout()
        layout.setContentsMargins(12, 6, 10, 6)
        layout.setSpacing(8)
        self.icon_label = QLabel()
        self.icon_label.setFixedSize(18, 18)
        self.refresh_icon()
        self.line_edit = QLineEdit()
        self.line_edit.setObjectName("quickFilterEdit")
        self.line_edit.setClearButtonEnabled(True)
        self.line_edit.setPlaceholderText(tr("Search in results"))
        shortcut = QKeySequence(QKeySequence.StandardKey.Find).toString(
            QKeySequence.SequenceFormat.NativeText
        )
        self.shortcut_label = QLabel(shortcut)
        self.shortcut_label.setObjectName("searchHint")
        layout.addWidget(self.icon_label)
        layout.addWidget(self.line_edit, stretch=1)
        layout.addWidget(self.shortcut_label)
        self.setLayout(layout)

    def refresh_icon(self) -> None:
        self.icon_label.setPixmap(themed_icon("search").pixmap(16, 16))


class WorkspaceHeader(QFrame):
    filter_clicked = pyqtSignal()
    filter_removed = pyqtSignal(int)
    details_toggle_clicked = pyqtSignal()

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("workspaceHeader")
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        title_row = QHBoxLayout()
        title_row.setSpacing(12)
        title_block = QVBoxLayout()
        title_block.setSpacing(4)
        self.title_label = QLabel("PaperSpider")
        self.title_label.setObjectName("datasetTitle")
        self.subtitle_label = QLabel("")
        self.subtitle_label.setObjectName("datasetSubtitle")
        title_block.addWidget(self.title_label)
        title_block.addWidget(self.subtitle_label)
        self.details_toggle_btn = QToolButton()
        self.details_toggle_btn.setObjectName("iconButton")
        self.details_toggle_btn.setIcon(themed_icon("chevron-left"))
        self.details_toggle_btn.setIconSize(QSize(16, 16))
        self.details_toggle_btn.setToolTip(tr("Show details"))
        self.details_toggle_btn.setVisible(False)
        self.details_toggle_btn.clicked.connect(
            self.details_toggle_clicked.emit
        )
        self.search_field = SearchField()
        self.search_field.setMinimumWidth(240)
        self.search_field.setMaximumWidth(380)
        self.filter_btn = QPushButton(tr("Filters"))
        self.filter_btn.setObjectName("filterButton")
        self.filter_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.filter_btn.clicked.connect(self.filter_clicked.emit)
        self.refresh_filter_icon()
        title_row.addLayout(title_block, stretch=1)
        title_row.addWidget(self.search_field)
        title_row.addWidget(self.filter_btn)
        title_row.addWidget(self.details_toggle_btn)
        layout.addLayout(title_row)

        self.chips_container = QWidget()
        self.chips_layout = QHBoxLayout()
        self.chips_layout.setContentsMargins(0, 0, 0, 0)
        self.chips_layout.setSpacing(8)
        self.chips_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.chips_container.setLayout(self.chips_layout)
        self.chips_container.setVisible(False)
        layout.addWidget(self.chips_container)
        self.setLayout(layout)

    @property
    def quick_filter_edit(self) -> QLineEdit:
        return self.search_field.line_edit

    def set_dataset(self, title: str, subtitle: str) -> None:
        self.title_label.setText(title)
        self.subtitle_label.setText(subtitle)

    def set_details_hidden(self, hidden: bool) -> None:
        self.details_toggle_btn.setVisible(hidden)

    def set_counts(self, total: int, matched: int) -> None:
        from .i18n import match_count, paper_count

        self.subtitle_label.setText(
            f"{paper_count(total)} · {match_count(matched)}"
        )

    def set_filters(self, configs: Sequence[FilterConfig]) -> None:
        while self.chips_layout.count():
            item = self.chips_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        for index, config in enumerate(configs):
            chip = QFrame()
            chip.setObjectName("filterChip")
            chip.setProperty("role", config.role)
            chip_layout = QHBoxLayout()
            chip_layout.setContentsMargins(10, 4, 4, 4)
            chip_layout.setSpacing(2)
            label = QLabel(
                f"{filter_role_label(config.role)} · {config.value}"
            )
            label.setObjectName("filterChipLabel")
            close_btn = QToolButton()
            close_btn.setObjectName("chipClose")
            close_btn.setText("×")
            close_btn.setToolTip(tr("Remove this rule"))
            close_btn.clicked.connect(
                lambda _checked=False, idx=index: self.filter_removed.emit(idx)
            )
            chip_layout.addWidget(label)
            chip_layout.addWidget(close_btn)
            chip.setLayout(chip_layout)
            self.chips_layout.addWidget(chip)
        self.chips_layout.addStretch(1)
        self.chips_container.setVisible(bool(configs))
        text = tr("Filters")
        if configs:
            text = f"{text} ({len(configs)})"
        self.filter_btn.setText(text)
        self.filter_btn.setProperty("active", bool(configs))
        _repolish(self.filter_btn)

    def refresh_filter_icon(self) -> None:
        self.filter_btn.setIcon(themed_icon("filter"))
        self.filter_btn.setIconSize(QSize(16, 16))

    def refresh_icons(self) -> None:
        self.search_field.refresh_icon()
        self.refresh_filter_icon()
        self.details_toggle_btn.setIcon(themed_icon("chevron-left"))
        self.details_toggle_btn.setIconSize(QSize(16, 16))


class DetailsPanel(QWidget):
    abstract_action_clicked = pyqtSignal()
    open_pdf_clicked = pyqtSignal()
    copy_bib_clicked = pyqtSignal()
    reveal_pdf_clicked = pyqtSignal()
    close_clicked = pyqtSignal()

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("detailsPanel")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setMinimumWidth(360)
        layout = QVBoxLayout()
        layout.setContentsMargins(26, 18, 26, 12)
        layout.setSpacing(10)

        self.breadcrumb_label = QLabel("")
        self.breadcrumb_label.setObjectName("detailsBreadcrumb")
        self.close_btn = QToolButton()
        self.close_btn.setObjectName("iconButton")
        self.close_btn.setIcon(themed_icon("chevron-right"))
        self.close_btn.setIconSize(QSize(16, 16))
        self.close_btn.setToolTip(tr("Hide details"))
        self.close_btn.clicked.connect(self.close_clicked.emit)
        breadcrumb_row = QHBoxLayout()
        breadcrumb_row.setContentsMargins(0, 0, 0, 0)
        breadcrumb_row.addWidget(self.breadcrumb_label, stretch=1)
        breadcrumb_row.addWidget(self.close_btn)
        self.title_label = QLabel()
        self.title_label.setObjectName("paperTitle")
        self.title_label.setWordWrap(True)
        self.authors_label = QLabel()
        self.authors_label.setObjectName("paperAuthors")
        self.authors_label.setWordWrap(True)

        self.tags_container = QWidget()
        self.tags_layout = QHBoxLayout()
        self.tags_layout.setContentsMargins(0, 0, 0, 0)
        self.tags_layout.setSpacing(6)
        self.tags_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.tags_container.setLayout(self.tags_layout)
        self.tags_container.setVisible(False)

        actions = QHBoxLayout()
        actions.setSpacing(10)
        self.open_pdf_btn = QPushButton(tr("Open PDF"))
        self.open_pdf_btn.setObjectName("primaryButton")
        self.copy_bib_btn = QPushButton(tr("Copy BibTeX"))
        self.copy_bib_btn.setObjectName("secondaryButton")
        self.open_pdf_btn.clicked.connect(self.open_pdf_clicked.emit)
        self.copy_bib_btn.clicked.connect(self.copy_bib_clicked.emit)
        actions.addWidget(self.open_pdf_btn, stretch=1)
        actions.addWidget(self.copy_bib_btn, stretch=1)

        divider = QFrame()
        divider.setObjectName("sidebarDivider")
        divider.setFrameShape(QFrame.Shape.HLine)

        abstract_header = QHBoxLayout()
        abstract_title = QLabel(tr("Abstract"))
        abstract_title.setObjectName("sectionTitle")
        self.abstract_action_btn = QToolButton()
        self.abstract_action_btn.setObjectName("sectionAction")
        self.abstract_action_btn.setText(tr("Copy"))
        self.abstract_action_btn.setToolTip(tr("Download abstract"))
        self.abstract_action_btn.clicked.connect(
            self.abstract_action_clicked.emit
        )
        abstract_header.addWidget(abstract_title)
        abstract_header.addStretch(1)
        abstract_header.addWidget(self.abstract_action_btn)

        self.abstract_text = QTextEdit()
        self.abstract_text.setObjectName("abstractText")
        self.abstract_text.setReadOnly(True)
        self.abstract_text.setPlaceholderText(
            tr("Abstract will appear here when available.")
        )
        self.abstract_text.setFrameShape(QFrame.Shape.NoFrame)

        self.reveal_pdf_btn = QPushButton(tr("Show in folder"))
        self.reveal_pdf_btn.setObjectName("secondaryButton")
        self.reveal_pdf_btn.clicked.connect(self.reveal_pdf_clicked.emit)

        self.feedback_label = QLabel("")
        self.feedback_label.setObjectName("detailsFeedbackLabel")
        self.feedback_label.setWordWrap(True)

        self.content_widget = QWidget()
        content_layout = QVBoxLayout()
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(10)
        content_layout.addWidget(self.title_label)
        content_layout.addWidget(self.authors_label)
        content_layout.addWidget(self.tags_container)
        content_layout.addSpacing(4)
        content_layout.addLayout(actions)
        content_layout.addSpacing(4)
        content_layout.addWidget(divider)
        content_layout.addLayout(abstract_header)
        content_layout.addWidget(self.abstract_text, stretch=1)
        content_layout.addWidget(self.reveal_pdf_btn)
        content_layout.addWidget(self.feedback_label)
        self.content_widget.setLayout(content_layout)

        self.placeholder = QWidget()
        placeholder_layout = QVBoxLayout()
        placeholder_layout.setSpacing(6)
        placeholder_layout.addStretch(2)
        self.placeholder_icon = QLabel()
        self.placeholder_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        placeholder_title = QLabel(tr("No paper selected"))
        placeholder_title.setObjectName("placeholderTitle")
        placeholder_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        placeholder_text = QLabel(tr("Select a row to preview details."))
        placeholder_text.setObjectName("placeholderText")
        placeholder_text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        placeholder_text.setWordWrap(True)
        placeholder_layout.addWidget(self.placeholder_icon)
        placeholder_layout.addSpacing(4)
        placeholder_layout.addWidget(placeholder_title)
        placeholder_layout.addWidget(placeholder_text)
        placeholder_layout.addStretch(3)
        self.placeholder.setLayout(placeholder_layout)

        layout.addLayout(breadcrumb_row)
        layout.addWidget(self.content_widget, stretch=1)
        layout.addWidget(self.placeholder, stretch=1)
        self.setLayout(layout)
        self.refresh_icons()
        self.set_row(None)

    def refresh_icons(self) -> None:
        self.close_btn.setIcon(themed_icon("chevron-right"))
        self.close_btn.setIconSize(QSize(16, 16))
        self.reveal_pdf_btn.setIcon(themed_icon("folder"))
        self.reveal_pdf_btn.setIconSize(QSize(16, 16))
        self.placeholder_icon.setPixmap(themed_icon("paper").pixmap(36, 36))

    def _set_tags(self, values: Sequence[str]) -> None:
        while self.tags_layout.count():
            item = self.tags_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        for value in values:
            chip = QFrame()
            chip.setObjectName("tagChip")
            chip_layout = QHBoxLayout()
            chip_layout.setContentsMargins(9, 4, 9, 4)
            label = QLabel(value)
            label.setObjectName("tagText")
            chip_layout.addWidget(label)
            chip.setLayout(chip_layout)
            self.tags_layout.addWidget(chip)
        self.tags_layout.addStretch(1)
        self.tags_container.setVisible(bool(values))

    def set_row(self, row: Optional[dict]) -> None:
        self.content_widget.setVisible(bool(row))
        self.placeholder.setVisible(not row)
        self.breadcrumb_label.setVisible(bool(row))
        if not row:
            return

        track = str(row.get("track") or "")
        paper_type = str(row.get("paper_type") or "")
        category = (
            display_category(track, paper_type)
            if track or paper_type
            else str(row.get("category_text") or "")
        )
        keywords = str(row.get("keywords_text") or "")
        abstract = str(row.get("abstract") or "")
        pdf_path = row.get("pdf_path")
        conf = str(row.get("conf") or "").replace("_", " ").upper()
        breadcrumb = " / ".join(
            part for part in (f"{conf} {row.get('year') or ''}".strip(), category) if part
        )
        self.breadcrumb_label.setText(breadcrumb)
        self.title_label.setText(row_title(row) or tr("Untitled paper"))
        self.authors_label.setText(str(row.get("authors_text") or tr("Unknown authors")))
        self._set_tags([value.strip() for value in keywords.split(",") if value.strip()][:6])
        self.abstract_text.setPlainText(abstract)
        self.set_feedback("")
        self.reveal_pdf_btn.setVisible(bool(pdf_path))
        self.abstract_action_btn.setText(tr("Copy") if abstract else tr("Download"))
        self.abstract_action_btn.setToolTip(
            tr("Copy abstract") if abstract else tr("Download abstract")
        )
        self.open_pdf_btn.setText(tr("Open PDF") if pdf_path else tr("Download PDF"))

    def set_feedback(self, message: str) -> None:
        self.feedback_label.setText(message)
        self.feedback_label.setVisible(bool(message))


class EmptyStateWidget(QWidget):
    primary_clicked = pyqtSignal()

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.title_label = QLabel(tr("Choose a dataset to start"))
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.title_label.setObjectName("emptyTitle")
        self.message_label = QLabel("")
        self.message_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.message_label.setWordWrap(True)
        self.message_label.setObjectName("mutedLabel")
        self.primary_btn = QPushButton(tr("Choose dataset"))
        self.primary_btn.setObjectName("primaryButton")
        self.primary_btn.clicked.connect(self.primary_clicked.emit)

        layout.addStretch()
        layout.addWidget(self.title_label)
        layout.addWidget(self.message_label)
        layout.addSpacing(8)
        layout.addWidget(self.primary_btn, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addStretch()
        self.setLayout(layout)

    def set_content(self, title: str, message: str, button_text: str) -> None:
        self.title_label.setText(title)
        self.message_label.setText(message)
        self.primary_btn.setText(button_text)


class CollapsibleLogPanel(QFrame):
    cancel_clicked = pyqtSignal()

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("taskBar")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.log_view = QTextEdit()
        self.log_view.setObjectName("taskLog")
        self.log_view.setReadOnly(True)
        self.log_view.setVisible(False)
        self.log_view.setMaximumHeight(180)

        bar = QWidget()
        bar_layout = QHBoxLayout()
        bar_layout.setContentsMargins(18, 8, 18, 8)
        bar_layout.setSpacing(12)
        self.status_label = QLabel(tr("Ready"))
        self.status_label.setObjectName("taskStatus")
        self.status_label.setMinimumWidth(180)
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 1)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(False)
        self.progress_count_label = QLabel("")
        self.progress_count_label.setObjectName("taskProgressCount")
        self.progress_count_label.setVisible(False)
        self.cancel_btn = QPushButton(tr("Cancel"))
        self.cancel_btn.setObjectName("taskCancel")
        self.cancel_btn.setVisible(False)
        self.cancel_btn.clicked.connect(self.cancel_clicked.emit)
        self.toggle_btn = QToolButton()
        self.toggle_btn.setObjectName("logToggleButton")
        self.toggle_btn.setText(tr("Task log"))
        self.toggle_btn.setArrowType(Qt.ArrowType.NoArrow)
        self.toggle_btn.setToolButtonStyle(
            Qt.ToolButtonStyle.ToolButtonTextOnly
        )
        self.toggle_btn.setCheckable(True)
        self.toggle_btn.setProperty("expanded", False)
        self.toggle_btn.toggled.connect(self._set_log_visible)

        bar_layout.addWidget(self.status_label)
        bar_layout.addWidget(self.progress_bar, stretch=1)
        bar_layout.addWidget(self.progress_count_label)
        bar_layout.addWidget(self.cancel_btn)
        bar_layout.addWidget(self.toggle_btn)
        bar.setLayout(bar_layout)

        layout.addWidget(self.log_view)
        layout.addWidget(bar)
        self.setLayout(layout)
        self.set_ready()

    def append_log(self, message: str) -> None:
        self.log_view.append(message)

    def set_busy(
        self,
        message: str,
        current: Optional[int] = None,
        total: Optional[int] = None,
        show_cancel: bool = True,
    ) -> None:
        self.status_label.setText(message)
        if current is not None and total:
            self.progress_bar.setRange(0, total)
            self.progress_bar.setValue(current)
            self.progress_count_label.setText(f"{current} / {total}")
            self.progress_count_label.setVisible(True)
        else:
            self.progress_bar.setRange(0, 0)
            self.progress_count_label.setVisible(False)
        self.progress_bar.setVisible(True)
        self.cancel_btn.setVisible(show_cancel)

    def set_ready(self, message: Optional[str] = None) -> None:
        self.status_label.setText(tr("Ready") if message is None else message)
        self.progress_bar.setRange(0, 1)
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(False)
        self.progress_count_label.setVisible(False)
        self.cancel_btn.setVisible(False)

    def show_cancel(self, visible: bool) -> None:
        self.cancel_btn.setVisible(visible)

    def expand_log(self) -> None:
        self.toggle_btn.setChecked(True)

    def _set_log_visible(self, visible: bool) -> None:
        self.log_view.setVisible(visible)
        self.toggle_btn.setProperty("expanded", visible)
        self.toggle_btn.style().unpolish(self.toggle_btn)
        self.toggle_btn.style().polish(self.toggle_btn)