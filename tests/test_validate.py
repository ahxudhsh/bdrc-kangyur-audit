"""Tests for the structural validator."""
from __future__ import annotations

from bdrc_audit import validate

TIB = "\u0f56\u0f0d "  # ba + shad + space


def test_imagegroup_from_utm():
    assert validate.imagegroup_from_utm("UTMW22084_0012_I0918") == "I0918"
    assert validate.imagegroup_from_utm("") == ""


def test_clean_tibetan_passes():
    text = ("\u0f56\u0f60\u0f0d " * 300)  # plenty of Tibetan + shad
    result = validate.validate_text("MW_ok", text)
    assert result.status == "pass"
    assert result.metrics["tibetan_ratio"] > 0.8


def test_image_marker_fails_even_with_high_tibetan_ratio():
    text = TIB * 500 + "\nImage As Per Original Document\n"
    result = validate.validate_text("MW22084_0008", text)
    assert result.status == "fail"
    assert "image_marker" in result.reasons
    assert result.metrics["tibetan_ratio"] > 0.9  # regression: high ratio, still fail


def test_low_tibetan_ratio_fails():
    result = validate.validate_text("MW_latin", "hello world this is english only")
    assert result.status == "fail"
    assert any("tibetan_ratio" in r for r in result.reasons)


def test_fffd_fails():
    text = TIB * 300 + "\ufffd"
    result = validate.validate_text("MW_fffd", text)
    assert result.status == "fail"
    assert any("fffd" in r for r in result.reasons)


def test_short_text_warns():
    text = TIB * 20  # ~60 chars, well under 500
    result = validate.validate_text("MW_short", text)
    assert result.status == "warn"
    assert any("too_short" in r for r in result.reasons)


def test_run_reads_file(tmp_path):
    p = tmp_path / "MW_x.txt"
    p.write_text(TIB * 300, encoding="utf-8")
    result = validate.run(p)
    assert result.work_id == "MW_x"
    assert result.status == "pass"


def test_run_handles_invalid_utf8(tmp_path):
    p = tmp_path / "MW_bad.txt"
    p.write_bytes(b"\xff\xfe\xfa some bytes")
    result = validate.run(p)
    assert result.status == "fail"
    assert any("utf8_decode_error" in r for r in result.reasons)
