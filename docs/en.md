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

1) Open **Settings** in the workspace.
2) Choose a base folder (this is where `conference/year` data is stored).
3) Select an existing dataset from the list, or click **Add** to create one and pick conference/year.
4) Click **Use selected** to load the workspace.

### Fetch and sync paper lists

- Click **Fetch paper list** to load or refresh the list for the selected conference/year.
- The list is stored in SQLite so you can reopen it later.
- Supported conferences: NeurIPS, ICML, ICLR.

### Add filters

1) Click **Add filter**.
2) Choose a field (All/Title/Authors/Abstract/Keywords).
3) Choose a match mode (contains / not contains).
4) Choose a role:
   - **Must**: required
   - **Should**: optional
   - **Must not**: excluded
5) Set **Min should match** to require at least N “Should” filters.
6) Click **Apply filter**.

### Select and download

- Use the checkbox column to select papers, or use **Select all / none / invert**.
- **Abstract**:
  - If **No**, click the cell to download.
  - If **Yes**, hover to preview the abstract.
- **PDF**:
  - If **No**, click the cell to download.
  - If **Yes**, double-click to open.
  - Ctrl+Click to reveal in folder.
- **Bibtex**:
  - If **No**, click the cell to download.
  - If **Yes**, double-click to copy to clipboard.
  - Ctrl+Click to reveal in folder.
- **Export selected**:
  - Open export dialog for selected papers.
  - Formats: CSV, JSON, plain text list.
  - For CSV/JSON you can select fields (title/authors/abstract).
  - Plain text list exports one paper title per line.
  - Generated content appears in a text box for select/copy, with a quick **Copy** button.
- Use **Cancel Download** while downloads are running.

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
