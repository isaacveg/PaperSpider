# Copyright 2026 Isaacveg
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#     http://www.apache.org/licenses/LICENSE-2.0

from __future__ import annotations

from contextlib import contextmanager
import threading
import time
from typing import Any, Callable, Iterator, Optional

import requests

from .base import ConferenceBase

USER_AGENT = "PaperSpider/0.1 (+https://localhost)"
RETRY_STATUS_CODES = frozenset({429, 500, 502, 503, 504})
MAX_RETRIES = 2
RETRY_BACKOFF_SECONDS = 1.0
MAX_RETRY_AFTER_SECONDS = 30.0


class RequestsConferenceBase(ConferenceBase):
    """Conference adapter base whose HTTP state is isolated per worker thread."""

    def __init__(self) -> None:
        self.request_delay = 0.1
        self._local = threading.local()
        self._session_override: Optional[requests.Session] = None

    @property
    def session(self) -> requests.Session:
        if self._session_override is not None:
            return self._session_override
        session = getattr(self._local, "session", None)
        if session is None:
            session = requests.Session()
            session.headers.update({"User-Agent": USER_AGENT})
            self._local.session = session
        return session

    @session.setter
    def session(self, value: requests.Session) -> None:
        self._session_override = value

    @contextmanager
    def cancellable(self, cancelled: Callable[[], bool]) -> Iterator[None]:
        previous = getattr(self._local, "cancel_checker", None)
        self._local.cancel_checker = cancelled
        try:
            yield
        finally:
            self._local.cancel_checker = previous

    def last_request_error(self) -> Optional[str]:
        """Describe the most recent failed request made by the current thread."""

        return getattr(self._local, "last_error", None)

    def _request(
        self,
        url: str,
        *,
        params: Optional[dict[str, Any]] = None,
        binary: bool = False,
        headers: Optional[dict[str, str]] = None,
    ) -> Optional[requests.Response]:
        self._local.last_error = None
        self._raise_if_cancelled()
        wait = self.request_delay
        for attempt in range(MAX_RETRIES + 1):
            self._sleep(wait)
            backoff = RETRY_BACKOFF_SECONDS * (2**attempt)
            try:
                resp = self.session.get(
                    url, params=params, timeout=(5, 20), headers=headers
                )
            except (requests.ConnectionError, requests.Timeout) as exc:
                self._local.last_error = f"{type(exc).__name__} for {url}"
                wait = backoff
                continue
            except requests.RequestException as exc:
                self._local.last_error = f"{type(exc).__name__} for {url}"
                return None
            self._raise_if_cancelled()
            if resp.status_code == 200:
                self._local.last_error = None
                if not binary:
                    resp.encoding = resp.encoding or "utf-8"
                return resp
            self._local.last_error = f"HTTP {resp.status_code} for {url}"
            if resp.status_code not in RETRY_STATUS_CODES:
                return None
            wait = _retry_after_seconds(resp) or backoff
        return None

    def _get(
        self,
        url: str,
        binary: bool = False,
        params: Optional[dict[str, Any]] = None,
    ) -> Optional[requests.Response]:
        return self._request(url, params=params, binary=binary)

    def _sleep(self, seconds: float) -> None:
        remaining = seconds
        while remaining > 0:
            self._raise_if_cancelled()
            interval = min(remaining, 0.05)
            time.sleep(interval)
            remaining -= interval

    def _raise_if_cancelled(self) -> None:
        checker = getattr(self._local, "cancel_checker", None)
        if checker and checker():
            raise RuntimeError("Request cancelled")


def _retry_after_seconds(resp: requests.Response) -> Optional[float]:
    raw = resp.headers.get("Retry-After")
    if raw is None:
        return None
    try:
        return max(0.0, min(MAX_RETRY_AFTER_SECONDS, float(raw)))
    except ValueError:
        return None
