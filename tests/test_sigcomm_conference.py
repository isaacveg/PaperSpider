# Copyright 2026 Isaacveg
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#     http://www.apache.org/licenses/LICENSE-2.0

from __future__ import annotations

import json
import unittest
from unittest.mock import patch

from paper_spider.conferences.sigcomm import SigcommConference
from paper_spider.models import PaperMeta


class _FakeResponse:
    def __init__(self, text: str, content: bytes | None = None) -> None:
        self.text = text
        self.content = content if content is not None else text.encode("utf-8")
        self.status_code = 200
        self.encoding = "utf-8"


LIST_HTML = """
<html><body>
<div class="paper-table">
  <table class="long_table_program">
    <tr class="bkg_color_2">
      <td id="session-netai">
        <p><span class="text-color-primary">09:00 — 10:20 | NetAI</span></p>
        <p class="style_italic"><span class="text-color-primary">Session Chair:</span> Jon Crowcroft</p>
      </td>
      <td></td>
      <td></td>
      <td></td>
    </tr>
    <tr>
      <td>
        <p><span class="text-color-primary">InfiniteHBD: Building Datacenter-Scale High-Bandwidth Domain for LLM with Optical Circuit Switching Transceivers</span></p>
        <p class="style_italic">Chenchen Shou (Peking University); Guyue Liu (Peking University), Hao Nie (StepFun)</p>
      </td>
      <td class="text_align_center">
        <button class="paper-title"></button>
      </td>
      <td class="text_align_center">
        <a href="https://dl.acm.org/doi/10.1145/3718958.3750468" target="_blank"></a>
      </td>
      <td></td>
    </tr>
    <tr class="abstract-row">
      <td colspan="4" class="abstract">
        <p class="abstract-info-row"><span class="text-color-secondary">Abstract: </span>Example SIGCOMM abstract.</p>
      </td>
    </tr>
  </table>
</div>
</body></html>
"""


CROSSREF_JSON = json.dumps(
    {
        "title": "InfiniteHBD: Building Datacenter-Scale High-Bandwidth Domain for LLM with Optical Circuit Switching Transceivers",
        "author": [
            {"given": "Chenchen", "family": "Shou"},
            {"given": "Guyue", "family": "Liu"},
            {"given": "Hao", "family": "Nie"},
        ],
        "link": [
            {
                "URL": "https://dl.acm.org/doi/pdf/10.1145/3718958.3750468",
                "content-type": "unspecified",
            }
        ],
    }
)


BIBTEX_TEXT = """
@inproceedings{Shou_2025,
  title={InfiniteHBD: Building Datacenter-Scale High-Bandwidth Domain for LLM with Optical Circuit Switching Transceivers},
  author={Shou, Chenchen and Liu, Guyue and Nie, Hao}
}
""".strip()


class SigcommConferenceTests(unittest.TestCase):
    def test_list_papers_parses_program_table(self) -> None:
        conf = SigcommConference()
        with patch.object(conf, "_get", return_value=_FakeResponse(LIST_HTML)) as mock_get:
            papers = conf.list_papers(2025)

        self.assertEqual("https://conferences.sigcomm.org/sigcomm/2025/program/papers-info/", mock_get.call_args[0][0])
        self.assertEqual(1, len(papers))
        self.assertEqual("10.1145_3718958.3750468", papers[0].paper_id)
        self.assertEqual(
            "InfiniteHBD: Building Datacenter-Scale High-Bandwidth Domain for LLM with Optical Circuit Switching Transceivers",
            papers[0].title,
        )
        self.assertEqual(["Chenchen Shou", "Guyue Liu", "Hao Nie"], papers[0].authors)
        self.assertEqual("Example SIGCOMM abstract.", papers[0].abstract)
        self.assertEqual(("technical", "conference"), (papers[0].track, papers[0].paper_type))
        self.assertEqual("https://doi.org/10.1145/3718958.3750468", papers[0].detail_url)

    def test_fetch_details_uses_crossref_metadata(self) -> None:
        conf = SigcommConference()
        with patch.object(conf, "_get", return_value=_FakeResponse(CROSSREF_JSON)) as mock_get:
            paper = PaperMeta(
                paper_id="10.1145_3718958.3750468",
                title="Old Title",
                conf="sigcomm",
                year=2025,
                detail_url="https://doi.org/10.1145/3718958.3750468",
            )
            updated = conf.fetch_details(paper)

        self.assertIn("/works/10.1145%2F3718958.3750468/transform/", mock_get.call_args[0][0])
        self.assertEqual(
            "InfiniteHBD: Building Datacenter-Scale High-Bandwidth Domain for LLM with Optical Circuit Switching Transceivers",
            updated.title,
        )
        self.assertEqual(["Chenchen Shou", "Guyue Liu", "Hao Nie"], updated.authors)
        self.assertEqual("https://dl.acm.org/doi/pdf/10.1145/3718958.3750468", updated.pdf_url)
        self.assertEqual("https://doi.org/10.1145/3718958.3750468", updated.bibtex_url)

    def test_fetch_bibtex_uses_doi_content_negotiation(self) -> None:
        conf = SigcommConference()
        with patch.object(conf, "_request", return_value=_FakeResponse(BIBTEX_TEXT)) as mock_request:
            paper = PaperMeta(
                paper_id="10.1145_3718958.3750468",
                title="InfiniteHBD",
                conf="sigcomm",
                year=2025,
                detail_url="https://doi.org/10.1145/3718958.3750468",
            )
            bibtex = conf.fetch_bibtex(paper)

        self.assertEqual("https://doi.org/10.1145/3718958.3750468", mock_request.call_args.args[0])
        self.assertEqual("application/x-bibtex", mock_request.call_args.kwargs["headers"]["Accept"])
        self.assertIn("@inproceedings", bibtex.lower())

    def test_fetch_pdf_uses_crossref_pdf_link(self) -> None:
        conf = SigcommConference()
        pdf_bytes = b"%PDF-1.7"

        def fake_get(url: str, binary: bool = False):
            if "api.crossref.org" in url:
                return _FakeResponse(CROSSREF_JSON)
            if url == "https://dl.acm.org/doi/pdf/10.1145/3718958.3750468":
                return _FakeResponse("", content=pdf_bytes)
            return None

        with patch.object(conf, "_get", side_effect=fake_get):
            paper = PaperMeta(
                paper_id="10.1145_3718958.3750468",
                title="InfiniteHBD",
                conf="sigcomm",
                year=2025,
                detail_url="https://doi.org/10.1145/3718958.3750468",
            )
            data = conf.fetch_pdf(paper)

        self.assertEqual(pdf_bytes, data)


if __name__ == "__main__":
    unittest.main()
