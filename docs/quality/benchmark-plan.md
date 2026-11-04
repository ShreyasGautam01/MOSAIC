# Mosaic evaluation and benchmark plan

**Purpose:** Demonstrate import correctness, source-grounded semantic interpretation, useful cross-model handoffs, and genuine improvement without regression.

## 1. Evaluation principles

1. Evaluate the application separately from the underlying model.
2. Keep source conversations and benchmark labels private and permissioned.
3. Split by conversation/source, not random individual messages, to prevent leakage.
4. Keep a protected holdout set that is never used to tune prompts, procedures, or thresholds.
5. Record parser, model, prompt, schema, and evaluator versions.
6. Distinguish source fidelity from factual truth. A source-linked claim may accurately describe what a model said while still being factually wrong.
7. Do not use model agreement as ground truth.
8. Use deterministic graders wherever possible; use human review for semantic dimensions; use model graders only as secondary evidence.
9. Publish confidence intervals and sample counts. Do not overstate results from a small corpus.
10. Any claimed learning improvement must be measured on unseen tasks and compared against a stable baseline.

## 2. Benchmark corpus

### 2.1 Import fixtures

Minimum compatibility fixtures:

- 3 ChatGPT export archives from different export shapes/versions where available;
- 3 Claude export archives;
- 3 Gemini Takeout archives;
- 10 manually pasted generic transcripts, including branching/partial metadata;
- malformed, truncated, duplicate, oversized, and unsupported files.

Fixtures must be user-owned, synthetic, or explicitly consented and redacted. Never place private archives in a public repository.

### 2.2 Semantic gold set

Build a versioned, human-reviewed dataset with at least:

- 60 conversations or conversation episodes across at least 3 providers and 5 task categories;
- 150 annotated knowledge items;
- 50 claims with exact supporting/challenging message spans;
- 25 methodology/strategy observations;
- 25 decision records;
- 20 open questions or unresolved conflicts;
- 15 examples where the best interpretation is “insufficient evidence / do not extract.”

Task categories should include technical problem-solving, conceptual explanation, research synthesis, planning/decision-making, and debugging/workflow analysis.

### 2.3 Data splits

Split at conversation level:

- development: 60%;
- validation: 20%;
- protected holdout: 20%.

Do not allow episodes from the same original conversation to cross splits. Revisions to the holdout set require a new benchmark version and documented reason.

### 2.4 Transfer/generalisation set

Create at least 50 unseen tasks that test whether a procedure learned from one conversation applies to a different but related problem. Include counterexamples where transfer should fail because preconditions are not met.

## 3. Metrics and provisional gates

The numeric thresholds below are **initial release targets**, not existing results. They must be recalibrated on a pilot set before being treated as final.

| Dimension | Metric | Provisional MVP / release target |
|---|---|---|
| Import | Message count and role mapping on supported fixtures | 100% expected records preserved on fixture suite; unsupported fields explicitly reported |
| Import | Duplicate handling | Identical archive is not duplicated silently |
| Grounding | Evidence-link validity | 100% of stored factual claims reference existing source messages or are classified as hypotheses |
| Grounding | Exact-span verification | ≥95% of extracted source spans match source text and support the associated statement |
| Extraction | Claim precision | ≥0.90 on gold set |
| Extraction | Claim recall | ≥0.75 on gold set; report by item category |
| Context | Objective/constraint retention | ≥0.95 recall for labelled objectives and hard constraints |
| Strategy | Strategy-label F1 | ≥0.80 against reviewed labels; explicit vs inferred reported separately |
| Decision | Decision/alternative extraction F1 | ≥0.80 on reviewed cases |
| Conflict | Contradiction precision | ≥0.85 on curated conflict set |
| Conflict | Contradiction recall | ≥0.65 initially; improve without reducing precision materially |
| Deduplication | False merge rate | <0.05 on adjudicated pair set |
| Handoff | Required-context retention | 100% for required objective/constraint/decision fields; optional evidence selection reviewed |
| Handoff | Human usefulness rating | Median ≥4/5 across at least 20 handoffs, with rubric and sample count |
| Learning | Promotion safety | 100% of active procedures have a recorded evaluation and approval event |
| Learning | Held-out improvement | Candidate must improve primary metric by a pre-registered meaningful margin; no critical regression |
| Security | Injection containment | 100% of tested malicious content fails to cause privileged action or policy change |
| Privacy | Deletion | 100% of deleted source text is absent from active search/indexes and dependent items are handled by policy |

