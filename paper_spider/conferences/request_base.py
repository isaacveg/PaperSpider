# Copyright 2026 Isaacveg
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#     http://www.apache.org/licenses/LICENSE-2.0

from __future__ import annotations

import time
from typing import Any, Optional

import requests

from .base import ConferenceBase


class RequestsConferenceBase(ConferenceBase):
    def __init__(self) -> None:
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "PaperSpider/0.1 (+https://localhost)"})
        self.request_delay = 0.1

    def _request(
        self,
        url: str,
        *,
        params: Optional[dict[str, Any]] = None,
        binary: bool = False,
        headers: Optional[dict[str, str]] = None,
    ) -> Optional[requests.Response]:
        if self.request_delay > 0:
            time.sleep(self.request_delay)
        try:
            resp = self.session.get(url, params=params, timeout=30, headers=headers)
        except requests.RequestException:
            return None
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
