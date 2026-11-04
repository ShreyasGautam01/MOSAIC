from __future__ import annotations


def _review_provider(client, provider: str, *, status: str = "allowed_with_conditions"):
    return client.put(
        f"/api/v1/settings/providers/{provider}/policy-review",
        json={
            "policy_url": f"https://policy.example.test/{provider}",
            "policy_version": "fixture-review-2026-11-03",
            "policy_status": status,
            "notes": "User-reviewed test fixture. This is not a legal determination.",
            "user_acknowledged": True,
        },
    )


def _import_zip(client, payload: bytes):
    return client.post(
        "/api/v1/imports",
        files={"file": ("conversations.zip", payload, "application/zip")},
        data={
            "confirm_local_storage": "true",
            "enable_local_indexing": "true",
            "enable_semantic_analysis": "true",
            "enable_strategy_analysis": "true",
            "enable_cross_provider_transfer": "false",
        },
    )


def _manual_handoff(client, conversation_id: str) -> str:
    response = client.post(
        f"/api/v1/conversations/{conversation_id}/analysis-packet",
        json={"destination_provider": "manual", "include_strategies": False},
    )
    assert response.status_code == 200, response.text
    return response.json()["handoff_id"]


def test_import_search_report_and_duplicate(client, chatgpt_zip) -> None:
    health = client.get("/api/v1/health")
    assert health.status_code == 200
    assert health.json()["status"] == "ok"

    imported = _import_zip(client, chatgpt_zip)
    assert imported.status_code == 200, imported.text
    result = imported.json()
    assert result["provider"] == "chatgpt"
    assert result["conversation_count"] == 1
    assert result["message_count"] == 3

    conversations = client.get("/api/v1/conversations").json()
    assert len(conversations) == 1
    conversation_id = conversations[0]["id"]

    detail = client.get(f"/api/v1/conversations/{conversation_id}")
    assert detail.status_code == 200
    assert detail.json()["messages"][0]["content_text"] == "How should I index a SQLite table?"

    report = client.get(f"/api/v1/conversations/{conversation_id}/report").json()
    assert report["message_count"] == 3
    assert len(report["episodes"]) == 2

    search = client.get("/api/v1/search", params={"q": "query plan"})
    assert search.status_code == 200
    assert search.json()[0]["conversation_id"] == conversation_id

    duplicate = _import_zip(client, chatgpt_zip)
    assert duplicate.status_code == 200
    assert duplicate.json()["duplicate"] is True
    assert duplicate.json()["conversation_count"] == 0


def test_import_requires_explicit_local_storage_confirmation(client, chatgpt_zip) -> None:
    response = client.post(
        "/api/v1/imports",
        files={"file": ("conversations.zip", chatgpt_zip, "application/zip")},
        data={"confirm_local_storage": "false", "enable_local_indexing": "true"},
    )
    assert response.status_code == 400
    assert "Confirm" in response.json()["detail"]


