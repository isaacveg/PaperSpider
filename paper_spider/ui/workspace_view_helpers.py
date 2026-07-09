# Copyright 2026 Isaacveg
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#     http://www.apache.org/licenses/LICENSE-2.0

from __future__ import annotations

from dataclasses import dataclass
from typing import AbstractSet, Mapping, Sequence


@dataclass(frozen=True)
class WorkspaceSummary:
    total: int
    abstracts: int
    pdfs: int
    bibs: int


def paper_id_for_row(row: Mapping[str, object]) -> str:
    return str(row.get("paper_id") or "")


def summarize_rows(rows: Sequence[Mapping[str, object]]) -> WorkspaceSummary:
    return WorkspaceSummary(
        total=len(rows),
        abstracts=sum(1 for row in rows if bool(row.get("abstract_status"))),
        pdfs=sum(1 for row in rows if bool(row.get("has_pdf"))),
        bibs=sum(1 for row in rows if bool(row.get("has_bib"))),
    )


def reconcile_selected_ids(
    rows: Sequence[Mapping[str, object]],
    selected_ids: AbstractSet[str],
) -> set[str]:
    visible_ids = {paper_id_for_row(row) for row in rows}
    return {paper_id for paper_id in selected_ids if paper_id in visible_ids}
