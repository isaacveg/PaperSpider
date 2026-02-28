# Copyright 2026 Isaacveg
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#     http://www.apache.org/licenses/LICENSE-2.0

from __future__ import annotations

import hashlib
import re
import time
from typing import Iterable, List, Optional
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from ..models import PaperMeta
from .base import ConferenceBase


class IcmlConference(ConferenceBase):
    name = "ICML"
    slug = "icml"

    def __init__(self) -> None:
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "PaperSpider/0.1 (+https://localhost)"})
        self.request_delay = 0.1

    def list_papers(self, year: int) -> List[PaperMeta]:
        volume_url = self._find_volume_url(year)
        if not volume_url:
            raise RuntimeError(f"Unable to find ICML volume for {year}")
        resp = self._get(volume_url)
        if resp is None:
            raise RuntimeError(f"Unable to load ICML volume page for {year}")

        soup = BeautifulSoup(resp.text, "html.parser")
        papers: List[PaperMeta] = []
        for block in soup.select("div.paper"):
            title_node = block.select_one("p.title")
            if not title_node:
                continue
            title = title_node.get_text(" ", strip=True)
            if not title:
                continue

            abs_link = self._find_link(block.find_all("a"), "abs")
            pdf_link = self._find_link(block.find_all("a"), "download pdf")
            detail_url = urljoin(volume_url, abs_link) if abs_link else None
            pdf_url = urljoin(volume_url, pdf_link) if pdf_link else None

            paper_id = self._extract_paper_id(detail_url, title)
            authors = self._parse_authors(block.select_one("p.authors"))
            papers.append(
                PaperMeta(
                    paper_id=paper_id,
                    title=title,
                    conf=self.slug,
                    year=year,
                    detail_url=detail_url,
                    pdf_url=pdf_url,
                    authors=authors,
                )
            )

        if not papers:
            raise RuntimeError(f"No ICML papers parsed for {year}")
        return papers

    def fetch_details(self, paper: PaperMeta) -> PaperMeta:
        if not paper.detail_url:
            return paper
        resp = self._get(paper.detail_url)
        if resp is None:
            return paper

        soup = BeautifulSoup(resp.text, "html.parser")
        abstract = self._extract_abstract(soup)
        authors = self._extract_authors(soup)
        bibtex = self._extract_bibtex(soup)
        pdf_url = self._find_link(soup.find_all("a"), "download pdf")

        if abstract:
            paper.abstract = abstract
        if authors:
            paper.authors = authors
        if bibtex:
            paper.bibtex = bibtex
        if pdf_url:
            paper.pdf_url = urljoin(paper.detail_url, pdf_url)
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
        if not paper.bibtex:
            paper = self.fetch_details(paper)
        if not paper.bibtex:
            raise RuntimeError("Bibtex not found")
        return paper.bibtex

    def _find_volume_url(self, year: int) -> Optional[str]:
        resp = self._get("https://proceedings.mlr.press/")
        if resp is None:
            return None

        soup = BeautifulSoup(resp.text, "html.parser")
        year_text = str(year)
        for item in soup.find_all("li"):
            text = item.get_text(" ", strip=True)
            normalized = re.sub(r"\s+", " ", text).lower()
            if year_text not in normalized:
                continue
            if "icml" not in normalized and "international conference on machine learning" not in normalized:
                continue
            anchor = item.find("a", href=True)
            if anchor:
                return urljoin("https://proceedings.mlr.press/", anchor["href"])
        return None

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

    def _find_link(self, anchors: Iterable, marker: str) -> Optional[str]:
        marker_norm = marker.strip().lower()
        for anchor in anchors:
            href = anchor.get("href")
            text = anchor.get_text(" ", strip=True).lower()
            if not href:
                continue
            if marker_norm in text:
                return href
        return None

    def _parse_authors(self, node) -> List[str]:
        if node is None:
            return []
        text = node.get_text(" ", strip=True)
        return [part.strip() for part in text.split(",") if part.strip()]

    def _extract_authors(self, soup: BeautifulSoup) -> List[str]:
        heading = soup.find("h1")
        if heading is None:
            return []
        node = heading.find_next_sibling()
        while node is not None:
            text = node.get_text(" ", strip=True)
            if not text:
                node = node.find_next_sibling()
                continue
            if "Proceedings of" in text:
                break
            if text and "Abstract" not in text:
                return [part.strip() for part in text.split(",") if part.strip()]
            node = node.find_next_sibling()
        return []

    def _extract_abstract(self, soup: BeautifulSoup) -> Optional[str]:
        for header in soup.find_all(["h2", "h3", "h4"]):
            if "abstract" != header.get_text(" ", strip=True).lower():
                continue
            node = header.find_next_sibling()
            chunks: List[str] = []
            while node is not None:
                if node.name in {"h2", "h3", "h4"}:
                    break
                text = node.get_text(" ", strip=True)
                if text:
                    chunks.append(text)
                node = node.find_next_sibling()
            if chunks:
                return " ".join(chunks)
        return None

    def _extract_bibtex(self, soup: BeautifulSoup) -> Optional[str]:
        for node in soup.find_all(["code", "pre"]):
            text = node.get_text("\n", strip=True)
            if "@InProceedings" in text or "@inproceedings" in text:
                return text
        return None

    def _extract_paper_id(self, detail_url: Optional[str], title: str) -> str:
        if detail_url:
            basename = detail_url.rstrip("/").split("/")[-1]
            if basename.endswith(".html"):
                return basename[:-5]
        return hashlib.md5(title.encode("utf-8")).hexdigest()
