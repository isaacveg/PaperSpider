# Copyright 2026 Isaacveg
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#     http://www.apache.org/licenses/LICENSE-2.0

from __future__ import annotations

import hashlib
import time
from typing import List, Optional
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from ..models import PaperMeta
from .base import ConferenceBase


class NsdiConference(ConferenceBase):
    name = "NSDI"
    slug = "nsdi"

    def __init__(self) -> None:
        self.web_base = "https://www.usenix.org"
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "PaperSpider/0.1 (+https://localhost)"})
        self.request_delay = 0.1

    def list_papers(self, year: int) -> List[PaperMeta]:
        schedule_url = f"{self.web_base}/conference/{self._year_slug(year)}/technical-sessions"
        resp = self._get(schedule_url)
        if resp is None:
            raise RuntimeError(f"Unable to load NSDI technical sessions for {year}")

        soup = BeautifulSoup(resp.text, "html.parser")
        papers: List[PaperMeta] = []
        for article in soup.select("article.node.node-paper.view-mode-schedule"):
            paper = self._paper_from_schedule(article, schedule_url, year)
            if paper:
                papers.append(paper)

        if not papers:
            raise RuntimeError(f"No NSDI papers parsed for {year}")
        return papers

    def fetch_details(self, paper: PaperMeta) -> PaperMeta:
        if not paper.detail_url:
            return paper
        resp = self._get(paper.detail_url)
        if resp is None:
            return paper

        soup = BeautifulSoup(resp.text, "html.parser")
        title = self._meta_content(soup, "citation_title")
        authors = self._meta_contents(soup, "citation_author")
        abstract = self._field_text(soup, "field-name-field-paper-description")
        pdf_url = self._meta_content(soup, "citation_pdf_url")
        bibtex_url = self._find_bibtex_download(soup, paper.detail_url)
        bibtex = self._extract_bibtex(soup)

        if title:
            paper.title = title
        if authors:
            paper.authors = authors
        if abstract:
            paper.abstract = abstract
        if pdf_url:
            paper.pdf_url = pdf_url
        if bibtex_url:
            paper.bibtex_url = bibtex_url
        if bibtex:
            paper.bibtex = bibtex
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
            paper = self.fetch_details(paper)
        if paper.bibtex:
            return paper.bibtex
        if not paper.bibtex_url:
            raise RuntimeError("Bibtex not found")

        resp = self._get(paper.bibtex_url)
        if resp is None:
            raise RuntimeError("Bibtex not found")
        paper.bibtex = resp.text.strip()
        return paper.bibtex

    def _paper_from_schedule(self, article, base_url: str, year: int) -> Optional[PaperMeta]:
        title_anchor = article.select_one("h2 a[href]")
        if title_anchor is None:
            return None
        title = title_anchor.get_text(" ", strip=True)
        detail_href = title_anchor.get("href")
        if not title or not detail_href:
            return None

        detail_url = urljoin(base_url, detail_href)
        paper_id = detail_url.rstrip("/").split("/")[-1]
        abstract = self._field_text(article, "field-name-field-paper-description-long")
        authors = self._extract_listing_authors(article)

        return PaperMeta(
            paper_id=paper_id or hashlib.md5(title.encode("utf-8")).hexdigest(),
            title=title,
            conf=self.slug,
            year=year,
            detail_url=detail_url,
            authors=authors,
            abstract=abstract,
        )

    def _extract_listing_authors(self, article) -> List[str]:
        authors_block = article.select_one(".field-name-field-paper-people-text p")
        if authors_block is None:
            return []

        authors_copy = BeautifulSoup(str(authors_block), "html.parser")
        for tag in authors_copy.find_all("em"):
            tag.decompose()
        text = authors_copy.get_text(" ", strip=True)
        if not text:
            return []

        normalized = text.replace(";", ",").replace(" and ", ",")
        parts = [part.strip(" ,") for part in normalized.split(",")]
        return [part for part in parts if part]

    def _find_bibtex_download(self, soup: BeautifulSoup, base_url: str) -> Optional[str]:
        for anchor in soup.select("a[href]"):
            href = anchor.get("href")
            if not href:
                continue
            if "/biblio/export/bibtex/" in href:
                return urljoin(base_url, href)
        return None

    def _extract_bibtex(self, soup: BeautifulSoup) -> Optional[str]:
        block = soup.select_one(".bibtex-text-entry")
        if block is None:
            return None
        text = block.get_text("\n", strip=True).replace("\xa0", " ")
        return text or None

    def _field_text(self, scope, class_name: str) -> Optional[str]:
        block = scope.select_one(f".{class_name}")
        if block is None:
            return None
        text = block.get_text(" ", strip=True)
        return text or None

    def _meta_content(self, soup: BeautifulSoup, name: str) -> Optional[str]:
        tag = soup.find("meta", attrs={"name": name})
        if tag is None:
            return None
        content = str(tag.get("content") or "").strip()
        return content or None

    def _meta_contents(self, soup: BeautifulSoup, name: str) -> List[str]:
        values: List[str] = []
        for tag in soup.find_all("meta", attrs={"name": name}):
            content = str(tag.get("content") or "").strip()
            if content:
                values.append(content)
        return values

    def _year_slug(self, year: int) -> str:
        return f"nsdi{year % 100:02d}"

    def _get(self, url: str, binary: bool = False) -> Optional[requests.Response]:
        if self.request_delay > 0:
            time.sleep(self.request_delay)
        try:
            resp = self.session.get(url, timeout=30)
        except requests.RequestException:
            return None
        if resp.status_code != 200:
            return None
        if binary:
            return resp
        resp.encoding = resp.encoding or "utf-8"
        return resp
