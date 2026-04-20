#!/usr/bin/env python3
"""
Fetch Figshare articles listed in data/figshare/seed.yaml.

For each article:
  1. GET https://api.figshare.com/v2/articles/<id>
  2. Write data/figshare/<id>/metadata.json.
  3. Download every file using the same classifier as Zenodo:
       - small non-archive         → files/<name>  (committed)
       - large / archive / binary  → .source/<name> (gitignored)
  4. Verify MD5 against Figshare's supplied_md5 (falling back to computed_md5).
  5. Write manifest.json including `paper_doi` (from article.resource_doi).
  6. Generate DATASHEET.md with paper-link, authors, license.

Idempotent. Mirrors fetch-zenodo.py's CLI.
"""

from __future__ import annotations

import argparse
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests
import yaml

from _common import DATA_DIR, load_env, stream_md5, write_json


FIGSHARE_API = "https://api.figshare.com/v2/articles/{id}"

FIGSHARE_DIR = DATA_DIR / "figshare"
SEED_PATH = FIGSHARE_DIR / "seed.yaml"

COMMIT_SIZE_LIMIT = 5 * 1024 * 1024  # 5 MiB — matches Zenodo fetcher.

# Same extension policy as fetch-zenodo.py. Kept duplicated here rather
# than in _common.py because the policy is an ingestion decision, not
# a utility — want it visible next to the script that applies it.
COMMIT_EXT = {
    ".csv", ".tsv", ".json", ".yaml", ".yml", ".md", ".txt",
    ".py", ".r", ".m", ".ipynb", ".xml", ".html", ".toml", ".ini",
    ".cfg", ".bib", ".ris",
}

NEVER_COMMIT_EXT = {
    ".zip", ".tar", ".gz", ".tgz", ".bz2", ".xz", ".7z", ".rar",
    ".exe", ".dll", ".so", ".dylib", ".bin",
}


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Ingest Figshare articles into data/figshare/.")
    p.add_argument("--ids", help="Comma-separated subset of article IDs.")
    p.add_argument("--refresh", help="Comma-separated IDs to refetch (destructive).")
    p.add_argument("--refresh-all", action="store_true")
    p.add_argument("--skip-download", action="store_true")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--sleep", type=float, default=1.0)
    return p.parse_args()


