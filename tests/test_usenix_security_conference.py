# Copyright 2026 Isaacveg
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#     http://www.apache.org/licenses/LICENSE-2.0

from __future__ import annotations

import importlib
import unittest
from unittest.mock import patch

from paper_spider.conferences.family_base import UsenixFamilyBase


class _FakeResponse:
    def __init__(self, text: str) -> None:
        self.text = text
        self.content = text.encode("utf-8")
        self.status_code = 200
        self.encoding = "utf-8"


def _load_conference_class():
    try:
        module = importlib.import_module("paper_spider.conferences.usenix_security")
    except ModuleNotFoundError as exc:
        if exc.name == "paper_spider.conferences.usenix_security":
            raise AssertionError("USENIX Security conference module should exist") from exc
        raise
    return module.UsenixSecurityConference


class UsenixSecurityConferenceTests(unittest.TestCase):
    def test_conference_metadata_uses_usenix_family(self) -> None:
        conference_class = _load_conference_class()

        self.assertTrue(issubclass(conference_class, UsenixFamilyBase))
        self.assertEqual("USENIX Security", conference_class.name)
        self.assertEqual("usenix_security", conference_class.slug)
        self.assertEqual("usenixsecurity", conference_class.conf_prefix)

    def test_list_papers_uses_usenixsecurity_year_slug(self) -> None:
        conference_class = _load_conference_class()
        conf = conference_class()
        html = """
        <html><body>
          <article class="node node-paper view-mode-schedule">
            <h2><a href="/conference/usenixsecurity25/presentation/gibson">Security Paper</a></h2>
            <div class="content">
              <div class="field field-name-field-paper-people-text">
                <div class="field-item odd"><p>Alice and Bob, <em>Example Lab</em></p></div>
              </div>
              <div class="field field-name-field-paper-description-long">
                <p>Security abstract.</p>
              </div>
            </div>
          </article>
        </body></html>
        """

        with patch.object(conf, "_get", return_value=_FakeResponse(html)) as mock_get:
            papers = conf.list_papers(2025)

        self.assertEqual(
            "https://www.usenix.org/conference/usenixsecurity25/technical-sessions",
            mock_get.call_args[0][0],
        )
        self.assertEqual(1, len(papers))
        self.assertEqual("gibson", papers[0].paper_id)
        self.assertEqual("Security Paper", papers[0].title)
        self.assertEqual("usenix_security", papers[0].conf)
        self.assertEqual(["Alice", "Bob"], papers[0].authors)
        self.assertEqual("Security abstract.", papers[0].abstract)
        self.assertEqual(("technical", "conference"), (papers[0].track, papers[0].paper_type))


if __name__ == "__main__":
    unittest.main()
