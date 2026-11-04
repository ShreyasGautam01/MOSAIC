# Mosaic test matrix

| Layer | What is tested | Example test | Gate |
|---|---|---|---|
| Unit | Pure parsers and domain rules | Role normalisation, exact evidence-span validation, status transitions | Every PR/change |
| Unit | Policy functions | `unreviewed` provider blocks transfer; personal-only item excluded from general packet | Every PR/change |
| Unit | Metric calculations | Precision/recall, paired comparison, timeout accounting | Every PR/change |
| Integration | Importer + database + FTS | Import fixture, restart, search, inspect references | Every importer change |
| Integration | Analysis + evidence repository | Model returns item with fabricated message ID; transaction rejects it | Every analysis change |
| Integration | Handoff + policy + redaction | Packet with test secret is redacted before copy | Every packet change |
| Integration | Learning + experiment + rollback | Candidate fails holdout and cannot activate; rollback restores prior method | Every learning change |
| Application | Main user journeys | Import → analyse → review → search → objective → packet → response | Every release candidate |
| Security | Prompt injection | Malicious transcript requests secret disclosure or policy changes | Every release candidate |
| Security | Archive processing | Path traversal, zip bomb, oversized/nested archive | Every importer release |
| Security | Browser companion | Confirm no host permissions/content scripts/cookie access | Every extension release |
| Privacy | Deletion | Delete source, verify messages/FTS/derived data and backup semantics | Every release candidate |
| Performance | Local archive search | 100k-message representative archive on declared reference hardware | Before performance claim |
| Acceptance | Learning benefit | Baseline vs knowledge-only vs adaptive on held-out tasks | Before claiming self-improvement |