"""Smoke tests for the bdrc-audit CLI."""
from __future__ import annotations

import pytest

from bdrc_audit import __version__
from bdrc_audit import cli
from bdrc_audit.cli import build_parser, main
from bdrc_audit.fetch import FetchOutcome, FetchResult
from bdrc_audit.walk import WalkResult


def test_version_string():
    assert __version__ == "0.1.0"


def test_no_command_prints_help_and_returns_1(capsys):
    assert main([]) == 1
    out = capsys.readouterr().out
    assert "usage:" in out


def test_validate_missing_path_returns_1(tmp_path, capsys):
    assert main(["validate", str(tmp_path / "nope")]) == 1
    assert "no such path" in capsys.readouterr().err


def test_report_missing_index_returns_1(tmp_path, capsys):
    assert main(["report", "--index", str(tmp_path / "nope.csv")]) == 1
    assert "no index" in capsys.readouterr().err


def test_validate_then_report_end_to_end(tmp_path):
    raw = tmp_path / "raw"
    raw.mkdir()
    (raw / "MW1_0001.txt").write_text("\u0f56\u0f0d " * 200, encoding="utf-8")
    (raw / "MW1_0002.txt").write_text("hello world only latin", encoding="utf-8")
    index = tmp_path / "index.csv"
    cands = tmp_path / "cands.csv"
    cands.write_text(
        "work_id,label,utm_id\nMW1_0001,t1,UTMW1_0001_I0001\n", encoding="utf-8"
    )
    assert main(["validate", str(raw), "-o", str(index), "--candidates", str(cands)]) == 0
    assert index.exists()
    report_md = tmp_path / "report.md"
    assert main(["report", "--index", str(index), "-o", str(report_md), "--root", "W1"]) == 0
    text = report_md.read_text(encoding="utf-8")
    assert "# Kangyur etext audit — W1" in text
    assert "Failure taxonomy" in text


def test_parser_exposes_all_subcommands():
    parser = build_parser()
    choices = set()
    for action in parser._actions:
        if hasattr(action, "choices") and action.choices:
            choices.update(action.choices)
    assert {"walk", "fetch", "validate", "report"} <= choices


def test_cli_walk_writes_csv(tmp_path, monkeypatch):
    out = tmp_path / "cands.csv"
    result = WalkResult(
        root="W99",
        mw_id="MW99",
        ie_id="IE99",
        candidates=[
            {
                "work_id": "MW99_0001",
                "label": "mdo 1",
                "source": "rdf_walk",
                "root_w": "W99",
                "mw_id": "MW99",
                "ie_id": "IE99",
                "utm_id": "UTMW99_0001_0000",
                "etext_url": "http://purl.bdrc.io/resource/UTMW99_0001_0000.txt",
            }
        ],
    )
    monkeypatch.setattr(cli.walk, "run", lambda *a, **k: result)
    assert main(["walk", "W99", "-o", str(out)]) == 0
    assert out.exists()
    assert "MW99_0001" in out.read_text(encoding="utf-8")


def test_cli_walk_handles_failure(monkeypatch, capsys):
    def boom(*a, **k):
        raise RuntimeError("no IE etext instance on W404")

    monkeypatch.setattr(cli.walk, "run", boom)
    assert main(["walk", "W404"]) == 1
    assert "walk failed" in capsys.readouterr().err


def test_cli_fetch_missing_input_returns_1(tmp_path, capsys):
    missing = tmp_path / "nope.csv"
    assert main(["fetch", str(missing)]) == 1
    assert "no such candidates file" in capsys.readouterr().err


def test_cli_fetch_runs(tmp_path, monkeypatch):
    csv_path = tmp_path / "cands.csv"
    csv_path.write_text(
        "work_id,etext_url\nMW99_0001,http://x/UTMW99_0001.txt\n", encoding="utf-8"
    )
    monkeypatch.setattr(
        cli.fetch,
        "run",
        lambda *a, **k: FetchResult([FetchOutcome("MW99_0001", "downloaded", chars=200)]),
    )
    assert main(["fetch", str(csv_path), "-o", str(tmp_path / "raw")]) == 0