def test_source_linked_analysis_candidates_and_transfer_gate(client, chatgpt_zip) -> None:
    _import_zip(client, chatgpt_zip)
    conversation = client.get("/api/v1/conversations").json()[0]
    conversation_id = conversation["id"]
    messages = client.get(f"/api/v1/conversations/{conversation_id}").json()["messages"]
    user_message = messages[0]
    assistant_message = messages[1]

    assert _review_provider(client, "chatgpt").status_code == 200
    packet = client.post(
        f"/api/v1/conversations/{conversation_id}/analysis-packet",
        json={"destination_provider": "chatgpt", "include_strategies": True},
    )
    assert packet.status_code == 200
    assert user_message["id"] in packet.json()["prompt"]
    assert "hidden chain-of-thought" in packet.json()["prompt"]

    submitted = client.post(
        f"/api/v1/conversations/{conversation_id}/analysis",
        json={
            "handoff_id": packet.json()["handoff_id"],
            "confirm_local_storage": True,
            "analysis": {
                "summary": "The discussion recommends diagnosis before indexing.",
                "items": [{
                    "kind": "procedure",
                    "scope": "general",
                    "canonical_text": "Inspect the query plan before adding an index.",
                    "description": "Use observed query cost to identify the bottleneck.",
                    "interpretation_class": "explicit",
                    "source_message_ids": [assistant_message["id"]],
                    "exact_span": "Inspect the query plan before adding an index.",
                    "strategy_labels": ["diagnostic_first"],
                }],
            },
        },
    )
    assert submitted.status_code == 200, submitted.text
    item_id = submitted.json()["created"][0]["id"]
    assert client.get("/api/v1/knowledge").json()[0]["status"] == "candidate"
    sources = client.get(f"/api/v1/knowledge/{item_id}/sources")
    assert sources.status_code == 200
    assert sources.json()[0]["message_id"] == assistant_message["id"]

    objective = client.post("/api/v1/objectives", json={
        "title": "Improve query diagnostics",
        "objective_text": "Review a database indexing approach.",
        "constraints": ["Keep the design lightweight"],
    })
    objective_id = objective.json()["objective_id"]
    denied = client.post(
        f"/api/v1/objectives/{objective_id}/packets",
        json={"destination_provider": "claude", "requested_role": "Critically review",
              "knowledge_item_ids": [item_id]},
    )
    assert denied.status_code == 403

    permissions = client.put(
        "/api/v1/settings/providers/chatgpt/permissions",
        json={"allow_store": True, "allow_index": True, "allow_derive": True,
              "allow_strategy_analysis": True, "allow_cross_provider_transfer": True},
    )
    assert permissions.status_code == 200
    assert _review_provider(client, "chatgpt").status_code == 200
    assert _review_provider(client, "claude").status_code == 200
    review = client.post(
        f"/api/v1/knowledge/{item_id}/review",
        json={"decision": "confirm", "rationale": "Confirmed for this user-owned workspace."},
    )
    assert review.status_code == 200
    allowed = client.post(
        f"/api/v1/objectives/{objective_id}/packets",
        json={"destination_provider": "claude", "requested_role": "Critically review",
              "knowledge_item_ids": [item_id]},
    )
    assert allowed.status_code == 200, allowed.text
    assert "Inspect the query plan" in allowed.json()["body_text"]

    spoofed_response = client.post(
        f"/api/v1/objectives/{objective_id}/responses",
        json={"session_id": allowed.json()["session_id"], "provider": "groq",
              "model_label": "test-model", "response_text": "Review response.",
              "confirm_local_storage": True},
    )
    assert spoofed_response.status_code == 422

    saved_response = client.post(
        f"/api/v1/objectives/{objective_id}/responses",
        json={"session_id": allowed.json()["session_id"],
              "model_label": "test-model", "response_text": "Review response.",
              "confirm_local_storage": True},
    )
    assert saved_response.status_code == 200
    with client.app.state.database.connect() as connection:
        stored = connection.execute(
            "SELECT provider,metadata_json FROM model_responses WHERE id=?",
            (saved_response.json()["response_id"],),
        ).fetchone()
    assert stored["provider"] == "claude"
    assert "user_attested_context_packet_destination" in stored["metadata_json"]
    replayed = client.post(
        f"/api/v1/objectives/{objective_id}/responses",
        json={"session_id": allowed.json()["session_id"],
              "model_label": "test-model", "response_text": "Second response.",
              "confirm_local_storage": True},
    )
    assert replayed.status_code == 400
    assert "already received" in replayed.json()["detail"].lower()


def test_disabling_provider_indexing_removes_message_and_knowledge_search(client, chatgpt_zip):
    _import_zip(client, chatgpt_zip)
    conversation_id = client.get("/api/v1/conversations").json()[0]["id"]
    messages = client.get(f"/api/v1/conversations/{conversation_id}").json()["messages"]
    handoff_id = _manual_handoff(client, conversation_id)
    analysis = client.post(
        f"/api/v1/conversations/{conversation_id}/analysis",
        json={
            "handoff_id": handoff_id,
            "confirm_manual_authorship": True,
            "analysis": {
                "summary": "Query-plan reasoning",
                "items": [{
                    "kind": "concept", "scope": "general",
                    "canonical_text": "Query plans reveal database access strategy",
                    "description": "Inspect the query plan before adding an index.",
                    "interpretation_class": "explicit",
                    "source_message_ids": [messages[1]["id"]],
                }],
            },
        },
    )
    assert analysis.status_code == 200, analysis.text
    assert client.get("/api/v1/search", params={"q": "query plan"}).json()
    assert client.get("/api/v1/search/knowledge", params={"q": "query plan"}).json()

    disabled = client.put(
        "/api/v1/settings/providers/chatgpt/permissions",
        json={"allow_store": True, "allow_index": False, "allow_derive": True,
              "allow_strategy_analysis": True, "allow_cross_provider_transfer": False},
    )
    assert disabled.status_code == 200
    assert client.get("/api/v1/search", params={"q": "query plan"}).json() == []
    assert client.get("/api/v1/search/knowledge", params={"q": "query plan"}).json() == []

    enabled = client.put(
        "/api/v1/settings/providers/chatgpt/permissions",
        json={"allow_store": True, "allow_index": True, "allow_derive": True,
              "allow_strategy_analysis": True, "allow_cross_provider_transfer": False},
    )
    assert enabled.status_code == 200
    assert client.get("/api/v1/search", params={"q": "query plan"}).json()
    assert client.get("/api/v1/search/knowledge", params={"q": "query plan"}).json()


