from __future__ import annotations

import io
import json
import zipfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from mosaic.api import create_app
from mosaic.config import Settings
from mosaic.db.database import Database


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    return Settings(data_dir=tmp_path / "mosaic-data")


@pytest.fixture
def database(settings: Settings) -> Database:
    db = Database(settings.data_dir / "mosaic.sqlite3")
    db.migrate()
    return db


@pytest.fixture
def client(settings: Settings):
    app = create_app(settings=settings)
    with TestClient(app, base_url="http://127.0.0.1") as test_client:
        yield test_client


def chatgpt_export() -> bytes:
    export = [
        {
            "id": "conv-1",
            "title": "SQLite indexing discussion",
            "create_time": 1_700_000_000,
            "update_time": 1_700_000_120,
            "mapping": {
                "root": {"id": "root", "parent": None, "children": ["m1"], "message": None},
                "m1": {
                    "id": "m1", "parent": "root", "children": ["m2"],
                    "message": {
                        "id": "m1", "author": {"role": "user"},
                        "create_time": 1_700_000_001,
                        "content": {"content_type": "text", "parts": ["How should I index a SQLite table?"]},
                        "metadata": {},
                    },
                },
                "m2": {
                    "id": "m2", "parent": "m1", "children": ["m3"],
                    "message": {
                        "id": "m2", "author": {"role": "assistant"},
                        "create_time": 1_700_000_002,
                        "content": {"content_type": "text", "parts": ["Inspect the query plan before adding an index."]},
                        "metadata": {"model_slug": "fixture-model"},
                    },
                },
                "m3": {
                    "id": "m3", "parent": "m2", "children": [],
                    "message": {
                        "id": "m3", "author": {"role": "user"},
                        "create_time": 1_700_000_003,
                        "content": {"content_type": "text", "parts": ["Why?"]},
                        "metadata": {},
                    },
                },
            },
        }
    ]
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("conversations.json", json.dumps(export))
    return buffer.getvalue()


@pytest.fixture
def chatgpt_zip() -> bytes:
    return chatgpt_export()