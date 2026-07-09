# Copyright 2026 Isaacveg
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#     http://www.apache.org/licenses/LICENSE-2.0

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QWidget


def apply_window_chrome(widget: QWidget) -> None:
    titlebar_hint = getattr(Qt.WindowType, "NoTitleBarBackgroundHint", None)
    if titlebar_hint is not None and not (widget.windowFlags() & titlebar_hint):
        widget.setWindowFlag(titlebar_hint, True)
    if hasattr(widget, "setUnifiedTitleAndToolBarOnMac"):
        widget.setUnifiedTitleAndToolBarOnMac(True)
    widget.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
