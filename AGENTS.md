# PaperSpider agent notes

## Verification

- Tests (unittest, no pytest): `QT_QPA_PLATFORM=offscreen .venv/bin/python -m unittest discover -s tests`
- CI runs each `tests/test_*.py` file separately with `uv run python -m unittest discover -s tests -p <file>`.
- Lint (no project ruff config; check pyflakes rules only): `uvx ruff check --select F paper_spider tests`

## Testing notes

- Window tests must not touch the real `QSettings("PaperSpider", "PaperSpider")`; `tests/test_workspace_window_ui.py` patches `paper_spider.ui.workspace_window.app_settings` to a temp INI file in `setUp`.
- Clear running cancel tokens before closing a `WorkspaceWindow` in tests, otherwise `closeEvent` opens a blocking quit confirmation.
- Wait for `window.thread_pool.waitForDone()` and `processEvents()` before mocking window methods, so the initial load worker cannot call into mocks.
