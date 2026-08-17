"""Bounded in-memory telemetry store for local development."""

from __future__ import annotations

from collections import deque
from datetime import datetime, timezone
from threading import RLock
from typing import Any, Deque, Dict, List, Optional

from app.core.config import settings
from app.telemetry.context import get_context
from app.telemetry.privacy import sanitize_mapping


TelemetryEvent = Dict[str, Any]


class LocalTelemetryStore:
    """Process-local bounded telemetry event buffer for local debugging."""

    def __init__(self) -> None:
        """Initialize the local event buffer."""
        self._lock = RLock()
        self._events: Deque[TelemetryEvent] = deque(maxlen=settings.local_telemetry_max_events)

    def is_enabled(self) -> bool:
        """Return whether local telemetry viewing is enabled."""
        return (
            settings.telemetry_enabled
            and settings.local_telemetry_viewer_enabled
            and settings.environment in {"local", "test"}
        )

    def append(self, event: str, level: str = "info", **attributes: Any) -> None:
        """Append a sanitized telemetry event to the local bounded buffer."""
        if not self.is_enabled():
            return

        context = get_context()
        payload: TelemetryEvent = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": level,
            "event": event,
            **context,
            "attributes": sanitize_mapping(attributes),
        }
        with self._lock:
            self._events.append(payload)

    def list_events(self) -> List[TelemetryEvent]:
        """Return all retained events in insertion order."""
        with self._lock:
            return list(self._events)

    def clear(self) -> None:
        """Clear all retained local telemetry events."""
        with self._lock:
            self._events.clear()

    def get_by_field(self, field_name: str, field_value: str) -> List[TelemetryEvent]:
        """Return events matching a top-level field value."""
        with self._lock:
            return [event for event in self._events if event.get(field_name) == field_value]

    def list_runs(self) -> List[Dict[str, Any]]:
        """Return compact summaries for recent run IDs."""
        summaries: Dict[str, Dict[str, Any]] = {}
        with self._lock:
            events = list(self._events)

        for event in events:
            run_id = event.get("run_id")
            if not run_id:
                continue
            summary = summaries.setdefault(
                str(run_id),
                {
                    "run_id": run_id,
                    "request_id": event.get("request_id"),
                    "session_id": event.get("session_id"),
                    "started_at": event.get("timestamp"),
                    "last_event_at": event.get("timestamp"),
                    "event_count": 0,
                    "status": "unknown",
                    "is_eval": event.get("is_eval", False),
                    "eval_suite": event.get("eval_suite"),
                    "eval_case_id": event.get("eval_case_id"),
                    "total_cost_usd": 0.0,
                },
            )
            summary["last_event_at"] = event.get("timestamp")
            summary["event_count"] += 1
            summary["is_eval"] = bool(summary.get("is_eval") or event.get("is_eval", False))
            summary["eval_suite"] = summary.get("eval_suite") or event.get("eval_suite")
            summary["eval_case_id"] = summary.get("eval_case_id") or event.get("eval_case_id")
            
            attrs = event.get("attributes") or {}
            cost_val = attrs.get("cost_usd", 0.0)
            if cost_val:
                summary["total_cost_usd"] += float(cost_val)

            if event.get("event") in {"orchestration_completed", "orchestration_failed", "orchestration_paused"}:
                summary["status"] = str(event.get("event")).replace("orchestration_", "")

        return sorted(summaries.values(), key=lambda item: str(item["last_event_at"]), reverse=True)[
            : settings.local_telemetry_max_runs
        ]


local_telemetry_store = LocalTelemetryStore()


def record_event(event: str, level: str = "info", **attributes: Any) -> None:
    """Record a sanitized event into the local telemetry store."""
    local_telemetry_store.append(event, level=level, **attributes)
