"""Telemetry wrappers for orchestrator nodes."""

from __future__ import annotations

import time
from typing import Any, Awaitable, Callable, Dict

from app.telemetry.ids import generate_id
from app.telemetry.logging import log_event


AgentNode = Callable[[Any], Awaitable[Dict[str, Any]]]


def instrument_node(node_name: str, handler: AgentNode) -> AgentNode:
    """Wrap an async orchestrator node with local telemetry lifecycle events."""

    async def wrapped(state: Any) -> Dict[str, Any]:
        step_id = generate_id("step")
        started_at = time.perf_counter()
        state_dict = state if isinstance(state, dict) else {}
        status_before = state_dict.get("status")
        log_event(
            "orchestrator_node_started",
            node_name=node_name,
            step_id=step_id,
            status_before=str(status_before),
            steps_taken=state_dict.get("steps_taken"),
            budget_spent_usd=state_dict.get("budget_spent_usd"),
        )
        try:
            updates = await handler(state)
            duration_ms = round((time.perf_counter() - started_at) * 1000, 2)
            status_after = updates.get("status", state_dict.get("status"))
            log_event(
                "orchestrator_node_completed",
                node_name=node_name,
                step_id=step_id,
                status_before=str(status_before),
                status_after=str(status_after),
                duration_ms=duration_ms,
                update_keys=sorted(updates.keys()),
            )
            return updates
        except Exception as exc:
            duration_ms = round((time.perf_counter() - started_at) * 1000, 2)
            log_event(
                "orchestrator_node_failed",
                level="error",
                node_name=node_name,
                step_id=step_id,
                status_before=str(status_before),
                duration_ms=duration_ms,
                error_type=type(exc).__name__,
            )
            raise

    return wrapped
