# Copyright 2026 Isaacveg
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#     http://www.apache.org/licenses/LICENSE-2.0

from __future__ import annotations

import threading
import unittest
from unittest import mock

from paper_spider.conferences import request_base
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

    def test_cancel_checker_is_isolated_per_thread(self) -> None:
        conf = _ConcreteRequestsConference()
        entered = threading.Event()
        release = threading.Event()
        seen = {}

        def other_thread() -> None:
            with conf.cancellable(lambda: False):
                entered.set()
                release.wait(2)
                try:
                    conf._raise_if_cancelled()
                    seen["other"] = "ok"
                except RuntimeError:
                    seen["other"] = "cancelled"

        thread = threading.Thread(target=other_thread)
        thread.start()
        entered.wait(2)
        with conf.cancellable(lambda: True):
            with self.assertRaises(RuntimeError):
                conf._raise_if_cancelled()
            release.set()
            thread.join(2)

        self.assertEqual("ok", seen["other"])
        conf._raise_if_cancelled()

    def test_sessions_are_created_per_thread(self) -> None:
        conf = _ConcreteRequestsConference()
        sessions = []
        thread = threading.Thread(target=lambda: sessions.append(conf.session))
        thread.start()
        thread.join(2)

        self.assertIsNot(conf.session, sessions[0])
        self.assertIs(conf.session, conf.session)

    def test_retries_transient_status_and_records_last_error(self) -> None:
        conf = _ConcreteRequestsConference()
        conf.request_delay = 0
        session = _SequenceSession([503, 200])
        conf.session = session

        with mock.patch.object(request_base, "RETRY_BACKOFF_SECONDS", 0):
            response = conf._get("https://example.com/a")

        self.assertEqual(200, response.status_code)
        self.assertEqual(2, len(session.calls))
        self.assertIsNone(conf.last_request_error())

    def test_does_not_retry_client_errors(self) -> None:
        conf = _ConcreteRequestsConference()
        conf.request_delay = 0
        session = _SequenceSession([404, 200])
        conf.session = session

        self.assertIsNone(conf._get("https://example.com/missing"))
        self.assertEqual(1, len(session.calls))
        self.assertEqual(
            "HTTP 404 for https://example.com/missing", conf.last_request_error()
        )


class _SequenceSession(_FakeSession):
    def __init__(self, statuses) -> None:
        super().__init__()
        self._statuses = list(statuses)

    def get(self, url, params=None, timeout=None, headers=None):
        super().get(url, params=params, timeout=timeout, headers=headers)
        response = _FakeResponse(self._statuses.pop(0))
        response.headers = {}
        return response


if __name__ == "__main__":
    unittest.main()
