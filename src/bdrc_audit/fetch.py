"""Fetch: download Unicode etexts for discovered sub-works.

Migrated from the branch_a MVP (``audit_download.py`` / ``bulk_download.py``).
Adds:
- **rate limit** (<= 2 req/s) via :class:`bdrc_audit.net.RateLimiter`
- **retries** (transport-level via the shared session + a small app-level loop)
- **resume**: existing non-empty output files are skipped unless ``force``.

OpenPecha BoCorpus fallback from the MVP is intentionally out of scope here; the
RDF walk already yields direct ``purl.bdrc.io`` ``.txt`` URLs.
"""
from __future__ import annotations

import csv
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

import requests

from . import net

MIN_TEXT_CHARS = 100


@dataclass
class FetchOutcome:
    work_id: str
    status: str  # "downloaded" | "skipped" | "failed"
    path: str = ""
    chars: int = 0
    http_status: str = ""
    error: str = ""


@dataclass
class FetchResult:
    outcomes: list[FetchOutcome] = field(default_factory=list)

    @property
    def downloaded(self) -> int:
        return sum(1 for o in self.outcomes if o.status == "downloaded")

    @property
    def skipped(self) -> int:
        return sum(1 for o in self.outcomes if o.status == "skipped")

    @property
    def failed(self) -> list[str]:
        return [o.work_id for o in self.outcomes if o.status == "failed"]


def _url_variants(url: str) -> list[str]:
    """Return [url] plus its http<->https counterpart, dropping fragments."""
    url = url.split("#")[0]
    variants = [url]
    if url.startswith("http://"):
        variants.append("https://" + url[len("http://") :])
    elif url.startswith("https://"):
        variants.append("http://" + url[len("https://") :])
    return variants


def load_candidates(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def fetch_one(
    work_id: str,
    etext_url: str,
    out_dir: Path,
    session: requests.Session,
    rate: net.RateLimiter,
    timeout: float = 120.0,
    force: bool = False,
) -> FetchOutcome:
    out = out_dir / f"{work_id}.txt"
    if out.exists() and out.stat().st_size > 0 and not force:
        return FetchOutcome(work_id, "skipped", str(out), out.stat().st_size)

    if not etext_url:
        return FetchOutcome(work_id, "failed", error="no_etext_url")

    last_status = ""
    last_err = "http_error"
    for url in _url_variants(etext_url):
        try:
            rate.wait()
            r = session.get(url, timeout=timeout)
            last_status = str(r.status_code)
            if not r.ok:
                last_err = "http_error"
                continue
            text = r.content.decode("utf-8", errors="strict")
            stripped = text.lstrip()
            if stripped.startswith("<!") or stripped.startswith("<html"):
                last_err = "html_not_text"
                continue
            if len(text) < MIN_TEXT_CHARS:
                last_err = "text_too_short"
                continue
            out_dir.mkdir(parents=True, exist_ok=True)
            out.write_text(text, encoding="utf-8")
            return FetchOutcome(work_id, "downloaded", str(out), len(text), last_status)
        except UnicodeDecodeError:
            last_err = "utf8_decode_error"
        except requests.RequestException as e:
            last_err = type(e).__name__
            last_status = last_status or "0"

    return FetchOutcome(work_id, "failed", http_status=last_status, error=last_err)


def run(
    candidates: Iterable[dict[str, str]],
    out_dir: Path,
    session: requests.Session | None = None,
    rate_limiter: net.RateLimiter | None = None,
    force: bool = False,
) -> FetchResult:
    """Download etexts for ``candidates`` into ``out_dir``.

    Each candidate dict needs ``work_id`` and ``etext_url``. Existing non-empty
    files are skipped (resume) unless ``force`` is set.
    """
    session = session or net.build_session()
    rate = rate_limiter or net.RateLimiter()
    out_dir = Path(out_dir)
    result = FetchResult()
    for c in candidates:
        result.outcomes.append(
            fetch_one(
                work_id=c["work_id"],
                etext_url=c.get("etext_url", ""),
                out_dir=out_dir,
                session=session,
                rate=rate,
                force=force,
            )
        )
    return result
