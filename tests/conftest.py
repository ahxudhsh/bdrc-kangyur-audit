"""Shared offline test fixtures: fake HTTP session and canned BDRC RDF data."""
from __future__ import annotations

from typing import Any, Callable

import pytest
import requests

from bdrc_audit import net


class FakeResponse:
    def __init__(
        self, status_code: int = 200, json_data: Any = None, text: str | None = None
    ) -> None:
        self.status_code = status_code
        self._json = json_data
        self.content = b"" if text is None else text.encode("utf-8")

    @property
    def ok(self) -> bool:
        return 200 <= self.status_code < 400

    def json(self) -> Any:
        return self._json

    def raise_for_status(self) -> None:
        if not self.ok:
            raise requests.HTTPError(f"status {self.status_code}", response=self)


Route = "FakeResponse | Callable[[], FakeResponse]"


class FakeSession:
    """Minimal stand-in for requests.Session driven by a url->response map."""

    def __init__(self, routes: dict[str, Any]) -> None:
        self.routes = routes
        self.calls: list[str] = []
        self.proxies: dict[str, str] = {}

    def get(self, url: str, timeout: float | None = None) -> FakeResponse:
        self.calls.append(url)
        resp = self.routes.get(url)
        if resp is None:
            return FakeResponse(404, json_data={}, text="not found")
        return resp() if callable(resp) else resp


def _wrap(rid: str, predicates: dict[str, Any]) -> dict[str, Any]:
    """Wrap predicates under the resource-uri key, mimicking purl.bdrc.io JSON."""
    return {f"http://purl.bdrc.io/resource/{rid}": predicates}


def _uri(rid: str) -> dict[str, str]:
    return {"type": "uri", "value": f"http://purl.bdrc.io/resource/{rid}"}


def _lit(value: str, lang: str = "bo-x-ewts") -> dict[str, str]:
    return {"type": "literal", "value": value, "lang": lang}


BDO = "http://purl.bdrc.io/ontology/core/"
SKOS = "http://www.w3.org/2004/02/skos/core#"


@pytest.fixture
def fast_rate() -> net.RateLimiter:
    """A rate limiter that never actually sleeps (for fast tests)."""
    return net.RateLimiter(max_rps=1_000_000.0)


@pytest.fixture
def walk_routes() -> dict[str, Any]:
    """Canned RDF for root W99 -> MW99 / IE99 -> V99_01 -> two UTM etexts."""
    base = "http://purl.bdrc.io/resource"
    routes: dict[str, Any] = {
        f"{base}/W99.json": FakeResponse(
            json_data=_wrap(
                "W99",
                {
                    f"{BDO}instanceReproductionOf": [_uri("MW99")],
                    f"{BDO}instanceHasReproduction": [_uri("IE99")],
                },
            )
        ),
        f"{base}/IE99.json": FakeResponse(
            json_data=_wrap("IE99", {f"{BDO}instanceHasVolume": [_uri("V99_01")]})
        ),
        f"{base}/V99_01.json": FakeResponse(
            json_data=_wrap(
                "V99_01",
                {
                    f"{BDO}volumeHasEtext": [
                        _uri("UTMW99_0001_0000"),
                        _uri("UTMW99_0002_0000"),
                    ]
                },
            )
        ),
        f"{base}/MW99_0001.json": FakeResponse(
            json_data=_wrap("MW99_0001", {f"{SKOS}prefLabel": [_lit("mdo 1")]})
        ),
        f"{base}/MW99_0002.json": FakeResponse(
            json_data=_wrap("MW99_0002", {f"{SKOS}prefLabel": [_lit("mdo 2")]})
        ),
    }
    return routes
