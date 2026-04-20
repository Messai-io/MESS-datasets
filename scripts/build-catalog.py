#!/usr/bin/env python3
"""
Scan data/zenodo/*/metadata.json + manifest.json and produce
data/zenodo/catalog.json.

Reads per-record artifacts, writes a compact aggregated index
conforming to schemas/dataset-catalog.schema.json.

Classification fields (`mes_relevance`, `mes_domains`, `data_kinds`,
`related_slugs`) are carried over from any existing catalog.json if
present — so a later classification pass can write to catalog.json
and not have those edits clobbered when we rebuild.

Usage:
    python scripts/build-catalog.py
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from _common import DATA_DIR, write_json


ZENODO_DIR = DATA_DIR / "zenodo"
CATALOG_PATH = ZENODO_DIR / "catalog.json"


def load_existing_classifications() -> dict[str, dict[str, Any]]:
    """Return {record_id: {mes_relevance, mes_domains, data_kinds, related_slugs}}."""
    if not CATALOG_PATH.exists():
        return {}
    try:
        with CATALOG_PATH.open("r", encoding="utf-8") as fh:
            prev = json.load(fh)
    except Exception:
        return {}
    out: dict[str, dict[str, Any]] = {}
    for r in prev.get("records", []):
        out[str(r.get("id"))] = {
            "mes_relevance": r.get("mes_relevance", None),
            "mes_domains": r.get("mes_domains", []) or [],
            "data_kinds": r.get("data_kinds", []) or [],
            "related_slugs": r.get("related_slugs") or {"parameters": [], "materials": []},
        }
    return out


def build_record(
    rec_dir: Path,
    prior: dict[str, dict[str, Any]],
) -> dict[str, Any] | None:
    meta_path = rec_dir / "metadata.json"
    manifest_path = rec_dir / "manifest.json"
    if not meta_path.exists() or not manifest_path.exists():
        return None

    with meta_path.open("r", encoding="utf-8") as fh:
        meta = json.load(fh)
    with manifest_path.open("r", encoding="utf-8") as fh:
        manifest = json.load(fh)

    m = meta.get("metadata", {}) or {}
    record_id = str(rec_dir.name)
    p = prior.get(record_id, {})

    files = manifest.get("files", []) or []
    total_bytes = sum(int(f.get("size", 0)) for f in files)
    committed_count = sum(1 for f in files if f.get("committed"))

    creators = [
        c.get("name")
        for c in (m.get("creators") or [])
        if isinstance(c, dict) and c.get("name")
    ]

    return {
        "source": "zenodo",
        "id": record_id,
        "doi": meta.get("doi"),
        "title": m.get("title") or meta.get("title") or "",
        "publication_date": m.get("publication_date"),
        "license": (m.get("license") or {}).get("id"),
        "creators": creators,
        "keywords": list(m.get("keywords") or []),
        "files": {
            "count": len(files),
            "total_bytes": total_bytes,
            "committed_count": committed_count,
        },
        "mes_relevance": p.get("mes_relevance", None),
        "mes_domains": p.get("mes_domains", []),
        "data_kinds": p.get("data_kinds", []),
        "related_slugs": p.get("related_slugs", {"parameters": [], "materials": []}),
        "last_synced": manifest.get("fetched_at")
        or datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }


def main() -> int:
    prior = load_existing_classifications()
    records: list[dict[str, Any]] = []
    for child in sorted(ZENODO_DIR.iterdir()):
        if not child.is_dir():
            continue
        if child.name.startswith("."):
            continue
        rec = build_record(child, prior)
        if rec:
            records.append(rec)

    # Stable order: by id ascending as integer if possible.
    def _key(r: dict[str, Any]) -> tuple[int, str]:
        try:
            return (int(r["id"]), r["id"])
        except (ValueError, TypeError):
            return (10**18, str(r["id"]))

    records.sort(key=_key)

    catalog = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "records": records,
    }
    write_json(CATALOG_PATH, catalog)
    print(f"Wrote {CATALOG_PATH} with {len(records)} record(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
