# Architecture — MESS intelligence graph

Status: living draft. This document captures the design of how MESS-datasets
connects to MESS-Parameters, MESS-Materials, and the downstream consumers
(messai-ai, MESS-Learning). It is intentionally written as a **contract +
extension surface**, not a finished schema — the point is to make scaling and
accuracy improvements additive, not breaking.

---

## 1. Context

The open-source MESS stack is a collection of repos:

- **MESS-Parameters** — parameter ontology + literature extractions (`papers/`,
  `parameters/`, `parameter-definitions-rich.json`).
- **MESS-Materials** — DFT-computed material properties sidecar, keyed by
  MESS-Parameters material slugs.
- **MESS-datasets** (this repo) — third-party datasets ingested from Zenodo,
  Figshare, and other sources.
- **MESS-Learning** (future) — models and training pipelines that consume the
  above.
- **messai-ai** (consumer) — pins all four via submodules under `open-source/`.

Each repo has good internal structure. What's historically been missing is a
**deliberate, versioned contract** for how they join. Without one, every
consumer invents its own cross-repo lookup and the graph rots.

This document defines the contract.

## 2. Core principles

1. **Additive, not breaking.** New fields, new enum values, new sources, and new
   join kinds are expected. Removals and renames are rare and follow a
   deprecation window (see §9). Consumers MUST ignore unknown fields.
2. **Provenance over cleverness.** Every non-trivial assertion (a slug join, a
   domain tag, a relevance tier) carries its origin: who/what said so, when, and
   with what confidence. Accuracy improvements come from sharpening provenance,
   not from replacing prior judgments silently.
3. **Null ≠ no.** A null classification means _unreviewed_, not _does not
   apply_. Explicit "reviewed, confirmed empty" is a distinct signal. This
   distinction enables iterative, non-clobbering classification passes.
4. **One canonical place per fact.** A parameter slug is defined in
   MESS-Parameters, full stop. A material's DFT band gap is in MESS-Materials. A
   dataset's file manifest is in MESS-datasets. No duplication — only
   references.
5. **Reproducibility first.** Every derived artifact (catalogs, rich JSONs,
   model outputs) must be rebuildable from source + code + pinned inputs. Schema
   validation is CI-gated.

## 3. The four join keys

Every cross-repo connection uses exactly one of:

| Key                   | Shape                                                                 | Owner                                                | Examples                                                          |
| --------------------- | --------------------------------------------------------------------- | ---------------------------------------------------- | ----------------------------------------------------------------- |
| **parameter slug**    | lower-snake                                                           | MESS-Parameters                                      | `carbon_cloth`, `coulombic_efficiency`, `anion_exchange_membrane` |
| **material slug**     | subset of parameter slugs where category=MATERIALS + data_type=OBJECT | MESS-Parameters (names) / MESS-Materials (DFT props) | `platinum_cathode`, `nafion_membrane`                             |
| **paper DOI**         | `10.xxxx/...`                                                         | papers-index.json (MESS-Parameters)                  | `10.3389/fenrg.2020.00174`                                        |
| **dataset reference** | `(source, id)` tuple                                                  | MESS-datasets                                        | `(zenodo, 7050972)`, `(figshare, 12725867)`                       |

Nothing else crosses repo boundaries. No free-text names, no repo-internal
integer IDs leaking outward, no URL-as-identifier. If you find yourself wanting
a fifth join key, add it here first with a proposal; don't ad-hoc it in a
consumer.

## 4. Per-repo responsibilities

### MESS-Parameters (ontology owner)

- Owns parameter slugs (canonical list at `parameters/` + rich.json).
- Owns `papers/papers-index.json` (**proposed v0.3** — see §10) keyed by paper
  DOI, with extraction refs and dataset back-refs.
- Owns literature extractions (which paper contributed which parameter value).

### MESS-Materials (DFT sidecar)

- Keyed by material slugs from MESS-Parameters.
- Publishes `mp-materials-rich.json` with DFT-computed properties.
- Never defines new slugs.

### MESS-datasets (this repo)

- Ingests third-party datasets, one record per upstream ID.
- Publishes three catalogs: per-source (`data/<source>/catalog.json`) and
  unified root (`data/catalog.json`).
- Every catalog record carries `paper_doi` (when known),
  `related_slugs.parameters`, `related_slugs.materials`.