def test_untrusted_browser_origin_is_rejected(client):
    response = client.get("/api/v1/health", headers={"Origin": "https://attacker.invalid"})
    assert response.status_code == 403


def test_knowledge_review_is_explicit_versioned_and_audited(client, chatgpt_zip):
    _import_zip(client, chatgpt_zip)
    conversation_id = client.get("/api/v1/conversations").json()[0]["id"]
    messages = client.get(f"/api/v1/conversations/{conversation_id}").json()["messages"]
    handoff_id = _manual_handoff(client, conversation_id)
    response = client.post(
        f"/api/v1/conversations/{conversation_id}/analysis",
        json={"handoff_id": handoff_id, "confirm_manual_authorship": True, "analysis": {"summary": "", "items": [{
            "kind": "claim", "scope": "personal", "canonical_text": "Query plans expose execution choices.",
            "description": "", "interpretation_class": "explicit",
            "source_message_ids": [messages[1]["id"]],
        }]}},
    )
    assert response.status_code == 200
    item_id = response.json()["created"][0]["id"]
    reviewed = client.post(f"/api/v1/knowledge/{item_id}/review", json={
        "decision": "confirm", "rationale": "The cited source supports this interpretation.",
    })
    assert reviewed.status_code == 200
    assert reviewed.json()["status"] == "user_confirmed"
    assert reviewed.json()["version"] == 2
    item = next(item for item in client.get("/api/v1/knowledge").json() if item["id"] == item_id)
    assert item["interpretation_class"] == "user_confirmed"
    assert item["version"] == 2


def test_exact_quotes_must_match_the_cited_message(client, chatgpt_zip):
    _import_zip(client, chatgpt_zip)
    conversation_id = client.get("/api/v1/conversations").json()[0]["id"]
    messages = client.get(f"/api/v1/conversations/{conversation_id}").json()["messages"]
    handoff_id = _manual_handoff(client, conversation_id)
    response = client.post(
        f"/api/v1/conversations/{conversation_id}/analysis",
        json={"handoff_id": handoff_id, "confirm_manual_authorship": True, "analysis": {"summary": "", "items": [{
            "kind": "claim", "scope": "personal", "canonical_text": "A supported claim.",
            "description": "", "interpretation_class": "explicit",
            "source_message_ids": [messages[1]["id"]], "exact_span": "This exact quote does not exist.",
        }]}},
    )
    assert response.status_code == 422
    assert "verbatim" in response.json()["detail"]


def test_external_analysis_cannot_mark_knowledge_as_user_confirmed(client, chatgpt_zip):
    _import_zip(client, chatgpt_zip)
    conversation_id = client.get("/api/v1/conversations").json()[0]["id"]
    messages = client.get(f"/api/v1/conversations/{conversation_id}").json()["messages"]
    handoff_id = _manual_handoff(client, conversation_id)
    response = client.post(
        f"/api/v1/conversations/{conversation_id}/analysis",
        json={"handoff_id": handoff_id, "confirm_manual_authorship": True, "analysis": {"summary": "", "items": [{
            "kind": "claim", "scope": "personal", "canonical_text": "A claim.",
            "description": "", "interpretation_class": "user_confirmed",
            "source_message_ids": [messages[1]["id"]],
        }]}},
    )
    assert response.status_code == 422
    assert "only the user" in response.json()["detail"].lower()