## 4. Evaluation tasks

### 4.1 Import correctness

- supported archive detection;
- role mapping and ordering;
- timestamps and branch links;
- malformed record recovery;
- unknown field warnings;
- duplicate imports;
- archive resource limits;
- idempotent retry after interruption.

### 4.2 Semantic interpretation

Annotators label:

- objective and constraints;
- concepts/definitions;
- factual claims;
- evidence spans;
- explicit vs inferred interpretations;
- strategy observations;
- decisions and alternatives;
- outcomes and unresolved questions;
- disagreements and contradictions.

Evaluate precision/recall/F1 per category. For source support, the reviewer must judge not only whether a citation points to a real message but whether that message actually supports the extracted statement.

### 4.3 Conversation-level reconstruction

Human reviewers score 1–5:

- objective preserved;
- important constraints preserved;
- major decision sequence preserved;
- disagreements and corrections preserved;
- final state and open questions preserved;
- no unsupported certainty added.

Report per-dimension median and inter-rater agreement when multiple reviewers are available.

### 4.4 Cross-model coordination

For each task, compare:

A. one model with no imported context;  
B. one model with a Mosaic context packet;  
C. a manually coordinated multi-model sequence using Mosaic packets.

Use comparable prompts, model versions, and evaluation rubrics where possible. Measure:

- final task success;
- factual/technical error count;
- constraints violated;
- unresolved disagreements;
- source/evidence quality;
- user correction count;
- elapsed human time and number of manual handoffs.

Do not assume C must always beat A. The system should learn when multi-model coordination adds value and when it adds unnecessary overhead.

### 4.5 Learning-effectiveness experiment

Compare three arms:

- **A — Baseline:** same local model/inference configuration, no accumulated knowledge or procedural memory.
- **B — Knowledge only:** retrieve approved source-linked knowledge, but no learned procedure selection.
- **C — Knowledge + adaptation:** retrieve knowledge and use procedures promoted through prior experiments.

Use the same protected task set. Keep model version, prompts, temperature/decoding settings where available, and evaluator stable. Use paired tasks and repeated runs for stochastic systems.

Primary outcome: task success under the pre-defined rubric. Secondary outcomes: correction rate, attempts, time, token/context size where observable, and resource use.

Promotion requires:

1. candidate passes the pre-registered held-out comparison;
2. improvement exceeds a practical threshold defined before the run;
3. paired confidence interval does not indicate a material regression;
4. protected regression set passes;
5. results are reproducible across at least two runs where randomness is relevant;
6. user approves activation in MVP.

If sample size is insufficient or uncertainty remains high, label the result `inconclusive`; do not force promotion.

### 4.6 Model/strategy performance ledger

Only record a success/failure when there is a defined evaluator or explicit user judgement. Store task category, complexity, provider, model version, strategy, and evaluation method. Show per-category sample counts. Do not recommend a model for a category until at least 20 comparable observations are present; even then, expose uncertainty and avoid universal rankings.

## 5. Regression suite

Maintain protected tests for:

- import parser versions;
- exact source-span validation;
- context packet required fields;
- privacy redaction;
- knowledge status transitions;
- personal/general scope isolation;
- provider policy gates;
- deletion and FTS cleanup;
- failed model output handling;
- experiment promotion and rollback;
- extension permission boundaries.

Run the deterministic suite on every change. Run the full semantic holdout benchmark before any change to prompts, extraction schemas, local model, retrieval policy, or procedure-promotion logic.

## 6. Reporting format

Every evaluation report includes:

- build/commit identifier;
- schema, parser, prompt, local model, and evaluator versions;
- benchmark suite version and split;
- exact sample sizes;
- metrics with confidence intervals where appropriate;
- per-provider and per-task breakdowns;
- failure examples and error taxonomy;
- resource use and duration;
- accepted/rejected/inconclusive decision;
- limitations and known confounders.

No statement such as “Mosaic learned” is allowed in release notes unless it is tied to a measured held-out outcome and regression report.