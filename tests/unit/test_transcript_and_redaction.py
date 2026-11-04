from __future__ import annotations

import pytest

from mosaic.importers.transcript import parse_transcript
from mosaic.security.redaction import redact_secrets
from mosaic.semantic.segmentation import segment_messages


def test_transcript_speaker_boundaries() -> None:
    conversation = parse_transcript("User: Hello\nAssistant: Hi\nUser: Another question")
    assert [message.role for message in conversation.messages] == ["user", "assistant", "user"]
    assert conversation.messages[2].content_text == "Another question"


def test_unlabelled_transcript_is_preserved_as_one_message() -> None:
    conversation = parse_transcript("A note without speaker labels\nSecond line")
    assert len(conversation.messages) == 1
    assert conversation.messages[0].role == "unknown"


def test_episode_segmentation_splits_at_user_turn() -> None:
    messages = [
        {"id": "1", "role": "user", "sequence_no": 0, "content_text": "Question A"},
        {"id": "2", "role": "assistant", "sequence_no": 1, "content_text": "Answer A"},
        {"id": "3", "role": "user", "sequence_no": 2, "content_text": "Question B"},
    ]
    episodes = segment_messages(messages)
    assert len(episodes) == 2
    assert episodes[0]["message_ids"] == ["1", "2"]
    assert episodes[1]["title"] == "Question B"


def test_secret_redaction() -> None:
    result = redact_secrets("api_key=abcdefghijklmno123456 and normal text")
    assert "abcdefghijklmno123456" not in result.text
    assert "REDACTED" in result.text
    assert "generic_api_key" in result.findings


def test_local_model_endpoint_rejects_non_loopback():
    from mosaic.semantic.ollama import LocalModelUnavailable, validate_loopback_endpoint
    import pytest

    assert validate_loopback_endpoint("http://127.0.0.1:11434") == "http://127.0.0.1:11434"
    with pytest.raises(LocalModelUnavailable, match="Remote"):
        validate_loopback_endpoint("http://example.com:11434")


def test_analysis_prompt_redacts_credentials_before_external_handoff():
    from mosaic.semantic.assisted import build_analysis_prompt

    secret = "ghp_" + "A" * 36
    prompt, report = build_analysis_prompt(
        {
            "title": "Credential handling",
            "messages": [
                {
                    "id": "message-1",
                    "sequence_no": 0,
                    "role": "user",
                    "content_text": f"Please inspect this token: {secret}",
                }
            ],
        },
        include_strategies=False,
    )

    assert secret not in prompt
    assert "[REDACTED:github_token]" in prompt
    assert report["redactions_count"] == 1
    assert report["detected_secret_types"] == ["github_token"]


def test_settings_reject_network_bind_and_non_loopback_cors(tmp_path):
    from mosaic.config import Settings

    with pytest.raises(ValueError, match="loopback"):
        Settings(data_dir=tmp_path, host="0.0.0.0")
    with pytest.raises(ValueError, match="CORS origins"):
        Settings(data_dir=tmp_path, cors_origins=("https://attacker.example",))