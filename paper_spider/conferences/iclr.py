# Copyright 2026 Isaacveg
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#     http://www.apache.org/licenses/LICENSE-2.0

from __future__ import annotations

import hashlib
import time
from typing import Any, Dict, Iterable, List, Optional
from urllib.parse import parse_qs, urljoin, urlparse

import requests

from ..models import PaperMeta
from .base import ConferenceBase


class IclrConference(ConferenceBase):
    name = "ICLR"
    slug = "iclr"

    def __init__(self) -> None:
        self.api_bases = ["https://api.openreview.net", "https://api2.openreview.net"]
        self.web_base = "https://openreview.net"
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "PaperSpider/0.1 (+https://localhost)"})
        self.request_delay = 0.1

    def list_papers(self, year: int) -> List[PaperMeta]:
        notes = self._load_submission_notes(year)
        if not notes:
            raise RuntimeError(f"Unable to load ICLR submissions for {year}")

        accepted = [note for note in notes if self._is_accepted(note, year)]
        selected = accepted if accepted else notes

        papers = []
        for note in selected:
            paper = self._note_to_paper(note, year)
            if paper:
                papers.append(paper)
        if not papers:
            raise RuntimeError(f"No ICLR papers parsed for {year}")
        return papers

    def fetch_details(self, paper: PaperMeta) -> PaperMeta:
        forum_id = self._forum_id_from_paper(paper)
        if not forum_id:
            return paper

        note = self._fetch_single_note(forum_id)
        if note:
            content = note.get("content", {})
            title = self._content_value(content, "title")
            abstract = self._content_value(content, "abstract")
            authors = self._content_list(content, "authors")
            keywords = self._content_list(content, "keywords")
            pdf = self._content_value(content, "pdf")

            if title:
                paper.title = title
            if abstract:
                paper.abstract = abstract
            if authors:
                paper.authors = authors
            if keywords:
                paper.keywords = keywords
            if pdf:
                paper.pdf_url = self._normalize_pdf_url(pdf, forum_id)
            elif not paper.pdf_url:
                paper.pdf_url = f"{self.web_base}/pdf?id={forum_id}"

        bibtex = self._fetch_citation(forum_id)
        if bibtex:
            paper.bibtex = bibtex
        return paper

    def fetch_pdf(self, paper: PaperMeta) -> bytes:
        forum_id = self._forum_id_from_paper(paper)
        if not paper.pdf_url and forum_id:
            paper.pdf_url = f"{self.web_base}/pdf?id={forum_id}"
        if not paper.pdf_url:
            paper = self.fetch_details(paper)
        if not paper.pdf_url:
            raise RuntimeError("PDF URL not found")

        resp = self._get(paper.pdf_url, binary=True)
        if resp is None:
            raise RuntimeError("Failed to download PDF")
        return resp.content

    def fetch_bibtex(self, paper: PaperMeta) -> str:
        if paper.bibtex:
            return paper.bibtex
        forum_id = self._forum_id_from_paper(paper)
        if not forum_id:
            raise RuntimeError("Bibtex forum id not found")

        bibtex = self._fetch_citation(forum_id)
        if not bibtex:
            paper = self.fetch_details(paper)
            bibtex = paper.bibtex
        if not bibtex:
            raise RuntimeError("Bibtex not found")
        return bibtex

    def _load_submission_notes(self, year: int) -> List[Dict[str, Any]]:
        candidates = [
            f"ICLR.cc/{year}/Conference/-/Blind_Submission",
            f"ICLR.cc/{year}/Conference/-/Submission",
        ]
        for invitation in candidates:
            notes = list(self._iter_notes_for_invitation(invitation))
            if notes:
                return self._dedupe_notes(notes)

        venueid_candidates = [
            f"ICLR.cc/{year}/Conference",
            f"ICLR.cc/{year}/Conference/-/Acceptance",
        ]
        for venueid in venueid_candidates:
            notes = list(self._iter_notes({"content.venueid": venueid}))
            if notes:
                return self._dedupe_notes(notes)

        venue_candidates = [
            f"ICLR {year} Conference",
            f"Submitted to ICLR {year}",
        ]
        merged: List[Dict[str, Any]] = []
        for venue in venue_candidates:
            merged.extend(self._iter_notes({"content.venue": venue}))
        if merged:
            return self._dedupe_notes(merged)
        return []

    def _iter_notes_for_invitation(self, invitation: str) -> Iterable[Dict[str, Any]]:
        yield from self._iter_notes({"invitation": invitation})

    def _iter_notes(self, base_params: Dict[str, Any]) -> Iterable[Dict[str, Any]]:
        offset = 0
        limit = 1000
        while True:
            params = {**base_params, "limit": limit, "offset": offset}
            notes: List[Dict[str, Any]] = []
            for api_base in self.api_bases:
                payload = self._get_json(f"{api_base}/notes", params=params)
                notes = self._extract_notes(payload)
                if notes:
                    break
            if not notes:
                break
            for note in notes:
                yield note
            if len(notes) < limit:
                break
            offset += limit

    def _dedupe_notes(self, notes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        deduped: Dict[str, Dict[str, Any]] = {}
        for note in notes:
            forum = str(note.get("forum") or note.get("id") or "")
            if not forum:
                title = self._content_value(note.get("content", {}), "title") or ""
                forum = hashlib.md5(title.encode("utf-8")).hexdigest()
            deduped[forum] = note
        return list(deduped.values())

    def _extract_notes(self, payload: Any) -> List[Dict[str, Any]]:
        if isinstance(payload, dict):
            notes = payload.get("notes")
            if isinstance(notes, list):
                return [n for n in notes if isinstance(n, dict)]
            return []
        if isinstance(payload, list):
            return [n for n in payload if isinstance(n, dict)]
        return []

    def _note_to_paper(self, note: Dict[str, Any], year: int) -> Optional[PaperMeta]:
        content = note.get("content", {})
        title = self._content_value(content, "title")
        if not title:
            return None

        forum = note.get("forum") or note.get("id")
        if not forum:
            forum = hashlib.md5(title.encode("utf-8")).hexdigest()

        pdf = self._content_value(content, "pdf")
        pdf_url = self._normalize_pdf_url(pdf, str(forum)) if pdf else f"{self.web_base}/pdf?id={forum}"

        return PaperMeta(
            paper_id=str(forum),
            title=title,
            conf=self.slug,
            year=year,
            detail_url=f"{self.web_base}/forum?id={forum}",
            authors=self._content_list(content, "authors"),
            abstract=self._content_value(content, "abstract"),
            keywords=self._content_list(content, "keywords"),
            pdf_url=pdf_url,
        )

    def _is_accepted(self, note: Dict[str, Any], year: int) -> bool:
        content = note.get("content", {})
        venue = (self._content_value(content, "venue") or "").lower()
        if venue:
            if f"iclr {year}" in venue and "conference" in venue:
                rejected_tokens = ["submitted", "withdrawn", "reject", "desk reject"]
                return not any(token in venue for token in rejected_tokens)

        decision = self._decision_text(note).lower()
        if not decision:
            return False
        if "accept" in decision:
            return True
        return False

    def _decision_text(self, note: Dict[str, Any]) -> str:
        details = note.get("details", {})
        replies = details.get("directReplies", []) if isinstance(details, dict) else []
        for reply in replies:
            if not isinstance(reply, dict):
                continue
            invitation = str(reply.get("invitation", "")).lower()
            if "decision" not in invitation:
                continue
            content = reply.get("content", {})
            for key in ("decision", "recommendation"):
                value = self._content_value(content, key)
                if value:
                    return value
        return ""

    def _fetch_single_note(self, forum_id: str) -> Optional[Dict[str, Any]]:
        params = {"forum": forum_id, "details": "directReplies,original", "limit": 1}
        for api_base in self.api_bases:
            payload = self._get_json(f"{api_base}/notes", params=params)
            notes = self._extract_notes(payload)
            if notes:
                return notes[0]
        return None

    def _fetch_citation(self, forum_id: str) -> Optional[str]:
        urls = [
            f"{self.web_base}/citation?id={forum_id}&format=bibtex",
            f"{self.web_base}/citation?id={forum_id}",
        ]
        for url in urls:
            resp = self._get(url)
            if resp is None:
                continue
            text = resp.text.strip()
            if "@" in text and "{" in text:
                return text
        return None

    def _forum_id_from_paper(self, paper: PaperMeta) -> Optional[str]:
        if paper.paper_id:
            return paper.paper_id
        if not paper.detail_url:
            return None
        query = parse_qs(urlparse(paper.detail_url).query)
        values = query.get("id")
        if values:
            return values[0]
        return None

    def _normalize_pdf_url(self, value: str, forum_id: str) -> str:
        if value.startswith("http://") or value.startswith("https://"):
            return value
        if value.startswith("/"):
            return urljoin(self.web_base, value)
        return f"{self.web_base}/pdf?id={forum_id}"

    def _content_value(self, content: Dict[str, Any], key: str) -> Optional[str]:
        raw = content.get(key)
        if raw is None:
            return None
        if isinstance(raw, dict):
            value = raw.get("value")
            if isinstance(value, str):
                return value.strip()
            if isinstance(value, list):
                return ", ".join(str(item) for item in value)
            if value is None:
                return None
            return str(value)
        if isinstance(raw, list):
            return ", ".join(str(item) for item in raw)
        if isinstance(raw, str):
            return raw.strip()
        return str(raw)

    def _content_list(self, content: Dict[str, Any], key: str) -> List[str]:
        raw = content.get(key)
        if raw is None:
            return []
        if isinstance(raw, dict):
            raw = raw.get("value")
        if isinstance(raw, list):
            return [str(item).strip() for item in raw if str(item).strip()]
        if isinstance(raw, str):
            parts = [part.strip() for part in raw.replace(";", ",").split(",")]
            return [part for part in parts if part]
        return []

    def _get_json(self, url: str, params: Optional[Dict[str, Any]] = None) -> Any:
        resp = self._get(url, params=params)
        if resp is None:
            return {}
        try:
            return resp.json()
        except ValueError:
            return {}

    def _get(
        self,
        url: str,
        params: Optional[Dict[str, Any]] = None,
        binary: bool = False,
    ) -> Optional[requests.Response]:
        if self.request_delay > 0:
            time.sleep(self.request_delay)
        try:
            resp = self.session.get(url, params=params, timeout=30)
        except requests.RequestException:
            return None
        if resp.status_code != 200:
            return None
        if binary:
            return resp
        resp.encoding = resp.encoding or "utf-8"
        return resp
