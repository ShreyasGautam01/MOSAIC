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