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
from paper_spider.workspace_service import WorkspaceService


class _FakeConference:
    slug = "iclr"

    def fetch_details(self, paper: PaperMeta) -> PaperMeta:
        if paper.paper_id == "missing-abstract":
            return paper
        paper.abstract = "Updated abstract"
        paper.authors = ["Alice"]
        paper.keywords = ["systems"]
        paper.pdf_url = "https://example.com/paper.pdf"
        paper.bibtex = "@inproceedings{paper1}"
        return paper

    def fetch_pdf(self, paper: PaperMeta) -> bytes:
        if paper.paper_id == "broken-pdf":
            raise RuntimeError("PDF URL not found")
        return b"%PDF-1.7"

    def fetch_bibtex(self, paper: PaperMeta) -> str:
        return "@inproceedings{paper1}"


class WorkspaceServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.storage = PaperStorage(self.temp_dir.name, "iclr", 2025)
        self.storage.upsert_papers(
            [
                PaperMeta(paper_id="paper-1", title="Paper One", conf="iclr", year=2025),
                PaperMeta(paper_id="broken-pdf", title="Broken PDF", conf="iclr", year=2025),
                PaperMeta(
                    paper_id="missing-abstract",
                    title="Missing Abstract",
                    conf="iclr",
                    year=2025,
                ),
            ]
        )
        self.service = WorkspaceService()
        self.conf = _FakeConference()

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_download_abstracts_updates_storage_metadata(self) -> None:
        rows = self.storage.list_papers()
        row = next(row for row in rows if row["paper_id"] == "paper-1")

        result = self.service.download_abstracts(
            self.conf,
            self.storage,
            [row],
            cancelled=lambda: False,
        )

        refreshed = self.storage.get_paper("paper-1")
        self.assertIsNotNone(refreshed)
        self.assertEqual(1, result.succeeded)
        self.assertEqual(["paper-1"], [row["paper_id"] for row in result.updated_rows])
        self.assertEqual("Updated abstract", refreshed["abstract"])
        self.assertEqual(["Alice"], refreshed["authors_list"])
        self.assertEqual(["systems"], refreshed["keywords_list"])
        self.assertEqual("https://example.com/paper.pdf", refreshed["pdf_url"])

    def test_download_abstracts_reports_missing_abstract_without_counting_success(self) -> None:
        rows = self.storage.list_papers()
        row = next(row for row in rows if row["paper_id"] == "missing-abstract")

        result = self.service.download_abstracts(
            self.conf,
            self.storage,
            [row],
            cancelled=lambda: False,
        )

        self.assertEqual(0, result.succeeded)
        self.assertEqual(1, len(result.failures))
        self.assertIn("Abstract not found", result.failures[0].message)

    def test_download_pdfs_writes_artifact_and_marks_storage(self) -> None:
        rows = self.storage.list_papers()
        row = next(row for row in rows if row["paper_id"] == "paper-1")

        result = self.service.download_pdfs(
            self.conf,
            self.storage,
            [row],
            cancelled=lambda: False,
        )

        refreshed = self.storage.get_paper("paper-1")
        self.assertIsNotNone(refreshed)
        self.assertEqual(1, result.succeeded)
        self.assertEqual(["paper-1"], [row["paper_id"] for row in result.updated_rows])
        self.assertEqual(1, refreshed["pdf_status"])
        self.assertTrue(os.path.exists(refreshed["pdf_path"]))

    def test_download_pdfs_keeps_going_when_one_paper_fails(self) -> None:
        rows = self.storage.list_papers()
        selected = [
            next(row for row in rows if row["paper_id"] == "broken-pdf"),
            next(row for row in rows if row["paper_id"] == "paper-1"),
        ]

        result = self.service.download_pdfs(
            self.conf,
            self.storage,
            selected,
            cancelled=lambda: False,
        )

        self.assertEqual(1, result.succeeded)
        self.assertEqual(1, len(result.failures))
        self.assertEqual("broken-pdf", result.failures[0].paper_id)
        self.assertTrue(self.storage.get_paper("paper-1")["has_pdf"])

    def test_download_pdfs_marks_cancelled_before_next_paper(self) -> None:
        rows = self.storage.list_papers()
        selected = [
            next(row for row in rows if row["paper_id"] == "paper-1"),
            next(row for row in rows if row["paper_id"] == "broken-pdf"),
        ]
        calls = {"count": 0}

        def cancelled() -> bool:
            calls["count"] += 1
            return calls["count"] > 1

        result = self.service.download_pdfs(
            self.conf,
            self.storage,
            selected,
            cancelled=cancelled,
        )

        self.assertTrue(result.cancelled)
        self.assertEqual(1, result.succeeded)

    def test_export_bibtex_writes_artifact_and_marks_storage(self) -> None:
        rows = self.storage.list_papers()
        row = next(row for row in rows if row["paper_id"] == "paper-1")

        count = self.service.export_bibtex(self.conf, self.storage, [row])

        refreshed = self.storage.get_paper("paper-1")
        self.assertIsNotNone(refreshed)
        self.assertEqual(1, count)
        self.assertTrue(os.path.exists(refreshed["bib_path"]))
        self.assertIn("@inproceedings", refreshed["bibtex"])


if __name__ == "__main__":
    unittest.main()
