"""Tests for local telemetry request correlation and developer APIs."""

import pytest
from fastapi.testclient import TestClient
from pytest import MonkeyPatch
from types import SimpleNamespace

from app.core.config import settings
from app.main import app
from app.telemetry.context import set_context, reset_context
from app.telemetry.dev_store import local_telemetry_store
from app.telemetry.llm import traced_anthropic_messages_create
from app.telemetry.logging import log_event
from app.telemetry.nodes import instrument_node
from app.telemetry.tools import ToolRegistry


client = TestClient(app)


def test_request_id_is_generated_and_local_event_is_recorded() -> None:
    """Requests without X-Request-ID receive one and are recorded locally."""
    local_telemetry_store.clear()

    response = client.get("/health")

    assert response.status_code == 200
    request_id = response.headers.get("x-request-id")
    assert request_id

    events = local_telemetry_store.get_by_field("request_id", request_id)
    assert any(event["event"] == "request_started" for event in events)
    assert any(event["event"] == "request_completed" for event in events)


def test_safe_incoming_request_id_is_preserved() -> None:
    """Safe caller-provided request IDs are preserved in the response."""
    local_telemetry_store.clear()

    response = client.get("/health", headers={"X-Request-ID": "external-req-123"})

    assert response.status_code == 200
    assert response.headers["x-request-id"] == "external-req-123"
    assert local_telemetry_store.get_by_field("request_id", "external-req-123")


def test_eval_headers_are_recorded_in_local_context() -> None:
    """Local eval request headers are added to retained telemetry events."""
    local_telemetry_store.clear()

    response = client.get(
        "/health",
        headers={
            "X-Request-ID": "eval-req-123",
            "X-BuildSense-Eval": "true",
            "X-BuildSense-Eval-Suite": "agent_quality",
            "X-BuildSense-Eval-Case-Id": "case_001",
            "X-BuildSense-Dataset-Version": "2026-08-14",
        },
    )

    assert response.status_code == 200
    events = local_telemetry_store.get_by_field("request_id", "eval-req-123")
    assert events
    assert events[0]["is_eval"] is True
    assert events[0]["eval_suite"] == "agent_quality"
    assert events[0]["eval_case_id"] == "case_001"
    assert events[0]["dataset_version"] == "2026-08-14"


def test_local_telemetry_events_are_sanitized() -> None:
    """Sensitive telemetry attributes are redacted before local storage."""
    local_telemetry_store.clear()
    token = set_context({"request_id": "req_sanitize_test", "environment": "local", "service": "buildsense-api"})
    try:
        log_event(
            "secret_test",
            authorization="Bearer secret-token",
            anthropic_api_key="sk-secret",
            prompt="This is a sensitive user prompt.",
            duration_ms=12,
        )
    finally:
        reset_context(token)

    events = local_telemetry_store.get_by_field("request_id", "req_sanitize_test")
    assert len(events) == 1
    attributes = events[0]["attributes"]
    assert attributes["authorization"] == "[REDACTED]"
    assert attributes["anthropic_api_key"] == "[REDACTED]"
    assert attributes["prompt_hash"]
    assert attributes["prompt_length"] == 32
    assert "This is a sensitive user prompt." not in str(events[0])


def test_local_telemetry_api_is_disabled_outside_local(monkeypatch: MonkeyPatch) -> None:
    """Development telemetry endpoints are not available in production mode."""
    monkeypatch.setattr(settings, "environment", "production")
    monkeypatch.setattr(settings, "telemetry_enabled", True)
    monkeypatch.setattr(settings, "local_telemetry_viewer_enabled", True)

    response = client.get("/api/dev/telemetry/events")

    assert response.status_code == 404


def test_local_telemetry_api_honors_enabled_flag(monkeypatch: MonkeyPatch) -> None:
    """Development telemetry endpoints are hidden when telemetry is disabled."""
    monkeypatch.setattr(settings, "environment", "local")
    monkeypatch.setattr(settings, "telemetry_enabled", False)
    monkeypatch.setattr(settings, "local_telemetry_viewer_enabled", True)

    response = client.get("/api/dev/telemetry/events")

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_instrument_node_records_started_and_completed_events() -> None:
    """Instrumented nodes append lifecycle events to the local telemetry store."""
    local_telemetry_store.clear()
    token = set_context({"request_id": "req_node_test", "run_id": "run_node_test", "environment": "local"})

    async def node_handler(state: dict[str, object]) -> dict[str, object]:
        return {"status": "COMPLETED", "answer": 42}

    try:
        wrapped = instrument_node("test_node", node_handler)
        updates = await wrapped({"status": "ROUTING", "steps_taken": 0, "budget_spent_usd": 0.0})
    finally:
        reset_context(token)

    assert updates["status"] == "COMPLETED"
    events = local_telemetry_store.get_by_field("run_id", "run_node_test")
    event_names = [event["event"] for event in events]
    assert "orchestrator_node_started" in event_names
    assert "orchestrator_node_completed" in event_names


def test_tool_registry_records_tool_call_events() -> None:
    """Registered tools append started and completed events with wrapping status."""
    local_telemetry_store.clear()
    registry = ToolRegistry()
    registry.register(
        name="demo_tool",
        handler=lambda query: f'<untrusted_tool_output source="demo">{query}</untrusted_tool_output>',
        source="test",
        requires_untrusted_wrapping=True,
    )
    token = set_context({"request_id": "req_tool_test", "run_id": "run_tool_test", "environment": "local"})
    try:
        output = registry.call("demo_tool", query="hello")
    finally:
        reset_context(token)

    assert "hello" in output
    events = local_telemetry_store.get_by_field("run_id", "run_tool_test")
    event_names = [event["event"] for event in events]
    assert "tool_call_started" in event_names
    completed = next(event for event in events if event["event"] == "tool_call_completed")
    assert completed["attributes"]["tool_name"] == "demo_tool"
    assert completed["attributes"]["output_wrapped"] is True


@pytest.mark.asyncio
async def test_traced_anthropic_call_records_usage_and_cost() -> None:
    """LLM wrapper records token usage, cost, hashes, and completion status."""
    local_telemetry_store.clear()

    class Messages:
        async def create(self, **kwargs: object) -> SimpleNamespace:
            return SimpleNamespace(
                usage=SimpleNamespace(input_tokens=100, output_tokens=50),
                stop_reason="end_turn",
                content=[SimpleNamespace(type="text", text="done")],
            )

    client_mock = SimpleNamespace(messages=Messages())
    token = set_context({"request_id": "req_llm_test", "run_id": "run_llm_test", "environment": "local"})
    try:
        response = await traced_anthropic_messages_create(
            client_mock,
            model="claude-haiku-4-5-20251001",
            purpose="unit_test",
            is_byok=False,
            max_tokens=100,
            messages=[{"role": "user", "content": "hello"}],
        )
    finally:
        reset_context(token)

    assert response.stop_reason == "end_turn"
    events = local_telemetry_store.get_by_field("run_id", "run_llm_test")
    event_names = [event["event"] for event in events]
    assert "llm_call_started" in event_names
    completed = next(event for event in events if event["event"] == "llm_call_completed")
    assert completed["attributes"]["llm_model"] == "claude-haiku-4-5-20251001"
    assert completed["attributes"]["input_tokens"] == 100
    assert completed["attributes"]["output_tokens"] == 50
    assert completed["attributes"]["cost_usd"] > 0
