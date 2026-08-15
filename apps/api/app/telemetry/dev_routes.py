"""Development-only telemetry inspection routes."""

from __future__ import annotations

from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException, status

from app.telemetry.dev_store import local_telemetry_store


router = APIRouter(prefix="/api/dev/telemetry", tags=["dev-telemetry"])


def _ensure_enabled() -> None:
    """Reject local telemetry access outside local/test environments."""
    if not local_telemetry_store.is_enabled():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Local telemetry viewer is disabled.")


@router.get("/events")
async def list_events() -> List[Dict[str, Any]]:
    """Return retained local telemetry events."""
    _ensure_enabled()
    return local_telemetry_store.list_events()


@router.get("/runs")
async def list_runs() -> List[Dict[str, Any]]:
    """Return recent telemetry run summaries."""
    _ensure_enabled()
    return local_telemetry_store.list_runs()


@router.get("/runs/{run_id}")
async def get_run(run_id: str) -> List[Dict[str, Any]]:
    """Return telemetry events for one run ID."""
    _ensure_enabled()
    return local_telemetry_store.get_by_field("run_id", run_id)


@router.get("/requests/{request_id}")
async def get_request(request_id: str) -> List[Dict[str, Any]]:
    """Return telemetry events for one request ID."""
    _ensure_enabled()
    return local_telemetry_store.get_by_field("request_id", request_id)


@router.get("/sessions/{session_id}")
async def get_session(session_id: str) -> List[Dict[str, Any]]:
    """Return telemetry events for one session ID."""
    _ensure_enabled()
    return local_telemetry_store.get_by_field("session_id", session_id)


@router.delete("")
async def clear_events() -> Dict[str, str]:
    """Clear all local telemetry events."""
    _ensure_enabled()
    local_telemetry_store.clear()
    return {"status": "cleared"}
