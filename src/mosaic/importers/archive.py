"""Defensive ZIP inspection. Files are read in place and never extracted to disk."""

from __future__ import annotations

import stat
import zipfile
from dataclasses import dataclass
from io import BytesIO
from pathlib import PurePosixPath

from mosaic.config import Settings


class UnsafeArchiveError(ValueError):
    """The archive violates Mosaic's archive safety limits."""


@dataclass(frozen=True, slots=True)
class ArchiveContents:
    conversations_json: bytes
    warnings: tuple[str, ...]


def inspect_chat_archive(data: bytes, settings: Settings) -> ArchiveContents:
    if len(data) > settings.max_upload_bytes:
        raise UnsafeArchiveError("Archive exceeds the configured upload size limit")
    try:
        archive = zipfile.ZipFile(BytesIO(data))
    except (zipfile.BadZipFile, OSError) as exc:
        raise UnsafeArchiveError("The uploaded ZIP archive is malformed") from exc

    with archive:
        infos = archive.infolist()
        if len(infos) > settings.max_archive_entries:
            raise UnsafeArchiveError("Archive contains too many entries")

        seen: set[str] = set()
        total_uncompressed = 0
        candidates: list[zipfile.ZipInfo] = []
        warnings: list[str] = []

        for info in infos:
            raw_name = info.filename.replace("\\", "/")
            path = PurePosixPath(raw_name)
            if (
                path.is_absolute()
                or ".." in path.parts
                or not raw_name
                or (path.parts and ":" in path.parts[0])
            ):
                raise UnsafeArchiveError("Archive contains an unsafe path")
            normalised = str(path)
            if normalised in seen:
                raise UnsafeArchiveError("Archive contains duplicate entry paths")
            seen.add(normalised)

            mode = info.external_attr >> 16
            if stat.S_ISLNK(mode):
                raise UnsafeArchiveError("Archive contains a symbolic link")
            if info.flag_bits & 0x1:
                raise UnsafeArchiveError("Encrypted ZIP entries are not supported")
            if info.is_dir():
                continue
            if info.file_size > settings.max_archive_entry_bytes:
                raise UnsafeArchiveError("An archive entry exceeds the configured size limit")
            total_uncompressed += info.file_size
            if total_uncompressed > settings.max_archive_uncompressed_bytes:
                raise UnsafeArchiveError("Archive expands beyond the configured size limit")
            if info.file_size > 0 and info.compress_size == 0:
                raise UnsafeArchiveError("Archive entry has an invalid compression ratio")
            if info.compress_size > 0:
                ratio = info.file_size / info.compress_size
                if ratio > settings.max_compression_ratio:
                    raise UnsafeArchiveError("Archive compression ratio exceeds the safety limit")
            if path.name.lower() == "conversations.json":
                candidates.append(info)

        if not candidates:
            raise UnsafeArchiveError(
                "No conversations.json was found. This archive format is not supported yet."
            )
        if len(candidates) > 1:
            warnings.append(
                "Multiple conversations.json files were found; the first archive entry was used."
            )
        selected = candidates[0]
        try:
            payload = archive.read(selected)
        except (OSError, zipfile.BadZipFile, RuntimeError) as exc:
            raise UnsafeArchiveError("Could not safely read conversations.json") from exc
        if len(payload) > settings.max_archive_entry_bytes:
            raise UnsafeArchiveError("conversations.json exceeds the configured entry limit")
        return ArchiveContents(payload, tuple(warnings))