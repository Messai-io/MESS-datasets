# scripts/

Ingestion + index pipelines.

## Quick start

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python scripts/fetch-zenodo.py
python scripts/build-catalog.py
```

## Files

- `_common.py` — paths, env loader, atomic writes, MD5 streaming.
- `fetch-zenodo.py` — reads `data/zenodo/seed.yaml`, populates
  `data/zenodo/<id>/{metadata.json, manifest.json, DATASHEET.md}` and downloads
  each record's files into `files/` (committed) or `.source/` (gitignored) based
  on size + extension.
- `build-catalog.py` — scans per-record artifacts and writes
  `data/zenodo/catalog.json`. Preserves any classification fields
  (`mes_relevance`, `mes_domains`, `data_kinds`, `related_slugs`) from a prior
  catalog so rebuilds are non-destructive.

## Adding a new source

1. Drop a `fetch-<source>.py` here following the same pattern.
2. Add the source to the `source` enum in the three `schemas/*.schema.json`
   files.
3. Create `data/<source>/{SOURCE.md, seed.yaml}`.
4. Extend `build-catalog.py` to walk the new directory, or add a per-source
   `build-catalog-<source>.py` if the logic diverges.

See `../docs/sources/zenodo.md` for the zenodo-specific runbook.
