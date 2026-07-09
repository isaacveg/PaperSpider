# Copyright 2026 Isaacveg
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#     http://www.apache.org/licenses/LICENSE-2.0

from __future__ import annotations

import os
import re


def safe_filename(title: str, fallback: str, *, max_length: int = 120) -> str:
    name = title.strip().replace(" ", "_").replace("$", "")
    name = re.sub(r"[\\/:*?\"<>|]", "", name)
    name = re.sub(r"[^A-Za-z0-9._-]+", "_", name)
    name = re.sub(r"_+", "_", name).strip("._-")
    if not name:
        name = fallback
    if len(name) > max_length:
        name = name[:max_length].rstrip("._-")
    return name or fallback


def unique_artifact_path(directory: str, base_name: str, extension: str, fallback_suffix: str) -> str:
    path = os.path.join(directory, f"{base_name}.{extension}")
    if not os.path.exists(path):
        return path
    return os.path.join(directory, f"{base_name}_{fallback_suffix}.{extension}")


def write_binary_artifact(path: str, data: bytes) -> None:
    with open(path, "wb") as f:
        f.write(data)


def write_text_artifact(path: str, text: str) -> None:
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
