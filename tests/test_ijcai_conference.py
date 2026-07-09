# Copyright 2026 Isaacveg
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#     http://www.apache.org/licenses/LICENSE-2.0

from __future__ import annotations

import unittest
from unittest.mock import patch

from paper_spider.conferences.ijcai import IjcaiConference
from paper_spider.models import PaperMeta


class _FakeResponse:
    def __init__(self, text: str, content: bytes | None = None) -> None:
        self.text = text
        self.content = content if content is not None else text.encode("utf-8")
        self.status_code = 200
        self.encoding = "utf-8"


class IjcaiConferenceTests(unittest.TestCase):
    def test_list_papers_parses_official_proceedings_page(self) -> None:
        conf = IjcaiConference()
        html = """
        <h2>Content</h2>
        <div class="section" id="section0">
          <div class="section_title"><h3>Main Track</h3></div>
          <div class="subsection" id="subsection0">
            <div class="subsection_title">Agent-based and Multi-agent Systems</div>
            <div id="paper1" class="paper_wrapper">
              <div class="title">Certified Policy Verification and Synthesis for MDPs under Distributional Reach-Avoidance Properties</div>
              <div class="authors">S. Akshay, Krishnendu Chatterjee, Tobias Meggendorfer, Đorđe Žikelić</div>
              <div class="details">(<a href="0001.pdf">PDF</a> | <a href="/proceedings/2024/1"> Details</a>)</div>
            </div>
          </div>
        </div>
        """

        with patch.object(conf, "_get", return_value=_FakeResponse(html)):
            papers = conf.list_papers(2024)

        self.assertEqual(1, len(papers))
        self.assertEqual("ijcai2024p1", papers[0].paper_id)
        self.assertEqual(
            "Certified Policy Verification and Synthesis for MDPs under Distributional Reach-Avoidance Properties",
            papers[0].title,
        )
        self.assertEqual(
            ["S. Akshay", "Krishnendu Chatterjee", "Tobias Meggendorfer", "Đorđe Žikelić"],
            papers[0].authors,
        )
        self.assertEqual("ijcai", papers[0].conf)
        self.assertEqual(2024, papers[0].year)
        self.assertEqual("Main Track", papers[0].track)
        self.assertEqual("Agent-based and Multi-agent Systems", papers[0].paper_type)
        self.assertEqual("https://www.ijcai.org/proceedings/2024/1", papers[0].detail_url)
        self.assertEqual("https://www.ijcai.org/proceedings/2024/0001.pdf", papers[0].pdf_url)
        self.assertEqual("https://www.ijcai.org/proceedings/2024/bibtex/1", papers[0].bibtex_url)

    def test_fetch_details_extracts_abstract_keywords_pdf_and_bibtex_url(self) -> None:
        conf = IjcaiConference()
        html = """
        <div class="container-fluid proceedings-detail">
          <div class="row">
            <div class="col-md-8 col-xs-12 col-sm-12">
              <h1>Certified Policy Verification and Synthesis for MDPs under Distributional Reach-Avoidance Properties</h1>
              <h2>S. Akshay, Krishnendu Chatterjee, Tobias Meggendorfer, Đorđe Žikelić</h2>
            </div>
          </div>
          <div class="row">
            <div class="col-md-8 col-xs-12 col-sm-12">
              <div>Proceedings of the Thirty-Third International Joint Conference on Artificial Intelligence</div>
              <div>Main Track. Pages 3-12.
                <a href="https://doi.org/10.24963/ijcai.2024/1" class="doi">https://doi.org/10.24963/ijcai.2024/1</a>
              </div>
            </div>
            <div class="col-md-4 col-xs-12 col-sm-12">
              <a class="button btn-lg btn-download" href="https://www.ijcai.org/proceedings/2024/0001.pdf">PDF</a>
              <a class="button btn-lg btn-download" href="/proceedings/2024/bibtex/1">BibTeX</a>
            </div>
          </div>
          <hr>
          <div class="row">
            <div class="col-md-12">
              Markov Decision Processes (MDPs) are a classical model for decision making.

              In this work, we consider certified policy verification and synthesis.
            </div>
            <div class="col-md-12">
              <div class="keywords">
                <div class="title">Keywords:</div>
                <div class="topic">Agent-based and Multi-agent Systems: MAS: Formal verification, validation and synthesis </div>
                <div class="topic"> Planning and Scheduling: PS: Planning under uncertainty</div>
              </div>
            </div>
          </div>
        </div>
        """

        with patch.object(conf, "_get", return_value=_FakeResponse(html)):
            paper = PaperMeta(
                paper_id="1",
                title="Old title",
                conf="ijcai",
                year=2024,
                detail_url="https://www.ijcai.org/proceedings/2024/1",
            )
            updated = conf.fetch_details(paper)

        self.assertEqual(
            "Certified Policy Verification and Synthesis for MDPs under Distributional Reach-Avoidance Properties",
            updated.title,
        )
        self.assertEqual(
            ["S. Akshay", "Krishnendu Chatterjee", "Tobias Meggendorfer", "Đorđe Žikelić"],
            updated.authors,
        )
        self.assertEqual(
            "Markov Decision Processes (MDPs) are a classical model for decision making. "
            "In this work, we consider certified policy verification and synthesis.",
            updated.abstract,
        )
        self.assertEqual(
            [
                "Agent-based and Multi-agent Systems: MAS: Formal verification, validation and synthesis",
                "Planning and Scheduling: PS: Planning under uncertainty",
            ],
            updated.keywords,
        )
        self.assertEqual("https://www.ijcai.org/proceedings/2024/0001.pdf", updated.pdf_url)
        self.assertEqual("https://www.ijcai.org/proceedings/2024/bibtex/1", updated.bibtex_url)

    def test_fetch_bibtex_downloads_bibtex_endpoint(self) -> None:
        conf = IjcaiConference()
        requested_urls: list[str] = []

        def fake_get(url: str, binary: bool = False):
            requested_urls.append(url)
            return _FakeResponse("@inproceedings{ijcai2024p1}")

        with patch.object(conf, "_get", side_effect=fake_get):
            paper = PaperMeta(
                paper_id="ijcai2024p1",
                title="Paper One",
                conf="ijcai",
                year=2024,
            )
            bibtex = conf.fetch_bibtex(paper)

        self.assertIn("@inproceedings", bibtex)
        self.assertEqual(["https://www.ijcai.org/proceedings/2024/bibtex/1"], requested_urls)
        self.assertEqual(bibtex, paper.bibtex)

    def test_fetch_bibtex_returns_cached_value_without_request(self) -> None:
        conf = IjcaiConference()
        paper = PaperMeta(
            paper_id="ijcai2024p1",
            title="Paper One",
            conf="ijcai",
            year=2024,
            bibtex="@inproceedings{cached}",
        )

        with patch.object(conf, "_get") as mock_get:
            bibtex = conf.fetch_bibtex(paper)

        mock_get.assert_not_called()
        self.assertEqual("@inproceedings{cached}", bibtex)


if __name__ == "__main__":
    unittest.main()
