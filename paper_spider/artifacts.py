# Copyright 2026 Isaacveg
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#     http://www.apache.org/licenses/LICENSE-2.0

from __future__ import annotations

import contextlib
import os
import re
import tempfile


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
    suffix = safe_filename(fallback_suffix, "file")
    path = os.path.join(directory, f"{base_name}_{suffix}.{extension}")
    counter = 2
    while os.path.exists(path):
        path = os.path.join(directory, f"{base_name}_{suffix}_{counter}.{extension}")
        counter += 1
    return path


def write_binary_artifact(path: str, data: bytes) -> None:
    _atomic_write(path, data)


def write_text_artifact(path: str, text: str) -> None:
    _atomic_write(path, text.encode("utf-8"))


def _atomic_write(path: str, data: bytes) -> None:
    directory = os.path.dirname(path) or "."
    fd, tmp_path = tempfile.mkstemp(dir=directory, prefix=".tmp-", suffix=".part")
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(data)
        os.replace(tmp_path, path)
    except BaseException:
        with contextlib.suppress(OSError):
            os.unlink(tmp_path)
        raise
