"""Parser for the common ChatGPT conversations.json export shape.

The parser is intentionally strict about structural invariants and permissive about
unknown metadata. It does not execute or interpret imported content.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

from mosaic.schemas import CanonicalConversation, CanonicalMessage, Role


class ImportFormatError(ValueError):
    """The source data is not a supported conversation export."""


def parse_datetime(value: Any) -> datetime | None:
    if value is None or value == "":
        return None
    try:
        if isinstance(value, (int, float)):
            return datetime.fromtimestamp(float(value), tz=UTC)
        if isinstance(value, str):
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
            return parsed.replace(tzinfo=UTC) if parsed.tzinfo is None else parsed
    except (ValueError, OverflowError, OSError):
        return None
    return None


def _safe_metadata(value: Any, *, max_chars: int = 16_000) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    # Preserve useful metadata while excluding large/raw nested message bodies.
    allowed = {
        "is_archived",
        "is_starred",
        "is_do_not_remember",
        "default_model_slug",
        "model_slug",
        "message_type",
        "status",
        "recipient",
        "channel",
        "content_type",
    }
    cleaned = {key: value[key] for key in allowed if key in value}
    try:
        encoded = json.dumps(cleaned, ensure_ascii=False, default=str)
    except (TypeError, ValueError):
        return {}
    if len(encoded) > max_chars:
        return {}
    return cleaned


def _content_to_text(content: Any) -> tuple[str, str]:
    if isinstance(content, str):
        return content, "text"
    if not isinstance(content, dict):
        return "", "unknown"
    content_type = str(content.get("content_type") or "text")[:80]
    parts = content.get("parts")
    if parts is None and isinstance(content.get("text"), str):
        parts = [content["text"]]
    if not isinstance(parts, list):
        return "", content_type
    text_parts: list[str] = []
    detected_modality = "text"
    for part in parts:
        if isinstance(part, str):
            text_parts.append(part)
        elif isinstance(part, dict):
            text_value = part.get("text") or part.get("content")
            if isinstance(text_value, str):
                text_parts.append(text_value)
            elif any(key in part for key in ("image", "image_url", "asset_pointer")):
                detected_modality = "mixed"
            elif any(key in part for key in ("audio", "video", "frames")):
                detected_modality = "mixed"
        # Non-text parts are intentionally not decoded in the MVP.
    if not text_parts and content_type not in {"text", "code"}:
        detected_modality = content_type
    return "\n".join(text_parts), detected_modality


def _normalise_role(value: Any) -> Role:
    role = str(value or "unknown").lower()
    if role in {"system", "developer", "user", "assistant", "tool"}:
        return role  # type: ignore[return-value]
    if role in {"function", "browser", "python"}:
        return "tool"
    return "unknown"


def _parse_mapping_conversation(raw: dict[str, Any]) -> CanonicalConversation:
    mapping = raw.get("mapping")
    if not isinstance(mapping, dict):
        raise ImportFormatError("Conversation is missing the expected message mapping")

    rows: list[tuple[int, float, str, dict[str, Any], dict[str, Any]]] = []
    for index, (node_id, node) in enumerate(mapping.items()):
        if not isinstance(node, dict):
            continue
        message = node.get("message")
        if not isinstance(message, dict):
            continue
        timestamp = parse_datetime(message.get("create_time"))
        sort_time = timestamp.timestamp() if timestamp else float(index)
        rows.append((index, sort_time, str(node_id), node, message))

    rows.sort(key=lambda row: (row[1], row[0]))
    node_to_provider_id: dict[str, str] = {}
    for _, _, node_id, node, message in rows:
        provider_id = str(message.get("id") or node_id)
        node_to_provider_id[node_id] = provider_id

    messages: list[CanonicalMessage] = []
    for sequence, (_, _, node_id, node, message) in enumerate(rows):
        author = message.get("author") if isinstance(message.get("author"), dict) else {}
        content_text, modality = _content_to_text(message.get("content"))
        parent_id = node.get("parent")
        parent_provider_id = node_to_provider_id.get(str(parent_id)) if parent_id else None
        metadata = _safe_metadata(message.get("metadata"))
        metadata["node_id"] = node_id
        messages.append(
            CanonicalMessage(
                provider_message_id=node_to_provider_id[node_id],
                parent_provider_message_id=parent_provider_id,
                sequence_no=sequence,
                role=_normalise_role(author.get("role")),
                author_label=str(author.get("name"))[:120] if author.get("name") else None,
                model_label=(
                    str(message.get("metadata", {}).get("model_slug"))[:120]
                    if isinstance(message.get("metadata"), dict)
                    and message.get("metadata", {}).get("model_slug")
                    else None
                ),
                created_at=parse_datetime(message.get("create_time")),
                content_text=content_text,
                modality=modality,
                metadata=metadata,
            )
        )

    if not messages:
        raise ImportFormatError("Conversation contains no parseable messages")
    started = parse_datetime(raw.get("create_time"))
    ended = parse_datetime(raw.get("update_time"))
    return CanonicalConversation(
        provider_conversation_id=str(raw.get("id") or raw.get("conversation_id") or "") or None,
        title=str(raw.get("title") or "Untitled conversation")[:500],
        started_at=started,
        ended_at=ended,
        metadata={
            "source_format": "chatgpt_mapping_v1",
            "is_archived": bool(raw.get("is_archived", False)),
        },
        messages=messages,
    )


def _parse_flat_conversation(raw: dict[str, Any]) -> CanonicalConversation:
    messages_raw = raw.get("messages")
    if not isinstance(messages_raw, list):
        raise ImportFormatError("Conversation is missing mapping or messages array")
    messages: list[CanonicalMessage] = []
    provider_ids: set[str] = set()
    for index, item in enumerate(messages_raw):
        if not isinstance(item, dict):
            continue
        author = item.get("author") if isinstance(item.get("author"), dict) else {}
        role = item.get("role") or author.get("role")
        content = item.get("content", item.get("text", ""))
        content_text, modality = _content_to_text(content)
        provider_id = str(item.get("id") or f"message-{index}")
        if provider_id in provider_ids:
            provider_id = f"{provider_id}-{index}"
        provider_ids.add(provider_id)
        parent = item.get("parent_id") or item.get("parent")
        messages.append(
            CanonicalMessage(
                provider_message_id=provider_id,
                parent_provider_message_id=str(parent) if parent else None,
                sequence_no=len(messages),
                role=_normalise_role(role),
                author_label=str(author.get("name"))[:120] if author.get("name") else None,
                model_label=str(item.get("model"))[:120] if item.get("model") else None,
                created_at=parse_datetime(item.get("create_time") or item.get("timestamp")),
                content_text=content_text,
                modality=modality,
                metadata=_safe_metadata(item.get("metadata")),
            )
        )
    if not messages:
        raise ImportFormatError("Conversation contains no parseable messages")
    return CanonicalConversation(
        provider_conversation_id=str(raw.get("id") or raw.get("conversation_id") or "") or None,
        title=str(raw.get("title") or "Untitled conversation")[:500],
        started_at=parse_datetime(raw.get("create_time") or raw.get("created_at")),
        ended_at=parse_datetime(raw.get("update_time") or raw.get("updated_at")),
        metadata={"source_format": "chatgpt_flat_v1"},
        messages=messages,
    )


def parse_chatgpt_json(payload: bytes) -> tuple[list[CanonicalConversation], list[str]]:
    try:
        raw_data = json.loads(payload.decode("utf-8-sig"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ImportFormatError("conversations.json is not valid UTF-8 JSON") from exc

    if isinstance(raw_data, dict) and isinstance(raw_data.get("conversations"), list):
        raw_data = raw_data["conversations"]
    if isinstance(raw_data, dict):
        raw_data = [raw_data]
    if not isinstance(raw_data, list):
        raise ImportFormatError("Expected an array of conversations")

    conversations: list[CanonicalConversation] = []
    warnings: list[str] = []
    for index, raw in enumerate(raw_data):
        if not isinstance(raw, dict):
            warnings.append(f"Conversation entry {index} was not an object and was skipped")
            continue
        try:
            conversation = (
                _parse_mapping_conversation(raw)
                if isinstance(raw.get("mapping"), dict)
                else _parse_flat_conversation(raw)
            )
            conversations.append(conversation)
        except (ImportFormatError, ValueError) as exc:
            warnings.append(f"Conversation entry {index} was skipped: {str(exc)[:240]}")
    if not conversations:
        raise ImportFormatError("No valid conversations could be parsed from this export")
    return conversations, warnings