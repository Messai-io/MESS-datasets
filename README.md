# MESS-datasets

<!-- MIRROR_DISCLOSURE_START -->

> **This repository is a downstream mirror.** Source of truth lives in the
> private `messai-ai` monorepo; this mirror is updated automatically on each
> release. Issues and Discussions are welcome here. PRs against this mirror will
> be redirected — see [CONTRIBUTING.md](./CONTRIBUTING.md).
>
> History was reset on **YYYY-MM-DD** as part of monorepo consolidation.
> Versions tagged before that date (e.g. `v0.2.0`) remain accessible as
> historical refs and retain their Zenodo DOIs.

<!-- MIRROR_DISCLOSURE_END -->

Curated datasets ingested from various sources for Microbial Electrochemical
Systems (MES) research. A **sidecar to
[Messai-io/MESS-Parameters](https://github.com/Messai-io/MESS-Parameters)** and
[Messai-io/MESS-Materials](https://github.com/Messai-io/MESS-Materials), keyed
(where applicable) by the same parameter and material slugs.

## What this repo is

A staging and publication ground for experimental, observational, and
third-party datasets relevant to MES research:

- Literature-extracted experimental results (performance curves, polarization
  data, coulombic efficiency, etc.).
- Time-series operational data from reactors, pilot systems, and lab
  experiments.
- Microbial community / metagenomic datasets relevant to MES.
- Open third-party datasets re-packaged in a consistent schema (with attribution
  preserved).
- Benchmark datasets for ML training and evaluation downstream.

Each dataset is stored under `data/<source-or-topic>/` with its own
`DATASHEET.md` describing provenance, license, schema, and known limitations.

## What this repo is not

- **Not** a replacement for MESS-Parameters. The parameter ontology and
  canonical literature extractions stay there.
- **Not** a replacement for MESS-Materials. DFT-computed material properties
  stay there.
- **Not** an ML training repo. Models and training pipelines live downstream
  (e.g. MESS-Learning). This repo publishes the raw and curated datasets those
  pipelines consume.

## How it connects to the ecosystem

```
MESS-Parameters   ──slug join──►  MESS-datasets  ◄──slug join──  MESS-Materials
(ontology, lit           (experimental, time-series,         (DFT properties)
 extractions)             community, benchmark data)
```

Consumers (messai-ai, notebooks, downstream models) join across repos by slug
where the dataset carries parameter or material identifiers.

## Status

**v0.0 — scaffolding.** No data yet. Ingestion pipelines and the first dataset
drops will land with `v0.1.0-pilot`.

## Licensing

- This repo's code and curated data: see `LICENSE` (CC-BY-4.0, matching
  MESS-Parameters).
- **Upstream dataset licenses vary.** Every dataset must ship a `DATASHEET.md`
  stating its upstream license and attribution requirements. Downstream
  consumers are responsible for honoring upstream terms — this repo does not
  relicense third-party data.

## Layout

```
data/      curated datasets, one subdirectory per source/topic,
           each with its own DATASHEET.md
schemas/   JSON Schema definitions for published dataset artifacts
scripts/   ingestion, cleaning, and validation pipelines
docs/      methodology, dataset catalog, consumer contract
ci/        schema validation + dataset integrity checks
```

## Getting involved

This repo is part of the [Messai-io](https://github.com/Messai-io) open-source
ecosystem for microbial electrochemical systems. Issues and PRs welcome once
`v0.1.0-pilot` lands.
