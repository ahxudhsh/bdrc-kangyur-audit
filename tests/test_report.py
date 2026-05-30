"""Tests for index building and report rendering."""
from __future__ import annotations

import csv

from bdrc_audit import report

TIB = "\u0f56\u0f0d "


def _make_raw(tmp_path):
    raw = tmp_path / "raw"
    raw.mkdir()
    (raw / "MW1_0001.txt").write_text(TIB * 400, encoding="utf-8")  # pass
    (raw / "MW1_0002.txt").write_text(
        TIB * 400 + "\nImage As Per Original Document\n", encoding="utf-8"
    )  # fail (marker)
    (raw / "MW1_0003.txt").write_text("latin only english text here", encoding="utf-8")  # fail
    return raw


def test_build_index_assigns_status(tmp_path):
    raw = _make_raw(tmp_path)
    cands = tmp_path / "c.csv"
    cands.write_text(
        "work_id,label,utm_id\n"
        "MW1_0001,t1,UTMW1_0001_I0001\n"
        "MW1_0002,t2,UTMW1_0002_I0001\n"
        "MW1_0003,t3,UTMW1_0003_I0002\n",
        encoding="utf-8",
    )
    rows = report.build_index(raw, candidates_csv=cands)
    by_id = {r["work_id"]: r for r in rows}
    assert by_id["MW1_0001"]["status"] == "pass"
    assert by_id["MW1_0002"]["status"] == "fail"
    assert by_id["MW1_0002"]["has_image_marker"] == 1
    assert by_id["MW1_0001"]["imagegroup"] == "I0001"


def test_write_and_load_index_roundtrip(tmp_path):
    raw = _make_raw(tmp_path)
    rows = report.build_index(raw)
    out = report.write_index(rows, tmp_path / "index.csv")
    with out.open(encoding="utf-8") as f:
        loaded = list(csv.DictReader(f))
    assert len(loaded) == 3
    assert set(loaded[0]) == set(report.INDEX_FIELDS)


def test_render_has_required_sections(tmp_path):
    raw = _make_raw(tmp_path)
    rows = report.build_index(raw)
    md = report.render(rows, root="W1")
    assert "# Kangyur etext audit — W1" in md
    assert "## Summary" in md
    assert "## Failure taxonomy" in md
    assert "## Cohort slices" in md
    assert "## Findings" in md
    # at least 3 findings are enumerated
    assert "3." in md


def test_failure_taxonomy_counts_reasons(tmp_path):
    raw = _make_raw(tmp_path)
    rows = report.build_index(raw)
    tax = report._failure_taxonomy(rows)
    assert tax.get("image_marker", 0) >= 1
    assert tax.get("tibetan_ratio", 0) >= 1


def test_run_writes_report(tmp_path):
    raw = _make_raw(tmp_path)
    rows = report.build_index(raw)
    index = report.write_index(rows, tmp_path / "index.csv")
    out = report.run(index, tmp_path / "report.md", root="W1")
    assert out.exists()
    assert "Kangyur etext audit" in out.read_text(encoding="utf-8")
