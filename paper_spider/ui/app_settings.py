# Copyright 2026 Isaacveg
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#     http://www.apache.org/licenses/LICENSE-2.0

"""Shared access to the desktop app's persisted settings."""

from __future__ import annotations

from PyQt6.QtCore import QSettings

ORGANIZATION = "PaperSpider"
APPLICATION = "PaperSpider"
DEFAULT_REQUEST_DELAY_MS = 100


def app_settings() -> QSettings:
    return QSettings(ORGANIZATION, APPLICATION)


def request_delay_ms(settings: QSettings) -> int:
    try:
        return int(settings.value("request_delay_ms", DEFAULT_REQUEST_DELAY_MS))
    except (TypeError, ValueError):
        return DEFAULT_REQUEST_DELAY_MS


def base_dir(settings: QSettings) -> str:
    value = settings.value("base_dir", "")
    return str(value).strip() if value is not None else ""
