"""SQLite connection and migration management."""

from __future__ import annotations

import sqlite3
from contextlib import closing
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

MIGRATIONS_DIR = Path(__file__).parent / "migrations"


class DatabaseError(RuntimeError):
    """Raised for database setup or integrity failures."""


class Database:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path, timeout=10, isolation_level=None)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA busy_timeout = 10000")
        return connection

    def migrate(self) -> None:
        with closing(self.connect()) as connection:
            connection.execute("PRAGMA journal_mode = WAL")
            connection.execute(
                "CREATE TABLE IF NOT EXISTS schema_migrations "
                "(version TEXT PRIMARY KEY, applied_at TEXT NOT NULL)"
            )
            for migration in sorted(MIGRATIONS_DIR.glob("*.sql")):
                version = migration.stem
                exists = connection.execute(
                    "SELECT 1 FROM schema_migrations WHERE version = ?", (version,)
                ).fetchone()
                if exists:
                    continue
                sql = migration.read_text(encoding="utf-8")
                try:
                    connection.executescript(sql)
                    connection.execute(
                        "INSERT INTO schema_migrations(version, applied_at) "
                        "VALUES (?, strftime('%Y-%m-%dT%H:%M:%fZ','now'))",
                        (version,),
                    )
                except sqlite3.Error as exc:
                    raise DatabaseError(f"Migration {version} failed: {exc}") from exc
            try:
                connection.execute("SELECT rowid FROM messages_fts LIMIT 1")
                connection.execute("SELECT rowid FROM knowledge_fts LIMIT 1")
            except sqlite3.Error as exc:
                raise DatabaseError("SQLite FTS5 is required but unavailable") from exc

    @contextmanager
    def transaction(self) -> Iterator[sqlite3.Connection]:
        connection = self.connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def close_checkpoint(self) -> None:
        with closing(self.connect()) as connection:
            connection.execute("PRAGMA wal_checkpoint(TRUNCATE)")