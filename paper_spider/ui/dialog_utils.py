# Copyright 2026 Isaacveg
# Licensed under the Apache License, Version 2.0 (the "License");

from __future__ import annotations

from typing import Optional

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QDialog, QMessageBox, QWidget

from .theme import apply_theme


def configure_utility_dialog(dialog: QDialog) -> None:
    """Use app-provided footer actions instead of operating-system chrome."""

    dialog.setWindowFlag(Qt.WindowType.FramelessWindowHint, True)
    dialog.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
    dialog.setObjectName("utilityDialog")


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
    box.setIcon(icon)
    box.setText(text)
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


def ask_confirmation(parent: Optional[QWidget], title: str, text: str) -> bool:
    box = build_message_box(
        parent,
        QMessageBox.Icon.Question,
        title,
        text,
        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
    )
    return _exec_message(box) == QMessageBox.StandardButton.Yes
