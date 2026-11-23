# Copyright 2026 Isaacveg
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#     http://www.apache.org/licenses/LICENSE-2.0

"""Command-line interface for searching, downloading, and exporting papers."""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any, Callable, Dict, Optional, Sequence

from . import __version__
from .operations import (
    DEFAULT_SEARCH_LIMIT,
    EXPORT_FORMATS,
    OperationError,
    PaperSpiderOperations,
    validate_delay_ms,
    validate_limit,
    validate_offset,
    validate_year,
)


def _int_argument(validator: Callable[[Any], int]) -> Callable[[str], int]:
    def parse(value: str) -> int:
        try:
            return validator(value)
        except OperationError as exc:
            raise argparse.ArgumentTypeError(str(exc)) from exc

    return parse


_year_type = _int_argument(validate_year)
_limit_type = _int_argument(validate_limit)
_offset_type = _int_argument(validate_offset)
_delay_type = _int_argument(validate_delay_ms)


def _global_options() -> argparse.ArgumentParser:
    parent = argparse.ArgumentParser(add_help=False)
    parent.add_argument(
        "--base-dir",
        metavar="DIR",
        default=argparse.SUPPRESS,
        help=(
            "storage folder. Defaults to PAPERSPIDER_BASE_DIR, then the "
            "desktop app setting, then ~/PaperSpider."
        ),
    )
    parent.add_argument(
        "--delay-ms",
        metavar="MS",
        type=_delay_type,
        default=argparse.SUPPRESS,
        help="delay between web requests in milliseconds (default: 100).",
    )
    parent.add_argument(
        "-j",
        "--json",
        action="store_true",
        default=argparse.SUPPRESS,
        help="print machine-readable JSON instead of text.",
    )
    return parent


