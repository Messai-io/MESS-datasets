"""
Shared helpers for MESS-datasets ingestion pipelines.

Responsibilities:
- Canonical paths (REPO_ROOT, DATA_DIR).
- .env loading for per-source tokens.
- Small I/O helpers (atomic JSON writes, MD5 streaming).

Kept small and source-agnostic — source-specific logic lives in the
per-source fetcher (e.g. fetch-zenodo.py).
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv


REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = REPO_ROOT / "data"


def load_env() -> None:
    """Load .env from the repo root. Call once at script entry."""
    load_dotenv(REPO_ROOT / ".env")


def zenodo_token() -> str | None:
    """Return ZENODO_TOKEN if set; None otherwise."""
    tok = os.environ.get("ZENODO_TOKEN", "").strip()
    return tok or None


def write_json(path: Path, data: Any, *, sort_keys: bool = True) -> None:
    """Atomic pretty-printed JSON write."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2, sort_keys=sort_keys, ensure_ascii=False)
        fh.write("\n")
    tmp.replace(path)


def stream_md5(path: Path, *, chunk: int = 1 << 20) -> str:
    """Compute hex MD5 of a file by streaming."""
    h = hashlib.md5()
    with path.open("rb") as fh:
        while True:
            buf = fh.read(chunk)
            if not buf:
                break
            h.update(buf)
    return h.hexdigest()
