# Catalog consumer contract

Every ingest source writes an aggregated `data/<source>/catalog.json`
conforming to `schemas/dataset-catalog.schema.json`. Downstream
consumers (messai-ai, MESS-Learning, notebooks) read these catalogs
to discover datasets without crawling the filesystem.

## Shape

```json
{
  "generated_at": "2026-04-20T...",
  "records": [
    {
      "source": "zenodo",
      "id": "7050972",
      "doi": "10.5281/zenodo.7050972",
      "title": "Bayesian Estimation on Microbial Electrochemical Time Profiles ...",
      "publication_date": "2022-09-09",
      "license": "CC-BY-4.0",
      "creators": ["Miran, Waheed", "Huang, Nanqi", ...],
      "keywords": ["bioelectrochemical", "Bayesian", ...],
      "files": {
        "count": 9,
        "total_bytes": 60235123,
        "committed_count": 5
      },
      "mes_relevance": null,
      "mes_domains": [],
      "data_kinds": [],
      "related_slugs": {
        "parameters": [],
        "materials": []
      },
      "last_synced": "2026-04-20T..."
    }
  ]
}
```

## Field semantics

- **`source`** — namespace for `id`. `zenodo` today; more as we grow.
- **`id`** — string. For Zenodo: the record ID as a decimal string.
- **`doi`** — canonical DOI when one exists. Null otherwise.
- **`mes_relevance`** — `core | adjacent | tangential | null`. `null`
  means not yet reviewed. Assigned in a follow-up classification pass.
- **`mes_domains`** — zero-or-more of `mfc, mec, mes_general, biofilm,
  electrocatalysis, oect, bioremediation, corrosion, energy_storage,
  sensor, co2_capture, wastewater, metagenomics, other`. A record can
  sit in multiple domains.
- **`data_kinds`** — zero-or-more of `experimental, time_series,
  spectroscopy, image, genomic, simulation, benchmark, code, mixed,
  other`.
- **`related_slugs.parameters`** — MESS-Parameters slugs this dataset
  touches. Join key for cross-repo queries.
- **`related_slugs.materials`** — MESS-Materials slugs this dataset
  touches. Same slug join as MESS-Materials uses against MESS-Parameters.
- **`last_synced`** — UTC timestamp of the last fetcher run for this
  record.

## Stability

- Field names and enums are stable within a major version of this repo.
- Adding enum values is a minor change; removing/renaming is breaking.
- New optional fields may appear at any time; consumers should ignore
  unknown fields.

## Relation to per-record artifacts

`catalog.json` is a *derived, summarized* view. The full picture lives
per record:

- `data/<source>/<id>/metadata.json` — upstream API snapshot (source-specific)
- `data/<source>/<id>/manifest.json` — file list + checksums (schemas/dataset-manifest.schema.json)
- `data/<source>/<id>/DATASHEET.md` — human-readable record card

Consumers that need file-level detail should follow the catalog entry's
`(source, id)` pair to those artifacts.
