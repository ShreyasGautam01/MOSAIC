"""Conservative secret detection and outbound context redaction."""

from __future__ import annotations

import re
from dataclasses import dataclass

_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("private_key", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----[\s\S]+?-----END (?:RSA |EC |OPENSSH )?PRIVATE KEY-----")),
    ("aws_access_key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("github_token", re.compile(r"\b(?:gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,})\b")),
    ("openai_or_anthropic_key", re.compile(r"\bsk-(?:proj-|ant-)?[A-Za-z0-9_-]{20,}\b")),
    ("google_api_key", re.compile(r"\bAIza[0-9A-Za-z_-]{30,}\b")),
    ("generic_api_key", re.compile(r"(?i)\b(?:api[_-]?key|token|secret)\s*[:=]\s*[\"']?[A-Za-z0-9_./+=-]{16,}[\"']?")),
    ("password_assignment", re.compile(r"(?i)\bpassword\s*[:=]\s*[^\s,;]{6,}")),
)


@dataclass(frozen=True, slots=True)
class RedactionResult:
    text: str
    findings: tuple[str, ...]


def redact_secrets(text: str) -> RedactionResult:
    findings: list[str] = []
    output = text
    for label, pattern in _PATTERNS:
        output, count = pattern.subn(f"[REDACTED:{label}]", output)
        if count:
            findings.extend([label] * count)
    return RedactionResult(output, tuple(findings))