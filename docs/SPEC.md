# Mosaic — Cross-Model Intelligence & Adaptive Knowledge System

**Product specification:** 1.0  
**Status:** Proposed baseline for implementation  
**Date:** 3 November 2026  
**Working product name:** Mosaic (codename; naming/trademark clearance not performed)

---

## 1. Product definition

Mosaic is a **local-first, provider-independent intelligence layer** that helps one user understand, preserve, connect, and reuse the knowledge contained in conversations with multiple consumer AI systems. It transforms imported or user-pasted conversations into source-linked knowledge, observable problem-solving strategies, decisions, evidence, and reusable procedures. It also prepares context handoffs between ordinary consumer chat interfaces and learns—through validated outcomes—which knowledge and procedures are useful in which circumstances.

Mosaic is not another foundation model, a model marketplace, an API-based model router, or an autonomous browser agent. Its core asset is a user-controlled semantic knowledge base and the evaluation history attached to it.

### 1.1 Product promise

A user should be able to:

1. Import conversations from supported AI platforms or paste a conversation manually.
2. Understand what was discussed, what was learned, what was decided, which visible problem-solving approaches were used, and what remains unresolved.
3. Trace extracted claims and methods back to exact source messages.
4. Search and connect knowledge across conversations and providers.
5. Prepare a relevant, compact context packet for another AI's normal chat interface.
6. bring the response back, compare it with prior work, and update the knowledge base.
7. Experiment with proposed methods against baselines and only promote improvements that pass defined gates.

### 1.2 Architectural decisions already selected

| Decision | Baseline |
|---|---|
| Interpretation | Hybrid: deterministic parsers + local model inference for routine semantic work + user-mediated consumer AI assistance for difficult cases |
| Coordination | Both: manual handoffs are the guaranteed path; an optional browser companion assists with outbound context preparation and navigation, without reading provider pages or auto-submitting prompts |
| Intelligence scope | Hybrid personal/general: personal knowledge is user-specific; general knowledge is transferable within the user's own library. Nothing is public or shared by default |
| Deployment | Local-first on Windows; no cloud account required for MVP |
| Provider connectivity | No commercial model APIs and no work-mode agents required |
| Learning | External memory, evidence and procedural adaptation; no foundation-model weight updates in MVP |
| Human control | User approves sensitive exports, provider handoffs, knowledge promotion, and consequential changes |

### 1.3 Terminology

- **Source artifact:** Original user-supplied archive, file, or pasted transcript.
- **Canonical conversation:** Provider-neutral representation of a conversation and its message structure.
- **Episode:** A coherent sub-problem or phase within a longer conversation.
- **Knowledge item:** A structured concept, claim, constraint, decision, finding, method, preference, outcome, or open question.
- **Evidence:** A source span, user observation, independent reference, or experiment result that supports or challenges a knowledge item.
- **Strategy observation:** A description of an externally observable problem-solving behaviour (e.g., decomposition, comparison, adversarial critique, testing). It is not a reconstruction of hidden model cognition.
- **Procedure:** A reusable, versioned sequence of steps with preconditions, applicability conditions, and failure modes.
- **Context packet:** A compact, user-previewable bundle of task context prepared for a destination chat interface.
- **Learning event:** An auditable event that proposes, validates, rejects, updates, or retires knowledge or a procedure.
- **Personal scope:** Knowledge that is tied to the user's projects, preferences, history, or private context.
- **General scope:** Knowledge or a procedure that appears transferable beyond one personal episode. In MVP it remains inside that user's private library; it is not publicly shared.

---

## 2. Problem statement and product thesis

Consumer AI conversations are fragmented across providers, accounts, projects, and interfaces. Important context, corrections, research, decisions, and useful problem-solving approaches are difficult to carry into a new conversation. Ordinary transcript search and summarisation preserve some information but do not reliably turn it into reusable, evidence-linked knowledge.

Mosaic addresses this by separating **conversation storage**, **semantic interpretation**, **knowledge management**, **cross-model handoff**, and **validated adaptation**. The system's persistent memory is independent of any one provider, so users can change models without losing their accumulated knowledge.

### 2.1 Core differentiator

Mosaic must go beyond:

- transcript storage;
- summarising a chat;
- comparing several model answers;
- copying a conversation into another provider;
- maintaining an unverified vector database of chat text.

Its distinguishing workflow is:

**conversation → source-grounded interpretation → connected knowledge → context-aware handoff → observed outcome → controlled evaluation → validated procedural update.**

### 2.2 What “learn from reasoning” means

Mosaic must not claim to inspect another model's hidden chain-of-thought, token-level computation, or private internal reasoning. Those are not reliably available through ordinary consumer chat interfaces, and generated explanations may not faithfully represent internal computation.

Instead, Mosaic extracts and evaluates observable behaviour in the conversation, such as:

- identifying objectives and constraints;
- decomposing a problem;
- generating alternatives;
- comparing trade-offs;
- searching for evidence;
- identifying assumptions and uncertainty;
- proposing counterexamples;
- testing or verifying a result;
- revising a previous answer after criticism;
- synthesising several contributions.

Each observation must be labelled as one of:

- `explicit`: directly stated or clearly shown in the transcript;
- `inferred`: a plausible interpretation derived from observable messages;
- `user_confirmed`: reviewed and confirmed by the user;
- `experiment_supported`: tested against an outcome;
- `disputed`: contradicted or insufficiently supported.

Mosaic records a **visible strategy and its outcome**, not a claim about what the external model internally thought.

---

## 3. Goals, non-goals, and release boundaries

### 3.1 Product goals

**G1 — Reliable conversation portability.** Import supported official exports and manually supplied conversations into a common format while preserving message order, roles, timestamps, branches where present, and provenance.

