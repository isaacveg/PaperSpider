# Copyright 2026 Isaacveg
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#     http://www.apache.org/licenses/LICENSE-2.0

"""Local library operations used by the PaperSpider command-line interface."""

from __future__ import annotations

import os
import re
from typing import Any, Callable, Dict, List, Mapping, Optional, Sequence, Tuple

from .artifacts import safe_filename, write_text_artifact
from .conferences import available_conferences
from .conferences.base import ConferenceBase
from .datasets import YEAR_MAX, YEAR_MIN, scan_datasets
from .export_utils import build_export_text
from .filtering import matches_terms, query_terms, search_text
from .storage import PaperStorage
from .workspace_service import WorkspaceService, paper_from_row

MAX_BATCH_SIZE = 200
DEFAULT_SEARCH_LIMIT = 20
MAX_SEARCH_LIMIT = 200
DEFAULT_REQUEST_DELAY_MS = 100
MAX_REQUEST_DELAY_MS = 10000
DEFAULT_BASE_DIR_NAME = "PaperSpider"
EXPORT_FORMATS = ("csv", "json", "txt", "bibtex")

_CONF_SLUG_RE = re.compile(r"[a-z0-9][a-z0-9_-]*")

ConferenceProvider = Callable[[], Sequence[ConferenceBase]]


class OperationError(Exception):
    """A failure that the CLI can report without a traceback."""


def resolve_base_dir(environ: Optional[Mapping[str, str]] = None) -> str:
    """Resolve the storage folder from the environment, app settings, or home directory."""

    env = os.environ if environ is None else environ
    explicit = (env.get("PAPERSPIDER_BASE_DIR") or "").strip()
    if explicit:
        return os.path.abspath(os.path.expanduser(explicit))
    configured = _settings_base_dir()
    if configured:
        return os.path.abspath(os.path.expanduser(configured))
    return os.path.join(os.path.expanduser("~"), DEFAULT_BASE_DIR_NAME)


def _settings_base_dir() -> Optional[str]:
    try:
        from PyQt6.QtCore import QSettings
    except ImportError:
        return None
    value = QSettings("PaperSpider", "PaperSpider").value("base_dir", "")
    text = str(value).strip() if value is not None else ""
    return text or None


def resolve_request_delay_ms(
    environ: Optional[Mapping[str, str]] = None,
) -> int:
    """Read the request delay from the environment, defaulting to 100 ms."""

    env = os.environ if environ is None else environ
    raw = (env.get("PAPERSPIDER_REQUEST_DELAY_MS") or "").strip()
    if not raw:
        return DEFAULT_REQUEST_DELAY_MS
    try:
        value = int(raw)
    except ValueError:
        return DEFAULT_REQUEST_DELAY_MS
    return max(0, min(MAX_REQUEST_DELAY_MS, value))


def _validate_integer(
    name: str,
    value: Any,
    minimum: int,
    maximum: int,
) -> int:
    if isinstance(value, bool):
        raise OperationError(f"{name} must be an integer.")
    if isinstance(value, str) and value.strip().isdigit():
        value = int(value.strip())
    if not isinstance(value, int):
        raise OperationError(f"{name} must be an integer.")
    if not minimum <= value <= maximum:
        raise OperationError(
            f"{name} must be between {minimum} and {maximum}."
        )
    return value


def validate_conf_slug(value: Any) -> str:
    """Normalize and validate a conference slug."""

    if not isinstance(value, str) or not value.strip():
        raise OperationError(
            "conference must be a slug such as 'iclr' or 'usenix_security'."
        )
    slug = value.strip().lower()
    if not _CONF_SLUG_RE.fullmatch(slug):
        raise OperationError(
            "conference must be a slug such as 'iclr' or 'usenix_security'."
        )
    return slug


def validate_year(value: Any) -> int:
    """Validate a conference year."""

    return _validate_integer("year", value, YEAR_MIN, YEAR_MAX)


def validate_limit(value: Any) -> int:
    """Validate a search result limit."""

    return _validate_integer("limit", value, 1, MAX_SEARCH_LIMIT)


def validate_offset(value: Any) -> int:
    """Validate a search result offset."""

    return _validate_integer("offset", value, 0, 1_000_000_000)


