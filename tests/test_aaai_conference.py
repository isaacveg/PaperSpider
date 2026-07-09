# Copyright 2026 Isaacveg
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#     http://www.apache.org/licenses/LICENSE-2.0

from __future__ import annotations

import unittest
from unittest.mock import patch

from paper_spider.models import PaperMeta


class _FakeResponse:
    def __init__(self, text: str) -> None:
        self.text = text
        self.content = text.encode("utf-8")
        self.status_code = 200
        self.encoding = "utf-8"


def _conference_class():
    try:
        from paper_spider.conferences.aaai import AaaiConference
    except ModuleNotFoundError as exc:
        raise AssertionError("AAAI conference implementation is missing") from exc
    return AaaiConference


ARCHIVE_HTML = """
<html><body>
  <ul class="issues_archive">
    <li>
      <div class="obj_issue_summary">
        <h2>
          <a class="title" href="https://ojs.aaai.org/index.php/AAAI/issue/view/683">
            AAAI-26 Technical Tracks 1
          </a>
          <div class="series">Vol. 40 No. 1</div>
        </h2>
        <div class="description">
          <p><strong>Fortieth AAAI Conference on Artificial Intelligence</strong></p>
          <p>Copyright (c) 2026 Association for the Advancement of Artificial Intelligence</p>
        </div>
      </div>
    </li>
  </ul>
</body></html>
"""

ARCHIVE_2026_ONLY_HTML = """
<html><body>
  <ul class="issues_archive">
    <li>
      <div class="obj_issue_summary">
        <h2><a class="title" href="https://ojs.aaai.org/index.php/AAAI/issue/view/683">AAAI-26 Technical Tracks 1</a></h2>
        <div class="description"><p>Copyright (c) 2026 Association for the Advancement of Artificial Intelligence</p></div>
      </div>
    </li>
  </ul>
  <div class="cmp_pagination">
    <a class="next" href="https://ojs.aaai.org/index.php/AAAI/issue/archive/2">Next</a>
  </div>
</body></html>
"""

ARCHIVE_2025_HTML = """
<html><body>
  <ul class="issues_archive">
    <li>
      <div class="obj_issue_summary">
        <h2><a class="title" href="https://ojs.aaai.org/index.php/AAAI/issue/view/624">AAAI-25 Technical Tracks 1</a></h2>
        <div class="description"><p>Copyright (c) 2025 Association for the Advancement of Artificial Intelligence</p></div>
      </div>
    </li>
  </ul>
</body></html>
"""

ISSUE_HTML = """
<html><body>
  <div class="sections">
    <div class="section">
      <h2>AAAI Technical Track on Application Domains I</h2>
      <ul class="cmp_article_list articles">
        <li>
          <div class="obj_article_summary">
            <h3 class="title">
              <a id="article-36958" href="https://ojs.aaai.org/index.php/AAAI/article/view/36958">
                Resource Efficient Sleep Staging via Multi-Level Masking and Prompt Learning
              </a>
            </h3>
            <div class="meta">
              <div class="authors">Lejun Ai, Yulong Li, Rui Wang</div>
              <div class="pages">3-11</div>
            </div>
            <ul class="galleys_links">
              <li>
                <a class="obj_galley_link pdf" href="https://ojs.aaai.org/index.php/AAAI/article/view/36958/40920">
                  PDF
                </a>
              </li>
            </ul>
          </div>
        </li>
      </ul>
    </div>
    <div class="section">
      <h2>IAAI Technical Track on Emerging Applications of AI</h2>
      <ul class="cmp_article_list articles">
        <li>
          <div class="obj_article_summary">
            <h3 class="title">
              <a id="article-99999" href="https://ojs.aaai.org/index.php/AAAI/article/view/99999">
                Non-AAAI Co-located Paper
              </a>
            </h3>
            <div class="meta"><div class="authors">Someone Else</div></div>
          </div>
        </li>
      </ul>
    </div>
  </div>
</body></html>
"""

COLOCATED_ONLY_ISSUE_HTML = """
<html><body>
  <div class="sections">
    <div class="section">
      <h2>IAAI Technical Track on Emerging Applications of AI</h2>
      <ul class="cmp_article_list articles">
        <li>
          <div class="obj_article_summary">
            <h3 class="title">
              <a id="article-99999" href="https://ojs.aaai.org/index.php/AAAI/article/view/99999">
                Non-AAAI Co-located Paper
              </a>
            </h3>
            <div class="meta"><div class="authors">Someone Else</div></div>
          </div>
        </li>
      </ul>
    </div>
  </div>
</body></html>
"""

DETAIL_HTML = """
<html><head>
  <meta name="citation_title" content="Resource Efficient Sleep Staging via Multi-Level Masking and Prompt Learning"/>
  <meta name="citation_author" content="Lejun Ai"/>
  <meta name="citation_author" content="Yulong Li"/>
  <meta name="citation_author" content="Rui Wang"/>
  <meta name="DC.Description" content="Automatic sleep staging plays a vital role."/>
  <meta name="citation_pdf_url" content="https://ojs.aaai.org/index.php/AAAI/article/download/36958/40920"/>
</head><body>
  <article class="obj_article_details">
    <h1 class="page_title">Resource Efficient Sleep Staging via Multi-Level Masking and Prompt Learning</h1>
    <section class="item doi">
      <span class="value"><a href="https://doi.org/10.1609/aaai.v40i1.36958">doi</a></span>
    </section>
    <section class="item abstract">
      <h2 class="label">Abstract</h2>
      Automatic sleep staging plays a vital role.
    </section>
    <div class="citation_formats_list">
      <a href="https://ojs.aaai.org/index.php/AAAI/citationstylelanguage/download/bibtex?submissionId=36958&amp;publicationId=35217">
        BibTeX
      </a>
    </div>
  </article>
</body></html>
"""


