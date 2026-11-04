"""Optional local Ollama JSON inference adapter. It never contacts a remote host."""

from __future__ import annotations

import ipaddress
import json
from urllib.parse import urlparse

import httpx
from pydantic import ValidationError

from mosaic.config import Settings
from mosaic.schemas import AnalysisSubmission


class LocalModelUnavailable(RuntimeError):
    """The configured local model endpoint is unavailable or misconfigured."""


def validate_loopback_endpoint(url: str) -> str:
    parsed = urlparse(url)
    if parsed.scheme != "http" or not parsed.hostname:
        raise LocalModelUnavailable("Local model endpoint must be an HTTP loopback URL")
    host = parsed.hostname.lower()
    is_loopback = host == "localhost"
    try:
        is_loopback = is_loopback or ipaddress.ip_address(host).is_loopback
    except ValueError:
        pass
    if not is_loopback:
        raise LocalModelUnavailable("Remote model endpoints are disabled in the local-first MVP")
    return url.rstrip("/")


async def analyse_with_ollama(settings: Settings, prompt: str) -> AnalysisSubmission:
    if not settings.ollama_model.strip():
        raise LocalModelUnavailable("No local model is configured. Set MOSAIC_OLLAMA_MODEL.")
    endpoint = validate_loopback_endpoint(settings.ollama_base_url)
    payload = {
        "model": settings.ollama_model,
        "stream": False,
        "format": AnalysisSubmission.model_json_schema(),
        "messages": [{"role": "user", "content": prompt}],
        "options": {"temperature": 0.1},
    }
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(180.0, connect=5.0), trust_env=False) as client:
            response = await client.post(f"{endpoint}/api/chat", json=payload)
            response.raise_for_status()
            body = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise LocalModelUnavailable("Local Ollama request failed; use manual analysis instead") from exc
    content = body.get("message", {}).get("content")
    if not isinstance(content, str):
        raise LocalModelUnavailable("Local model returned an unexpected response shape")
    try:
        return AnalysisSubmission.model_validate(json.loads(content))
    except (json.JSONDecodeError, ValidationError) as exc:
        raise LocalModelUnavailable("Local model response did not satisfy Mosaic's extraction schema") from exc