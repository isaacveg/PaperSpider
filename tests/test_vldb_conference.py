# Copyright 2026 Isaacveg
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#     http://www.apache.org/licenses/LICENSE-2.0

from __future__ import annotations

import html
import json
import unittest
from unittest.mock import patch

from paper_spider.conferences.vldb import VldbConference
from paper_spider.models import PaperMeta


class _FakeResponse:
    def __init__(self, text: str, content: bytes | None = None) -> None:
        self.text = text
        self.content = content if content is not None else text.encode("utf-8")
        self.status_code = 200
        self.encoding = "utf-8"


def _next_data_html(page_props: dict) -> str:
    payload = {
        "props": {"pageProps": page_props},
        "page": "/volumes/[volume]",
        "query": {"volume": "17"},
        "buildId": "test-build",
    }
    return (
        '<html><body><script id="__NEXT_DATA__" type="application/json">'
        f"{html.escape(json.dumps(payload))}"
        "</script></body></html>"
    )


VLDB_HTML = _next_data_html(
    {
        "volume": "17",
        "groupedIssues": {
            "1": [
                {
                    "issue": 1,
                    "authors": "Meihui Zhang and Cyrus Shahabi",
                    "pdf": "https://www.vldb.org/pvldb/vol17/FrontMatterVol17No1.pdf",
                    "title": "Front Matter",
                },
                {
                    "issue": 1,
                    "authors": "Bolong Zheng, Yongyong Gao, Jingyi Wan",
                    "pdf": "https://www.vldb.org/pvldb/vol17/p1-zheng.pdf",
                    "title": "DecLog: Decentralized Logging in Non-Volatile Memory for Time Series Database Systems",
                    "start_page": 1,
                    "end_page": 14,
                },
            ]
        },
        "volumeSummaries": [
            {
                "Author Names": "Bolong Zheng, Yongyong Gao, Jingyi Wan",
                "Paper ID": "vol17/p1-zheng",
                "Paper Title": "DecLog: Decentralized Logging in Non-Volatile Memory for Time Series Database Systems",
                "Abstract": "Growing demands for the efficient processing of extreme-scale time series workloads.",
                "Artificats": "yes",
            }
        ],
    }
)


class VldbConferenceTests(unittest.TestCase):
    def test_metadata_matches_vldb(self) -> None:
        conf = VldbConference()

        self.assertEqual("VLDB", conf.name)
        self.assertEqual("vldb", conf.slug)
        self.assertEqual(17, conf._volume_for_year(2024))

    def test_list_papers_parses_next_data_volume(self) -> None:
        conf = VldbConference()
        with patch.object(conf, "_get", return_value=_FakeResponse(VLDB_HTML)) as mock_get:
            papers = conf.list_papers(2024)

        self.assertEqual("https://www.vldb.org/pvldb/volumes/17/", mock_get.call_args[0][0])
        self.assertEqual(1, len(papers))
        self.assertEqual("vol17_p1-zheng", papers[0].paper_id)
        self.assertEqual(
            "DecLog: Decentralized Logging in Non-Volatile Memory for Time Series Database Systems",
            papers[0].title,
        )
        self.assertEqual(["Bolong Zheng", "Yongyong Gao", "Jingyi Wan"], papers[0].authors)
        self.assertEqual("Growing demands for the efficient processing of extreme-scale time series workloads.", papers[0].abstract)
        self.assertEqual("https://www.vldb.org/pvldb/vol17/p1-zheng.pdf", papers[0].pdf_url)
        self.assertEqual("https://www.vldb.org/pvldb/volumes/17/#issue-1", papers[0].detail_url)
        self.assertEqual(("main", "conference"), (papers[0].track, papers[0].paper_type))

    def test_fetch_details_returns_existing_static_metadata(self) -> None:
        conf = VldbConference()
        paper = PaperMeta(
            paper_id="vol17_p1-zheng",
            title="DecLog",
            conf="vldb",
            year=2024,
            abstract="Abstract from list.",
            pdf_url="https://www.vldb.org/pvldb/vol17/p1-zheng.pdf",
        )

        self.assertIs(conf.fetch_details(paper), paper)

    def test_fetch_pdf_downloads_known_pdf_url(self) -> None:
        conf = VldbConference()
        pdf_bytes = b"%PDF-1.7"
        paper = PaperMeta(
            paper_id="vol17_p1-zheng",
            title="DecLog",
            conf="vldb",
            year=2024,
            pdf_url="https://www.vldb.org/pvldb/vol17/p1-zheng.pdf",
        )

        with patch.object(conf, "_get", return_value=_FakeResponse("", content=pdf_bytes)) as mock_get:
            data = conf.fetch_pdf(paper)

        self.assertEqual("https://www.vldb.org/pvldb/vol17/p1-zheng.pdf", mock_get.call_args[0][0])
        self.assertTrue(mock_get.call_args.kwargs["binary"])
        self.assertEqual(pdf_bytes, data)

    def test_fetch_bibtex_synthesizes_entry_from_metadata(self) -> None:
        conf = VldbConference()
        paper = PaperMeta(
            paper_id="vol17_p1-zheng",
            title="DecLog",
            conf="vldb",
            year=2024,
            authors=["Bolong Zheng", "Yongyong Gao", "Jingyi Wan"],
            pdf_url="https://www.vldb.org/pvldb/vol17/p1-zheng.pdf",
        )

        bibtex = conf.fetch_bibtex(paper)

        self.assertIn("@inproceedings{vol17_p1-zheng", bibtex)
        self.assertIn("title = {DecLog}", bibtex)
        self.assertIn("author = {Bolong Zheng and Yongyong Gao and Jingyi Wan}", bibtex)
        self.assertIn("booktitle = {Proceedings of the VLDB Endowment}", bibtex)
        self.assertIn("url = {https://www.vldb.org/pvldb/vol17/p1-zheng.pdf}", bibtex)


if __name__ == "__main__":
    unittest.main()
