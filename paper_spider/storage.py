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
from typing import Iterable, List, Optional

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
                    json.dumps(data["authors"], ensure_ascii=True),
                    data["abstract"],
                    json.dumps(data["keywords"], ensure_ascii=True),
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
                    authors=excluded.authors,
                    abstract=COALESCE(excluded.abstract, papers.abstract),
                    keywords=excluded.keywords,
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
        results = []
        for row in rows:
            results.append(dict(row))
        return results

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
        now = str(int(time.time()))
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE papers
                SET abstract = ?,
                    authors = ?,
                    keywords = ?,
                    pdf_url = COALESCE(?, pdf_url),
                    bibtex_url = COALESCE(?, bibtex_url),
                    bibtex = COALESCE(?, bibtex),
                    abstract_status = CASE WHEN ? IS NULL THEN abstract_status ELSE 1 END,
                    updated_at = ?
                WHERE paper_id = ?
                """,
                (
                    abstract,
                    json.dumps(authors, ensure_ascii=True),
                    json.dumps(keywords, ensure_ascii=True),
                    pdf_url,
                    bibtex_url,
                    bibtex,
                    abstract,
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
