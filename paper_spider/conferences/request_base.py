# Copyright 2026 Isaacveg
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#     http://www.apache.org/licenses/LICENSE-2.0

from __future__ import annotations

from contextlib import contextmanager
import time
from typing import Any, Callable, Iterator, Optional

import requests

from .base import ConferenceBase


class RequestsConferenceBase(ConferenceBase):
    def __init__(self) -> None:
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "PaperSpider/0.1 (+https://localhost)"})
        self.request_delay = 0.1
        self._cancel_checker: Optional[Callable[[], bool]] = None

    @contextmanager
    def cancellable(self, cancelled: Callable[[], bool]) -> Iterator[None]:
        previous = self._cancel_checker
        self._cancel_checker = cancelled
        try:
            yield
        finally:
            self._cancel_checker = previous

    def _request(
        self,
        url: str,
        *,
        params: Optional[dict[str, Any]] = None,
        binary: bool = False,
        headers: Optional[dict[str, str]] = None,
    ) -> Optional[requests.Response]:
        self._raise_if_cancelled()
        self._sleep_request_delay()
        try:
            resp = self.session.get(url, params=params, timeout=(5, 20), headers=headers)
        except requests.RequestException:
            return None
        self._raise_if_cancelled()
        if resp.status_code != 200:
            return None
        if binary:
            return resp
        resp.encoding = resp.encoding or "utf-8"
        return resp

    def _get(
        self,
        url: str,
        binary: bool = False,
        params: Optional[dict[str, Any]] = None,
    ) -> Optional[requests.Response]:
        return self._request(url, params=params, binary=binary)

    def _sleep_request_delay(self) -> None:
        remaining = self.request_delay
        while remaining > 0:
            self._raise_if_cancelled()
            interval = min(remaining, 0.05)
            time.sleep(interval)
            remaining -= interval

    def _raise_if_cancelled(self) -> None:
        if self._cancel_checker and self._cancel_checker():
            raise RuntimeError("Request cancelled")
