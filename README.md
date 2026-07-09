# PaperSpider (MVP)

[中文 README](README.zh.md) | [Documentation](docs/en.md) | [中文 文档](docs/zh.md)

**News**
- 2026-07-09: Added CCF A adapters for AAAI, ICCV, IJCAI, FAST, USENIX Security, NDSS, and VLDB; documented the remaining CCF A conference roadmap.
- 2026-03-12: Added a SIGCOMM adapter based on the official proceedings page plus DOI/Crossref metadata.
- 2026-03-12: Added CVPR adapter based on the official CVF Open Access repository.
- 2026-03-12: Added ACL, NAACL, OSDI, and ATC adapters by reusing ACL Anthology and USENIX base implementations.
- 2026-03-11: Added EMNLP and NSDI conference adapters with unit tests.
- 2026-02-28: Added selected-paper export dialog (CSV/JSON/plain list) with copy-ready output.
- 2026-02-28: Added ICML and ICLR conference adapters with unit tests.
- 2026-01-10: Added workspace-first flow, multi-filter (Must/Should/Must not), cancelable downloads, PDF/bib quick actions, and request interval setting.

A minimal PyQt app to fetch conference paper lists, download abstracts/PDFs, and manage them in SQLite.

## Features

- Conference adapters: NeurIPS, ICML, ICLR, AAAI, IJCAI, CVPR, ICCV, EMNLP, ACL, NAACL, SIGCOMM, NSDI, OSDI, ATC, FAST, USENIX Security, NDSS, VLDB
- Workspace-first UI: choose/manage datasets from the empty state or top dataset name, then fetch the paper list
- Filters: Must/Should/Must not + min-should-match, plus quick search within the current paper list
- Paper table focused on metadata, with artifact actions moved out of the columns
- Details panel for full abstract preview, copy/download abstract, download/open PDF, and Bib copy/reveal actions
- Export selected papers to CSV/JSON/plain text list with field selection and quick copy
- Status/log area for progress messages and cancelable abstract/PDF downloads
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

- Pick or create a dataset from the workspace empty state or top dataset name; set the base folder in Datasets and use Settings only for request interval.
- Data is stored under `CONFERENCE/YEAR/`.
- Abstracts are stored in SQLite; bibtex is stored in SQLite and exported to files.

## License

Apache-2.0. See `LICENSE` and `NOTICE`.
