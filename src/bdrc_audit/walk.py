"""RDF walk: discover Kangyur sub-works (W -> IE -> UTM) for a root W number.

Stub for v0.1.0 Day 1. Real RDF-graph traversal lands on Day 2 (migrated from
the branch_a MVP).
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class WalkResult:
    root: str
    candidates: list[str]


def run(root: str, limit: int | None = None) -> WalkResult:
    """Walk the RDF graph from ``root`` and return candidate sub-work ids.

    Not implemented yet; returns an empty result so the CLI wiring is testable.
    """
    raise NotImplementedError(
        "walk.run is a Day 1 stub; RDF traversal is migrated on Day 2."
    )