**G2 — High-quality semantic interpretation.** Extract knowledge, claims, assumptions, methods, decisions, outcomes, and open questions with traceable source spans.

**G3 — Connected personal knowledge.** Search and connect relevant information across many conversations without requiring the user to remember where it came from.

**G4 — Cross-model continuity.** Prepare concise, task-specific context packets for ordinary consumer chat interfaces; accept returned responses with explicit provider/model attribution.

**G5 — Evidence-gated adaptation.** Learn from explicit feedback and verified task outcomes; evaluate candidate procedures before promoting them.

**G6 — Independence and portability.** Keep canonical knowledge, source references, evaluation results, and procedures provider-independent and exportable.

**G7 — Lightweight operation.** Avoid mandatory cloud services, paid APIs, distributed infrastructure, and large vector databases.

### 3.2 Explicit non-goals for MVP

- Training or fine-tuning foundation models using third-party provider outputs.
- Claiming access to hidden chain-of-thought or internal model states.
- Unattended control of ChatGPT, Claude, Gemini, or other consumer websites.
- Scraping DOM content, reading full provider pages in the background, session-cookie access, or automated extraction from provider interfaces.
- Automatically submitting prompts or sending messages on the user's behalf.
- API-based model aggregation or model-provider billing integration.
- Autonomous execution of arbitrary imported code or shell commands.
- Self-modification of Mosaic's source code, security rules, permissions, or deployment configuration.
- Public crowdsourced knowledge, multi-user collaboration, cloud sync, and organisation-wide tenancy.
- Full multimodal understanding of images, audio, or video in the first release. Attachment metadata may be retained; text content is the MVP focus.
- A universal assistant for unconstrained tasks. The initial quality target is knowledge work that can be evaluated with observable criteria.

### 3.3 MVP scope

The MVP is complete when a user can:

1. Create a local workspace.
2. Import a supported ChatGPT, Claude, or Gemini archive (adapter compatibility is verified against fixture archives; unknown structures fail safely) or paste a transcript.
3. Review the import summary and processing errors.
4. Run deterministic parsing and local-LLM semantic analysis; request a user-mediated analysis packet for difficult cases.
5. Inspect a conversation report with linked knowledge, decisions, methods, uncertainties, and source messages.
6. Search across imported conversations and knowledge using SQLite full-text search plus metadata filters.
7. Create an objective and generate a context packet for a selected provider and collaboration role.
8. Copy the packet, open the provider's normal chat page, manually paste and submit it, then paste/import the response into Mosaic.
9. Compare contributions, record agreements/disagreements, and update knowledge with provenance.
10. Record explicit feedback and verified outcomes.
11. Run a bounded, non-arbitrary-code experiment on curated text/structured task fixtures; retain results and allow user approval or rejection of a candidate procedure.
12. Export the canonical data and delete selected source material with documented dependency handling.

### 3.4 Release sequencing

- **MVP 0.1:** Import, canonicalisation, semantic reports, source-linked knowledge, search, objectives, manual context packets, manual response intake, basic evaluation, export/delete.
- **MVP 0.2:** Browser companion with an outbound-only handoff panel; no provider-page access or automated sending.
- **MVP 0.3:** Strategy performance ledger, controlled experiments, and evidence-gated procedure promotion.
- **Post-MVP:** Optional semantic embeddings, local graph visualisation, encrypted backup UX, desktop packaging, richer attachment processing, and provider integrations only where authorised and justified.

---

## 4. Primary users and core journeys

### 4.1 Initial user

A single technically curious user who uses multiple consumer AI chat products, accumulates long conversations, wants to retain intellectual work across providers, and is willing to review important extractions and handoffs.

### 4.2 Journey A — Import and understand an archive

1. User selects an export ZIP/JSON file.
2. Mosaic detects archive type and provider adapter.
3. Mosaic displays provider, archive size, expected content types, policy status, and retention/storage estimate.
4. User confirms that they have the right to import the data and selects permitted uses (store, index, derive, transfer). Defaults are conservative.
5. Archive validator checks file count, compressed/uncompressed size, path traversal, file types, and parsing limits.
6. Adapter normalises conversations and messages.
7. User sees counts, skipped records, unknown fields, and parser warnings.
8. Analysis pipeline creates episodes and candidate knowledge.
9. Each extracted item links to one or more exact source messages.
10. User can correct, confirm, reject, or defer items.

### 4.3 Journey B — Use knowledge in a new AI conversation

1. User creates an objective and records required outcome, constraints, and known decisions.
2. Mosaic retrieves relevant personal/general knowledge and unresolved questions.
3. User chooses destination provider and role (e.g., independent proposal, critique, counterexample search, evidence check, synthesis).
4. Mosaic generates a context packet, displays source references and redactions, and estimates packet length.
5. User copies the packet and opens the provider's standard web application.
6. User pastes and submits manually.
7. User pastes the resulting response into Mosaic and selects provider/model metadata (unknown values remain unknown).
8. Mosaic compares new content with current knowledge and marks claims as new, supporting, conflicting, or redundant.
9. User reviews any material update.

### 4.4 Journey C — Investigate a methodology

1. User selects a candidate method or asks Mosaic to identify a repeated pattern.
2. Mosaic describes the method, observed source examples, preconditions, assumptions, and possible failure modes.
3. Mosaic proposes a falsifiable hypothesis and predicts measurable outcomes.
4. The user approves an experiment definition and benchmark set.
5. Baseline and candidate are evaluated on the same cases and evaluator version.
6. Results include failures, uncertainty, resource use, and limitations.
7. The candidate remains experimental until it passes the acceptance rule and any required user approval.
8. Promotion creates a new immutable procedure version; rollback restores the prior active version.

---

## 5. Functional requirements

Priority legend: **P0** required for MVP; **P1** required for the first complete product; **P2** post-MVP.

### 5.1 Import and canonicalisation

