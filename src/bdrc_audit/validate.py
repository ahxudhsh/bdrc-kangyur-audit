"""Validate: multi-dimensional quality checks on downloaded etexts.

Stub for v0.1.0 Day 1. The upgraded validator (lexical_score, shad_density on
top of UTF-8 / Tibetan-ratio checks) lands on Day 3.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

STATUSES = ("pass", "warn", "fail")


@dataclass
class ValidationResult:
    path: str
    status: str
    metrics: dict[str, float] = field(default_factory=dict)
    notes: list[str] = field(default_factory=list)


def run(path: Path) -> ValidationResult:
    """Validate a single etext file and return a pass/warn/fail result.

    Not implemented yet; raises so callers know this is a Day 1 stub.
    """
    raise NotImplementedError(
        "validate.run is a Day 1 stub; multi-dimensional checks land on Day 3."
    )
