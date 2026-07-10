# PaperSpider Workspace UI Modernization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver a modern, intuitive PaperSpider workspace with direct filters, top-level quick search, clean table selection/status visuals, compact settings, and consistent native windows.

**Architecture:** Keep the existing PyQt6 modular monolith. Change only UI widgets, models, theme resources, and their tests; preserve the existing storage, service, worker, and conference interfaces.

**Tech Stack:** Python 3.12, PyQt6 6.10, `unittest`, Qt model/view, Qt Style Sheets, bundled SVG resources.

## Global Constraints

- Keep the existing PyQt6, SQLite, synchronous-adapter, and `QThreadPool` architecture.
- The quick paper search is in the top workspace bar at the same visual level as the dataset summary.
- Structured filters use Include, Prefer, and Exclude language while preserving must, should, and must-not semantics.
- The table has no Qt vertical row-header gutter and keeps its own `#` column.
- Selection has empty, checked, and partially-selected dash states; state is not communicated by color alone.
- Status artwork uses bundled SVG resources, not emoji text.
- Main, Dataset, Settings, and Export use native OS window chrome with no custom traffic lights or Windows controls.
- Settings topics have visible spacing and separators in a compact single-column layout.
- No MVVM framework, dependency injection container, web frontend, ORM, asyncio integration, or plugin system.
- Every behavior change follows red-green-refactor TDD.
- All existing tests must remain green.

---

### Task 1: Paper table selection and SVG statuses

**Files:**
- Create: `paper_spider/ui/assets/status-abstract-light.svg`
- Create: `paper_spider/ui/assets/status-abstract-dark.svg`
- Create: `paper_spider/ui/assets/status-pdf-light.svg`
- Create: `paper_spider/ui/assets/status-pdf-dark.svg`
- Modify: `paper_spider/ui/paper_table_model.py`
- Modify: `paper_spider/ui/workspace_window.py`
- Modify: `paper_spider/ui/theme.py`
- Test: `tests/test_paper_table_model.py`
- Test: `tests/test_workspace_window_ui.py`
- Test: `tests/test_workspace_widgets.py`

**Interfaces:**
- Consumes: existing `PaperTableModel.selection_state()`, `has_pdf`, `abstract_status`, and `abstract` row fields.
- Produces: a hidden `QTableView.verticalHeader()`, a `#` model header, tri-state header rendering, and themed SVG status icon roles/tooltips.

- [ ] **Step 1: Write failing model and window tests**

Add tests asserting that the first display header is `#`, the table vertical header is hidden, status display text contains no emoji, status decoration/tooltips distinguish abstract/PDF availability, and header check state returns unchecked/partial/checked.

- [ ] **Step 2: Run focused tests and verify RED**

Run: `.venv/bin/python -m unittest tests.test_paper_table_model tests.test_workspace_window_ui`

Expected: failures for visible vertical header, emoji status text, and missing decoration data.

- [ ] **Step 3: Implement minimal table and SVG behavior**

Hide the vertical header in `WorkspaceWindow`, label the model's numeric column `#`, return themed SVG icons through `DecorationRole`, keep accessible tooltips, and draw unchecked/partial/checked header indicators with the platform style.

- [ ] **Step 4: Run focused tests and verify GREEN**

Run: `.venv/bin/python -m unittest tests.test_paper_table_model tests.test_workspace_window_ui tests.test_workspace_widgets`

Expected: all focused tests pass.

- [ ] **Step 5: Commit**

Run: `git add paper_spider/ui/assets paper_spider/ui/paper_table_model.py paper_spider/ui/workspace_window.py paper_spider/ui/theme.py tests/test_paper_table_model.py tests/test_workspace_window_ui.py tests/test_workspace_widgets.py && git commit -m "feat: modernize paper table selection and status"`

### Task 2: Modern structured filters and top workspace search

