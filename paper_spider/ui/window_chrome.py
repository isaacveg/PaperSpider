# Copyright 2026 Isaacveg
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#     http://www.apache.org/licenses/LICENSE-2.0

from __future__ import annotations

import sys
from typing import Optional

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QMouseEvent
from PyQt6.QtWidgets import QFrame, QHBoxLayout, QLabel, QToolButton, QWidget


def is_macos() -> bool:
    return sys.platform == "darwin"


def apply_window_chrome(widget: QWidget) -> None:
    if not (widget.windowFlags() & Qt.WindowType.FramelessWindowHint):
        widget.setWindowFlag(Qt.WindowType.FramelessWindowHint, True)
    titlebar_hint = getattr(Qt.WindowType, "NoTitleBarBackgroundHint", None)
    if titlebar_hint is not None and not (widget.windowFlags() & titlebar_hint):
        widget.setWindowFlag(titlebar_hint, True)
    widget.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)


class WindowControls(QWidget):
    def __init__(self, window: QWidget, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.window = window
        self.setObjectName("windowControls")
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8 if is_macos() else 2)

        if is_macos():
            buttons = [
                self._button("", "trafficCloseButton", "Close", self.window.close),
                self._button("", "trafficMinimizeButton", "Minimize", self.window.showMinimized),
                self._button("", "trafficZoomButton", "Zoom", self._toggle_maximized),
            ]
        else:
            buttons = [
                self._button("-", "windowMinimizeButton", "Minimize", self.window.showMinimized),
                self._button("□", "windowMaximizeButton", "Maximize", self._toggle_maximized),
                self._button("x", "windowCloseButton", "Close", self.window.close),
            ]
        for button in buttons:
            layout.addWidget(button)
        self.setLayout(layout)

    def _button(self, text: str, object_name: str, tooltip: str, slot) -> QToolButton:
        button = QToolButton()
        button.setText(text)
        button.setObjectName(object_name)
        button.setToolTip(tooltip)
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        button.clicked.connect(slot)
        return button

    def _toggle_maximized(self) -> None:
        if self.window.isMaximized():
            self.window.showNormal()
        else:
            self.window.showMaximized()


class FramelessTitleBar(QFrame):
    def __init__(
        self,
        window: QWidget,
        title: str = "",
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.window = window
        self._drag_offset = None
        self.setObjectName("framelessTitleBar")
        self.setFixedHeight(34)

        layout = QHBoxLayout()
        layout.setContentsMargins(12, 0, 12, 0)
        layout.setSpacing(8)
        self.controls = WindowControls(window, self)
        self.title_label = QLabel(title)
        self.title_label.setObjectName("framelessTitleLabel")
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        if is_macos():
            layout.addWidget(self.controls)
            layout.addStretch()
            layout.addWidget(self.title_label)
            layout.addStretch()
            layout.addSpacing(self.controls.sizeHint().width())
        else:
            layout.addWidget(self.title_label)
            layout.addStretch()
            layout.addWidget(self.controls)
        self.setLayout(layout)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_offset = event.globalPosition().toPoint() - self.window.frameGeometry().topLeft()
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self._drag_offset is not None and event.buttons() & Qt.MouseButton.LeftButton:
            self.window.move(event.globalPosition().toPoint() - self._drag_offset)
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        self._drag_offset = None
        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.controls._toggle_maximized()
            event.accept()
            return
        super().mouseDoubleClickEvent(event)
