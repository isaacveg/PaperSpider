# Copyright 2026 Isaacveg
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#     http://www.apache.org/licenses/LICENSE-2.0

from __future__ import annotations

import unittest

from paper_spider.ui.theme import (
    DEFAULT_THEME,
    THEMES,
    appearance_from_values,
    build_stylesheet,
    selected_theme,
)


class FakeSettings:
    def __init__(self, values: dict[str, object] | None = None) -> None:
        self.values = values or {}

    def value(self, key: str, default=None):
        return self.values.get(key, default)


class ThemeResolutionTests(unittest.TestCase):
    def test_theme_choices_include_system(self) -> None:
        self.assertEqual(("System", "Light", "Dark"), THEMES)
        self.assertEqual("Light", DEFAULT_THEME)

    def test_system_theme_resolves_to_light_or_dark(self) -> None:
        dark = appearance_from_values(
            "System", "Blue", system_theme_name="Dark"
        )
        self.assertEqual("Dark", dark.theme)
        self.assertEqual("#1b1c1b", dark.background)
        self.assertIn("#1b1c1b", build_stylesheet(dark))

        light = appearance_from_values(
            "System", "Blue", system_theme_name="Light"
        )
        self.assertEqual("Light", light.theme)
        self.assertEqual("#f8f8fa", light.background)

    def test_explicit_theme_ignores_system_scheme(self) -> None:
        appearance = appearance_from_values(
            "Dark", "Green", system_theme_name="Light"
        )
        self.assertEqual("Dark", appearance.theme)
        self.assertEqual("#4ade80", appearance.accent_color)
        light = appearance_from_values(
            "Light", "Green", system_theme_name="Dark"
        )
        self.assertEqual("#16a34a", light.accent_color)

    def test_unknown_theme_defaults_to_light(self) -> None:
        appearance = appearance_from_values(
            "Unknown", "Blue", system_theme_name="Dark"
        )
        self.assertEqual("Light", appearance.theme)

    def test_selected_theme_reads_saved_choice_and_validates(self) -> None:
        self.assertEqual(
            "System", selected_theme(FakeSettings({"appearance/theme": "System"}))
        )
        self.assertEqual(
            "Dark", selected_theme(FakeSettings({"appearance/theme": "Dark"}))
        )
        self.assertEqual(
            "Light", selected_theme(FakeSettings({"appearance/theme": "Unknown"}))
        )


if __name__ == "__main__":
    unittest.main()