def validate_delay_ms(value: Any) -> int:
    """Validate the delay between web requests."""

    return _validate_integer("delay-ms", value, 0, MAX_REQUEST_DELAY_MS)


def validate_paper_ids(value: Any) -> List[str]:
    """Validate and deduplicate a batch of paper ids."""

    if value is None:
        raise OperationError("at least one paper id is required.")
    if isinstance(value, str):
        value = [value]
    if not isinstance(value, list) or not value:
        raise OperationError("at least one paper id is required.")
    if len(value) > MAX_BATCH_SIZE:
        raise OperationError(
            f"at most {MAX_BATCH_SIZE} paper ids are accepted per call."
        )
    ids: List[str] = []
    seen = set()
    for item in value:
        if not isinstance(item, str) or not item.strip():
            raise OperationError("paper ids must be non-empty strings.")
        paper_id = item.strip()
        if paper_id in seen:
            continue
        seen.add(paper_id)
        ids.append(paper_id)
    return ids


def validate_export_format(value: Any) -> str:
    """Validate an export format name."""

    if not isinstance(value, str):
        raise OperationError(
            "format must be one of: " + ", ".join(EXPORT_FORMATS) + "."
        )
    export_format = value.strip().lower()
    if export_format not in EXPORT_FORMATS:
        raise OperationError(
            "format must be one of: " + ", ".join(EXPORT_FORMATS) + "."
        )
    return export_format


def _optional_text(value: Any, name: str) -> Optional[str]:
    if value is None:
        return None
    if not isinstance(value, str):
        raise OperationError(f"{name} must be a string.")
    text = value.strip()
    return text or None


def _row_matches_terms(row: Mapping[str, Any], terms: Sequence[str]) -> bool:
    return not terms or matches_terms(search_text(row), terms)


def _apply_file_flags(row: Dict[str, Any]) -> Dict[str, Any]:
    pdf_path = row.get("pdf_path")
    row["has_pdf"] = (
        bool(row.get("pdf_status"))
        and bool(pdf_path)
        and os.path.exists(pdf_path)
    )
    bib_path = row.get("bib_path")
    row["has_bib"] = bool(bib_path) and os.path.exists(bib_path)
    return row


def _paper_summary(row: Mapping[str, Any], include_abstract: bool) -> Dict[str, Any]:
    item: Dict[str, Any] = {
        "paper_id": row.get("paper_id"),
        "title": row.get("title") or "",
        "conf": row.get("conf"),
        "year": row.get("year"),
        "category": row.get("category_text"),
        "authors": row.get("authors_list") or [],
        "keywords": row.get("keywords_list") or [],
        "has_abstract": bool(row.get("abstract")),
        "has_pdf": bool(row.get("has_pdf")),
        "has_bib": bool(row.get("has_bib")),
        "detail_url": row.get("detail_url"),
        "pdf_url": row.get("pdf_url"),
    }
    if include_abstract:
        item["abstract"] = row.get("abstract")
    return item


def _full_paper(row: Mapping[str, Any]) -> Dict[str, Any]:
    return {
        "paper_id": row.get("paper_id"),
        "title": row.get("title") or "",
        "conf": row.get("conf"),
        "year": row.get("year"),
        "track": row.get("track"),
        "paper_type": row.get("paper_type"),
        "category": row.get("category_text"),
        "authors": row.get("authors_list") or [],
        "keywords": row.get("keywords_list") or [],
        "abstract": row.get("abstract"),
        "detail_url": row.get("detail_url"),
        "pdf_url": row.get("pdf_url"),
        "bibtex_url": row.get("bibtex_url"),
        "bibtex": row.get("bibtex"),
        "pdf_path": row.get("pdf_path"),
        "bib_path": row.get("bib_path"),
        "has_pdf": bool(row.get("has_pdf")),
        "has_bib": bool(row.get("has_bib")),
    }


def _failure_dict(failure: Any) -> Dict[str, str]:
    return {
        "paper_id": failure.paper_id,
        "title": failure.title,
        "message": failure.message,
    }


