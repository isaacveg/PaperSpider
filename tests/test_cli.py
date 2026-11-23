# Copyright 2026 Isaacveg
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#     http://www.apache.org/licenses/LICENSE-2.0

from __future__ import annotations

import io
import json
import os
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from paper_spider.cli import main
from paper_spider.models import PaperMeta
from paper_spider.operations import PaperSpiderOperations, resolve_base_dir

REPO_ROOT = Path(__file__).resolve().parents[1]
PAPERS = [
    PaperMeta(
        paper_id="p1",
        title="Alpha Systems",
        conf="iclr",
        year=2025,
        authors=["Alice"],
        abstract="An alpha abstract about systems",
        keywords=["systems"],
    ),
    PaperMeta(
        paper_id="p2",
        title="Beta Vision",
        conf="iclr",
        year=2025,
        authors=["Bob"],
        keywords=["vision"],
    ),
    PaperMeta(
        paper_id="p3",
        title="Gamma Systems",
        conf="iclr",
        year=2025,
        authors=["Carol"],
        keywords=["systems"],
    ),
]


class _FakeConference:
    name = "ICLR"
    slug = "iclr"

    def __init__(self) -> None:
        self.request_delay = 0.0

    def list_papers(self, year: int):
        return [
            PaperMeta(
                paper_id=paper.paper_id,
                title=paper.title,
                conf=self.slug,
                year=year,
                category=paper.category,
                authors=list(paper.authors),
                abstract=paper.abstract,
                keywords=list(paper.keywords),
            )
            for paper in PAPERS
        ]

    def fetch_details(self, paper: PaperMeta) -> PaperMeta:
        paper.abstract = f"Fetched abstract for {paper.paper_id}"
        paper.authors = list(paper.authors) + ["Dana"]
        paper.keywords = list(paper.keywords) + ["fetched"]
        paper.pdf_url = f"https://example.com/{paper.paper_id}.pdf"
        paper.bibtex_url = f"https://example.com/{paper.paper_id}.bib"
        paper.bibtex = f"@inproceedings{{{paper.paper_id}}}"
        return paper

    def fetch_pdf(self, paper: PaperMeta) -> bytes:
        return b"%PDF-1.7\nfake pdf"

    def fetch_bibtex(self, paper: PaperMeta) -> str:
        return f"@inproceedings{{{paper.paper_id},\n  title = {{{paper.title}}}\n}}"


class CliTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.api = PaperSpiderOperations(
            base_dir=self.temp_dir.name,
            conference_provider=lambda: [_FakeConference()],
            request_delay_ms=0,
        )

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def run_cli(self, *argv: str):
        stdout = io.StringIO()
        stderr = io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            code = main(list(argv), api=self.api)
        return code, stdout.getvalue(), stderr.getvalue()

    def add_dataset(self) -> None:
        code, _, stderr = self.run_cli("add", "iclr", "2025")
        self.assertEqual(0, code, stderr)

    def test_help_and_version(self) -> None:
        stdout = io.StringIO()
        with redirect_stdout(stdout), self.assertRaises(SystemExit) as context:
            main(["--help"], api=self.api)
        self.assertEqual(0, context.exception.code)
        output = stdout.getvalue()
        for command in (
            "conferences",
            "datasets",
            "add",
            "search",
            "show",
            "download-abstracts",
            "download-pdfs",
            "download-bibtex",
            "export",
        ):
            self.assertIn(command, output)

        stdout = io.StringIO()
        with redirect_stdout(stdout), self.assertRaises(SystemExit) as context:
            main(["--version"], api=self.api)
        self.assertEqual(0, context.exception.code)
        self.assertIn("paperspider-cli", stdout.getvalue())

    def test_conferences_accepts_json_before_or_after_command(self) -> None:
        code, stdout, stderr = self.run_cli(
            "conferences", "--query", "iclr"
        )
        self.assertEqual(0, code)
        self.assertIn("iclr\tICLR", stdout)
        self.assertIn("1 conference", stderr)

        for argv in (
            ("--json", "conferences", "--query", "iclr"),
            ("conferences", "--query", "iclr", "--json"),
        ):
            code, stdout, _ = self.run_cli(*argv)
            self.assertEqual(0, code)
            data = json.loads(stdout)
            self.assertEqual(1, data["count"])
            self.assertEqual("iclr", data["conferences"][0]["slug"])

    def test_add_and_datasets(self) -> None:
        code, stdout, stderr = self.run_cli("add", "iclr", "2025")
        self.assertEqual(0, code, stderr)
        self.assertIn("Fetched 3 papers", stdout)
        self.assertTrue(
            os.path.exists(
                os.path.join(self.temp_dir.name, "iclr", "2025", "papers.sqlite")
            )
        )

        code, stdout, _ = self.run_cli("datasets")
        self.assertEqual(0, code)
        self.assertIn("iclr\t2025\t3\ticlr/2025", stdout)

        code, stdout, _ = self.run_cli("--json", "datasets")
        self.assertEqual(0, code)
        data = json.loads(stdout)
        self.assertEqual(1, data["count"])
        self.assertTrue(data["datasets"][0]["supported"])

    def test_search_filters_pages_and_searches_all_datasets(self) -> None:
        self.add_dataset()

        code, stdout, stderr = self.run_cli(
            "search", "--conf", "iclr", "--year", "2025", "--query", "alpha"
        )
        self.assertEqual(0, code)
        self.assertIn("p1\tAlpha Systems", stdout)
        self.assertNotIn("p2", stdout)
        self.assertIn("Showing 1 of 1", stderr)

        code, _, stderr = self.run_cli(
            "search",
            "--conf",
            "iclr",
            "--year",
            "2025",
            "--query",
            "systems",
        )
        self.assertEqual(0, code)
        self.assertIn("Showing 2 of 2", stderr)

        code, stdout, _ = self.run_cli(
            "search",
            "--conf",
            "iclr",
            "--year",
            "2025",
            "--query",
            "systems",
            "--limit",
            "1",
            "--offset",
            "1",
            "--json",
        )
        self.assertEqual(0, code)
        data = json.loads(stdout)
        self.assertEqual(2, data["total"])
        self.assertEqual(1, data["count"])
        self.assertEqual(1, data["offset"])

        code, stdout, _ = self.run_cli(
            "search", "--query", "systems", "--abstract"
        )
        self.assertEqual(0, code)
        self.assertIn("An alpha abstract about systems", stdout)

        code, stdout, _ = self.run_cli("search", "--query", "vision")
        self.assertEqual(0, code)
        self.assertIn("p2\tBeta Vision", stdout)

    def test_show_and_fetch(self) -> None:
        self.add_dataset()

        code, stdout, _ = self.run_cli("show", "iclr", "2025", "p2")
        self.assertEqual(0, code)
        self.assertIn("not downloaded", stdout)

        code, stdout, _ = self.run_cli(
            "show", "iclr", "2025", "p2", "--fetch", "--bibtex"
        )
        self.assertEqual(0, code)
        self.assertIn("Fetched abstract for p2", stdout)
        self.assertIn("@inproceedings{p2}", stdout)

        code, stdout, _ = self.run_cli(
            "show", "iclr", "2025", "p2", "--json"
        )
        self.assertEqual(0, code)
        self.assertEqual(
            "Fetched abstract for p2",
            json.loads(stdout)["paper"]["abstract"],
        )

    def test_download_abstracts(self) -> None:
        self.add_dataset()

        code, stdout, stderr = self.run_cli(
            "download-abstracts", "iclr", "2025", "p1", "p2"
        )
        self.assertEqual(0, code)
        self.assertIn("p2\tBeta Vision", stdout)
        self.assertIn("Fetched abstract for p2", stdout)
        self.assertNotIn("p1\tAlpha Systems", stdout)
        self.assertIn("Downloaded 1 abstract(s), skipped 1", stderr)

    def test_download_pdfs_and_recover_deleted_files(self) -> None:
        self.add_dataset()

        code, stdout, stderr = self.run_cli(
            "download-pdfs", "iclr", "2025", "p1", "p2"
        )
        self.assertEqual(0, code, stderr)
        lines = [line for line in stdout.splitlines() if line.strip()]
        self.assertEqual(2, len(lines))
        paths = {}
        for line in lines:
            paper_id, path = line.split("\t")
            paths[paper_id] = path
            self.assertTrue(os.path.exists(path))
            with open(path, "rb") as handle:
                self.assertTrue(handle.read().startswith(b"%PDF"))

        os.remove(paths["p1"])
        code, stdout, _ = self.run_cli("show", "iclr", "2025", "p1", "--json")
        self.assertEqual(0, code)
        self.assertFalse(json.loads(stdout)["paper"]["has_pdf"])

        code, _, stderr = self.run_cli(
            "download-pdfs", "iclr", "2025", "p1"
        )
        self.assertEqual(0, code, stderr)
        self.assertIn("Downloaded 1 PDF(s)", stderr)

        code, _, stderr = self.run_cli(
            "download-pdfs", "iclr", "2025", "p1"
        )
        self.assertEqual(0, code)
        self.assertIn("skipped 1", stderr)

    def test_download_bibtex(self) -> None:
        self.add_dataset()

        code, stdout, stderr = self.run_cli(
            "download-bibtex", "iclr", "2025", "p1", "p2"
        )
        self.assertEqual(0, code, stderr)
        lines = [line for line in stdout.splitlines() if line.strip()]
        self.assertEqual(2, len(lines))
        for line in lines:
            _, path = line.split("\t")
            self.assertTrue(os.path.exists(path))

        code, stdout, _ = self.run_cli(
            "show", "iclr", "2025", "p1", "--bibtex"
        )
        self.assertEqual(0, code)
        self.assertIn("@inproceedings{p1", stdout)

    def test_export_formats_save_and_json_wrapper(self) -> None:
        self.add_dataset()

        code, stdout, _ = self.run_cli(
            "export", "iclr", "2025", "p1", "--format", "csv"
        )
        self.assertEqual(0, code)
        self.assertTrue(stdout.startswith("title,authors"))
        self.assertIn("Alpha Systems", stdout)

        code, stdout, _ = self.run_cli(
            "export", "iclr", "2025", "--format", "json"
        )
        self.assertEqual(0, code)
        exported = json.loads(stdout)
        self.assertEqual(3, len(exported))

        code, stdout, _ = self.run_cli(
            "export", "iclr", "2025", "--format", "txt"
        )
        self.assertEqual(0, code)
        self.assertEqual(3, len(stdout.splitlines()))

        code, stdout, _ = self.run_cli(
            "export", "iclr", "2025", "p1", "p2", "--format", "bibtex"
        )
        self.assertEqual(0, code)
        self.assertIn("@inproceedings{p1", stdout)
        self.assertIn("@inproceedings{p2", stdout)

        code, stdout, stderr = self.run_cli(
            "export",
            "iclr",
            "2025",
            "p1",
            "--format",
            "csv",
            "--save",
            "--filename",
            "../../report",
        )
        self.assertEqual(0, code, stderr)
        self.assertIn("Saved to", stderr)
        export_path = stderr.split("Saved to ", 1)[1].splitlines()[0]
        exports_dir = os.path.join(
            self.temp_dir.name, "iclr", "2025", "exports"
        )
        self.assertEqual(exports_dir, os.path.dirname(export_path))
        self.assertTrue(os.path.exists(export_path))
        with open(export_path, "r", encoding="utf-8", newline="") as handle:
            self.assertEqual(stdout.strip(), handle.read().strip())

        code, stdout, _ = self.run_cli(
            "--json", "export", "iclr", "2025", "p1", "--format", "csv"
        )
        self.assertEqual(0, code)
        data = json.loads(stdout)
        self.assertEqual("csv", data["format"])
        self.assertIn("Alpha Systems", data["content"])

    def test_export_requires_a_selected_field(self) -> None:
        self.add_dataset()
        code, _, stderr = self.run_cli(
            "export",
            "iclr",
            "2025",
            "--format",
            "csv",
            "--no-title",
            "--no-authors",
        )
        self.assertEqual(1, code)
        self.assertIn("Select at least one field", stderr)

    def test_operation_errors(self) -> None:
        code, _, stderr = self.run_cli(
            "search", "--conf", "iclr", "--year", "2024"
        )
        self.assertEqual(1, code)
        self.assertIn("no local dataset", stderr)

        code, _, stderr = self.run_cli("add", "nope", "2025")
        self.assertEqual(1, code)
        self.assertIn("not supported", stderr)

        code, _, stderr = self.run_cli(
            "search", "--conf", "../etc", "--year", "2025"
        )
        self.assertEqual(1, code)
        self.assertIn("conference must be a slug", stderr)

        self.add_dataset()
        code, _, stderr = self.run_cli(
            "download-pdfs", "iclr", "2025", "missing"
        )
        self.assertEqual(1, code)
        self.assertIn("not found", stderr)

        code, _, stderr = self.run_cli(
            "download-pdfs",
            "iclr",
            "2025",
            *[f"p{index}" for index in range(201)],
        )
        self.assertEqual(1, code)
        self.assertIn("at most 200", stderr)

    def test_invalid_year_is_a_usage_error(self) -> None:
        stderr = io.StringIO()
        with redirect_stderr(stderr), self.assertRaises(SystemExit) as context:
            main(["search", "--year", "1700"], api=self.api)
        self.assertEqual(2, context.exception.code)
        self.assertIn("year must be between 1980 and 2100", stderr.getvalue())

    def test_resolve_base_dir_prefers_environment(self) -> None:
        resolved = resolve_base_dir(
            environ={"PAPERSPIDER_BASE_DIR": "~/paper-spider-data"}
        )
        self.assertEqual(
            os.path.abspath(os.path.expanduser("~/paper-spider-data")),
            resolved,
        )


