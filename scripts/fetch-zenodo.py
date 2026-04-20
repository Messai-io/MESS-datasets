#!/usr/bin/env python3
"""
Fetch Zenodo records listed in data/zenodo/seed.yaml.

For each record:
  1. GET https://zenodo.org/api/records/<id>
  2. Write data/zenodo/<id>/metadata.json (pretty-printed snapshot).
  3. Download every file:
       - small (<= COMMIT_SIZE_LIMIT) and non-archive  → files/<key>  (committed)
       - everything else                                → .source/<key> (gitignored)
  4. Verify MD5 against Zenodo's reported checksum.
  5. Write data/zenodo/<id>/manifest.json.
  6. Generate data/zenodo/<id>/DATASHEET.md from template.

Idempotent: existing records are skipped unless --refresh is passed.

Usage:
    python scripts/fetch-zenodo.py                  # all records in seed.yaml
    python scripts/fetch-zenodo.py --ids 7050972    # subset
    python scripts/fetch-zenodo.py --refresh 7050972
    python scripts/fetch-zenodo.py --skip-download  # metadata-only
    python scripts/fetch-zenodo.py --dry-run
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests
import yaml

from _common import (
    DATA_DIR,
    load_env,
    stream_md5,
    write_json,
    zenodo_token,
)


ZENODO_API = "https://zenodo.org/api/records/{id}"

ZENODO_DIR = DATA_DIR / "zenodo"
SEED_PATH = ZENODO_DIR / "seed.yaml"

COMMIT_SIZE_LIMIT = 5 * 1024 * 1024  # 5 MiB

# File extensions we'll commit even below the size limit — human-readable
# sources + code. Anything else goes to .source/.
COMMIT_EXT = {
    ".csv",
    ".tsv",
    ".json",
    ".yaml",
    ".yml",
    ".md",
    ".txt",
    ".py",
    ".r",
    ".m",
    ".ipynb",
    ".xml",
    ".html",
    ".toml",
    ".ini",
    ".cfg",
    ".bib",
    ".ris",
}

# Extensions we always push to .source/ regardless of size (archives,
# binary blobs). Git already gitignores most of these, but being
# explicit here avoids staging them.
NEVER_COMMIT_EXT = {
    ".zip",
    ".tar",
    ".gz",
    ".tgz",
    ".bz2",
    ".xz",
    ".7z",
    ".rar",
    ".exe",
    ".dll",
    ".so",
    ".dylib",
    ".bin",
}


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Ingest Zenodo records into data/zenodo/.")
    p.add_argument(
        "--ids",
        help="Comma-separated subset of record IDs. Default: every id in seed.yaml.",
    )
    p.add_argument(
        "--refresh",
        help="Comma-separated record IDs to refetch (deletes existing metadata + files).",
    )
    p.add_argument(
        "--refresh-all",
        action="store_true",
        help="Refetch every record (destructive to files/ and .source/).",
    )
    p.add_argument(
        "--skip-download",
        action="store_true",
        help="Fetch metadata only; do not download files.",
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Print what would be fetched without doing it.",
    )
    p.add_argument(
        "--sleep",
        type=float,
        default=1.0,
        help="Seconds to sleep between record fetches (courtesy; default 1.0).",
    )
    return p.parse_args()


def load_seed() -> dict[str, Any]:
    with SEED_PATH.open("r", encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def session() -> requests.Session:
    s = requests.Session()
    s.headers["Accept"] = "application/json"
    s.headers["User-Agent"] = "MESS-datasets/0.1 (+https://github.com/Messai-io/MESS-datasets)"
    tok = zenodo_token()
    if tok:
        s.headers["Authorization"] = f"Bearer {tok}"
    return s


def classify_file(key: str, size: int) -> str:
    """Return 'commit' | 'source'."""
    ext = Path(key).suffix.lower()
    if ext in NEVER_COMMIT_EXT:
        return "source"
    if size > COMMIT_SIZE_LIMIT:
        return "source"
    if ext in COMMIT_EXT:
        return "commit"
    # Unknown small file → commit. Better to over-commit small human
    # artifacts than miss them.
    return "commit"


def rmtree(path: Path) -> None:
    if not path.exists():
        return
    if path.is_file() or path.is_symlink():
        path.unlink()
        return
    for child in path.iterdir():
        rmtree(child)
    path.rmdir()


def download(sess: requests.Session, url: str, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    with sess.get(url, stream=True, timeout=60) as r:
        r.raise_for_status()
        tmp = dest.with_suffix(dest.suffix + ".part")
        with tmp.open("wb") as fh:
            for chunk in r.iter_content(chunk_size=1 << 20):
                if chunk:
                    fh.write(chunk)
        tmp.replace(dest)


def extract_checksum(raw: str) -> str:
    """Zenodo reports 'md5:<hex>'. Return just the hex."""
    if raw.startswith("md5:"):
        return raw[len("md5:"):]
    return raw


def fetch_record(
    sess: requests.Session,
    record_id: str,
    *,
    skip_download: bool,
    dry_run: bool,
) -> dict[str, Any]:
    url = ZENODO_API.format(id=record_id)
    print(f"[{record_id}] GET {url}")
    if dry_run:
        return {"id": record_id, "dry_run": True}

    r = sess.get(url, timeout=30)
    r.raise_for_status()
    meta = r.json()

    rec_dir = ZENODO_DIR / record_id
    rec_dir.mkdir(parents=True, exist_ok=True)
    write_json(rec_dir / "metadata.json", meta)

    manifest_files: list[dict[str, Any]] = []
    for f in meta.get("files", []):
        key = f["key"]
        size = int(f["size"])
        checksum_raw = f.get("checksum", "")
        checksum_hex = extract_checksum(checksum_raw)
        dl_url = f.get("links", {}).get("self", "")

        bucket = classify_file(key, size)
        if bucket == "commit":
            local_rel = f"files/{key}"
        else:
            local_rel = f".source/{key}"
        dest = rec_dir / local_rel

        entry: dict[str, Any] = {
            "key": key,
            "size": size,
            "checksum": checksum_raw,
            "download_url": dl_url,
            "committed": bucket == "commit",
            "local_path": local_rel,
            "skipped_reason": None,
        }

        if skip_download:
            entry["skipped_reason"] = "skip_download flag"
            manifest_files.append(entry)
            continue

        if dest.exists():
            # Idempotency: trust prior download if size matches.
            if dest.stat().st_size == size:
                print(f"  [{key}] skip (already present, {size} bytes)")
                manifest_files.append(entry)
                continue
            # Size mismatch → refetch.
            dest.unlink()

        print(f"  [{key}] download {size} bytes → {local_rel}")
        try:
            download(sess, dl_url, dest)
        except Exception as exc:  # noqa: BLE001
            print(f"  [{key}] DOWNLOAD FAILED: {exc}")
            entry["skipped_reason"] = f"download_failed: {exc}"
            manifest_files.append(entry)
            continue

        if checksum_hex:
            got = stream_md5(dest)
            if got != checksum_hex:
                print(f"  [{key}] CHECKSUM MISMATCH: got {got}, expected {checksum_hex}")
                entry["skipped_reason"] = f"checksum_mismatch: got={got}"
        manifest_files.append(entry)

    manifest = {
        "source": "zenodo",
        "id": record_id,
        "doi": meta.get("doi"),
        "fetched_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "files": manifest_files,
    }
    write_json(rec_dir / "manifest.json", manifest)

    write_datasheet(rec_dir, meta, manifest)
    return manifest


def write_datasheet(rec_dir: Path, meta: dict, manifest: dict) -> None:
    m = meta.get("metadata", {})
    title = m.get("title") or meta.get("title") or "(untitled)"
    doi = meta.get("doi") or ""
    pub_date = m.get("publication_date") or ""
    license_id = (m.get("license") or {}).get("id") or ""
    creators = ", ".join(
        c.get("name", "") for c in m.get("creators", []) if c.get("name")
    )
    keywords = ", ".join(m.get("keywords", []) or [])
    description = m.get("description") or ""

    lines = [
        f"# {title}",
        "",
        f"- **Source**: Zenodo",
        f"- **Record ID**: `{manifest['id']}`",
        f"- **DOI**: [{doi}](https://doi.org/{doi})" if doi else "- **DOI**: _none_",
        f"- **Publication date**: {pub_date or '_unknown_'}",
        f"- **License (upstream)**: {license_id or '_unknown_'}",
        f"- **Creators**: {creators or '_unknown_'}",
        f"- **Keywords**: {keywords or '_none_'}",
        f"- **Fetched**: {manifest['fetched_at']}",
        "",
        "## Files",
        "",
        "| Key | Size (bytes) | Committed | Local path |",
        "| --- | --- | --- | --- |",
    ]
    for f in manifest["files"]:
        committed = "yes" if f["committed"] else "no (.source/)"
        lines.append(f"| `{f['key']}` | {f['size']} | {committed} | `{f['local_path']}` |")
    lines += [
        "",
        "## Abstract (from Zenodo)",
        "",
        description.strip() or "_no description provided_",
        "",
        "## MES relevance",
        "",
        "_Unreviewed._ Populate `mes_relevance`, `mes_domains`, `data_kinds`,",
        "and `related_slugs` in `catalog.json` during the classification pass.",
        "",
        "## Attribution",
        "",
        "Cite the upstream record per its license. Zenodo DOI is the canonical",
        "citation anchor.",
        "",
    ]
    (rec_dir / "DATASHEET.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    args = parse_args()
    load_env()

    seed = load_seed()
    all_ids = [str(r["id"]) for r in seed.get("records", [])]

    if args.ids:
        subset = {s.strip() for s in args.ids.split(",") if s.strip()}
        ids = [i for i in all_ids if i in subset]
        missing = subset - set(ids)
        if missing:
            print(f"WARN: ids not in seed.yaml: {sorted(missing)}", file=sys.stderr)
    else:
        ids = list(all_ids)

    refresh: set[str] = set()
    if args.refresh_all:
        refresh = set(all_ids)
    elif args.refresh:
        refresh = {s.strip() for s in args.refresh.split(",") if s.strip()}

    sess = session()

    for i, rid in enumerate(ids):
        rec_dir = ZENODO_DIR / rid
        if rid in refresh and rec_dir.exists() and not args.dry_run:
            print(f"[{rid}] --refresh: clearing {rec_dir}")
            rmtree(rec_dir)

        # Idempotency: if metadata already present AND we're not refreshing,
        # still make sure files are downloaded (in case of interrupted run).
        fetch_record(
            sess,
            rid,
            skip_download=args.skip_download,
            dry_run=args.dry_run,
        )
        if i < len(ids) - 1 and not args.dry_run:
            time.sleep(args.sleep)

    print(f"\nDone. Processed {len(ids)} record(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
