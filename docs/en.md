# PaperSpider guide

[README](../README.md) · [中文使用说明](zh.md)

PaperSpider helps you turn a full conference paper list into a focused set that you can inspect, download, and export.

## Start the app

Install Python 3.10+ and [uv](https://docs.astral.sh/uv/), clone the repository, then run:

```bash
uv run paperspider
```

## 1. Choose a conference

1. Datasets appear in the left sidebar. Click one to open its paper list.
2. To add a dataset, click **+** next to **Conference datasets**.
3. Choose the base folder, conference, and year, then click **Fetch dataset**.

The paper list is stored locally and can be reopened without fetching it again. Use the refresh button beside the selected dataset's **⋯** menu to update it.

Use the **⋯** button on the selected dataset to **Open in folder** or **Delete dataset**. Deleting moves the dataset folder to `.trash` and requires fetching it again. Drag the divider to resize the sidebar; dragging it narrow snaps it to a compact icon rail (hover for names, right-click a dataset for its actions, or use the arrow to expand again). The collapse button hides the sidebar completely.

## 2. Use filters

Click **Filters** above the paper list. A filter dialog opens where you can add rules:

- **Include**: the paper must match.
- **Prefer**: the match is optional unless **Minimum preferred matches** requires one or more Prefer rules.
- **Exclude**: matching papers are removed.

Applied rules appear as chips under the search box. Click a chip's close button to remove that rule without reopening the dialog.

## 3. Narrow the results further

Type in **Search in results** above the paper list. This searches only the current filtered result and does not change your filter rules.

## 4. Inspect and download papers

Select a row to see its title, authors, tags, abstract, and local files in the details panel on the right.

- Use **Open PDF** or **Copy BibTeX** for the selected paper. Missing BibTeX is fetched from the conference site and copied to the clipboard.
- Use **Show in folder** under **Local files** to open the file manager at the downloaded PDF.
- Tick several papers, then use **Download abstracts** or **Download PDFs** in the action bar.
- Use the header checkbox to select or clear all visible papers, or **Invert** to reverse the selection of visible papers.
- Ticked papers stay selected when searching or filtering hides them; the action bar shows how many are not shown, and downloads and exports include them.
- Keyboard: <kbd>Space</kbd> ticks the current paper, <kbd>Enter</kbd> opens its PDF, and <kbd>Ctrl/⌘</kbd>+<kbd>A</kbd> ticks all visible papers. Right-click a paper for more actions.
- Click the **Papers / authors**, **Abstract**, or **PDF** header to sort; click again to reverse, and a third time to restore the default order.
- Use **Task log** at the bottom to follow progress or cancel all running tasks. Results appear in the status bar, and the log opens automatically when some items fail.

## 5. Export results

Select the papers you need and click **Export** to export titles, authors, and optional abstracts as CSV or JSON, or a plain title list. Use **Copy BibTeX** in the details panel for BibTeX entries.

## Local data

PaperSpider stores data under the base folder:

```text
<base folder>/<conference>/<year>/
  papers.sqlite
  pdf/
  bib/
  exports/
```

Open **Settings** to change the request interval or appearance. The **Theme**
option can follow the system appearance or stay on Light or Dark. The interface
language follows the system language (Chinese or English). A moderate request
interval is recommended when downloading many items.

## Command line

For scripted access to the same library, use `uv run paperspider-cli`. The
complete manual is [man/paperspider-cli.1](../man/paperspider-cli.1):

```bash
man ./man/paperspider-cli.1
```
