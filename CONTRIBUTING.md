# Contributing to Mosaic

Mosaic is an early-stage local-first application. Reliability, data provenance, user control, and honest capability boundaries take priority over feature breadth.

## Set up the backend

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -e ".[dev]"
Copy-Item .env.example .env
```

## Run checks

```powershell
pytest
python -m compileall -q src tests
ruff check .
```

## Set up the frontend

```powershell
cd frontend
npm install
npm run typecheck
npm run build
```

Generate and commit `frontend/package-lock.json` before using `npm ci` for reproducible installation. Do not commit `node_modules/` or `dist/`.

## Change requirements

- Start from `docs/SPEC.md` and the relevant ADR.
- Add/update a test before or alongside implementation.
- Add a SQL migration for every schema change.
- Keep external model output untrusted and source-check every evidence reference server-side.
- Keep provider-specific export parsing behind importer adapters with versioned fixtures.
- Preserve backwards compatibility or document a migration path.

## Pull requests

Describe the user-visible behaviour, security/privacy implications, migrations, and tests run. Clearly identify checks that were not run. Do not claim full provider support without fixture-based tests against real, appropriately redacted exports.