def test_context_packet_rejects_candidate_until_user_confirms(client, chatgpt_zip):
    _import_zip(client, chatgpt_zip)
    conversation_id = client.get("/api/v1/conversations").json()[0]["id"]
    messages = client.get(f"/api/v1/conversations/{conversation_id}").json()["messages"]
    handoff_id = _manual_handoff(client, conversation_id)
    created = client.post(
        f"/api/v1/conversations/{conversation_id}/analysis",
        json={"handoff_id": handoff_id, "confirm_manual_authorship": True, "analysis": {"summary": "", "items": [{
            "kind": "procedure",
            "scope": "general",
            "canonical_text": "Inspect query plans before adding indexes.",
            "description": "A source-grounded procedure awaiting review.",
            "interpretation_class": "explicit",
            "source_message_ids": [messages[1]["id"]],
        }]}},
    )
    assert created.status_code == 200, created.text
    knowledge_id = created.json()["created"][0]["id"]

    permissions = client.put(
        "/api/v1/settings/providers/chatgpt/permissions",
        json={"allow_store": True, "allow_index": True, "allow_derive": True,
              "allow_strategy_analysis": True, "allow_cross_provider_transfer": True},
    )
    assert permissions.status_code == 200
    assert _review_provider(client, "chatgpt").status_code == 200
    assert _review_provider(client, "claude").status_code == 200
    objective = client.post("/api/v1/objectives", json={
        "title": "Review a database procedure",
        "objective_text": "Evaluate the supplied method.",
    }).json()["objective_id"]
    packet_request = {
        "destination_provider": "claude",
        "requested_role": "Critically review the selected knowledge.",
        "knowledge_item_ids": [knowledge_id],
    }

    rejected = client.post(f"/api/v1/objectives/{objective}/packets", json=packet_request)
    assert rejected.status_code == 403
    assert "user-confirmed or validated" in rejected.json()["detail"]

    reviewed = client.post(f"/api/v1/knowledge/{knowledge_id}/review", json={
        "decision": "confirm", "rationale": "The cited conversation supports this procedure.",
    })
    assert reviewed.status_code == 200
    accepted = client.post(f"/api/v1/objectives/{objective}/packets", json=packet_request)
    assert accepted.status_code == 200, accepted.text
    assert "Inspect query plans before adding indexes" in accepted.json()["body_text"]


def test_mixed_provider_knowledge_is_not_indexed_until_all_sources_allow_it(client, chatgpt_zip):
    _import_zip(client, chatgpt_zip)
    conversation_id = client.get("/api/v1/conversations").json()[0]["id"]
    messages = client.get(f"/api/v1/conversations/{conversation_id}").json()["messages"]
    handoff_id = _manual_handoff(client, conversation_id)
    analysis = client.post(
        f"/api/v1/conversations/{conversation_id}/analysis",
        json={"handoff_id": handoff_id, "confirm_manual_authorship": True, "analysis": {"summary": "", "items": [{
            "kind": "concept", "scope": "general",
            "canonical_text": "Cross-provider indexing permission invariant",
            "description": "Indexing must respect every provider source linked to a knowledge item.",
            "interpretation_class": "explicit", "source_message_ids": [messages[1]["id"]],
        }]}},
    )
    assert analysis.status_code == 200, analysis.text
    knowledge_id = analysis.json()["created"][0]["id"]
    assert client.get("/api/v1/search/knowledge", params={"q": "cross-provider indexing"}).json()

    # Introduce a second provider-backed evidence source whose local indexing is disabled.
    assert client.put("/api/v1/settings/providers/manual/permissions", json={
        "allow_store": True, "allow_index": False, "allow_derive": True,
        "allow_strategy_analysis": False, "allow_cross_provider_transfer": False,
    }).status_code == 200
    database = client.app.state.database
    workspace_id = client.app.state.workspace_id
    from mosaic.repositories import new_id, utc_now

    second_conversation_id = new_id()
    now = utc_now()
    with database.transaction() as connection:
        connection.execute(
            """INSERT INTO conversations(
                id,workspace_id,source_artifact_id,provider,provider_conversation_id,title,
                started_at,ended_at,imported_at,content_hash,metadata_json
            ) VALUES (?,?,NULL,'manual',NULL,'Unindexed source',NULL,NULL,?,NULL,'{}')""",
            (second_conversation_id, workspace_id, now),
        )
        connection.execute(
            """INSERT INTO knowledge_evidence(
                id,knowledge_item_id,evidence_type,stance,source_artifact_id,conversation_id,
                message_id,experiment_run_id,external_reference,exact_span,note,created_at
            ) VALUES (?,?, 'external_reference','qualifies',NULL,?,NULL,NULL,?,NULL,?,?)""",
            (new_id(), knowledge_id, second_conversation_id, "manual://source-2",
             "Second source with stricter index policy.", now),
        )
    assert client.get("/api/v1/search/knowledge", params={"q": "cross-provider indexing"}).json() == []

    enabled = client.put("/api/v1/settings/providers/manual/permissions", json={
        "allow_store": True, "allow_index": True, "allow_derive": True,
        "allow_strategy_analysis": False, "allow_cross_provider_transfer": False,
    })
    assert enabled.status_code == 200
    assert client.get("/api/v1/search/knowledge", params={"q": "cross-provider indexing"}).json()


