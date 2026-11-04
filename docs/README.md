# Mosaic specification package

Mosaic is a local-first, cross-model intelligence and adaptive knowledge system. This package defines the implementation baseline; it does **not** contain a working application yet.

## Documents

- [`SPEC.md`](SPEC.md) — authoritative product and system specification.
- [`architecture/system.mmd`](architecture/system.mmd) — Mermaid system architecture diagram.
- [`architecture/component-map.md`](architecture/component-map.md) — module responsibilities and dependency rules.
- [`database/schema.sql`](database/schema.sql) — initial SQLite reference schema.
- [`database/data-dictionary.md`](database/data-dictionary.md) — entity and lifecycle definitions.
- [`security/threat-model.md`](security/threat-model.md) — assets, boundaries, threats, mitigations, abuse cases.
- [`quality/benchmark-plan.md`](quality/benchmark-plan.md) — corpus, metrics, evaluation and release gates.
- [`planning/implementation-backlog.md`](planning/implementation-backlog.md) — dependency-ordered implementation tasks.
- [`decisions/ADR-001-local-first-modular-monolith.md`](decisions/ADR-001-local-first-modular-monolith.md) — architecture decision.
- [`decisions/ADR-002-no-provider-scraping.md`](decisions/ADR-002-no-provider-scraping.md) — provider interaction boundary.
- [`provider-policy-matrix-template.md`](provider-policy-matrix-template.md) — provider-by-provider legal/policy review template.

## Important status

This is a design baseline, not an implementation. No application code has been built or tested as part of this package. The SQL schema is a reference snapshot and must be applied through migrations and tested against the SQLite version shipped with the application.

## Recommended first implementation slice

1. Create the backend and frontend skeleton.
2. Add SQLite migrations and canonical conversation/message models.
3. Import one real, user-owned ChatGPT export fixture.
4. Display the imported conversation and message sequence.
5. Analyse one episode and extract a small set of source-linked knowledge items.
6. Correct/confirm one item and prove it remains searchable after restart.

The first slice should not include browser automation, vector databases, multi-provider API routing, autonomous code execution, or model fine-tuning.

## Proposed project structure

```text
mosaic/
├─ apps/
│  ├─ web/                    # React + TypeScript UI
│  └─ browser-companion/      # Optional outbound-only extension, later milestone
├─ backend/
│  ├─ app/
│  │  ├─ api/                 # FastAPI routes and request/response contracts
│  │  ├─ canonical/            # Conversation/message schemas
│  │  ├─ importers/            # Provider archive adapters
│  │  ├─ analysis/             # Segmentation and semantic extraction
│  │  ├─ knowledge/            # Items, evidence, relations, lifecycle
│  │  ├─ retrieval/            # FTS and context construction
│  │  ├─ coordination/         # Objectives, sessions, context packets
│  │  ├─ learning/             # Feedback, model observations, experiments
│  │  ├─ policy/               # Provider gates, redaction, approvals
│  │  ├─ storage/              # Repositories and file store
│  │  └─ jobs/                 # Durable background jobs
│  ├─ migrations/              # Alembic migrations
│  └─ tests/
│     ├─ unit/
│     ├─ integration/
│     ├─ security/
│     └─ fixtures/             # Synthetic/redacted fixtures only
├─ docs/                       # Copy of specification package
├─ scripts/
└─ pyproject.toml
```

## Windows development environment (proposed)

When implementation begins, use PowerShell from the repository root:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
```

Then install backend dependencies from the eventual `pyproject.toml` and frontend dependencies from `apps/web/package.json`. The actual dependency list and lockfiles must be generated during implementation; do not invent placeholder package versions in advance.

Local inference is optional. If Ollama is installed and a compatible model is available, configure the local adapter to use its loopback endpoint. Mosaic must remain useful when Ollama is absent.

## Change control

`SPEC.md` is authoritative. Any change to provider interaction, data retention, personal/general scope, extraction contracts, or knowledge promotion must include:

- a change to the relevant requirement;
- an ADR when the architectural decision changes;
- schema migration if needed;
- tests for the changed acceptance criteria;
- benchmark report if semantic behaviour changes.
