# Copyright 2026 Isaacveg
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#     http://www.apache.org/licenses/LICENSE-2.0

from __future__ import annotations

import unittest
from unittest.mock import patch

from paper_spider.conferences.iclr import IclrConference
from paper_spider.models import PaperMeta


class _FakeResponse:
    def __init__(self, text: str) -> None:
        self.text = text
        self.status_code = 200
        self.encoding = "utf-8"


class IclrConferenceTests(unittest.TestCase):
    def test_list_papers_prefers_accepted_notes(self) -> None:
        conf = IclrConference()
        notes = [
            {
                "id": "n1",
                "forum": "n1",
                "content": {
                    "title": "Accepted Paper",
                    "abstract": "abstract",
                    "authors": ["Alice"],
                    "venue": "ICLR 2024 Conference",
                },
            },
            {
                "id": "n2",
                "forum": "n2",
                "content": {
                    "title": "Rejected Paper",
                    "abstract": "abstract",
                    "authors": ["Bob"],
                    "venue": "Submitted to ICLR 2024",
                },
            },
        ]

        with patch.object(conf, "_iter_notes_for_invitation", return_value=iter(notes)):
            papers = conf.list_papers(2024)

        self.assertEqual(1, len(papers))
        self.assertEqual("Accepted Paper", papers[0].title)
        self.assertEqual("n1", papers[0].paper_id)

    def test_list_papers_fallbacks_to_all_notes_when_acceptance_not_detected(self) -> None:
        conf = IclrConference()
        notes = [
            {
                "id": "n1",
                "forum": "n1",
                "content": {
                    "title": "Paper One",
                    "abstract": "a",
                    "authors": ["Alice"],
                },
            },
            {
                "id": "n2",
                "forum": "n2",
                "content": {
                    "title": "Paper Two",
                    "abstract": "b",
                    "authors": ["Bob"],
                },
            },
        ]

        with patch.object(conf, "_iter_notes_for_invitation", return_value=iter(notes)):
            papers = conf.list_papers(2024)

        self.assertEqual(2, len(papers))

    def test_list_papers_uses_venue_fallback_when_invitation_returns_empty(self) -> None:
        conf = IclrConference()
        venue_note = {
            "id": "n1",
            "forum": "n1",
            "content": {
                "title": "Venue Fallback Paper",
                "abstract": "a",
                "authors": ["Alice"],
                "venue": "ICLR 2025 Conference",
            },
        }

        def fake_iter(base_params):
            if "content.venue" in base_params:
                return iter([venue_note])
            return iter([])

        with patch.object(conf, "_iter_notes_for_invitation", return_value=iter([])), patch.object(
            conf,
            "_iter_notes",
            side_effect=fake_iter,
        ):
            papers = conf.list_papers(2025)

        self.assertEqual(1, len(papers))
        self.assertEqual("Venue Fallback Paper", papers[0].title)

    def test_list_papers_dedupes_notes_from_multiple_fallback_paths(self) -> None:
        conf = IclrConference()
        note = {
            "id": "n1",
            "forum": "n1",
            "content": {
                "title": "Duplicate Paper",
                "abstract": "a",
                "authors": ["Alice"],
                "venue": "ICLR 2025 Conference",
            },
        }

        def fake_iter(base_params):
            if "content.venueid" in base_params:
                return iter([note])
            if "content.venue" in base_params:
                return iter([note])
            return iter([])

        with patch.object(conf, "_iter_notes_for_invitation", return_value=iter([])), patch.object(
            conf,
            "_iter_notes",
            side_effect=fake_iter,
        ):
            papers = conf.list_papers(2025)

        self.assertEqual(1, len(papers))
        self.assertEqual("n1", papers[0].paper_id)

    def test_fetch_details_updates_fields_and_bibtex(self) -> None:
        conf = IclrConference()
        note = {
            "id": "n1",
            "forum": "n1",
            "content": {
                "title": "Updated Title",
                "abstract": "Updated Abstract",
                "authors": ["Alice", "Bob"],
                "keywords": ["llm"],
                "pdf": "/pdf?id=n1",
            },
        }

        with patch.object(conf, "_fetch_single_note", return_value=note), patch.object(
            conf,
            "_fetch_citation",
            return_value="@inproceedings{n1,title={Updated Title}}",
        ):
            paper = PaperMeta(
                paper_id="n1",
                title="Old",
                conf="iclr",
                year=2024,
                detail_url="https://openreview.net/forum?id=n1",
            )
            updated = conf.fetch_details(paper)

        self.assertEqual("Updated Title", updated.title)
        self.assertEqual("Updated Abstract", updated.abstract)
        self.assertEqual(["Alice", "Bob"], updated.authors)
        self.assertEqual(["llm"], updated.keywords)
        self.assertEqual("https://openreview.net/pdf?id=n1", updated.pdf_url)
        self.assertIn("@inproceedings", updated.bibtex or "")

    def test_fetch_bibtex_uses_citation_endpoint(self) -> None:
        conf = IclrConference()
        with patch.object(conf, "_get", return_value=_FakeResponse("@inproceedings{n1}")):
            paper = PaperMeta(paper_id="n1", title="t", conf="iclr", year=2024)
            bibtex = conf.fetch_bibtex(paper)
        self.assertIn("@inproceedings", bibtex)


if __name__ == "__main__":
    unittest.main()
