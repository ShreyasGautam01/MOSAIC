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