| ID | Priority | Requirement | Acceptance condition |
|---|---|---|---|
| IMP-01 | P0 | Import user-selected official export archives and standalone JSON/Markdown/text files | Supported fixtures import with stable IDs and accurate counts |
| IMP-02 | P0 | Provide adapters for ChatGPT, Claude, and Gemini export structures | Each adapter has versioned fixture tests; unknown schema is reported, not guessed |
| IMP-03 | P0 | Support manual paste as a generic conversation | User can assign provider, model, date, and speaker labels; unknowns allowed |
| IMP-04 | P0 | Preserve source artifact and hash | Original archive remains available until user deletes it |
| IMP-05 | P0 | Canonicalise roles, timestamps, message order, branching, and metadata | Round-trip tests preserve supported fields and report unsupported fields |
| IMP-06 | P0 | Detect duplicates | Identical source hashes are not re-imported silently; user can intentionally reprocess |
| IMP-07 | P0 | Enforce archive and resource limits | Zip bombs, path traversal, oversized entries, and unsupported files are safely rejected |
| IMP-08 | P0 | Display import provenance and warnings | User can inspect source filename, provider, parser version, import time, skipped counts |
| IMP-09 | P1 | Incremental import | New/changed conversations can be imported without duplicating unchanged content |
| IMP-10 | P2 | Attachment content extraction | Only after separate format, malware, and privacy evaluation |

