"""Smoke tests for the bdrc-audit CLI skeleton (Day 1)."""
from __future__ import annotations

import pytest

from bdrc_audit import __version__
from bdrc_audit.cli import build_parser, main


def test_version_string():
    assert __version__ == "0.1.0"


def test_no_command_prints_help_and_returns_1(capsys):
    assert main([]) == 1
    out = capsys.readouterr().out
    assert "usage:" in out


@pytest.mark.parametrize(
    "argv",
    [
        ["walk", "W22084"],
        ["walk", "W22084", "--limit", "5"],
        ["fetch", "candidates.csv"],
        ["fetch", "candidates.csv", "-o", "outputs/raw"],
        ["validate", "some/path"],
        ["report"],
        ["report", "--index", "i.csv", "-o", "r.md"],
    ],
)
def test_subcommands_are_wired_and_exit_zero(argv):
    assert main(argv) == 0


def test_parser_exposes_all_subcommands():
    parser = build_parser()
    # argparse stores subparser choices on the subparsers action.
    choices = set()
    for action in parser._actions:
        if hasattr(action, "choices") and action.choices:
            choices.update(action.choices)
    assert {"walk", "fetch", "validate", "report"} <= choices
