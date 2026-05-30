"""Validate: structural quality checks on downloaded etexts.

This is the **structural tier** (v0): UTF-8 validity, Tibetan-block ratio, shad
(``།``) density, ``U+FFFD`` replacement chars, Latin contamination and the
``Image As Per Original Document`` OCR marker. It assigns each etext a
``pass`` / ``warn`` / ``fail`` status with human-readable reasons.

The heavier lexical tier (``lexical_score`` via botok / Monlam dictionaries)
is intentionally deferred to the later data-cleaning pass; the report only
needs the structural status to be useful.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

STATUSES = ("pass", "warn", "fail")

# Tibetan Unicode block.
_TIB_LO, _TIB_HI = "\u0f00", "\u0fff"
SHAD = "\u0f0d"  # །
NYIS_SHAD = "\u0f0e"  # ༎
REPLACEMENT = "\ufffd"
IMAGE_MARKER = "image as per original document"

# Thresholds (structural tier v0).
FAIL_TIBETAN_RATIO = 0.5
WARN_TIBETAN_RATIO = 0.8
WARN_MIN_CHARS = 500
WARN_LATIN_RATIO = 0.05
# At least 1 shad per 500 Tibetan chars; below 1.0 here means de-punctuated.
WARN_SHAD_PER_500 = 1.0


@dataclass
class ValidationResult:
    work_id: str
    status: str
    metrics: dict[str, float] = field(default_factory=dict)
    reasons: list[str] = field(default_factory=list)


def imagegroup_from_utm(utm_id: str) -> str:
    """``UTMW22084_0012_I0918`` -> ``I0918`` (the imagegroup cohort key)."""
    if not utm_id:
        return ""
    return utm_id.rsplit("_", 1)[-1]


def analyze(text: str) -> dict[str, float]:
    n_chars = len(text)
    n_tibetan = sum(1 for c in text if _TIB_LO <= c <= _TIB_HI)
    n_latin = sum(1 for c in text if c.isascii() and c.isalpha())
    n_nonspace = sum(1 for c in text if not c.isspace()) or 1
    n_shad = text.count(SHAD) + text.count(NYIS_SHAD)
    n_fffd = text.count(REPLACEMENT)
    shad_per_500 = (n_shad / (n_tibetan / 500)) if n_tibetan else 0.0
    return {
        "n_chars": n_chars,
        "n_tibetan": n_tibetan,
        "tibetan_ratio": round(n_tibetan / n_nonspace, 4),
        "latin_ratio": round(n_latin / (n_chars or 1), 4),
        "shad_count": n_shad,
        "shad_per_500_tib": round(shad_per_500, 2),
        "fffd_count": n_fffd,
        "has_image_marker": float(IMAGE_MARKER in text.lower()),
    }


def status_from_metrics(metrics: dict[str, float]) -> tuple[str, list[str]]:
    reasons: list[str] = []
    status = "pass"

    # --- fail conditions ---
    if metrics["fffd_count"] > 0:
        reasons.append(f"fffd_replacement_chars={int(metrics['fffd_count'])}")
        status = "fail"
    if metrics["has_image_marker"]:
        reasons.append("image_marker")
        status = "fail"
    if metrics["tibetan_ratio"] < FAIL_TIBETAN_RATIO:
        reasons.append(f"tibetan_ratio={metrics['tibetan_ratio']}<{FAIL_TIBETAN_RATIO}")
        status = "fail"

    if status == "fail":
        return status, reasons

    # --- warn conditions ---
    if metrics["tibetan_ratio"] < WARN_TIBETAN_RATIO:
        reasons.append(f"tibetan_ratio={metrics['tibetan_ratio']}<{WARN_TIBETAN_RATIO}")
        status = "warn"
    if metrics["n_chars"] < WARN_MIN_CHARS:
        reasons.append(f"too_short={int(metrics['n_chars'])}<{WARN_MIN_CHARS}")
        status = "warn"
    if metrics["n_tibetan"] and metrics["shad_per_500_tib"] < WARN_SHAD_PER_500:
        reasons.append(f"low_shad_density={metrics['shad_per_500_tib']}")
        status = "warn"
    if metrics["latin_ratio"] > WARN_LATIN_RATIO:
        reasons.append(f"latin_ratio={metrics['latin_ratio']}>{WARN_LATIN_RATIO}")
        status = "warn"

    return status, reasons


def validate_text(work_id: str, text: str) -> ValidationResult:
    metrics = analyze(text)
    status, reasons = status_from_metrics(metrics)
    return ValidationResult(work_id, status, metrics, reasons or ["ok"])


def run(path: Path, work_id: str | None = None) -> ValidationResult:
    """Validate a single etext file and return a pass/warn/fail result."""
    path = Path(path)
    wid = work_id or path.stem
    raw = path.read_bytes()
    try:
        text = raw.decode("utf-8", errors="strict")
    except UnicodeDecodeError as e:
        return ValidationResult(
            wid, "fail", {"n_chars": float(len(raw))}, [f"utf8_decode_error:{e.reason}"]
        )
    return validate_text(wid, text)
