# Copyright 2026 Isaacveg
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#     http://www.apache.org/licenses/LICENSE-2.0

from __future__ import annotations

import unittest
from unittest.mock import patch

from paper_spider.conferences.acl import AclConference
from paper_spider.conferences.atc import AtcConference
from paper_spider.conferences.naacl import NaaclConference
from paper_spider.conferences.osdi import OsdiConference


class _FakeResponse:
    def __init__(self, text: str) -> None:
        self.text = text
        self.content = text.encode("utf-8")
        self.status_code = 200
        self.encoding = "utf-8"


ACL_HTML = """
<html><body>
  <div class="d-sm-flex align-items-stretch mb-3">
    <div class="d-block me-2 list-button-row">
      <a href="https://aclanthology.org/2025.acl-long.1.pdf">pdf</a>
      <a href="/2025.acl-long.1.bib">bib</a>
    </div>
    <span class="d-block">
      <strong><a class="align-middle" href="/2025.acl-long.1/">ACL Paper</a></strong><br />
      <a href="/people/alice/">Alice</a>
    </span>
  </div>
</body></html>
"""

ACL_SHORT_HTML = """
<html><body>
  <div class="d-sm-flex align-items-stretch mb-3">
    <div class="d-block me-2 list-button-row">
      <a href="https://aclanthology.org/2025.acl-short.2.pdf">pdf</a>
      <a href="/2025.acl-short.2.bib">bib</a>
    </div>
    <span class="d-block">
      <strong><a class="align-middle" href="/2025.acl-short.2/">ACL Short Paper</a></strong><br />
      <a href="/people/bob/">Bob</a>
    </span>
  </div>
</body></html>
"""


USENIX_HTML = """
<html><body>
  <article class="node node-paper view-mode-schedule">
    <h2><a href="/conference/osdi24/presentation/example">Systems Paper</a></h2>
    <div class="content">
      <div class="field field-name-field-paper-people-text">
        <div class="field-item odd"><p>Alice and Bob, <em>Example Lab</em></p></div>
      </div>
      <div class="field field-name-field-paper-description-long">
        <p>Systems abstract.</p>
      </div>
    </div>
  </article>
</body></html>
"""


class FamilyConferenceTests(unittest.TestCase):
    def test_acl_combines_long_and_short_volumes(self) -> None:
        conf = AclConference()
        responses = {
            "https://aclanthology.org/volumes/2025.acl-long/": _FakeResponse(ACL_HTML),
            "https://aclanthology.org/volumes/2025.acl-short/": _FakeResponse(ACL_SHORT_HTML),
        }

        def fake_get(url: str, binary: bool = False):
            return responses.get(url)

        with patch.object(conf, "_get", side_effect=fake_get) as mock_get:
            papers = conf.list_papers(2025)

        self.assertEqual(
            [
                "https://aclanthology.org/volumes/2025.acl-long/",
                "https://aclanthology.org/volumes/2025.acl-short/",
            ],
            [call.args[0] for call in mock_get.call_args_list],
        )
        self.assertEqual(["ACL Paper", "ACL Short Paper"], [paper.title for paper in papers])
        self.assertEqual([("main", "long"), ("main", "short")], [(paper.track, paper.paper_type) for paper in papers])

    def test_naacl_uses_long_and_short_volumes(self) -> None:
        conf = NaaclConference()
        responses = {
            "https://aclanthology.org/volumes/2025.naacl-long/": _FakeResponse(ACL_HTML),
            "https://aclanthology.org/volumes/2025.naacl-short/": _FakeResponse(ACL_SHORT_HTML),
        }

        def fake_get(url: str, binary: bool = False):
            return responses.get(url)

        with patch.object(conf, "_get", side_effect=fake_get) as mock_get:
            conf.list_papers(2025)

        self.assertEqual(
            [
                "https://aclanthology.org/volumes/2025.naacl-long/",
                "https://aclanthology.org/volumes/2025.naacl-short/",
            ],
            [call.args[0] for call in mock_get.call_args_list],
        )

    def test_osdi_uses_osdi_year_slug(self) -> None:
        conf = OsdiConference()
        with patch.object(conf, "_get", return_value=_FakeResponse(USENIX_HTML)) as mock_get:
            papers = conf.list_papers(2024)

        self.assertEqual("https://www.usenix.org/conference/osdi24/technical-sessions", mock_get.call_args[0][0])
        self.assertEqual("Systems Paper", papers[0].title)
        self.assertEqual(("technical", "conference"), (papers[0].track, papers[0].paper_type))

    def test_atc_uses_atc_year_slug(self) -> None:
        conf = AtcConference()
        with patch.object(conf, "_get", return_value=_FakeResponse(USENIX_HTML)) as mock_get:
            conf.list_papers(2025)

        self.assertEqual("https://www.usenix.org/conference/atc25/technical-sessions", mock_get.call_args[0][0])


if __name__ == "__main__":
    unittest.main()
