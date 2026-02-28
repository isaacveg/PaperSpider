# Copyright 2026 Isaacveg
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#     http://www.apache.org/licenses/LICENSE-2.0

from __future__ import annotations

import json
import unittest

from paper_spider.export_utils import build_export_text


class ExportUtilsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.rows = [
            {
                "title": "Paper A",
                "authors": '["Alice", "Bob"]',
                "abstract": "Abstract A",
            },
            {
                "title": "Paper B",
                "authors": "Carol, Dan",
                "abstract": "Abstract B",
            },
        ]

    def test_plain_text_export(self) -> None:
        output = build_export_text(
            rows=self.rows,
            export_format="txt",
            include_title=False,
            include_authors=False,
            include_abstract=False,
        )
        self.assertEqual("Paper A\nPaper B", output)

    def test_json_export_with_selected_fields(self) -> None:
        output = build_export_text(
            rows=self.rows,
            export_format="json",
            include_title=True,
            include_authors=True,
            include_abstract=False,
        )
        parsed = json.loads(output)
        self.assertEqual("Paper A", parsed[0]["title"])
        self.assertEqual(["Alice", "Bob"], parsed[0]["authors"])
        self.assertNotIn("abstract", parsed[0])

    def test_csv_export_with_abstract(self) -> None:
        output = build_export_text(
            rows=self.rows,
            export_format="csv",
            include_title=True,
            include_authors=False,
            include_abstract=True,
        )
        self.assertIn("title,abstract", output)
        self.assertIn("Paper A,Abstract A", output)

    def test_csv_or_json_requires_fields(self) -> None:
        with self.assertRaises(ValueError):
            build_export_text(
                rows=self.rows,
                export_format="csv",
                include_title=False,
                include_authors=False,
                include_abstract=False,
            )


if __name__ == "__main__":
    unittest.main()
