# Copyright 2026 Isaacveg
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#     http://www.apache.org/licenses/LICENSE-2.0

from __future__ import annotations

import unittest
from unittest.mock import patch

from paper_spider.conferences.fast import FastConference


class _FakeResponse:
    def __init__(self, text: str) -> None:
        self.text = text
        self.content = text.encode("utf-8")
        self.status_code = 200
        self.encoding = "utf-8"


FAST_HTML = """
<html><body>
  <article class="node node-paper view-mode-schedule">
    <h2><a href="/conference/fast25/presentation/example">Storage Paper</a></h2>
    <div class="content">
      <div class="field field-name-field-paper-people-text">
        <div class="field-item odd"><p>Alice and Bob, <em>Example Lab</em></p></div>
      </div>
      <div class="field field-name-field-paper-description-long">
        <p>Storage abstract.</p>
      </div>
    </div>
  </article>
</body></html>
"""


class FastConferenceTests(unittest.TestCase):
    def test_metadata_matches_usenix_fast_slug(self) -> None:
        conf = FastConference()

        self.assertEqual("FAST", conf.name)
        self.assertEqual("fast", conf.slug)
        self.assertEqual("fast25", conf._year_slug(2025))

    def test_list_papers_uses_fast_year_slug(self) -> None:
        conf = FastConference()
        with patch.object(conf, "_get", return_value=_FakeResponse(FAST_HTML)) as mock_get:
            papers = conf.list_papers(2025)

        self.assertEqual("https://www.usenix.org/conference/fast25/technical-sessions", mock_get.call_args[0][0])
        self.assertEqual(1, len(papers))
        self.assertEqual("example", papers[0].paper_id)
        self.assertEqual("Storage Paper", papers[0].title)
        self.assertEqual("fast", papers[0].conf)
        self.assertEqual(("technical", "conference"), (papers[0].track, papers[0].paper_type))
        self.assertEqual(["Alice", "Bob"], papers[0].authors)
        self.assertEqual("Storage abstract.", papers[0].abstract)


if __name__ == "__main__":
    unittest.main()
