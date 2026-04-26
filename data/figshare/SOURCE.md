# Figshare (data/figshare/)

Datasets ingested from [Figshare](https://figshare.com). Most Figshare records
surfaced for this repo are **supplementary files attached to published papers**
(typical layout: one or more .docx / .pdf / .xlsx with tables, source data, data
sheets), so each record carries a `paper_doi` pointer to the upstream paper —
that's the primary join key to a papers database.

## Layout

```
data/figshare/
  SOURCE.md                this file
  seed.yaml                article IDs + search provenance
  catalog.json             aggregated index for this source
  <article-id>/
    metadata.json          /v2/articles/<id> snapshot
    manifest.json          file list + commit status + paper_doi
    DATASHEET.md           human record card
    files/                 committed small files
    .source/               gitignored — full raw downloads
```

## Licensing

Most Figshare records in our scope are CC-BY-4.0 (matching the papers they
supplement). Every record's `DATASHEET.md` states the upstream license.
Downstream consumers must honor upstream terms.

## API notes

- Endpoint: `https://api.figshare.com/v2/articles/<id>`
- Anonymous, no auth required for public records.
- File shape:
  `files[].id, name, size, download_url, supplied_md5, computed_md5`.
- Paper DOI: `resource_doi` field at article level.
- Figshare's own supplementary DOI: `doi` (often `10.xxxx/....s00N`).

## Paper linkage

For each record, `manifest.json.paper_doi` is populated from the Figshare
`resource_doi`. Downstream tools can join datasets to papers via that DOI. See
`docs/architecture.md` for the broader wiring.
