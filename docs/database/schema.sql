-- Reference snapshot: apply versioned files in migrations/ in lexical order.
-- Mosaic initial SQLite schema (MVP baseline)
-- Apply this versioned SQL migration through Mosaic migration runner.
PRAGMA foreign_keys = ON;
PRAGMA journal_mode = WAL;

CREATE TABLE IF NOT EXISTS workspaces (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    default_scope TEXT NOT NULL DEFAULT 'personal' CHECK (default_scope IN ('personal','general')),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS provider_policies (
    id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    provider TEXT NOT NULL,
    product TEXT NOT NULL DEFAULT 'consumer_chat',
    policy_url TEXT,
    reviewed_at TEXT,
    reviewed_by TEXT,
    policy_version TEXT,
    policy_status TEXT NOT NULL DEFAULT 'unreviewed'
        CHECK (policy_status IN ('unreviewed','allowed_with_conditions','restricted','prohibited')),
    allow_store INTEGER NOT NULL DEFAULT 0 CHECK (allow_store IN (0,1)),
    allow_index INTEGER NOT NULL DEFAULT 0 CHECK (allow_index IN (0,1)),
    allow_derive INTEGER NOT NULL DEFAULT 0 CHECK (allow_derive IN (0,1)),
    allow_strategy_analysis INTEGER NOT NULL DEFAULT 0 CHECK (allow_strategy_analysis IN (0,1)),
    allow_cross_provider_transfer INTEGER NOT NULL DEFAULT 0 CHECK (allow_cross_provider_transfer IN (0,1)),
    allow_model_training INTEGER NOT NULL DEFAULT 0 CHECK (allow_model_training IN (0,1)),
    notes TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(workspace_id, provider, product)
);

CREATE TABLE IF NOT EXISTS source_artifacts (
    id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    provider TEXT NOT NULL DEFAULT 'manual',
    source_type TEXT NOT NULL CHECK (source_type IN ('archive','json','markdown','text','clipboard','other')),
    original_filename TEXT,
    storage_relpath TEXT,
    sha256 TEXT,
    byte_size INTEGER NOT NULL DEFAULT 0 CHECK (byte_size >= 0),
    mime_type TEXT,
    imported_at TEXT NOT NULL,
    source_created_at TEXT,
    parser_name TEXT,
    parser_version TEXT,
    parse_status TEXT NOT NULL DEFAULT 'pending'
        CHECK (parse_status IN ('pending','processing','complete','partial','failed','deleted')),
    policy_status TEXT NOT NULL DEFAULT 'unreviewed'
        CHECK (policy_status IN ('unreviewed','approved','restricted','rejected')),
    retention_state TEXT NOT NULL DEFAULT 'retain'
        CHECK (retention_state IN ('retain','delete_requested','deleted')),
    metadata_json TEXT NOT NULL DEFAULT '{}' CHECK (json_valid(metadata_json)),
    UNIQUE(workspace_id, sha256)
);

CREATE TABLE IF NOT EXISTS conversations (
    id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    source_artifact_id TEXT REFERENCES source_artifacts(id) ON DELETE SET NULL,
    provider TEXT NOT NULL DEFAULT 'unknown',
    provider_conversation_id TEXT,
    title TEXT NOT NULL DEFAULT 'Untitled conversation',
    started_at TEXT,
    ended_at TEXT,
    imported_at TEXT NOT NULL,
    content_hash TEXT,
    metadata_json TEXT NOT NULL DEFAULT '{}' CHECK (json_valid(metadata_json)),
    UNIQUE(source_artifact_id, provider_conversation_id)
);

CREATE TABLE IF NOT EXISTS messages (
    id TEXT PRIMARY KEY,
    conversation_id TEXT NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    provider_message_id TEXT,
    parent_message_id TEXT REFERENCES messages(id) ON DELETE SET NULL,
    sequence_no INTEGER NOT NULL CHECK (sequence_no >= 0),
    role TEXT NOT NULL CHECK (role IN ('system','developer','user','assistant','tool','unknown')),
    author_label TEXT,
    model_label TEXT,
    created_at TEXT,
    content_text TEXT NOT NULL DEFAULT '',
    content_hash TEXT,
    modality TEXT NOT NULL DEFAULT 'text',
    visibility TEXT NOT NULL DEFAULT 'normal' CHECK (visibility IN ('normal','hidden_metadata','redacted')),
    metadata_json TEXT NOT NULL DEFAULT '{}' CHECK (json_valid(metadata_json)),
    UNIQUE(conversation_id, sequence_no)
);
CREATE INDEX IF NOT EXISTS idx_messages_conversation ON messages(conversation_id, sequence_no);
CREATE INDEX IF NOT EXISTS idx_messages_parent ON messages(parent_message_id);

CREATE TABLE IF NOT EXISTS episodes (
    id TEXT PRIMARY KEY,
    conversation_id TEXT NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    episode_type TEXT NOT NULL DEFAULT 'discussion',
    summary TEXT NOT NULL DEFAULT '',
    start_sequence INTEGER NOT NULL,
    end_sequence INTEGER NOT NULL,
    extraction_version TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'candidate'
        CHECK (status IN ('candidate','reviewed','rejected','superseded')),
    metadata_json TEXT NOT NULL DEFAULT '{}' CHECK (json_valid(metadata_json)),
    created_at TEXT NOT NULL,
    CHECK (end_sequence >= start_sequence)
);
CREATE INDEX IF NOT EXISTS idx_episodes_conversation ON episodes(conversation_id, start_sequence);

CREATE TABLE IF NOT EXISTS episode_messages (
    episode_id TEXT NOT NULL REFERENCES episodes(id) ON DELETE CASCADE,
    message_id TEXT NOT NULL REFERENCES messages(id) ON DELETE CASCADE,
    position INTEGER NOT NULL,
    PRIMARY KEY (episode_id, message_id),
    UNIQUE (episode_id, position)
);

CREATE TABLE IF NOT EXISTS knowledge_items (
    id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    kind TEXT NOT NULL CHECK (kind IN (
        'concept','claim','constraint','decision','procedure','strategy_observation',
        'finding','preference','outcome','open_question'
    )),
    scope TEXT NOT NULL DEFAULT 'personal' CHECK (scope IN ('personal','general')),
    canonical_text TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT 'candidate' CHECK (status IN (
        'candidate','user_confirmed','source_supported','experiment_supported',
        'active','disputed','rejected','deprecated','withdrawn'
    )),
    interpretation_class TEXT NOT NULL DEFAULT 'inferred'
        CHECK (interpretation_class IN ('explicit','inferred','user_confirmed')),
    support_level TEXT NOT NULL DEFAULT 'unassessed'
        CHECK (support_level IN ('unassessed','low','moderate','strong','conflicting')),
    extractor_name TEXT,
    extractor_version TEXT,
    version INTEGER NOT NULL DEFAULT 1 CHECK (version >= 1),
    properties_json TEXT NOT NULL DEFAULT '{}' CHECK (json_valid(properties_json)),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    supersedes_id TEXT REFERENCES knowledge_items(id) ON DELETE SET NULL
);
CREATE INDEX IF NOT EXISTS idx_knowledge_scope_status ON knowledge_items(workspace_id, scope, status, kind);

CREATE TABLE IF NOT EXISTS knowledge_evidence (
    id TEXT PRIMARY KEY,
    knowledge_item_id TEXT NOT NULL REFERENCES knowledge_items(id) ON DELETE CASCADE,
    evidence_type TEXT NOT NULL CHECK (evidence_type IN (
        'direct_quote','source_paraphrase','user_confirmation','user_correction',
        'external_reference','deterministic_test','experiment_result','counterexample',
        'model_rationale_unverified'
    )),
    stance TEXT NOT NULL CHECK (stance IN ('supports','challenges','qualifies','context_only')),
    source_artifact_id TEXT REFERENCES source_artifacts(id) ON DELETE SET NULL,
    conversation_id TEXT REFERENCES conversations(id) ON DELETE SET NULL,
    message_id TEXT REFERENCES messages(id) ON DELETE SET NULL,
    experiment_run_id TEXT,
    external_reference TEXT,
    exact_span TEXT,
    note TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    CHECK (
        source_artifact_id IS NOT NULL OR message_id IS NOT NULL OR
        experiment_run_id IS NOT NULL OR external_reference IS NOT NULL
    )
);
CREATE INDEX IF NOT EXISTS idx_evidence_item ON knowledge_evidence(knowledge_item_id);
CREATE INDEX IF NOT EXISTS idx_evidence_message ON knowledge_evidence(message_id);

CREATE TABLE IF NOT EXISTS knowledge_relations (
    id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    from_item_id TEXT NOT NULL REFERENCES knowledge_items(id) ON DELETE CASCADE,
    to_item_id TEXT NOT NULL REFERENCES knowledge_items(id) ON DELETE CASCADE,
    relation_type TEXT NOT NULL CHECK (relation_type IN (
        'related_to','supports','contradicts','qualifies','depends_on','derived_from',
        'applies_to','instance_of','supersedes','alternative_to'
    )),
    status TEXT NOT NULL DEFAULT 'candidate' CHECK (status IN ('candidate','confirmed','rejected')),
    evidence_json TEXT NOT NULL DEFAULT '{}' CHECK (json_valid(evidence_json)),
    created_at TEXT NOT NULL,
    CHECK (from_item_id <> to_item_id),
    UNIQUE(from_item_id, to_item_id, relation_type)
);

CREATE TABLE IF NOT EXISTS procedures (
    id TEXT PRIMARY KEY,
    knowledge_item_id TEXT NOT NULL REFERENCES knowledge_items(id) ON DELETE CASCADE,
    procedure_key TEXT NOT NULL,
    version INTEGER NOT NULL DEFAULT 1,
    objective TEXT NOT NULL,
    preconditions_json TEXT NOT NULL DEFAULT '[]' CHECK (json_valid(preconditions_json)),
    applicability_json TEXT NOT NULL DEFAULT '{}' CHECK (json_valid(applicability_json)),
    failure_modes_json TEXT NOT NULL DEFAULT '[]' CHECK (json_valid(failure_modes_json)),
    evaluation_summary_json TEXT NOT NULL DEFAULT '{}' CHECK (json_valid(evaluation_summary_json)),
    status TEXT NOT NULL DEFAULT 'candidate'
        CHECK (status IN ('candidate','experimental','validated','active','rejected','superseded','withdrawn')),
    created_at TEXT NOT NULL,
    UNIQUE(procedure_key, version)
);

CREATE TABLE IF NOT EXISTS procedure_steps (
    id TEXT PRIMARY KEY,
    procedure_id TEXT NOT NULL REFERENCES procedures(id) ON DELETE CASCADE,
    step_no INTEGER NOT NULL CHECK (step_no >= 1),
    instruction TEXT NOT NULL,
    expected_observation TEXT NOT NULL DEFAULT '',
    failure_condition TEXT NOT NULL DEFAULT '',
    UNIQUE(procedure_id, step_no)
);

CREATE TABLE IF NOT EXISTS objectives (
    id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    objective_text TEXT NOT NULL,
    expected_output TEXT NOT NULL DEFAULT '',
    constraints_json TEXT NOT NULL DEFAULT '[]' CHECK (json_valid(constraints_json)),
    non_goals_json TEXT NOT NULL DEFAULT '[]' CHECK (json_valid(non_goals_json)),
    decisions_json TEXT NOT NULL DEFAULT '[]' CHECK (json_valid(decisions_json)),
    status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active','paused','completed','archived')),
    version INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS coordination_sessions (
    id TEXT PRIMARY KEY,
    objective_id TEXT NOT NULL REFERENCES objectives(id) ON DELETE CASCADE,
    provider TEXT NOT NULL DEFAULT 'unknown',
    model_label TEXT NOT NULL DEFAULT 'unknown',
    model_version TEXT NOT NULL DEFAULT 'unknown',
    coordination_mode TEXT NOT NULL CHECK (coordination_mode IN ('parallel','sequential','adversarial','evidence_check','synthesis','independent')),
    requested_role TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'prepared' CHECK (status IN ('prepared','handed_off','response_received','analysed','closed','cancelled')),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS context_packets (
    id TEXT PRIMARY KEY,
    objective_id TEXT NOT NULL REFERENCES objectives(id) ON DELETE CASCADE,
    session_id TEXT REFERENCES coordination_sessions(id) ON DELETE SET NULL,
    packet_version INTEGER NOT NULL DEFAULT 1,
    destination_provider TEXT NOT NULL DEFAULT 'unknown',
    purpose TEXT NOT NULL,
    body_text TEXT NOT NULL,
    included_item_ids_json TEXT NOT NULL DEFAULT '[]' CHECK (json_valid(included_item_ids_json)),
    redaction_report_json TEXT NOT NULL DEFAULT '{}' CHECK (json_valid(redaction_report_json)),
    content_hash TEXT NOT NULL,
    created_at TEXT NOT NULL,
    UNIQUE(objective_id, packet_version)
);

CREATE TABLE IF NOT EXISTS model_responses (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL REFERENCES coordination_sessions(id) ON DELETE CASCADE,
    source_message_id TEXT REFERENCES messages(id) ON DELETE SET NULL,
    response_text TEXT NOT NULL,
    provider TEXT NOT NULL DEFAULT 'unknown',
    model_label TEXT NOT NULL DEFAULT 'unknown',
    model_version TEXT NOT NULL DEFAULT 'unknown',
    received_at TEXT NOT NULL,
    metadata_json TEXT NOT NULL DEFAULT '{}' CHECK (json_valid(metadata_json))
);

CREATE TABLE IF NOT EXISTS feedback_events (
    id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    target_type TEXT NOT NULL CHECK (target_type IN ('message','knowledge_item','procedure','objective','response','experiment')),
    target_id TEXT NOT NULL,
    feedback_type TEXT NOT NULL CHECK (feedback_type IN (
        'confirm','reject','correct','useful','not_useful','task_pass','task_fail',
        'preference','withdraw','other'
    )),
    explicit INTEGER NOT NULL DEFAULT 1 CHECK (explicit IN (0,1)),
    details TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS benchmark_suites (
    id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    version TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    split_policy TEXT NOT NULL DEFAULT 'conversation_level',
    created_at TEXT NOT NULL,
    UNIQUE(workspace_id, name, version)
);

CREATE TABLE IF NOT EXISTS benchmark_cases (
    id TEXT PRIMARY KEY,
    suite_id TEXT NOT NULL REFERENCES benchmark_suites(id) ON DELETE CASCADE,
    case_key TEXT NOT NULL,
    category TEXT NOT NULL,
    input_json TEXT NOT NULL CHECK (json_valid(input_json)),
    expected_json TEXT NOT NULL CHECK (json_valid(expected_json)),
    split TEXT NOT NULL CHECK (split IN ('development','validation','holdout','regression')),
    sensitivity TEXT NOT NULL DEFAULT 'synthetic' CHECK (sensitivity IN ('synthetic','redacted_user_data','public')),
    created_at TEXT NOT NULL,
    UNIQUE(suite_id, case_key)
);

CREATE TABLE IF NOT EXISTS experiments (
    id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    target_knowledge_item_id TEXT REFERENCES knowledge_items(id) ON DELETE SET NULL,
    title TEXT NOT NULL,
    hypothesis TEXT NOT NULL,
    baseline_procedure_id TEXT REFERENCES procedures(id) ON DELETE SET NULL,
    candidate_procedure_id TEXT REFERENCES procedures(id) ON DELETE SET NULL,
    benchmark_suite_id TEXT REFERENCES benchmark_suites(id) ON DELETE SET NULL,
    protocol_json TEXT NOT NULL CHECK (json_valid(protocol_json)),
    primary_metric TEXT NOT NULL,
    evaluator_version TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'proposed'
        CHECK (status IN ('proposed','approved','running','completed','aborted','inconclusive','rejected')),
    promotion_state TEXT NOT NULL DEFAULT 'not_eligible'
        CHECK (promotion_state IN ('not_eligible','eligible','approved','rejected','rolled_back')),
    approved_at TEXT,
    started_at TEXT,
    completed_at TEXT,
    result_summary_json TEXT NOT NULL DEFAULT '{}' CHECK (json_valid(result_summary_json)),
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS experiment_runs (
    id TEXT PRIMARY KEY,
    experiment_id TEXT NOT NULL REFERENCES experiments(id) ON DELETE CASCADE,
    benchmark_case_id TEXT REFERENCES benchmark_cases(id) ON DELETE SET NULL,
    procedure_id TEXT REFERENCES procedures(id) ON DELETE SET NULL,
    run_no INTEGER NOT NULL DEFAULT 1,
    outcome TEXT NOT NULL CHECK (outcome IN ('pass','fail','partial','error','skipped')),
    score REAL,
    duration_ms INTEGER CHECK (duration_ms IS NULL OR duration_ms >= 0),
    resource_json TEXT NOT NULL DEFAULT '{}' CHECK (json_valid(resource_json)),
    result_json TEXT NOT NULL DEFAULT '{}' CHECK (json_valid(result_json)),
    error_class TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS model_observations (
    id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    provider TEXT NOT NULL,
    model_label TEXT NOT NULL DEFAULT 'unknown',
    model_version TEXT NOT NULL DEFAULT 'unknown',
    task_category TEXT NOT NULL,
    complexity_label TEXT NOT NULL DEFAULT 'unknown',
    strategy_labels_json TEXT NOT NULL DEFAULT '[]' CHECK (json_valid(strategy_labels_json)),
    evaluation_method TEXT NOT NULL,
    outcome TEXT NOT NULL CHECK (outcome IN ('success','partial','failure','unverified')),
    score REAL,
    resource_json TEXT NOT NULL DEFAULT '{}' CHECK (json_valid(resource_json)),
    evidence_json TEXT NOT NULL DEFAULT '{}' CHECK (json_valid(evidence_json)),
    observed_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS processing_jobs (
    id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    job_type TEXT NOT NULL,
    entity_id TEXT,
    status TEXT NOT NULL DEFAULT 'queued' CHECK (status IN ('queued','running','completed','failed','cancelled')),
    progress REAL NOT NULL DEFAULT 0 CHECK (progress >= 0 AND progress <= 1),
    attempts INTEGER NOT NULL DEFAULT 0,
    max_attempts INTEGER NOT NULL DEFAULT 2,
    error_code TEXT,
    error_message_safe TEXT,
    payload_json TEXT NOT NULL DEFAULT '{}' CHECK (json_valid(payload_json)),
    created_at TEXT NOT NULL,
    started_at TEXT,
    updated_at TEXT NOT NULL,
    completed_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_jobs_status_created ON processing_jobs(status, created_at);

CREATE TABLE IF NOT EXISTS audit_events (
    id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    actor TEXT NOT NULL DEFAULT 'user',
    action TEXT NOT NULL,
    entity_type TEXT NOT NULL,
    entity_id TEXT NOT NULL,
    details_json TEXT NOT NULL DEFAULT '{}' CHECK (json_valid(details_json)),
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_audit_entity ON audit_events(entity_type, entity_id, created_at);

-- Policy-aware full-text indexes. FTS content is stored separately so entries can
-- be removed when the user disables indexing for a provider.
CREATE VIRTUAL TABLE IF NOT EXISTS messages_fts USING fts5(
    message_id UNINDEXED,
    conversation_id UNINDEXED,
    content_text,
    tokenize='unicode61'
);

CREATE TRIGGER IF NOT EXISTS messages_ai AFTER INSERT ON messages
WHEN EXISTS (
    SELECT 1 FROM conversations c
    JOIN provider_policies p ON p.workspace_id=c.workspace_id AND p.provider=c.provider
    WHERE c.id=new.conversation_id AND p.allow_index=1
)
BEGIN
    INSERT INTO messages_fts(message_id,conversation_id,content_text)
    VALUES (new.id,new.conversation_id,new.content_text);
END;
CREATE TRIGGER IF NOT EXISTS messages_ad AFTER DELETE ON messages BEGIN
    DELETE FROM messages_fts WHERE message_id=old.id;
END;
CREATE TRIGGER IF NOT EXISTS messages_au AFTER UPDATE OF content_text ON messages BEGIN
    DELETE FROM messages_fts WHERE message_id=old.id;
    INSERT INTO messages_fts(message_id,conversation_id,content_text)
    SELECT new.id,new.conversation_id,new.content_text
    WHERE EXISTS (
        SELECT 1 FROM conversations c
        JOIN provider_policies p ON p.workspace_id=c.workspace_id AND p.provider=c.provider
        WHERE c.id=new.conversation_id AND p.allow_index=1
    );
END;

CREATE VIRTUAL TABLE IF NOT EXISTS knowledge_fts USING fts5(
    knowledge_item_id UNINDEXED,
    canonical_text,
    description,
    tokenize='unicode61'
);

CREATE TRIGGER IF NOT EXISTS knowledge_evidence_ai AFTER INSERT ON knowledge_evidence BEGIN
    DELETE FROM knowledge_fts WHERE knowledge_item_id=new.knowledge_item_id;
    INSERT INTO knowledge_fts(knowledge_item_id,canonical_text,description)
    SELECT k.id,k.canonical_text,k.description
    FROM knowledge_items k
    WHERE k.id=new.knowledge_item_id
      AND EXISTS (
          SELECT 1 FROM knowledge_evidence e
          JOIN conversations c ON c.id=e.conversation_id
          JOIN provider_policies p ON p.workspace_id=c.workspace_id AND p.provider=c.provider
          WHERE e.knowledge_item_id=k.id AND p.allow_index=1
      )
      AND NOT EXISTS (
          SELECT 1 FROM knowledge_evidence e
          JOIN conversations c ON c.id=e.conversation_id
          LEFT JOIN provider_policies p ON p.workspace_id=c.workspace_id AND p.provider=c.provider
          WHERE e.knowledge_item_id=k.id AND (p.id IS NULL OR p.allow_index=0)
      );
END;
CREATE TRIGGER IF NOT EXISTS knowledge_evidence_ad AFTER DELETE ON knowledge_evidence BEGIN
    DELETE FROM knowledge_fts WHERE knowledge_item_id=old.knowledge_item_id;
    INSERT INTO knowledge_fts(knowledge_item_id,canonical_text,description)
    SELECT k.id,k.canonical_text,k.description
    FROM knowledge_items k
    WHERE k.id=old.knowledge_item_id
      AND EXISTS (
          SELECT 1 FROM knowledge_evidence e
          JOIN conversations c ON c.id=e.conversation_id
          JOIN provider_policies p ON p.workspace_id=c.workspace_id AND p.provider=c.provider
          WHERE e.knowledge_item_id=k.id AND p.allow_index=1
      )
      AND NOT EXISTS (
          SELECT 1 FROM knowledge_evidence e
          JOIN conversations c ON c.id=e.conversation_id
          LEFT JOIN provider_policies p ON p.workspace_id=c.workspace_id AND p.provider=c.provider
          WHERE e.knowledge_item_id=k.id AND (p.id IS NULL OR p.allow_index=0)
      );
END;
CREATE TRIGGER IF NOT EXISTS knowledge_items_au AFTER UPDATE OF canonical_text,description ON knowledge_items BEGIN
    DELETE FROM knowledge_fts WHERE knowledge_item_id=old.id;
    INSERT INTO knowledge_fts(knowledge_item_id,canonical_text,description)
    SELECT k.id,k.canonical_text,k.description
    FROM knowledge_items k
    WHERE k.id=new.id
      AND EXISTS (
          SELECT 1 FROM knowledge_evidence e
          JOIN conversations c ON c.id=e.conversation_id
          JOIN provider_policies p ON p.workspace_id=c.workspace_id AND p.provider=c.provider
          WHERE e.knowledge_item_id=k.id AND p.allow_index=1
      )
      AND NOT EXISTS (
          SELECT 1 FROM knowledge_evidence e
          JOIN conversations c ON c.id=e.conversation_id
          LEFT JOIN provider_policies p ON p.workspace_id=c.workspace_id AND p.provider=c.provider
          WHERE e.knowledge_item_id=k.id AND (p.id IS NULL OR p.allow_index=0)
      );
END;
CREATE TRIGGER IF NOT EXISTS knowledge_items_ad AFTER DELETE ON knowledge_items BEGIN
    DELETE FROM knowledge_fts WHERE knowledge_item_id=old.id;
END;

CREATE TRIGGER IF NOT EXISTS provider_policy_index_au AFTER UPDATE OF allow_index ON provider_policies
WHEN old.allow_index <> new.allow_index
BEGIN
    DELETE FROM messages_fts WHERE message_id IN (
        SELECT m.id FROM messages m JOIN conversations c ON c.id=m.conversation_id
        WHERE c.workspace_id=new.workspace_id AND c.provider=new.provider
    );
    INSERT INTO messages_fts(message_id,conversation_id,content_text)
    SELECT m.id,m.conversation_id,m.content_text
    FROM messages m JOIN conversations c ON c.id=m.conversation_id
    WHERE new.allow_index=1 AND c.workspace_id=new.workspace_id AND c.provider=new.provider;

    DELETE FROM knowledge_fts WHERE knowledge_item_id IN (
        SELECT DISTINCT e.knowledge_item_id FROM knowledge_evidence e
        JOIN conversations c ON c.id=e.conversation_id
        WHERE c.workspace_id=new.workspace_id AND c.provider=new.provider
    );
    INSERT INTO knowledge_fts(knowledge_item_id,canonical_text,description)
    SELECT DISTINCT k.id,k.canonical_text,k.description
    FROM knowledge_items k
    JOIN knowledge_evidence e ON e.knowledge_item_id=k.id
    JOIN conversations c ON c.id=e.conversation_id
    JOIN provider_policies p ON p.workspace_id=c.workspace_id AND p.provider=c.provider
    WHERE k.workspace_id=new.workspace_id
      AND k.id IN (
          SELECT e2.knowledge_item_id FROM knowledge_evidence e2
          JOIN conversations c2 ON c2.id=e2.conversation_id
          WHERE c2.workspace_id=new.workspace_id AND c2.provider=new.provider
      )
      AND EXISTS (
          SELECT 1 FROM knowledge_evidence e3
          JOIN conversations c3 ON c3.id=e3.conversation_id
          JOIN provider_policies p3 ON p3.workspace_id=c3.workspace_id AND p3.provider=c3.provider
          WHERE e3.knowledge_item_id=k.id AND p3.allow_index=1
      )
      AND NOT EXISTS (
          SELECT 1 FROM knowledge_evidence e3
          JOIN conversations c3 ON c3.id=e3.conversation_id
          LEFT JOIN provider_policies p3 ON p3.workspace_id=c3.workspace_id AND p3.provider=c3.provider
          WHERE e3.knowledge_item_id=k.id AND (p3.id IS NULL OR p3.allow_index=0)
      );
END;

-- Migration 0002
-- Immutable user review decisions and before-state snapshots.
CREATE TABLE IF NOT EXISTS knowledge_reviews (
    id TEXT PRIMARY KEY,
    knowledge_item_id TEXT NOT NULL REFERENCES knowledge_items(id) ON DELETE CASCADE,
    version_before INTEGER NOT NULL,
    version_after INTEGER NOT NULL,
    decision TEXT NOT NULL CHECK (decision IN ('confirm','reject','withdraw')),
    previous_status TEXT NOT NULL,
    resulting_status TEXT NOT NULL,
    rationale TEXT NOT NULL DEFAULT '',
    snapshot_json TEXT NOT NULL CHECK (json_valid(snapshot_json)),
    created_at TEXT NOT NULL,
    CHECK (version_after > version_before)
);
CREATE INDEX IF NOT EXISTS idx_knowledge_reviews_item ON knowledge_reviews(knowledge_item_id, version_after);


-- Migration 0003: server-issued, single-use analysis handoffs.
-- Server-issued, single-use handoff records bind returned analysis to its destination provider.
CREATE TABLE IF NOT EXISTS analysis_handoffs (
    id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    conversation_id TEXT NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    source_provider TEXT NOT NULL,
    destination_provider TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'prepared'
        CHECK (status IN ('prepared','consumed','revoked','expired')),
    content_hash TEXT NOT NULL,
    redaction_report_json TEXT NOT NULL DEFAULT '{}' CHECK (json_valid(redaction_report_json)),
    created_at TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    consumed_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_analysis_handoffs_workspace_status
    ON analysis_handoffs(workspace_id,status,expires_at);
CREATE INDEX IF NOT EXISTS idx_analysis_handoffs_conversation
    ON analysis_handoffs(conversation_id,created_at);