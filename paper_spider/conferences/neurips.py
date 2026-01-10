# Copyright 2026 Isaacveg
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#     http://www.apache.org/licenses/LICENSE-2.0

from __future__ import annotations

import hashlib
import re
import time
from typing import List, Optional
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from .base import ConferenceBase
from ..models import PaperMeta


class NeuripsConference(ConferenceBase):
    name = "NeurIPS"
    slug = "neurips"

    def __init__(self) -> None:
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": "PaperSpider/0.1 (+https://localhost)",
            }
        )
        self.request_delay = 0.1

    def list_papers(self, year: int) -> List[PaperMeta]:
        base_urls = [
            f"https://proceedings.neurips.cc/paper/{year}",
            f"https://papers.nips.cc/paper_files/paper/{year}",
        ]
        for base_url in base_urls:
            resp = self._get(base_url)
            if resp is None:
                continue
            soup = BeautifulSoup(resp.text, "html.parser")
            papers = []
            for anchor in soup.find_all("a"):
                href = anchor.get("href")
                if not href:
                    continue
                if "Abstract" not in href and "abstract" not in href:
                    continue
                if "Bibtex" in href or "bibtex" in href:
                    continue
                title = anchor.get_text(" ", strip=True)
                if not title:
                    continue
                detail_url = urljoin(base_url, href)
                paper_id = self._extract_paper_id(detail_url, title)
                papers.append(
                    PaperMeta(
                        paper_id=paper_id,
                        title=title,
                        conf=self.slug,
                        year=year,
                        detail_url=detail_url,
                    )
                )
            if papers:
                return papers
        raise RuntimeError("Unable to load NeurIPS proceedings list")

    def fetch_details(self, paper: PaperMeta) -> PaperMeta:
        if not paper.detail_url:
            return paper
        resp = self._get(paper.detail_url)
        if resp is None:
            return paper
        soup = BeautifulSoup(resp.text, "html.parser")
        abstract = self._section_text(soup, "Abstract")
        authors_text = self._section_text(soup, "Authors")
        keywords_text = self._section_text(soup, "Keywords")
        authors = self._split_people(authors_text)
        keywords = self._split_keywords(keywords_text)
        pdf_url = self._find_pdf_link(soup, paper.detail_url)
        bibtex_url = self._find_bibtex_link(soup, paper.detail_url)

        paper.abstract = abstract or paper.abstract
        if authors:
            paper.authors = authors
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
        if not paper.bibtex_url:
            paper = self.fetch_details(paper)
        if not paper.bibtex_url:
            raise RuntimeError("Bibtex URL not found")
        resp = self._get(paper.bibtex_url)
        if resp is None:
            raise RuntimeError("Failed to download bibtex")
        return resp.text

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

    def _extract_paper_id(self, url: str, title: str) -> str:
        basename = url.split("/")[-1]
        match = re.match(r"(.+?)-(Abstract|Paper|Title)", basename)
        if match:
            return match.group(1)
        if basename.endswith(".html"):
            return basename.replace(".html", "")
        digest = hashlib.md5(title.encode("utf-8")).hexdigest()
        return digest

    def _section_text(self, soup: BeautifulSoup, section_name: str) -> Optional[str]:
        for header in soup.find_all(["h2", "h3", "h4"]):
            if header.get_text(" ", strip=True).lower() != section_name.lower():
                continue
            sibling = header.find_next_sibling()
            while sibling and sibling.name in {"br", "hr"}:
                sibling = sibling.find_next_sibling()
            if sibling:
                return sibling.get_text(" ", strip=True)
        return None

    def _split_people(self, text: Optional[str]) -> List[str]:
        if not text:
            return []
        parts = [part.strip() for part in text.replace(";", ",").split(",")]
        return [part for part in parts if part]

    def _split_keywords(self, text: Optional[str]) -> List[str]:
        if not text:
            return []
        parts = [part.strip() for part in text.replace(";", ",").split(",")]
        return [part for part in parts if part]

    def _find_pdf_link(self, soup: BeautifulSoup, base_url: str) -> Optional[str]:
        for anchor in soup.find_all("a"):
            href = anchor.get("href")
            if not href:
                continue
            text = anchor.get_text(" ", strip=True).lower()
            if href.lower().endswith(".pdf") or "pdf" in text:
                return urljoin(base_url, href)
        return None

    def _find_bibtex_link(self, soup: BeautifulSoup, base_url: str) -> Optional[str]:
        for anchor in soup.find_all("a"):
            href = anchor.get("href")
            if not href:
                continue
            text = anchor.get_text(" ", strip=True).lower()
            if "bibtex" in text or "bibtex" in href.lower() or href.lower().endswith(".bib"):
                return urljoin(base_url, href)
        return None
