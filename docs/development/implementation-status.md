# Implementation status

This document distinguishes implemented behaviour from the product roadmap. It is not a claim that the product has passed release acceptance.

## Implemented in the current vertical slice

- Local FastAPI application factory; loopback-only settings validation and trusted-host/origin checks.
- SQLite database migration runner, foreign-key enforcement, WAL mode, FTS5 checks, and explicit schema migrations.
- ChatGPT export ZIP/JSON parsing for tested common mapping/flat shapes.
- Manual TXT/Markdown transcript import.
- ZIP safety validation with no filesystem extraction.
- Content-addressed original source storage and exact-file duplicate detection.
- Canonical conversations/messages with source IDs, parent links, sequence numbers, metadata and content hashes.
- Deterministic episode segmentation and message/knowledge FTS search.
- Provider-specific storage/indexing/derivation/strategy/transfer permissions; indexing is optional and the FTS index is removed/rebuilt when policy changes.
- User-recorded provider policy review attestations with HTTPS policy references; cross-provider transfers require both source and destination policy records to be marked `allowed_with_conditions`.
- Permission-aware search-index removal/rebuild. For a knowledge item with multiple provider-backed sources, indexing requires every such source to permit indexing.
- Analysis prompts that ask for observable behaviour only, not hidden chain-of-thought; credential-like string redaction before outbound analysis.
- Optional local Ollama structured-output adapter restricted to loopback.
- Candidate knowledge with message-level provenance and exact-quote verification.
- Explicit user confirm/reject/withdraw review, versioning, feedback and audit records.
- Candidate/rejected/withdrawn knowledge is blocked from context packets; only user-confirmed or validated states are exportable.
- Objective/context packet APIs and server-issued, 24-hour single-use analysis handoffs bound to workspace, source conversation, source provider, destination provider, content hash, and redaction report. Provider attribution is derived from the handoff record, not a client field. Permissions and policy status are rechecked transactionally when returned analysis is persisted.
- Objective response provider attribution is derived from the prepared context packet, not a client field; destination and source-transfer policies are rechecked before response persistence, and each session accepts one response.
- Initial React UI for Overview, Import, Conversations and Knowledge review.

## Not implemented yet

- Claude and Gemini export adapters. These require real, redacted, versioned fixtures before claims of support.
- Streaming/chunked import and background job execution for very large archives.
- Dependency-aware source deletion and full data-retention UI.
- Semantic embeddings, vector retrieval, knowledge graph relationship suggestions, and cross-conversation consolidation.
- Rich episode-level analysis, disagreement resolution, strategy comparison, and model performance ledger.
- Objectives and parallel/sequential/adversarial coordination UI.
- Experiment design/runner, benchmark suite management, and evidence-gated procedure promotion.
- Browser companion. No provider page scraping, DOM access, cookies, auto-fill, or auto-submit is included.
- Encrypted backup/export, Windows installer, and end-user recovery workflow.
- Full frontend typecheck/build; the preparation environment could not access the npm registry and no lockfile was generated.

## Validation performed

- Backend pytest suite: 34 tests passed, including spoofed-provider rejection, one-use replay prevention, expiry, missing storage consent, and transaction-time transfer-permission rechecks.
- Python bytecode compilation: passed.
- Ruff, Python bytecode compilation, and all 34 backend tests passed in GitHub Actions on Python 3.11, 3.12, and 3.13 (CI run 41818979251).
- Frontend TypeScript typecheck and Vite production build passed in the same GitHub Actions run. Local npm installation was unavailable in the preparation environment, so frontend verification was performed on the clean CI runner.
- The repository does not yet contain a frontend lockfile; exact transitive dependency reproducibility remains a follow-up task.