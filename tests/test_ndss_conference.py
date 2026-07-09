# Copyright 2026 Isaacveg
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#     http://www.apache.org/licenses/LICENSE-2.0

from __future__ import annotations

import unittest
from unittest.mock import patch

from paper_spider.conferences.ndss import NdssConference
from paper_spider.models import PaperMeta


class _FakeResponse:
    def __init__(self, text: str, content: bytes | None = None) -> None:
        self.text = text
        self.content = content if content is not None else text.encode("utf-8")
        self.status_code = 200
        self.encoding = "utf-8"


LIST_HTML = """
<html><body>
<div class="pt-cv-wrapper">
  <div class="pt-cv-view">
    <div class="pt-cv-content-item pt-cv-2-col" data-pid="23756">
      <h2 class="pt-cv-title">
        <a href="https://www.ndss-symposium.org/ndss-paper/a-causal-perspective-for-enhancing-jailbreak-attack-and-defense/">
          A Causal Perspective for Enhancing Jailbreak Attack and Defense
        </a>
      </h2>
      <div class="pt-cv-ctf-value">
        <p>Licheng Pan (Zhejiang University), Yunsheng Lu (University of Chicago), Jiexi Liu (Alibaba Group)</p>
      </div>
    </div>
  </div>
</div>
</body></html>
"""


DETAIL_HTML = """
<html><body>
<main class="main">
  <h1 class="entry-title">A Causal Perspective for Enhancing Jailbreak Attack and Defense</h1>
  <article class="ndss-paper tag-fall-cycle-2026">
    <div class="entry-content">
      <div class="paper-data">
        <p><strong>
          <p>Licheng Pan (Zhejiang University), Yunsheng Lu (University of Chicago), Jiexi Liu (Alibaba Group)</p>
        </strong></p>
        <p><p>Uncovering the mechanisms behind jailbreaks is crucial.<br />
        Existing studies overlook causal relationships.<br />
        Our results suggest a causal perspective improves reliability.</p></p>
      </div>
      <div class="paper-buttons">
        <a role="button" class="btn btn-light btn-sm pdf-button" target="_blank"
           href="https://www.ndss-symposium.org/wp-content/uploads/2026-f797-paper.pdf">Paper</a>
      </div>
    </div>
  </article>
</main>
</body></html>
"""


class NdssConferenceTests(unittest.TestCase):
    def test_list_papers_parses_accepted_papers_grid(self) -> None:
        conf = NdssConference()
        with patch.object(conf, "_get", return_value=_FakeResponse(LIST_HTML)) as mock_get:
            papers = conf.list_papers(2026)

        self.assertEqual(
            "https://www.ndss-symposium.org/ndss2026/accepted-papers/",
            mock_get.call_args[0][0],
        )
        self.assertEqual(1, len(papers))
        self.assertEqual(
            "a-causal-perspective-for-enhancing-jailbreak-attack-and-defense",
            papers[0].paper_id,
        )
        self.assertEqual(
            "A Causal Perspective for Enhancing Jailbreak Attack and Defense",
            papers[0].title,
        )
        self.assertEqual(["Licheng Pan", "Yunsheng Lu", "Jiexi Liu"], papers[0].authors)
        self.assertEqual("technical", papers[0].track)
        self.assertEqual("conference", papers[0].paper_type)
        self.assertEqual(
            "https://www.ndss-symposium.org/ndss-paper/a-causal-perspective-for-enhancing-jailbreak-attack-and-defense/",
            papers[0].detail_url,
        )

    def test_fetch_details_updates_abstract_pdf_and_bibtex(self) -> None:
        conf = NdssConference()
        with patch.object(conf, "_get", return_value=_FakeResponse(DETAIL_HTML)):
            paper = PaperMeta(
                paper_id="a-causal-perspective-for-enhancing-jailbreak-attack-and-defense",
                title="Old",
                conf="ndss",
                year=2026,
                detail_url="https://www.ndss-symposium.org/ndss-paper/a-causal-perspective-for-enhancing-jailbreak-attack-and-defense/",
            )
            updated = conf.fetch_details(paper)

        self.assertEqual(
            "A Causal Perspective for Enhancing Jailbreak Attack and Defense",
            updated.title,
        )
        self.assertEqual(["Licheng Pan", "Yunsheng Lu", "Jiexi Liu"], updated.authors)
        self.assertEqual(
            "Uncovering the mechanisms behind jailbreaks is crucial. Existing studies overlook causal relationships. Our results suggest a causal perspective improves reliability.",
            updated.abstract,
        )
        self.assertEqual(
            "https://www.ndss-symposium.org/wp-content/uploads/2026-f797-paper.pdf",
            updated.pdf_url,
        )
        self.assertIn("@inproceedings", updated.bibtex or "")
        self.assertIn("ndss2026causalperspective", updated.bibtex or "")

    def test_fetch_bibtex_generates_from_detail_page(self) -> None:
        conf = NdssConference()
        with patch.object(conf, "_get", return_value=_FakeResponse(DETAIL_HTML)):
            paper = PaperMeta(
                paper_id="a-causal-perspective-for-enhancing-jailbreak-attack-and-defense",
                title="A Causal Perspective for Enhancing Jailbreak Attack and Defense",
                conf="ndss",
                year=2026,
                detail_url="https://www.ndss-symposium.org/ndss-paper/a-causal-perspective-for-enhancing-jailbreak-attack-and-defense/",
            )
            bibtex = conf.fetch_bibtex(paper)

        self.assertIn("booktitle = {Network and Distributed System Security (NDSS) Symposium}", bibtex)
        self.assertIn("url = {https://www.ndss-symposium.org/ndss-paper/a-causal-perspective-for-enhancing-jailbreak-attack-and-defense/}", bibtex)

    def test_fetch_pdf_downloads_paper_link(self) -> None:
        conf = NdssConference()

        def fake_get(url: str, binary: bool = False):
            if url.endswith(".pdf"):
                return _FakeResponse("", content=b"%PDF-ndss")
            return _FakeResponse(DETAIL_HTML)

        with patch.object(conf, "_get", side_effect=fake_get):
            paper = PaperMeta(
                paper_id="a-causal-perspective-for-enhancing-jailbreak-attack-and-defense",
                title="A Causal Perspective for Enhancing Jailbreak Attack and Defense",
                conf="ndss",
                year=2026,
                detail_url="https://www.ndss-symposium.org/ndss-paper/a-causal-perspective-for-enhancing-jailbreak-attack-and-defense/",
            )
            content = conf.fetch_pdf(paper)

        self.assertEqual(b"%PDF-ndss", content)


if __name__ == "__main__":
    unittest.main()
