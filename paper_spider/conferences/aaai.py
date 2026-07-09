# Copyright 2026 Isaacveg
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#     http://www.apache.org/licenses/LICENSE-2.0

from __future__ import annotations

import hashlib
import re
from typing import List, Optional
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from ..models import PaperCategory, PaperMeta
from .request_base import RequestsConferenceBase


class AaaiConference(RequestsConferenceBase):
    name = "AAAI"
    slug = "aaai"

    archive_url = "https://ojs.aaai.org/index.php/AAAI/issue/archive"
    max_archive_pages = 20

    def list_papers(self, year: int) -> List[PaperMeta]:
        issue_urls = self._find_issue_urls(year)
        if not issue_urls:
            raise RuntimeError(f"Unable to find AAAI proceedings issues for {year}")

        papers: List[PaperMeta] = []
        seen_ids: set[str] = set()
        for issue_url in issue_urls:
            resp = self._get(issue_url)
            if resp is None:
                continue
            for paper in self._papers_from_issue(resp.text, year, issue_url):
                if paper.paper_id in seen_ids:
                    continue
                seen_ids.add(paper.paper_id)
                papers.append(paper)

        if not papers:
            raise RuntimeError(f"No AAAI papers parsed for {year}")
        return papers

    def fetch_details(self, paper: PaperMeta) -> PaperMeta:
        if not paper.detail_url:
            return paper

        resp = self._get(paper.detail_url)
        if resp is None:
            return paper

        soup = BeautifulSoup(resp.text, "html.parser")
        title = self._meta_content(soup, "citation_title") or self._detail_title(soup)
        authors = self._meta_contents(soup, "citation_author") or self._detail_authors(soup)
        abstract = self._meta_content(soup, "DC.Description") or self._detail_abstract(soup)
        pdf_url = self._meta_content(soup, "citation_pdf_url") or self._find_pdf_link(soup, paper.detail_url)
        bibtex_url = self._find_bibtex_url(soup, paper.detail_url)
        keywords = self._detail_keywords(soup)
        track = self._meta_content(soup, "DC.Type.articleType")

        if title:
            paper.title = title
        if authors:
            paper.authors = authors
        if abstract:
            paper.abstract = abstract
        if keywords:
            paper.keywords = keywords
        if pdf_url:
            paper.pdf_url = urljoin(paper.detail_url, pdf_url)
        if bibtex_url:
            paper.bibtex_url = bibtex_url
        if track:
            paper.category = PaperCategory(track=track, paper_type=paper.paper_type)
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
        if not paper.bibtex_url:
            raise RuntimeError("Bibtex URL not found")

        resp = self._get(paper.bibtex_url)
        if resp is None:
            raise RuntimeError("Failed to download bibtex")
        bibtex = resp.text.strip()
        if not bibtex:
            raise RuntimeError("Bibtex not found")
        paper.bibtex = bibtex
        return bibtex

    def _find_issue_urls(self, year: int) -> List[str]:
        archive_url = self.archive_url
        issue_urls: List[str] = []
        seen_urls: set[str] = set()
        found_requested_year = False

        for _ in range(self.max_archive_pages):
            resp = self._get(archive_url)
            if resp is None:
                break

            soup = BeautifulSoup(resp.text, "html.parser")
            stop_after_page = False
            for issue in soup.select(".obj_issue_summary"):
                issue_year = self._issue_year(issue)
                if issue_year == year and self._is_aaai_issue(issue):
                    href = self._issue_href(issue, archive_url)
                    if href and href not in seen_urls:
                        seen_urls.add(href)
                        issue_urls.append(href)
                    found_requested_year = True
                elif found_requested_year and issue_year is not None and issue_year < year:
                    stop_after_page = True

            if stop_after_page:
                break

            next_url = self._next_archive_url(soup, archive_url)
            if not next_url or next_url == archive_url:
                break
            archive_url = next_url

        return issue_urls

    def _papers_from_issue(self, html: str, year: int, issue_url: str) -> List[PaperMeta]:
        soup = BeautifulSoup(html, "html.parser")
        papers: List[PaperMeta] = []
        sections = soup.select(".sections .section") or soup.select(".section")
        for section in sections:
            track = self._section_title(section)
            if self._is_colocated_section(track):
                continue
            for summary in section.select(".obj_article_summary"):
                paper = self._paper_from_summary(summary, year, issue_url, track)
                if paper:
                    papers.append(paper)

        if papers:
            return papers

        if sections:
            return papers

        for summary in soup.select(".obj_article_summary"):
            paper = self._paper_from_summary(summary, year, issue_url, "AAAI")
            if paper:
                papers.append(paper)
        return papers

    def _paper_from_summary(self, summary, year: int, issue_url: str, track: str) -> Optional[PaperMeta]:
        title_anchor = summary.select_one("h3.title a[href], .title a[href]")
        if title_anchor is None:
            return None

        title = title_anchor.get_text(" ", strip=True)
        href = title_anchor.get("href")
        if not title or not href:
            return None

        detail_url = urljoin(issue_url, href)
        return PaperMeta(
            paper_id=self._paper_id_from_url(detail_url, title),
            title=title,
            conf=self.slug,
            year=year,
            category=PaperCategory(track=track or "AAAI", paper_type="conference"),
            detail_url=detail_url,
            authors=self._split_authors(self._summary_authors(summary)),
            pdf_url=self._find_pdf_link(summary, issue_url),
        )

    def _issue_year(self, issue) -> Optional[int]:
        text = issue.get_text(" ", strip=True)
        match = re.search(r"\b(?:AAAI|IAAI|EAAI)-(\d{2})\b", text, re.IGNORECASE)
        if match:
            return 2000 + int(match.group(1))
        match = re.search(r"\b(20\d{2})\b", text)
        if match:
            return int(match.group(1))
        return None

    def _is_aaai_issue(self, issue) -> bool:
        text = issue.get_text(" ", strip=True).lower()
        return "aaai-" in text or "aaai conference on artificial intelligence" in text

    def _issue_href(self, issue, base_url: str) -> Optional[str]:
        anchor = issue.select_one("h2 a.title[href], a.title[href]")
        if anchor is None:
            return None
        href = anchor.get("href")
        if not href:
            return None
        return urljoin(base_url, href)

    def _next_archive_url(self, soup: BeautifulSoup, base_url: str) -> Optional[str]:
        next_link = soup.select_one(".cmp_pagination a.next[href]")
        if next_link is None:
            return None
        href = next_link.get("href")
        if not href:
            return None
        return urljoin(base_url, href)

    def _section_title(self, section) -> str:
        heading = section.find(["h2", "h3", "h4"])
        if heading is None:
            return "AAAI"
        return heading.get_text(" ", strip=True) or "AAAI"

    def _is_colocated_section(self, track: str) -> bool:
        normalized = track.strip().lower()
        return normalized.startswith("iaai") or normalized.startswith("eaai")

    def _summary_authors(self, summary) -> str:
        node = summary.select_one(".meta .authors, .authors")
        if node is None:
            return ""
        return node.get_text(" ", strip=True)

    def _split_authors(self, text: str) -> List[str]:
        if not text:
            return []
        return [part.strip() for part in text.split(",") if part.strip()]

    def _paper_id_from_url(self, url: str, title: str) -> str:
        match = re.search(r"/article/view/(\d+)", url)
        if match:
            return match.group(1)
        basename = url.rstrip("/").split("/")[-1]
        if basename:
            return basename
        return hashlib.md5(title.encode("utf-8")).hexdigest()

    def _find_pdf_link(self, scope, base_url: str) -> Optional[str]:
        for anchor in scope.select("a[href]"):
            href = anchor.get("href")
            if not href:
                continue
            text = anchor.get_text(" ", strip=True).lower()
            classes = {str(class_name).lower() for class_name in anchor.get("class", [])}
            if text == "pdf" or "pdf" in classes:
                return urljoin(base_url, href)
        return None

    def _find_bibtex_url(self, soup: BeautifulSoup, base_url: str) -> Optional[str]:
        for anchor in soup.select("a[href]"):
            href = anchor.get("href")
            if not href:
                continue
            text = anchor.get_text(" ", strip=True).lower()
            if "bibtex" in text or "download/bibtex" in href.lower():
                return urljoin(base_url, href)
        return None

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
            content = tag.get("content")
            if content:
                values.append(str(content).strip())
        return [value for value in values if value]

    def _detail_title(self, soup: BeautifulSoup) -> Optional[str]:
        title = soup.select_one("h1.page_title")
        if title is None:
            return None
        return title.get_text(" ", strip=True) or None

    def _detail_authors(self, soup: BeautifulSoup) -> List[str]:
        authors: List[str] = []
        for node in soup.select("section.authors span.name, section.item.authors span.name"):
            text = node.get_text(" ", strip=True)
            if text:
                authors.append(text)
        return authors

    def _detail_abstract(self, soup: BeautifulSoup) -> Optional[str]:
        abstract = soup.select_one("section.item.abstract")
        if abstract is None:
            return None
        heading = abstract.find(["h2", "h3", "h4"])
        if heading:
            heading.extract()
        return abstract.get_text(" ", strip=True) or None

    def _detail_keywords(self, soup: BeautifulSoup) -> List[str]:
        node = soup.select_one("section.item.keywords .value, section.item.keywords")
        if node is None:
            return []
        heading = node.find(["h2", "h3", "h4"])
        if heading:
            heading.extract()
        text = node.get_text(" ", strip=True)
        if not text:
            return []
        return [part.strip() for part in re.split(r"[,;]", text) if part.strip()]