class AaaiConferenceTests(unittest.TestCase):
    def test_list_papers_parses_ojs_issue_pages(self) -> None:
        conf = _conference_class()()
        responses = {
            "https://ojs.aaai.org/index.php/AAAI/issue/archive": _FakeResponse(ARCHIVE_HTML),
            "https://ojs.aaai.org/index.php/AAAI/issue/view/683": _FakeResponse(ISSUE_HTML),
        }

        def fake_get(url: str, binary: bool = False):
            return responses.get(url)

        with patch.object(conf, "_get", side_effect=fake_get):
            papers = conf.list_papers(2026)

        self.assertEqual(1, len(papers))
        self.assertEqual("36958", papers[0].paper_id)
        self.assertEqual("aaai", papers[0].conf)
        self.assertEqual(2026, papers[0].year)
        self.assertEqual(
            "Resource Efficient Sleep Staging via Multi-Level Masking and Prompt Learning",
            papers[0].title,
        )
        self.assertEqual(["Lejun Ai", "Yulong Li", "Rui Wang"], papers[0].authors)
        self.assertEqual("AAAI Technical Track on Application Domains I", papers[0].track)
        self.assertEqual("conference", papers[0].paper_type)
        self.assertEqual("https://ojs.aaai.org/index.php/AAAI/article/view/36958", papers[0].detail_url)
        self.assertEqual("https://ojs.aaai.org/index.php/AAAI/article/view/36958/40920", papers[0].pdf_url)

    def test_list_papers_follows_archive_pagination_to_requested_year(self) -> None:
        conf = _conference_class()()
        responses = {
            "https://ojs.aaai.org/index.php/AAAI/issue/archive": _FakeResponse(ARCHIVE_2026_ONLY_HTML),
            "https://ojs.aaai.org/index.php/AAAI/issue/archive/2": _FakeResponse(ARCHIVE_2025_HTML),
            "https://ojs.aaai.org/index.php/AAAI/issue/view/624": _FakeResponse(ISSUE_HTML),
        }

        def fake_get(url: str, binary: bool = False):
            return responses.get(url)

        with patch.object(conf, "_get", side_effect=fake_get) as mock_get:
            papers = conf.list_papers(2025)

        self.assertEqual(
            [
                "https://ojs.aaai.org/index.php/AAAI/issue/archive",
                "https://ojs.aaai.org/index.php/AAAI/issue/archive/2",
                "https://ojs.aaai.org/index.php/AAAI/issue/view/624",
            ],
            [call.args[0] for call in mock_get.call_args_list],
        )
        self.assertEqual(["36958"], [paper.paper_id for paper in papers])
        self.assertEqual(2025, papers[0].year)

    def test_issue_parser_does_not_fallback_to_colocated_sections(self) -> None:
        conf = _conference_class()()

        papers = conf._papers_from_issue(
            COLOCATED_ONLY_ISSUE_HTML,
            2026,
            "https://ojs.aaai.org/index.php/AAAI/issue/view/999",
        )

        self.assertEqual([], papers)

    def test_fetch_details_extracts_article_metadata_and_bibtex_url(self) -> None:
        conf = _conference_class()()
        paper = PaperMeta(
            paper_id="36958",
            title="Old Title",
            conf="aaai",
            year=2026,
            detail_url="https://ojs.aaai.org/index.php/AAAI/article/view/36958",
        )

        with patch.object(conf, "_get", return_value=_FakeResponse(DETAIL_HTML)):
            updated = conf.fetch_details(paper)

        self.assertEqual(
            "Resource Efficient Sleep Staging via Multi-Level Masking and Prompt Learning",
            updated.title,
        )
        self.assertEqual(["Lejun Ai", "Yulong Li", "Rui Wang"], updated.authors)
        self.assertEqual("Automatic sleep staging plays a vital role.", updated.abstract)
        self.assertEqual(
            "https://ojs.aaai.org/index.php/AAAI/article/download/36958/40920",
            updated.pdf_url,
        )
        self.assertEqual(
            "https://ojs.aaai.org/index.php/AAAI/citationstylelanguage/download/bibtex?submissionId=36958&publicationId=35217",
            updated.bibtex_url,
        )

    def test_fetch_bibtex_downloads_ojs_citation(self) -> None:
        conf = _conference_class()()
        paper = PaperMeta(
            paper_id="36958",
            title="Resource Efficient Sleep Staging via Multi-Level Masking and Prompt Learning",
            conf="aaai",
            year=2026,
            bibtex_url=(
                "https://ojs.aaai.org/index.php/AAAI/citationstylelanguage/download/bibtex"
                "?submissionId=36958&publicationId=35217"
            ),
        )

        with patch.object(conf, "_get", return_value=_FakeResponse("@article{ai2026resource}")):
            bibtex = conf.fetch_bibtex(paper)

        self.assertEqual("@article{ai2026resource}", bibtex)


if __name__ == "__main__":
    unittest.main()
