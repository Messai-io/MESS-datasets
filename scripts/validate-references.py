#!/usr/bin/env python3
"""
Referential integrity check for data/classifications.yaml.

For each classification entry, verify that every slug in
`related_slugs.parameters` exists in MESS-Parameters, and every slug
in `related_slugs.materials` exists in MESS-Materials. Exit 1 on any
violation; output a human-readable report either way.

Slug sources resolved via scripts/_slug_sources.py (local-first,
URL-fallback for CI).
"""

from __future__ import annotations

import sys
from pathlib import Path

import yaml

from _common import DATA_DIR
from _slug_sources import load_material_slugs, load_parameter_slugs


CLASSIFICATIONS_PATH = DATA_DIR / "classifications.yaml"


def main() -> int:
    if not CLASSIFICATIONS_PATH.exists():
        print(f"No {CLASSIFICATIONS_PATH} — nothing to validate.", file=sys.stderr)
        return 0

    with CLASSIFICATIONS_PATH.open("r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh) or {}

    entries: dict[str, dict] = data.get("entries") or {}
    if not isinstance(entries, dict):
        print(f"classifications.yaml: `entries` must be a mapping", file=sys.stderr)
        return 1

    param_slugs = load_parameter_slugs()
    mat_slugs = load_material_slugs()
    print(f"Loaded {len(param_slugs)} parameter slugs, {len(mat_slugs)} material slugs.")

    errors: list[str] = []
    total_params = 0
    total_materials = 0
    for key, cls in entries.items():
        related = (cls or {}).get("related_slugs") or {}
        params = related.get("parameters") or []
        materials = related.get("materials") or []
        total_params += len(params)
        total_materials += len(materials)
        for slug in params:
            if slug not in param_slugs:
                errors.append(f"{key}: unknown parameter slug '{slug}'")
        for slug in materials:
            if slug not in mat_slugs:
                errors.append(f"{key}: unknown material slug '{slug}'")

    if errors:
        print("\nFAILED referential integrity:")
        for e in errors:
            print(f"  - {e}")
        print(f"\n{len(errors)} violation(s) across {len(entries)} entries.")
        return 1

    print(
        f"OK — {len(entries)} entries, "
        f"{total_params} parameter refs, {total_materials} material refs, "
        f"all resolve."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
