"""Offline tests for etext fetching (rate limit / retries / resume)."""
from __future__ import annotations

from bdrc_audit import fetch

from .conftest import FakeResponse, FakeSession

GOOD_TEXT = "བཀའ་འགྱུར། " * 50  # > MIN_TEXT_CHARS Tibetan content


def _routes_ok(url: str) -> dict:
    return {url: FakeResponse(200, text=GOOD_TEXT)}


def test_url_variants_adds_https_counterpart():
    variants = fetch._url_variants("http://x/a.txt#utm=1")
    assert variants == ["http://x/a.txt", "https://x/a.txt"]


def test_fetch_one_downloads(tmp_path, fast_rate):
    url = "http://purl.bdrc.io/resource/UTMW99_0001.txt"
    session = FakeSession(_routes_ok(url))
    out = fetch.fetch_one("MW99_0001", url, tmp_path, session, fast_rate)
    assert out.status == "downloaded"
    assert (tmp_path / "MW99_0001.txt").read_text(encoding="utf-8") == GOOD_TEXT
    assert out.chars == len(GOOD_TEXT)


def test_fetch_one_resumes_existing(tmp_path, fast_rate):
    url = "http://x/a.txt"
    (tmp_path / "MW99_0001.txt").write_text("already here", encoding="utf-8")
    session = FakeSession(_routes_ok(url))
    out = fetch.fetch_one("MW99_0001", url, tmp_path, session, fast_rate)
    assert out.status == "skipped"
    assert session.calls == []  # no network call when resuming


def test_fetch_one_force_redownloads(tmp_path, fast_rate):
    url = "http://x/a.txt"
    (tmp_path / "MW99_0001.txt").write_text("old", encoding="utf-8")
    session = FakeSession(_routes_ok(url))
    out = fetch.fetch_one("MW99_0001", url, tmp_path, session, fast_rate, force=True)
    assert out.status == "downloaded"
    assert session.calls  # network call happened


def test_fetch_one_html_is_rejected(tmp_path, fast_rate):
    url = "http://x/a.txt"
    session = FakeSession({url: FakeResponse(200, text="<!DOCTYPE html><html>nope")})
    # http and https variants both map to the same url here
    session.routes["https://x/a.txt"] = FakeResponse(200, text="<html>nope")
    out = fetch.fetch_one("MW99_X", url, tmp_path, session, fast_rate)
    assert out.status == "failed"
    assert out.error == "html_not_text"


def test_fetch_one_too_short_is_rejected(tmp_path, fast_rate):
    url = "http://x/a.txt"
    session = FakeSession(
        {url: FakeResponse(200, text="short"), "https://x/a.txt": FakeResponse(200, text="short")}
    )
    out = fetch.fetch_one("MW99_X", url, tmp_path, session, fast_rate)
    assert out.status == "failed"
    assert out.error == "text_too_short"


def test_fetch_one_no_url(tmp_path, fast_rate):
    out = fetch.fetch_one("MW99_X", "", tmp_path, FakeSession({}), fast_rate)
    assert out.status == "failed"
    assert out.error == "no_etext_url"


def test_run_aggregates(tmp_path, fast_rate):
    u1 = "http://purl.bdrc.io/resource/UTMW99_0001.txt"
    u2 = "http://purl.bdrc.io/resource/UTMW99_0002.txt"
    routes = {u1: FakeResponse(200, text=GOOD_TEXT), u2: FakeResponse(404, text="x")}
    routes["https://purl.bdrc.io/resource/UTMW99_0002.txt"] = FakeResponse(404, text="x")
    session = FakeSession(routes)
    candidates = [
        {"work_id": "MW99_0001", "etext_url": u1},
        {"work_id": "MW99_0002", "etext_url": u2},
    ]
    result = fetch.run(candidates, tmp_path, session=session, rate_limiter=fast_rate)
    assert result.downloaded == 1
    assert result.failed == ["MW99_0002"]


def test_load_candidates(tmp_path):
    p = tmp_path / "c.csv"
    p.write_text("work_id,etext_url\nMW1,http://x/1.txt\n", encoding="utf-8")
    rows = fetch.load_candidates(p)
    assert rows == [{"work_id": "MW1", "etext_url": "http://x/1.txt"}]
