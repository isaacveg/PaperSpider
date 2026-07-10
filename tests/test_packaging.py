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
    "paper_spider/ui/assets/chevron-down-dark.svg",
    "paper_spider/ui/assets/chevron-down-light.svg",
    "paper_spider/ui/assets/status-abstract-dark.svg",
    "paper_spider/ui/assets/status-abstract-light.svg",
    "paper_spider/ui/assets/status-pdf-dark.svg",
    "paper_spider/ui/assets/status-pdf-light.svg",
}


class WheelPackagingTests(unittest.TestCase):
    def test_wheel_contains_all_required_ui_svg_assets(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            isolated_root = Path(temp_dir) / "source"
            isolated_root.mkdir()
            for filename in ("pyproject.toml", "README.md", "LICENSE"):
                shutil.copy2(REPO_ROOT / filename, isolated_root / filename)
            shutil.copytree(REPO_ROOT / "paper_spider", isolated_root / "paper_spider")

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


if __name__ == "__main__":
    unittest.main()
