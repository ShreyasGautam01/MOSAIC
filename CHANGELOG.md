# Changelog

## Unreleased

- Added 24-hour, single-use, server-issued analysis handoffs; provider attribution is server-derived and transfer/storage policy is rechecked transactionally when analysis is ingested.
- Added integration coverage for provider spoofing, handoff replay/expiry, missing storage consent, and revoked transfer permission.

- Establish the first import-to-knowledge vertical slice.

## 0.1.0 — Initial implementation baseline

- FastAPI local API and SQLite migration runner.
- ChatGPT ZIP/JSON and manual TXT/Markdown import adapters.
- Defensive ZIP inspection without extraction.
- Canonical conversation and message persistence with source provenance.
- FTS5 message and knowledge search with provider-aware indexing permissions.
- Source-grounded candidate extraction via manual consumer-model handoff or optional local Ollama inference.
- Credential-like string redaction before outbound analysis/context packets.
- Explicit knowledge review lifecycle and audit records.
- Objective/context packet and manual model-response persistence endpoints.
- Initial React workspaces for overview, import, conversation inspection, and knowledge review.
