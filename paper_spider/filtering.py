# Copyright 2026 Isaacveg
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#     http://www.apache.org/licenses/LICENSE-2.0

from __future__ import annotations

from dataclasses import dataclass
from typing import List


@dataclass
class FilterConfig:
    enabled: bool
    field: str
    mode: str
    role: str
    value: str


_FIELD_KEYS = {
    "title": "title",
    "authors": "authors_text",
    "category": "category_text",
    "abstract": "abstract",
    "keywords": "keywords_text",
}


def filter_paper_rows(
    rows: List[dict],
    configs: List[FilterConfig],
    min_should_match: int,
) -> List[dict]:
    if not configs:
        return list(rows)

    must: List[tuple[FilterConfig, str]] = []
    should: List[tuple[FilterConfig, str]] = []
    must_not: List[tuple[FilterConfig, str]] = []
    for cfg in configs:
        item = (cfg, cfg.value.lower())
        role = _role_key(cfg)
        if role == "must":
            must.append(item)
        elif role == "should":
            should.append(item)
        elif role == "must not":
            must_not.append(item)

    filtered: List[dict] = []
    for row in rows:
        if any(_matches(row, cfg, value) for cfg, value in must_not):
            continue
        if must and not all(_matches(row, cfg, value) for cfg, value in must):
            continue
        if should and min_should_match > 0:
            match_count = sum(
                1 for cfg, value in should if _matches(row, cfg, value)
            )
            if match_count < min_should_match:
                continue
        filtered.append(row)
    return filtered


def _matches(row: dict, cfg: FilterConfig, value: str) -> bool:
    contains = value in _field_text(row, cfg.field)
    if cfg.mode == "contains":
        return contains
    return not contains


def _role_key(cfg: FilterConfig) -> str:
    return cfg.role.replace("_", " ").lower()


def _field_text(row: dict, field: str) -> str:
    key = _FIELD_KEYS.get(field)
    if key is not None:
        return str(row.get(key) or "").lower()
    return " ".join(
        str(row.get(key) or "")
        for key in (
            "title",
            "category_text",
            "authors_text",
            "abstract",
            "keywords_text",
        )
    ).lower()
