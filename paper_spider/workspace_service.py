# Copyright 2026 Isaacveg
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#     http://www.apache.org/licenses/LICENSE-2.0

from __future__ import annotations

from contextlib import nullcontext
from dataclasses import dataclass, field
from typing import Callable, List, Optional

from .artifacts import (
    safe_filename,
    unique_artifact_path,
    write_binary_artifact,
    write_text_artifact,
)
from .filtering import FilterConfig, filter_paper_rows
from .models import PaperCategory, PaperMeta
from .storage import PaperStorage

LogFn = Callable[[str], None]
CancelFn = Callable[[], bool]


@dataclass
class PaperLoadResult:
    storage_key: str
    all_rows: List[dict]
    filtered_rows: List[dict]


@dataclass
class DownloadFailure:
    paper_id: str
    title: str
    message: str


@dataclass
class DownloadBatchResult:
    succeeded: int = 0
    skipped: int = 0
    failures: List[DownloadFailure] = field(default_factory=list)
    updated_rows: List[dict] = field(default_factory=list)
    cancelled: bool = False


class WorkspaceService:
    def fetch_list(self, conf, storage: PaperStorage) -> int:
        papers = conf.list_papers(storage.year)
        storage.upsert_papers(papers)
        return len(papers)

    def load_papers(
        self,
        storage: PaperStorage,
        cached_rows: Optional[List[dict]],
        configs: List[FilterConfig],
        min_should_match: int,
    ) -> PaperLoadResult:
        all_rows = cached_rows
        if all_rows is None:
            all_rows = storage.reconcile_file_states(storage.list_papers())
        filtered_rows = filter_paper_rows(all_rows, configs, min_should_match)
        return PaperLoadResult(
            storage_key=storage.paths.db_path,
            all_rows=all_rows,
            filtered_rows=filtered_rows,
        )

    def download_abstracts(
        self,
        conf,
        storage: PaperStorage,
        rows: List[dict],
        cancelled: CancelFn,
        log: Optional[LogFn] = None,
    ) -> DownloadBatchResult:
        total = len(rows)
        result = DownloadBatchResult()
        for idx, row in enumerate(rows, start=1):
            if cancelled():
                result.cancelled = True
                break
            paper_id = str(row.get("paper_id") or "")
            title = str(row.get("title") or paper_id)
            if row.get("abstract_status") and row.get("abstract"):
                result.skipped += 1
                continue
            paper = paper_from_row(row, conf.slug, storage.year)
            try:
                with _conference_cancel_context(conf, cancelled):
                    updated = conf.fetch_details(paper)
            except Exception as exc:  # pragma: no cover - exact adapter exceptions vary.
                if cancelled():
                    result.cancelled = True
                    break
                result.failures.append(DownloadFailure(paper_id, title, str(exc)))
                if log:
                    log(f"[{idx}/{total}] failed abstract: {title} ({exc})")
                continue
            storage.update_details(
                updated.paper_id,
                updated.abstract,
                updated.authors,
                updated.keywords,
                updated.pdf_url,
                updated.bibtex_url,
                updated.bibtex,
            )
            refreshed = storage.get_paper(updated.paper_id)
            if refreshed:
                result.updated_rows.append(refreshed)
            if updated.abstract and updated.abstract.strip():
                result.succeeded += 1
            else:
                result.failures.append(
                    DownloadFailure(updated.paper_id, updated.title, "Abstract not found")
                )
            if log:
                if updated.abstract and updated.abstract.strip():
                    log(f"[{idx}/{total}] abstract: {updated.title}")
                else:
                    log(f"[{idx}/{total}] missing abstract: {updated.title}")
        return result

    def download_pdfs(
        self,
        conf,
        storage: PaperStorage,
        rows: List[dict],
        cancelled: CancelFn,
        log: Optional[LogFn] = None,
    ) -> DownloadBatchResult:
        total = len(rows)
        result = DownloadBatchResult()
        for idx, row in enumerate(rows, start=1):
            if cancelled():
                result.cancelled = True
                break
            paper_id = str(row.get("paper_id") or "")
            title = str(row.get("title") or paper_id)
            if row.get("has_pdf"):
                result.skipped += 1
                continue
            paper = paper_from_row(row, conf.slug, storage.year)
            try:
                with _conference_cancel_context(conf, cancelled):
                    data = conf.fetch_pdf(paper)
                if not _looks_like_pdf(data):
                    raise RuntimeError("Downloaded file is not a PDF")
            except Exception as exc:  # pragma: no cover - exact adapter exceptions vary.
                if cancelled():
                    result.cancelled = True
                    break
                result.failures.append(DownloadFailure(paper_id, title, str(exc)))
                if log:
                    log(f"[{idx}/{total}] failed PDF: {title} ({exc})")
                continue
            base_name = safe_filename(row.get("title") or "", paper.paper_id)
            file_path = unique_artifact_path(
                storage.paths.pdf_dir,
                base_name,
                "pdf",
                paper.paper_id,
            )
            write_binary_artifact(file_path, data)
            storage.mark_pdf_downloaded(paper.paper_id, file_path)
            if paper.pdf_url:
                storage.update_details(
                    paper.paper_id,
                    paper.abstract,
                    paper.authors,
                    paper.keywords,
                    paper.pdf_url,
                    paper.bibtex_url,
                    paper.bibtex,
                )
            refreshed = storage.get_paper(paper.paper_id)
            if refreshed:
                result.updated_rows.append(refreshed)
            result.succeeded += 1
            if log:
                log(f"[{idx}/{total}] {paper.paper_id}")
        return result

    def export_bibtex(
        self,
        conf,
        storage: PaperStorage,
        rows: List[dict],
        log: Optional[LogFn] = None,
    ) -> int:
        total = len(rows)
        exported = 0
        for idx, row in enumerate(rows, start=1):
            bibtex = row.get("bibtex")
            if not bibtex:
                paper = paper_from_row(row, conf.slug, storage.year)
                try:
                    bibtex = conf.fetch_bibtex(paper)
                except RuntimeError:
                    bibtex = None
            if bibtex:
                base_name = safe_filename(row.get("title") or "", row["paper_id"])
                file_path = unique_artifact_path(
                    storage.paths.bib_dir,
                    base_name,
                    "bib",
                    row["paper_id"],
                )
                write_text_artifact(file_path, bibtex)
                storage.mark_bib_exported(row["paper_id"], bibtex, file_path)
                exported += 1
                if log:
                    log(f"[{idx}/{total}] saved bibtex: {row['paper_id']}")
            elif log:
                log(f"[{idx}/{total}] missing bibtex: {row['paper_id']}")
        return exported


