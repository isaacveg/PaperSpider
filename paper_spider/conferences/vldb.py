# Copyright 2026 Isaacveg
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#     http://www.apache.org/licenses/LICENSE-2.0

from __future__ import annotations

import hashlib
import html
import json
import re
from typing import Any, List, Optional
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

from ..models import PaperCategory, PaperMeta
from .request_base import RequestsConferenceBase


class VldbConference(RequestsConferenceBase):
    name = "VLDB"
    slug = "vldb"
    web_base = "https://www.vldb.org/pvldb"

    def list_papers(self, year: int) -> List[PaperMeta]:
        volume = self._volume_for_year(year)
        volume_url = self._volume_url(volume)
        resp = self._get(volume_url)
        if resp is None:
            raise RuntimeError(f"Unable to load VLDB/PVLDB volume page for {year}")

        page_props = self._extract_page_props(resp.text)
        summaries = self._summary_lookup(page_props.get("volumeSummaries", []))
        grouped_issues = page_props.get("groupedIssues", {})
        if not isinstance(grouped_issues, dict):
            raise RuntimeError(f"Unexpected VLDB/PVLDB volume data for {year}")

        papers: List[PaperMeta] = []
        seen_ids: set[str] = set()
        for issue_key in sorted(grouped_issues, key=self._issue_sort_key):
            issue_items = grouped_issues.get(issue_key)
            if not isinstance(issue_items, list):
                continue
            for item in issue_items:
                if not isinstance(item, dict):
                    continue
                paper = self._paper_from_issue_item(item, summaries, volume_url, year)
                if paper is None or paper.paper_id in seen_ids:
                    continue
                seen_ids.add(paper.paper_id)
                papers.append(paper)

        if not papers:
            raise RuntimeError(f"No VLDB/PVLDB papers parsed for {year}")
        return papers

    def fetch_details(self, paper: PaperMeta) -> PaperMeta:
        return paper

    def fetch_pdf(self, paper: PaperMeta) -> bytes:
        if not paper.pdf_url:
            paper.pdf_url = self._pdf_url_from_paper_id(paper.paper_id)
        if not paper.pdf_url:
            raise RuntimeError("PDF URL not found")

        resp = self._get(paper.pdf_url, binary=True)
        if resp is None:
            raise RuntimeError("Failed to download PDF")
        return resp.content

    def fetch_bibtex(self, paper: PaperMeta) -> str:
        if paper.bibtex:
            return paper.bibtex

        fields = [
            ("title", paper.title),
            ("author", " and ".join(paper.authors)),
            ("booktitle", "Proceedings of the VLDB Endowment"),
            ("year", str(paper.year)),
        ]
        if paper.pdf_url:
            fields.append(("url", paper.pdf_url))

        body = ",\n".join(
            f"  {key} = {{{self._bibtex_escape(value)}}}" for key, value in fields if value
        )
        paper.bibtex = f"@inproceedings{{{self._bibtex_key(paper)},\n{body}\n}}"
        return paper.bibtex

    def _paper_from_issue_item(
        self,
        item: dict[str, Any],
        summaries: dict[str, dict[str, Any]],
        volume_url: str,
        year: int,
    ) -> Optional[PaperMeta]:
        title = self._clean_text(item.get("title"))
        if not title or title.lower() == "front matter":
            return None

        pdf_url = self._clean_text(item.get("pdf"))
        source_id = self._source_id_from_pdf_url(pdf_url)
        summary = summaries.get(source_id or "") or summaries.get(self._normalize_title(title), {})
        summary_id = self._clean_text(summary.get("Paper ID"))
        if summary_id:
            source_id = summary_id
        if not source_id:
            source_id = f"vldb-{hashlib.md5(title.encode('utf-8')).hexdigest()}"

        authors_text = self._clean_text(summary.get("Author Names")) or self._clean_text(item.get("authors"))
        abstract = self._clean_text(summary.get("Abstract"))
        issue = item.get("issue")

        return PaperMeta(
            paper_id=self._paper_id(source_id),
            title=title,
            conf=self.slug,
            year=year,
            category=PaperCategory(track="main", paper_type="conference"),
            detail_url=self._issue_url(volume_url, issue),
            authors=self._split_authors(authors_text),
            abstract=abstract,
            pdf_url=urljoin(volume_url, pdf_url) if pdf_url else self._pdf_url_from_source_id(source_id),
        )

    def _extract_page_props(self, text: str) -> dict[str, Any]:
        soup = BeautifulSoup(text, "html.parser")
        script = soup.find("script", id="__NEXT_DATA__", attrs={"type": "application/json"})
        if script is None or script.string is None:
            raise RuntimeError("VLDB/PVLDB Next.js data not found")

        try:
            data = json.loads(html.unescape(script.string))
        except json.JSONDecodeError as exc:
            raise RuntimeError("VLDB/PVLDB Next.js data is invalid") from exc

        page_props = data.get("props", {}).get("pageProps", {})
        if not isinstance(page_props, dict):
            raise RuntimeError("VLDB/PVLDB page props not found")
        return page_props

    def _summary_lookup(self, summaries: Any) -> dict[str, dict[str, Any]]:
        lookup: dict[str, dict[str, Any]] = {}
        if not isinstance(summaries, list):
            return lookup

        for summary in summaries:
            if not isinstance(summary, dict):
                continue
            source_id = self._clean_text(summary.get("Paper ID"))
            title = self._clean_text(summary.get("Paper Title"))
            if source_id:
                lookup[source_id] = summary
            if title:
                lookup[self._normalize_title(title)] = summary
        return lookup

    def _volume_for_year(self, year: int) -> int:
        volume = year - 2007
        if volume < 1:
            raise RuntimeError(f"No VLDB/PVLDB volume mapping for {year}")
        return volume

    def _volume_url(self, volume: int) -> str:
        return f"{self.web_base}/volumes/{volume}/"

    def _issue_url(self, volume_url: str, issue: Any) -> str:
        if isinstance(issue, int) or (isinstance(issue, str) and issue.isdigit()):
            return f"{volume_url}#issue-{issue}"
        return volume_url

    def _source_id_from_pdf_url(self, pdf_url: Optional[str]) -> Optional[str]:
        if not pdf_url:
            return None
        path = urlparse(pdf_url).path
        marker = "/pvldb/"
        if marker in path:
            path = path.split(marker, 1)[1]
        else:
            path = path.lstrip("/")
        if path.lower().endswith(".pdf"):
            path = path[:-4]
        return path or None

    def _pdf_url_from_paper_id(self, paper_id: str) -> Optional[str]:
        if not paper_id.startswith("vol"):
            return None
        source_id = paper_id.replace("_", "/", 1)
        return self._pdf_url_from_source_id(source_id)

    def _pdf_url_from_source_id(self, source_id: str) -> Optional[str]:
        if not source_id.startswith("vol"):
            return None
        return f"{self.web_base}/{source_id}.pdf"

    def _paper_id(self, source_id: str) -> str:
        return source_id.replace("/", "_")

    def _split_authors(self, text: Optional[str]) -> List[str]:
        if not text:
            return []
        separator = "," if "," in text else " and "
        return [part.strip() for part in text.split(separator) if part.strip()]

    def _clean_text(self, value: Any) -> Optional[str]:
        if value is None:
            return None
        text = re.sub(r"\s+", " ", str(value)).strip()
        return text or None

    def _normalize_title(self, title: str) -> str:
        return re.sub(r"\s+", " ", title).strip().casefold()

    def _issue_sort_key(self, issue: str) -> tuple[int, str]:
        return (int(issue), issue) if issue.isdigit() else (999, issue)

    def _bibtex_key(self, paper: PaperMeta) -> str:
        return re.sub(r"[^A-Za-z0-9:_-]+", "_", paper.paper_id).strip("_") or "vldb"

    def _bibtex_escape(self, value: str) -> str:
        return value.replace("\\", "\\\\").replace("{", "\\{").replace("}", "\\}")
