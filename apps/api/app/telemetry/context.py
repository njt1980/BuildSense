"""Request-scoped telemetry context using context variables."""

from __future__ import annotations

from contextvars import ContextVar, Token
from typing import Any, Dict, Optional


_telemetry_context: ContextVar[Dict[str, Any]] = ContextVar("buildsense_telemetry_context", default={})


def get_context() -> Dict[str, Any]:
    """Return a shallow copy of the current telemetry context."""
    return dict(_telemetry_context.get())


def set_context(values: Dict[str, Any]) -> Token[Dict[str, Any]]:
    """Replace the current telemetry context and return its reset token."""
    cleaned = {key: value for key, value in values.items() if value is not None}
    return _telemetry_context.set(cleaned)


def update_context(**values: Any) -> None:
    """Merge non-null values into the current telemetry context."""
    context = get_context()
    context.update({key: value for key, value in values.items() if value is not None})
    _telemetry_context.set(context)


def reset_context(token: Token[Dict[str, Any]]) -> None:
    """Reset the telemetry context to a previous token."""
    _telemetry_context.reset(token)


def get_context_value(key: str) -> Optional[Any]:
    """Return a single context value if present."""
    return _telemetry_context.get().get(key)