def load_seed() -> dict[str, Any]:
    with SEED_PATH.open("r", encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def session() -> requests.Session:
    s = requests.Session()
    s.headers["Accept"] = "application/json"
    s.headers["User-Agent"] = "MESS-datasets/0.1 (+https://github.com/Messai-io/MESS-datasets)"
    return s


def classify_file(name: str, size: int) -> str:
    ext = Path(name).suffix.lower()
    if ext in NEVER_COMMIT_EXT:
        return "source"
    if size > COMMIT_SIZE_LIMIT:
        return "source"
    if ext in COMMIT_EXT:
        return "commit"
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
    with sess.get(url, stream=True, timeout=120, allow_redirects=True) as r:
        r.raise_for_status()
        tmp = dest.with_suffix(dest.suffix + ".part")
        with tmp.open("wb") as fh:
            for chunk in r.iter_content(chunk_size=1 << 20):
                if chunk:
                    fh.write(chunk)
        tmp.replace(dest)


def fetch_record(
    sess: requests.Session,
    article_id: str,
    *,
    skip_download: bool,
    dry_run: bool,
) -> dict[str, Any]:
    url = FIGSHARE_API.format(id=article_id)
    print(f"[{article_id}] GET {url}")
    if dry_run:
        return {"id": article_id, "dry_run": True}

    r = sess.get(url, timeout=30)
    r.raise_for_status()
    meta = r.json()

    rec_dir = FIGSHARE_DIR / article_id
    rec_dir.mkdir(parents=True, exist_ok=True)
    write_json(rec_dir / "metadata.json", meta)

    manifest_files: list[dict[str, Any]] = []
    for f in meta.get("files", []) or []:
        name = f.get("name") or f.get("filename") or f"file-{f.get('id')}"
        size = int(f.get("size", 0))
        # Figshare reports both supplied_md5 (uploader-claimed) and
        # computed_md5 (server-verified). Prefer supplied as canonical.
        md5 = f.get("supplied_md5") or f.get("computed_md5") or ""
        checksum = f"md5:{md5}" if md5 else ""
        dl_url = f.get("download_url", "")

        bucket = classify_file(name, size)
        local_rel = f"{'files' if bucket == 'commit' else '.source'}/{name}"
        dest = rec_dir / local_rel

        entry: dict[str, Any] = {
            "key": name,
            "size": size,
            "checksum": checksum,
            "download_url": dl_url,
            "committed": bucket == "commit",
            "local_path": local_rel,
            "skipped_reason": None,
        }

        if skip_download:
            entry["skipped_reason"] = "skip_download flag"
            manifest_files.append(entry)
            continue

        if dest.exists() and dest.stat().st_size == size:
            print(f"  [{name}] skip (already present, {size} bytes)")
            manifest_files.append(entry)
            continue
        if dest.exists():
            dest.unlink()

        print(f"  [{name}] download {size} bytes → {local_rel}")
        try:
            download(sess, dl_url, dest)
        except Exception as exc:  # noqa: BLE001
            print(f"  [{name}] DOWNLOAD FAILED: {exc}")
            entry["skipped_reason"] = f"download_failed: {exc}"
            manifest_files.append(entry)
            continue

        if md5:
            got = stream_md5(dest)
            if got != md5:
                print(f"  [{name}] CHECKSUM MISMATCH: got {got}, expected {md5}")
                entry["skipped_reason"] = f"checksum_mismatch: got={got}"
        manifest_files.append(entry)

    manifest = {
        "source": "figshare",
        "id": article_id,
        "doi": meta.get("doi"),
        "paper_doi": meta.get("resource_doi"),
        "fetched_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "files": manifest_files,
    }
    write_json(rec_dir / "manifest.json", manifest)

    write_datasheet(rec_dir, meta, manifest)
    return manifest


def write_datasheet(rec_dir: Path, meta: dict, manifest: dict) -> None:
    title = meta.get("title") or "(untitled)"
    doi = meta.get("doi") or ""
    paper_doi = meta.get("resource_doi") or ""
    pub_date = (meta.get("created_date") or "").split("T")[0]
    license_name = (meta.get("license") or {}).get("name", "")
    authors = ", ".join(
        a.get("full_name", "") for a in (meta.get("authors") or []) if a.get("full_name")
    )
    keywords = ", ".join(meta.get("tags") or meta.get("keywords") or [])
    description = meta.get("description") or ""

    lines = [
        f"# {title}",
        "",
        f"- **Source**: Figshare",
        f"- **Article ID**: `{manifest['id']}`",
        f"- **Supplementary DOI**: [{doi}](https://doi.org/{doi})" if doi else "- **Supplementary DOI**: _none_",
        f"- **Paper DOI**: [{paper_doi}](https://doi.org/{paper_doi})" if paper_doi else "- **Paper DOI**: _none known_",
        f"- **Publication date**: {pub_date or '_unknown_'}",
        f"- **License (upstream)**: {license_name or '_unknown_'}",
        f"- **Authors**: {authors or '_unknown_'}",
        f"- **Keywords**: {keywords or '_none_'}",
        f"- **Fetched**: {manifest['fetched_at']}",
        "",
        "## Files",
        "",
        "| Name | Size (bytes) | Committed | Local path |",
        "| --- | --- | --- | --- |",
    ]
    for f in manifest["files"]:
        committed = "yes" if f["committed"] else "no (.source/)"
        lines.append(f"| `{f['key']}` | {f['size']} | {committed} | `{f['local_path']}` |")
    lines += [
        "",
        "## Description (from Figshare)",
        "",
        _strip_html(description).strip() or "_no description provided_",
        "",
        "## MES relevance",
        "",
        "_Unreviewed._ Populate `mes_relevance`, `mes_domains`, `data_kinds`,",
        "and `related_slugs` in `catalog.json` during the classification pass.",
        "",
        "## Attribution",
        "",
        "Cite the upstream paper via `paper_doi` and the Figshare supplementary",
        "record via its own DOI.",
        "",
    ]
    (rec_dir / "DATASHEET.md").write_text("\n".join(lines), encoding="utf-8")


def _strip_html(text: str) -> str:
    """Very lightweight HTML-to-text for Figshare descriptions."""
    import re

    text = re.sub(r"<br\s*/?>", "\n", text, flags=re.I)
    text = re.sub(r"<[^>]+>", "", text)
    text = text.replace("&nbsp;", " ").replace("&amp;", "&")
    text = text.replace("&lt;", "<").replace("&gt;", ">")
    return text


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
        rec_dir = FIGSHARE_DIR / rid
        if rid in refresh and rec_dir.exists() and not args.dry_run:
            print(f"[{rid}] --refresh: clearing {rec_dir}")
            rmtree(rec_dir)
        fetch_record(sess, rid, skip_download=args.skip_download, dry_run=args.dry_run)
        if i < len(ids) - 1 and not args.dry_run:
            time.sleep(args.sleep)

    print(f"\nDone. Processed {len(ids)} article(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
