# Copyright 2026 Isaacveg
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#     http://www.apache.org/licenses/LICENSE-2.0

from __future__ import annotations

import re
from typing import List, Optional
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from ..models import PaperCategory, PaperMeta
from .request_base import RequestsConferenceBase


class IjcaiConference(RequestsConferenceBase):
    name = "IJCAI"
    slug = "ijcai"
    proceedings_base_url = "https://www.ijcai.org/proceedings/"

    def list_papers(self, year: int) -> List[PaperMeta]:
        proceedings_url = self._proceedings_url(year)
        resp = self._get(proceedings_url)
        if resp is None:
            raise RuntimeError(f"Unable to load IJCAI proceedings page for {year}")

        soup = BeautifulSoup(resp.text, "html.parser")
        papers: List[PaperMeta] = []
        for block in soup.select("div.paper_wrapper"):
            title = self._node_text(block.select_one("div.title"))
            if not title:
                continue

            detail_url = self._find_link(block, "details", proceedings_url)
            pdf_url = self._find_link(block, "pdf", proceedings_url)
            numeric_id = self._extract_numeric_paper_id(detail_url, block.get("id"))
            paper_id = self._paper_id(year, numeric_id)
            authors = self._split_authors(self._node_text(block.select_one("div.authors")))
            category = PaperCategory.from_fields(
                self._section_title(block),
                self._subsection_title(block),
            )

            papers.append(
                PaperMeta(
                    paper_id=paper_id,
                    title=title,
                    conf=self.slug,
                    year=year,
                    category=category,
                    detail_url=detail_url,
                    authors=authors,
                    pdf_url=pdf_url,
                    bibtex_url=self._bibtex_url(year, numeric_id),
                )
            )

        if not papers:
            raise RuntimeError(f"No IJCAI papers parsed for {year}")
        return papers

    def fetch_details(self, paper: PaperMeta) -> PaperMeta:
        if not paper.detail_url:
            return paper
        resp = self._get(paper.detail_url)
        if resp is None:
            return paper

        soup = BeautifulSoup(resp.text, "html.parser")
        detail = soup.select_one("div.proceedings-detail") or soup

        title = self._node_text(detail.select_one("h1"))
        authors = self._split_authors(self._node_text(detail.select_one("h2")))
        abstract = self._extract_abstract(detail)
        keywords = self._extract_keywords(detail)
        pdf_url = self._find_link(detail, "pdf", paper.detail_url)
        bibtex_url = self._find_link(detail, "bibtex", paper.detail_url)

        if title:
            paper.title = title
        if authors:
            paper.authors = authors
        if abstract:
            paper.abstract = abstract
        if keywords:
            paper.keywords = keywords
        if pdf_url:
            paper.pdf_url = pdf_url
        if bibtex_url:
            paper.bibtex_url = bibtex_url
        return paper

    def fetch_pdf(self, paper: PaperMeta) -> bytes:
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
        if not paper.bibtex_url:
            numeric_id = self._numeric_id_from_paper(paper)
            paper.bibtex_url = self._bibtex_url(paper.year, numeric_id)
        resp = self._get(paper.bibtex_url)
        if resp is None:
            raise RuntimeError("Failed to download bibtex")
        paper.bibtex = resp.text
        return paper.bibtex

    def _proceedings_url(self, year: int) -> str:
        return urljoin(self.proceedings_base_url, f"{year}/")

    def _paper_id(self, year: int, numeric_id: str) -> str:
        return f"ijcai{year}p{numeric_id}"

    def _bibtex_url(self, year: int, numeric_id: str) -> str:
        return urljoin(self._proceedings_url(year), f"bibtex/{numeric_id}")

    def _find_link(self, node, marker: str, base_url: str) -> Optional[str]:
        marker_norm = marker.lower()
        for anchor in node.find_all("a", href=True):
            text = anchor.get_text(" ", strip=True).lower()
            href = anchor["href"]
            if marker_norm in text or marker_norm in href.lower():
                return urljoin(base_url, href)
        return None

    def _section_title(self, block) -> Optional[str]:
        for parent in block.parents:
            if "section" not in parent.get("class", []):
                continue
            title = parent.find("div", class_="section_title", recursive=False)
            text = self._node_text(title)
            if text:
                return text
        return None

    def _subsection_title(self, block) -> Optional[str]:
        parent = block.find_parent("div", class_="subsection")
        if parent is None:
            return None
        return self._node_text(parent.find("div", class_="subsection_title", recursive=False))

    def _extract_abstract(self, detail) -> Optional[str]:
        keywords = detail.select_one("div.keywords")
        for row in detail.select("div.row"):
            if keywords is not None and keywords in row.descendants:
                abstract_parts: List[str] = []
                for column in row.find_all("div", class_=self._has_column_class, recursive=False):
                    if column.select_one("div.keywords"):
                        continue
                    text = self._node_text(column)
                    if text:
                        abstract_parts.append(text)
                if abstract_parts:
                    return " ".join(abstract_parts)
        return None

    def _extract_keywords(self, detail) -> List[str]:
        return [
            text
            for text in (self._node_text(node) for node in detail.select("div.keywords div.topic"))
            if text
        ]

    def _extract_numeric_paper_id(self, detail_url: Optional[str], fallback: Optional[str]) -> str:
        if detail_url:
            basename = detail_url.rstrip("/").split("/")[-1]
            if basename:
                return str(int(basename)) if basename.isdigit() else basename
        if fallback:
            match = re.search(r"(\d+)$", fallback)
            if match:
                return str(int(match.group(1)))
        raise RuntimeError("IJCAI paper id not found")

    def _numeric_id_from_paper(self, paper: PaperMeta) -> str:
        match = re.search(r"p(\d+)$", paper.paper_id)
        if match:
            return str(int(match.group(1)))
        if paper.paper_id.isdigit():
            return str(int(paper.paper_id))
        return self._extract_numeric_paper_id(paper.detail_url, None)

    def _split_authors(self, text: Optional[str]) -> List[str]:
        if not text:
            return []
        return [part.strip() for part in text.split(",") if part.strip()]

    def _node_text(self, node) -> Optional[str]:
        if node is None:
            return None
        text = node.get_text(" ", strip=True)
        text = re.sub(r"\s+", " ", text)
        return text or None

    def _has_column_class(self, css_class) -> bool:
        if not css_class:
            return False
        classes = css_class if isinstance(css_class, list) else [css_class]
        return any(str(value).startswith("col-") for value in classes)
