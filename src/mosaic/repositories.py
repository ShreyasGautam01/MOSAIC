"""Small explicit SQLite repositories; transactions stay visible at service boundaries."""

from __future__ import annotations

from contextlib import closing

import hashlib
import json
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from mosaic.db.database import Database
from mosaic.schemas import CanonicalConversation


def new_id() -> str:
    return str(uuid.uuid4())


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


def json_compact(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), default=str)


def ensure_default_workspace(database: Database) -> str:
    with database.transaction() as connection:
        row = connection.execute(
            "SELECT id FROM workspaces ORDER BY created_at LIMIT 1"
        ).fetchone()
        if row:
            return str(row["id"])
        workspace_id = new_id()
        now = utc_now()
        connection.execute(
            "INSERT INTO workspaces(id,name,description,default_scope,created_at,updated_at) "
            "VALUES (?,?,?,?,?,?)",
            (workspace_id, "Personal workspace", "Private local Mosaic workspace", "personal", now, now),
        )
        return workspace_id


def get_provider_policy(database: Database, workspace_id: str, provider: str) -> dict[str, Any] | None:
    with closing(database.connect()) as connection:
        row = connection.execute(
            "SELECT * FROM provider_policies WHERE workspace_id=? AND provider=? "
            "AND product='consumer_chat'",
            (workspace_id, provider),
        ).fetchone()
        return dict(row) if row else None


def record_user_permissions(
    database: Database,
    workspace_id: str,
    provider: str,
    *,
    allow_store: bool,
    allow_index: bool,
    allow_derive: bool,
    allow_strategy_analysis: bool,
    allow_cross_provider_transfer: bool,
) -> None:
    now = utc_now()
    note = (
        "User-configured local data permissions. These settings record the user's choice; "
        "they are not a legal determination or provider policy review. Provider status remains unreviewed."
    )
    with database.transaction() as connection:
        connection.execute(
            """INSERT INTO provider_policies(
                id,workspace_id,provider,product,policy_status,allow_store,allow_index,
                allow_derive,allow_strategy_analysis,allow_cross_provider_transfer,
                allow_model_training,notes,created_at,updated_at
            ) VALUES (?,?,?,'consumer_chat','unreviewed',?,?,?,?,?,0,?,?,?)
            ON CONFLICT(workspace_id,provider,product) DO UPDATE SET
                allow_store=excluded.allow_store,
                allow_index=excluded.allow_index,
                allow_derive=excluded.allow_derive,
                allow_strategy_analysis=excluded.allow_strategy_analysis,
                allow_cross_provider_transfer=excluded.allow_cross_provider_transfer,
                notes=excluded.notes,
                updated_at=excluded.updated_at""",
            (
                new_id(), workspace_id, provider, int(allow_store), int(allow_index),
                int(allow_derive), int(allow_strategy_analysis), int(allow_cross_provider_transfer),
                note, now, now,
            ),
        )



def record_provider_policy_review(
    database: Database,
    workspace_id: str,
    provider: str,
    *,
    policy_url: str,
    policy_version: str,
    policy_status: str,
    notes: str,
) -> dict[str, Any]:
    """Record the user's policy review attestation; Mosaic does not make a legal determination."""
    if policy_status not in {"allowed_with_conditions", "restricted", "prohibited"}:
        raise ValueError("Unsupported policy review status")
    if not notes.strip():
        raise ValueError("Record the relevant conditions, restrictions, or reason")
    now = utc_now()
    with database.transaction() as connection:
        connection.execute(
            """INSERT INTO provider_policies(
                id,workspace_id,provider,product,policy_url,reviewed_at,reviewed_by,
                policy_version,policy_status,allow_store,allow_index,allow_derive,
                allow_strategy_analysis,allow_cross_provider_transfer,allow_model_training,
                notes,created_at,updated_at
            ) VALUES (?,?,?,'consumer_chat',?,?, 'local_user',?,?,0,0,0,0,0,0,?,?,?)
            ON CONFLICT(workspace_id,provider,product) DO UPDATE SET
                policy_url=excluded.policy_url,
                reviewed_at=excluded.reviewed_at,
                reviewed_by=excluded.reviewed_by,
                policy_version=excluded.policy_version,
                policy_status=excluded.policy_status,
                notes=excluded.notes,
                updated_at=excluded.updated_at""",
            (new_id(), workspace_id, provider, policy_url, now, policy_version,
             policy_status, notes.strip(), now, now),
        )
        connection.execute(
            """INSERT INTO audit_events(
                id,workspace_id,actor,action,entity_type,entity_id,details_json,created_at
            ) VALUES (?,?,?,?,?,?,?,?)""",
            (new_id(), workspace_id, "user", "provider_policy.reviewed", "provider_policy",
             provider, json_compact({"policy_status": policy_status, "policy_version": policy_version,
                                    "policy_url": policy_url}), now),
        )
        row = connection.execute(
            """SELECT provider,policy_url,reviewed_at,reviewed_by,policy_version,policy_status,notes
               FROM provider_policies WHERE workspace_id=? AND provider=? AND product='consumer_chat'""",
            (workspace_id, provider),
        ).fetchone()
        return dict(row)


