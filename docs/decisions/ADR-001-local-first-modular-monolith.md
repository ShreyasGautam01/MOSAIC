# ADR-001: Local-first modular monolith

- **Status:** Accepted for MVP
- **Date:** 2026-11-03

## Context

Mosaic is a single-user knowledge and coordination application. Its core risk is correct semantic extraction, provenance, and controlled updates—not high-throughput distributed processing. The application must work without paid APIs and should be practical on a Windows desktop.

## Decision

Use a local React/TypeScript client, a Python/FastAPI backend, SQLite + FTS5, and a local file store. Keep logical modules in one deployable backend. Use a durable jobs table and a single worker for import/analysis tasks. Local inference is optional behind a provider interface.

## Consequences

Positive:
- fewer moving parts and easier local debugging;
- no required cloud account or paid hosted service;
- easier user ownership and backup/export;
- clear seams for tests and later modularisation.

Trade-offs:
- SQLite write throughput is limited and WAL is same-host only;
- long local model tasks may occupy the single worker;
- multi-device sync and collaborative use are not MVP capabilities;
- local model quality depends on user hardware and selected model.

## Revisit when

Measured concurrency, multi-user requirements, or deployment constraints justify a separate worker/database service.