# Copyright 2026 Isaacveg
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#     http://www.apache.org/licenses/LICENSE-2.0

from __future__ import annotations

import unittest
from unittest.mock import patch

from paper_spider.conferences.cvpr import CvprConference
from paper_spider.models import PaperMeta


class _FakeResponse:
    def __init__(self, text: str, content: bytes | None = None) -> None:
        self.text = text
        self.content = content if content is not None else text.encode("utf-8")
        self.status_code = 200
        self.encoding = "utf-8"


LIST_HTML = """
<html><body>
<dt class="ptitle"><br><a href="/content/CVPR2025/html/Xiao_Example_CVPR_2025_paper.html">Example CVPR Paper</a></dt>
<dd>
<a>Alice Example</a>,
<a>Bob Example</a>
</dd>
<dd>
[<a href="/content/CVPR2025/papers/Xiao_Example_CVPR_2025_paper.pdf">pdf</a>]
<div class="link2">[<a class="fakelink">bibtex</a>]
<div class="bibref pre-white-space">@InProceedings{Xiao_2025_CVPR,
    author = {Example, Alice and Example, Bob},
    title = {Example CVPR Paper}
}</div>
</div>
</dd>
</body></html>
"""


DETAIL_HTML = """
<html><head>
<meta name="citation_title" content="Example CVPR Paper" />
<meta name="citation_author" content="Example, Alice" />
<meta name="citation_author" content="Example, Bob" />
<meta name="citation_pdf_url" content="https://openaccess.thecvf.com/content/CVPR2025/papers/Xiao_Example_CVPR_2025_paper.pdf" />
</head><body>
<div id="abstract">This is the CVPR abstract.</div>
<div class="bibref pre-white-space">@InProceedings{Xiao_2025_CVPR,
    author = {Example, Alice and Example, Bob},
    title = {Example CVPR Paper}
}</div>
</body></html>
"""


class CvprConferenceTests(unittest.TestCase):
    def test_list_papers_parses_openaccess_listing(self) -> None:
        conf = CvprConference()
        with patch.object(conf, "_get", return_value=_FakeResponse(LIST_HTML)) as mock_get:
            papers = conf.list_papers(2025)

        self.assertEqual("https://openaccess.thecvf.com/CVPR2025?day=all", mock_get.call_args[0][0])
        self.assertEqual(1, len(papers))
        self.assertEqual("Xiao_Example_CVPR_2025", papers[0].paper_id)
        self.assertEqual("Example CVPR Paper", papers[0].title)
        self.assertEqual(["Alice Example", "Bob Example"], papers[0].authors)
        self.assertEqual("main", papers[0].track)
        self.assertEqual("conference", papers[0].paper_type)
        self.assertIn("@InProceedings", papers[0].bibtex or "")

    def test_fetch_details_updates_abstract_pdf_and_bibtex(self) -> None:
        conf = CvprConference()
        with patch.object(conf, "_get", return_value=_FakeResponse(DETAIL_HTML)):
            paper = PaperMeta(
                paper_id="Xiao_Example_CVPR_2025",
                title="Old",
                conf="cvpr",
                year=2025,
                detail_url="https://openaccess.thecvf.com/content/CVPR2025/html/Xiao_Example_CVPR_2025_paper.html",
            )
            updated = conf.fetch_details(paper)

        self.assertEqual("Example CVPR Paper", updated.title)
        self.assertEqual(["Alice Example", "Bob Example"], updated.authors)
        self.assertEqual("This is the CVPR abstract.", updated.abstract)
        self.assertEqual(
            "https://openaccess.thecvf.com/content/CVPR2025/papers/Xiao_Example_CVPR_2025_paper.pdf",
            updated.pdf_url,
        )
        self.assertIn("@InProceedings", updated.bibtex or "")

    def test_fetch_bibtex_uses_detail_page(self) -> None:
        conf = CvprConference()
        with patch.object(conf, "_get", return_value=_FakeResponse(DETAIL_HTML)):
            paper = PaperMeta(
                paper_id="Xiao_Example_CVPR_2025",
                title="Example CVPR Paper",
                conf="cvpr",
                year=2025,
                detail_url="https://openaccess.thecvf.com/content/CVPR2025/html/Xiao_Example_CVPR_2025_paper.html",
            )
            bibtex = conf.fetch_bibtex(paper)

        self.assertIn("@InProceedings", bibtex)


if __name__ == "__main__":
    unittest.main()
