# Copyright 2026 Isaacveg
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#     http://www.apache.org/licenses/LICENSE-2.0

from __future__ import annotations

import hashlib
import json
import re
import time
from typing import List, Optional
from urllib.parse import quote, urljoin

import requests
from bs4 import BeautifulSoup

from ..models import PaperCategory, PaperMeta
from .base import ConferenceBase


class RequestsConferenceBase(ConferenceBase):
    web_base: str

    def __init__(self) -> None:
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "PaperSpider/0.1 (+https://localhost)"})
        self.request_delay = 0.1

    def _request(
        self,
        url: str,
        *,
        binary: bool = False,
        headers: Optional[dict[str, str]] = None,
    ) -> Optional[requests.Response]:
        if self.request_delay > 0:
            time.sleep(self.request_delay)
        try:
            resp = self.session.get(url, timeout=30, headers=headers)
        except requests.RequestException:
            return None
        if resp.status_code != 200:
            return None
        if binary:
            return resp
        resp.encoding = resp.encoding or "utf-8"
        return resp

    def _get(self, url: str, binary: bool = False) -> Optional[requests.Response]:
        return self._request(url, binary=binary)


class AclAnthologyFamilyBase(RequestsConferenceBase):
    name: str
    slug: str
    volume_suffixes: tuple[str, ...]

    def __init__(self) -> None:
        self.web_base = "https://aclanthology.org"
        super().__init__()

    def list_papers(self, year: int) -> List[PaperMeta]:
        papers: List[PaperMeta] = []
        seen_ids: set[str] = set()
        for volume_suffix in self._volume_suffixes():
            volume_url = f"{self.web_base}/volumes/{year}.{volume_suffix}/"
            resp = self._get(volume_url)
            if resp is None:
                continue

            soup = BeautifulSoup(resp.text, "html.parser")
            for block in soup.select("div.d-sm-flex.align-items-stretch.mb-3"):
                paper = self._paper_from_listing(block, volume_url, year, volume_suffix)
                if paper is None or paper.paper_id in seen_ids:
                    continue
                seen_ids.add(paper.paper_id)
                papers.append(paper)

        if not papers:
            raise RuntimeError(f"No {self.name} papers parsed for {year}")
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

    def _paper_from_listing(
        self,
        block,
        base_url: str,
        year: int,
        volume_suffix: str,
    ) -> Optional[PaperMeta]:
        title_anchor = block.select_one("strong a[href]")
        if title_anchor is None:
            return None
        detail_href = title_anchor.get("href")
        if not detail_href:
            return None

        detail_url = urljoin(base_url, detail_href)
        paper_id = detail_url.rstrip("/").split("/")[-1]
        if paper_id.endswith(".0") or paper_id == f"{year}.{volume_suffix}":
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
        category = self._category_for_volume_suffix(volume_suffix)

        return PaperMeta(
            paper_id=paper_id,
            title=title,
            conf=self.slug,
            year=year,
            category=category,
            detail_url=detail_url,
            authors=authors,
            abstract=abstract,
            pdf_url=pdf_url,
            bibtex_url=bibtex_url,
        )

    def _volume_suffixes(self) -> tuple[str, ...]:
        return self.volume_suffixes

    def _category_for_volume_suffix(self, volume_suffix: str) -> PaperCategory:
        if volume_suffix.endswith("-long"):
            return PaperCategory(track="main", paper_type="long")
        if volume_suffix.endswith("-short"):
            return PaperCategory(track="main", paper_type="short")
        if volume_suffix.endswith("-main"):
            return PaperCategory(track="main", paper_type="conference")
        return PaperCategory(track="main", paper_type="conference")

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


