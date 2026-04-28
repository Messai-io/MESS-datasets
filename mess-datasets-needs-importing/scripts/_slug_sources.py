"""
Shared slug loader.

Local-first (sibling MESS-Parameters / MESS-Materials clones), with
URL fallback for CI. Results cached to ci/.slug-cache/ so CI runs stay
fast after the first hit.

Slugification matches messai-ai's parameter-slug.ts exactly — see
MESS-Materials/scripts/_common.py for the reference implementation.
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any

from _common import REPO_ROOT


PARAMETERS_LOCAL_CANDIDATES = [
    REPO_ROOT.parent / "MESS-Parameters" / "data" / "parameter-definitions-rich.json",
    Path.home() / "repos" / "messai-ai" / "open-source" / "MESS-Parameters"
    / "data" / "parameter-definitions-rich.json",
]

MATERIALS_LOCAL_CANDIDATES = [
    REPO_ROOT.parent / "MESS-Materials" / "data" / "mess-material-slugs.json",
    Path.home() / "repos" / "messai-ai" / "open-source" / "MESS-Materials"
    / "data" / "mess-material-slugs.json",
]

PARAMETERS_URL = (
    "https://raw.githubusercontent.com/Messai-io/MESS-Parameters/main/"
    "data/parameter-definitions-rich.json"
)
MATERIALS_URL = (
    "https://raw.githubusercontent.com/Messai-io/MESS-Materials/main/"
    "data/mess-material-slugs.json"
)

CACHE_DIR = REPO_ROOT / "ci" / ".slug-cache"


def slugify(name: str) -> str:
    """Byte-compatible with messai-ai's slugify (see MESS-Materials _common.py)."""
    s = name.lower()
    s = re.sub(r"\s+", "_", s)
    s = re.sub(r"[()/]", "", s)
    s = s.replace(":", "", 1)
    return s


def _cached_load(name: str, local_candidates: list[Path], url: str) -> Any:
    """Try each local path; fall back to URL with on-disk cache."""
    for p in local_candidates:
        if p.exists():
            return json.loads(p.read_text(encoding="utf-8"))

    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache = CACHE_DIR / name
    if cache.exists() and os.environ.get("MESS_SLUG_FORCE_REFETCH") != "1":
        return json.loads(cache.read_text(encoding="utf-8"))

    # Import lazily; avoid requests dep when running purely local.
    import requests

    r = requests.get(url, timeout=30)
    r.raise_for_status()
    data = r.json()
    cache.write_text(json.dumps(data), encoding="utf-8")
    return data


def load_parameter_slugs() -> set[str]:
    """Return the set of all valid MESS-Parameters slugs (~687)."""
    data = _cached_load(
        "parameter-definitions-rich.json",
        PARAMETERS_LOCAL_CANDIDATES,
        PARAMETERS_URL,
    )
    if not isinstance(data, list):
        raise RuntimeError("parameter-definitions-rich.json must be a list")
    return {slugify(e["name"]) for e in data if isinstance(e, dict) and e.get("name")}


def load_material_slugs() -> set[str]:
    """Return the 26 MESS-Materials slugs (subset of parameter slugs)."""
    data = _cached_load(
        "mess-material-slugs.json",
        MATERIALS_LOCAL_CANDIDATES,
        MATERIALS_URL,
    )
    entries = data.get("slugs", []) if isinstance(data, dict) else []
    return {e["slug"] for e in entries if isinstance(e, dict) and e.get("slug")}