def test_provider_policy_review_requires_explicit_acknowledgement_and_https(client):
    missing_ack = client.put("/api/v1/settings/providers/chatgpt/policy-review", json={
        "policy_url": "https://policy.example.test/chatgpt",
        "policy_version": "terms-2026-11",
        "policy_status": "allowed_with_conditions",
        "notes": "Conditions reviewed.",
    })
    assert missing_ack.status_code == 422

    insecure_url = client.put("/api/v1/settings/providers/chatgpt/policy-review", json={
        "policy_url": "http://policy.example.test/chatgpt",
        "policy_version": "terms-2026-11",
        "policy_status": "allowed_with_conditions",
        "notes": "Conditions reviewed.",
        "user_acknowledged": True,
    })
    assert insecure_url.status_code == 422

    reviewed = _review_provider(client, "chatgpt")
    assert reviewed.status_code == 200
    assert reviewed.json()["policy_status"] == "allowed_with_conditions"
    assert reviewed.json()["reviewed_by"] == "local_user"


def test_restricted_provider_policy_blocks_cross_provider_handoff(client, chatgpt_zip):
    _import_zip(client, chatgpt_zip)
    conversation_id = client.get("/api/v1/conversations").json()[0]["id"]
    assert client.put("/api/v1/settings/providers/chatgpt/permissions", json={
        "allow_store": True, "allow_index": True, "allow_derive": True,
        "allow_strategy_analysis": False, "allow_cross_provider_transfer": True,
    }).status_code == 200
    assert _review_provider(client, "chatgpt").status_code == 200
    assert _review_provider(client, "claude", status="restricted").status_code == 200
    response = client.post(
        f"/api/v1/conversations/{conversation_id}/analysis-packet",
        json={"destination_provider": "claude", "include_strategies": False},
    )
    assert response.status_code == 403
    assert "not marked allowed_with_conditions" in response.json()["detail"]


def test_import_can_store_without_enabling_local_indexing(client, chatgpt_zip):
    response = client.post(
        "/api/v1/imports",
        files={"file": ("conversations.zip", chatgpt_zip, "application/zip")},
        data={"confirm_local_storage": "true", "enable_local_indexing": "false"},
    )
    assert response.status_code == 200, response.text
    conversation = client.get("/api/v1/conversations").json()[0]
    assert conversation["message_count"] == 3
    assert client.get("/api/v1/search", params={"q": "query plan"}).json() == []
    policy = client.get("/api/v1/settings/providers").json()[0]
    assert policy["allow_store"] == 1
    assert policy["allow_index"] == 0