**Files:**
- Modify: `paper_spider/ui/workspace_widgets.py`
- Modify: `paper_spider/ui/workspace_window.py`
- Modify: `paper_spider/ui/theme.py`
- Test: `tests/test_workspace_window_ui.py`
- Test: `tests/test_workspace_widgets.py`
- Test: `tests/test_workspace_filters.py`

**Interfaces:**
- Consumes: existing `FilterConfig` fields and `_quick_filtered_rows()` semantics.
- Produces: Include/Prefer/Exclude UI labels mapped to must/should/must-not values, one Add rule control, conditional minimum-preferred UI, and a TopBar-owned quick search widget.

- [ ] **Step 1: Write failing filter and TopBar tests**

Add tests asserting that filter roles display Include/Prefer/Exclude while `config()` returns existing internal values; the quick search is a child of `TopBar`, keeps its debounce and shortcut behavior, and is no longer inside the table center header; minimum-preferred controls hide when no Prefer rule exists.

- [ ] **Step 2: Run focused tests and verify RED**

Run: `.venv/bin/python -m unittest tests.test_workspace_window_ui tests.test_workspace_widgets tests.test_workspace_filters`

Expected: failures for old labels, separate add buttons, always-visible minimum controls, and search parentage.

- [ ] **Step 3: Implement minimal filter and search layout**

Refactor `FilterRow` to a sentence-like compact rule, replace three add buttons with Add rule, update explanatory copy, move `quick_filter_edit` into `TopBar` beside `SummaryStrip`, and toggle minimum-preferred visibility based on active Prefer rules.

- [ ] **Step 4: Run focused tests and verify GREEN**

Run: `.venv/bin/python -m unittest tests.test_workspace_window_ui tests.test_workspace_widgets tests.test_workspace_filters`

Expected: all focused tests pass.

- [ ] **Step 5: Commit**

Run: `git add paper_spider/ui/workspace_widgets.py paper_spider/ui/workspace_window.py paper_spider/ui/theme.py tests/test_workspace_window_ui.py tests/test_workspace_widgets.py tests/test_workspace_filters.py && git commit -m "feat: redesign workspace filtering and search"`

### Task 3: Native windows and compact Settings

**Files:**
- Modify: `paper_spider/ui/theme.py`
- Modify: `paper_spider/ui/window_chrome.py`
- Modify: `paper_spider/ui/workspace_widgets.py`
- Modify: `paper_spider/ui/workspace_window.py`
- Modify: `paper_spider/ui/settings_dialog.py`
- Modify: `paper_spider/ui/export_dialog.py`
- Test: `tests/test_ui_dialogs.py`
- Test: `tests/test_workspace_window_ui.py`
- Test: `tests/test_workspace_widgets.py`

**Interfaces:**
- Consumes: existing `QSettings` keys and `SettingsDialog.request_delay_ms()`.
- Produces: native window flags for every top-level interface, a compact single-column Settings layout with separated topic cards, and a themed native Export dialog.

- [ ] **Step 1: Write failing native-window and Settings tests**

Replace frameless expectations with tests asserting no `FramelessWindowHint`, no `FramelessTitleBar` child, compact Settings minimum/initial sizes, vertically separated Request and Appearance cards, and themed Export controls.

- [ ] **Step 2: Run focused tests and verify RED**

Run: `.venv/bin/python -m unittest tests.test_ui_dialogs tests.test_workspace_window_ui tests.test_workspace_widgets`

Expected: failures while custom window chrome and the Settings sidebar remain.

- [ ] **Step 3: Implement native windows and compact Settings**

Stop `apply_theme()` from changing window flags, remove custom title-bar/control construction from main/dialog layouts, simplify Settings into separated topic cards in one column with a footer, and apply the shared theme to Export while preserving native chrome.

- [ ] **Step 4: Run focused tests and verify GREEN**

Run: `.venv/bin/python -m unittest tests.test_ui_dialogs tests.test_workspace_window_ui tests.test_workspace_widgets`

Expected: all focused tests pass.

- [ ] **Step 5: Commit**

