# Copyright 2026 Isaacveg
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#     http://www.apache.org/licenses/LICENSE-2.0

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class PaperMeta:
    paper_id: str
    title: str
    conf: str
    year: int
    detail_url: Optional[str] = None
    authors: List[str] = field(default_factory=list)
    abstract: Optional[str] = None
    keywords: List[str] = field(default_factory=list)
    pdf_url: Optional[str] = None
    bibtex_url: Optional[str] = None
    bibtex: Optional[str] = None

    def to_row(self) -> dict:
        return {
            "paper_id": self.paper_id,
            "title": self.title,
            "conf": self.conf,
            "year": self.year,
            "detail_url": self.detail_url,
            "authors": self.authors,
            "abstract": self.abstract,
            "keywords": self.keywords,
            "pdf_url": self.pdf_url,
            "bibtex_url": self.bibtex_url,
            "bibtex": self.bibtex,
        }
