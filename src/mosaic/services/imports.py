"""Import orchestration: size limits, format selection, policy gates and persistence."""

from __future__ import annotations

import hashlib
import os
import uuid
from dataclasses import dataclass
from pathlib import Path, PurePath

from mosaic.config import Settings
from mosaic.db.database import Database
from mosaic.importers.archive import UnsafeArchiveError, inspect_chat_archive
from mosaic.importers.chatgpt import ImportFormatError, parse_chatgpt_json
from mosaic.importers.transcript import parse_transcript
from mosaic.repositories import (
    find_duplicate_source,
    persist_import,
    record_user_permissions,
)


class ImportRejected(ValueError):
    """The import cannot be accepted under configured safety or consent rules."""


@dataclass(frozen=True, slots=True)
class ImportOutcome:
    source_artifact_id: str
    provider: str
    conversation_count: int
    message_count: int
    duplicate: bool
    warnings: list[str]


def _store_source(data: bytes, sha256: str, filename: str | None, data_dir: Path) -> str:
    suffix = PurePath(filename or "source.txt").suffix.lower()
    if suffix not in {".zip", ".json", ".txt", ".md"}:
        suffix = ".bin"
    relative = Path("sources") / sha256[:2] / f"{sha256}{suffix}"
    target = data_dir / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    if not target.exists():
        temporary = target.with_name(f"{target.name}.{uuid.uuid4().hex}.tmp")
        try:
            with temporary.open("xb") as handle:
                handle.write(data)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, target)
        finally:
            if temporary.exists():
                temporary.unlink(missing_ok=True)
    return relative.as_posix()


def execute_import(
    database: Database,
    settings: Settings,
    *,
    workspace_id: str,
    filename: str | None,
    data: bytes,
    confirm_local_storage: bool,
    enable_local_indexing: bool,
    enable_semantic_analysis: bool,
    enable_strategy_analysis: bool,
    enable_cross_provider_transfer: bool,
) -> ImportOutcome:
    if not confirm_local_storage:
        raise ImportRejected("Confirm that you want to store this archive locally before importing")
    if not data:
        raise ImportRejected("Uploaded file is empty")
    if len(data) > settings.max_upload_bytes:
        raise ImportRejected("Upload exceeds the configured size limit")

    name = PurePath(filename or "upload.txt").name
    extension = Path(name).suffix.lower()
    warnings: list[str] = []

    if extension == ".zip":
        archive = inspect_chat_archive(data, settings)
        conversations, parser_warnings = parse_chatgpt_json(archive.conversations_json)
        provider = "chatgpt"
        source_type = "archive"
        parser_name = "chatgpt_export"
        warnings.extend(archive.warnings)
        warnings.extend(parser_warnings)
    elif extension == ".json":
        conversations, parser_warnings = parse_chatgpt_json(data)
        provider = "chatgpt"
        source_type = "json"
        parser_name = "chatgpt_json"
        warnings.extend(parser_warnings)
    elif extension in {".txt", ".md"}:
        try:
            text = data.decode("utf-8-sig")
        except UnicodeDecodeError as exc:
            raise ImportRejected("Transcript must be UTF-8 text") from exc
        try:
            conversations = [parse_transcript(text, name)]
        except ValueError as exc:
            raise ImportRejected(str(exc)) from exc
        provider = "manual"
        source_type = "markdown" if extension == ".md" else "text"
        parser_name = "manual_transcript"
    else:
        raise ImportRejected("Supported uploads are ChatGPT ZIP/JSON exports and TXT/Markdown transcripts")

    if len(conversations) > 20_000:
        raise ImportRejected("Archive contains more than 20,000 conversations")
    message_count = sum(len(conversation.messages) for conversation in conversations)
    if message_count > 500_000:
        raise ImportRejected("Archive contains more than 500,000 messages")

    digest = hashlib.sha256(data).hexdigest()
    duplicate = find_duplicate_source(database, workspace_id, digest)
    if duplicate:
        return ImportOutcome(
            source_artifact_id=duplicate["id"], provider=duplicate["provider"],
            conversation_count=0, message_count=0, duplicate=True,
            warnings=["This exact source archive has already been imported."],
        )

    record_user_permissions(
        database, workspace_id, provider,
        allow_store=True,
        allow_index=enable_local_indexing,
        allow_derive=enable_semantic_analysis,
        allow_strategy_analysis=enable_semantic_analysis and enable_strategy_analysis,
        allow_cross_provider_transfer=enable_cross_provider_transfer,
    )
    relative_path = _store_source(data, digest, name, settings.data_dir)
    try:
        artifact_id, conversation_count, persisted_messages = persist_import(
            database,
            workspace_id=workspace_id,
            provider=provider,
            source_type=source_type,
            filename=name,
            storage_relpath=relative_path,
            source_bytes=data,
            conversations=conversations,
            parser_name=parser_name,
            warnings=warnings,
        )
    except Exception:
        # Keep any pre-existing content-addressed file; remove only if no DB row owns it.
        if not find_duplicate_source(database, workspace_id, digest):
            (settings.data_dir / relative_path).unlink(missing_ok=True)
        raise
    return ImportOutcome(
        source_artifact_id=artifact_id,
        provider=provider,
        conversation_count=conversation_count,
        message_count=persisted_messages,
        duplicate=False,
        warnings=warnings,
    )