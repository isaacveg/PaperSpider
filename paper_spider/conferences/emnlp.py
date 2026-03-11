# Copyright 2026 Isaacveg
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#     http://www.apache.org/licenses/LICENSE-2.0

from __future__ import annotations

import time
from typing import List, Optional
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from ..models import PaperMeta
from .base import ConferenceBase


class EmnlpConference(ConferenceBase):
    name = "EMNLP"
    slug = "emnlp"

    def __init__(self) -> None:
        self.web_base = "https://aclanthology.org"
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "PaperSpider/0.1 (+https://localhost)"})
        self.request_delay = 0.1

    def list_papers(self, year: int) -> List[PaperMeta]:
        volume_url = f"{self.web_base}/volumes/{year}.emnlp-main/"
        resp = self._get(volume_url)
        if resp is None:
            raise RuntimeError(f"Unable to load EMNLP proceedings for {year}")

        soup = BeautifulSoup(resp.text, "html.parser")
        papers: List[PaperMeta] = []
        for block in soup.select("div.d-sm-flex.align-items-stretch.mb-3"):
            paper = self._paper_from_listing(block, volume_url, year)
            if paper:
                papers.append(paper)

        if not papers:
            raise RuntimeError(f"No EMNLP papers parsed for {year}")
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
        abstract = self._extract_detail_abstract(soup)
        pdf_url = self._meta_content(soup, "citation_pdf_url")

        if title:
            paper.title = title
        if authors:
            paper.authors = authors
        if abstract:
            paper.abstract = abstract
        if pdf_url:
            paper.pdf_url = pdf_url

        if not paper.bibtex_url:
            paper.bibtex_url = f"{self.web_base}/{paper.paper_id}.bib"
        return paper

    def fetch_pdf(self, paper: PaperMeta) -> bytes:
        if not paper.pdf_url:
            paper = self.fetch_details(paper)
        if not paper.pdf_url:
            paper.pdf_url = f"{self.web_base}/{paper.paper_id}.pdf"

        resp = self._get(paper.pdf_url, binary=True)
        if resp is None:
            raise RuntimeError("Failed to download PDF")
        return resp.content

    def fetch_bibtex(self, paper: PaperMeta) -> str:
        if paper.bibtex:
            return paper.bibtex
        if not paper.bibtex_url:
            paper = self.fetch_details(paper)
        if not paper.bibtex_url:
            paper.bibtex_url = f"{self.web_base}/{paper.paper_id}.bib"

        resp = self._get(paper.bibtex_url)
        if resp is None:
            raise RuntimeError("Bibtex not found")
        paper.bibtex = resp.text.strip()
        return paper.bibtex

    def _paper_from_listing(self, block, base_url: str, year: int) -> Optional[PaperMeta]:
        title_anchor = block.select_one("strong a[href]")
        if title_anchor is None:
            return None
        detail_href = title_anchor.get("href")
        if not detail_href:
            return None

        detail_url = urljoin(base_url, detail_href)
        paper_id = detail_url.rstrip("/").split("/")[-1]
        if paper_id.endswith(".0") or paper_id == f"{year}.emnlp-main":
            return None

        title = title_anchor.get_text(" ", strip=True)
        if not title:
            return None

        authors = [
            anchor.get_text(" ", strip=True)
            for anchor in block.select("span.d-block > a[href*='/people/']")
            if anchor.get_text(" ", strip=True)
        ]
        pdf_url = self._find_badge_url(block, "pdf", base_url)
        bibtex_url = self._find_badge_url(block, "bib", base_url)

        abstract = None
        abstract_block = block.find_next_sibling()
        if abstract_block is not None and "abstract-collapse" in (abstract_block.get("class") or []):
            body = abstract_block.select_one(".card-body")
            if body is not None:
                abstract = body.get_text(" ", strip=True) or None

        return PaperMeta(
            paper_id=paper_id,
            title=title,
            conf=self.slug,
            year=year,
            detail_url=detail_url,
            authors=authors,
            abstract=abstract,
            pdf_url=pdf_url,
            bibtex_url=bibtex_url,
        )

    def _find_badge_url(self, block, badge_text: str, base_url: str) -> Optional[str]:
        expected = badge_text.strip().lower()
        for anchor in block.select("a[href]"):
            text = anchor.get_text(" ", strip=True).lower()
            if text != expected:
                continue
            return urljoin(base_url, anchor["href"])
        return None

    def _extract_detail_abstract(self, soup: BeautifulSoup) -> Optional[str]:
        block = soup.select_one(".acl-abstract span")
        if block is None:
            block = soup.select_one(".acl-abstract")
        if block is None:
            return None
        text = block.get_text(" ", strip=True)
        return text or None

    def _meta_content(self, soup: BeautifulSoup, name: str) -> Optional[str]:
        tag = soup.find("meta", attrs={"name": name})
        if tag is None:
            return None
        content = tag.get("content")
        if not content:
            return None
        return str(content).strip() or None

    def _meta_contents(self, soup: BeautifulSoup, name: str) -> List[str]:
        values: List[str] = []
        for tag in soup.find_all("meta", attrs={"name": name}):
            content = str(tag.get("content") or "").strip()
            if content:
                values.append(content)
        return values

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
