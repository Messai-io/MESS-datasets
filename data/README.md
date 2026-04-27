# data/

One subdirectory per dataset source or topic. Each subdirectory
must contain a `DATASHEET.md` before any data files land, covering:

- **Source** — upstream URL, DOI, or citation.
- **License** — upstream license and attribution text.
- **Schema** — which `schemas/*.schema.json` this dataset conforms to.
- **Slug join keys** — which MESS-Parameters / MESS-Materials slugs
  (if any) the dataset references.
- **Known limitations** — units, coverage gaps, missing values.
- **Provenance** — script used to ingest, date, upstream version/tag.

Large intermediate caches should go under `data/.cache/` (gitignored).
