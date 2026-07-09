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
        paper.abstract = "Updated abstract"
        paper.authors = ["Alice"]
        paper.keywords = ["systems"]
        paper.pdf_url = "https://example.com/paper.pdf"
        paper.bibtex = "@inproceedings{paper1}"
        return paper

    def fetch_pdf(self, paper: PaperMeta) -> bytes:
        return b"%PDF-1.7"

    def fetch_bibtex(self, paper: PaperMeta) -> str:
        return "@inproceedings{paper1}"


class WorkspaceServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.storage = PaperStorage(self.temp_dir.name, "iclr", 2025)
        self.storage.upsert_papers(
            [PaperMeta(paper_id="paper-1", title="Paper One", conf="iclr", year=2025)]
        )
        self.service = WorkspaceService()
        self.conf = _FakeConference()

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_download_abstracts_updates_storage_metadata(self) -> None:
        rows = self.storage.list_papers()

        count = self.service.download_abstracts(
            self.conf,
            self.storage,
            rows,
            cancelled=lambda: False,
        )

        refreshed = self.storage.list_papers()[0]
        self.assertEqual(1, count)
        self.assertEqual("Updated abstract", refreshed["abstract"])
        self.assertEqual(["Alice"], refreshed["authors_list"])
        self.assertEqual(["systems"], refreshed["keywords_list"])
        self.assertEqual("https://example.com/paper.pdf", refreshed["pdf_url"])

    def test_download_pdfs_writes_artifact_and_marks_storage(self) -> None:
        rows = self.storage.list_papers()

        count = self.service.download_pdfs(
            self.conf,
            self.storage,
            rows,
            cancelled=lambda: False,
        )

        refreshed = self.storage.list_papers()[0]
        self.assertEqual(1, count)
        self.assertEqual(1, refreshed["pdf_status"])
        self.assertTrue(os.path.exists(refreshed["pdf_path"]))

    def test_export_bibtex_writes_artifact_and_marks_storage(self) -> None:
        rows = self.storage.list_papers()

        count = self.service.export_bibtex(self.conf, self.storage, rows)

        refreshed = self.storage.list_papers()[0]
        self.assertEqual(1, count)
        self.assertTrue(os.path.exists(refreshed["bib_path"]))
        self.assertIn("@inproceedings", refreshed["bibtex"])


if __name__ == "__main__":
    unittest.main()
