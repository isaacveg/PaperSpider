# Copyright 2026 Isaacveg
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#     http://www.apache.org/licenses/LICENSE-2.0

from __future__ import annotations

import hashlib
import re
from typing import List, Optional
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

from ..models import PaperCategory, PaperMeta
from .request_base import RequestsConferenceBase


class NdssConference(RequestsConferenceBase):
    name = "NDSS"
    slug = "ndss"
    web_base = "https://www.ndss-symposium.org"

    def list_papers(self, year: int) -> List[PaperMeta]:
        list_url = f"{self.web_base}/ndss{year}/accepted-papers/"
        resp = self._get(list_url)
        if resp is None:
            raise RuntimeError(f"Unable to load NDSS accepted papers for {year}")

        soup = BeautifulSoup(resp.text, "html.parser")
        papers: List[PaperMeta] = []
        seen_ids: set[str] = set()
        for item in soup.select(".pt-cv-content-item"):
            paper = self._paper_from_listing(item, year)
            if paper is None or paper.paper_id in seen_ids:
                continue
            seen_ids.add(paper.paper_id)
            papers.append(paper)

        if not papers:
            raise RuntimeError(f"No NDSS papers parsed for {year}")
        return papers

    def fetch_details(self, paper: PaperMeta) -> PaperMeta:
        if not paper.detail_url:
            return paper
        resp = self._get(paper.detail_url)
        if resp is None:
            return paper

        soup = BeautifulSoup(resp.text, "html.parser")
        title = self._detail_title(soup)
        authors = self._detail_authors(soup)
        abstract = self._detail_abstract(soup)
        pdf_url = self._find_pdf_url(soup, paper.detail_url)

        if title:
            paper.title = title
        if authors:
            paper.authors = authors
        if abstract:
            paper.abstract = abstract
        if pdf_url:
            paper.pdf_url = pdf_url
        if not paper.bibtex:
            paper.bibtex = self._generate_bibtex(paper)
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
        if paper.detail_url and (not paper.authors or not paper.abstract or not paper.pdf_url):
            paper = self.fetch_details(paper)
        if not paper.bibtex:
            paper.bibtex = self._generate_bibtex(paper)
        return paper.bibtex

    def _paper_from_listing(self, item, year: int) -> Optional[PaperMeta]:
        title_anchor = item.select_one(".pt-cv-title a[href*='/ndss-paper/']")
        if title_anchor is None:
            title_anchor = item.select_one("h2 a[href*='/ndss-paper/']")
        if title_anchor is None:
            return None

        href = title_anchor.get("href")
        title = self._normalize_text(title_anchor.get_text(" ", strip=True))
        if not href or not title:
            return None

        detail_url = urljoin(self.web_base, href)
        authors_node = (
            item.select_one(".pt-cv-ctf-display_authors .pt-cv-ctf-value")
            or item.select_one(".pt-cv-ctf-value")
        )
        author_text = authors_node.get_text(" ", strip=True) if authors_node is not None else ""

        return PaperMeta(
            paper_id=self._paper_id_from_url(detail_url, title),
            title=title,
            conf=self.slug,
            year=year,
            category=PaperCategory(track="technical", paper_type="conference"),
            detail_url=detail_url,
            authors=self._parse_authors(author_text),
        )

    def _detail_title(self, soup: BeautifulSoup) -> Optional[str]:
        title_node = soup.select_one("h1.entry-title")
        if title_node is None:
            title_node = soup.find("h1")
        if title_node is None:
            return None
        return self._normalize_text(title_node.get_text(" ", strip=True)) or None

    def _detail_authors(self, soup: BeautifulSoup) -> List[str]:
        paper_data = soup.select_one(".paper-data")
        if paper_data is None:
            return []

        strong = paper_data.find("strong")
        if strong is not None:
            authors = self._parse_authors(strong.get_text(" ", strip=True))
            if authors:
                return authors

        first_paragraph = paper_data.find("p")
        if first_paragraph is None:
            return []
        return self._parse_authors(first_paragraph.get_text(" ", strip=True))

    def _detail_abstract(self, soup: BeautifulSoup) -> Optional[str]:
        paper_data = soup.select_one(".paper-data")
        if paper_data is None:
            return None

        data_copy = BeautifulSoup(str(paper_data), "html.parser")
        for strong in data_copy.find_all("strong"):
            strong.decompose()
        text = self._normalize_text(data_copy.get_text(" ", strip=True))
        return text or None

    def _find_pdf_url(self, soup: BeautifulSoup, base_url: str) -> Optional[str]:
        scopes = [soup.select_one(".paper-buttons"), soup]
        for scope in scopes:
            if scope is None:
                continue
            for anchor in scope.select("a[href]"):
                href = str(anchor.get("href") or "")
                text = anchor.get_text(" ", strip=True).lower()
                classes = anchor.get("class") or []
                if not href:
                    continue
                if href.lower().endswith(".pdf") and (
                    text in {"paper", "pdf"} or "pdf-button" in classes or scope is not soup
                ):
                    return urljoin(base_url, href)
        return None

    def _parse_authors(self, text: str) -> List[str]:
        if not text:
            return []
        cleaned = text.replace("\xa0", " ")
        previous = None
        while cleaned != previous:
            previous = cleaned
            cleaned = re.sub(r"\([^()]*\)", "", cleaned)
        cleaned = re.sub(r"\s+and\s+", ", ", cleaned, flags=re.IGNORECASE)
        cleaned = self._normalize_text(cleaned)
        parts = [part.strip(" ,") for part in cleaned.split(",")]
        return [part for part in parts if part]

    def _generate_bibtex(self, paper: PaperMeta) -> str:
        fields = [
            f"  title = {{{self._bibtex_escape(paper.title)}}}",
            "  booktitle = {Network and Distributed System Security (NDSS) Symposium}",
            f"  year = {{{paper.year}}}",
        ]
        if paper.authors:
            authors = " and ".join(self._bibtex_escape(author) for author in paper.authors)
            fields.insert(1, f"  author = {{{authors}}}")
        if paper.detail_url:
            fields.append(f"  url = {{{paper.detail_url}}}")
        if paper.pdf_url:
            fields.append(f"  pdf = {{{paper.pdf_url}}}")
        return "@inproceedings{" + self._bibtex_key(paper) + ",\n" + ",\n".join(fields) + "\n}"

    def _bibtex_key(self, paper: PaperMeta) -> str:
        words = re.findall(r"[a-zA-Z0-9]+", paper.title.lower())
        stop_words = {"a", "an", "and", "for", "in", "is", "of", "on", "the", "to", "via", "with"}
        significant = [word for word in words if word not in stop_words]
        suffix = "".join(significant[:2])
        if not suffix:
            suffix = hashlib.md5(paper.paper_id.encode("utf-8")).hexdigest()[:8]
        return f"ndss{paper.year}{suffix}"

    def _bibtex_escape(self, value: str) -> str:
        return value.replace("\\", "\\\\").replace("{", "\\{").replace("}", "\\}")

    def _paper_id_from_url(self, url: str, title: str) -> str:
        path = urlparse(url).path.rstrip("/")
        if path:
            paper_id = path.rsplit("/", 1)[-1]
            if paper_id:
                return paper_id
        return hashlib.md5(title.encode("utf-8")).hexdigest()

    def _normalize_text(self, text: str) -> str:
        return re.sub(r"\s+", " ", text.replace("\xa0", " ")).strip()
