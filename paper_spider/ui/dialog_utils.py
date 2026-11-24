# Copyright 2026 Isaacveg
# Licensed under the Apache License, Version 2.0 (the "License");

from __future__ import annotations

from typing import Optional

from PyQt6.QtCore import QPoint, QSize, Qt
from PyQt6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QLayout,
    QMessageBox,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from .i18n import tr
from .theme import apply_theme, themed_icon


def configure_utility_dialog(dialog: QDialog) -> None:
    """Use app-provided footer actions instead of operating-system chrome."""

    dialog.setWindowFlag(Qt.WindowType.FramelessWindowHint, True)
    dialog.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
    dialog.setObjectName("utilityDialog")


class DialogTitleBar(QWidget):
    """In-app title bar for frameless dialogs: title, close button, drag to move."""

    def __init__(self, dialog: QDialog) -> None:
        super().__init__(dialog)
        self._dialog = dialog
        self._drag_offset: Optional[QPoint] = None
        self.setObjectName("dialogTitleBar")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setFixedHeight(42)
        layout = QHBoxLayout()
        layout.setContentsMargins(16, 0, 8, 0)
        self.title_label = QLabel(dialog.windowTitle())
        self.title_label.setObjectName("dialogTitle")
        self.close_btn = QToolButton()
        self.close_btn.setObjectName("iconButton")
        self.close_btn.setIcon(themed_icon("close"))
        self.close_btn.setIconSize(QSize(16, 16))
        self.close_btn.setToolTip(tr("Close"))
        self.close_btn.clicked.connect(dialog.reject)
        layout.addWidget(self.title_label, stretch=1)
        layout.addWidget(self.close_btn)
        self.setLayout(layout)
        dialog.windowTitleChanged.connect(self.title_label.setText)

    def mousePressEvent(self, event) -> None:
        if event.button() != Qt.MouseButton.LeftButton:
            return super().mousePressEvent(event)
        handle = self._dialog.windowHandle()
        if handle is not None and handle.startSystemMove():
            return
        self._drag_offset = (
            event.globalPosition().toPoint() - self._dialog.frameGeometry().topLeft()
        )

    def mouseMoveEvent(self, event) -> None:
        if self._drag_offset is not None:
            self._dialog.move(event.globalPosition().toPoint() - self._drag_offset)
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        self._drag_offset = None
        super().mouseReleaseEvent(event)


def finish_utility_dialog(dialog: QDialog, content: QLayout) -> DialogTitleBar:
    """Install ``content`` below a draggable title bar as the dialog's layout."""

    container = QWidget()
    container.setLayout(content)
    root = QVBoxLayout()
    root.setContentsMargins(1, 1, 1, 1)
    root.setSpacing(0)
    title_bar = DialogTitleBar(dialog)
    root.addWidget(title_bar)
    root.addWidget(container, stretch=1)
    dialog.setLayout(root)
    dialog.title_bar = title_bar
    return title_bar


def build_message_box(
    parent: Optional[QWidget],
    icon: QMessageBox.Icon,
    title: str,
    text: str,
    buttons: QMessageBox.StandardButton = QMessageBox.StandardButton.Close,
) -> QMessageBox:
    box = QMessageBox(parent)
    configure_utility_dialog(box)
    box.setObjectName("messageDialog")
    box.setWindowTitle(title)
    box.setIcon(QMessageBox.Icon.NoIcon)
    box.setText(title)
    box.setInformativeText(text)
    box.setStandardButtons(buttons)

    close_button = box.button(QMessageBox.StandardButton.Close)
    cancel_button = box.button(QMessageBox.StandardButton.Cancel)
    yes_button = box.button(QMessageBox.StandardButton.Yes)
    if close_button is not None:
        close_button.setObjectName("primaryButton")
        box.setDefaultButton(QMessageBox.StandardButton.Close)
        box.setEscapeButton(close_button)
    if cancel_button is not None:
        cancel_button.setObjectName("secondaryButton")
        box.setDefaultButton(QMessageBox.StandardButton.Cancel)
        box.setEscapeButton(cancel_button)
    if yes_button is not None:
        yes_button.setObjectName("primaryButton")
        if cancel_button is None:
            box.setDefaultButton(QMessageBox.StandardButton.Yes)

    apply_theme(box)
    return box


def _exec_message(box: QMessageBox) -> QMessageBox.StandardButton:
    return QMessageBox.StandardButton(box.exec())


def show_information(parent: Optional[QWidget], title: str, text: str) -> None:
    _exec_message(build_message_box(parent, QMessageBox.Icon.Information, title, text))


def show_warning(parent: Optional[QWidget], title: str, text: str) -> None:
    _exec_message(build_message_box(parent, QMessageBox.Icon.Warning, title, text))


def show_error(parent: Optional[QWidget], title: str, text: str) -> None:
    _exec_message(build_message_box(parent, QMessageBox.Icon.Critical, title, text))


def ask_confirmation(
    parent: Optional[QWidget],
    title: str,
    text: str,
    confirm_text: Optional[str] = None,
    cancel_text: Optional[str] = None,
) -> bool:
    box = build_message_box(
        parent,
        QMessageBox.Icon.Question,
        title,
        text,
        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
    )
    yes_button = box.button(QMessageBox.StandardButton.Yes)
    cancel_button = box.button(QMessageBox.StandardButton.Cancel)
    if yes_button is not None and confirm_text:
        yes_button.setText(confirm_text)
    if cancel_button is not None and cancel_text:
        cancel_button.setText(cancel_text)
    return _exec_message(box) == QMessageBox.StandardButton.Yes
