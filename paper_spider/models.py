# Copyright 2026 Isaacveg
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#     http://www.apache.org/licenses/LICENSE-2.0

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass(frozen=True)
class PaperCategory:
    track: str = "main"
    paper_type: str = "conference"

    def __post_init__(self) -> None:
        track = self.track.strip() or "main"
        paper_type = self.paper_type.strip() or "conference"
        object.__setattr__(self, "track", track)
        object.__setattr__(self, "paper_type", paper_type)

    @classmethod
    def from_fields(cls, track: Optional[str], paper_type: Optional[str]) -> "PaperCategory":
        return cls(
            track=(track or "main").strip() or "main",
            paper_type=(paper_type or "conference").strip() or "conference",
        )

    @property
    def label(self) -> str:
        return f"{self.track} / {self.paper_type}"


@dataclass
class PaperMeta:
    paper_id: str
    title: str
    conf: str
    year: int
    category: PaperCategory = field(default_factory=PaperCategory)
    detail_url: Optional[str] = None
    authors: List[str] = field(default_factory=list)
    abstract: Optional[str] = None
    keywords: List[str] = field(default_factory=list)
    pdf_url: Optional[str] = None
    bibtex_url: Optional[str] = None
    bibtex: Optional[str] = None

    @property
    def track(self) -> str:
        return self.category.track

    @property
    def paper_type(self) -> str:
        return self.category.paper_type

    @property
    def category_text(self) -> str:
        return self.category.label

    def to_row(self) -> dict:
        return {
            "paper_id": self.paper_id,
            "title": self.title,
            "conf": self.conf,
            "year": self.year,
            "track": self.category.track,
            "paper_type": self.category.paper_type,
            "detail_url": self.detail_url,
            "authors": self.authors,
            "abstract": self.abstract,
            "keywords": self.keywords,
            "pdf_url": self.pdf_url,
            "bibtex_url": self.bibtex_url,
            "bibtex": self.bibtex,
        }