class PaperSpiderOperations:
    """Implement PaperSpider library operations for the CLI."""

    def __init__(
        self,
        base_dir: Optional[str] = None,
        conference_provider: Optional[ConferenceProvider] = None,
        service: Optional[WorkspaceService] = None,
        request_delay_ms: Optional[int] = None,
    ) -> None:
        resolved = base_dir or resolve_base_dir()
        self.base_dir = os.path.abspath(os.path.expanduser(resolved))
        self._conference_provider = conference_provider or available_conferences
        self._service = service or WorkspaceService()
        if request_delay_ms is None:
            self.request_delay_ms = resolve_request_delay_ms()
        else:
            self.request_delay_ms = validate_delay_ms(request_delay_ms)
        self._conferences: Optional[Dict[str, ConferenceBase]] = None

    def conference_map(self) -> Dict[str, ConferenceBase]:
        if self._conferences is None:
            delay_seconds = self.request_delay_ms / 1000.0
            conferences: Dict[str, ConferenceBase] = {}
            for conference in self._conference_provider():
                conference.request_delay = delay_seconds
                conferences[conference.slug] = conference
            self._conferences = conferences
        return self._conferences

    def list_conferences(self, query: Optional[str] = None) -> Dict[str, Any]:
        needle = _optional_text(query, "query")
        conferences = [
            {"slug": conference.slug, "name": conference.name}
            for conference in self.conference_map().values()
        ]
        if needle:
            folded = needle.casefold()
            conferences = [
                item
                for item in conferences
                if folded in item["name"].casefold() or folded in item["slug"]
            ]
        return {
            "base_dir": self.base_dir,
            "count": len(conferences),
            "conferences": conferences,
        }

    def list_datasets(self) -> Dict[str, Any]:
        conferences = self.conference_map()
        datasets = []
        for entry in scan_datasets(self.base_dir):
            conference = conferences.get(entry.conf_slug)
            datasets.append(
                {
                    "conf": entry.conf_slug,
                    "name": (
                        conference.name if conference else entry.conf_slug
                    ),
                    "year": entry.year,
                    "papers": entry.paper_count,
                    "path": os.path.relpath(entry.path, self.base_dir),
                    "supported": conference is not None,
                }
            )
        return {
            "base_dir": self.base_dir,
            "count": len(datasets),
            "datasets": datasets,
        }

    def add_conference(self, conf: str, year: int) -> Dict[str, Any]:
        conf_slug = validate_conf_slug(conf)
        year_value = validate_year(year)
        conference = self.conference_map().get(conf_slug)
        if conference is None:
            raise OperationError(self._unknown_conference_message(conf_slug))
        storage = PaperStorage(self.base_dir, conf_slug, year_value)
        try:
            fetched = self._service.fetch_list(conference, storage)
        except Exception as exc:
            raise OperationError(
                f"failed to fetch {conference.name} {year_value}: {exc}"
            ) from exc
        return {
            "conf": conf_slug,
            "name": conference.name,
            "year": year_value,
            "fetched": fetched,
            "total": storage.count_papers(),
            "path": os.path.relpath(storage.paths.root_dir, self.base_dir),
        }

    def search_papers(
        self,
        conf: Optional[str] = None,
        year: Optional[int] = None,
        query: Optional[str] = None,
        title: Optional[str] = None,
        author: Optional[str] = None,
        keyword: Optional[str] = None,
        limit: int = DEFAULT_SEARCH_LIMIT,
        offset: int = 0,
        include_abstract: bool = False,
    ) -> Dict[str, Any]:
        conf_slug = validate_conf_slug(conf) if conf is not None else None
        year_value = validate_year(year) if year is not None else None
        query_text = _optional_text(query, "query")
        title_text = _optional_text(title, "title")
        author_text = _optional_text(author, "author")
        keyword_text = _optional_text(keyword, "keyword")
        limit_value = validate_limit(limit)
        offset_value = validate_offset(offset)

        if conf_slug is not None and year_value is not None:
            _, storage = self._local_dataset(conf_slug, year_value)
            datasets = [(conf_slug, year_value, storage)]
            errors: List[Dict[str, str]] = []
        else:
            entries = []
            for entry in scan_datasets(self.base_dir):
                if conf_slug is not None and entry.conf_slug != conf_slug:
                    continue
                if year_value is not None and entry.year != year_value:
                    continue
                entries.append(entry)
            if not entries:
                raise OperationError(
                    self._no_dataset_message(conf_slug, year_value)
                )
            datasets = []
            errors = []
            for entry in entries:
                try:
                    storage = PaperStorage(
                        self.base_dir, entry.conf_slug, entry.year
                    )
                except Exception as exc:
                    errors.append(
                        {
                            "conf": entry.conf_slug,
                            "year": str(entry.year),
                            "message": str(exc),
                        }
                    )
                    continue
                datasets.append((entry.conf_slug, entry.year, storage))

        terms = query_terms(query_text) if query_text else []
        matches: List[dict] = []
        for dataset_conf, dataset_year, storage in datasets:
            try:
                rows = storage.list_papers(
                    title_query=title_text,
                    author_query=author_text,
                    keyword_query=keyword_text,
                )
            except Exception as exc:
                if len(datasets) == 1:
                    raise OperationError(
                        f"failed to search {dataset_conf} {dataset_year}: {exc}"
                    ) from exc
                errors.append(
                    {
                        "conf": dataset_conf,
                        "year": str(dataset_year),
                        "message": str(exc),
                    }
                )
                continue
            matches.extend(row for row in rows if _row_matches_terms(row, terms))

        matches.sort(
            key=lambda row: (
                str(row.get("conf") or ""),
                -int(row.get("year") or 0),
                str(row.get("title") or "").casefold(),
            )
        )
        total = len(matches)
        page = [
            _apply_file_flags(row)
            for row in matches[offset_value : offset_value + limit_value]
        ]
        result: Dict[str, Any] = {
            "total": total,
            "count": len(page),
            "offset": offset_value,
            "limit": limit_value,
            "papers": [_paper_summary(row, include_abstract) for row in page],
        }
        if errors:
            result["errors"] = errors
        return result

    def get_paper(
        self,
        conf: str,
        year: int,
        paper_id: str,
        fetch_details: bool = False,
    ) -> Dict[str, Any]:
        conf_slug = validate_conf_slug(conf)
        year_value = validate_year(year)
        paper_id_value = _optional_text(paper_id, "paper_id")
        if paper_id_value is None:
            raise OperationError("paper_id must not be empty.")

        conference, storage = self._local_dataset(conf_slug, year_value)
        row = storage.get_paper(paper_id_value)
        if row is None:
            raise OperationError(
                f"paper '{paper_id_value}' not found in {conf_slug} {year_value}. "
                "Use search to find valid paper ids."
            )
        if fetch_details:
            if conference is None:
                raise OperationError(
                    f"conference '{conf_slug}' is not supported by this "
                    "PaperSpider version, so details cannot be fetched."
                )
            paper = paper_from_row(row, conf_slug, year_value)
            try:
                updated = conference.fetch_details(paper)
            except Exception as exc:
                raise OperationError(
                    f"failed to fetch details for '{paper_id_value}' from "
                    f"{conference.name} {year_value}: {exc}"
                ) from exc
            storage.update_details(
                updated.paper_id,
                updated.abstract,
                updated.authors,
                updated.keywords,
                updated.pdf_url,
                updated.bibtex_url,
                updated.bibtex,
            )
            row = storage.get_paper(paper_id_value) or row
        row = _apply_file_flags(row)
        return {"paper": _full_paper(row)}

    def download_abstracts(
        self,
        conf: str,
        year: int,
        paper_ids: Sequence[str],
    ) -> Dict[str, Any]:
        conference, storage, rows = self._network_selection(
            conf, year, paper_ids
        )
        try:
            result = self._service.download_abstracts(
                conference,
                storage,
                rows,
                cancelled=lambda: False,
            )
        except Exception as exc:
            raise OperationError(f"abstract download failed: {exc}") from exc
        papers = [
            {
                "paper_id": row.get("paper_id"),
                "title": row.get("title") or "",
                "abstract": row.get("abstract"),
            }
            for row in result.updated_rows
        ]
        return {
            "conf": conference.slug,
            "year": storage.year,
            "requested": len(rows),
            "succeeded": result.succeeded,
            "skipped": result.skipped,
            "failures": [_failure_dict(failure) for failure in result.failures],
            "papers": papers,
        }

    def download_pdfs(
        self,
        conf: str,
        year: int,
        paper_ids: Sequence[str],
    ) -> Dict[str, Any]:
        conference, storage, rows = self._network_selection(
            conf, year, paper_ids
        )
        try:
            result = self._service.download_pdfs(
                conference,
                storage,
                rows,
                cancelled=lambda: False,
            )
        except Exception as exc:
            raise OperationError(f"PDF download failed: {exc}") from exc
        files = [
            {
                "paper_id": row.get("paper_id"),
                "title": row.get("title") or "",
                "path": row.get("pdf_path"),
            }
            for row in result.updated_rows
            if row.get("pdf_path")
        ]
        return {
            "conf": conference.slug,
            "year": storage.year,
            "requested": len(rows),
            "succeeded": result.succeeded,
            "skipped": result.skipped,
            "failures": [_failure_dict(failure) for failure in result.failures],
            "files": files,
        }

    def download_bibtex(
        self,
        conf: str,
        year: int,
        paper_ids: Sequence[str],
    ) -> Dict[str, Any]:
        conference, storage, rows = self._network_selection(
            conf, year, paper_ids
        )
        try:
            self._service.export_bibtex(conference, storage, rows)
        except Exception as exc:
            raise OperationError(f"BibTeX download failed: {exc}") from exc
        files = []
        failures = []
        refreshed_rows = storage.get_papers(row["paper_id"] for row in rows)
        for row in rows:
            refreshed = refreshed_rows.get(row["paper_id"], row)
            bib_path = refreshed.get("bib_path")
            if bib_path and os.path.exists(bib_path):
                files.append(
                    {
                        "paper_id": refreshed.get("paper_id"),
                        "title": refreshed.get("title") or "",
                        "path": bib_path,
                        "bibtex": refreshed.get("bibtex"),
                    }
                )
            else:
                failures.append(
                    {
                        "paper_id": row.get("paper_id"),
                        "title": row.get("title") or "",
                        "message": "BibTeX not available",
                    }
                )
        return {
            "conf": conference.slug,
            "year": storage.year,
            "requested": len(rows),
            "exported": len(files),
            "failures": failures,
            "files": files,
        }

    def export_papers(
        self,
        conf: str,
        year: int,
        export_format: str = "csv",
        paper_ids: Optional[Sequence[str]] = None,
        include_title: bool = True,
        include_authors: bool = True,
        include_abstract: bool = False,
        save: bool = False,
        filename: Optional[str] = None,
    ) -> Dict[str, Any]:
        conf_slug = validate_conf_slug(conf)
        year_value = validate_year(year)
        format_value = validate_export_format(export_format)
        ids = validate_paper_ids(paper_ids) if paper_ids is not None else None
        filename_value = _optional_text(filename, "filename")

        conference, storage = self._local_dataset(conf_slug, year_value)
        rows = (
            self._rows_for_ids(storage, ids)
            if ids is not None
            else storage.list_papers()
        )
        if not rows:
            raise OperationError(
                f"dataset {conf_slug} {year_value} has no papers to export."
            )

        failures: List[Dict[str, str]] = []
        if format_value == "bibtex":
            content, failures = self._bibtex_text(
                conference, storage, rows, conf_slug, year_value
            )
            count = len(rows) - len(failures)
            extension = "bib"
        else:
            try:
                content = build_export_text(
                    rows=rows,
                    export_format=format_value,
                    include_title=bool(include_title),
                    include_authors=bool(include_authors),
                    include_abstract=bool(include_abstract),
                )
            except ValueError as exc:
                raise OperationError(str(exc)) from exc
            count = len(rows)
            extension = format_value

        result: Dict[str, Any] = {
            "conf": conf_slug,
            "year": year_value,
            "format": format_value,
            "count": count,
            "content": content,
        }
        if failures:
            result["failures"] = failures
        if save:
            result["path"] = self._save_export(
                storage,
                content,
                filename_value,
                extension,
                conf_slug,
                year_value,
            )
        return result

    def _network_selection(
        self,
        conf: str,
        year: int,
        paper_ids: Sequence[str],
    ) -> Tuple[ConferenceBase, PaperStorage, List[dict]]:
        conf_slug = validate_conf_slug(conf)
        year_value = validate_year(year)
        ids = validate_paper_ids(paper_ids)
        conference = self.conference_map().get(conf_slug)
        if conference is None:
            raise OperationError(self._unknown_conference_message(conf_slug))
        _, storage = self._local_dataset(conf_slug, year_value)
        rows = self._rows_for_ids(storage, ids)
        return conference, storage, rows

    def _local_dataset(
        self, conf_slug: str, year: int
    ) -> Tuple[Optional[ConferenceBase], PaperStorage]:
        root_dir = os.path.join(self.base_dir, conf_slug, str(year))
        db_path = os.path.join(root_dir, "papers.sqlite")
        if not os.path.exists(db_path):
            hint = ""
            if conf_slug in self.conference_map():
                hint = (
                    f" Run add {conf_slug} {year} to fetch this dataset."
                )
            raise OperationError(
                f"no local dataset for '{conf_slug}' {year} under "
                f"{self.base_dir}.{hint}"
            )
        return self.conference_map().get(conf_slug), PaperStorage(
            self.base_dir, conf_slug, year
        )

    def _rows_for_ids(
        self, storage: PaperStorage, paper_ids: Sequence[str]
    ) -> List[dict]:
        rows_by_id = storage.get_papers(paper_ids)
        missing = [paper_id for paper_id in paper_ids if paper_id not in rows_by_id]
        if missing:
            raise OperationError(
                f"paper ids not found in {storage.conf_slug} {storage.year}: "
                f"{', '.join(missing)}. Use search to find valid ids."
            )
        return [_apply_file_flags(rows_by_id[paper_id]) for paper_id in paper_ids]

    def _bibtex_text(
        self,
        conference: Optional[ConferenceBase],
        storage: PaperStorage,
        rows: Sequence[dict],
        conf_slug: str,
        year: int,
    ) -> Tuple[str, List[Dict[str, str]]]:
        chunks: List[str] = []
        failures: List[Dict[str, str]] = []
        for row in rows:
            bibtex = row.get("bibtex")
            message = "BibTeX not available"
            if not bibtex:
                if conference is None:
                    message = (
                        f"BibTeX not cached and conference '{conf_slug}' is not "
                        "supported by this PaperSpider version"
                    )
                else:
                    paper = paper_from_row(row, conf_slug, year)
                    try:
                        bibtex = conference.fetch_bibtex(paper)
                    except Exception as exc:
                        message = f"BibTeX fetch failed: {exc}"
            if bibtex and bibtex.strip():
                entry = bibtex.strip()
                storage.update_details(
                    row["paper_id"], None, [], [], None, None, entry
                )
                chunks.append(entry)
            else:
                failures.append(
                    {
                        "paper_id": row.get("paper_id"),
                        "title": row.get("title") or "",
                        "message": message,
                    }
                )
        return "\n\n".join(chunks), failures

    def _save_export(
        self,
        storage: PaperStorage,
        content: str,
        filename: Optional[str],
        extension: str,
        conf_slug: str,
        year: int,
    ) -> str:
        exports_dir = os.path.join(storage.paths.root_dir, "exports")
        os.makedirs(exports_dir, exist_ok=True)
        fallback = f"paperspider_{conf_slug}_{year}"
        base_name = safe_filename(filename or fallback, fallback)
        suffix = f".{extension}"
        if base_name.lower().endswith(suffix):
            base_name = base_name[: -len(suffix)]
        base_name = base_name.rstrip("._-") or fallback
        path = os.path.join(exports_dir, f"{base_name}{suffix}")
        index = 1
        while os.path.exists(path):
            path = os.path.join(exports_dir, f"{base_name}_{index}{suffix}")
            index += 1
        write_text_artifact(path, content)
        return path

    def _unknown_conference_message(self, conf_slug: str) -> str:
        supported = ", ".join(sorted(self.conference_map()))
        return (
            f"conference '{conf_slug}' is not supported by this PaperSpider "
            f"version. Supported conferences: {supported}. "
            "Run conferences for names."
        )

    def _no_dataset_message(
        self, conf_slug: Optional[str], year: Optional[int]
    ) -> str:
        if conf_slug is not None and year is not None:
            target = f"'{conf_slug}' {year}"
        elif conf_slug is not None:
            target = f"conference '{conf_slug}'"
        elif year is not None:
            target = f"year {year}"
        else:
            target = "any conference"
        return (
            f"no local dataset found for {target} under {self.base_dir}. "
            "Run datasets to see available datasets or add to fetch one."
        )