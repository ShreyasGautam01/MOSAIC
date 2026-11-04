"""Deterministic segmentation: new user turns start new discussion episodes."""

from __future__ import annotations

from typing import Any


def segment_messages(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not messages:
        return []
    episodes: list[list[dict[str, Any]]] = []
    current: list[dict[str, Any]] = []
    for message in messages:
        if message["role"] == "user" and current and any(
            item["role"] == "user" for item in current
        ):
            episodes.append(current)
            current = []
        current.append(message)
    if current:
        episodes.append(current)

    result: list[dict[str, Any]] = []
    for index, episode in enumerate(episodes, start=1):
        user_message = next((m for m in episode if m["role"] == "user"), episode[0])
        title = " ".join(user_message["content_text"].split())[:120] or f"Episode {index}"
        last_assistant = next(
            (m for m in reversed(episode) if m["role"] == "assistant" and m["content_text"].strip()),
            None,
        )
        result.append({
            "episode_no": index,
            "title": title,
            "start_sequence": episode[0]["sequence_no"],
            "end_sequence": episode[-1]["sequence_no"],
            "message_ids": [m["id"] for m in episode],
            "message_count": len(episode),
            "user_request": user_message["content_text"][:2_000],
            "last_assistant_excerpt": (last_assistant["content_text"][:1_200] if last_assistant else ""),
            "analysis_status": "not_analysed",
            "segmentation_method": "user_turn_boundary_v1",
        })
    return result