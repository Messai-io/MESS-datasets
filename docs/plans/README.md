# MESS-datasets — Strategy & Roadmap

_Authored 2026-04-20. Canonical companion to the repo's top-level
`README.md`. Supersedes any references to per-source sidecar repos
(e.g. "MESS-Zenodo", "MESS-Figshare") in prior planning artifacts —
see §1._

## 1. Why this repo is shaped this way

Other producer sidecars in the Messai-io org are named by **content
type**, not by source:

- `MESS-Parameters` — the MES parameter ontology.
- `MESS-Materials` — DFT-computed material properties.
- `MESS-Metagenomics` — organism / community data.

Naming a sidecar after a source (e.g. "MESS-Zenodo", "MESS-Figshare")
breaks that convention and creates real problems:

1. **Zenodo and Figshare cover the same kind of thing** — standalone
   research datasets with DOIs, CC-licensing, and file bundles. The
   same MES study often deposits on one or the other; sometimes
   cross-deposits. Splitting by source would fragment a single
   logical resource (the "research dataset corpus") across two repos
   that share 80% of their schema and 100% of their downstream use.
2. **More sources are coming.** Dryad, OSF, Mendeley Data, university
   repositories, supplementary-data hosters. Creating one sidecar
   repo per source is cumulative overhead with no architectural
   benefit.
3. **Downstream consumers don't care about source.** A researcher
   asking "what datasets exist for carbon cloth anodes in MFCs?"
   wants a unified answer, not per-source silos.

So this repo covers **standalone research datasets** as a content
type, regardless of which open repository hosts them. Every record
carries its source as a first-class field (`source: zenodo`,
`source: figshare`, …), and downstream queries can filter or not.

**Patents are a different content type** — IP documents, not datasets,
with different licensing, metadata structure, and usage patterns.
They live in a separate `MESS-patents` repo. Cross-linking between
datasets and patents is deferred until both are populated enough to
make a join meaningful.

## 2. Scope — what belongs here vs. elsewhere

**In scope for MESS-datasets:**
- Raw electrochemical data (CV, EIS, polarization, LSV traces)
  deposited with research papers.
- Time-series operational data from reactors and pilot systems.
- Microbial community / amplicon-sequencing data tied to MES
  experiments (until MESS-Metagenomics is promoted to consume it
  directly).
- Simulation inputs and outputs (COMSOL `.mph`, OpenFOAM cases,
  custom solver data) — though MESS-Simulations is the ultimate
  consumer.
- Benchmark datasets (labeled data for ML training, e.g. paired
  electrode-performance with operating conditions).
- Re-packaged third-party curated datasets (with attribution and
  upstream license preserved).

**Out of scope, belongs elsewhere:**
- The parameter ontology and per-parameter literature extractions →
  `MESS-Parameters`.
- DFT-computed material properties → `MESS-Materials`.
- ML models, training pipelines, and learned weights →
  `MESS-Learning`.
- Organism-level reference data and community-level analyses →
  `MESS-Metagenomics` (once promoted to a declared submodule).
- Patents → `MESS-patents`.
- Paper text bodies → `MESS-Parameters/papers/` (local corpus).
- Curated methods and protocols → `MESS-Methods`.

## 3. Cross-repo relationships

```
MESS-Parameters   ◄──slug refs──►  MESS-datasets  ◄──slug refs──►  MESS-Materials
(ontology + lit                     (datasets, time-                (DFT properties)
 extractions)                        series, community,
                                     benchmarks)
                                          │
                                          │  DOI refs
                                          ▼
                                   MESS-patents (separate repo;
                                   cross-linking deferred)
```

**Directions of dependency:**
- MESS-datasets consumes MESS-Parameters' slug vocabulary at build
  time (via its pinned submodule) to produce the slug crosswalks in
  each dataset record.
- MESS-datasets does **not** consume MESS-Materials — the crosswalk
  key is the MESS-Parameters slug, and materials-in-MP information
  stays in MESS-Materials.
- Consumers (messai-ai, notebooks, MESS-Learning, MESS-Hypotheses)
  perform multi-repo joins at the edge, never inside a producer.

The sidecar-producer pattern, invariants, and sidecar-topology
diagram are the same as the ones established for MESS-Materials —
see `Messai-io/MESS-Materials:docs/plans/v0.1-mp-ingest.md` Part 2
and the wider strategy doc in
`messai-ai:docs/plans/multi-source-ingest-strategy.md`.

## 4. Release roadmap

| Tag | Scope | Status |
|---|---|---|
| `v0.0` | Repo scaffolding, README, schemas placeholder | ✅ done |
| `v0.1.0-pilot` | Zenodo ingest — ~100 records, prove the pipeline end-to-end | planned, see `v0.1-zenodo-ingest.md` |
| `v0.1.0` | Zenodo — scale to a solid coverage tier (~500–1000 records) | next after pilot |
| `v0.2.0` | Add Figshare as a second source behind the same unified schema | after v0.1.0 |
| `v0.3.0` | Dataset-level crosswalks: link each dataset to paper DOIs in MESS-Parameters and material slugs in MESS-Materials (not just parameter slugs) | after v0.2.0 |
| `v0.4.0+` | Add Dryad, OSF, Mendeley Data, etc. under the same schema. Each new source is a schema-invariant addition, not a new repo. | TBD |

Explicitly **not** in this roadmap:
- Patent ingest — lives in `MESS-patents`. Its v0.1 is a separate
  plan in that repo.
