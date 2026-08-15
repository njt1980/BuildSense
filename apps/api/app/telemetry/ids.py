"""Identifier generation utilities for telemetry correlation."""

from __future__ import annotations

import re
import uuid


_SAFE_EXTERNAL_ID_PATTERN = re.compile(r"^[A-Za-z0-9_.:-]{1,128}$")


def generate_id(prefix: str) -> str:
    """Return a compact correlation identifier with the provided prefix."""
    return f"{prefix}_{uuid.uuid4().hex}"


def generate_request_id() -> str:
    """Return a new request identifier."""
    return generate_id("req")


def generate_run_id() -> str:
    """Return a new orchestration run identifier."""
    return generate_id("run")


def sanitize_external_request_id(value: str | None) -> str | None:
    """Return a safe external request ID or None when the value is invalid."""
    if not value:
        return None
    candidate = value.strip()
    if not _SAFE_EXTERNAL_ID_PATTERN.fullmatch(candidate):
        return None
    return candidate

