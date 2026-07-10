# PaperSpider Workspace UI Modernization Design

## Goal

Modernize the PaperSpider workspace and dialogs while keeping the existing PyQt6, SQLite, synchronous-adapter, and `QThreadPool` architecture. The result must be intuitive, visually consistent, compact enough for normal laptop screens, and maintainable without adding a UI framework or a new application layer.

## Approved Product Decisions

1. The structured filter remains a first-class feature, but its language and layout become modern and direct.
2. The quick paper search moves out of the table header and into the top workspace bar at the same visual level as the dataset summary.
3. The table removes the unintended vertical row-header gutter to the left of the numeric paper index.
4. Row selection uses explicit empty/checked visual states, and the header supports unchecked, partially selected, and fully selected states.
5. Paper artifact status uses bundled SVG icons instead of emoji.
6. Settings remains grouped into small topics with visible spacing and separators, but loses the oversized navigation/sidebar treatment.
7. The main workspace uses the operating system's native title bar on macOS, Windows, and Linux.
8. Dataset and Settings dialogs do not implement custom traffic-light or Windows window-control buttons. They use native dialog chrome and explicit footer actions such as Cancel, Close, Apply, or Save.
9. Export follows the same native-window and theme policy so all top-level interfaces are consistent.
10. Existing data, conference adapters, downloads, filters, export behavior, and storage layout remain compatible.

## Workspace Layout

The main content has four horizontal regions:

1. Native OS title bar.
2. Top workspace bar: PaperSpider brand and dataset chooser on the left, summary in the middle/right, then a prominent `Search papers…` field and Settings action.
3. Three-pane workspace: compact structured-filter sidebar, paper table, details pane. Splitter panes remain resizable and collapsible; table space receives priority.
4. Compact task/log status area.

The quick search is global to the currently structured-filtered result. It keeps the existing debounce and `Ctrl/Cmd+F` shortcut.

## Structured Filter Design

The filter sidebar uses a compact section header, short explanation, and one `Add rule` action. Each rule reads left-to-right as a sentence:

`[Include / Prefer / Exclude] [Title / Category / Author / Abstract / Keywords / Anywhere] [contains / does not contain] [value] [remove]`

The roles map to existing behavior:

- Include → `must`
- Prefer → `should`
- Exclude → `must not`

`Minimum preferred matches` appears only when Prefer rules exist. Apply and Reset remain explicit to avoid running the full structured filter while the user edits several fields. The sidebar uses labels and tooltips that describe effects without Boolean-search jargon.

## Paper Table

The model keeps an explicit numeric `#` column and an explicit selection column. The `QTableView` vertical header is hidden, removing the extra empty gutter before `#`.

Selection rendering is provided by the Qt style/delegate path, not emoji text in the model:

- empty square: unselected;
- checked square: selected;
- horizontal dash: header partially selected;
- checked square: header fully selected.

The status column exposes two bundled SVG-backed indicators with accessible tooltips:

- abstract available;
- PDF available.

The title remains the stretch column and receives more width than category, authors, and status.

## Dialogs and Native Windows

`apply_theme()` only applies theme styling. It must no longer force `FramelessWindowHint`.

The main window and every dialog use native top-level window chrome. Dataset and Settings remove `FramelessTitleBar`; their footer buttons are the explicit path to accept/reject. The native close button may still exist because the operating system owns the window frame, but the product does not draw or manage it.

Settings becomes a single scrollable column of visually separated topic cards. Request behavior and Appearance are distinct cards with spacing, internal row dividers, concise descriptions, and a compact footer. Dataset keeps the wide table workflow but removes the leading checkboxes because selection is single-row. `Use selected` is disabled without a usable current row. Export applies the same theme and spacing conventions.

## Theme and Accessibility

Bundled SVG icons must work in both light and dark themes. Icons use neutral or theme-compatible artwork and must not rely on platform emoji fonts.

Checkbox state may not rely on color alone. Tooltips and accessible text remain available for status indicators. Native window chrome is preferred to reduce platform-specific accessibility and lifecycle behavior.

## Testing

Behavioral tests cover:

- filter role labels and existing role mapping;
- quick search placement in the top bar;
- hidden table vertical header;
- tri-state selection behavior;
- SVG status icon resources and tooltips;
- absence of `FramelessWindowHint` on all top-level interfaces;
- Settings card separation and compact dimensions;
- Dataset single-row selection without checkboxes;
- dialog footer actions and theme consistency.

All existing 141 tests must continue to pass. Visual QA renders empty/populated main windows plus Dataset, Settings, and Export in light and dark themes at normal and reduced sizes.

## Explicit Non-Goals

- No MVVM framework, dependency injection container, web frontend, ORM, asyncio integration, or plugin system.
- No changes to conference parsing, storage schema, network behavior, or artifact formats.
- No attempt to disable macOS Accessibility APIs as a crash workaround.