def require_provider_transfer_review(
    database: Database, workspace_id: str, source_provider: str, destination_provider: str
) -> None:
    """Require user-recorded policy review for every external provider in a handoff."""
    providers = {source_provider, destination_provider} - {"manual", "local"}
    for provider in providers:
        policy = get_provider_policy(database, workspace_id, provider)
        if not policy or policy["policy_status"] != "allowed_with_conditions":
            raise PermissionError(
                f"Provider policy review for {provider} is not marked allowed_with_conditions"
            )


def find_duplicate_source(database: Database, workspace_id: str, sha256: str) -> dict[str, Any] | None:
    with closing(database.connect()) as connection:
        row = connection.execute(
            "SELECT id,provider,parse_status FROM source_artifacts WHERE workspace_id=? AND sha256=?",
            (workspace_id, sha256),
        ).fetchone()
        return dict(row) if row else None


def persist_import(
    database: Database,
    *,
    workspace_id: str,
    provider: str,
    source_type: str,
    filename: str | None,
    storage_relpath: str,
    source_bytes: bytes,
    conversations: list[CanonicalConversation],
    parser_name: str,
    warnings: list[str],
) -> tuple[str, int, int]:
    now = utc_now()
    artifact_id = new_id()
    total_messages = sum(len(item.messages) for item in conversations)
    with database.transaction() as connection:
        connection.execute(
            """INSERT INTO source_artifacts(
                id,workspace_id,provider,source_type,original_filename,storage_relpath,
                sha256,byte_size,mime_type,imported_at,parser_name,parser_version,
                parse_status,policy_status,retention_state,metadata_json
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,'unreviewed','retain',?)""",
            (
                artifact_id, workspace_id, provider, source_type, filename, storage_relpath,
                hashlib.sha256(source_bytes).hexdigest(), len(source_bytes),
                "application/zip" if source_type == "archive" else "text/plain",
                now, parser_name, "0.1.0", "complete", json_compact({"warnings": warnings}),
            ),
        )
        for conversation in conversations:
            conversation_id = new_id()
            content_hash = hashlib.sha256(
                "\n".join(message.content_text for message in conversation.messages).encode("utf-8")
            ).hexdigest()
            connection.execute(
                """INSERT INTO conversations(
                    id,workspace_id,source_artifact_id,provider,provider_conversation_id,
                    title,started_at,ended_at,imported_at,content_hash,metadata_json
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    conversation_id, workspace_id, artifact_id, provider,
                    conversation.provider_conversation_id, conversation.title,
                    conversation.started_at.isoformat() if conversation.started_at else None,
                    conversation.ended_at.isoformat() if conversation.ended_at else None,
                    now, content_hash, json_compact(conversation.metadata),
                ),
            )
            message_id_by_provider: dict[str, str] = {}
            deferred_parents: list[tuple[str, str]] = []
            for message in conversation.messages:
                message_id = new_id()
                provider_message_id = message.provider_message_id or message_id
                message_id_by_provider[provider_message_id] = message_id
                metadata = dict(message.metadata)
                if message.parent_provider_message_id:
                    deferred_parents.append((message_id, message.parent_provider_message_id))
                content_hash_message = hashlib.sha256(message.content_text.encode("utf-8")).hexdigest()
                connection.execute(
                    """INSERT INTO messages(
                        id,conversation_id,provider_message_id,parent_message_id,sequence_no,
                        role,author_label,model_label,created_at,content_text,content_hash,
                        modality,metadata_json
                    ) VALUES (?,?,?,NULL,?,?,?,?,?,?,?,?,?)""",
                    (
                        message_id, conversation_id, provider_message_id, message.sequence_no,
                        message.role, message.author_label, message.model_label,
                        message.created_at.isoformat() if message.created_at else None,
                        message.content_text, content_hash_message, message.modality,
                        json_compact(metadata),
                    ),
                )
            for child_id, parent_provider_id in deferred_parents:
                parent_id = message_id_by_provider.get(parent_provider_id)
                if parent_id and parent_id != child_id:
                    connection.execute(
                        "UPDATE messages SET parent_message_id=? WHERE id=?",
                        (parent_id, child_id),
                    )
        connection.execute(
            "INSERT INTO audit_events(id,workspace_id,actor,action,entity_type,entity_id,details_json,created_at) "
            "VALUES (?,?,?,?,?,?,?,?)",
            (
                new_id(), workspace_id, "user", "conversation.imported", "source_artifact",
                artifact_id, json_compact({"provider": provider, "conversations": len(conversations),
                                           "messages": total_messages}), now,
            ),
        )
    return artifact_id, len(conversations), total_messages


def list_imports(database: Database, workspace_id: str) -> list[dict[str, Any]]:
    with closing(database.connect()) as connection:
        rows = connection.execute(
            """SELECT s.id,s.provider,s.source_type,s.original_filename,s.byte_size,
                      s.imported_at,s.parse_status,s.policy_status,
                      COUNT(DISTINCT c.id) AS conversation_count,
                      COUNT(m.id) AS message_count
               FROM source_artifacts s
               LEFT JOIN conversations c ON c.source_artifact_id=s.id
               LEFT JOIN messages m ON m.conversation_id=c.id
               WHERE s.workspace_id=? AND s.retention_state!='deleted'
               GROUP BY s.id ORDER BY s.imported_at DESC""",
            (workspace_id,),
        ).fetchall()
        return [dict(row) for row in rows]


def list_conversations(database: Database, workspace_id: str, limit: int = 100) -> list[dict[str, Any]]:
    with closing(database.connect()) as connection:
        rows = connection.execute(
            """SELECT c.id,c.provider,c.title,c.started_at,c.ended_at,c.imported_at,
                      COUNT(m.id) AS message_count
               FROM conversations c LEFT JOIN messages m ON m.conversation_id=c.id
               WHERE c.workspace_id=? GROUP BY c.id
               ORDER BY COALESCE(c.started_at,c.imported_at) DESC LIMIT ?""",
            (workspace_id, limit),
        ).fetchall()
        return [dict(row) for row in rows]


def get_conversation(database: Database, conversation_id: str) -> dict[str, Any] | None:
    with closing(database.connect()) as connection:
        conversation = connection.execute(
            """SELECT c.*,s.original_filename,s.id AS artifact_id
               FROM conversations c LEFT JOIN source_artifacts s ON s.id=c.source_artifact_id
               WHERE c.id=?""",
            (conversation_id,),
        ).fetchone()
        if not conversation:
            return None
        messages = connection.execute(
            """SELECT id,provider_message_id,parent_message_id,sequence_no,role,author_label,
                      model_label,created_at,content_text,modality,metadata_json
               FROM messages WHERE conversation_id=? ORDER BY sequence_no""",
            (conversation_id,),
        ).fetchall()
        result = dict(conversation)
        result["metadata"] = json.loads(result.pop("metadata_json") or "{}")
        result["messages"] = []
        for row in messages:
            item = dict(row)
            item["metadata"] = json.loads(item.pop("metadata_json") or "{}")
            result["messages"].append(item)
        return result


def search_messages(database: Database, workspace_id: str, query: str, limit: int = 30) -> list[dict[str, Any]]:
    import re

    terms = re.findall(r"[\w-]{2,80}", query, flags=re.UNICODE)[:12]
    if not terms:
        return []
    fts_query = " AND ".join(f'"{term.replace(chr(34), "")}"' for term in terms)
    with closing(database.connect()) as connection:
        rows = connection.execute(
            """SELECT m.id AS message_id,m.conversation_id,m.sequence_no,m.role,
                      c.title,c.provider,substr(m.content_text,1,360) AS excerpt,
                      bm25(messages_fts) AS rank
               FROM messages_fts
               JOIN messages m ON m.id=messages_fts.message_id
               JOIN conversations c ON c.id=m.conversation_id
               WHERE messages_fts MATCH ? AND c.workspace_id=?
               ORDER BY rank LIMIT ?""",
            (fts_query, workspace_id, limit),
        ).fetchall()
        return [dict(row) for row in rows]


def get_policy_flags(database: Database, workspace_id: str, provider: str) -> dict[str, bool]:
    row = get_provider_policy(database, workspace_id, provider)
    if not row:
        return {
            "allow_store": False,
            "allow_index": False,
            "allow_derive": False,
            "allow_strategy_analysis": False,
            "allow_cross_provider_transfer": False,
        }
    return {
        name: bool(row[name])
        for name in (
            "allow_store", "allow_index", "allow_derive", "allow_strategy_analysis",
            "allow_cross_provider_transfer",
        )
    }


def search_knowledge(database: Database, workspace_id: str, query: str, limit: int = 30) -> list[dict[str, Any]]:
    import re

    terms = re.findall(r"[\w-]{2,80}", query, flags=re.UNICODE)[:12]
    if not terms:
        return []
    fts_query = " AND ".join(f'"{term.replace(chr(34), "")}"' for term in terms)
    with closing(database.connect()) as connection:
        rows = connection.execute(
            """SELECT k.id,k.kind,k.scope,k.canonical_text,k.description,k.status,
                      bm25(knowledge_fts) AS rank
               FROM knowledge_fts JOIN knowledge_items k
                 ON k.id=knowledge_fts.knowledge_item_id
               WHERE knowledge_fts MATCH ? AND k.workspace_id=?
               ORDER BY rank LIMIT ?""",
            (fts_query, workspace_id, limit),
        ).fetchall()
        return [dict(row) for row in rows]



def create_analysis_handoff(
    database: Database,
    *,
    workspace_id: str,
    conversation_id: str,
    source_provider: str,
    destination_provider: str,
    content_hash: str,
    redaction_report: dict[str, Any],
) -> str:
    """Create a short-lived, single-use server-issued handoff capability."""
    handoff_id = new_id()
    now = datetime.now(UTC)
    with database.transaction() as connection:
        conversation = connection.execute(
            "SELECT provider FROM conversations WHERE id=? AND workspace_id=?",
            (conversation_id, workspace_id),
        ).fetchone()
        if not conversation or conversation["provider"] != source_provider:
            raise LookupError("Conversation not found or source provider changed")
        connection.execute(
            """INSERT INTO analysis_handoffs(
                id,workspace_id,conversation_id,source_provider,destination_provider,
                status,content_hash,redaction_report_json,created_at,expires_at
            ) VALUES (?,?,?,?,?,'prepared',?,?,?,?)""",
            (handoff_id, workspace_id, conversation_id, source_provider, destination_provider,
             content_hash, json_compact(redaction_report), now.isoformat(),
             (now + timedelta(hours=24)).isoformat()),
        )
        connection.execute(
            "INSERT INTO audit_events(id,workspace_id,actor,action,entity_type,entity_id,details_json,created_at) "
            "VALUES (?,?,?,?,?,?,?,?)",
            (new_id(), workspace_id, "user", "analysis_handoff.prepared", "analysis_handoff",
             handoff_id, json_compact({"source_provider": source_provider,
                                      "destination_provider": destination_provider}), now.isoformat()),
        )
    return handoff_id


def get_analysis_handoff(
    database: Database, *, workspace_id: str, conversation_id: str, handoff_id: str
) -> dict[str, Any] | None:
    with closing(database.connect()) as connection:
        row = connection.execute(
            """SELECT * FROM analysis_handoffs
               WHERE id=? AND workspace_id=? AND conversation_id=?""",
            (handoff_id, workspace_id, conversation_id),
        ).fetchone()
        return dict(row) if row else None

def create_analysis_candidates(
    database: Database,
    *,
    workspace_id: str,
    conversation_id: str,
    summary: str,
    items: list[dict[str, Any]],
    analysis_provider: str = "manual",
    handoff_id: str | None = None,
    confirm_local_storage: bool = False,
    confirm_manual_authorship: bool = False,
) -> list[dict[str, str]]:
    """Persist source-linked candidates and atomically consume an optional handoff.

    External provider attribution is derived only from a valid server-issued handoff,
    never from client-supplied provider labels.
    """
    now = utc_now()
    created: list[dict[str, str]] = []
    with database.transaction() as connection:
        conv = connection.execute(
            "SELECT source_artifact_id,provider FROM conversations WHERE id=? AND workspace_id=?",
            (conversation_id, workspace_id),
        ).fetchone()
        if not conv:
            raise LookupError("Conversation not found")

        source_provider = str(conv["provider"])
        effective_provider = analysis_provider if analysis_provider in {"manual", "local"} else "manual"
        if handoff_id:
            handoff = connection.execute(
                """SELECT * FROM analysis_handoffs
                   WHERE id=? AND workspace_id=? AND conversation_id=?""",
                (handoff_id, workspace_id, conversation_id),
            ).fetchone()
            if not handoff:
                raise ValueError("Unknown analysis handoff")
            if handoff["status"] != "prepared":
                raise ValueError("Analysis handoff has already been used or revoked")
            if handoff["expires_at"] <= now:
                raise ValueError("Analysis handoff has expired; prepare a new packet")
            if handoff["source_provider"] != source_provider:
                raise ValueError("Analysis handoff source no longer matches the conversation")
            effective_provider = str(handoff["destination_provider"])
            if effective_provider not in {"manual", "local"} and not confirm_local_storage:
                raise PermissionError("Confirm local storage of the external analysis response")
            if effective_provider == "manual" and not confirm_manual_authorship:
                raise PermissionError("Confirm that this is your own manually authored analysis")
            analysis_provider = effective_provider

        source_policy = connection.execute(
            "SELECT * FROM provider_policies WHERE workspace_id=? AND provider=? AND product='consumer_chat'",
            (workspace_id, source_provider),
        ).fetchone()
        if not source_policy or not source_policy["allow_derive"]:
            raise PermissionError("Semantic derivation is disabled for this source")
        if any(item["kind"] == "strategy_observation" for item in items) and not source_policy["allow_strategy_analysis"]:
            raise PermissionError("Strategy extraction is disabled for this source")

        if handoff_id and effective_provider not in {"manual", "local"}:
            if effective_provider != source_provider and not source_policy["allow_cross_provider_transfer"]:
                raise PermissionError("Cross-provider analysis is disabled for this source")
            for provider in {source_provider, effective_provider} - {"manual", "local"}:
                policy = connection.execute(
                    "SELECT policy_status FROM provider_policies WHERE workspace_id=? AND provider=? AND product='consumer_chat'",
                    (workspace_id, provider),
                ).fetchone()
                if not policy or policy["policy_status"] != "allowed_with_conditions":
                    raise PermissionError(
                        f"Provider policy review for {provider} is not marked allowed_with_conditions"
                    )

        if handoff_id and effective_provider not in {"manual", "local"}:
            # Consent and receipt are committed atomically with candidate persistence.
            connection.execute(
                """INSERT INTO provider_policies(
                    id,workspace_id,provider,product,policy_status,allow_store,allow_index,
                    allow_derive,allow_strategy_analysis,allow_cross_provider_transfer,
                    allow_model_training,notes,created_at,updated_at
                ) VALUES (?,?,?,'consumer_chat','unreviewed',1,0,0,0,0,0,?,?,?)
                ON CONFLICT(workspace_id,provider,product) DO UPDATE SET
                    allow_store=1,
                    notes=provider_policies.notes || ' User explicitly confirmed local storage of a returned analysis response.',
                    updated_at=excluded.updated_at""",
                (new_id(), workspace_id, effective_provider,
                 "User explicitly confirmed local storage of a returned analysis response.", now, now),
            )

        message_text_by_id = {
            row["id"]: row["content_text"] for row in connection.execute(
                "SELECT id,content_text FROM messages WHERE conversation_id=?", (conversation_id,)
            ).fetchall()
        }
        for item in items:
            source_ids = item["source_message_ids"]
            if not source_ids or any(source_id not in message_text_by_id for source_id in source_ids):
                raise ValueError("Every knowledge candidate must cite messages from this conversation")
            exact_span = item.get("exact_span")
            if exact_span and not any(exact_span in message_text_by_id[source_id] for source_id in source_ids):
                raise ValueError("An exact_span must occur verbatim in at least one cited source message")

        for item in items:
            item_id = new_id()
            connection.execute(
                """INSERT INTO knowledge_items(
                    id,workspace_id,kind,scope,canonical_text,description,status,
                    interpretation_class,support_level,extractor_name,extractor_version,
                    properties_json,created_at,updated_at
                ) VALUES (?,?,?,?,?,?,'candidate',?,'unassessed',?,'0.1.0',?,?,?)""",
                (
                    item_id, workspace_id, item["kind"], item["scope"],
                    item["canonical_text"], item["description"], item["interpretation_class"],
                    "ollama_local" if analysis_provider == "local" else f"assisted:{effective_provider}",
                    json_compact({
                        "strategy_labels": item.get("strategy_labels", []),
                        "conversation_summary": summary,
                        "analysis_provider": effective_provider,
                        "attribution_basis": (
                            "internal_local_inference" if effective_provider == "local"
                            else "user_attested_handoff_destination" if handoff_id
                            else "user_attested_manual_authorship"
                        ),
                    }), now, now,
                ),
            )
            for source_id in item["source_message_ids"]:
                connection.execute(
                    """INSERT INTO knowledge_evidence(
                        id,knowledge_item_id,evidence_type,stance,source_artifact_id,
                        conversation_id,message_id,exact_span,note,created_at
                    ) VALUES (?,?,?, 'supports', ?,?,?,?,?,?)""",
                    (
                        new_id(), item_id,
                        "direct_quote" if item.get("exact_span") else "source_paraphrase",
                        conv["source_artifact_id"], conversation_id, source_id,
                        item.get("exact_span"), "User-mediated semantic analysis; review required.", now,
                    ),
                )
            created.append({"id": item_id, "status": "candidate", "kind": item["kind"]})

        if handoff_id:
            changed = connection.execute(
                """UPDATE analysis_handoffs SET status='consumed',consumed_at=?
                   WHERE id=? AND workspace_id=? AND conversation_id=? AND status='prepared' AND expires_at>?""",
                (now, handoff_id, workspace_id, conversation_id, now),
            ).rowcount
            if changed != 1:
                raise ValueError("Analysis handoff is no longer available")

        connection.execute(
            "INSERT INTO audit_events(id,workspace_id,actor,action,entity_type,entity_id,details_json,created_at) "
            "VALUES (?,?,?,?,?,?,?,?)",
            (new_id(), workspace_id, "user", "knowledge.candidates_created", "conversation",
             conversation_id, json_compact({"count": len(created), "analysis_provider": effective_provider,
                                            "handoff_id": handoff_id}), now),
        )
    return created


def list_knowledge(database: Database, workspace_id: str, limit: int = 100) -> list[dict[str, Any]]:
    with closing(database.connect()) as connection:
        rows = connection.execute(
            """SELECT k.id,k.kind,k.scope,k.canonical_text,k.description,k.status,
                      k.interpretation_class,k.support_level,k.version,k.created_at,
                      COUNT(e.id) AS evidence_count
               FROM knowledge_items k LEFT JOIN knowledge_evidence e ON e.knowledge_item_id=k.id
               WHERE k.workspace_id=? GROUP BY k.id ORDER BY k.created_at DESC LIMIT ?""",
            (workspace_id, limit),
        ).fetchall()
        return [dict(row) for row in rows]


def review_knowledge_item(
    database: Database,
    *,
    workspace_id: str,
    knowledge_id: str,
    decision: str,
    rationale: str,
) -> dict[str, Any]:
    transitions = {
        "confirm": ("user_confirmed", "user_confirmed", "confirm"),
        "reject": ("rejected", None, "reject"),
        "withdraw": ("withdrawn", None, "withdraw"),
    }
    if decision not in transitions:
        raise ValueError("Unsupported review decision")
    target_status, interpretation_class, feedback_type = transitions[decision]
    now = utc_now()
    review_id = new_id()
    with database.transaction() as connection:
        row = connection.execute(
            "SELECT * FROM knowledge_items WHERE id=? AND workspace_id=?",
            (knowledge_id, workspace_id),
        ).fetchone()
        if not row:
            raise LookupError("Knowledge item not found")
        if row["status"] not in {"candidate", "user_confirmed"}:
            raise ValueError(f"Cannot review an item in status {row['status']}")
        before = dict(row)
        new_version = int(row["version"]) + 1
        connection.execute(
            """INSERT INTO knowledge_reviews(
                id,knowledge_item_id,version_before,version_after,decision,previous_status,
                resulting_status,rationale,snapshot_json,created_at
            ) VALUES (?,?,?,?,?,?,?,?,?,?)""",
            (review_id, knowledge_id, row["version"], new_version, decision, row["status"],
             target_status, rationale, json_compact(before), now),
        )
        if interpretation_class:
            connection.execute(
                "UPDATE knowledge_items SET status=?,interpretation_class=?,version=?,updated_at=? WHERE id=?",
                (target_status, interpretation_class, new_version, now, knowledge_id),
            )
        else:
            connection.execute(
                "UPDATE knowledge_items SET status=?,version=?,updated_at=? WHERE id=?",
                (target_status, new_version, now, knowledge_id),
            )
        connection.execute(
            """INSERT INTO feedback_events(
                id,workspace_id,target_type,target_id,feedback_type,explicit,details,created_at
            ) VALUES (?,?, 'knowledge_item',?,?,1,?,?)""",
            (new_id(), workspace_id, knowledge_id, feedback_type, rationale, now),
        )
        connection.execute(
            "INSERT INTO audit_events(id,workspace_id,actor,action,entity_type,entity_id,details_json,created_at) "
            "VALUES (?,?,?,?,?,?,?,?)",
            (new_id(), workspace_id, "user", f"knowledge.{decision}", "knowledge_item",
             knowledge_id, json_compact({"review_id": review_id, "version": new_version}), now),
        )
        return {
            "review_id": review_id,
            "knowledge_item_id": knowledge_id,
            "decision": decision,
            "status": target_status,
            "version": new_version,
        }


def get_knowledge_sources(database: Database, knowledge_id: str) -> list[dict[str, Any]]:
    with closing(database.connect()) as connection:
        rows = connection.execute(
            """SELECT e.id,e.evidence_type,e.stance,e.exact_span,e.note,
                      m.id AS message_id,m.sequence_no,m.role,m.content_text,
                      c.id AS conversation_id,c.title,c.provider
               FROM knowledge_evidence e
               LEFT JOIN messages m ON m.id=e.message_id
               LEFT JOIN conversations c ON c.id=e.conversation_id
               WHERE e.knowledge_item_id=? ORDER BY m.sequence_no""",
            (knowledge_id,),
        ).fetchall()
        return [dict(row) for row in rows]