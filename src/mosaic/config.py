"""Environment-backed application settings with safe local defaults."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse


def _int_env(name: str, default: int, *, minimum: int = 1) -> int:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        value = int(raw)
    except ValueError as exc:
        raise ValueError(f"{name} must be an integer") from exc
    if value < minimum:
        raise ValueError(f"{name} must be >= {minimum}")
    return value


@dataclass(frozen=True, slots=True)
class Settings:
    data_dir: Path
    host: str = "127.0.0.1"
    port: int = 8765
    max_upload_bytes: int = 100 * 1024 * 1024
    max_archive_entries: int = 2_500
    max_archive_uncompressed_bytes: int = 500 * 1024 * 1024
    max_archive_entry_bytes: int = 200 * 1024 * 1024
    max_compression_ratio: int = 200
    cors_origins: tuple[str, ...] = ("http://127.0.0.1:5173", "http://localhost:5173")
    ollama_base_url: str = "http://127.0.0.1:11434"
    ollama_model: str = ""

    def __post_init__(self) -> None:
        if self.host not in {"127.0.0.1", "localhost", "::1"}:
            raise ValueError("Mosaic must bind to a loopback address in this release")
        if not 1 <= self.port <= 65535:
            raise ValueError("MOSAIC_PORT must be between 1 and 65535")
        if not self.cors_origins:
            raise ValueError("At least one explicit loopback CORS origin must be configured")
        for origin in self.cors_origins:
            parsed = urlparse(origin)
            if parsed.scheme != "http" or parsed.hostname not in {"127.0.0.1", "localhost", "::1"}:
                raise ValueError("CORS origins must use HTTP and a loopback hostname")

    @classmethod
    def from_env(cls) -> "Settings":
        data_dir = Path(os.getenv("MOSAIC_DATA_DIR", "./data")).expanduser().resolve()
        origins = tuple(
            item.strip()
            for item in os.getenv(
                "MOSAIC_CORS_ORIGINS",
                "http://127.0.0.1:5173,http://localhost:5173",
            ).split(",")
            if item.strip()
        )
        host = os.getenv("MOSAIC_HOST", "127.0.0.1")
        return cls(
            data_dir=data_dir,
            host=host,
            port=_int_env("MOSAIC_PORT", 8765),
            max_upload_bytes=_int_env("MOSAIC_MAX_UPLOAD_BYTES", 100 * 1024 * 1024),
            max_archive_entries=_int_env("MOSAIC_MAX_ARCHIVE_ENTRIES", 2_500),
            max_archive_uncompressed_bytes=_int_env(
                "MOSAIC_MAX_ARCHIVE_UNCOMPRESSED_BYTES", 500 * 1024 * 1024
            ),
            max_archive_entry_bytes=_int_env(
                "MOSAIC_MAX_ARCHIVE_ENTRY_BYTES", 200 * 1024 * 1024
            ),
            max_compression_ratio=_int_env("MOSAIC_MAX_COMPRESSION_RATIO", 200),
            cors_origins=origins,
            ollama_base_url=os.getenv("MOSAIC_OLLAMA_BASE_URL", "http://127.0.0.1:11434"),
            ollama_model=os.getenv("MOSAIC_OLLAMA_MODEL", ""),
        )