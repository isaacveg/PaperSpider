# Copyright 2026 Isaacveg
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#     http://www.apache.org/licenses/LICENSE-2.0

from __future__ import annotations

import unittest
from unittest.mock import patch

from paper_spider.conferences.icml import IcmlConference
from paper_spider.models import PaperMeta


class _FakeResponse:
    def __init__(self, text: str, status_code: int = 200) -> None:
        self.text = text
        self.status_code = status_code
        self.encoding = "utf-8"
        self.content = text.encode("utf-8")


class IcmlConferenceTests(unittest.TestCase):
    def test_list_papers_parses_volume_page(self) -> None:
        conf = IcmlConference()
        home_html = """
        <ul>
          <li><a href=\"/v999/\">Volume 999</a> Proceedings of ICML 2024</li>
        </ul>
        """
        volume_html = """
        <div class=\"paper\">
          <p class=\"title\">A Paper Title</p>
          <p class=\"authors\">Alice, Bob</p>
          <p>
            <a href=\"/v999/paper24a.html\">abs</a>
            <a href=\"/v999/paper24a/paper24a.pdf\">Download PDF</a>
          </p>
        </div>
        """

        def fake_get(url: str, binary: bool = False):
            if url == "https://proceedings.mlr.press/":
                return _FakeResponse(home_html)
            if url == "https://proceedings.mlr.press/v999/":
                return _FakeResponse(volume_html)
            return None

        with patch.object(conf, "_get", side_effect=fake_get):
            papers = conf.list_papers(2024)

        self.assertEqual(1, len(papers))
        self.assertEqual("A Paper Title", papers[0].title)
        self.assertEqual(["Alice", "Bob"], papers[0].authors)
        self.assertEqual("https://proceedings.mlr.press/v999/paper24a.html", papers[0].detail_url)
        self.assertEqual("https://proceedings.mlr.press/v999/paper24a/paper24a.pdf", papers[0].pdf_url)

    def test_fetch_details_extracts_abstract_authors_and_bibtex(self) -> None:
        conf = IcmlConference()
        detail_html = """
        <h1>A Paper Title</h1>
        <p>Alice, Bob</p>
        <h2>Abstract</h2>
        <p>This is the abstract text.</p>
        <h2>Citation</h2>
        <pre>@InProceedings{pmlr-v999-paper24a, title={A Paper Title}}</pre>
        <a href=\"/v999/paper24a/paper24a.pdf\">Download PDF</a>
        """

        with patch.object(conf, "_get", return_value=_FakeResponse(detail_html)):
            paper = PaperMeta(
                paper_id="paper24a",
                title="A Paper Title",
                conf="icml",
                year=2024,
                detail_url="https://proceedings.mlr.press/v999/paper24a.html",
            )
            updated = conf.fetch_details(paper)

        self.assertEqual("This is the abstract text.", updated.abstract)
        self.assertEqual(["Alice", "Bob"], updated.authors)
        self.assertIn("@InProceedings", updated.bibtex or "")
        self.assertEqual(
            "https://proceedings.mlr.press/v999/paper24a/paper24a.pdf",
            updated.pdf_url,
        )


if __name__ == "__main__":
    unittest.main()
