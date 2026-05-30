"""Command-line interface for bdrc-audit.

``walk`` and ``fetch`` are implemented (Day 2, migrated from the branch_a MVP).
``validate`` and ``report`` remain stubs until Days 3-4.
"""
from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from . import __version__, fetch, report, validate, walk


def _cmd_walk(args: argparse.Namespace) -> int:
    try:
        result = walk.run(args.root, limit=args.limit, with_labels=not args.no_labels)
    except Exception as e:  # noqa: BLE001 - surface a clean CLI error
        print(f"[bdrc-audit] walk failed: {e}", file=sys.stderr)
        return 1
    out_path = walk.write_csv(result, Path(args.out))
    mapped = sum(1 for c in result.candidates if c["utm_id"])
    print(
        f"walk root={result.root} mw={result.mw_id} ie={result.ie_id} "
        f"candidates={len(result.candidates)} utm_mapped={mapped} -> {out_path}"
    )
    return 0


def _cmd_fetch(args: argparse.Namespace) -> int:
    in_path = Path(args.input)
    if not in_path.exists():
        print(f"[bdrc-audit] fetch failed: no such candidates file {in_path}", file=sys.stderr)
        return 1
    candidates = fetch.load_candidates(in_path)
    result = fetch.run(candidates, Path(args.out_dir), force=args.force)
    print(
        f"fetch total={len(result.outcomes)} downloaded={result.downloaded} "
        f"skipped={result.skipped} failed={len(result.failed)} -> {args.out_dir}"
    )
    if result.failed:
        print("  failed: " + ", ".join(result.failed[:20]) +
              (" ..." if len(result.failed) > 20 else ""), file=sys.stderr)
    return 0


def _cmd_validate(args: argparse.Namespace) -> int:
    path = Path(args.path)
    if not path.exists():
        print(f"[bdrc-audit] validate failed: no such path {path}", file=sys.stderr)
        return 1
    if path.is_file():
        result = validate.run(path)
        print(f"{result.work_id}\t{result.status}\t{';'.join(result.reasons)}")
        return 0
    rows = report.build_index(path, candidates_csv=Path(args.candidates) if args.candidates else None)
    out = report.write_index(rows, Path(args.out))
    counts = {s: sum(1 for r in rows if r["status"] == s) for s in validate.STATUSES}
    print(
        f"validate dir={path} files={len(rows)} "
        f"pass={counts['pass']} warn={counts['warn']} fail={counts['fail']} -> {out}"
    )
    return 0


def _cmd_report(args: argparse.Namespace) -> int:
    index = Path(args.index)
    if not index.exists():
        print(
            f"[bdrc-audit] report failed: no index {index}; run `bdrc-audit validate` first.",
            file=sys.stderr,
        )
        return 1
    out = report.run(index, Path(args.out), root=args.root)
    print(f"report <- {index} -> {out}")
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
    p_walk.add_argument(
        "-o", "--out", default="outputs/rdf_candidates.csv", help="Candidates CSV path."
    )
    p_walk.add_argument(
        "--no-labels", action="store_true", help="Skip per-work label lookups (faster)."
    )
    p_walk.set_defaults(func=_cmd_walk)

    p_fetch = sub.add_parser("fetch", help="Download Unicode etexts for sub-works.")
    p_fetch.add_argument("input", help="Candidates CSV from `walk` (work_id, etext_url).")
    p_fetch.add_argument(
        "-o", "--out-dir", default="outputs/raw", help="Output directory."
    )
    p_fetch.add_argument(
        "--force", action="store_true", help="Re-download even if a file exists."
    )
    p_fetch.set_defaults(func=_cmd_fetch)

    p_validate = sub.add_parser("validate", help="Run quality checks on etexts.")
    p_validate.add_argument("path", help="A .txt file or a directory of etexts.")
    p_validate.add_argument(
        "-o", "--out", default="outputs/kangyur_master_index_v0.csv",
        help="Master index CSV to write (directory mode).",
    )
    p_validate.add_argument(
        "--candidates", default="outputs/rdf_candidates.csv",
        help="walk candidates CSV to join metadata (utm_id/imagegroup/label).",
    )
    p_validate.set_defaults(func=_cmd_validate)

    p_report = sub.add_parser("report", help="Render a human-readable audit report.")
    p_report.add_argument(
        "--index", default="outputs/kangyur_master_index_v0.csv", help="Index CSV."
    )
    p_report.add_argument("-o", "--out", default="outputs/report.md", help="Report path.")
    p_report.add_argument("--root", default="W22084", help="Root W id for the report title.")
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