def test_external_analysis_requires_server_handoff_and_cannot_spoof_provider(client, chatgpt_zip):
    _import_zip(client, chatgpt_zip)
    conversation_id = client.get("/api/v1/conversations").json()[0]["id"]
    messages = client.get(f"/api/v1/conversations/{conversation_id}").json()["messages"]
    assert _review_provider(client, "chatgpt").status_code == 200
    packet = client.post(
        f"/api/v1/conversations/{conversation_id}/analysis-packet",
        json={"destination_provider": "chatgpt"},
    )
    assert packet.status_code == 200, packet.text
    payload = {"summary": "A returned observation.", "items": [{
        "kind": "claim", "scope": "personal", "canonical_text": "The query plan reveals a scan.",
        "description": "Source-linked candidate.", "interpretation_class": "explicit",
        "source_message_ids": [messages[1]["id"]],
    }]}

    spoofed = client.post(
        f"/api/v1/conversations/{conversation_id}/analysis",
        json={"analysis_provider": "local", "analysis": payload},
    )
    assert spoofed.status_code == 422  # Unknown field and missing server-issued handoff.

    missing_consent = client.post(
        f"/api/v1/conversations/{conversation_id}/analysis",
        json={"handoff_id": packet.json()["handoff_id"], "analysis": payload},
    )
    assert missing_consent.status_code == 400
    assert "confirm local storage" in missing_consent.json()["detail"].lower()

    accepted = client.post(
        f"/api/v1/conversations/{conversation_id}/analysis",
        json={"handoff_id": packet.json()["handoff_id"],
              "confirm_local_storage": True, "analysis": payload},
    )
    assert accepted.status_code == 200, accepted.text
    assert accepted.json()["analysis_provider"] == "chatgpt"
    assert client.get("/api/v1/settings/providers").json()[0]["allow_store"] == 1

    replay = client.post(
        f"/api/v1/conversations/{conversation_id}/analysis",
        json={"handoff_id": packet.json()["handoff_id"],
              "confirm_local_storage": True, "analysis": payload},
    )
    assert replay.status_code == 409
    assert "already been used" in replay.json()["detail"].lower()


def test_handoff_rechecks_cross_provider_permissions_at_ingestion(client, chatgpt_zip):
    _import_zip(client, chatgpt_zip)
    conversation_id = client.get("/api/v1/conversations").json()[0]["id"]
    messages = client.get(f"/api/v1/conversations/{conversation_id}").json()["messages"]
    assert client.put("/api/v1/settings/providers/chatgpt/permissions", json={
        "allow_store": True, "allow_index": True, "allow_derive": True,
        "allow_strategy_analysis": True, "allow_cross_provider_transfer": True,
    }).status_code == 200
    assert _review_provider(client, "chatgpt").status_code == 200
    assert _review_provider(client, "claude").status_code == 200
    packet = client.post(
        f"/api/v1/conversations/{conversation_id}/analysis-packet",
        json={"destination_provider": "claude"},
    )
    assert packet.status_code == 200, packet.text

    # Revoke source transfer permission after packet creation. Ingestion must re-check.
    assert client.put("/api/v1/settings/providers/chatgpt/permissions", json={
        "allow_store": True, "allow_index": True, "allow_derive": True,
        "allow_strategy_analysis": True, "allow_cross_provider_transfer": False,
    }).status_code == 200
    rejected = client.post(
        f"/api/v1/conversations/{conversation_id}/analysis",
        json={"handoff_id": packet.json()["handoff_id"],
              "confirm_local_storage": True, "analysis": {"summary": "", "items": [{
                  "kind": "claim", "scope": "personal", "canonical_text": "A source-grounded claim.",
                  "description": "", "interpretation_class": "explicit",
                  "source_message_ids": [messages[1]["id"]],
              }]}},
    )
    assert rejected.status_code == 403
    assert "cross-provider" in rejected.json()["detail"].lower()
    assert client.get("/api/v1/knowledge").json() == []


def test_analysis_handoff_is_bound_to_conversation_and_expires(client, chatgpt_zip):
    _import_zip(client, chatgpt_zip)
    conversation_id = client.get("/api/v1/conversations").json()[0]["id"]
    handoff_id = _manual_handoff(client, conversation_id)
    database = client.app.state.database
    with database.transaction() as connection:
        connection.execute(
            "UPDATE analysis_handoffs SET expires_at='2000-01-01T00:00:00+00:00' WHERE id=?",
            (handoff_id,),
        )
    expired = client.post(
        f"/api/v1/conversations/{conversation_id}/analysis",
        json={"handoff_id": handoff_id, "confirm_manual_authorship": True, "analysis": {"summary": "", "items": []}},
    )
    assert expired.status_code == 409
    assert "expired" in expired.json()["detail"].lower()


def test_manual_analysis_requires_explicit_authorship_attestation(client, chatgpt_zip):
    _import_zip(client, chatgpt_zip)
    conversation_id = client.get("/api/v1/conversations").json()[0]["id"]
    handoff_id = _manual_handoff(client, conversation_id)
    payload = {"summary": "", "items": []}
    rejected = client.post(
        f"/api/v1/conversations/{conversation_id}/analysis",
        json={"handoff_id": handoff_id, "analysis": payload},
    )
    assert rejected.status_code == 400
    assert "manually authored analysis" in rejected.json()["detail"].lower()


