# Copyright 2026 Isaacveg
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#     http://www.apache.org/licenses/LICENSE-2.0

"""Workspace widgets: sidebar, header, details panel, and task bar."""

from __future__ import annotations

from pathlib import Path
from typing import List, Optional, Sequence

from PyQt6.QtCore import QPoint, QSize, Qt, pyqtSignal
from PyQt6.QtGui import (
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
    QTextEdit,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from ..filtering import FilterConfig
from .filter_dialog import filter_role_label
from .i18n import display_category, tr
from .theme import themed_icon


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
        self.setObjectName("sidebarItem")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setCheckable(False)
        self.setToolTip(text)
        self.setAccessibleName(text)
        if icon_name:
            self.refresh_icon()

    def set_full_text(self, text: str) -> None:
        self._full_text = text
        self.setToolTip(text)
        self.setAccessibleName(text)
        self._refresh_text()

    def _refresh_text(self) -> None:
        if self._elide:
            available = max(12, self.width() - 48)
            text = self.fontMetrics().elidedText(
                self._full_text, Qt.TextElideMode.ElideRight, available
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
            painter.drawEllipse(
                center.x() + offset - 2,
                center.y() - 2,
                4,
                4,
            )

    def enterEvent(self, event) -> None:
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:
        self.update()
        super().leaveEvent(event)


class DatasetSidebarItem(QWidget):
    activated = pyqtSignal(str, int)
    menu_requested = pyqtSignal(str, int, QPoint)
    refresh_requested = pyqtSignal(str, int)

    def __init__(
        self,
        conf_slug: str,
        year: int,
        text: str,
        paper_count: int,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.conf_slug = conf_slug
        self.year = year
        self.setObjectName("datasetItem")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_Hover, True)
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 8, 0)
        layout.setSpacing(2)
        self.main_btn = SidebarButton(text, "nav-dataset", self, elide=True)
        self.main_btn.setToolTip(f"{text} · {tr('{count} papers', count=paper_count)}")
        self.main_btn.clicked.connect(
            lambda: self.activated.emit(self.conf_slug, self.year)
        )
        self.refresh_btn = QToolButton()
        self.refresh_btn.setObjectName("datasetRefreshAction")
        self.refresh_btn.setIcon(themed_icon("refresh"))
        self.refresh_btn.setIconSize(QSize(15, 15))
        self.refresh_btn.setFixedSize(24, 24)
        self.refresh_btn.setToolTip(tr("Refresh dataset"))
        self.refresh_btn.setVisible(False)
        self.refresh_btn.clicked.connect(self._request_refresh)
        self.menu_btn = DatasetMenuButton(self)
        self.menu_btn.setVisible(False)
        self.menu_btn.clicked.connect(self._request_menu)
        layout.addWidget(self.main_btn, stretch=1)
        layout.addWidget(
            self.refresh_btn, alignment=Qt.AlignmentFlag.AlignVCenter
        )
        layout.addWidget(
            self.menu_btn, alignment=Qt.AlignmentFlag.AlignVCenter
        )
        self.setLayout(layout)
        self._active = False
        self._hovered = False
        self._update_menu_visibility()

    def set_active(self, active: bool) -> None:
        self._active = active
        self.setProperty("active", active)
        self.style().unpolish(self)
        self.style().polish(self)
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
        visible = self._active or self._hovered
        self.refresh_btn.setVisible(visible)
        self.menu_btn.setVisible(visible)

    def _request_refresh(self) -> None:
        self.refresh_requested.emit(self.conf_slug, self.year)

    def _request_menu(self) -> None:
        position = self.menu_btn.mapToGlobal(
            QPoint(0, self.menu_btn.height())
        )
        self.menu_requested.emit(self.conf_slug, self.year, position)

    def refresh_icon(self) -> None:
        self.main_btn.refresh_icon()
        self.refresh_btn.setIcon(themed_icon("refresh"))
        self.refresh_btn.setIconSize(QSize(15, 15))


class AppSidebar(QWidget):
    settings_clicked = pyqtSignal()
    add_dataset_clicked = pyqtSignal()
    all_papers_clicked = pyqtSignal()
    filters_clicked = pyqtSignal()
    dataset_clicked = pyqtSignal(str, int)
    collapse_clicked = pyqtSignal()
    open_dataset_folder = pyqtSignal(str, int)
    delete_dataset = pyqtSignal(str, int)
    refresh_dataset = pyqtSignal(str, int)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("appSidebar")
        self.setMinimumWidth(140)
        self.setMaximumWidth(440)
        self._dataset_items: List[DatasetSidebarItem] = []

        layout = QVBoxLayout()
        layout.setContentsMargins(18, 18, 14, 16)
        layout.setSpacing(8)
        self.root_layout = layout

        brand = QHBoxLayout()
        brand.setSpacing(10)
        icon_label = QLabel()
        icon_path = Path(__file__).with_name("assets") / "app-icon.png"
        device_ratio = 1.0
        screen = QGuiApplication.primaryScreen()
        if screen is not None:
            device_ratio = screen.devicePixelRatio()
        pixmap = QPixmap(icon_path.as_posix()).scaled(
            int(40 * device_ratio),
            int(40 * device_ratio),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        pixmap.setDevicePixelRatio(device_ratio)
        icon_label.setPixmap(pixmap)
        icon_label.setFixedSize(42, 42)
        self.brand_label = QLabel("PaperSpider")
        self.brand_label.setObjectName("brandLabel")
        self.collapse_btn = QToolButton()
        self.collapse_btn.setObjectName("iconButton")
        self.collapse_btn.setIcon(themed_icon("chevron-left"))
        self.collapse_btn.setIconSize(QSize(16, 16))
        self.collapse_btn.setToolTip(tr("Collapse sidebar"))
        self.collapse_btn.clicked.connect(self.collapse_clicked.emit)
        brand.addWidget(icon_label)
        brand.addWidget(self.brand_label)
        brand.addStretch(1)
        brand.addWidget(self.collapse_btn)
        layout.addLayout(brand)
        layout.addSpacing(12)

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

        section = QHBoxLayout()
        section.setContentsMargins(8, 4, 0, 0)
        self.section_label = QLabel(tr("Conference datasets"))
        self.section_label.setObjectName("sidebarSection")
        self.add_dataset_btn = QToolButton()
        self.add_dataset_btn.setObjectName("sidebarAddButton")
        self.add_dataset_btn.setText("+")
        self.add_dataset_btn.setToolTip(tr("Add dataset"))
        self.add_dataset_btn.clicked.connect(self.add_dataset_clicked.emit)
        section.addWidget(self.section_label)
        section.addStretch(1)
        section.addWidget(self.add_dataset_btn)
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
        layout.addWidget(self.dataset_scroll, stretch=1)

        self.settings_btn = SidebarButton(tr("Settings"), "nav-settings")
        self.settings_btn.setObjectName("sidebarSettings")
        self.settings_btn.clicked.connect(self.settings_clicked.emit)
        layout.addWidget(self.settings_btn)
        self.setLayout(layout)
        self._apply_compact_layout()

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
            )
            item.activated.connect(self.dataset_clicked.emit)
            item.menu_requested.connect(self._show_dataset_menu)
            item.refresh_requested.connect(self.refresh_dataset.emit)
            item.set_active(bool(entry.get("selected")))
            self._dataset_items.append(item)
            self.dataset_layout.addWidget(item)

    def set_active_dataset(self, conf_slug: str, year: int) -> None:
        for item in self._dataset_items:
            item.set_active(
                item.conf_slug == conf_slug and item.year == year
            )

    def refresh_icons(self) -> None:
        for button in (
            self.all_papers_btn,
            self.filters_btn,
            self.settings_btn,
        ):
            button.refresh_icon()
        for item in self._dataset_items:
            item.refresh_icon()
        self.collapse_btn.setIcon(themed_icon("chevron-left"))
        self.collapse_btn.setIconSize(QSize(16, 16))

    def _show_dataset_menu(
        self, conf_slug: str, year: int, position: QPoint
    ) -> None:
        menu = QMenu(self)
        open_action = menu.addAction(tr("Open in folder"))
        delete_action = menu.addAction(tr("Delete dataset"))
        chosen = menu.exec(position)
        if chosen == open_action:
            self.open_dataset_folder.emit(conf_slug, year)
        elif chosen == delete_action:
            self.delete_dataset.emit(conf_slug, year)

    def _apply_compact_layout(self) -> None:
        width = self.width()
        self.brand_label.setVisible(width >= 210)
        self.section_label.setVisible(width >= 190)
        if width < 210:
            self.root_layout.setContentsMargins(10, 14, 8, 12)
        else:
            self.root_layout.setContentsMargins(18, 18, 14, 16)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._apply_compact_layout()


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
    sidebar_toggle_clicked = pyqtSignal()
    details_toggle_clicked = pyqtSignal()

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("workspaceHeader")
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        title_row = QHBoxLayout()
        title_row.setSpacing(12)
        self.sidebar_toggle_btn = QToolButton()
        self.sidebar_toggle_btn.setObjectName("iconButton")
        self.sidebar_toggle_btn.setIcon(themed_icon("chevron-right"))
        self.sidebar_toggle_btn.setIconSize(QSize(16, 16))
        self.sidebar_toggle_btn.setToolTip(tr("Show sidebar"))
        self.sidebar_toggle_btn.setVisible(False)
        self.sidebar_toggle_btn.clicked.connect(
            self.sidebar_toggle_clicked.emit
        )
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
        title_row.addWidget(self.sidebar_toggle_btn)
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

    def set_sidebar_hidden(self, hidden: bool) -> None:
        self.sidebar_toggle_btn.setVisible(hidden)

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

    def refresh_filter_icon(self) -> None:
        self.filter_btn.setIcon(themed_icon("filter"))
        self.filter_btn.setIconSize(QSize(16, 16))

    def refresh_icons(self) -> None:
        self.search_field.refresh_icon()
        self.refresh_filter_icon()
        self.sidebar_toggle_btn.setIcon(themed_icon("chevron-right"))
        self.sidebar_toggle_btn.setIconSize(QSize(16, 16))
        self.details_toggle_btn.setIcon(themed_icon("chevron-left"))
        self.details_toggle_btn.setIconSize(QSize(16, 16))


class DetailsPanel(QWidget):
    download_abstract_clicked = pyqtSignal()
    open_pdf_clicked = pyqtSignal()
    copy_bib_clicked = pyqtSignal()
    reveal_pdf_clicked = pyqtSignal()
    close_clicked = pyqtSignal()

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("detailsPanel")
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
        self.title_label = QLabel(tr("No paper selected"))
        self.title_label.setObjectName("paperTitle")
        self.title_label.setWordWrap(True)
        self.authors_label = QLabel(tr("Select a row to preview details."))
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
        self.download_abstract_btn = QToolButton()
        self.download_abstract_btn.setObjectName("sectionAction")
        self.download_abstract_btn.setText(tr("Copy"))
        self.download_abstract_btn.setToolTip(tr("Download abstract"))
        self.download_abstract_btn.clicked.connect(
            self.download_abstract_clicked.emit
        )
        abstract_header.addWidget(abstract_title)
        abstract_header.addStretch(1)
        abstract_header.addWidget(self.download_abstract_btn)

        self.abstract_text = QTextEdit()
        self.abstract_text.setObjectName("abstractText")
        self.abstract_text.setReadOnly(True)
        self.abstract_text.setPlaceholderText(
            tr("Abstract will appear here when available.")
        )
        self.abstract_text.setFrameShape(QFrame.Shape.NoFrame)

        self.local_files_container = QWidget()
        local_files_layout = QVBoxLayout()
        local_files_layout.setContentsMargins(0, 0, 0, 0)
        local_files_layout.setSpacing(8)
        files_title = QLabel(tr("Local files"))
        files_title.setObjectName("sectionTitle")
        self.reveal_pdf_btn = QPushButton(tr("Show in folder"))
        self.reveal_pdf_btn.setObjectName("secondaryButton")
        self.reveal_pdf_btn.setIcon(themed_icon("folder"))
        self.reveal_pdf_btn.setIconSize(QSize(16, 16))
        self.reveal_pdf_btn.clicked.connect(self.reveal_pdf_clicked.emit)
        local_files_layout.addWidget(files_title)
        local_files_layout.addWidget(self.reveal_pdf_btn)
        self.local_files_container.setLayout(local_files_layout)

        self.feedback_label = QLabel("")
        self.feedback_label.setObjectName("detailsFeedbackLabel")
        self.feedback_label.setWordWrap(True)

        layout.addLayout(breadcrumb_row)
        layout.addWidget(self.title_label)
        layout.addWidget(self.authors_label)
        layout.addWidget(self.tags_container)
        layout.addLayout(actions)
        layout.addWidget(divider)
        layout.addLayout(abstract_header)
        layout.addWidget(self.abstract_text, stretch=1)
        layout.addWidget(self.local_files_container)
        layout.addWidget(self.feedback_label)
        self.setLayout(layout)
        self.set_row(None)

    def refresh_icons(self) -> None:
        self.close_btn.setIcon(themed_icon("chevron-right"))
        self.close_btn.setIconSize(QSize(16, 16))
        self.reveal_pdf_btn.setIcon(themed_icon("folder"))
        self.reveal_pdf_btn.setIconSize(QSize(16, 16))

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
        if not row:
            self.breadcrumb_label.setText("")
            self.title_label.setText(tr("No paper selected"))
            self.authors_label.setText(tr("Select a row to preview details."))
            self.abstract_text.clear()
            self._set_tags([])
            self.local_files_container.setVisible(False)
            self.reveal_pdf_btn.setEnabled(False)
            self.set_feedback("")
            self._set_action_enabled(False, False, False, False)
            self.download_abstract_btn.setText(tr("Copy"))
            self.download_abstract_btn.setToolTip(tr("Download abstract"))
            self.open_pdf_btn.setText(tr("Open PDF"))
            self.copy_bib_btn.setText(tr("Copy BibTeX"))
            return

        authors = row.get("authors_text") or tr("Unknown authors")
        track = str(row.get("track") or "")
        paper_type = str(row.get("paper_type") or "")
        category = (
            display_category(track, paper_type)
            if track or paper_type
            else str(row.get("category_text") or tr("Uncategorized"))
        )
        keywords = row.get("keywords_text") or ""
        abstract = row.get("abstract") or ""
        pdf_path = row.get("pdf_path") or ""
        conf = str(row.get("conf") or "").replace("_", " ").upper()
        year = row.get("year") or ""

        breadcrumb = f"{conf} {year}".strip()
        if category:
            breadcrumb = f"{breadcrumb} / {category}" if breadcrumb else category
        self.breadcrumb_label.setText(breadcrumb)
        self.title_label.setText(str(row.get("title") or tr("Untitled paper")))
        self.authors_label.setText(str(authors))
        tags = [
            value.strip()
            for value in str(keywords).split(",")
            if value.strip()
        ][:6]
        if not tags:
            tags = [category]
        self._set_tags(tags)
        self.abstract_text.setPlainText(str(abstract))
        self.set_feedback("")
        self.local_files_container.setVisible(bool(pdf_path))
        self.reveal_pdf_btn.setEnabled(bool(pdf_path))
        self.download_abstract_btn.setText(
            tr("Copy") if abstract else tr("Download")
        )
        self.download_abstract_btn.setToolTip(
            tr("Copy abstract") if abstract else tr("Download abstract")
        )
        self.open_pdf_btn.setText(
            tr("Open PDF") if pdf_path else tr("Download PDF")
        )
        self.copy_bib_btn.setText(tr("Copy BibTeX"))
        self._set_action_enabled(
            True, True, True, bool(pdf_path)
        )

    def set_feedback(self, message: str) -> None:
        self.feedback_label.setText(message)
        self.feedback_label.setVisible(bool(message))

    def _set_action_enabled(
        self,
        open_pdf: bool,
        download_abstract: bool,
        copy_bib: bool,
        reveal_pdf: bool,
    ) -> None:
        self.open_pdf_btn.setEnabled(open_pdf)
        self.download_abstract_btn.setEnabled(download_abstract)
        self.copy_bib_btn.setEnabled(copy_bib)
        self.reveal_pdf_btn.setEnabled(reveal_pdf)


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
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.log_view = QTextEdit()
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

    def _set_log_visible(self, visible: bool) -> None:
        self.log_view.setVisible(visible)
        self.toggle_btn.setProperty("expanded", visible)
        self.toggle_btn.style().unpolish(self.toggle_btn)
        self.toggle_btn.style().polish(self.toggle_btn)