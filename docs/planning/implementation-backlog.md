# Mosaic implementation backlog

The backlog is ordered by dependency and risk reduction. Build vertical slices that persist real data and have tests; do not create placeholder flows that look finished but do not work.

## Engineering rules

- Work on one bounded issue at a time.
- Before coding, read the relevant requirement and acceptance test.
- Each feature includes unit, integration, and user-facing tests where applicable.
- Add a database migration for every schema change.
- Preserve user data; do not run destructive migration/reset commands without explicit user approval.
- Repository updates are authorised on feature branches for this project. Do not force-push, merge pull requests, reset/discard user work, or deploy unless explicitly requested.
- Never store provider passwords, session cookies, API keys, or browser tokens.
- Every LLM output is untrusted until schema- and source-validated.

---

## Epic 0 — Finalise constraints and fixtures

### MOS-001: Provider policy review record

- Create a provider policy registry schema and review template.
- Record provider, product, terms URL, review date, operations allowed/unclear/prohibited, and reviewer.
- Default unreviewed provider actions to disabled.
- **Acceptance:** Cross-provider transfer and derived learning are blocked when policy state is unreviewed/restricted.

### MOS-002: Gather private, redacted import fixtures

- Obtain one valid export archive from each selected provider where available.
- Create synthetic fixtures for edge cases.
- Remove names, emails, credentials, and confidential material.
- Store private fixtures outside the public repository.
- **Acceptance:** Fixture manifest documents source version and expected record counts without publishing private content.

### MOS-003: Lock MVP benchmark annotation guide

- Define labels for concepts, claims, constraints, strategies, decisions, evidence, conflicts, and questions.
- Define explicit/inferred/user-confirmed semantics.
- **Acceptance:** Two reviewers can independently label a sample and resolve disagreements using the guide.

## Epic 1 — Repository and application foundation

### MOS-010: Create backend package skeleton

- FastAPI application factory.
- Settings/configuration using environment variables and local config file.
- Structured logging with content redaction.
- Health endpoint.
- **Acceptance:** App starts locally and health check passes without any model installed.

### MOS-011: Create frontend shell

- React + TypeScript + Vite.
- Initial Overview, Imports, Conversations, and Knowledge workspaces are implemented in the first vertical slice.
- Objectives, Experiments, and Settings workspaces remain planned.
- Loading, empty, failure, and degraded-mode states.
- **Acceptance:** UI can connect to local API; no placeholder controls imply unsupported behaviour.

### MOS-012: Add schema migrations and SQLite repository

- Explicit SQL migration files managed by Mosaic's small migration runner (no ORM dependency in the MVP).
- SQLite foreign keys enabled on every connection.
- WAL mode configured for local same-host use.
- FTS5 availability check at startup.
- **Acceptance:** Fresh DB migration and upgrade test pass; FTS search works; DB backup/restore test passes.

### MOS-013: Add durable job queue

- `processing_jobs` table.
- Single worker with lease/claim, retry cap, cancellation, and idempotency key.
- **Acceptance:** Kill/restart test does not duplicate committed import or corrupt state.

## Epic 2 — First import vertical slice

### MOS-020: Define canonical conversation Pydantic schemas

- Conversation, Message, Branch, AttachmentMetadata models.
- Strict role and timestamp normalisation.
- Preserve unrecognised source metadata in a bounded JSON field.
- **Acceptance:** Schema tests include missing/unknown values and branching.

### MOS-021: Implement safe archive intake

- File signature and MIME checks.
- Streaming archive inspection.
- Compressed/expanded limits, entry limits, path checks, and duplicate-name handling.
- Temp directory cleanup on failure.
- **Acceptance:** Zip slip, decompression bomb, oversized and malformed archive tests pass.

### MOS-022: Implement ChatGPT export adapter

- Parse verified fixture shape(s).
- Preserve conversation ID/title/message graph/timestamps and supported metadata.
- Report unsupported content rather than silently dropping it.
- **Acceptance:** Message counts, roles, branches, and source spans match fixture expectations.

### MOS-023: Implement generic pasted transcript adapter

