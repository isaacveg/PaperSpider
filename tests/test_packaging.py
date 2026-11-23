# Copyright 2026 Isaacveg
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import annotations

import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from zipfile import ZipFile


REPO_ROOT = Path(__file__).resolve().parents[1]
REQUIRED_UI_SVGS = {
    "paper_spider/ui/assets/check-dark.svg",
    "paper_spider/ui/assets/check-light.svg",
    "paper_spider/ui/assets/chevron-down-dark.svg",
    "paper_spider/ui/assets/chevron-down-light.svg",
    "paper_spider/ui/assets/chevron-left-dark.svg",
    "paper_spider/ui/assets/chevron-left-light.svg",
    "paper_spider/ui/assets/chevron-right-dark.svg",
    "paper_spider/ui/assets/chevron-right-light.svg",
    "paper_spider/ui/assets/dash-dark.svg",
    "paper_spider/ui/assets/dash-light.svg",
    "paper_spider/ui/assets/filter-dark.svg",
    "paper_spider/ui/assets/filter-light.svg",
    "paper_spider/ui/assets/folder-dark.svg",
    "paper_spider/ui/assets/folder-light.svg",
    "paper_spider/ui/assets/nav-all-dark.svg",
    "paper_spider/ui/assets/nav-all-light.svg",
    "paper_spider/ui/assets/nav-dataset-dark.svg",
    "paper_spider/ui/assets/nav-dataset-light.svg",
    "paper_spider/ui/assets/nav-settings-dark.svg",
    "paper_spider/ui/assets/nav-settings-light.svg",
    "paper_spider/ui/assets/refresh-dark.svg",
    "paper_spider/ui/assets/refresh-light.svg",
    "paper_spider/ui/assets/search-dark.svg",
    "paper_spider/ui/assets/search-light.svg",
}
REQUIRED_UI_PNG = {
    "paper_spider/ui/assets/app-icon.png",
}
REQUIRED_CLI_FILES = {
    "paper_spider/cli.py",
    "paper_spider/operations.py",
}
REQUIRED_MAN_PAGE = "share/man/man1/paperspider-cli.1"


class WheelPackagingTests(unittest.TestCase):
    def test_wheel_contains_required_package_data(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            isolated_root = Path(temp_dir) / "source"
            isolated_root.mkdir()
            for filename in ("pyproject.toml", "README.md", "LICENSE"):
                shutil.copy2(REPO_ROOT / filename, isolated_root / filename)
            shutil.copytree(REPO_ROOT / "paper_spider", isolated_root / "paper_spider")
            shutil.copytree(REPO_ROOT / "man", isolated_root / "man")

            wheel_dir = Path(temp_dir) / "wheelhouse"
            result = subprocess.run(
                ["uv", "build", "--wheel", "--out-dir", str(wheel_dir)],
                cwd=isolated_root,
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(0, result.returncode, result.stdout + result.stderr)
            wheels = list(wheel_dir.glob("*.whl"))
            self.assertEqual(1, len(wheels), result.stdout + result.stderr)

            with ZipFile(wheels[0]) as wheel:
                wheel_members = set(wheel.namelist())

        self.assertEqual(set(), REQUIRED_UI_SVGS - wheel_members)
        self.assertEqual(set(), REQUIRED_UI_PNG - wheel_members)
        self.assertEqual(set(), REQUIRED_CLI_FILES - wheel_members)
        self.assertTrue(
            any(member.endswith(REQUIRED_MAN_PAGE) for member in wheel_members)
        )


if __name__ == "__main__":
    unittest.main()
