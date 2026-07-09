from __future__ import annotations

import unittest

from paper_spider.ui.workspace_view_helpers import (
    WorkspaceSummary,
    paper_id_for_row,
    reconcile_selected_ids,
    summarize_rows,
)


class WorkspaceViewHelpersTests(unittest.TestCase):
    def test_summarize_rows_counts_visible_states(self) -> None:
        rows = [
            {"paper_id": "p1", "abstract_status": 1, "has_pdf": True, "has_bib": True},
            {"paper_id": "p2", "abstract_status": 0, "has_pdf": False, "has_bib": True},
            {"paper_id": "p3", "abstract_status": True, "has_pdf": True, "has_bib": False},
        ]

        self.assertEqual(
            WorkspaceSummary(total=3, abstracts=2, pdfs=2, bibs=2),
            summarize_rows(rows),
        )

    def test_reconcile_selected_ids_keeps_only_visible_rows(self) -> None:
        rows = [{"paper_id": "p1"}, {"paper_id": "p3"}]

        self.assertEqual({"p1", "p3"}, reconcile_selected_ids(rows, {"p1", "p2", "p3"}))

    def test_paper_id_for_row_normalizes_to_string(self) -> None:
        self.assertEqual("42", paper_id_for_row({"paper_id": 42}))


if __name__ == "__main__":
    unittest.main()
