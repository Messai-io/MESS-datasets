# 20240909_BIOCTANE_INRAE_PUB1.3_V01

- **Source**: Recherche Data Gouv (INRAE)
- **Record ID**: `D1FHK9`
- **DOI**: [10.57745/D1FHK9](https://doi.org/10.57745/D1FHK9)
- **Publication date**: 2024-11-23
- **License (upstream)**: etalab-2.0 (Open License v2.0)
- **Creators**: Eric Trably, Nicolas Bernet, Jose Antonio Magdalena Cadelo,
  Maria Fernanda Perez Bernal
- **Project**: BIOCTANE (EU H2020)
- **Fetched**: 2026-05-16T03:19:13+00:00
- **Raw 16S sequences**: NCBI bioproject PRJNA1152534

## Abstract

Dataset containing experimental data supporting research on _"Microbial
electrolysis cells as a tool to polish short chain-rich dark fermentation
effluents for propionate production"_.

## Logical datasets (18 files total, 2.8 MB)

1. **DF_continuous_pH7** — Dark fermentation continuous reactor, pH 7, food
   waste substrate, 3 OLR stages (30/45/60 g VS/L·d). Biogas %, VFAs (g/L, g
   COD/L), tCOD, sCOD, COD removal efficiency.
2. **MECs*R1R2*…\_ORL60_pH7** — Two MECs fed with DF effluent at OLR 60. HPLC
   metabolites; H2 volumes (measured + theoretical from charge); coulombic
   efficiency (CE); cathodic efficiency (rCAT); global yield (rH2);
   chronoamperometry at +256 mV vs Ag/AgCl; cyclic voltammetry (−0.6 to +0.6 V
   at 1 mV/s).
3. **Enrichment** — Bioanode (BA1, BA2) enrichment, n-stat reactor, +256 mV vs
   Ag/AgCl, acetate substrate. Chronoamperometry + CV per enrichment cycle.
4. **OTUS_NStat_and_MECs_R1R2** — 16S rRNA OTU tables for the enrichment + MEC
   R1/R2 phases. Bulk phase + electrode surface separately.
5. **OTUs_Continuous_DF** — OTU tables from the DF stage, by OLR.

## Canonical parameter mapping

| BIOCTANE variable          | Canonical slug                         | Unit      |
| -------------------------- | -------------------------------------- | --------- |
| Coulombic Efficiency (CE)  | `coulombic_efficiency`                 | %         |
| Cathodic Efficiency (rCAT) | `cathodic_h2_recovery`                 | %         |
| Global Yield (rH2)         | `h2_yield`                             | mol/mol   |
| Chronoamperometry I        | `current_density`                      | A/m²      |
| Total VFAs                 | `volatile_fatty_acids`                 | mg/L      |
| Acetate                    | `acetic_acid_concentration`            | mg/L      |
| Butyrate                   | `butyrate_concentration`               | mg/L      |
| Propionate                 | `propionic_acid_concentration`         | mg/L      |
| OLR                        | `organic_loading_rate`                 | g COD/L/d |
| Biogas CH4 %               | `ch4_content_biogas`                   | %         |
| Cathode / anode V          | `cathode_potential`, `anode_potential` | V         |

See `MANIFEST.TXT` and `Readme_metadata.txt` (preserved at the record root) for
the upstream file-by-file descriptions.

## MES relevance

`core` — full MEC + microbial community + electrochemical kinetics pipeline.

- mes_domains: mec, mes_general, wastewater
- data_kinds: experimental, time_series, genomic

## Attribution

Cite the upstream record per its etalab-2.0 license. DOI is the canonical
citation anchor.