def test_external_policy_is_rechecked_after_handoff_creation(client, chatgpt_zip):
    _import_zip(client, chatgpt_zip)
    conversation_id = client.get("/api/v1/conversations").json()[0]["id"]
    messages = client.get(f"/api/v1/conversations/{conversation_id}").json()["messages"]
    assert client.put("/api/v1/settings/providers/chatgpt/permissions", json={
        "allow_store": True, "allow_index": True, "allow_derive": True,
        "allow_strategy_analysis": True, "allow_cross_provider_transfer": True,
    }).status_code == 200
    assert _review_provider(client, "chatgpt").status_code == 200
    assert _review_provider(client, "claude").status_code == 200
    packet = client.post(
        f"/api/v1/conversations/{conversation_id}/analysis-packet",
        json={"destination_provider": "claude"},
    )
    assert packet.status_code == 200, packet.text
    assert _review_provider(client, "claude", status="restricted").status_code == 200

    rejected = client.post(
        f"/api/v1/conversations/{conversation_id}/analysis",
        json={"handoff_id": packet.json()["handoff_id"],
              "confirm_local_storage": True, "analysis": {"summary": "", "items": [{
                  "kind": "claim", "scope": "personal", "canonical_text": "An attributed claim.",
                  "description": "", "interpretation_class": "explicit",
                  "source_message_ids": [messages[1]["id"]],
              }]}},
    )
    assert rejected.status_code == 403
    assert "claude" in rejected.json()["detail"].lower()
    assert client.get("/api/v1/knowledge").json() == []


def test_objective_response_rechecks_source_transfer_policy(client, chatgpt_zip):
    _import_zip(client, chatgpt_zip)
    conversation_id = client.get("/api/v1/conversations").json()[0]["id"]
    messages = client.get(f"/api/v1/conversations/{conversation_id}").json()["messages"]
    candidate = client.post(
        f"/api/v1/conversations/{conversation_id}/analysis",
        json={"handoff_id": _manual_handoff(client, conversation_id),
              "confirm_manual_authorship": True, "analysis": {"summary": "", "items": [{
                  "kind": "procedure", "scope": "general",
                  "canonical_text": "Check query plan before indexing.", "description": "",
                  "interpretation_class": "explicit", "source_message_ids": [messages[1]["id"]],
              }]}},
    )
    assert candidate.status_code == 200, candidate.text
    knowledge_id = candidate.json()["created"][0]["id"]
    assert client.put("/api/v1/settings/providers/chatgpt/permissions", json={
        "allow_store": True, "allow_index": True, "allow_derive": True,
        "allow_strategy_analysis": True, "allow_cross_provider_transfer": True,
    }).status_code == 200
    assert _review_provider(client, "chatgpt").status_code == 200
    assert _review_provider(client, "claude").status_code == 200
    reviewed = client.post(f"/api/v1/knowledge/{knowledge_id}/review", json={
        "decision": "confirm", "rationale": "The method is supported by the source conversation.",
    })
    assert reviewed.status_code == 200
    objective_id = client.post("/api/v1/objectives", json={
        "title": "Review diagnostic procedure", "objective_text": "Check the method.",
    }).json()["objective_id"]
    packet = client.post(f"/api/v1/objectives/{objective_id}/packets", json={
        "destination_provider": "claude", "requested_role": "Critique the procedure.",
        "knowledge_item_ids": [knowledge_id],
    })
    assert packet.status_code == 200, packet.text

    # The source permission can be revoked after packet creation; returned response must be blocked.
    assert client.put("/api/v1/settings/providers/chatgpt/permissions", json={
        "allow_store": True, "allow_index": True, "allow_derive": True,
        "allow_strategy_analysis": True, "allow_cross_provider_transfer": False,
    }).status_code == 200
    blocked = client.post(f"/api/v1/objectives/{objective_id}/responses", json={
        "session_id": packet.json()["session_id"], "model_label": "test-model",
        "response_text": "A review response.", "confirm_local_storage": True,
    })
    assert blocked.status_code == 400
    assert "cross-provider transfer" in blocked.json()["detail"].lower()