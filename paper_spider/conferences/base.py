# Copyright 2026 Isaacveg
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#     http://www.apache.org/licenses/LICENSE-2.0

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Iterable, List

from ..models import PaperMeta


class ConferenceBase(ABC):
    name: str
    slug: str

    @abstractmethod
    def list_papers(self, year: int) -> List[PaperMeta]:
        raise NotImplementedError

    @abstractmethod
    def fetch_details(self, paper: PaperMeta) -> PaperMeta:
        raise NotImplementedError

    @abstractmethod
    def fetch_pdf(self, paper: PaperMeta) -> bytes:
        raise NotImplementedError

    @abstractmethod
    def fetch_bibtex(self, paper: PaperMeta) -> str:
        raise NotImplementedError
