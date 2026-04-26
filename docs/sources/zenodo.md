# Zenodo ingestion

## Pipeline

```
scripts/fetch-zenodo.py  →  data/zenodo/<id>/{metadata,manifest}.json + files
scripts/build-catalog.py →  data/zenodo/catalog.json
```

## First-time setup

```bash
cd /path/to/MESS-datasets
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # optional; fill in ZENODO_TOKEN if desired
```

## Running the fetcher

```bash
# Ingest everything listed in data/zenodo/seed.yaml
python scripts/fetch-zenodo.py

# Ingest a subset
python scripts/fetch-zenodo.py --ids 7050972,4944335

# Re-fetch metadata + files for a record (clears cached files)
python scripts/fetch-zenodo.py --refresh 7050972

# Metadata only, no file downloads
python scripts/fetch-zenodo.py --skip-download

# Preview what would be fetched
python scripts/fetch-zenodo.py --dry-run
```

The fetcher is idempotent — records already populated are skipped unless
`--refresh` is passed.

## Committed vs gitignored files

For each record, the fetcher decides per file:

- **Committed** (`data/zenodo/<id>/files/<key>`) — small, non-archive,
  human-readable source (CSVs ≤5MB, JSON, Python/R scripts, markdown, YAML,
  plain text).
- **Gitignored source copy** (`data/zenodo/<id>/.source/<key>`) — large files
  and archives. Still present on disk for local analysis; never pushed to
  GitHub.

The per-record `manifest.json` records which bucket each file landed in, with
MD5 checksums. Future on-demand fetching will read manifests to know what to
pull from upstream.

## Rate limits

Anonymous: 60 requests/minute, 2000/hour. We're well under that for current seed
sizes. The fetcher sleeps 1s between records as a courtesy.

## Rerunning

Safe to rerun. Existing `data/zenodo/<id>/` dirs are skipped unless `--refresh`
is passed. After adding new IDs to `seed.yaml`, just rerun; only the new records
are fetched.

After any successful run, rebuild the catalog:

```bash
python scripts/build-catalog.py
```

## Schema validation

```bash
python -m jsonschema -i data/zenodo/catalog.json schemas/dataset-catalog.schema.json
for f in data/zenodo/*/manifest.json; do
  python -m jsonschema -i "$f" schemas/dataset-manifest.schema.json
done
```
