from __future__ import annotations

import io
import zipfile

import pytest

from mosaic.config import Settings
from mosaic.importers.archive import UnsafeArchiveError, inspect_chat_archive


def make_zip(name: str, content: bytes) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(name, content)
    return buffer.getvalue()


def test_archive_is_read_without_extracting(tmp_path) -> None:
    archive = make_zip("conversations.json", b"[]")
    result = inspect_chat_archive(archive, Settings(data_dir=tmp_path))
    assert result.conversations_json == b"[]"
    assert not list(tmp_path.iterdir())


def test_rejects_path_traversal(tmp_path) -> None:
    archive = make_zip("../conversations.json", b"[]")
    with pytest.raises(UnsafeArchiveError, match="unsafe path"):
        inspect_chat_archive(archive, Settings(data_dir=tmp_path))


def test_rejects_decompression_ratio(tmp_path) -> None:
    archive = make_zip("conversations.json", b"0" * 100_000)
    settings = Settings(data_dir=tmp_path, max_compression_ratio=2)
    with pytest.raises(UnsafeArchiveError, match="compression ratio"):
        inspect_chat_archive(archive, settings)


def test_rejects_missing_conversation_payload(tmp_path) -> None:
    archive = make_zip("unrelated.txt", b"hello")
    with pytest.raises(UnsafeArchiveError, match="No conversations.json"):
        inspect_chat_archive(archive, Settings(data_dir=tmp_path))