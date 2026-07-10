# PaperSpider guide

[README](../README.md) · [中文使用说明](zh.md)

PaperSpider helps you turn a full conference paper list into a focused set that you can inspect, download, and export.

## Start the app

Install Python 3.10+ and [uv](https://docs.astral.sh/uv/), clone the repository, then run:

```bash
uv run paperspider
```

## 1. Choose a conference

1. Open **Datasets** from the dataset button at the top.
2. Choose the base folder where PaperSpider should store data.
3. Select an existing conference/year and click **Use selected**.
4. To add another dataset, click **Add Dataset**, choose a conference and year, then click **Fetch dataset**.

The paper list is stored locally and can be reopened without fetching it again. Use **Refresh** when you want to update an existing list.

## 2. Use filters

Click **Add rule**, then choose a role, field, match mode, and keyword:

- **Include**: the paper must match.
- **Prefer**: the match is optional unless **Minimum preferred** requires one or more Prefer rules.
- **Exclude**: matching papers are removed.

You can target any field, or only the title, authors, abstract, or keywords. Disable a rule with its checkbox without deleting it. Click **Apply** when the rules are ready.

## 3. Narrow the results further

Type in **Search papers** above the workspace. This searches only the current filtered result and does not change your filter rules. Clear the search box to return to the full filtered result.

## 4. Inspect and download papers

Click a row to see its title, authors, category, abstract, and available files in the details panel.

- Use the details panel to copy or download one abstract, open one PDF, or copy BibTeX.
- Tick several papers, then use **Download abstracts** or **Download PDFs** for a batch.
- Use the header checkbox to select or clear all visible papers. Use **Invert** to reverse the current selection.
- Open **Show log** to follow progress or cancel an active batch.

## 5. Export results

Select the papers you need and click **Export selected**. Choose:

- **CSV** or **JSON** for titles, authors, and optional abstracts.
- **Plain list** for one paper title per line.

Use **Export Bib** when you need BibTeX files for the selected papers.

## Local data

PaperSpider stores data under the base folder:

```text
<base folder>/<conference>/<year>/
  papers.sqlite
  pdf/
  bib/
```

Open **Settings** to change the request interval or appearance. A moderate request interval is recommended when downloading many items.
