# PaperSpider Documentation

## Getting Started

### Install

1) Install Python 3.10+ and `uv`.
2) Clone the repo.
3) Run the app:

```bash
uv run paperspider
```

### Choose a conference and dataset

1) From the empty state or the top dataset name, choose a dataset to start.
2) Use the top area to see the active conference/year.
3) Use the dedicated dataset window to set the base folder, select an existing dataset, or create one by choosing conference/year, then load it into the workspace.
4) Open **Settings** only when you need to adjust the request interval.

### Fetch and sync paper lists

- Click **Fetch list** to load or refresh the list for the selected conference/year.
- The list is stored in SQLite so you can reopen it later.
- Supported conferences: NeurIPS, ICML, ICLR, AAAI, IJCAI, CVPR, ICCV, EMNLP, ACL, NAACL, SIGCOMM, NSDI, OSDI, ATC, FAST, USENIX Security, NDSS, VLDB.

### Add filters

1) Open the filter area.
2) Add rules under **Must**, **Should**, or **Must not**.
3) Choose a field (All/Title/Authors/Abstract/Keywords).
4) Choose a match mode (contains / not contains).
5) Enter the rule text.
6) Set **Min should match** to require at least N “Should” filters.
7) Apply the filters.
8) Use the quick filter above the table to search within the currently filtered list without changing the saved filter rules.

Filter roles:

- **Must**: every enabled Must rule must match.
- **Should**: optional by default; becomes required when **Min should match** is greater than 0.
- **Must not**: matching papers are excluded.

### Select, inspect, and download

- Use the checkbox column to select papers, or use **Select all / none / invert** from the action bar below the table.
- Use the paper table for selection and metadata scanning. Artifact actions are not embedded in table columns.
- Use the details panel for the focused paper:
  - Read the full abstract.
  - Copy an existing abstract or download a missing abstract.
  - Download a missing PDF, or open/reveal an existing PDF file.
  - Fetch/export, copy, or reveal the BibTeX file.
- Use the status/log area to follow fetch and download progress.
- Use the cancel control in the status/log area while abstract or PDF downloads are running.

### Export selected papers

- Select one or more papers, then click **Export selected**.
- Formats: CSV, JSON, plain text list.
- For CSV/JSON you can select fields (title/authors/abstract).
- Plain text list exports one paper title per line.
- Generated content appears in a text box for select/copy, with a quick **Copy** button.

### Data layout

All data is stored under:

```
<base folder>/<conference>/<year>/
  papers.sqlite
  pdf/
  bib/
```

## Development

### Prerequisites

- Python 3.10+
- `uv`

### Setup

1) Fork or clone the repo.
2) Install dependencies:

```bash
uv sync
```

3) Run the app:

```bash
uv run paperspider
```

4) Run tests:

```bash
.venv/bin/python -m unittest discover -s tests -v
```

### Build a double-clickable app

macOS:

```bash
uv run --with pyinstaller pyinstaller --noconfirm --clean --windowed --name PaperSpider paper_spider/__main__.py
```

Windows:

```bash
uv run --with pyinstaller pyinstaller --noconfirm --clean --windowed --name PaperSpider paper_spider/__main__.py
```

### Notes

- The UI is built with PyQt6.
- Conference adapters live in `paper_spider/conferences/`.
- Storage and schema are in `paper_spider/storage.py`.
- The CCF A conference implementation survey is in `docs/ccf_a_conference_research.md`.