class ManPageTests(unittest.TestCase):
    def test_manual_documents_every_command_and_option(self) -> None:
        path = REPO_ROOT / "man" / "paperspider-cli.1"
        text = path.read_text(encoding="utf-8")
        for command in (
            "conferences",
            "datasets",
            "add",
            "search",
            "show",
            "download\\-abstracts",
            "download\\-pdfs",
            "download\\-bibtex",
            "export",
        ):
            self.assertIn(command, text)
        for option in (
            "\\-\\-base\\-dir",
            "\\-\\-delay\\-ms",
            "\\-\\-json",
            "\\-\\-fetch",
            "\\-\\-bibtex",
            "\\-\\-format",
            "\\-\\-save",
            "\\-\\-filename",
            "\\-\\-abstract",
            "\\-\\-no\\-title",
            "\\-\\-no\\-authors",
        ):
            self.assertIn(option, text)
        for env_name in (
            "PAPERSPIDER_BASE_DIR",
            "PAPERSPIDER_REQUEST_DELAY_MS",
        ):
            self.assertIn(env_name, text)
        for path_name in ("papers.sqlite", "pdf/", "bib/", "exports/"):
            self.assertIn(path_name, text)
        for exit_code in ("0", "1", "2", "130"):
            self.assertIn(exit_code, text)


if __name__ == "__main__":
    unittest.main()