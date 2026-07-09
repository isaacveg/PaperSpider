# Copyright 2026 Isaacveg
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#     http://www.apache.org/licenses/LICENSE-2.0

from __future__ import annotations

import os
import tempfile
import unittest

from paper_spider.artifacts import safe_filename, unique_artifact_path


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


if __name__ == "__main__":
    unittest.main()
