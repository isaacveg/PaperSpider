---
name: paperspider
description: Search, inspect, download, and export conference papers through the local PaperSpider CLI. Use when the user asks to find papers by conference, year, title, author, or keyword; add a conference dataset; retrieve abstracts, PDFs, or BibTeX; or export paper metadata without starting a server.
---

# PaperSpider CLI

Use `paperspider-cli` to access the same local paper library as the PaperSpider desktop app. From a source checkout, run it as `uv run paperspider-cli`. No server or MCP setup is needed.

## Discover and search

Start with local data. Use `--base-dir` when the user specifies a library folder; otherwise preserve the CLI's configured library selection.

```bash
paperspider-cli datasets --json
paperspider-cli search --json --limit 20 --query "diffusion"
paperspider-cli show CONF YEAR PAPER_ID --json
```

- Restrict searches with `--conf` and `--year` when known. Use `--title`, `--author`, or `--keyword` for targeted searches.
- Start with at most 20 results and paginate with `--offset`. Add `--abstract` only when abstracts are needed.
- List supported conferences with `paperspider-cli conferences --json` only when a new dataset is needed.
- Use `show --fetch` only when the user wants to refresh metadata from the conference site.

## Fetch, download, and export

The following operations may access the network or write to the library. Perform them when requested, respect sandbox and approval prompts, and ensure the target directory is writable. Avoid concurrent writes to the same conference and year, including downloads running in the desktop app.

```bash
paperspider-cli add CONF YEAR --json
paperspider-cli download-abstracts CONF YEAR PAPER_ID [PAPER_ID ...] --json
paperspider-cli download-pdfs CONF YEAR PAPER_ID [PAPER_ID ...] --json
paperspider-cli download-bibtex CONF YEAR PAPER_ID [PAPER_ID ...] --json
paperspider-cli export CONF YEAR [PAPER_ID ...] --format csv --json
```

- Reuse paper IDs returned by `search`; do not invent them.
- Choose export format `csv`, `json`, `txt`, or `bibtex`. Add `--save` only when a file under the dataset's `exports/` folder is wanted.
- For JSON-wrapped exports, read the export from `content` and the optional saved file from `path`.
- Keep request pacing at the configured default unless the user specifies `--delay-ms`.

## Report results

Return a concise summary with paper IDs or artifact paths needed for follow-up actions. Do not dump full JSON documents or abstracts unless requested.

For batch downloads and BibTeX exports, exit status 1 can mean partial success. Inspect `failures`, report completed and failed items separately, and do not blindly repeat items that already succeeded.

Use `paperspider-cli --help`, command-specific `--help`, or `man paperspider-cli` for detailed options. In a source checkout without an installed man page, use `man ./man/paperspider-cli.1`.
