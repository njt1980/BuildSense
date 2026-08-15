"""FastAPI middleware for request telemetry context and local flow events."""

from __future__ import annotations

import time
from typing import Awaitable, Callable

from fastapi import Request, Response

from app.core.config import settings
from app.telemetry.context import reset_context, set_context
from app.telemetry.ids import generate_request_id, sanitize_external_request_id
from app.telemetry.logging import log_event
from app.telemetry.privacy import stable_hash


def _parse_bool_header(value: str | None) -> bool:
    """Return True when a request header explicitly represents a truthy value."""
    return (value or "").strip().lower() in {"1", "true", "yes", "y"}


async def telemetry_context_middleware(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    """Assign request correlation context, emit lifecycle events, and return request ID."""
    incoming_request_id = sanitize_external_request_id(request.headers.get("x-request-id"))
    request_id = incoming_request_id or generate_request_id()
    route = request.url.path
    client_host = request.client.host if request.client else "unknown"
    token = set_context(
        {
            "request_id": request_id,
            "environment": settings.environment,
            "service": settings.service_name,
            "http_method": request.method,
            "http_route": route,
            "client_ip_hash": stable_hash(client_host),
            "is_eval": _parse_bool_header(request.headers.get("x-buildsense-eval")),
            "eval_suite": request.headers.get("x-buildsense-eval-suite"),
            "eval_case_id": request.headers.get("x-buildsense-eval-case-id"),
            "dataset_version": request.headers.get("x-buildsense-dataset-version"),
            "model_version": request.headers.get("x-buildsense-model-version"),
            "prompt_version": request.headers.get("x-buildsense-prompt-version"),
        }
    )
    started_at = time.perf_counter()
    try:
        log_event("request_started", method=request.method, route=route)
        response = await call_next(request)
        duration_ms = round((time.perf_counter() - started_at) * 1000, 2)
        response.headers["X-Request-ID"] = request_id
        log_event(
            "request_completed",
            method=request.method,
            route=route,
            status_code=response.status_code,
            duration_ms=duration_ms,
        )
        return response
    except Exception as exc:
        duration_ms = round((time.perf_counter() - started_at) * 1000, 2)
        log_event(
            "request_failed",
            level="error",
            method=request.method,
            route=route,
            duration_ms=duration_ms,
            error_type=type(exc).__name__,
        )
        raise
    finally:
        reset_context(token)
