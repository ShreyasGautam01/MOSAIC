# Mosaic

**Cross-Model Intelligence & Adaptive Knowledge System** — a local-first, provider-independent conversation intelligence workspace.

Mosaic imports user-supplied AI conversation exports, normalises them, preserves source provenance, supports local search, prepares source-grounded analysis packets, and stores extracted knowledge as reviewable candidates. It also supports policy-gated, user-mediated handoffs between ordinary consumer AI chat interfaces.

> **Project status:** early implementation / first vertical slice. This repository is being bootstrapped. The initial source package and detailed specification will be added on a feature branch. Do not treat the application as production-ready.

## Principles

- Local-first: API binds to loopback; user data stays on the local machine by default.
- User-mediated provider interaction: no scraping, cookies, session tokens, automated extraction, or silent submission.
- Evidence-first: knowledge remains a candidate until reviewed and retains source-message references.
- Honest attribution: provider labels on returned responses are user-attested, not cryptographically verified.
- Reversible learning: no foundation-model fine-tuning or self-modifying application code in the MVP.
- Provider-policy gates: storage, indexing, derivation, strategy analysis, and cross-provider transfer are separate controls.

## Documentation

The authoritative product specification, architecture, database model, threat model, benchmark plan, and implementation backlog will live under `docs/`.

## Development

Backend: Python 3.11+, FastAPI, SQLite/FTS5.  
Frontend: React, TypeScript, Vite.  
Optional local inference: Ollama on loopback.

Run commands and current verified capabilities will be documented in the implementation README after the first source bundle is committed.

## Security

Never commit imported conversation archives, local databases, credentials, provider cookies, or user data. See `SECURITY.md` for reporting instructions.
