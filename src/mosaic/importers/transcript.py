"""Parser for user-pasted plain text and Markdown transcripts."""

from __future__ import annotations

import re
from datetime import UTC, datetime
from pathlib import PurePath

from mosaic.schemas import CanonicalConversation, CanonicalMessage, Role

_SPEAKER = re.compile(r"^(?:#{1,6}\s*)?(user|assistant|system|developer|tool|you|chatgpt|claude|gemini)\s*:\s*(.*)$", re.I)


def _role(speaker: str) -> Role:
    value = speaker.lower()
    if value in {"you", "user"}:
        return "user"
    if value in {"chatgpt", "claude", "gemini", "assistant"}:
        return "assistant"
    if value in {"system", "developer", "tool"}:
        return value  # type: ignore[return-value]
    return "unknown"


def parse_transcript(text: str, filename: str | None = None) -> CanonicalConversation:
    if not text.strip():
        raise ValueError("Transcript is empty")
    title = PurePath(filename).stem if filename else "Pasted conversation"
    segments: list[tuple[str, list[str]]] = []
    current_role = "unknown"
    current_lines: list[str] = []
    saw_speaker = False

    for line in text.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        match = _SPEAKER.match(line.strip())
        if match:
            saw_speaker = True
            if current_lines:
                segments.append((current_role, current_lines))
            current_role = match.group(1)
            current_lines = [match.group(2)]
        else:
            current_lines.append(line)
    if current_lines:
        segments.append((current_role, current_lines))

    if not saw_speaker:
        segments = [("unknown", text.splitlines())]

    now = datetime.now(UTC)
    messages = [
        CanonicalMessage(
            provider_message_id=f"manual-{index + 1}",
            sequence_no=index,
            role=_role(speaker),
            author_label=speaker if speaker != "unknown" else None,
            created_at=None,
            content_text="\n".join(lines).strip(),
            modality="text",
            metadata={"source_format": "manual_transcript"},
        )
        for index, (speaker, lines) in enumerate(segments)
        if "\n".join(lines).strip()
    ]
    if not messages:
        raise ValueError("Transcript did not contain any message text")
    return CanonicalConversation(
        provider_conversation_id=None,
        title=title[:500],
        started_at=None,
        ended_at=None,
        metadata={"source_format": "manual_transcript", "imported_at": now.isoformat()},
        messages=messages,
    )