- Text/Markdown input with manual speaker labels.
- **Acceptance:** User can import and reopen a transcript with stable message boundaries.

### MOS-024: Implement import report UI

- Provider detection, record counts, warnings, parser version, skipped entries.
- **Acceptance:** User can distinguish complete, partial, failed, and unsupported imports.

### MOS-025: Add Claude export adapter

- Use only actual export fixtures and documented supported formats.
- **Acceptance:** Adapter tests run on multiple fixtures; unknown versions fail safely.

### MOS-026: Add Gemini Takeout adapter

- Identify Gemini Apps activity records in a user-selected Takeout archive.
- **Acceptance:** Adapter tests preserve message order and provider metadata; unrelated Takeout data is skipped safely.

### MOS-027: Add source deletion and duplicate detection

- Hash archive and deduplicate imports.
- Dependency-aware deletion transaction and FTS cleanup.
- **Acceptance:** Delete/reopen/search tests prove source text is no longer indexed.

## Epic 3 — Semantic interpretation

### MOS-030: Define extraction JSON schemas

- KnowledgeItem, Evidence, StrategyObservation, Episode, ConflictCandidate schemas.
- Explicit/inferred labels and controlled vocabularies.
- **Acceptance:** Invalid IDs, malformed arrays, and missing evidence are rejected.

### MOS-031: Implement deterministic segmentation and metadata extraction

- Heading/code block/message-boundary heuristics.
- No LLM required.
- **Acceptance:** Stable output and unit tests on short/long/branched conversations.

### MOS-032: Implement local model adapter

- Provider-neutral interface.
- Optional Ollama implementation.
- Configurable model ID and endpoint restricted to loopback by default.
- JSON-schema constrained request where supported; Pydantic server validation always required.
- **Acceptance:** Offline/unavailable mode is handled; local model can be changed without schema/database changes.

### MOS-033: Implement episode analysis pipeline

- Analyze one episode at a time.
- Return source-linked candidate items.
- Check all referenced message IDs/spans server-side.
- One repair retry, then unresolved state.
- **Acceptance:** Gold-set grounding and extraction metrics are reported.

### MOS-034: Implement assisted analysis packet

- Generate provider-neutral prompt asking for structured analysis and exact message references.
- Explicitly forbid hidden-CoT solicitation.
- User pastes response back; validate it like any other untrusted model output.
- **Acceptance:** A full report can be completed without any model API.

### MOS-035: Conversation intelligence report UI

- Overview, episodes, extracted knowledge, strategies, decisions, open questions, and source references.
- Inline confirm/reject/correct actions.
- **Acceptance:** Every displayed item opens its source message(s).

## Epic 4 — Knowledge network and retrieval

### MOS-040: Knowledge repository and lifecycle

- Create/update/version/reject/deprecate/withdraw operations.
- Enforce candidate-first rules.
- **Acceptance:** State transition unit tests and audit records pass.

### MOS-041: Evidence and relationship management

- Supports/challenges/qualifies/context relations.
- Knowledge graph edge suggestions.
- **Acceptance:** No relationship is promoted from candidate without review/evidence.

### MOS-042: FTS5 indexing and search UI

- Index messages and knowledge items.
- Provider/date/type/scope/status filters.
- **Acceptance:** Search result links to source and respects workspace/scope/policy filters.

### MOS-043: Cross-conversation consolidation

- Similarity and duplicate suggestions.
- Conflict candidate generation.
- **Acceptance:** No automatic merge; false-merge benchmark measured.

### MOS-044: Personal/general scope controls

- UI to set scope and review personal-data warnings.
- General scope remains private in MVP.
- **Acceptance:** Scope-leakage tests pass and general promotion is user-approved.

## Epic 5 — Objective and coordination workflow

### MOS-050: Objective workspace

- Objective, expected output, constraints, non-goals, decisions, status, versioning.
- **Acceptance:** Context packet is always bound to a specific objective version.

### MOS-051: Context retrieval and packet compiler

- Retrieve relevant knowledge by FTS and metadata.
- Compile objective, constraints, decisions, evidence, conflicts, open questions, requested role.
- **Acceptance:** Required fields preserved; packet source list and length shown.

