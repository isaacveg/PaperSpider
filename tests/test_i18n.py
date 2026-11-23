# Copyright 2026 Isaacveg
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#     http://www.apache.org/licenses/LICENSE-2.0

from __future__ import annotations

import os
import unittest
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("PAPERSPIDER_LANG", "en")

from paper_spider.ui import i18n


class LocalizationTests(unittest.TestCase):
    def tearDown(self) -> None:
        i18n.set_language("en")

    def test_language_override_and_system_detection(self) -> None:
        with patch.dict(os.environ, {"PAPERSPIDER_LANG": "en"}):
            i18n.reset_language()
            self.assertEqual("en", i18n.current_language())
        with patch.dict(os.environ, {"PAPERSPIDER_LANG": "zh"}):
            i18n.reset_language()
            self.assertEqual("zh", i18n.current_language())
        i18n.set_language("en")

    def test_chinese_copy_covers_workspace_labels(self) -> None:
        i18n.set_language("zh")
        self.assertEqual("全部论文", i18n.tr("All papers"))
        self.assertEqual("筛选", i18n.tr("Filters"))
        self.assertEqual("会议数据集", i18n.tr("Conference datasets"))
        self.assertEqual("在结果中搜索", i18n.tr("Search in results"))
        self.assertEqual("下载摘要", i18n.tr("Download abstracts"))
        self.assertEqual("论文 / 作者", i18n.tr("Papers / authors"))
        self.assertEqual("包含", i18n.tr("Include"))
        self.assertEqual("排除", i18n.tr("Exclude"))
        self.assertEqual("跟随系统", i18n.tr("System"))

    def test_count_helpers_handle_singular_and_plural(self) -> None:
        i18n.set_language("en")
        self.assertEqual("1 paper", i18n.paper_count(1))
        self.assertEqual("3 papers", i18n.paper_count(3))
        self.assertEqual("1 match", i18n.match_count(1))
        self.assertEqual("3 matches", i18n.match_count(3))
        self.assertEqual("2 selected", i18n.selected_count(2))

        i18n.set_language("zh")
        self.assertEqual("1 篇论文", i18n.paper_count(1))
        self.assertEqual("3 篇论文", i18n.paper_count(3))
        self.assertEqual("1 篇匹配", i18n.match_count(1))
        self.assertEqual("2 篇匹配", i18n.match_count(2))
        self.assertEqual("已选 2 篇", i18n.selected_count(2))

    def test_category_display_follows_language(self) -> None:
        i18n.set_language("en")
        self.assertEqual(
            "main / conference", i18n.display_category("main", "conference")
        )
        i18n.set_language("zh")
        self.assertEqual(
            "主会 / 会议论文", i18n.display_category("main", "conference")
        )
        self.assertEqual(
            "技术 / 会议论文", i18n.display_category("technical", "conference")
        )


if __name__ == "__main__":
    unittest.main()