class UsenixFamilyBase(RequestsConferenceBase):
    name: str
    slug: str
    conf_prefix: str

    def __init__(self) -> None:
        self.web_base = "https://www.usenix.org"
        super().__init__()

    def list_papers(self, year: int) -> List[PaperMeta]:
        schedule_url = f"{self.web_base}/conference/{self._year_slug(year)}/technical-sessions"
        resp = self._get(schedule_url)
        if resp is None:
            raise RuntimeError(f"Unable to load {self.name} technical sessions for {year}")

        soup = BeautifulSoup(resp.text, "html.parser")
        papers: List[PaperMeta] = []
        for article in soup.select("article.node.node-paper.view-mode-schedule"):
            paper = self._paper_from_schedule(article, schedule_url, year)
            if paper:
                papers.append(paper)

        if not papers:
            raise RuntimeError(f"No {self.name} papers parsed for {year}")
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
            category=PaperCategory(track="technical", paper_type="conference"),
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
        return f"{self.conf_prefix}{year % 100:02d}"


class CvfOpenAccessFamilyBase(RequestsConferenceBase):
    name: str
    slug: str
    conf_code: str

    def __init__(self) -> None:
        self.web_base = "https://openaccess.thecvf.com"
        super().__init__()

    def list_papers(self, year: int) -> List[PaperMeta]:
        list_url = f"{self.web_base}/{self._conference_path(year)}?day=all"
        resp = self._get(list_url)
        if resp is None:
            raise RuntimeError(f"Unable to load {self.name} Open Access listing for {year}")

        soup = BeautifulSoup(resp.text, "html.parser")
        papers: List[PaperMeta] = []
        for title_node in soup.select("dt.ptitle"):
            paper = self._paper_from_listing(title_node, year, list_url)
            if paper:
                papers.append(paper)

        if not papers:
            raise RuntimeError(f"No {self.name} papers parsed for {year}")
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
        abstract = self._detail_abstract(soup)
        pdf_url = self._meta_content(soup, "citation_pdf_url")
        bibtex = self._bibtex_text(soup)

        if title:
            paper.title = title
        if authors:
            paper.authors = [self._normalize_author_name(author) for author in authors]
        if abstract:
            paper.abstract = abstract
        if pdf_url:
            paper.pdf_url = pdf_url
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
        paper = self.fetch_details(paper)
        if not paper.bibtex:
            raise RuntimeError("Bibtex not found")
        return paper.bibtex

    def _conference_path(self, year: int) -> str:
        return f"{self.conf_code}{year}"

    def _paper_from_listing(self, title_node, year: int, base_url: str) -> Optional[PaperMeta]:
        title_anchor = title_node.select_one("a[href]")
        if title_anchor is None:
            return None
        detail_href = title_anchor.get("href")
        title = title_anchor.get_text(" ", strip=True)
        if not detail_href or not title:
            return None

        detail_url = urljoin(base_url, detail_href)
        paper_id = detail_url.rstrip("/").split("/")[-1].replace("_paper.html", "")
        authors_node = title_node.find_next_sibling("dd")
        assets_node = authors_node.find_next_sibling("dd") if authors_node is not None else None

        authors = self._listing_authors(authors_node)
        pdf_url = self._find_asset_url(assets_node, "pdf", base_url)
        bibtex = self._bibtex_text(assets_node)

        return PaperMeta(
            paper_id=paper_id,
            title=title,
            conf=self.slug,
            year=year,
            category=PaperCategory(track="main", paper_type="conference"),
            detail_url=detail_url,
            authors=authors,
            pdf_url=pdf_url,
            bibtex=bibtex,
        )

    def _listing_authors(self, authors_node) -> List[str]:
        if authors_node is None:
            return []
        authors: List[str] = []
        for anchor in authors_node.select("a"):
            text = anchor.get_text(" ", strip=True)
            if text:
                authors.append(self._normalize_author_name(text))
        return authors

    def _normalize_author_name(self, author: str) -> str:
        parts = [part.strip() for part in author.split(",")]
        if len(parts) == 2:
            return f"{parts[1]} {parts[0]}".strip()
        return author.strip()

    def _find_asset_url(self, assets_node, marker: str, base_url: str) -> Optional[str]:
        if assets_node is None:
            return None
        expected = marker.strip().lower()
        for anchor in assets_node.select("a[href]"):
            href = anchor.get("href")
            text = anchor.get_text(" ", strip=True).lower()
            if not href or text != expected:
                continue
            return urljoin(base_url, href)
        return None

    def _bibtex_text(self, scope) -> Optional[str]:
        if scope is None:
            return None
        block = scope.select_one(".bibref")
        if block is None:
            return None
        text = block.get_text("\n", strip=True)
        return text or None

    def _detail_abstract(self, soup: BeautifulSoup) -> Optional[str]:
        block = soup.select_one("#abstract")
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


