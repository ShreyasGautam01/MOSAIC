# Mosaic component map

| Module | Owns | Must not own |
|---|---|---|
| Import adapters | Provider export parsing, archive validation, format detection | Semantic truth decisions, provider login/session access |
| Canonical model | Normalised conversations, messages, branches, timestamps | Provider-specific scraping |
| Semantic pipeline | Episode boundaries, extraction requests, strategy observations | Direct database writes outside repositories; hidden-CoT claims |
| Local model adapter | Local inference request/response contract | Cloud inference or provider credentials |
| Assisted analysis | User-visible prompts and structured return intake | Sending messages to provider websites |
| Knowledge manager | Items, evidence, relations, versions, conflict workflow | Silent factual promotion |
| Retrieval | FTS5 queries, filters, context assembly | Unreviewed external transmission |
| Coordination | Objectives, sessions, packets, attribution | Provider-site automation |
| Learning controller | Feedback events, candidate lifecycle, promotion policy | Modifying its own security rules or executable source |
| Experiment engine | Bounded task runs, baseline/candidate execution | Arbitrary code execution from imported content |
| Evaluation | Metric calculations, regression gates, benchmark versions | Changing test labels to make a candidate pass |
| Policy layer | Provider permissions, scope checks, redaction, approvals | Legal conclusions without a reviewed policy record |
| Audit layer | Minimal event metadata, actor, operation, timestamp | Full transcript or secret logging |

## Dependency rules

1. UI depends on API contracts, not database tables.
2. Import adapters depend on canonical schemas and repositories, not the semantic pipeline.
3. Semantic pipeline returns validated typed objects; repositories decide whether and how to persist them.
4. Knowledge items always preserve evidence relationships.
5. Context builder reads only items permitted by workspace, provider policy, user scope, and explicit packet selections.
6. Learning controller cannot promote a procedure without an evaluation record and a rollback version.
7. Policy checks run before import, indexing, derived analysis, and external handoff.
8. Experiments accept declarative test cases only in MVP.