- Does NOT define new slugs. Does NOT own paper metadata beyond the DOI pointer.

### MESS-Learning (future)

- Training runs keyed by `(source, id)` for inputs.
- Model cards name the parameter slugs they predict.
- Never defines new slugs.

### messai-ai (consumer)

- Pins all upstream repos via submodules.
- Exposes a **federated query module**:
  `getAllForSlug(slug) → { parameter, material?, papers[], datasets[] }`. Every
  UI/API call goes through this, not raw file reads.
- CI-gates orphan references (slug referenced → must exist in pinned ontology).

## 5. Data model — the graph

```
                     ┌─────────────────────────┐
                     │  MESS-Parameters        │
                     │  ─────────────          │
                     │  parameter slug  ──────────────►  (authoritative list)
                     │  material slug   ─────────┐
                     │  papers-index    ─────┐   │
                     └─────────────────────┐ │   │
                                           │ │   │
             ┌──────────────┐   paper_doi  │ │   │  material_slug
             │ MESS-datasets│◄─────────────┘ │   │◄─────────────┐
             │              │  related_slugs │   │              │
             │ catalog.json │  .parameters   │   │   ┌──────────┴─────────┐
             │  records     ├────────────────┘   │   │  MESS-Materials    │
             │              │                    │   │  mp-materials-rich │
             │              │  related_slugs.materials │  (DFT sidecar)    │
             │              ├────────────────────┘   └────────────────────┘
             └──────┬───────┘
                    │  (source, id)
                    ▼
           ┌──────────────────┐
           │  MESS-Learning   │
           │  (training runs) │
           └──────────────────┘
```

Every edge is typed and named by §3 keys. Every node is auto-rebuildable from
source.

## 6. Flexibility hooks

This is where the "don't repaint the whole house every time" design lives. Each
hook is the answer to a specific class of future need.

### 6.1 Adding a new dataset source

Drop in `scripts/fetch-<source>.py` + `data/<source>/{SOURCE.md, seed.yaml}`,
add the source to the three `schemas/*.schema.json` source enums, teach
`scripts/build-catalog.py` one more builder. No consumer change.

### 6.2 Adding a new classification dimension

Every catalog record today carries
`mes_relevance, mes_domains, data_kinds, related_slugs`. New dimension (e.g.
`reactor_geometry`, `substrate_type`, `ph_range`, `scale_tier`) = add an
optional field to `dataset-catalog.schema.json`. Because consumers ignore
unknowns, the field is invisible until someone reads it. Because
`build-catalog.py` preserves prior classifications by key, manual edits survive
rebuilds.

### 6.3 Adding a new join key

If a new cross-repo identifier is proposed (e.g. microbial taxon ID, ChEBI
compound), it is added here (§3) with:

- a documented format
- a canonical owner repo
- migration path for existing records

Until formalized, it lives in record-local metadata only, not as a catalog-level
field.

### 6.4 Adding provenance / confidence

The manifest and catalog schemas already have room for `skipped_reason` and can
gain an optional `provenance` block (proposed shape below). No field is "just
the value" — everything can carry its source.

```json
"related_slugs": {
  "parameters": [
    {
      "slug": "coulombic_efficiency",
      "confidence": 0.92,
      "source": "llm_suggest_v3",
      "reviewed_by": "human:fronssam",
      "reviewed_at": "2026-04-20T..."
    }
  ]
}
```

For the current classification pass we use the simpler string-array form
(`["coulombic_efficiency"]`); the catalog schema is forward- compatible with
either (via an oneOf we add when we need it).

### 6.5 Adding accuracy checks

Every schema has a CI gate today (jsonschema validate). Planned additions:

- **Referential integrity**: every `related_slugs.parameters[i]` must exist in
  the pinned MESS-Parameters slug list.
- **DOI resolvability**: optional nightly check that `paper_doi` and `doi`
  resolve (non-blocking warning, not a PR fail).
- **File checksum re-verification**: weekly job re-computes MD5s of committed
  files against upstream Zenodo/Figshare to detect upstream edits.
- **Catalog drift**: the unified `data/catalog.json` must equal the
  concatenation of the per-source catalogs by `(source, id)`. CI fails on
  mismatch.

### 6.6 Versioning upstream records

