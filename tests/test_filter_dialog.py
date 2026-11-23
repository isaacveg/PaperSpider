# Copyright 2026 Isaacveg
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#     http://www.apache.org/licenses/LICENSE-2.0

from __future__ import annotations

import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("PAPERSPIDER_LANG", "en")

from PyQt6.QtWidgets import QApplication

from paper_spider.filtering import FilterConfig
from paper_spider.ui.filter_dialog import FilterDialog, FilterRow


_APPLICATION = QApplication.instance() or QApplication([])


class FilterDialogTests(unittest.TestCase):
    def setUp(self) -> None:
        self.app = _APPLICATION

    def test_dialog_round_trips_configs_and_minimum(self) -> None:
        configs = [
            FilterConfig(True, "title", "contains", "must", "systems"),
            FilterConfig(False, "authors", "contains", "must not", "ignored"),
            FilterConfig(True, "keywords", "contains", "should", "cache"),
        ]
        dialog = FilterDialog(configs=configs, min_should_match=1)

        self.assertEqual([configs[0], configs[2]], dialog.filter_configs())
        self.assertEqual(1, dialog.min_should_match())
        self.assertEqual(3, len(dialog._rows))

    def test_rows_append_remove_and_clear(self) -> None:
        dialog = FilterDialog()
        self.assertEqual(1, len(dialog._rows))

        row = dialog._add_row()
        row.text_edit.setText("systems")
        self.assertEqual(2, len(dialog._rows))

        dialog._remove_row(row)
        self.assertEqual(1, len(dialog._rows))

        dialog._rows[0].text_edit.setText("cache")
        dialog._clear_filters()
        self.assertEqual(1, len(dialog._rows))
        self.assertEqual([], dialog.filter_configs())

    def test_should_count_requires_enabled_non_empty_prefer_rule(self) -> None:
        dialog = FilterDialog()
        row = dialog._rows[0]
        row.role_combo.setCurrentIndex(row.role_combo.findText("Prefer"))

        self.assertEqual(0, dialog._should_count())
        row.text_edit.setText("systems")
        self.assertEqual(1, dialog._should_count())
        row.enable_checkbox.setChecked(False)
        self.assertEqual(0, dialog._should_count())

    def test_filter_row_config_reads_all_controls(self) -> None:
        row = FilterRow()
        row.text_edit.setText("diffusion")
        row.role_combo.setCurrentIndex(row.role_combo.findText("Exclude"))
        row.field_combo.setCurrentIndex(row.field_combo.findText("Title"))
        row.mode_combo.setCurrentIndex(row.mode_combo.findText("does not contain"))

        config = row.config()
        self.assertTrue(config.enabled)
        self.assertEqual("diffusion", config.value)
        self.assertEqual("must not", config.role)
        self.assertEqual("title", config.field)
        self.assertEqual("not_contains", config.mode)


if __name__ == "__main__":
    unittest.main()