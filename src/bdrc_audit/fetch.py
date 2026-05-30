"""Fetch: download Unicode etexts for discovered sub-works.

Stub for v0.1.0 Day 1. Rate-limited (<= 2 req/s), 3 retries and resume support
land on Day 2 (migrated from the branch_a MVP).
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass
class FetchResult:
    requested: int
    downloaded: int
    failed: list[str]


def run(ids: list[str], out_dir: Path) -> FetchResult:
    """Download etexts for ``ids`` into ``out_dir``.

    Not implemented yet; raises so callers know this is a Day 1 stub.
    """
    raise NotImplementedError(
        "fetch.run is a Day 1 stub; download logic is migrated on Day 2."
    )
