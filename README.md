<h1 align="center">PaperSpider</h1>

<p align="center">
  <img src="docs/images/app-icon.png" width="128" alt="PaperSpider icon">
</p>

[中文 README](README.zh.md) · [English guide](docs/en.md) · [中文使用说明](docs/zh.md)

PaperSpider is a desktop app for finding conference papers, narrowing a large paper list, and downloading or exporting the results you need.

![PaperSpider workspace with papers](docs/images/workspace.png)

## What it does

- Fetches paper lists from major AI, systems, security, vision, and NLP conferences.
- Combines reusable filter rules with a quick search for further narrowing.
- Downloads abstracts and PDFs for one paper or many selected papers.
- Exports selected paper metadata and abstracts as CSV, JSON, or a plain list.
- Stores each conference and year locally in SQLite, alongside downloaded files.

## Start

Download the latest package for **macOS** or **Windows** from
[GitHub Releases](https://github.com/isaacveg/PaperSpider/releases/latest).

To run from source, install [uv](https://docs.astral.sh/uv/), then run:

```bash
uv run paperspider
```

## Basic workflow

1. Choose a conference and year from **Datasets**, then fetch or open its paper list.
2. Add **Include**, **Prefer**, or **Exclude** filter rules and click **Apply**.
3. Use **Search papers** to narrow the filtered results further.
4. Select papers, then download abstracts or PDFs in a batch. Select one row to use its individual actions.
5. Click **Export selected** to export titles, authors, abstracts, or a simple title list.

See the [English guide](docs/en.md) for filter meanings and the complete workflow.

## Supported conferences

NeurIPS, ICML, ICLR, AAAI, IJCAI, CVPR, ICCV, EMNLP, ACL, NAACL, SIGCOMM, NSDI, OSDI, ATC, FAST, USENIX Security, NDSS, and VLDB.

## Test

```bash
uv run python -m unittest discover -s tests -v
```

Apache-2.0. See [LICENSE](LICENSE) and [NOTICE](NOTICE).
