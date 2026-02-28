# PaperSpider (MVP)

[中文 README](README.zh.md) | [Documentation](docs/en.md) | [中文 文档](docs/zh.md)

**News**
- 2026-02-28: Added selected-paper export dialog (CSV/JSON/plain list) with copy-ready output.
- 2026-02-28: Added ICML and ICLR conference adapters with unit tests.
- 2026-01-10: Added workspace-first flow, multi-filter (Must/Should/Must not), cancelable downloads, PDF/bib quick actions, and request interval setting.

A minimal PyQt app to fetch conference paper lists, download abstracts/PDFs, and manage them in SQLite.

## Features

- Conference adapters: NeurIPS, ICML, ICLR
- Workspace UI with filters and selection
- Filters: Must/Should/Must not + min-should-match
- Abstract download (hover to preview; click to fetch missing)
- PDF download (click to fetch; double-click to open; Ctrl+Click to reveal in folder)
- Bibtex export (click to fetch; double-click to copy; Ctrl+Click to reveal in folder)
- Export selected papers to CSV/JSON/plain text list with field selection and quick copy
- Cancelable abstract/PDF downloads
- Request interval (polite crawling)
- Output structure per `conference/year`, with SQLite + `pdf/` + `bib/`

## Run

```bash
uv run paperspider
```

If you prefer running the module directly:

```bash
uv run -m paper_spider
```

## Test

```bash
.venv/bin/python -m unittest discover -s tests -v
```

## Notes

- Pick a base directory in the Settings dialog; data is stored under `CONFERENCE/YEAR/`.
- Abstracts are stored in SQLite; bibtex is stored in SQLite and exported to files.

## License

Apache-2.0. See `LICENSE` and `NOTICE`.
