#!/usr/bin/env python3
"""
Scan per-source record directories and produce:

  data/zenodo/catalog.json      — zenodo records only
  data/figshare/catalog.json    — figshare records only
  data/catalog.json             — unified (all sources, source-keyed)

All three conform to schemas/dataset-catalog.schema.json.

Classification fields (`mes_relevance`, `mes_domains`, `data_kinds`,
`related_slugs`) from prior catalogs are preserved across rebuilds —
so a later classification pass can write to any catalog and not get
clobbered.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

import yaml

from _common import DATA_DIR, write_json


CLASSIFICATIONS_PATH = DATA_DIR / "classifications.yaml"


def load_yaml_classifications() -> dict[str, dict[str, Any]]:
    """Return {<source>:<id> -> classification dict} from the YAML."""
    if not CLASSIFICATIONS_PATH.exists():
        return {}
    with CLASSIFICATIONS_PATH.open("r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh) or {}
    entries = data.get("entries") or {}
    if not isinstance(entries, dict):
        return {}
    return {k: v for k, v in entries.items() if isinstance(v, dict)}


SOURCES: list[tuple[str, Path, Callable[[dict, dict], dict]]] = []


def load_prior_classifications(catalog_path: Path) -> dict[str, dict[str, Any]]:
    """Return {(source, id) or id -> classification dict}."""
    if not catalog_path.exists():
        return {}
    try:
        prev = json.loads(catalog_path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    out: dict[str, dict[str, Any]] = {}
    for r in prev.get("records", []):
        key = f"{r.get('source')}:{r.get('id')}"
        out[key] = {
            "mes_relevance": r.get("mes_relevance", None),
            "mes_domains": r.get("mes_domains", []) or [],
            "data_kinds": r.get("data_kinds", []) or [],
            "related_slugs": r.get("related_slugs") or {"parameters": [], "materials": []},
        }
    return out


def summarize_files(manifest: dict) -> dict[str, int]:
    files = manifest.get("files", []) or []
    return {
        "count": len(files),
        "total_bytes": sum(int(f.get("size", 0)) for f in files),
        "committed_count": sum(1 for f in files if f.get("committed")),
    }


def _resolve_classification(
    key: str,
    prior: dict[str, dict[str, Any]],
    yaml_entries: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    """YAML is the human source of truth; prior catalog is a fallback."""
    if key in yaml_entries:
        y = yaml_entries[key]
        return {
            "mes_relevance": y.get("mes_relevance", None),
            "mes_domains": list(y.get("mes_domains") or []),
            "data_kinds": list(y.get("data_kinds") or []),
            "related_slugs": y.get("related_slugs") or {"parameters": [], "materials": []},
        }
    return prior.get(key, {})


def build_zenodo_record(
    rec_dir: Path,
    prior: dict[str, dict[str, Any]],
    yaml_entries: dict[str, dict[str, Any]],
) -> dict[str, Any] | None:
    meta_path = rec_dir / "metadata.json"
    manifest_path = rec_dir / "manifest.json"
    if not meta_path.exists() or not manifest_path.exists():
        return None
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    m = meta.get("metadata", {}) or {}
    record_id = rec_dir.name
    p = _resolve_classification(f"zenodo:{record_id}", prior, yaml_entries)

    # Try to pull a paper DOI from related_identifiers (relation ~ isSupplementTo).
    paper_doi = None
    for ri in m.get("related_identifiers") or []:
        if (ri.get("relation") or "").lower() in {
            "issupplementto", "isderivedfrom", "isdocumentedby", "cites"
        } and (ri.get("scheme") or "").lower() == "doi":
            paper_doi = ri.get("identifier")
            break

    creators = [
        c.get("name") for c in (m.get("creators") or [])
        if isinstance(c, dict) and c.get("name")
    ]

    return {
        "source": "zenodo",
        "id": record_id,
        "doi": meta.get("doi"),
        "paper_doi": paper_doi,
        "title": m.get("title") or meta.get("title") or "",
        "publication_date": m.get("publication_date"),
        "license": (m.get("license") or {}).get("id"),
        "creators": creators,
        "keywords": list(m.get("keywords") or []),
        "files": summarize_files(manifest),
        "mes_relevance": p.get("mes_relevance", None),
        "mes_domains": p.get("mes_domains", []),
        "data_kinds": p.get("data_kinds", []),
        "related_slugs": p.get("related_slugs", {"parameters": [], "materials": []}),
        "last_synced": manifest.get("fetched_at")
        or datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }


def build_figshare_record(
    rec_dir: Path,
    prior: dict[str, dict[str, Any]],
    yaml_entries: dict[str, dict[str, Any]],
) -> dict[str, Any] | None:
    meta_path = rec_dir / "metadata.json"
    manifest_path = rec_dir / "manifest.json"
    if not meta_path.exists() or not manifest_path.exists():
        return None
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    record_id = rec_dir.name
    p = _resolve_classification(f"figshare:{record_id}", prior, yaml_entries)

    authors = [
        a.get("full_name") for a in (meta.get("authors") or [])
        if isinstance(a, dict) and a.get("full_name")
    ]
    pub_date = (meta.get("created_date") or "").split("T")[0] or None
    lic = (meta.get("license") or {}).get("name")

    return {
        "source": "figshare",
        "id": record_id,
        "doi": meta.get("doi"),
        "paper_doi": meta.get("resource_doi"),
        "title": meta.get("title") or "",
        "publication_date": pub_date,
        "license": lic,
        "creators": authors,
        "keywords": list(meta.get("tags") or meta.get("keywords") or []),
        "files": summarize_files(manifest),
        "mes_relevance": p.get("mes_relevance", None),
        "mes_domains": p.get("mes_domains", []),
        "data_kinds": p.get("data_kinds", []),
        "related_slugs": p.get("related_slugs", {"parameters": [], "materials": []}),
        "last_synced": manifest.get("fetched_at")
        or datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }


SOURCE_BUILDERS: dict[str, Callable[[Path, dict, dict], dict | None]] = {
    "zenodo": build_zenodo_record,
    "figshare": build_figshare_record,
}


def stable_sort_key(r: dict[str, Any]) -> tuple[str, int, str]:
    try:
        return (r["source"], int(r["id"]), r["id"])
    except (ValueError, TypeError):
        return (r["source"], 10**18, str(r["id"]))


def scan_source(source: str) -> list[dict[str, Any]]:
    source_dir = DATA_DIR / source
    if not source_dir.is_dir():
        return []
    per_source_catalog = source_dir / "catalog.json"
    unified_catalog = DATA_DIR / "catalog.json"

    # Prior classifications: merge per-source + unified so edits anywhere survive.
    prior = {
        **load_prior_classifications(per_source_catalog),
        **load_prior_classifications(unified_catalog),
    }

    yaml_entries = load_yaml_classifications()

    builder = SOURCE_BUILDERS[source]
    records: list[dict[str, Any]] = []
    for child in sorted(source_dir.iterdir()):
        if not child.is_dir() or child.name.startswith("."):
            continue
        rec = builder(child, prior, yaml_entries)
        if rec:
            records.append(rec)
    records.sort(key=stable_sort_key)
    return records


def main() -> int:
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")

    all_records: list[dict[str, Any]] = []
    for source in SOURCE_BUILDERS:
        records = scan_source(source)
        per_source_path = DATA_DIR / source / "catalog.json"
        write_json(per_source_path, {"generated_at": now, "records": records})
        print(f"Wrote {per_source_path} ({len(records)} records)")
        all_records.extend(records)

    all_records.sort(key=stable_sort_key)
    unified_path = DATA_DIR / "catalog.json"
    write_json(unified_path, {"generated_at": now, "records": all_records})
    print(f"Wrote {unified_path} ({len(all_records)} records across {len(SOURCE_BUILDERS)} sources)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
