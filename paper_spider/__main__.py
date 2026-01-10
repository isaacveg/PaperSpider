# Copyright 2026 Isaacveg
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#     http://www.apache.org/licenses/LICENSE-2.0

import sys

from PyQt6.QtWidgets import QApplication

from paper_spider.ui.workspace_window import WorkspaceWindow


def main() -> None:
    app = QApplication(sys.argv)
    window = WorkspaceWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
