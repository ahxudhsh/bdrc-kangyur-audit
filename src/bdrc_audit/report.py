"""Report: render a human-readable audit report from validation results.

Stub for v0.1.0 Day 1. The full report (failure taxonomy, cohort slices,
evidence-backed findings) lands on Day 4.
"""
from __future__ import annotations

from pathlib import Path


def run(index_csv: Path, out_path: Path) -> Path:
    """Build ``outputs/report.md`` from a master index CSV.

    Not implemented yet; raises so callers know this is a Day 1 stub.
    """
    raise NotImplementedError(
        "report.run is a Day 1 stub; report generation lands on Day 4."
    )
