"""Offline tests for the RDF walk."""
from __future__ import annotations

import csv

import pytest

from bdrc_audit import walk
from bdrc_audit.walk import BdrcClient

from .conftest import FakeSession


def test_instance_from_utm_matches_root():
    assert walk.instance_from_utm("UTMW99_0001_0000", "MW99") == "MW99_0001"


def test_instance_from_utm_rejects_mismatched_root():
    assert walk.instance_from_utm("UTMW99_0001_0000", "MW42") is None


def test_instance_from_utm_rejects_non_utm():
    assert walk.instance_from_utm("W99_0001", "MW99") is None


def test_rid_from_uri():
    assert walk.rid_from_uri("http://purl.bdrc.io/resource/MW99/") == "MW99"


def test_run_discovers_candidates(walk_routes, fast_rate):
    client = BdrcClient(session=FakeSession(walk_routes), rate_limiter=fast_rate)
    result = walk.run("W99", client=client)
    assert result.mw_id == "MW99"
    assert result.ie_id == "IE99"
    ids = [c["work_id"] for c in result.candidates]
    assert ids == ["MW99_0001", "MW99_0002"]
    first = result.candidates[0]
    assert first["label"] == "mdo 1"
    assert first["etext_url"].endswith("UTMW99_0001_0000.txt")


def test_run_respects_limit(walk_routes, fast_rate):
    client = BdrcClient(session=FakeSession(walk_routes), rate_limiter=fast_rate)
    result = walk.run("W99", limit=1, client=client)
    assert len(result.candidates) == 1


def test_run_no_labels_skips_label_lookup(walk_routes, fast_rate):
    session = FakeSession(walk_routes)
    client = BdrcClient(session=session, rate_limiter=fast_rate)
    result = walk.run("W99", client=client, with_labels=False)
    assert result.candidates[0]["label"] == "MW99_0001"
    assert not any("MW99_0001.json" in url for url in session.calls)


def test_run_raises_when_no_ie(fast_rate):
    base = "http://purl.bdrc.io/resource"
    from .conftest import _uri, _wrap, BDO, FakeResponse

    routes = {
        f"{base}/W77.json": FakeResponse(
            json_data=_wrap(
                "W77", {f"{BDO}instanceReproductionOf": [_uri("MW77")]}
            )
        ),
    }
    client = BdrcClient(session=FakeSession(routes), rate_limiter=fast_rate)
    with pytest.raises(RuntimeError, match="no IE etext instance"):
        walk.run("W77", client=client)


def test_write_csv_roundtrip(tmp_path, walk_routes, fast_rate):
    client = BdrcClient(session=FakeSession(walk_routes), rate_limiter=fast_rate)
    result = walk.run("W99", client=client)
    out = walk.write_csv(result, tmp_path / "c.csv")
    with out.open(encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    assert len(rows) == 2
    assert set(rows[0]) == set(walk.CSV_FIELDS)
