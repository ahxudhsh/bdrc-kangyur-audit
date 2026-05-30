"""RDF walk: discover Kangyur sub-works (W -> MW / IE -> volumes -> UTM etexts).

Migrated from the branch_a MVP (``bdrc_rdf.py`` / ``run_rdf_walk.py``) into the
package, with the shared rate-limited + retrying HTTP session from
:mod:`bdrc_audit.net`.
"""
from __future__ import annotations

import csv
import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import requests

from . import net

BASE = "http://purl.bdrc.io/resource"
BDO = "http://purl.bdrc.io/ontology/core/"
SKOS = "http://www.w3.org/2004/02/skos/core#"
RDFS_LABEL = "http://www.w3.org/2000/01/rdf-schema#label"
ETEXT_URL = "http://purl.bdrc.io/resource/{utm}.txt"

UTM_INSTANCE_RE = re.compile(r"^UTM(W\d+)_(\d{4}[A-Z]?)_")

CSV_FIELDS = [
    "work_id",
    "label",
    "source",
    "root_w",
    "mw_id",
    "ie_id",
    "utm_id",
    "etext_url",
]


def instance_from_utm(utm: str, mw_rid: str) -> str | None:
    """Derive an ``MW...._NNNN`` instance id from a ``UTM...`` etext id."""
    m = UTM_INSTANCE_RE.match(utm)
    if not m:
        return None
    w_root, suffix = m.group(1), m.group(2)
    expected_mw = f"MW{w_root[1:]}"
    if mw_rid != expected_mw:
        return None
    return f"{mw_rid}_{suffix}"


def rid_from_uri(uri: str) -> str:
    return urlparse(uri).path.rstrip("/").split("/")[-1]


def uri_values(obj: dict[str, Any], predicate: str) -> list[str]:
    items = obj.get(predicate, [])
    return [x["value"] for x in items if x.get("type") == "uri"]


def literal_values(
    obj: dict[str, Any], predicate: str, lang: str | None = "bo-x-ewts"
) -> list[str]:
    items = obj.get(predicate, [])
    out: list[str] = []
    for x in items:
        if x.get("type") != "literal":
            continue
        if lang is None or x.get("lang") in (lang, "bo", ""):
            out.append(x["value"])
    return out


@dataclass
class WalkResult:
    root: str
    mw_id: str | None
    ie_id: str | None
    candidates: list[dict[str, str]] = field(default_factory=list)


class BdrcClient:
    """Walk purl.bdrc.io resource JSON with caching, rate limiting and retries."""

    def __init__(
        self,
        session: requests.Session | None = None,
        rate_limiter: net.RateLimiter | None = None,
        timeout: float = net.DEFAULT_TIMEOUT,
    ) -> None:
        self.timeout = timeout
        self._session = session or net.build_session()
        self._rate = rate_limiter or net.RateLimiter()
        self._cache: dict[str, dict[str, Any]] = {}

    def fetch(self, rid: str) -> dict[str, Any]:
        rid = rid_from_uri(rid) if rid.startswith("http") else rid
        if rid in self._cache:
            return self._cache[rid]
        url = f"{BASE}/{rid}.json"
        last_err: Exception | None = None
        for attempt in range(net.DEFAULT_RETRIES):
            try:
                self._rate.wait()
                r = self._session.get(url, timeout=self.timeout)
                r.raise_for_status()
                data = r.json()
                key = f"{BASE}/{rid}"
                if key not in data:
                    key = next(
                        (k for k in data if k.rstrip("/").endswith(f"/{rid}")),
                        key,
                    )
                if key not in data:
                    raise KeyError(f"unexpected JSON shape for {rid}")
                self._cache[rid] = data[key]
                return data[key]
            except (requests.RequestException, KeyError) as e:
                last_err = e
                time.sleep(0.5 * (attempt + 1))
        assert last_err is not None
        raise last_err

    def label_for(self, rid: str) -> str:
        obj = self.fetch(rid)
        for pred in (f"{SKOS}prefLabel", f"{SKOS}altLabel", RDFS_LABEL):
            vals = literal_values(obj, pred, lang=None)
            if vals:
                return vals[0]
        return rid

    def mw_from_w(self, w_rid: str) -> str:
        obj = self.fetch(w_rid)
        for uri in uri_values(obj, f"{BDO}instanceReproductionOf"):
            rid = rid_from_uri(uri)
            if rid.startswith("MW"):
                return rid
        raise ValueError(f"no MW instanceReproductionOf on {w_rid}")

    def ie_from_w(self, w_rid: str) -> str | None:
        obj = self.fetch(w_rid)
        for uri in uri_values(obj, f"{BDO}instanceHasReproduction"):
            rid = rid_from_uri(uri)
            if rid.startswith("IE"):
                return rid
        return None

    def collect_etext_candidates(
        self, ie_rid: str, mw_rid: str, limit: int | None = None
    ) -> list[dict[str, str]]:
        """Scan IE volumes; derive (MW instance, utm) from volumeHasEtext ids."""
        ie = self.fetch(ie_rid)
        volumes = uri_values(ie, f"{BDO}instanceHasVolume")
        results: list[dict[str, str]] = []
        seen: set[str] = set()
        for vol_uri in volumes:
            vol = rid_from_uri(vol_uri)
            try:
                ve = self.fetch(vol)
            except requests.RequestException:
                continue
            for utm_uri in uri_values(ve, f"{BDO}volumeHasEtext"):
                utm = rid_from_uri(utm_uri)
                inst = instance_from_utm(utm, mw_rid)
                if not inst or inst in seen:
                    continue
                seen.add(inst)
                results.append({"work_id": inst, "utm_id": utm})
                if limit is not None and len(results) >= limit:
                    return results
        return results

    def etext_url(self, utm_rid: str) -> str:
        return ETEXT_URL.format(utm=utm_rid)


def run(
    root: str,
    limit: int | None = None,
    client: BdrcClient | None = None,
    with_labels: bool = True,
) -> WalkResult:
    """Walk the RDF graph from ``root`` (a digital instance W id) and return
    candidate sub-works, each with its UTM etext id and download URL.
    """
    client = client or BdrcClient()
    mw = client.mw_from_w(root)
    ie = client.ie_from_w(root)
    if not ie:
        raise RuntimeError(f"no IE etext instance on {root}")
    raw = client.collect_etext_candidates(ie, mw, limit)
    if not raw:
        raise RuntimeError(f"no UTM etext candidates under {ie}")

    candidates: list[dict[str, str]] = []
    for item in raw:
        inst, utm = item["work_id"], item["utm_id"]
        candidates.append(
            {
                "work_id": inst,
                "label": client.label_for(inst) if with_labels else inst,
                "source": "rdf_walk",
                "root_w": root,
                "mw_id": mw,
                "ie_id": ie,
                "utm_id": utm,
                "etext_url": client.etext_url(utm),
            }
        )
    return WalkResult(root=root, mw_id=mw, ie_id=ie, candidates=candidates)


def write_csv(result: WalkResult, out_path: Path) -> Path:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        writer.writeheader()
        writer.writerows(result.candidates)
    return out_path
