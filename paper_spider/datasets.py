# Copyright 2026 Isaacveg
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#     http://www.apache.org/licenses/LICENSE-2.0

"""Shared discovery and removal helpers for local conference datasets."""

from __future__ import annotations

import os
import shutil
import sqlite3
import time
from dataclasses import dataclass
from typing import List

YEAR_MIN = 1980
YEAR_MAX = 2100


@dataclass
class DatasetEntry:
    conf_slug: str
    year: int
    path: str
    paper_count: int = 0


def _safe_listdir(path: str) -> List[str]:
    try:
        return os.listdir(path)
    except OSError:
        return []


def _paper_count(db_path: str, conf_slug: str, year: int) -> int:
    try:
        with sqlite3.connect(db_path) as conn:
            row = conn.execute(
                "SELECT COUNT(*) FROM papers WHERE conf = ? AND year = ?",
                (conf_slug, year),
            ).fetchone()
    except sqlite3.Error:
        return 0
    return int(row[0]) if row else 0


def scan_datasets(base_dir: str) -> List[DatasetEntry]:
    """Scan local conference/year datasets under a base folder."""

    datasets: List[DatasetEntry] = []
    if not os.path.isdir(base_dir):
        return datasets
    for conf_slug in sorted(_safe_listdir(base_dir)):
        if conf_slug.startswith("."):
            continue
        conf_path = os.path.join(base_dir, conf_slug)
        if not os.path.isdir(conf_path):
            continue
        for year_name in sorted(_safe_listdir(conf_path), reverse=True):
            year_path = os.path.join(conf_path, year_name)
            if not os.path.isdir(year_path):
                continue
            db_path = os.path.join(year_path, "papers.sqlite")
            if not os.path.exists(db_path):
                continue
            try:
                year = int(year_name)
            except ValueError:
                continue
            if year < YEAR_MIN or year > YEAR_MAX:
                continue
            datasets.append(
                DatasetEntry(
                    conf_slug=conf_slug,
                    year=year,
                    path=year_path,
                    paper_count=_paper_count(db_path, conf_slug, year),
                )
            )
    return datasets


def move_dataset_to_trash(base_dir: str, dataset_path: str) -> bool:
    """Move a dataset folder into the base folder's .trash directory."""

    trash_root = os.path.join(base_dir, ".trash")
    try:
        os.makedirs(trash_root, exist_ok=True)
        stamp = int(time.time())
        name = os.path.relpath(dataset_path, base_dir).replace(os.sep, "_")
        destination = os.path.join(trash_root, f"{name}_{stamp}")
        shutil.move(dataset_path, destination)
    except (OSError, shutil.Error):
        return False
    return True