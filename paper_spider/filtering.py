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


def filter_paper_rows(
    rows: List[dict],
    configs: List[FilterConfig],
    min_should_match: int,
) -> List[dict]:
    if not configs:
        return list(rows)

    must = [cfg for cfg in configs if cfg.role == "must"]
    should = [cfg for cfg in configs if cfg.role == "should"]
    must_not = [cfg for cfg in configs if cfg.role == "must not"]

    filtered: List[dict] = []
    for row in rows:
        if any(_matches(row, cfg) for cfg in must_not):
            continue
        if must and not all(_matches(row, cfg) for cfg in must):
            continue
        if should and min_should_match > 0:
            match_count = sum(1 for cfg in should if _matches(row, cfg))
            if match_count < min_should_match:
                continue
        filtered.append(row)
    return filtered


def _matches(row: dict, cfg: FilterConfig) -> bool:
    value = cfg.value.lower()
    haystack = _field_text(row, cfg.field)
    contains = value in haystack
    if cfg.mode == "contains":
        return contains
    return not contains


def _field_text(row: dict, field: str) -> str:
    title = (row.get("title") or "").lower()
    category = (row.get("category_text") or "").lower()
    abstract = (row.get("abstract") or "").lower()
    authors = (row.get("authors_text") or "").lower()
    keywords = (row.get("keywords_text") or "").lower()

    if field == "title":
        return title
    if field == "authors":
        return authors
    if field == "category":
        return category
    if field == "abstract":
        return abstract
    if field == "keywords":
        return keywords
    return " ".join([title, category, authors, abstract, keywords])
