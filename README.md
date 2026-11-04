# Mosaic

**Cross-Model Intelligence & Adaptive Knowledge System** — local-first, provider-independent conversation intelligence.

Mosaic imports user-supplied conversation exports, normalises them into a provider-neutral structure, preserves source provenance, supports full-text search, prepares user-mediated analysis prompts, and stores reviewed knowledge as candidates until a user approves it. It also prepares context packets for manual handoffs between ordinary consumer chat interfaces.

> **Current maturity:** early implementation / first vertical slice. This is not a finished product. ChatGPT export JSON and manual text/Markdown imports, conversation search, source-linked candidate extraction, explicit knowledge review, server-issued, single-use analysis handoffs, context-packet-bound model-response intake, manual cross-model handoffs, and the initial React workspace are implemented. Claude and Gemini adapters, experiment execution, objective-management UI, and the browser companion are not yet implemented.

## Design principles

- Local-first: the API binds to loopback by default and stores data under `./data`.
- User-controlled: no provider login, cookies, session tokens, scraping, auto-submit, or unattended browser operation.
- Evidence-first: extracted knowledge remains a `candidate` and includes message-level evidence.
- Honest interpretation: Mosaic records observable conversation behaviour; it does not claim access to hidden chain-of-thought.
- Provider permissions: storage, indexing, semantic derivation, strategy analysis, and cross-provider transfer are separate explicit controls. Unreviewed provider policy status remains visible. Cross-provider handoffs require a user-recorded policy attestation for both providers.
- Reversible evolution: MVP does not update foundation-model weights or self-modify application code.

## Requirements

- Python 3.11+
- Windows, macOS, or Linux (Windows is the first documented target)
- Optional: Ollama on the same computer for local semantic analysis
- Optional frontend development: Node.js 20+

## Run the backend

PowerShell:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -e ".[dev]"
Copy-Item .env.example .env
mosaic
```

The local API is available at `http://127.0.0.1:8765`; interactive API documentation is at `/docs`.

Alternative without installing the console script:

```powershell
$env:PYTHONPATH = "src"
python -m uvicorn mosaic.main:app --host 127.0.0.1 --port 8765
```

The data directory is configurable with `MOSAIC_DATA_DIR`. **Never commit this directory**: it contains original user archives and the local database.

## Run the frontend

In a second PowerShell window:

```powershell
cd frontend
npm install
npm run dev
```

Open `http://127.0.0.1:5173`. The frontend talks only to the local API at `http://127.0.0.1:8765`.

> `package-lock.json` is not yet committed because the build environment used to prepare this slice had no npm registry network access. Until it is generated and committed, `npm install` resolves the exact top-level versions in `package.json` but does not provide a fully locked transitive dependency graph. Generate and commit the lockfile before treating frontend builds as reproducible releases.

## Run the test suite

```powershell
pytest
ruff check .
python -m compileall -q src tests
```

The backend test suite currently has 34 passing tests covering import parsing/security, API integration, policy-aware indexing, source-grounded extraction, candidate review, provider policy attestations, transfer gates, single-use handoff expiry/replay/spoofing protections, credential redaction, and loopback-only configuration. Frontend build/type-check is pending dependency installation in a network-enabled environment.

## Current import support

- ChatGPT `conversations.json` (common mapping and flat message shapes), including a ZIP containing that file.
- Plain-text and Markdown transcripts with `User:` / `Assistant:` style speaker labels.
- ZIP validation checks entry count, expanded size, per-entry size, compression ratio, path traversal, duplicate paths, symlinks, and encrypted entries. Entries are read in place; archives are never extracted to disk.
- Unknown or unsupported archive structures fail with an explicit error instead of being silently treated as valid.

Claude and Gemini export adapters are intentionally not claimed as complete until fixture-based tests exist.

## Import permissions

The import endpoint requires explicit confirmation to store the data locally. Local search indexing is optional and separately selected; disabling it stores the source and parsed conversations but does not add them to full-text search. Semantic analysis, observable strategy analysis, and cross-provider transfer are separate flags. The UI/API stores these as user preferences; it does **not** claim that a provider's terms have been legally reviewed. Provider policy status stays `unreviewed` until you record a policy review in Settings. Cross-provider transfers require the source's explicit transfer permission and an `allowed_with_conditions` review record for source and destination providers. Each analysis packet receives a 24-hour, single-use handoff ID. The ID is bound to the source conversation and destination; Mosaic rechecks policy and permission at ingestion and derives provider attribution from its server-side record. Provider attribution is user-attested, not cryptographically verified against the destination service. Objective response intake similarly derives its provider label from the server-side context packet and rechecks source/destination policy before storage. Selecting `manual` requires the user to attest that the analysis was authored manually and not generated by another AI service. Mosaic records your policy attestation; it does not interpret terms or give legal advice.

To update permissions through the local API, use `PUT /api/v1/settings/providers/{provider}/permissions` with JSON such as:

```json
{
  "allow_store": true,
  "allow_index": true,
  "allow_derive": true,
  "allow_strategy_analysis": false,
  "allow_cross_provider_transfer": false
}
```

## Optional local inference

Install and run Ollama locally, pull a model suitable for structured extraction, then configure:

```text
MOSAIC_OLLAMA_BASE_URL=http://127.0.0.1:11434
MOSAIC_OLLAMA_MODEL=<local-model-name>
```

Mosaic rejects non-loopback Ollama endpoints in this release. The model response is validated against Pydantic schemas and all resulting knowledge remains a candidate. If local inference is unavailable, the manual prompt / paste-back workflow remains available.

## API overview

- `GET /api/v1/health`
- `POST /api/v1/imports`
- `GET /api/v1/imports`
- `GET /api/v1/conversations`
- `GET /api/v1/conversations/{id}`
- `GET /api/v1/conversations/{id}/report`
- `GET /api/v1/search?q=...`
- `POST /api/v1/conversations/{id}/analysis-packet`
- `POST /api/v1/conversations/{id}/analysis`
- The `/analysis-packet` response includes a server-issued 24-hour, single-use `handoff_id`; `/analysis` requires that ID and derives provider attribution server-side. Manual submissions require an explicit user-authorship attestation; external responses require local-storage consent.
- `POST /api/v1/conversations/{id}/analyse-local`
- `GET /api/v1/knowledge`
- `GET /api/v1/knowledge/{id}/sources`
- `POST /api/v1/knowledge/{id}/review`
- `GET /api/v1/search/knowledge`
- `GET /api/v1/settings/providers`
- `PUT /api/v1/settings/providers/{provider}/permissions`
- `PUT /api/v1/settings/providers/{provider}/policy-review`
- `POST /api/v1/objectives`
- `POST /api/v1/objectives/{id}/packets`
- `POST /api/v1/objectives/{id}/responses`

## Important limitations

- The local API is intended for a single trusted local user. It is not safe to expose on a LAN or public internet; host validation prevents non-loopback binding by default.
- The browser companion is not implemented. No content-script or provider-page permissions are included.
- Semantic extraction is a user-mediated or optional local-model operation. Deterministic episode segmentation is not presented as semantic understanding.
- No knowledge item is automatically promoted to active truth. Extracted items remain candidates until explicit user review; only user-confirmed or validated items can be included in cross-model context packets.
- No arbitrary code execution or autonomous experiment execution is included in this vertical slice.
- Backup encryption, dependency-aware source deletion, Claude/Gemini adapters, migration upgrade/rollback verification, and Windows installer are pending.

## Project documents

See `docs/` for the product specification, architecture, database schema, threat model, evaluation plan, implementation backlog, and decision records. The authoritative specification is `docs/SPEC.md`.
