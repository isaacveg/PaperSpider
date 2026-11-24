# Copyright 2026 Isaacveg
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#     http://www.apache.org/licenses/LICENSE-2.0

from __future__ import annotations

import os
import tempfile
import unittest

from paper_spider.artifacts import (
    safe_filename,
    unique_artifact_path,
    write_binary_artifact,
    write_text_artifact,
)


class ArtifactTests(unittest.TestCase):
    def test_safe_filename_removes_unsafe_characters_and_compacts_spaces(self) -> None:
        self.assertEqual(
            "A_Paper_Title_v2",
            safe_filename(' A Paper: "Title" / v2? ', "fallback"),
        )

    def test_safe_filename_uses_fallback_when_title_has_no_safe_characters(self) -> None:
        self.assertEqual("paper-1", safe_filename("$$$   ", "paper-1"))

    def test_unique_artifact_path_adds_suffix_when_file_exists(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            existing = os.path.join(temp_dir, "paper.pdf")
            with open(existing, "wb") as f:
                f.write(b"x")

            path = unique_artifact_path(temp_dir, "paper", "pdf", "paper-1")

        self.assertTrue(path.endswith("paper_paper-1.pdf"))

    def test_unique_artifact_path_never_returns_an_existing_file(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            for name in ("paper.pdf", "paper_paper-1.pdf"):
                with open(os.path.join(temp_dir, name), "wb") as f:
                    f.write(b"x")

            path = unique_artifact_path(temp_dir, "paper", "pdf", "paper-1")

        self.assertTrue(path.endswith("paper_paper-1_2.pdf"))

    def test_atomic_write_replaces_content_without_leaving_temp_files(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = os.path.join(temp_dir, "paper.bib")
            write_text_artifact(path, "old")
            write_text_artifact(path, "new")
            write_binary_artifact(os.path.join(temp_dir, "paper.pdf"), b"%PDF")

            with open(path, encoding="utf-8") as f:
                content = f.read()
            names = sorted(os.listdir(temp_dir))

        self.assertEqual("new", content)
        self.assertEqual(["paper.bib", "paper.pdf"], names)


if __name__ == "__main__":
    unittest.main()
