# Copyright 2026 Isaacveg
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#     http://www.apache.org/licenses/LICENSE-2.0

from __future__ import annotations

import re
from typing import List


def split_author_names(text: str) -> List[str]:
    normalized = re.sub(r"\s+", " ", text or "").strip()
    if not normalized:
        return []
    normalized = re.sub(r"^(authors?|by)\s*:\s*", "", normalized, flags=re.IGNORECASE)
    if ";" in normalized:
        return _clean_parts(normalized.split(";"))
    if re.search(r"\s+and\s+", normalized, flags=re.IGNORECASE):
        return _clean_parts(re.split(r"\s+and\s+", normalized, flags=re.IGNORECASE))
    return _clean_parts(normalized.split(","))


def _clean_parts(parts) -> List[str]:
    return [part.strip(" ,") for part in parts if part and part.strip(" ,")]