### MOS-052: Packet preview, redaction, and clipboard

- Full preview, secret checks, user removal/override.
- Explicit copy action.
- **Acceptance:** Seeded secret is redacted or requires explicit review.

### MOS-053: Manual response intake

- Paste response, set provider/model/version (unknown allowed), link to session.
- **Acceptance:** Response retains attribution and is analysed as untrusted input.

### MOS-054: Parallel/sequential/adversarial session views

- Distinct sessions under one objective.
- Contribution comparison and disagreement table.
- **Acceptance:** No majority vote; unresolved contradictions remain visible.

### MOS-055: Browser companion (outbound-only)

- Minimal-permission browser extension.
- Show packet, copy packet, open selected provider URL, return to Mosaic UI.
- No provider-page content access, no content scripts, no auto-fill/submit, no cookies.
- **Acceptance:** Manifest inspection verifies minimal permissions; browser tests show no page-read capability.

## Epic 6 — Learning and experiments

### MOS-060: Feedback event capture

- Explicit confirm/reject/correct/useful/not-useful/task pass/fail.
- Distinguish preferences from correctness.
- **Acceptance:** Silence does not create feedback events.

### MOS-061: Model/strategy performance ledger

- Comparable task metadata, provider/model/version, evaluation method, outcome.
- **Acceptance:** UI shows sample counts and does not rank insufficiently sampled providers.

### MOS-062: Benchmark suite runner

- Stable suite version and splits.
- Deterministic evaluator interface plus human review record.
- **Acceptance:** Holdout cases are not available to tuning workflows.

### MOS-063: Experiment planner

- Hypothesis, baseline, candidate, control variables, metrics, test split, limits, stopping rule.
- **Acceptance:** Cannot start without complete protocol and approval.

### MOS-064: Bounded experiment runner

- Structured/text tasks only; no arbitrary imported code.
- Timeout, case limit, cancellation.
- **Acceptance:** Resource caps and reproducibility tests pass.

### MOS-065: Promotion and rollback

- Gate checks, immutable procedure version, approval, regression suite.
- **Acceptance:** Failed or inconclusive candidate cannot become active; rollback restores previous version.

## Epic 7 — Hardening and release

### MOS-070: Threat-model test suite

- Prompt injection, archive abuse, fake provenance, secret leakage, scope leakage, deletion, excessive agency.
- **Acceptance:** All critical security tests pass.

### MOS-071: Backup/export and restore

- SQLite-consistent backup, selected source inclusion, manifest and hashes.
- Optional encrypted export if supported by reviewed implementation.
- **Acceptance:** Fresh install restores conversations, knowledge, evidence, and links.

### MOS-072: Resource monitor and degraded modes

- Storage usage, model availability, job failures, configured budgets.
- **Acceptance:** No model/internet/storage failure makes the core archive unreadable.

### MOS-073: Full application acceptance run

- Import → analyse → correct → search → objective → handoff → response → experiment → promotion/rollback → delete/export.
- **Acceptance:** End-to-end run completes on Windows from documented PowerShell commands.

### MOS-074: Release documentation

- User guide, backup/deletion guide, provider policy notice, troubleshooting, benchmark report.
- **Acceptance:** A new user can perform the core journey without developer intervention.

---

## Suggested milestones

| Milestone | Scope | Exit evidence |
|---|---|---|
| M0 | Repo, DB, health endpoint, canonical schema | Unit tests + fresh DB migration |
| M1 | ChatGPT import vertical slice | Fixture import + source-linked conversation view |
| M2 | Semantic report + local/assisted analysis | Gold-set report and evidence metrics |
| M3 | Claude/Gemini adapters + FTS knowledge | Multi-provider import benchmark |
| M4 | Objectives + manual coordination | Successful sequential and adversarial handoff demos |
| M5 | Browser companion | Minimal-permission manifest and outbound-only tests |
| M6 | Learning experiments | Baseline/candidate report on holdout tasks |
| M7 | Hardened MVP release | Full acceptance, threat-model, backup, and deletion reports |

Do not start M5 before manual coordination works. Do not start M6 before source-grounded semantic extraction and benchmark labels are reliable.