Run: `git add paper_spider/ui/theme.py paper_spider/ui/window_chrome.py paper_spider/ui/workspace_widgets.py paper_spider/ui/workspace_window.py paper_spider/ui/settings_dialog.py paper_spider/ui/export_dialog.py tests/test_ui_dialogs.py tests/test_workspace_window_ui.py tests/test_workspace_widgets.py && git commit -m "feat: unify native windows and settings"`

### Task 4: Dataset single-selection dialog and integration polish

**Files:**
- Modify: `paper_spider/ui/dataset_dialog.py`
- Modify: `paper_spider/ui/theme.py`
- Modify: `paper_spider/ui/workspace_window.py`
- Test: `tests/test_ui_dialogs.py`
- Test: `tests/test_workspace_window_ui.py`

**Interfaces:**
- Consumes: existing `SelectionResult`, current-row selection, fetch intent, and dataset scan behavior.
- Produces: no leading dataset checkboxes, reliable current-row selection, disabled Use selected when invalid, correct storage summary, and responsive splitter sizing.

- [ ] **Step 1: Write failing Dataset and integration tests**

Add tests asserting the Dataset table has no checkable leading column, `_selected_row()` uses only `currentRow()`, `Use selected` enables only for a valid row, loading a stored base directory updates the storage label, and the workspace can resize below the previous 1333-pixel lower bound without clipping filter controls.

- [ ] **Step 2: Run focused tests and verify RED**

Run: `.venv/bin/python -m unittest tests.test_ui_dialogs tests.test_workspace_window_ui`

Expected: failures for checkbox rows, selection fallback, stale storage label, and current minimum-width behavior.

- [ ] **Step 3: Implement Dataset and responsive integration behavior**

Remove the checkbox column, update table indexes and actions, connect current-row changes to the primary button state, synchronize the storage label during initial load, reduce fixed pane minimums, and allow filter/details splitter panes to collapse while prioritizing the table.

- [ ] **Step 4: Run focused tests and verify GREEN**

Run: `.venv/bin/python -m unittest tests.test_ui_dialogs tests.test_workspace_window_ui`

Expected: all focused tests pass.

- [ ] **Step 5: Run full regression suite and commit**

Run: `.venv/bin/python -m unittest discover -s tests -v`

Expected: all tests pass.

Run: `git add paper_spider/ui/dataset_dialog.py paper_spider/ui/theme.py paper_spider/ui/workspace_window.py tests/test_ui_dialogs.py tests/test_workspace_window_ui.py && git commit -m "feat: simplify datasets and responsive workspace"`

### Task 5: Visual QA and final integration

**Files:**
- Modify as required by verified visual defects: `paper_spider/ui/*.py`, `paper_spider/ui/assets/*.svg`
- Test as required by each defect: `tests/test_ui_dialogs.py`, `tests/test_workspace_window_ui.py`, `tests/test_workspace_widgets.py`, `tests/test_paper_table_model.py`

**Interfaces:**
- Consumes: completed Tasks 1–4.
- Produces: verified light/dark screenshots at 1440×820 and reduced width, with no clipping, inconsistent chrome, low-information empty gutters, or unthemed dialogs.

- [ ] **Step 1: Render the main workspace, Dataset, Settings, and Export in light and dark themes**

Use Qt offscreen rendering with isolated `QSettings`; include empty and populated main-window states at 1440×820 and a reduced width near 1100×720.

- [ ] **Step 2: For every material visual defect, write a failing regression test**

Run the smallest relevant test module and confirm each new test fails for the observed defect before changing production code.

- [ ] **Step 3: Implement only the fixes required by failing tests**

Preserve the approved layout and avoid unrelated architecture changes.

- [ ] **Step 4: Run complete verification**

Run: `.venv/bin/python -m unittest discover -s tests -v`

Run: `git diff --check`

Expected: all tests pass and diff check produces no output.

- [ ] **Step 5: Commit**

Run: `git add paper_spider tests && git commit -m "fix: polish workspace visual integration"` when Task 5 changes files; otherwise record that no additional commit is necessary.