def paper_from_row(row: dict, conf_slug: str, year: int) -> PaperMeta:
    category = row.get("category")
    if not isinstance(category, PaperCategory):
        category = PaperCategory.from_fields(row.get("track"), row.get("paper_type"))
    return PaperMeta(
        paper_id=row["paper_id"],
        title=row.get("title") or "",
        conf=conf_slug,
        year=year,
        category=category,
        detail_url=row.get("detail_url"),
        authors=_row_list(row, "authors"),
        abstract=row.get("abstract"),
        keywords=_row_list(row, "keywords"),
        pdf_url=row.get("pdf_url"),
        bibtex_url=row.get("bibtex_url"),
        bibtex=row.get("bibtex"),
    )


def _row_list(row: dict, field: str) -> List[str]:
    list_value = row.get(f"{field}_list")
    if isinstance(list_value, list):
        return [str(value).strip() for value in list_value if str(value).strip()]
    raw_value = row.get(field)
    if isinstance(raw_value, list):
        return [str(value).strip() for value in raw_value if str(value).strip()]
    return []


def _looks_like_pdf(data: bytes) -> bool:
    return b"%PDF" in data[:1024]


def _conference_cancel_context(conf, cancelled: CancelFn):
    cancellable = getattr(conf, "cancellable", None)
    if callable(cancellable):
        return cancellable(cancelled)
    return nullcontext()
