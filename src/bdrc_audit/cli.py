"""Command-line interface for bdrc-audit.

Day 1 skeleton: the four subcommands (walk / fetch / validate / report) are
wired to the argument parser but their handlers are stubs. They print a clear
"not implemented yet" notice and exit 0 so the CLI is demonstrable and the
plumbing is testable. Real logic is filled in on Days 2-4.
"""
from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence

from . import __version__

_NOT_IMPLEMENTED = "[bdrc-audit] '{cmd}' is a Day 1 stub and not implemented yet."


def _cmd_walk(args: argparse.Namespace) -> int:
    print(_NOT_IMPLEMENTED.format(cmd="walk"), file=sys.stderr)
    print(f"  would walk root={args.root!r} limit={args.limit}")
    return 0


def _cmd_fetch(args: argparse.Namespace) -> int:
    print(_NOT_IMPLEMENTED.format(cmd="fetch"), file=sys.stderr)
    print(f"  would fetch ids from {args.input!r} into {args.out_dir!r}")
    return 0


def _cmd_validate(args: argparse.Namespace) -> int:
    print(_NOT_IMPLEMENTED.format(cmd="validate"), file=sys.stderr)
    print(f"  would validate path={args.path!r}")
    return 0


def _cmd_report(args: argparse.Namespace) -> int:
    print(_NOT_IMPLEMENTED.format(cmd="report"), file=sys.stderr)
    print(f"  would build report from {args.index!r} into {args.out!r}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="bdrc-audit",
        description="Audit toolkit for BDRC Kangyur Unicode etexts.",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    sub = parser.add_subparsers(dest="command", metavar="{walk,fetch,validate,report}")

    p_walk = sub.add_parser("walk", help="Discover sub-works from a root W number.")
    p_walk.add_argument("root", help="Root work id, e.g. W22084.")
    p_walk.add_argument("--limit", type=int, default=None, help="Max candidates.")
    p_walk.set_defaults(func=_cmd_walk)

    p_fetch = sub.add_parser("fetch", help="Download Unicode etexts for sub-works.")
    p_fetch.add_argument("input", help="Path to candidates file (csv/json).")
    p_fetch.add_argument(
        "-o", "--out-dir", default="outputs/raw", help="Output directory."
    )
    p_fetch.set_defaults(func=_cmd_fetch)

    p_validate = sub.add_parser("validate", help="Run quality checks on etexts.")
    p_validate.add_argument("path", help="File or directory of etexts to validate.")
    p_validate.set_defaults(func=_cmd_validate)

    p_report = sub.add_parser("report", help="Render a human-readable audit report.")
    p_report.add_argument(
        "--index", default="outputs/kangyur_master_index_v0.csv", help="Index CSV."
    )
    p_report.add_argument("-o", "--out", default="outputs/report.md", help="Report path.")
    p_report.set_defaults(func=_cmd_report)

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not getattr(args, "command", None):
        parser.print_help()
        return 1
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