class SigcommProgramFamilyBase(RequestsConferenceBase):
    name: str
    slug: str
    site_slug: str

    def __init__(self) -> None:
        self.web_base = "https://conferences.sigcomm.org"
        self.crossref_base = "https://api.crossref.org/works"
        self.doi_base = "https://doi.org"
        super().__init__()

    def list_papers(self, year: int) -> List[PaperMeta]:
        list_url = self._program_url(year)
        resp = self._get(list_url)
        if resp is None:
            raise RuntimeError(f"Unable to load {self.name} proceedings page for {year}")

        soup = BeautifulSoup(resp.text, "html.parser")
        papers: List[PaperMeta] = []
        seen_ids: set[str] = set()

        for row in soup.select(".paper-table tr"):
            if self._session_name_from_row(row):
                continue

            paper = self._paper_from_program_row(row, year)
            if paper is None or paper.paper_id in seen_ids:
                continue
            seen_ids.add(paper.paper_id)
            papers.append(paper)

        if not papers:
            raise RuntimeError(f"No {self.name} papers parsed for {year}")
        return papers

    def fetch_details(self, paper: PaperMeta) -> PaperMeta:
        doi = self._paper_doi(paper)
        if not doi:
            return paper

        metadata = self._fetch_crossref_metadata(doi)
        if metadata:
            title = self._crossref_title(metadata)
            authors = self._crossref_authors(metadata)
            pdf_url = self._crossref_pdf_url(metadata)

            if title:
                paper.title = title
            if authors:
                paper.authors = authors
            if pdf_url:
                paper.pdf_url = pdf_url

        paper.detail_url = self._doi_url(doi)
        paper.bibtex_url = self._doi_url(doi)
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

        doi = self._paper_doi(paper)
        if not doi:
            paper = self.fetch_details(paper)
            doi = self._paper_doi(paper)
        if not doi:
            raise RuntimeError("Bibtex not found")

        resp = self._request(
            self._doi_url(doi),
            headers={"Accept": "application/x-bibtex"},
        )
        if resp is None:
            raise RuntimeError("Bibtex not found")

        paper.bibtex = resp.text.strip()
        paper.bibtex_url = self._doi_url(doi)
        return paper.bibtex

    def _program_url(self, year: int) -> str:
        return f"{self.web_base}/{self.site_slug}/{year}/program/papers-info/"

    def _paper_from_program_row(self, row, year: int) -> Optional[PaperMeta]:
        if row.select_one("button.paper-title") is None:
            return None

        cells = row.find_all("td")
        if not cells:
            return None

        info_cell = cells[0]
        title_node = info_cell.select_one("p span.text-color-primary")
        authors_node = info_cell.select_one("p.style_italic")
        doi_anchor = row.select_one("a[href*='doi/']")
        title = title_node.get_text(" ", strip=True) if title_node is not None else ""
        if not title:
            return None

        doi = self._extract_doi(doi_anchor.get("href") if doi_anchor is not None else None)
        abstract = self._abstract_from_row(row.find_next_sibling("tr"))
        paper_id = self._paper_id_from_doi(doi) if doi else hashlib.md5(title.encode("utf-8")).hexdigest()

        return PaperMeta(
            paper_id=paper_id,
            title=title,
            conf=self.slug,
            year=year,
            category=PaperCategory(track="technical", paper_type="conference"),
            detail_url=self._doi_url(doi) if doi else None,
            authors=self._listing_authors(authors_node.get_text(" ", strip=True) if authors_node is not None else ""),
            abstract=abstract,
            bibtex_url=self._doi_url(doi) if doi else None,
        )

    def _session_name_from_row(self, row) -> str:
        session_cell = row.select_one("td[id^='session-']")
        if session_cell is None:
            return ""
        title_node = session_cell.select_one("p span.text-color-primary")
        text = title_node.get_text(" ", strip=True) if title_node is not None else session_cell.get_text(" ", strip=True)
        if "|" in text:
            return text.split("|", 1)[1].strip()
        return text.strip()

    def _abstract_from_row(self, row) -> Optional[str]:
        if row is None or "abstract-row" not in (row.get("class") or []):
            return None
        block = row.select_one(".abstract-info-row")
        if block is None:
            block = row.select_one(".abstract")
        if block is None:
            return None
        text = block.get_text(" ", strip=True)
        text = re.sub(r"^Abstract:\s*", "", text, flags=re.IGNORECASE)
        return text or None

    def _listing_authors(self, raw: str) -> List[str]:
        if not raw:
            return []
        normalized = re.sub(r"\([^)]*\)", "", raw)
        normalized = normalized.replace(";", ",")
        parts = [part.strip(" ,") for part in normalized.split(",")]
        return [part for part in parts if part]

    def _paper_doi(self, paper: PaperMeta) -> Optional[str]:
        return (
            self._extract_doi(paper.detail_url)
            or self._extract_doi(paper.bibtex_url)
            or self._extract_doi(paper.pdf_url)
        )

    def _doi_url(self, doi: Optional[str]) -> Optional[str]:
        if not doi:
            return None
        return f"{self.doi_base}/{doi}"

    def _extract_doi(self, value: Optional[str]) -> Optional[str]:
        if not value:
            return None
        match = re.search(r"(10\.\d{4,9}/[^\s?#]+)", value)
        if match is None:
            return None
        return match.group(1).rstrip(").,;")

    def _paper_id_from_doi(self, doi: str) -> str:
        return doi.replace("/", "_")

    def _fetch_crossref_metadata(self, doi: str) -> Optional[dict]:
        encoded = quote(doi, safe="")
        resp = self._get(
            f"{self.crossref_base}/{encoded}/transform/application/vnd.citationstyles.csl+json"
        )
        if resp is None:
            return None
        try:
            payload = json.loads(resp.text)
        except ValueError:
            return None
        return payload if isinstance(payload, dict) else None

    def _crossref_title(self, metadata: dict) -> Optional[str]:
        title = metadata.get("title")
        if isinstance(title, str):
            text = title.strip()
            return text or None
        return None

    def _crossref_authors(self, metadata: dict) -> List[str]:
        authors: List[str] = []
        raw_authors = metadata.get("author")
        if not isinstance(raw_authors, list):
            return authors
        for author in raw_authors:
            if not isinstance(author, dict):
                continue
            given = str(author.get("given") or "").strip()
            family = str(author.get("family") or "").strip()
            literal = str(author.get("literal") or "").strip()
            name = " ".join(part for part in [given, family] if part).strip() or literal
            if name:
                authors.append(name)
        return authors

    def _crossref_pdf_url(self, metadata: dict) -> Optional[str]:
        links = metadata.get("link")
        if not isinstance(links, list):
            return None
        for link in links:
            if not isinstance(link, dict):
                continue
            url = str(link.get("URL") or "").strip()
            if not url:
                continue
            if "/doi/pdf/" in url or url.endswith(".pdf"):
                return url
        return None
