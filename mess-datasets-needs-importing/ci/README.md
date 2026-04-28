# ci/

GitHub Actions CI for MESS-datasets lives in `.github/workflows/ci.yml`. Three
jobs run on every push to `dev`/`main` and every PR:

## Jobs

### `validate-schemas`

Walks every catalog, manifest, and Zenodo metadata snapshot and validates
against the schemas under `../schemas/`:

- `dataset-catalog.schema.json` ← `data/catalog.json` + `data/*/catalog.json`
- `dataset-manifest.schema.json` ← `data/*/*/manifest.json`
- `zenodo-record.schema.json` ← `data/zenodo/*/metadata.json`

Fails the PR on any validation error.

### `validate-references`

Runs `scripts/validate-references.py`. For every slug listed in
`data/classifications.yaml`:

- `related_slugs.parameters[*]` must resolve in MESS-Parameters.
- `related_slugs.materials[*]` must resolve in MESS-Materials.

Slug sources are fetched from the `main` branch of the respective repos and
cached under `.slug-cache/` for subsequent runs.

Fails the PR on any unknown slug. Catches typos and drift when upstream slug
lists change.

### `build-catalog-drift`

Rebuilds all three catalogs and compares to the committed state (ignoring
`generated_at` / `last_synced` timestamps). Fails the PR if
`classifications.yaml` has drifted from the committed catalogs — reminds
contributors to run `python scripts/build-catalog.py` after editing
classifications.

## `.slug-cache/`

Populated by `scripts/_slug_sources.py` when running in CI (no local
MESS-Parameters / MESS-Materials clone available). Gitignored. Invalidated
whenever `_slug_sources.py` changes.

## Running CI checks locally

```bash
source .venv/bin/activate
python scripts/build-catalog.py
python scripts/validate-references.py
python -c "
import json
from jsonschema import validate
from pathlib import Path
s = json.loads(Path('schemas/dataset-catalog.schema.json').read_text())
for p in [*Path('data').glob('*/catalog.json'), Path('data/catalog.json')]:
    validate(json.loads(p.read_text()), s)
print('OK')
"
```
