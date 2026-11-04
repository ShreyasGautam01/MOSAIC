"""Command-line entry point."""

from __future__ import annotations

import argparse

import uvicorn

from mosaic.config import Settings


def main() -> None:
    parser = argparse.ArgumentParser(prog="mosaic")
    parser.add_argument("--port", type=int, default=None)
    args = parser.parse_args()
    settings = Settings.from_env()
    uvicorn.run(
        "mosaic.main:app",
        host=settings.host,
        port=args.port or settings.port,
        reload=False,
        log_level="info",
    )