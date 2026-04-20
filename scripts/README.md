# scripts/

Ingestion, cleaning, and validation pipelines. One script (or module)
per source where practical. Each script should:

- Be reproducible — pin upstream versions / snapshot dates.
- Emit into `data/<source>/` using the matching schema in `schemas/`.
- Record provenance in the dataset's `DATASHEET.md`.
