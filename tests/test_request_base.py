# Copyright 2026 Isaacveg
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#     http://www.apache.org/licenses/LICENSE-2.0

from __future__ import annotations

import unittest

from paper_spider.conferences.request_base import RequestsConferenceBase


class _FakeResponse:
    def __init__(self, status_code: int = 200) -> None:
        self.status_code = status_code
        self.encoding = None
        self.text = "ok"
        self.content = b"ok"


class _FakeSession:
    def __init__(self) -> None:
        self.headers = {}
        self.calls = []

    def get(self, url, params=None, timeout=None, headers=None):
        self.calls.append(
            {
                "url": url,
                "params": params,
                "timeout": timeout,
                "headers": headers,
            }
        )
        return _FakeResponse()


class _ConcreteRequestsConference(RequestsConferenceBase):
    name = "Concrete"
    slug = "concrete"

    def list_papers(self, year):
        return []

    def fetch_details(self, paper):
        return paper

    def fetch_pdf(self, paper):
        return b""

    def fetch_bibtex(self, paper):
        return ""


class RequestsConferenceBaseTests(unittest.TestCase):
    def test_get_preserves_positional_binary_argument(self) -> None:
        conf = _ConcreteRequestsConference()
        conf.request_delay = 0
        session = _FakeSession()
        conf.session = session

        response = conf._get("https://example.com/paper.pdf", True)

        self.assertEqual(b"ok", response.content)
        self.assertEqual("https://example.com/paper.pdf", session.calls[0]["url"])

    def test_get_passes_query_params_to_session(self) -> None:
        conf = _ConcreteRequestsConference()
        conf.request_delay = 0
        session = _FakeSession()
        conf.session = session

        conf._get("https://api.example.com/notes", params={"limit": 1000})

        self.assertEqual({"limit": 1000}, session.calls[0]["params"])


if __name__ == "__main__":
    unittest.main()
