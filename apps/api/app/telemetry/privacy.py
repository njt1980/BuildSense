"""Privacy helpers for telemetry event sanitization."""

from __future__ import annotations

import hashlib
from typing import Any, Dict


_SECRET_KEY_PARTS = (
    "authorization",
    "api_key",
    "apikey",
    "anthropic",
    "jwt",
    "token",
    "password",
    "secret",
)

_RAW_CONTENT_KEYS = (
    "file_content",
    "raw_input_text_or_audio",
    "prompt",
    "messages",
    "response_content",
    "document",
)


def stable_hash(value: str) -> str:
    """Return a deterministic short SHA-256 hash for a string value."""
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:16]


def sanitize_mapping(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Return a telemetry-safe copy of a dictionary."""
    sanitized: Dict[str, Any] = {}
    for key, value in payload.items():
        lower_key = key.lower()
        if lower_key.endswith("_tokens") or lower_key in {"input_tokens", "output_tokens"}:
            sanitized[key] = value
            continue
        if any(part in lower_key for part in _SECRET_KEY_PARTS):
            sanitized[key] = "[REDACTED]"
            continue
        if any(part == lower_key for part in _RAW_CONTENT_KEYS):
            if isinstance(value, str):
                sanitized[f"{key}_hash"] = stable_hash(value)
                sanitized[f"{key}_length"] = len(value)
            else:
                sanitized[key] = "[REDACTED]"
            continue
        if isinstance(value, dict):
            sanitized[key] = sanitize_mapping(value)
        elif isinstance(value, list):
            sanitized[key] = f"[list:{len(value)}]"
        else:
            sanitized[key] = value
    return sanitized
