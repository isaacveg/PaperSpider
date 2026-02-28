# Copyright 2026 Isaacveg
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#     http://www.apache.org/licenses/LICENSE-2.0

from __future__ import annotations

import csv
import io
import json
from typing import Any, Dict, Iterable, List


def build_export_text(
    rows: Iterable[Dict[str, Any]],
    export_format: str,
    include_title: bool,
    include_authors: bool,
    include_abstract: bool,
) -> str:
    normalized_rows = [_normalize_row(row) for row in rows]
    if export_format == "txt":
        titles = [row["title"] for row in normalized_rows if row["title"]]
        return "\n".join(titles)

    fields = []
    if include_title:
        fields.append("title")
    if include_authors:
        fields.append("authors")
    if include_abstract:
        fields.append("abstract")
    if not fields:
        raise ValueError("Select at least one field.")

    if export_format == "json":
        output = []
        for row in normalized_rows:
            item: Dict[str, Any] = {}
            if "title" in fields:
                item["title"] = row["title"]
            if "authors" in fields:
                item["authors"] = row["authors_list"]
            if "abstract" in fields:
                item["abstract"] = row["abstract"]
            output.append(item)
        return json.dumps(output, ensure_ascii=False, indent=2)

    if export_format == "csv":
        buffer = io.StringIO()
        writer = csv.DictWriter(buffer, fieldnames=fields)
        writer.writeheader()
        for row in normalized_rows:
            item: Dict[str, str] = {}
            if "title" in fields:
                item["title"] = row["title"]
            if "authors" in fields:
                item["authors"] = "; ".join(row["authors_list"])
            if "abstract" in fields:
                item["abstract"] = row["abstract"]
            writer.writerow(item)
        return buffer.getvalue().strip()

    raise ValueError(f"Unsupported export format: {export_format}")


def _normalize_row(row: Dict[str, Any]) -> Dict[str, Any]:
    title = _as_text(row.get("title"))
    abstract = _as_text(row.get("abstract"))
    authors_list = _parse_authors(row.get("authors"))
    return {
        "title": title,
        "abstract": abstract,
        "authors_list": authors_list,
    }


def _as_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    return str(value)


def _parse_authors(raw: Any) -> List[str]:
    if raw is None:
        return []
    if isinstance(raw, list):
        return [str(item).strip() for item in raw if str(item).strip()]
    if isinstance(raw, str):
        text = raw.strip()
        if not text:
            return []
        try:
            parsed = json.loads(text)
            if isinstance(parsed, list):
                return [str(item).strip() for item in parsed if str(item).strip()]
        except ValueError:
            pass
        parts = [part.strip() for part in text.replace(";", ",").split(",")]
        return [part for part in parts if part]
    return [str(raw).strip()] if str(raw).strip() else []
