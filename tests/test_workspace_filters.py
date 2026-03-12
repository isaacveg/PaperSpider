# Copyright 2026 Isaacveg
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#     http://www.apache.org/licenses/LICENSE-2.0

from __future__ import annotations

import unittest

from paper_spider.ui.workspace_window import FilterConfig, _filter_paper_rows


class WorkspaceFilterTests(unittest.TestCase):
    def setUp(self) -> None:
        self.rows = [
            {
                "title": "Efficient Systems",
                "category_text": "main / long",
                "abstract": "Fast storage pipeline",
                "authors_text": "Alice, Bob",
                "keywords_text": "systems, storage",
            },
            {
                "title": "Language Models",
                "category_text": "main / short",
                "abstract": "Transformer scaling laws",
                "authors_text": "Carol",
                "keywords_text": "nlp, llm",
            },
        ]

    def test_must_and_must_not_filters(self) -> None:
        filtered = _filter_paper_rows(
            self.rows,
            [
                FilterConfig(True, "all", "contains", "must", "storage"),
                FilterConfig(True, "title", "contains", "must_not", "language"),
            ],
            min_should_match=0,
        )

        self.assertEqual(["Efficient Systems"], [row["title"] for row in filtered])

    def test_should_filters_respect_minimum_matches(self) -> None:
        filtered = _filter_paper_rows(
            self.rows,
            [
                FilterConfig(True, "keywords", "contains", "should", "systems"),
                FilterConfig(True, "abstract", "contains", "should", "scaling"),
            ],
            min_should_match=1,
        )

        self.assertEqual(2, len(filtered))

        filtered = _filter_paper_rows(
            self.rows,
            [
                FilterConfig(True, "keywords", "contains", "should", "systems"),
                FilterConfig(True, "abstract", "contains", "should", "scaling"),
            ],
            min_should_match=2,
        )

        self.assertEqual([], filtered)

    def test_not_contains_mode(self) -> None:
        filtered = _filter_paper_rows(
            self.rows,
            [FilterConfig(True, "authors", "not_contains", "must", "alice")],
            min_should_match=0,
        )

        self.assertEqual(["Language Models"], [row["title"] for row in filtered])

    def test_category_filter_distinguishes_long_and_short(self) -> None:
        filtered = _filter_paper_rows(
            self.rows,
            [FilterConfig(True, "category", "contains", "must", "short")],
            min_should_match=0,
        )

        self.assertEqual(["Language Models"], [row["title"] for row in filtered])


if __name__ == "__main__":
    unittest.main()