- Dataset-to-patent cross-linking — deferred until both repos have
  meaningful populations. Both will reference paper DOIs, so the
  eventual join is straightforward; no cross-linking infrastructure
  needs to be built preemptively.

## 5. Entity linking — the core technical approach

Each ingested dataset record must emit a **crosswalk object** mapping
it to zero-or-more MESS-Parameters slugs. This is what makes the
dataset usable for MES researchers:

```json
{
  "mess_entities": {
    "parameter_slugs": ["power_density", "coulombic_efficiency"],
    "material_slugs": ["carbon_cloth", "platinum_cathode"],
    "system_type": "MFC",
    "cited_dois": ["10.1016/j.bioelechem.2023.xxxx"],
    "confidence_tier": "medium"
  }
}
```

**Approach:** rule-based dictionary matching first (the MESS-Parameters
slug vocabulary, 687 slugs + synonyms), LLM-assisted for ambiguous
cases. The goal for v0.1 is a modest-precision pass; recall can grow
in v0.2+ once we have human-in-the-loop corrections to learn from.

**Reuse:** prefer to route through MESS-Parameters' existing
Nougat + Groq extraction pipeline rather than standing up a second
NLP pipeline in this repo. That keeps all extraction-quality caveats
(and their coefficient-of-variation track record) in one place. Open
decision — see §5 of
`messai-ai:docs/plans/multi-source-ingest-strategy.md`.

**Confidence tier semantics** (same conventions as MESS-Materials):
- `high` — exact slug name appears in title/description; no
  ambiguity.
- `medium` — synonym match or LLM inference with corroborating
  context.
- `low` — single weak signal; surface in UI only with an explicit
  "low confidence" badge.

## 6. Unified Dataset schema (v0.1 sketch)

Full schema goes in `schemas/dataset.schema.json` as part of the v0.1
execution plan. Sketch of the required shape here so downstream
consumers can plan against it:

```yaml
id: "zenodo:1234567"                 # canonical: <source>:<record_id>
doi: "10.5281/zenodo.1234567"        # when available
source: "zenodo" | "figshare" | ...
source_record_id: "1234567"
source_url: "https://zenodo.org/records/1234567"

title: "..."
description: "..."
creators: [{ name, orcid? }, ...]
published_date: "2024-06-15"
version: "1.2"
keywords: ["microbial fuel cell", "MXene", ...]

license:
  spdx_id: "CC-BY-4.0"
  upstream_label: "Creative Commons Attribution 4.0 International"
  attribution_text: "Cite as: Smith et al. (2024)..."

files:
  - filename, format, size_bytes, checksum, download_url

mess_entities:     # the crosswalk; §5
  parameter_slugs, material_slugs, system_type, cited_dois,
  confidence_tier, extraction_notes

fetched_at: "2026-04-20T..."
source_snapshot_date: "2026-04-20"
mess_parameters_tag: "v0.2.0"         # pinned upstream version
confidence_notes: "..."
```

Same design principles as MESS-Materials' `mp-material.schema.json`:
additive future versions, explicit provenance, explicit license,
every consumer surface that shows the data must preserve attribution.

## 7. Operational rules

- **Per-dataset DATASHEET.md** in every `data/<source-or-topic>/`
  folder. Required before any data files land. Covers source,
  license, schema, slug join keys, known limitations, ingestion
  provenance.
- **Raw responses cached** under `data/<source>/raw/` where size
  permits; committed for reproducibility like MESS-Materials'
  `mp-cache/`. Very large blobs go under `data/.cache/` (gitignored)
  with a content-hash manifest checked in.
- **CI invariants** (enforced per PR): schema validation on every
  record, every record has a non-null license field, every
  `parameter_slug` and `material_slug` exists in the pinned
  MESS-Parameters / MESS-Materials at build time.
- **Tag-pinned upstreams.** MESS-datasets submodule-pins
  MESS-Parameters (slug vocabulary source) and, at v0.3+, optionally
  MESS-Materials (material-slug validation). Just like MESS-Materials
  pins MESS-Parameters.

## 8. Not in this strategy (yet)

- **Raw bulk downloads of multi-GB Zenodo datasets.** v0.1 stores
  metadata + crosswalks + small files only. Bulk content storage is
  a deployment decision deferred until we know which datasets are
  heavily used downstream — probably a Git LFS or separate CDN layer.
- **Cross-source deduplication.** Some authors cross-deposit the
  same dataset on Zenodo and Figshare. Dedup on DOI where present;
  flag without merging when DOIs differ. Real deduplication is v0.3.
- **Custom Zenodo / Figshare communities for MES.** Could coordinate
  with maintainers to request an official MES community tag on
  those platforms — that would dramatically improve discoverability
  and recall. Track as an open opportunity, not a blocker.

## 9. Cross-references

- `README.md` — repo top-level, scope summary.
- `docs/plans/v0.1-zenodo-ingest.md` — execution plan for the first
  tagged release.
- `Messai-io/MESS-Parameters:docs/consumer-contract.md` — upstream
  vocabulary contract that MESS-datasets crosswalks consume.
- `Messai-io/MESS-Materials:docs/plans/v0.1-mp-ingest.md` — sibling
  sidecar's producer plan, the template this repo mirrors.
- `messai-ai:docs/plans/multi-source-ingest-strategy.md` — the wider
  architectural strategy. **Note:** that doc was authored before the
  content-type renaming decision documented in §1 here; any
  references to "MESS-Zenodo" / "MESS-Figshare" in it should be read
  as "MESS-datasets (Zenodo-sourced records)" / "MESS-datasets
  (Figshare-sourced records)". That doc will be updated to match.
