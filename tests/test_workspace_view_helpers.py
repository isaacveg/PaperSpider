from __future__ import annotations

import unittest

from paper_spider.ui.workspace_view_helpers import (
    paper_id_for_row,
    reconcile_selected_ids,
)


class WorkspaceViewHelpersTests(unittest.TestCase):
    def test_reconcile_selected_ids_keeps_only_visible_rows(self) -> None:
        rows = [{"paper_id": "p1"}, {"paper_id": "p3"}]

        self.assertEqual({"p1", "p3"}, reconcile_selected_ids(rows, {"p1", "p2", "p3"}))

    def test_paper_id_for_row_normalizes_to_string(self) -> None:
        self.assertEqual("42", paper_id_for_row({"paper_id": 42}))


if __name__ == "__main__":
    unittest.main()