Initial adapters target the documented export routes currently offered by the providers: ChatGPT data export; Claude Settings > Privacy export; Gemini Apps data through Google Takeout. The adapter contract must be fixture-driven because export schemas can change. Official export routes are documented by the providers: [ChatGPT export](https://help.openai.com/en/articles/7260999-how-do-i-export-my-chatgpt-history-and-data), [Claude export](https://support.anthropic.com/en/articles/9450526-how-can-i-export-my-claude-data), [Gemini Apps export](https://support.google.com/gemini/answer/16920332).

### 5.2 Semantic interpretation

| ID | Priority | Requirement | Acceptance condition |
|---|---|---|---|
| SEM-01 | P0 | Segment long conversations into coherent episodes | Each episode links to its member messages |
| SEM-02 | P0 | Extract concepts, claims, constraints, decisions, procedures, outcomes, and open questions | Output conforms to versioned Pydantic schemas |
| SEM-03 | P0 | Attach exact source message references and text spans | Every factual/claim item has evidence or is explicitly marked as hypothesis |
| SEM-04 | P0 | Distinguish explicit statements from inferred interpretations | UI displays provenance and interpretation type |
| SEM-05 | P0 | Extract observable strategy patterns without asserting hidden cognition | Strategy observations use the approved taxonomy and source links |
| SEM-06 | P0 | Preserve disagreements and unresolved issues | Contradictory items are linked, not silently merged |
| SEM-07 | P0 | Use deterministic parsing before LLM interpretation | Exact fields are not unnecessarily delegated to a model |
| SEM-08 | P0 | Use optional local inference for semantic extraction | Invalid model output is rejected or retried; raw output is never directly trusted |
| SEM-09 | P0 | Generate a structured analysis prompt for user-mediated assistance | Prompt includes scope, schema, source boundaries, and no hidden-CoT request |
| SEM-10 | P1 | Cross-conversation consolidation | Similar items are suggested for merge with source lineage preserved |
| SEM-11 | P1 | Knowledge contradiction detection | Conflicts are surfaced with comparison and source evidence |
| SEM-12 | P1 | Re-analysis with new pipeline version | Old extraction remains auditable; re-analysis is a new version |

### 5.3 Knowledge management and retrieval

| ID | Priority | Requirement | Acceptance condition |
|---|---|---|---|
| KNO-01 | P0 | Store knowledge items with type, status, scope, timestamps, and version | All accepted item types have typed fields or validated JSON properties |
| KNO-02 | P0 | Maintain evidence links to original messages and experiments | User can open source conversation at relevant message |
| KNO-03 | P0 | Support personal and general scopes | General-scope items cannot contain personal-only fields without a warning and explicit override |
| KNO-04 | P0 | Search messages and knowledge using FTS5 | Exact and phrase search returns source-linked results |
| KNO-05 | P0 | Filter by provider, date, model, project, item type, and status | Filters work in combination |
| KNO-06 | P0 | User correction, confirmation, rejection, and deprecation | Every material change is versioned and audited |
| KNO-07 | P0 | Export knowledge and provenance in portable JSON/Markdown | Export can be re-imported without losing IDs or source lineage |
| KNO-08 | P1 | Suggest semantic relationships across concepts and methods | Suggestions are reviewable; no silent graph mutation |
| KNO-09 | P1 | Optional embeddings | Only after retrieval benchmark shows material value over FTS5 + metadata |
| KNO-10 | P1 | Deletion dependency resolution | Source deletion invalidates/retracts dependent records according to policy |

### 5.4 Cross-model coordination

| ID | Priority | Requirement | Acceptance condition |
|---|---|---|---|
| COO-01 | P0 | Create objective records with outcome, constraints, requirements, and decisions | All handoffs bind to an objective version |
| COO-02 | P0 | Generate provider-neutral context packets | Packet includes objective, constraints, relevant knowledge, decisions, evidence, open questions, requested role |
| COO-03 | P0 | Provide handoff roles: independent solution, critique, adversarial review, evidence check, synthesis | Each role has a versioned packet template |
| COO-04 | P0 | User copies packet and manually submits it | No provider auto-submit or session access is required |
| COO-05 | P0 | User pastes/imports returned response | Response retains provider/model metadata when supplied |
| COO-06 | P0 | Support parallel and sequential workflows | Multiple sessions can contribute to one objective while retaining attribution |
| COO-07 | P0 | Show disagreement and evidence rather than majority-vote consensus | Unresolved conflicts remain visible |
| COO-08 | P1 | Thin browser companion | Outbound-only packet copy, open provider URL, and link to local workspace; no host-page access |
| COO-09 | P1 | Per-provider policy gate | Restricted transfer/derivation actions are disabled or require explicit policy review |
| COO-10 | P2 | Provider-authorised integrations | Only after provider terms and technical authorisation are reviewed |

### 5.5 Learning and experimentation

| ID | Priority | Requirement | Acceptance condition |
|---|---|---|---|
| LEA-01 | P0 | Record explicit feedback and verified task outcomes | Every learning signal records source, event type, and trust class |
| LEA-02 | P0 | Keep extracted items in candidate state by default | No model-generated item becomes trusted solely because it was generated |
| LEA-03 | P0 | Separate user preference from objective correctness | Preference signals do not change factual truth status |
| LEA-04 | P0 | Record model/strategy observations only with comparable task context | Provider/model/version, task type, evaluation method, sample count, outcome stored |
| LEA-05 | P1 | Generate experiment plans and falsifiable hypotheses | Plan names baseline, candidate, control variables, test cases, metrics, stopping rule |
| LEA-06 | P1 | Execute bounded experiments on safe structured/text fixtures | No arbitrary shell or imported-code execution in MVP |
| LEA-07 | P1 | Require held-out evaluation before promotion | Test split is protected from candidate development |
| LEA-08 | P1 | Promote and rollback versioned procedures | Active procedure has a recoverable prior version |
| LEA-09 | P1 | Detect regression | Protected benchmark reruns after a procedure update |
| LEA-10 | P2 | Automated low-risk promotion | Only after reliable calibration, security review, and user-configured thresholds |

### 5.6 User experience and governance

| ID | Priority | Requirement | Acceptance condition |
|---|---|---|---|
| UX-01 | P0 | Show processing status and errors | Import and analysis jobs expose progress and retryable errors |
| UX-02 | P0 | Preview context packet before copy | Exact outbound content is visible; sensitive content is highlighted |
| UX-03 | P0 | Allow pause, cancel, and retry of jobs | No partial job corrupts committed source data |
| UX-04 | P0 | Provide inspectable history of changes | Every knowledge promotion/retraction is traceable |
| UX-05 | P0 | Delete source, conversation, and derived items | Deletion semantics are clear and testable |
| UX-06 | P0 | Export a full portable backup | Backup includes database-consistent snapshot and source artifacts selected by user |
| UX-07 | P1 | Browser companion permission disclosure | Extension requests minimal permissions and explains each one |
| UX-08 | P1 | Storage and local-model resource monitor | User can set archive, storage, inference, and experiment limits |

---

## 6. Hybrid interpretation architecture

### 6.1 Three-stage interpretation path

**Stage A — deterministic processing**

Use code for operations with objectively defined answers:

- archive detection and safe extraction;
- schema parsing and structural normalisation;
- message ordering and speaker mapping;
- timestamp parsing;
- content hashing and duplicate detection;
- metadata extraction;
- text cleaning that preserves original source;
- segmentation hints such as headings, code blocks, and user-defined boundaries;
- exact evidence-span lookup;
- JSON schema validation and database constraints.

**Stage B — local semantic inference**

Use an optional local model for tasks requiring interpretation:

- episode summaries;
- concept and claim extraction;
- methodology reconstruction;
- explicit-versus-inferred classification;
- candidate relationship suggestions;
- contradiction candidates;
- context packet drafting.

Recommended initial local runtime: Ollama, behind a provider-neutral `LocalModelProvider` interface. Ollama documents schema-constrained structured outputs through its `format` parameter. Mosaic must still validate every result with Pydantic and verify source spans independently. Local model availability, hardware fit, and extraction quality are installation-specific and must be measured rather than assumed.

**Stage C — user-mediated high-capability analysis**

When a task is too difficult or local inference is unavailable/uncertain, Mosaic generates an analysis packet for the user to submit to an existing consumer AI interface. The request asks for concise structured findings, evidence spans, assumptions, and uncertainty. It must not ask the provider to reveal hidden chain-of-thought. The user returns the response manually; Mosaic treats it as an attributed, untrusted contribution until validated.

### 6.2 Inference routing rules

1. Deterministic parser first.
2. Local model for routine semantic extraction when enabled.
3. If the local model is unavailable, return a clear degraded mode; importing and search remain usable.
4. If the schema fails, allow one constrained repair attempt; then mark the item unresolved rather than guessing.
5. If the task requires higher-quality interpretation, prepare a user-mediated external analysis packet.
6. Do not silently transmit imported content to a cloud model.
7. Before any external handoff, show the exact content and destination.

### 6.3 Canonical extraction object

Every extracted record should carry:

- stable ID;
- item type;
- canonical statement;
- concise explanation;
- scope (`personal` or `general`);
- status (`candidate`, `user_confirmed`, `source_supported`, `experiment_supported`, `disputed`, `deprecated`);
- interpretation class (`explicit`, `inferred`, `user_confirmed`);
- source message IDs and exact evidence spans;
- assumptions and applicability conditions;
- counterevidence and limitations;
- extractor type and version;
- created and updated timestamps.

Do not present raw model confidence as calibrated probability. Use review statuses and evidence levels; numeric confidence can be used internally for queue prioritisation only until calibrated.

---

## 7. Semantic knowledge model

### 7.1 Knowledge item types

| Type | Definition | Example |
|---|---|---|
| `concept` | A domain concept or definition | Transaction isolation |
| `claim` | An assertion that may be supported or challenged | WAL permits concurrent readers and a writer |
| `constraint` | A requirement or boundary | The application must work without paid APIs |
| `decision` | A selected option with rationale and alternatives | Use SQLite for local persistence |
| `procedure` | A reusable sequence of steps | Inspect query plan before adding an index |
| `strategy_observation` | Observable approach used in a conversation | Constraint-first decomposition |
| `finding` | An outcome or evidence-backed observation | Candidate method passed 8 of 10 test cases |
| `preference` | A user-specific preference | Prefer local-first deployment |
| `outcome` | What happened after a task or experiment | Integration test passed after schema migration |
| `open_question` | Unresolved issue | How does this export variant represent branches? |

### 7.2 Strategy taxonomy

Initial controlled vocabulary:

- `objective_clarification`
- `constraint_extraction`
- `decomposition`
- `retrieval_and_evidence`
- `alternative_generation`
- `tradeoff_analysis`
- `assumption_identification`
- `adversarial_critique`
- `counterexample_search`
- `verification_and_testing`
- `iterative_refinement`
- `uncertainty_expression`
- `synthesis`

A strategy observation records which message sequence exhibits the behaviour, whether the label is explicit or inferred, the task context, and the observable result. It does not claim to reveal hidden model cognition.

### 7.3 Evidence model

Evidence records should distinguish:

- direct source quote/span;
- source paraphrase;
- user correction or confirmation;
- independent external reference;
- deterministic test result;
- experiment result;
- counterexample;
- model-generated rationale (unverified).

Evidence can support, challenge, qualify, or merely contextualise a knowledge item. One source repeated across multiple model outputs is not independent evidence.

### 7.4 Knowledge scopes

**Personal scope** includes user preferences, project decisions, private task context, and user-specific experience.

**General scope** means a candidate item is believed to be reusable beyond its originating task. Before promotion it must:

1. remove or generalise personal identifiers and project-specific secrets;
2. retain source provenance;
3. state preconditions and limitations;
4. have independent support or a reproducible experiment where applicable;
5. pass any provider-specific rights/policy gate;
6. be explicitly approved by the user in MVP.

General scope is still private to the user's local Mosaic installation. Sharing/publishing is out of scope.

### 7.5 Conflict handling

Mosaic must not overwrite conflicting claims. It should create a conflict relation with:

- each claim and its provenance;
- time/version context;
- scope and assumptions;
- type of conflict (direct contradiction, context-dependent difference, definition mismatch, version drift);
- resolution status (unresolved, qualified, resolved by evidence, resolved by user).

---

## 8. Cross-model coordination design

### 8.1 Coordination modes

- **Parallel exploration:** create distinct packets for multiple providers from the same objective version.
- **Sequential handoff:** a later provider receives the original objective plus selected findings, criticisms, and open questions from earlier contributions.
- **Adversarial critique:** ask a provider to identify assumptions, failure modes, and counterexamples.
- **Evidence verification:** ask a provider to assess claims and locate independent evidence; returned sources still require verification.
- **Synthesis:** prepare a packet that asks for a structured synthesis while preserving unresolved disagreement.

### 8.2 Context packet structure

A context packet must be versioned and contain, as applicable:

1. objective and expected output;
2. constraints and non-goals;
3. relevant user-approved preferences;
4. established decisions and their reasons;
5. relevant knowledge with source/evidence identifiers;
6. prior model contributions with provider attribution;
7. criticisms and unresolved conflicts;
8. explicit open questions;
9. requested role and output schema;
10. privacy/redaction notes.

Packets must be concise and task-specific. Do not paste an entire archive unless the user explicitly chooses to do so.

### 8.3 Contribution handling

Every returned contribution is a new source object. Mosaic should:

- retain raw response text;
- capture provider/model labels when user supplies them;
- compare claims to existing knowledge;
- detect duplicates and contradictions;
- attach new source evidence;
- avoid majority voting;
- show where models disagree;
- require review before changing a decision or promoting a method.

### 8.4 Browser companion boundary

The optional browser companion is an outbound handoff helper, not a browser automation agent.

Allowed MVP behaviour:

- open the Mosaic local UI;
- show a user-selected objective/context packet;
- copy the packet to the clipboard after an explicit user click;
- open a provider's public chat URL after an explicit user click;
- show handoff status and manual next steps.

Not allowed:

- content scripts reading provider DOM;
- background polling or scraping;
- reading conversation history from an open provider tab;
- reading session cookies or local storage;
- automatically entering or submitting prompts;
- automatic extraction of responses;
- bypassing provider protections or rate limits.

Responses are pasted/imported into Mosaic by the user. Browser extension permissions must be minimal and documented; no broad host permission is needed for this outbound-only design. Any future page interaction requires a separate provider-terms, browser-store-policy, privacy, and security review.

---

## 9. Self-learning and experimentation protocol

### 9.1 Learning signals

Use only explicit or independently verifiable signals for consequential adaptation:

- user correction;
- explicit user confirmation/rejection;
- deterministic test pass/fail;
- documented experiment result;
- repeated task outcome with comparable criteria;
- user-selected preference.

Do not treat silence, response length, or the fact that a conversation continued as proof that an answer was correct or useful.

### 9.2 Learning lifecycle

`observed → candidate → experimental → validated → active`

Alternative terminal/holding states: `rejected`, `inconclusive`, `disputed`, `superseded`, `withdrawn`.

A knowledge item and a procedure have separate status lifecycles. A factual claim may be source-supported while its proposed procedure remains untested.

### 9.3 Experiment contract

Every experiment must define:

- question and hypothesis;
- baseline and candidate procedure versions;
- controlled variables;
- test-case IDs and split;
- primary and secondary metrics;
- resource/time limits;
- stopping rule;
- evaluator version;
- expected failure modes;
- approval state;
- raw outputs and result summary.

The test set used to accept a candidate must not be the same set used to invent or tune it. Experiments should be reproducible from stored inputs, procedure versions, model/version metadata, and evaluator configuration.

### 9.4 MVP experiment safety

MVP experiments run on text and structured fixtures using deterministic evaluators and/or explicitly configured model-based grading. They do not execute arbitrary code from imported chats or documents. If a future release adds code execution, it must use a separate sandbox with no network, constrained filesystem, CPU/memory/time limits, and an independent security review.

### 9.5 Model/strategy performance ledger

Store observations in context: provider, model/version (unknown is permitted), task category, problem complexity, strategy, evaluation method, outcome, resource cost, and sample count.

Do not publish a single permanent provider ranking. Recommendations are conditional on comparable task types and sufficient sample size. Show uncertainty and sample count. Do not compare outputs from different model versions as though they were the same system.

### 9.6 Promotion gate

A candidate can become active only when:

1. all required evidence/source links exist;
2. the experiment plan was approved;
3. the candidate passes the held-out evaluation rule;
4. protected regression tests pass;
5. no critical safety or privacy issue is introduced;
6. a user approves promotion in MVP;
7. a rollback version is available.

---

## 10. System architecture

### 10.1 Architecture style

Use a **modular monolith** with one local backend process and one lightweight frontend. Modules have explicit interfaces and independent tests, but they do not become separate network services. A small persistent job table and one worker process handle import and analysis tasks. Add service separation only when measured workload requires it.

### 10.2 Proposed technology baseline

| Layer | Baseline | Rationale |
|---|---|---|
| Frontend | React + TypeScript + Vite | Mature, lightweight application UI |
| Backend | Python 3.12 + FastAPI | Strong parsing/AI ecosystem and clear API boundaries |
| Validation | Pydantic v2 | Typed input/output contracts |
| ORM/migrations | SQLAlchemy 2 + Alembic | Explicit schema evolution |
| Database | SQLite | Embedded local persistence |
| Search | SQLite FTS5 | Full-text search without a separate search server |
| Local inference | Ollama adapter (optional) | Local model serving; can be disabled |
| File storage | Local application data directory | Source archives stay on device |
| Unit/integration tests | pytest | Backend test suite |
| Frontend tests | Vitest + Testing Library | UI component and state testing |
| End-to-end tests | Playwright | Real user journey testing |
| Browser companion | Chrome/Chromium Manifest V3, later | Minimal outbound handoff helper |
| Desktop packaging | Tauri, later | Optional shell around the local app |

### 10.3 Storage design

- SQLite stores metadata, messages, knowledge, relationships, jobs, experiments, and audit events.
- FTS5 indexes message text, episode summaries, and knowledge text.
- Original archives and permitted attachments live in a managed local file store; the database stores relative paths and hashes.
- No vector database in MVP.
- Embeddings are an optional future index, not the canonical knowledge store.
- SQLite WAL mode is suitable for a local same-host application; it must not be placed on a network filesystem. Backups must use SQLite's backup mechanism or a quiesced consistent snapshot, not an unsafe copy of the main DB file while WAL writes are active.

### 10.4 Resource defaults (configurable)

Initial safety defaults for implementation, to be tuned from benchmark data:

- maximum compressed archive: 500 MiB;
- maximum expanded archive: 2 GiB;
- maximum entries: 50,000;
- maximum individual text message: 5 MiB;
- analysis concurrency: one local inference job by default;
- per-analysis context: chunked by episode, never whole-archive prompt stuffing;
- experiment wall-clock: 5 minutes per case by default;
- experiment cases: 50 per run by default;
- local storage warning: 1 GiB; user-configurable hard cap;
- no arbitrary network access or process execution from experiment inputs.

All limits must be configurable, surfaced in the UI, and enforced server-side. Archive limits are not security by themselves; parsing must also be streaming and resistant to decompression bombs.

### 10.5 Logical modules

1. `importers`: provider archive adapters and generic transcript parser.
2. `canonical`: conversation/message data contracts and validation.
3. `analysis`: episode segmentation, extraction schemas, local inference, assisted prompts.
4. `knowledge`: item repository, evidence, graph relations, merge/conflict workflow.
5. `retrieval`: FTS5 search, filters, context assembly.
6. `coordination`: objectives, sessions, context packets, response intake.
7. `learning`: feedback, strategy observations, experiments, promotion, rollback.
8. `policy`: provider-use settings, data scope, redaction, permissions.
9. `storage`: SQLite, file store, backups, deletion.
10. `jobs`: durable background job state and retries.
11. `audit`: append-only metadata event log (never raw sensitive message content).
12. `api`: versioned HTTP boundary for frontend and companion.

### 10.6 System diagram

See [`architecture/system.mmd`](architecture/system.mmd).

---

## 11. Data model and schema

The initial relational schema is provided in [`database/schema.sql`](database/schema.sql). The data dictionary is in [`database/data-dictionary.md`](database/data-dictionary.md).

Principal entities:

- `workspaces`
- `provider_policies`
- `source_artifacts`
- `conversations`
- `messages`
- `episodes` and `episode_messages`
- `knowledge_items`
- `knowledge_evidence`
- `knowledge_relations`
- `procedures` and `procedure_steps`
- `objectives`
- `coordination_sessions`
- `context_packets`
- `model_responses`
- `feedback_events`
- `benchmark_suites` and `benchmark_cases`
- `experiments` and `experiment_runs`
- `model_observations`
- `processing_jobs`
- `audit_events`

### 11.1 Key integrity rules

1. Every imported conversation belongs to one source artifact and workspace.
2. Every message belongs to a conversation; parent references must remain within the same conversation.
3. Every extracted claim/finding/method must have one or more evidence links or remain explicitly marked as an unsupported hypothesis.
4. Every procedure is linked to a knowledge item and has immutable versions.
5. Every response belongs to a coordination session and has provider attribution or an explicit `unknown` value.
6. Every context packet references one objective version and records the included knowledge IDs.
7. Every experiment records baseline, candidate, evaluator version, test set, and results.
8. Only approved learning transitions may set an item/procedure to active.
9. Personal and general knowledge are separate scopes; general scope does not imply public sharing.
10. Source deletion must trigger dependent-record review/retraction and must remove original content and associated indexes.

### 11.2 Deletion policy

When the user deletes a source artifact:

- remove its raw file and original message content;
- remove FTS entries and source-message references;
- identify derived knowledge supported only by that source;
- mark dependent knowledge as `withdrawn` or delete it according to user choice;
- preserve an audit event containing only a minimal tombstone (entity ID, operation, timestamp), not the deleted content;
- keep a derived item only if it has independent provenance or the user explicitly re-enters/confirms it from another lawful source.

Deletion behaviour must be tested for backups, exports, indexes, caches, and context packets. Context packets copied outside Mosaic cannot be recalled by the application; the UI must state that limitation.

---

## 12. API boundary (local only)

The frontend talks to a local FastAPI service. The initial API is versioned under `/api/v1`.

Representative routes:

| Method | Route | Purpose |
|---|---|---|
| POST | `/imports` | Submit a user-selected archive/file |
| GET | `/imports/{id}` | Import status and warnings |
| POST | `/imports/{id}/cancel` | Cancel a queued/running import |
| GET | `/conversations` | List/search canonical conversations |
| GET | `/conversations/{id}` | Read conversation and messages |
| POST | `/conversations/{id}/analyze` | Queue semantic analysis |
| GET | `/knowledge` | Search/filter knowledge items |
| GET | `/knowledge/{id}` | Read item, evidence, and relationships |
| PATCH | `/knowledge/{id}` | User correction or status transition |
| POST | `/objectives` | Create objective |
| POST | `/objectives/{id}/packets` | Generate context packet |
| GET | `/packets/{id}` | Preview/copy packet |
| POST | `/sessions/{id}/responses` | Ingest user-pasted response |
| POST | `/feedback` | Record explicit feedback |
| POST | `/experiments` | Create experiment plan |
| POST | `/experiments/{id}/approve` | Approve bounded execution |
| GET | `/experiments/{id}` | Read status and results |
| POST | `/exports` | Create user-selected export/backup |
| DELETE | `/sources/{id}` | Delete source with dependency handling |

No route proxies a provider's chat endpoint or accesses an authenticated browser session.

---

## 13. Privacy, policy, and provider compatibility

### 13.1 Data ownership and consent

The user must confirm that they have the rights and permissions needed to import and process each archive. A conversation may contain information about other people, confidential work, or data subject to organisational retention policies. Mosaic must not assume that account access alone means every content item can be reused or transferred.

### 13.2 Provider policy registry

Provider policies can change. Maintain a versioned registry with:

- provider and applicable product;
- terms/policy URL;
- review date and reviewer;
- allowed/unclear/prohibited statuses for storage, indexing, derived knowledge, strategy analysis, cross-provider transfer, and model training;
- notes and evidence;
- feature gates.

Conservative defaults: `unreviewed` means no derived learning or external transfer. Users may still use generic/manual content only where they have rights and permissions. Provider-specific permissions must be reviewed before enabling adapter features.

### 13.3 OpenAI-specific compliance risk

The current OpenAI Terms of Use applicable outside the EEA/UK/Switzerland state that users may not automatically or programmatically extract data or Output, and may not use Output to develop models that compete with OpenAI. The MVP therefore excludes browser scraping and use of imported provider outputs to train/fine-tune a foundation model. The permissibility of a particular personal knowledge-management, indexing, strategy-analysis, or cross-provider transfer feature must be assessed; this specification does not provide legal advice or assume that external-memory/RAG is automatically exempt.

Before distributing Mosaic, obtain a provider-by-provider legal/policy review. If a provider's terms prohibit a proposed derived-learning or transfer operation, disable that operation for that provider. The user-mediated export/import path is not a substitute for legal review.

### 13.4 No hidden chain-of-thought extraction

Mosaic requests concise, evidence-linked explanations and observable procedures. It does not solicit private chain-of-thought, hidden system prompts, or internal model state. A provider's written rationale is treated as an output, not as proof of its actual internal reasoning.

### 13.5 External handoff controls

Before a packet is copied for external use:

- display destination provider;
- show full packet content;
- show source artifacts included;
- detect likely secrets and personal data;
- allow item-by-item removal;
- make cross-provider transfer an explicit user action;
- do not send anything over a network automatically.

---

## 14. Non-functional requirements

| Area | Requirement |
|---|---|
| Reliability | Interrupted imports/analysis jobs resume or fail safely without corrupting committed data |
| Performance | Search should return quickly on a local archive of 100,000 messages; benchmark on reference hardware before making a release claim |
| Scalability | Process archives incrementally by file/conversation/episode; never require whole-history prompts |
| Portability | Export canonical records, evidence, and relationships in documented open formats |
| Observability | Local logs record job IDs, durations, parser/model versions, and error classes without storing unnecessary raw content |
| Privacy | No cloud telemetry by default; no external inference unless user-mediated and explicitly approved |
| Security | Imported content is untrusted data; no code execution from transcripts; least privilege for the extension |
| Maintainability | Modular package boundaries and explicit interfaces; migrations for all schema changes |
| Reproducibility | Store prompt/schema/evaluator versions and experiment settings |
| Accessibility | Keyboard-operable primary flows, visible focus, readable status/error labels |
| Windows support | First-class PowerShell startup scripts and paths; no requirement for WSL or Docker in MVP |
| Cost | No mandatory paid API, subscription, or hosted infrastructure |

---

## 15. Observability and operational behaviour

Every import, analysis, handoff, and experiment should have a durable job/event record with:

- ID and operation type;
- start/end timestamps;
- status and retry count;
- input artifact IDs (not copied content);
- parser/extractor/evaluator versions;
- local model name/version when used;
- warnings and safe error details;
- resource usage when available.

Logs must not contain full conversation content, secrets, or complete context packets by default. A user can export a diagnostic bundle with explicit preview and redaction.

The application should function in degraded modes:

- no local LLM: archive import, parsing, search, manual analysis packets, and handoffs still work;
- no internet: local library, local inference (if installed), and manual text workflows still work;
- provider format changes: archive is retained, parser reports unsupported fields/version, and no silent partial import is reported as complete;
- local model malformed output: validate, retry once, then create a review task;
- storage limit reached: stop before writing partial derived state and present cleanup options.

---

## 16. Definition of Done

A feature is not complete when its UI appears to work. It is complete only when:

1. acceptance criteria are implemented;
2. unit tests cover normal and boundary cases;
3. integration tests cover persistence and module boundaries;
4. application tests cover the user workflow;
5. security/privacy tests cover relevant abuse cases;
6. database migration and rollback behaviour are tested;
7. errors are visible and recoverable;
8. documentation is updated;
9. no placeholder or mock behaviour is represented as production behaviour;
10. the implementation is reviewed for data-loss, policy, and permission implications.

---

## 17. Open risks and decisions to validate before coding

| Risk / question | Why it matters | Required action |
|---|---|---|
| Provider terms on indexing/deriving/transfer | Can constrain central product functionality | Complete provider-specific legal/policy review; enforce feature flags |
| Export format drift | Import adapters can break silently | Build real fixtures, parser version detection, unknown-field report |
| Local model quality | Poor extraction contaminates knowledge | Benchmark multiple local models on a fixed annotated corpus |
| Large archive processing | Memory/time spikes | Streaming extraction, chunked jobs, archive quotas |
| Strategy reconstruction | Written explanations can be post-hoc or inaccurate | Label explicit/inferred; measure against source-visible actions; never claim hidden cognition |
| False agreement | Models can share errors or sources | Preserve independent evidence and disagreement; no majority-vote truth |
| Knowledge poisoning | Malicious text can manipulate analysis | Treat content as data; isolate prompts; candidate status by default |
| Browser companion policy | Overreach may violate provider/store terms | Outbound-only, no host-page access in MVP |
| Deletion of derived data | Source deletion can leave hidden derivatives | Dependency graph, tombstones without payload, deletion tests |
| General knowledge contamination | Personal/private facts may be over-generalised | Explicit scope review, privacy scrub, source lineage |

---

## 18. Release gates

### Gate A — Import correctness

- Supported fixtures parse with no lost messages or role misclassification.
- Unknown formats fail visibly and preserve the original archive.
- Archive security tests pass.

### Gate B — Semantic reliability

- All factual claims have valid evidence references or are labelled as hypotheses.
- Key objectives and constraints are preserved.
- Strategy observations distinguish explicit from inferred.
- Human review confirms that extraction is useful and not misleading.

### Gate C — Handoff integrity

- Context packets preserve objective, constraints, decisions, and unresolved questions.
- Provider/model attribution is retained on returned responses.
- No automatic provider interaction occurs.
- Cross-provider content transfer is policy-gated and user-approved.

### Gate D — Learning validity

- Candidate procedures are evaluated on a held-out test set.
- Candidate improvements do not cause critical regressions.
- The evidence trail and rollback work.
- No unverified model-generated knowledge is automatically promoted.

### Gate E — Security and privacy

- Prompt injection, archive abuse, secret leakage, cross-scope leakage, deletion, and extension-permission tests pass.
- Provider policy registry is reviewed for each enabled provider.
- No mandatory outbound telemetry or cloud model calls exist.

---

## 19. Recommended first vertical slice

The first implementation slice should be deliberately narrow:

**Import one ChatGPT export fixture → canonicalise messages → analyse one conversation → extract five typed knowledge items with exact message citations → display the report → edit/confirm one item → search and retrieve it after application restart.**

Do not begin with all three adapters, a knowledge graph visualisation, a browser extension, autonomous experiments, or multi-model UI. Prove the end-to-end data contract and evidence integrity first. Then add the Claude and Gemini adapters using the same interface.

The product's core technical risk is semantic quality and provenance, not the number of providers connected.

---

## 20. Reference material

These sources inform the proposed compatibility, storage, structured-output, and security choices. They must be checked again during implementation and before each release because provider policies and export formats can change.

1. OpenAI Terms of Use (Rest of World), effective 1 January 2026: <https://openai.com/policies/row-terms-of-use/>.
2. OpenAI ChatGPT data export instructions: <https://help.openai.com/en/articles/7260999-how-do-i-export-my-chatgpt-history-and-data>.
3. Anthropic Claude data export instructions: <https://support.anthropic.com/en/articles/9450526-how-can-i-export-my-claude-data>.
4. Google Gemini Apps data export instructions: <https://support.google.com/gemini/answer/16920332>.
5. Ollama structured outputs: <https://docs.ollama.com/capabilities/structured-outputs>.
6. SQLite FTS5: <https://www.sqlite.org/fts5.html>.
7. SQLite Write-Ahead Logging: <https://www.sqlite.org/wal.html>.
8. OWASP GenAI Security — Prompt Injection: <https://genai.owasp.org/llmrisk/llm01-prompt-injection/>.
9. OWASP GenAI Security — Excessive Agency: <https://genai.owasp.org/llmrisk2023-24/llm08-excessive-agency/>.

---

**Specification authority:** This file is the product-level source of truth. Supporting schema, architecture, threat model, benchmark plan, and backlog documents must remain consistent with it. Any change to a P0 requirement, provider-policy boundary, knowledge lifecycle, or promotion gate requires an Architecture Decision Record (ADR) and corresponding test updates.