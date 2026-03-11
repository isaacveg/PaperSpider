# Copyright 2026 Isaacveg
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#     http://www.apache.org/licenses/LICENSE-2.0

from __future__ import annotations

import unittest
from unittest.mock import patch

from paper_spider.conferences.nsdi import NsdiConference
from paper_spider.models import PaperMeta


class _FakeResponse:
    def __init__(self, text: str, content: bytes | None = None) -> None:
        self.text = text
        self.content = content if content is not None else text.encode("utf-8")
        self.status_code = 200
        self.encoding = "utf-8"


class NsdiConferenceTests(unittest.TestCase):
    def test_list_papers_parses_schedule_entries(self) -> None:
        conf = NsdiConference()
        html = """
        <html><body>
          <article class="node node-paper view-mode-schedule">
            <h2><a href="/conference/nsdi25/presentation/du">PRED</a></h2>
            <div class="content">
              <div class="field field-name-field-paper-people-text">
                <div class="field-item odd">
                  <p>Alice, <em>Org A;</em> Bob and Carol, <em>Org B</em></p>
                </div>
              </div>
              <div class="field field-name-field-paper-description-long">
                <p>Datacenter abstract.</p>
              </div>
            </div>
          </article>
        </body></html>
        """

        with patch.object(conf, "_get", return_value=_FakeResponse(html)):
            papers = conf.list_papers(2025)

        self.assertEqual(1, len(papers))
        self.assertEqual("du", papers[0].paper_id)
        self.assertEqual("PRED", papers[0].title)
        self.assertEqual(["Alice", "Bob", "Carol"], papers[0].authors)
        self.assertEqual("Datacenter abstract.", papers[0].abstract)

    def test_fetch_details_updates_fields_and_bibtex(self) -> None:
        conf = NsdiConference()
        html = """
        <html><head>
          <meta name="citation_title" content="Updated NSDI Paper" />
          <meta name="citation_author" content="Alice" />
          <meta name="citation_author" content="Bob" />
          <meta name="citation_pdf_url" content="https://www.usenix.org/system/files/nsdi25-du.pdf" />
        </head><body>
          <div class="field field-name-field-paper-description">
            <div class="field-item odd"><p>Updated abstract.</p></div>
          </div>
          <div class="bibtex-text-entry">@inproceedings{305308,<br/>title = {Updated NSDI Paper}}</div>
          <div class="bibtex-download-link"><a href="/biblio/export/bibtex/305308">Download</a></div>
        </body></html>
        """

        with patch.object(conf, "_get", return_value=_FakeResponse(html)):
            paper = PaperMeta(
                paper_id="du",
                title="Old",
                conf="nsdi",
                year=2025,
                detail_url="https://www.usenix.org/conference/nsdi25/presentation/du",
            )
            updated = conf.fetch_details(paper)

        self.assertEqual("Updated NSDI Paper", updated.title)
        self.assertEqual(["Alice", "Bob"], updated.authors)
        self.assertEqual("Updated abstract.", updated.abstract)
        self.assertEqual("https://www.usenix.org/system/files/nsdi25-du.pdf", updated.pdf_url)
        self.assertEqual("https://www.usenix.org/biblio/export/bibtex/305308", updated.bibtex_url)
        self.assertIn("@inproceedings", updated.bibtex or "")

    def test_fetch_bibtex_downloads_from_export_url(self) -> None:
        conf = NsdiConference()
        with patch.object(conf, "_get", return_value=_FakeResponse("@inproceedings{305308}")):
            paper = PaperMeta(
                paper_id="du",
                title="PRED",
                conf="nsdi",
                year=2025,
                bibtex_url="https://www.usenix.org/biblio/export/bibtex/305308",
            )
            bibtex = conf.fetch_bibtex(paper)

        self.assertIn("@inproceedings", bibtex)


if __name__ == "__main__":
    unittest.main()
