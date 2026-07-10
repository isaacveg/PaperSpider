from __future__ import annotations

import unittest

from paper_spider.conferences.author_utils import split_author_names


class AuthorUtilsTests(unittest.TestCase):
    def test_split_author_names_handles_common_delimiters(self) -> None:
        self.assertEqual(["Alice", "Bob"], split_author_names("Alice and Bob"))
        self.assertEqual(["Alice", "Bob"], split_author_names("Alice; Bob"))
        self.assertEqual(["Alice", "Bob"], split_author_names("Authors: Alice, Bob"))

    def test_split_author_names_preserves_non_ascii_names(self) -> None:
        self.assertEqual(
            ["S. Akshay", "Krishnendu Chatterjee", "Đorđe Žikelić"],
            split_author_names("S. Akshay, Krishnendu Chatterjee, Đorđe Žikelić"),
        )


if __name__ == "__main__":
    unittest.main()
