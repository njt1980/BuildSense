"""Structured telemetry logging helpers."""

from __future__ import annotations

import logging
from typing import Any

from app.telemetry.context import get_context
from app.telemetry.dev_store import record_event
from app.telemetry.privacy import sanitize_mapping


logger = logging.getLogger("buildsense.telemetry")


def log_event(event: str, level: str = "info", message: str | None = None, **attributes: Any) -> None:
    """Emit a structured telemetry log event and mirror it to the local store."""
    safe_attributes = sanitize_mapping(attributes)
    extra = {
        "event": event,
        "telemetry_context": get_context(),
        "attributes": safe_attributes,
    }
    log_message = message or event
    log_level = getattr(logging, level.upper(), logging.INFO)
    logger.log(log_level, log_message, extra=extra)
    record_event(event, level=level, **safe_attributes)
