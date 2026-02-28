# Copyright 2026 Isaacveg
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#     http://www.apache.org/licenses/LICENSE-2.0

from __future__ import annotations

import unittest

from paper_spider.conferences import available_conferences


class ConferenceRegistryTests(unittest.TestCase):
    def test_available_conference_slugs(self) -> None:
        slugs = {conf.slug for conf in available_conferences()}
        self.assertIn("neurips", slugs)
        self.assertIn("icml", slugs)
        self.assertIn("iclr", slugs)


if __name__ == "__main__":
    unittest.main()
