"""Tests for the shared HTTP layer: proxy config and rate limiting."""
from __future__ import annotations

import time

import pytest

from bdrc_audit import net


def test_proxy_none_by_default(monkeypatch):
    monkeypatch.delenv("BDRC_PROXY", raising=False)
    monkeypatch.delenv("HTTPS_PROXY", raising=False)
    assert net.proxy_url() is None
    assert net.proxies() == {}


def test_proxy_from_bdrc_proxy_env(monkeypatch):
    monkeypatch.delenv("HTTPS_PROXY", raising=False)
    monkeypatch.setenv("BDRC_PROXY", "http://127.0.0.1:7891")
    assert net.proxy_url() == "http://127.0.0.1:7891"
    assert net.proxies() == {
        "http": "http://127.0.0.1:7891",
        "https": "http://127.0.0.1:7891",
    }


def test_bdrc_proxy_takes_precedence(monkeypatch):
    monkeypatch.setenv("HTTPS_PROXY", "http://other:1")
    monkeypatch.setenv("BDRC_PROXY", "http://127.0.0.1:7891")
    assert net.proxy_url() == "http://127.0.0.1:7891"


def test_rate_limiter_rejects_bad_rps():
    with pytest.raises(ValueError):
        net.RateLimiter(max_rps=0)


def test_rate_limiter_enforces_min_interval():
    rate = net.RateLimiter(max_rps=50.0)  # 20ms min interval
    rate.wait()  # first call returns immediately
    start = time.monotonic()
    rate.wait()
    elapsed = time.monotonic() - start
    assert elapsed >= 0.015  # allow scheduler slack below the 20ms target


def test_build_session_has_retry_adapters(monkeypatch):
    monkeypatch.delenv("BDRC_PROXY", raising=False)
    monkeypatch.delenv("HTTPS_PROXY", raising=False)
    session = net.build_session(retries=3)
    adapter = session.get_adapter("http://purl.bdrc.io")
    assert adapter.max_retries.total == 3
