# Copyright 2026 Isaacveg
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#     http://www.apache.org/licenses/LICENSE-2.0

from __future__ import annotations

import json
import os
import sqlite3
import time
from dataclasses import dataclass
from typing import Any, Iterable, List, Optional

from .models import PaperMeta


@dataclass
class StoragePaths:
    root_dir: str
    db_path: str
    pdf_dir: str
    bib_dir: str


class PaperStorage:
    def __init__(self, base_dir: str, conf_slug: str, year: int) -> None:
        self.base_dir = base_dir
        self.conf_slug = conf_slug
        self.year = year
        self.paths = self._init_paths()
        self._init_db()

    def _init_paths(self) -> StoragePaths:
        root_dir = os.path.join(self.base_dir, self.conf_slug, str(self.year))
        pdf_dir = os.path.join(root_dir, "pdf")
        bib_dir = os.path.join(root_dir, "bib")
        os.makedirs(pdf_dir, exist_ok=True)
        os.makedirs(bib_dir, exist_ok=True)
        db_path = os.path.join(root_dir, "papers.sqlite")
        return StoragePaths(root_dir=root_dir, db_path=db_path, pdf_dir=pdf_dir, bib_dir=bib_dir)

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.paths.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS papers (
                    paper_id TEXT PRIMARY KEY,
                    conf TEXT NOT NULL,
                    year INTEGER NOT NULL,
                    title TEXT NOT NULL,
                    detail_url TEXT,
                    authors TEXT,
                    abstract TEXT,
                    keywords TEXT,
                    pdf_url TEXT,
                    pdf_path TEXT,
                    bibtex_url TEXT,
                    bibtex TEXT,
                    bib_path TEXT,
                    abstract_status INTEGER NOT NULL DEFAULT 0,
                    pdf_status INTEGER NOT NULL DEFAULT 0,
                    updated_at TEXT NOT NULL
                )
                """
            )
            self._ensure_column(conn, "bib_path", "TEXT")
            self._ensure_column(conn, "pdf_path", "TEXT")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_conf_year ON papers(conf, year)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_title ON papers(title)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_authors ON papers(authors)")

    def _ensure_column(self, conn: sqlite3.Connection, name: str, definition: str) -> None:
        columns = [row["name"] for row in conn.execute("PRAGMA table_info(papers)").fetchall()]
        if name not in columns:
            conn.execute(f"ALTER TABLE papers ADD COLUMN {name} {definition}")

    def _serialize_list(self, values: Iterable[Any]) -> str:
        normalized = [str(value).strip() for value in values if str(value).strip()]
        return json.dumps(normalized, ensure_ascii=True)

    def _deserialize_list(self, raw: Any) -> List[str]:
        if raw is None:
            return []
        if isinstance(raw, list):
            return [str(item).strip() for item in raw if str(item).strip()]
        if isinstance(raw, str):
            text = raw.strip()
            if not text:
                return []
            try:
                parsed = json.loads(text)
            except ValueError:
                parsed = None
            if isinstance(parsed, list):
                return [str(item).strip() for item in parsed if str(item).strip()]
            parts = [part.strip() for part in text.replace(";", ",").split(",")]
            return [part for part in parts if part]
        return [str(raw).strip()] if str(raw).strip() else []

    def _normalize_row(self, row: dict) -> dict:
        authors_list = self._deserialize_list(row.get("authors"))
        keywords_list = self._deserialize_list(row.get("keywords"))
        row["authors_list"] = authors_list
        row["keywords_list"] = keywords_list
        row["authors_text"] = ", ".join(authors_list)
        row["keywords_text"] = ", ".join(keywords_list)
        row["has_pdf"] = bool(row.get("pdf_status") and row.get("pdf_path"))
        row["has_bib"] = bool(row.get("bib_path"))
        return row

    def reconcile_file_states(self, rows: Iterable[dict]) -> List[dict]:
        normalized_rows = [self._normalize_row(dict(row)) for row in rows]
        missing_pdf_ids: List[str] = []
        missing_bib_ids: List[str] = []

        for row in normalized_rows:
            pdf_path = row.get("pdf_path")
            pdf_available = bool(row.get("pdf_status")) and bool(pdf_path) and os.path.exists(pdf_path)
            if row.get("pdf_status") and not pdf_available:
                row["pdf_status"] = 0
                row["pdf_path"] = None
                missing_pdf_ids.append(row["paper_id"])
            row["has_pdf"] = pdf_available

            bib_path = row.get("bib_path")
            bib_available = bool(bib_path) and os.path.exists(bib_path)
            if bib_path and not bib_available:
                row["bib_path"] = None
                missing_bib_ids.append(row["paper_id"])
            row["has_bib"] = bib_available

        if missing_pdf_ids or missing_bib_ids:
            now = str(int(time.time()))
            with self._connect() as conn:
                if missing_pdf_ids:
                    conn.executemany(
                        """
                        UPDATE papers
                        SET pdf_status = 0,
                            pdf_path = NULL,
                            updated_at = ?
                        WHERE paper_id = ?
                        """,
                        [(now, paper_id) for paper_id in missing_pdf_ids],
                    )
                if missing_bib_ids:
                    conn.executemany(
                        """
                        UPDATE papers
                        SET bib_path = NULL,
                            updated_at = ?
                        WHERE paper_id = ?
                        """,
                        [(now, paper_id) for paper_id in missing_bib_ids],
                    )

        return normalized_rows

    def upsert_papers(self, papers: Iterable[PaperMeta]) -> int:
        now = str(int(time.time()))
        rows = []
        for paper in papers:
            data = paper.to_row()
            rows.append(
                (
                    data["paper_id"],
                    data["conf"],
                    data["year"],
                    data["title"],
                    data["detail_url"],
                    self._serialize_list(data["authors"]),
                    data["abstract"],
                    self._serialize_list(data["keywords"]),
                    data["pdf_url"],
                    None,
                    data["bibtex_url"],
                    data["bibtex"],
                    1 if data["abstract"] else 0,
                    0,
                    now,
                )
            )
        if not rows:
            return 0
        with self._connect() as conn:
            conn.executemany(
                """
                INSERT INTO papers (
                    paper_id, conf, year, title, detail_url, authors, abstract, keywords,
                    pdf_url, pdf_path, bibtex_url, bibtex, abstract_status, pdf_status, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(paper_id) DO UPDATE SET
                    title=excluded.title,
                    detail_url=excluded.detail_url,
                    authors=CASE
                        WHEN excluded.authors = '[]' THEN papers.authors
                        ELSE excluded.authors
                    END,
                    abstract=COALESCE(excluded.abstract, papers.abstract),
                    keywords=CASE
                        WHEN excluded.keywords = '[]' THEN papers.keywords
                        ELSE excluded.keywords
                    END,
                    pdf_url=COALESCE(excluded.pdf_url, papers.pdf_url),
                    bibtex_url=COALESCE(excluded.bibtex_url, papers.bibtex_url),
                    bibtex=COALESCE(excluded.bibtex, papers.bibtex),
                    abstract_status=MAX(excluded.abstract_status, papers.abstract_status),
                    updated_at=excluded.updated_at
                """,
                rows,
            )
        return len(rows)

    def list_papers(
        self,
        title_query: Optional[str] = None,
        author_query: Optional[str] = None,
        keyword_query: Optional[str] = None,
    ) -> List[dict]:
        clauses = ["conf = ?", "year = ?"]
        params: List[object] = [self.conf_slug, self.year]

        if title_query:
            clauses.append("title LIKE ?")
            params.append(f"%{title_query}%")
        if author_query:
            clauses.append("authors LIKE ?")
            params.append(f"%{author_query}%")
        if keyword_query:
            clauses.append("(keywords LIKE ? OR abstract LIKE ?)")
            params.append(f"%{keyword_query}%")
            params.append(f"%{keyword_query}%")

        where_sql = " AND ".join(clauses)
        sql = f"SELECT * FROM papers WHERE {where_sql} ORDER BY title"
        with self._connect() as conn:
            rows = conn.execute(sql, params).fetchall()
        return [self._normalize_row(dict(row)) for row in rows]

    def count_papers(self) -> int:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT COUNT(*) AS total FROM papers WHERE conf = ? AND year = ?",
                (self.conf_slug, self.year),
            ).fetchone()
        return int(row["total"]) if row else 0

    def update_details(
        self,
        paper_id: str,
        abstract: Optional[str],
        authors: List[str],
        keywords: List[str],
        pdf_url: Optional[str],
        bibtex_url: Optional[str],
        bibtex: Optional[str],
    ) -> None:
        abstract_value = abstract.strip() if isinstance(abstract, str) and abstract.strip() else None
        authors_value = self._serialize_list(authors) if authors else None
        keywords_value = self._serialize_list(keywords) if keywords else None
        now = str(int(time.time()))
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE papers
                SET abstract = COALESCE(?, abstract),
                    authors = COALESCE(?, authors),
                    keywords = COALESCE(?, keywords),
                    pdf_url = COALESCE(?, pdf_url),
                    bibtex_url = COALESCE(?, bibtex_url),
                    bibtex = COALESCE(?, bibtex),
                    abstract_status = CASE WHEN ? IS NULL THEN abstract_status ELSE 1 END,
                    updated_at = ?
                WHERE paper_id = ?
                """,
                (
                    abstract_value,
                    authors_value,
                    keywords_value,
                    pdf_url,
                    bibtex_url,
                    bibtex,
                    abstract_value,
                    now,
                    paper_id,
                ),
            )

    def mark_pdf_downloaded(self, paper_id: str, pdf_path: str) -> None:
        now = str(int(time.time()))
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE papers
                SET pdf_status = 1,
                    pdf_path = ?,
                    updated_at = ?
                WHERE paper_id = ?
                """,
                (pdf_path, now, paper_id),
            )

    def mark_pdf_missing(self, paper_id: str) -> None:
        now = str(int(time.time()))
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE papers
                SET pdf_status = 0,
                    pdf_path = NULL,
                    updated_at = ?
                WHERE paper_id = ?
                """,
                (now, paper_id),
            )

    def mark_bib_exported(self, paper_id: str, bibtex: str, bib_path: str) -> None:
        now = str(int(time.time()))
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE papers
                SET bibtex = ?, bib_path = ?, updated_at = ?
                WHERE paper_id = ?
                """,
                (bibtex, bib_path, now, paper_id),
            )

    def mark_bib_missing(self, paper_id: str) -> None:
        now = str(int(time.time()))
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE papers
                SET bib_path = NULL, updated_at = ?
                WHERE paper_id = ?
                """,
                (now, paper_id),
            )
