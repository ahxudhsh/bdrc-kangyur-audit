"""Shared HTTP layer: proxy config, rate limiting (<= 2 req/s) and retries.

Design notes
------------
- **Proxy**: direct by default so the tool works for anyone out of the box.
  Set ``BDRC_PROXY`` (or the standard ``HTTPS_PROXY``) to route through a local
  proxy, e.g. ``BDRC_PROXY=http://127.0.0.1:7891``.
- **Rate limit**: a token-free min-interval limiter caps requests at
  ``max_rps`` (default 2.0 req/s) to respect BDRC's terms.
- **Retries**: transport-level retries (default 3) with exponential backoff on
  429/5xx, honoring ``Retry-After``.
"""
from __future__ import annotations

import os
import threading
import time

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

DEFAULT_MAX_RPS = 2.0
DEFAULT_RETRIES = 3
DEFAULT_TIMEOUT = 30.0


def proxy_url() -> str | None:
    """Return the configured proxy URL, or ``None`` for a direct connection.

    Only an explicit ``BDRC_PROXY`` / ``HTTPS_PROXY`` enables proxying; there is
    no hard-coded default, so cloning and running needs no local proxy.
    """
    url = os.environ.get("BDRC_PROXY") or os.environ.get("HTTPS_PROXY")
    return url or None


def proxies() -> dict[str, str]:
    url = proxy_url()
    return {"http": url, "https": url} if url else {}


class RateLimiter:
    """Block so that calls happen at most ``max_rps`` per second (thread-safe)."""

    def __init__(self, max_rps: float = DEFAULT_MAX_RPS) -> None:
        if max_rps <= 0:
            raise ValueError("max_rps must be > 0")
        self.min_interval = 1.0 / max_rps
        self._lock = threading.Lock()
        self._next_allowed = 0.0

    def wait(self) -> None:
        with self._lock:
            now = time.monotonic()
            sleep_for = self._next_allowed - now
            if sleep_for > 0:
                time.sleep(sleep_for)
                now = time.monotonic()
            self._next_allowed = now + self.min_interval


def build_session(retries: int = DEFAULT_RETRIES) -> requests.Session:
    """Create a requests Session with retry adapters and proxy config."""
    session = requests.Session()
    session.proxies.update(proxies())
    retry = Retry(
        total=retries,
        connect=retries,
        read=retries,
        status=retries,
        backoff_factor=0.6,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=frozenset({"GET", "HEAD"}),
        respect_retry_after_header=True,
        raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session
