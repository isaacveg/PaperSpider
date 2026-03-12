# Copyright 2026 Isaacveg
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#     http://www.apache.org/licenses/LICENSE-2.0

from __future__ import annotations

import os
import tempfile
import unittest

from paper_spider.models import PaperMeta
from paper_spider.storage import PaperStorage


class PaperStorageTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.storage = PaperStorage(self.temp_dir.name, "iclr", 2025)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_upsert_preserves_existing_metadata_when_new_listing_is_sparse(self) -> None:
        self.storage.upsert_papers(
            [
                PaperMeta(
                    paper_id="paper-1",
                    title="Paper One",
                    conf="iclr",
                    year=2025,
                    authors=["Alice"],
                    abstract="Original abstract",
                    keywords=["systems"],
                )
            ]
        )

        self.storage.upsert_papers(
            [
                PaperMeta(
                    paper_id="paper-1",
                    title="Paper One",
                    conf="iclr",
                    year=2025,
                    authors=[],
                    abstract=None,
                    keywords=[],
                )
            ]
        )

        row = self.storage.list_papers()[0]
        self.assertEqual("main", row["track"])
        self.assertEqual("conference", row["paper_type"])
        self.assertEqual("main / conference", row["category_text"])
        self.assertEqual(["Alice"], row["authors_list"])
        self.assertEqual(["systems"], row["keywords_list"])
        self.assertEqual("Original abstract", row["abstract"])

    def test_update_details_keeps_existing_values_when_fetch_returns_empty_fields(self) -> None:
        self.storage.upsert_papers(
            [
                PaperMeta(
                    paper_id="paper-1",
                    title="Paper One",
                    conf="iclr",
                    year=2025,
                    authors=["Alice"],
                    abstract="Original abstract",
                    keywords=["systems"],
                    pdf_url="https://example.com/original.pdf",
                )
            ]
        )

        self.storage.update_details(
            paper_id="paper-1",
            abstract=None,
            authors=[],
            keywords=[],
            pdf_url="https://example.com/updated.pdf",
            bibtex_url=None,
            bibtex=None,
        )

        row = self.storage.list_papers()[0]
        self.assertEqual("Original abstract", row["abstract"])
        self.assertEqual(["Alice"], row["authors_list"])
        self.assertEqual(["systems"], row["keywords_list"])
        self.assertEqual("https://example.com/updated.pdf", row["pdf_url"])

    def test_reconcile_file_states_clears_missing_paths_and_parses_legacy_lists(self) -> None:
        self.storage.upsert_papers(
            [PaperMeta(paper_id="paper-1", title="Paper One", conf="iclr", year=2025)]
        )

        missing_pdf = os.path.join(self.storage.paths.pdf_dir, "missing.pdf")
        missing_bib = os.path.join(self.storage.paths.bib_dir, "missing.bib")
        with self.storage._connect() as conn:
            conn.execute(
                """
                UPDATE papers
                SET authors = ?,
                    keywords = ?,
                    pdf_status = 1,
                    pdf_path = ?,
                    bib_path = ?
                WHERE paper_id = ?
                """,
                ("Alice, Bob", "systems; ml", missing_pdf, missing_bib, "paper-1"),
            )

        rows = self.storage.reconcile_file_states(self.storage.list_papers())
        row = rows[0]
        self.assertEqual(["Alice", "Bob"], row["authors_list"])
        self.assertEqual(["systems", "ml"], row["keywords_list"])
        self.assertFalse(row["has_pdf"])
        self.assertFalse(row["has_bib"])
        self.assertIsNone(row["pdf_path"])
        self.assertIsNone(row["bib_path"])

        refreshed = self.storage.list_papers()[0]
        self.assertEqual(0, refreshed["pdf_status"])
        self.assertIsNone(refreshed["pdf_path"])
        self.assertIsNone(refreshed["bib_path"])


if __name__ == "__main__":
    unittest.main()
