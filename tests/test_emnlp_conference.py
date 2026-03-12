# Copyright 2026 Isaacveg
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#     http://www.apache.org/licenses/LICENSE-2.0

from __future__ import annotations

import unittest
from unittest.mock import patch

from paper_spider.conferences.emnlp import EmnlpConference
from paper_spider.models import PaperMeta


class _FakeResponse:
    def __init__(self, text: str, content: bytes | None = None) -> None:
        self.text = text
        self.content = content if content is not None else text.encode("utf-8")
        self.status_code = 200
        self.encoding = "utf-8"


class EmnlpConferenceTests(unittest.TestCase):
    def test_list_papers_parses_volume_page_and_skips_proceedings_entry(self) -> None:
        conf = EmnlpConference()
        html = """
        <html><body>
          <div class="d-sm-flex align-items-stretch mb-3">
            <div class="d-block me-2 list-button-row">
              <a href="/2024.emnlp-main.0.bib">bib</a>
            </div>
            <span class="d-block">
              <strong><a class="align-middle" href="/2024.emnlp-main.0/">Proceedings of the 2024 Conference on Empirical Methods in Natural Language Processing</a></strong>
            </span>
          </div>
          <div class="d-sm-flex align-items-stretch mb-3">
            <div class="d-block me-2 list-button-row">
              <a href="https://aclanthology.org/2024.emnlp-main.1.pdf">pdf</a>
              <a href="/2024.emnlp-main.1.bib">bib</a>
              <a role="button">abs</a>
            </div>
            <span class="d-block">
              <strong><a class="align-middle" href="/2024.emnlp-main.1/">Paper One</a></strong><br />
              <a href="/people/alice/">Alice</a> | <a href="/people/bob/">Bob</a>
            </span>
          </div>
          <div class="card bg-light mb-2 mb-lg-3 collapse abstract-collapse">
            <div class="card-body p-3 small">Abstract One</div>
          </div>
        </body></html>
        """

        with patch.object(conf, "_get", return_value=_FakeResponse(html)):
            papers = conf.list_papers(2024)

        self.assertEqual(1, len(papers))
        self.assertEqual("2024.emnlp-main.1", papers[0].paper_id)
        self.assertEqual("Paper One", papers[0].title)
        self.assertEqual("main", papers[0].track)
        self.assertEqual("conference", papers[0].paper_type)
        self.assertEqual(["Alice", "Bob"], papers[0].authors)
        self.assertEqual("Abstract One", papers[0].abstract)
        self.assertEqual("https://aclanthology.org/2024.emnlp-main.1.bib", papers[0].bibtex_url)

    def test_fetch_details_updates_metadata(self) -> None:
        conf = EmnlpConference()
        html = """
        <html><head>
          <meta name="citation_title" content="Updated Title" />
          <meta name="citation_author" content="Alice" />
          <meta name="citation_author" content="Bob" />
          <meta name="citation_pdf_url" content="https://aclanthology.org/2024.emnlp-main.1.pdf" />
        </head><body>
          <div class="card-body acl-abstract"><h5>Abstract</h5><span>Updated abstract</span></div>
        </body></html>
        """

        with patch.object(conf, "_get", return_value=_FakeResponse(html)):
            paper = PaperMeta(
                paper_id="2024.emnlp-main.1",
                title="Old",
                conf="emnlp",
                year=2024,
                detail_url="https://aclanthology.org/2024.emnlp-main.1/",
            )
            updated = conf.fetch_details(paper)

        self.assertEqual("Updated Title", updated.title)
        self.assertEqual(["Alice", "Bob"], updated.authors)
        self.assertEqual("Updated abstract", updated.abstract)
        self.assertEqual("https://aclanthology.org/2024.emnlp-main.1.pdf", updated.pdf_url)
        self.assertEqual("https://aclanthology.org/2024.emnlp-main.1.bib", updated.bibtex_url)

    def test_fetch_bibtex_downloads_from_acl_endpoint(self) -> None:
        conf = EmnlpConference()
        with patch.object(conf, "_get", return_value=_FakeResponse("@inproceedings{paper}")):
            paper = PaperMeta(
                paper_id="2024.emnlp-main.1",
                title="Paper One",
                conf="emnlp",
                year=2024,
            )
            bibtex = conf.fetch_bibtex(paper)

        self.assertIn("@inproceedings", bibtex)


if __name__ == "__main__":
    unittest.main()
