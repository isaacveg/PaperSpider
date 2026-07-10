from __future__ import annotations

import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication, QMessageBox

from paper_spider.ui.dialog_utils import build_message_box


def app() -> QApplication:
    existing = QApplication.instance()
    if existing is not None:
        return existing
    return QApplication([])


class MessageDialogTests(unittest.TestCase):
    def setUp(self) -> None:
        self.app = app()

    def test_message_box_has_no_window_chrome_and_uses_close_action(self) -> None:
        box = build_message_box(
            None,
            QMessageBox.Icon.Warning,
            "Unable to load",
            "The proceedings page could not be loaded.",
        )

        self.assertTrue(box.windowFlags() & Qt.WindowType.FramelessWindowHint)
        self.assertEqual("messageDialog", box.objectName())
        close_button = box.button(QMessageBox.StandardButton.Close)
        self.assertIsNotNone(close_button)
        self.assertEqual("Close", close_button.text())
        self.assertIs(close_button, box.escapeButton())


if __name__ == "__main__":
    unittest.main()