Zenodo and Figshare both version records. Current fetcher captures the snapshot
at fetch time. When a record updates upstream, re-running with `--refresh <id>`
overwrites. If we later need record version history, the cleanest addition is
`data/<source>/<id>/versions/<v>/` directories and a pointer to "current" — the
catalog stays flat.

## 7. Accuracy model

Three orthogonal concerns:

1. **Extraction accuracy** — is the parameter value pulled from a paper correct?
   Lives in MESS-Parameters (extraction provenance).
2. **Join accuracy** — is this dataset actually about this slug? Lives in
   MESS-datasets (`related_slugs` provenance, §6.4).
3. **Computational accuracy** — is this DFT result trustworthy? Lives in
   MESS-Materials (functional, tier, Pourbaix confidence).

Each concern is owned by the repo that produces it, and each carries its own
provenance — never trust values without their source. When two repos disagree
(e.g. a dataset classification conflicts with a parameter definition), consumers
surface the conflict; they do NOT silently pick a winner.

## 8. Scaling model

Designed for ~10k datasets, ~1k materials, ~10k papers, ~1k parameter slugs
without any architectural change:

- **Catalog files** stay JSON and flat. At 10k records, `data/catalog.json` is
  still well under 50MB and parseable in <1s. We revisit (split, or move to
  SQLite/duckdb) only if real usage hits a ceiling.
- **Per-record dirs** scale linearly — filesystem handles 100k+ dirs in one
  parent easily on modern FS. Flat-by-ID avoids any repartition need.
- **Gitignored `.source/`** is the escape hatch for large raw data. Once we
  ingest hundreds of GB, the on-demand fetcher (`scripts/ fetch-on-demand.py`,
  see §10) replaces local downloads with per- query pulls.
- **Submodule pins** keep every consumer reproducible. Upgrading pinned SHAs is
  a visible, reviewable event.

The design deliberately uses dumb-but-correct formats (JSON, flat dirs, git)
until a real scaling pain forces a move. Premature databases are harder to
evolve than file trees.

## 9. Schema evolution policy

- **Additive changes** (new optional field, new enum value): any time. Minor
  catalog regen. Consumers unaffected.
- **Deprecations**: mark field `deprecated: true` in schema description, keep
  emitting for two minor versions, then drop with a MAJOR catalog version bump.
- **Breaking changes**: bump `generated_at` format → add a `schema_version`
  top-level field to each catalog and bump it. Consumers pin a range.
- **Source enum additions** are always safe (adding a source never breaks
  existing entries).
- **Join-key additions** require a doc update here (§3) before schema lands.

The repo-level version tag (e.g. `v0.1.0-pilot`) gates compat; the schema files
themselves carry `$id` so consumers can validate against a pinned copy.

## 10. Roadmap (short)

1. **Classification pass** — fill
   `mes_relevance, mes_domains, data_kinds, related_slugs` for the current 36
   catalog records. LLM-assisted + human review. Non-destructive rebuild already
   wired.
2. **Improve paper_doi extraction in Zenodo** — Dryad/Nature mirror records put
   the paper DOI in `metadata.doi` directly; detect and promote.
3. **Promote `papers/` in MESS-Parameters to `papers-index.json`** — keyed by
   DOI, with `extractions: [slug]` and `datasets: [(source, id)]` back-refs.
   Back-fill from the 12 existing `paper_doi` records here.
4. **On-demand fetcher** — `scripts/fetch-on-demand.py` that reads manifests,
   pulls gitignored `.source/` files into a local cache on first use. Enables
   moving large records out of the committed tree once the scouting phase
   completes.
5. **Referential CI** — GitHub Actions check that every
   `related_slugs.parameters` slug resolves in the pinned MESS-Parameters
   submodule.
6. **messai-ai federated query module** — `getAllForSlug(slug)` as the single
   cross-repo read path. Deprecate direct file reads in consumers.

## 11. What this document is not

- Not a freeze. Every section is open to improvement.
- Not exhaustive. Minor decisions (file naming, tooling choice) stay in their
  owning repo.
- Not a DB schema. The relational structure is implied by the join keys, but we
  deliberately stay in files until the cost forces us to move.

When a design decision is unclear, the default is: **follow §2 core
principles**, prefer the lower-ceremony option, and write it down here so the
next decision can build on it.
