from __future__ import annotations

import json

import pytest

from mosaic.importers.chatgpt import ImportFormatError, parse_chatgpt_json


def test_parses_mapping_and_preserves_message_graph() -> None:
    payload = json.dumps([
        {
            "id": "c1", "title": "Example", "mapping": {
                "n1": {"parent": None, "message": None},
                "n2": {"parent": "n1", "message": {
                    "id": "m2", "author": {"role": "user"}, "create_time": 10,
                    "content": {"parts": ["Hello"]},
                }},
                "n3": {"parent": "n2", "message": {
                    "id": "m3", "author": {"role": "assistant"}, "create_time": 11,
                    "content": {"parts": ["World"]},
                }},
            },
        }
    ]).encode()
    conversations, warnings = parse_chatgpt_json(payload)
    assert not warnings
    assert len(conversations) == 1
    assert [item.role for item in conversations[0].messages] == ["user", "assistant"]
    assert conversations[0].messages[1].parent_provider_message_id == "m2"
    assert conversations[0].messages[0].content_text == "Hello"


def test_parses_flat_shape() -> None:
    payload = json.dumps([{
        "id": "c1", "title": "Flat", "messages": [
            {"id": "m1", "role": "user", "text": "Question"},
            {"id": "m2", "role": "assistant", "text": "Answer"},
        ],
    }]).encode()
    conversations, _ = parse_chatgpt_json(payload)
    assert len(conversations[0].messages) == 2
    assert conversations[0].messages[1].role == "assistant"


def test_rejects_invalid_json() -> None:
    with pytest.raises(ImportFormatError):
        parse_chatgpt_json(b"{not json")


def test_skips_invalid_entries_but_keeps_valid_conversation() -> None:
    payload = json.dumps([{"bad": True}, {
        "id": "valid", "messages": [{"id": "m1", "role": "user", "text": "Hi"}],
    }]).encode()
    conversations, warnings = parse_chatgpt_json(payload)
    assert len(conversations) == 1
    assert warnings