def build_parser() -> argparse.ArgumentParser:
    """Build the argument parser for paperspider-cli."""

    parent = _global_options()
    parser = argparse.ArgumentParser(
        prog="paperspider-cli",
        description=(
            "Search, download, and export conference papers stored by "
            "PaperSpider. Every command runs directly; no server is needed."
        ),
        epilog=(
            "The complete manual is in man/paperspider-cli.1. View it with "
            "'man paperspider-cli' when installed, or 'man "
            "./man/paperspider-cli.1' from the repository."
        ),
        parents=[parent],
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    subparsers = parser.add_subparsers(
        dest="command",
        required=True,
        metavar="COMMAND",
    )

    conferences = subparsers.add_parser(
        "conferences",
        parents=[parent],
        help="list supported conferences.",
        description="List the conferences PaperSpider can fetch paper lists from.",
    )
    conferences.add_argument(
        "--query",
        metavar="TEXT",
        help="filter by conference name or slug.",
    )
    conferences.set_defaults(handler=_cmd_conferences)

    datasets = subparsers.add_parser(
        "datasets",
        parents=[parent],
        help="list local datasets.",
        description=(
            "List conference and year datasets stored under the base folder, "
            "with paper counts and relative paths."
        ),
    )
    datasets.set_defaults(handler=_cmd_datasets)

    add = subparsers.add_parser(
        "add",
        parents=[parent],
        help="fetch a conference year into the local library.",
        description=(
            "Fetch the paper list for a supported conference and year from the "
            "web and store it locally. Creates or refreshes the dataset."
        ),
    )
    add.add_argument("conf", metavar="CONF", help="conference slug, e.g. iclr.")
    add.add_argument("year", metavar="YEAR", type=_year_type, help="conference year.")
    add.set_defaults(handler=_cmd_add)

    search = subparsers.add_parser(
        "search",
        parents=[parent],
        help="search local papers.",
        description=(
            "Search locally stored papers. Omit --conf and --year to search "
            "every local dataset."
        ),
    )
    search.add_argument("--conf", metavar="CONF", help="conference slug.")
    search.add_argument("--year", metavar="YEAR", type=_year_type, help="conference year.")
    search.add_argument(
        "--query",
        metavar="TEXT",
        help=(
            "free text matched against title, category, authors, abstract, and "
            "keywords. Every whitespace-separated term must match."
        ),
    )
    search.add_argument("--title", metavar="TEXT", help="match titles containing text.")
    search.add_argument("--author", metavar="TEXT", help="match authors containing text.")
    search.add_argument(
        "--keyword",
        metavar="TEXT",
        help="match keywords or abstracts containing text.",
    )
    search.add_argument(
        "--limit",
        metavar="N",
        type=_limit_type,
        default=DEFAULT_SEARCH_LIMIT,
        help=f"maximum papers to return (default: {DEFAULT_SEARCH_LIMIT}, max: 200).",
    )
    search.add_argument(
        "--offset",
        metavar="N",
        type=_offset_type,
        default=0,
        help="number of matches to skip (default: 0).",
    )
    search.add_argument(
        "--abstract",
        dest="include_abstract",
        action="store_true",
        help="include full abstracts in the results.",
    )
    search.set_defaults(handler=_cmd_search)

    show = subparsers.add_parser(
        "show",
        parents=[parent],
        help="show one paper.",
        description="Show full metadata for one paper.",
    )
    show.add_argument("conf", metavar="CONF", help="conference slug.")
    show.add_argument("year", metavar="YEAR", type=_year_type, help="conference year.")
    show.add_argument("paper_id", metavar="PAPER_ID", help="paper id from search.")
    show.add_argument(
        "--fetch",
        dest="fetch_details",
        action="store_true",
        help="refresh abstract, authors, PDF URL, and BibTeX from the web.",
    )
    show.add_argument(
        "--bibtex",
        action="store_true",
        help="print the BibTeX entry when available.",
    )
    show.set_defaults(handler=_cmd_show)

    abstracts = subparsers.add_parser(
        "download-abstracts",
        parents=[parent],
        help="download missing abstracts.",
        description=(
            "Fetch missing abstracts and metadata for up to 200 papers and "
            "store them locally. Prints each downloaded abstract."
        ),
    )
    abstracts.add_argument("conf", metavar="CONF", help="conference slug.")
    abstracts.add_argument("year", metavar="YEAR", type=_year_type, help="conference year.")
    abstracts.add_argument(
        "paper_ids", metavar="PAPER_ID", nargs="+", help="one or more paper ids."
    )
    abstracts.set_defaults(handler=_cmd_download_abstracts)

    pdfs = subparsers.add_parser(
        "download-pdfs",
        parents=[parent],
        help="download PDFs.",
        description=(
            "Download PDFs for up to 200 papers into the dataset pdf folder. "
            "Papers with an existing PDF are skipped. Prints local paths."
        ),
    )
    pdfs.add_argument("conf", metavar="CONF", help="conference slug.")
    pdfs.add_argument("year", metavar="YEAR", type=_year_type, help="conference year.")
    pdfs.add_argument(
        "paper_ids", metavar="PAPER_ID", nargs="+", help="one or more paper ids."
    )
    pdfs.set_defaults(handler=_cmd_download_pdfs)

    bibtex = subparsers.add_parser(
        "download-bibtex",
        parents=[parent],
        help="download BibTeX files.",
        description=(
            "Download BibTeX for up to 200 papers into the dataset bib folder "
            "and cache the entries. Prints local paths."
        ),
    )
    bibtex.add_argument("conf", metavar="CONF", help="conference slug.")
    bibtex.add_argument("year", metavar="YEAR", type=_year_type, help="conference year.")
    bibtex.add_argument(
        "paper_ids", metavar="PAPER_ID", nargs="+", help="one or more paper ids."
    )
    bibtex.set_defaults(handler=_cmd_download_bibtex)

    export = subparsers.add_parser(
        "export",
        parents=[parent],
        help="export paper metadata.",
        description=(
            "Export selected or all papers in one dataset. Content is written to "
            "stdout; use --save to also write a file."
        ),
    )
    export.add_argument("conf", metavar="CONF", help="conference slug.")
    export.add_argument("year", metavar="YEAR", type=_year_type, help="conference year.")
    export.add_argument(
        "paper_ids",
        metavar="PAPER_ID",
        nargs="*",
        help="papers to export. Omit to export every paper in the dataset.",
    )
    export.add_argument(
        "--format",
        dest="export_format",
        choices=EXPORT_FORMATS,
        default="csv",
        help="export format (default: csv).",
    )
    export.add_argument(
        "--no-title",
        dest="include_title",
        action="store_false",
        help="omit titles from csv and json output.",
    )
    export.add_argument(
        "--no-authors",
        dest="include_authors",
        action="store_false",
        help="omit authors from csv and json output.",
    )
    export.add_argument(
        "--abstract",
        dest="include_abstract",
        action="store_true",
        help="include abstracts in csv and json output.",
    )
    export.add_argument(
        "--save",
        action="store_true",
        help="also write the export to the dataset exports folder.",
    )
    export.add_argument(
        "--filename",
        metavar="NAME",
        help="base file name for --save; the format extension is added automatically.",
    )
    export.set_defaults(handler=_cmd_export)

    return parser


def _print_json(data: Any) -> None:
    print(json.dumps(data, ensure_ascii=False, indent=2))


def _use_json(args: argparse.Namespace) -> bool:
    return bool(getattr(args, "json", False))


def _report_failures(failures: Sequence[Dict[str, str]]) -> None:
    for failure in failures:
        print(
            f"failed: {failure['paper_id']} ({failure['title']}): "
            f"{failure['message']}",
            file=sys.stderr,
        )


def _cmd_conferences(api: PaperSpiderOperations, args: argparse.Namespace) -> int:
    result = api.list_conferences(query=args.query)
    if _use_json(args):
        _print_json(result)
        return 0
    for item in result["conferences"]:
        print(f"{item['slug']}\t{item['name']}")
    print(
        f"{result['count']} conference(s). Base folder: {result['base_dir']}",
        file=sys.stderr,
    )
    return 0


def _cmd_datasets(api: PaperSpiderOperations, args: argparse.Namespace) -> int:
    result = api.list_datasets()
    if _use_json(args):
        _print_json(result)
        return 0
    for item in result["datasets"]:
        print(
            f"{item['conf']}\t{item['year']}\t{item['papers']}\t{item['path']}"
        )
    if not result["datasets"]:
        print(
            f"No datasets under {result['base_dir']}. Run add CONF YEAR.",
            file=sys.stderr,
        )
    return 0


def _cmd_add(api: PaperSpiderOperations, args: argparse.Namespace) -> int:
    result = api.add_conference(args.conf, args.year)
    if _use_json(args):
        _print_json(result)
        return 0
    print(
        f"Fetched {result['fetched']} papers for {result['name']} "
        f"{result['year']}; {result['total']} stored at {result['path']}."
    )
    return 0


def _cmd_search(api: PaperSpiderOperations, args: argparse.Namespace) -> int:
    result = api.search_papers(
        conf=args.conf,
        year=args.year,
        query=args.query,
        title=args.title,
        author=args.author,
        keyword=args.keyword,
        limit=args.limit,
        offset=args.offset,
        include_abstract=args.include_abstract,
    )
    if _use_json(args):
        _print_json(result)
        return 0
    for paper in result["papers"]:
        print(f"{paper['paper_id']}\t{paper['title']}")
        meta = f"  {paper['conf']} {paper['year']}"
        authors = ", ".join(paper["authors"])
        if authors:
            meta += f" | {authors}"
        if paper.get("category"):
            meta += f" | {paper['category']}"
        print(meta)
        stored = [
            name
            for name, present in (
                ("abstract", paper["has_abstract"]),
                ("pdf", paper["has_pdf"]),
                ("bib", paper["has_bib"]),
            )
            if present
        ]
        if stored:
            print(f"  stored: {', '.join(stored)}")
        if args.include_abstract and paper.get("abstract"):
            print("  abstract:")
            for line in paper["abstract"].splitlines():
                print(f"    {line}")
    for error in result.get("errors", []):
        print(
            f"warning: {error['conf']} {error['year']}: {error['message']}",
            file=sys.stderr,
        )
    print(
        f"Showing {result['count']} of {result['total']} paper(s) "
        f"(offset {result['offset']}, limit {result['limit']}).",
        file=sys.stderr,
    )
    return 0


def _cmd_show(api: PaperSpiderOperations, args: argparse.Namespace) -> int:
    result = api.get_paper(
        args.conf,
        args.year,
        args.paper_id,
        fetch_details=args.fetch_details,
    )
    paper = result["paper"]
    if _use_json(args):
        _print_json(result)
        return 0
    print(f"Title: {paper['title']}")
    print(f"ID: {paper['paper_id']}")
    print(f"Conference: {paper['conf']} {paper['year']}")
    print(f"Category: {paper['category']}")
    print(f"Authors: {', '.join(paper['authors']) or '-'}")
    if paper["keywords"]:
        print(f"Keywords: {', '.join(paper['keywords'])}")
    if paper["detail_url"]:
        print(f"Detail: {paper['detail_url']}")
    if paper["pdf_url"]:
        print(f"PDF URL: {paper['pdf_url']}")
    if paper["pdf_path"]:
        print(f"PDF file: {paper['pdf_path']}")
    if paper["bib_path"]:
        print(f"BibTeX file: {paper['bib_path']}")
    print("Abstract:")
    if paper["abstract"]:
        print(paper["abstract"])
    else:
        print("(not downloaded; run show with --fetch)")
    if args.bibtex:
        print("BibTeX:")
        print(paper["bibtex"] or "(not downloaded; run download-bibtex)")
    return 0


def _cmd_download_abstracts(
    api: PaperSpiderOperations, args: argparse.Namespace
) -> int:
    result = api.download_abstracts(args.conf, args.year, args.paper_ids)
    if _use_json(args):
        _print_json(result)
        return 1 if result["failures"] else 0
    for paper in result["papers"]:
        print(f"{paper['paper_id']}\t{paper['title']}")
        if paper.get("abstract"):
            for line in paper["abstract"].splitlines():
                print(f"  {line}")
        print()
    _report_failures(result["failures"])
    print(
        f"Downloaded {result['succeeded']} abstract(s), skipped "
        f"{result['skipped']}, failed {len(result['failures'])}.",
        file=sys.stderr,
    )
    return 1 if result["failures"] else 0


def _cmd_download_pdfs(
    api: PaperSpiderOperations, args: argparse.Namespace
) -> int:
    result = api.download_pdfs(args.conf, args.year, args.paper_ids)
    if _use_json(args):
        _print_json(result)
        return 1 if result["failures"] else 0
    for item in result["files"]:
        print(f"{item['paper_id']}\t{item['path']}")
    _report_failures(result["failures"])
    print(
        f"Downloaded {result['succeeded']} PDF(s), skipped "
        f"{result['skipped']}, failed {len(result['failures'])}.",
        file=sys.stderr,
    )
    return 1 if result["failures"] else 0


def _cmd_download_bibtex(
    api: PaperSpiderOperations, args: argparse.Namespace
) -> int:
    result = api.download_bibtex(args.conf, args.year, args.paper_ids)
    if _use_json(args):
        _print_json(result)
        return 1 if result["failures"] else 0
    for item in result["files"]:
        print(f"{item['paper_id']}\t{item['path']}")
    _report_failures(result["failures"])
    print(
        f"Exported {result['exported']} BibTeX file(s), failed "
        f"{len(result['failures'])}.",
        file=sys.stderr,
    )
    return 1 if result["failures"] else 0


def _cmd_export(api: PaperSpiderOperations, args: argparse.Namespace) -> int:
    result = api.export_papers(
        args.conf,
        args.year,
        export_format=args.export_format,
        paper_ids=args.paper_ids or None,
        include_title=args.include_title,
        include_authors=args.include_authors,
        include_abstract=args.include_abstract,
        save=args.save,
        filename=args.filename,
    )
    if _use_json(args):
        _print_json(result)
    else:
        sys.stdout.write(result["content"])
        if result["content"] and not result["content"].endswith("\n"):
            sys.stdout.write("\n")
    if result.get("path"):
        print(f"Saved to {result['path']}", file=sys.stderr)
    failures = result.get("failures", [])
    _report_failures(failures)
    print(f"Exported {result['count']} paper(s).", file=sys.stderr)
    return 1 if failures else 0


def main(
    argv: Optional[Sequence[str]] = None,
    api: Optional[PaperSpiderOperations] = None,
) -> int:
    """Run one CLI command and return its exit code."""

    parser = build_parser()
    args = parser.parse_args(argv)
    operations = api or PaperSpiderOperations(
        base_dir=getattr(args, "base_dir", None),
        request_delay_ms=getattr(args, "delay_ms", None),
    )
    try:
        return args.handler(operations, args)
    except OperationError as exc:
        print(f"{parser.prog}: error: {exc}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print(f"{parser.prog}: interrupted", file=sys.stderr)
        return 130
    except BrokenPipeError:
        return 0


def entrypoint() -> None:
    """Console-script entry point."""

    sys.exit(main())


if __name__ == "__main__":
    entrypoint()