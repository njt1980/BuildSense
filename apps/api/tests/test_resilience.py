"""Resilience and edge-case tests for BuildSense backend orchestration.

This module contains deterministic pytest scenarios for:
- HITL and multi-turn resumption
- Redis budget enforcement and BYOK bypass handling
- LLM tool failure fallback behavior
- FastAPI middleware and global rate limiting
- Untrusted tool output wrapping and context pruning
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.core.auth import AuthenticatedUser, get_current_user
from app.core.orchestrator import Orchestrator, orchestrator
from app.db.postgres import postgres_client
from app.db.redis import MockRedis, redis_client
from app.models.state import Message, ProcessComponents, SessionMode, SessionState, SessionStatus
from app.models.state import FailureMetadata, FailureSeverity
from app.telemetry.llm import traced_anthropic_messages_create
from app.telemetry.logging import log_event

client = TestClient(app)


def test_failure_metadata_is_typed_and_bounded() -> None:
    """Failure metadata exposes stable semantics and rejects oversized reasons."""
    failure = FailureMetadata(
        node="sanitize_input",
        category="provider_authentication",
        severity=FailureSeverity.USER_ACTIONABLE,
        retryable=True,
        reason="Provider rejected the request",
    )
    assert failure.severity is FailureSeverity.USER_ACTIONABLE
    with pytest.raises(ValueError):
        FailureMetadata(
            node="node",
            category="provider",
            severity=FailureSeverity.DEGRADED,
            retryable=True,
            reason="x" * 241,
        )


@pytest.mark.asyncio
async def test_llm_failure_telemetry_is_sanitized_and_re_raises() -> None:
    """Provider failures are observable without persisting the raw exception payload."""
    client_mock = MagicMock()
    client_mock.messages.create = AsyncMock(side_effect=RuntimeError("secret-key=sk-test\nprovider unavailable"))
    with patch("app.telemetry.llm.log_event") as emit:
        with pytest.raises(RuntimeError):
            await traced_anthropic_messages_create(
                client_mock,
                model="claude-3-haiku",
                purpose="test",
                is_byok=False,
                messages=[{"role": "user", "content": "hello"}],
            )
    failed = next(call for call in emit.call_args_list if call.args[0] == "llm_call_failed")
    assert failed.kwargs["error_type"] == "RuntimeError"
    assert "sk-test" not in failed.kwargs["error_reason"]
    assert len(failed.kwargs["error_reason"]) <= 240


@pytest.mark.asyncio
async def test_sanitize_provider_auth_failure_returns_visible_failed_state() -> None:
    """Anthropic auth failures during sanitization must not fall through to healthy routing."""
    local_orchestrator = Orchestrator()
    state = {
        "session_id": "session-provider-auth-001",
        "mode": SessionMode.OPTIMIZER,
        "status": SessionStatus.ROUTING,
        "budget_spent_usd": 0.0,
        "max_budget_usd": 1.25,
        "steps_taken": 0,
        "max_steps": 15,
        "messages": [Message(role="user", content="I run a courier desk and assign delivery routes in WhatsApp.")],
        "metadata": {},
        "clarification_questions": [],
        "clarification_responses": {},
        "dag_plan": [],
        "company_name": None,
        "company_industry": None,
        "company_core_tools": None,
        "process_components": {},
        "user_constraints": [],
        "lang": "en",
        "playback_confirmed": False,
        "playback_shown": False,
        "clarification_turns": 0,
    }

    with patch("app.core.orchestrator.HAS_ANTHROPIC", True), \
         patch("app.core.orchestrator.settings.anthropic_api_key", "sk-test-secret"), \
         patch("app.core.orchestrator.AsyncAnthropic", return_value=MagicMock()), \
         patch("app.core.orchestrator.traced_anthropic_messages_create", AsyncMock(side_effect=RuntimeError("401 Unauthorized sk-test-secret"))), \
         patch.object(local_orchestrator, "_save_intermediate_state", AsyncMock()):
        updates = await local_orchestrator._node_sanitize_input(state)

    assert updates["status"] == SessionStatus.FAILED
    assert updates["failure"]["category"] == "provider_authentication"
    assert updates["failure"]["severity"] == FailureSeverity.USER_ACTIONABLE
    assert "sk-test-secret" not in repr(updates)
    assert updates["metadata"]["failure_reason"] == "AI provider authentication failed. Check the configured provider key."


def test_log_event_mirrors_only_sanitized_attributes() -> None:
    """The structured logger receives sanitized attributes before persistence."""
    with patch("app.telemetry.logging.logger.log") as logger_log, patch("app.telemetry.logging.record_event"):
        log_event("test_event", secret="sk-test-secret", nested={"token": "secret"})
    logged_attributes = logger_log.call_args.kwargs["extra"]["attributes"]
    assert "sk-test-secret" not in repr(logged_attributes)


@pytest.fixture(autouse=True)
def clear_dependency_overrides() -> None:
    """Ensure FastAPI dependency overrides are cleared between tests."""
    yield
    app.dependency_overrides.clear()


@pytest.fixture
def authenticated_user() -> AuthenticatedUser:
    return AuthenticatedUser(
        id="00000000-0000-0000-0000-000000000000",
        email="test@buildsense.local"
    )


@pytest.fixture
def mock_postgres_store() -> dict[str, str]:
    """Provide an in-memory session state store for persistence assertions."""
    store: dict[str, str] = {}

    async def fake_connect() -> None:
        return None

    async def fake_save_session_state(state: SessionState) -> None:
        store[state.session_id] = state.model_dump_json()

    async def fake_get_session_state(session_id: str) -> SessionState | None:
        payload = store.get(session_id)
        if not payload:
            return None
        return SessionState.model_validate_json(payload)

    async def fake_get_project(project_id: str) -> None:
        return None

    async def fake_get_company(company_id: str) -> None:
        return None

    with patch.object(postgres_client, "connect", AsyncMock(side_effect=fake_connect)), \
         patch.object(postgres_client, "save_session_state", AsyncMock(side_effect=fake_save_session_state)), \
         patch.object(postgres_client, "get_session_state", AsyncMock(side_effect=fake_get_session_state)), \
         patch.object(postgres_client, "get_project", AsyncMock(side_effect=fake_get_project)), \
         patch.object(postgres_client, "get_company", AsyncMock(side_effect=fake_get_company)), \
         patch.object(postgres_client, "update_project_mode_and_title", AsyncMock()), \
         patch.object(postgres_client, "save_graph", AsyncMock()):
        yield store


@pytest.fixture
def mock_redis_client() -> MockRedis:
    """Replace the Redis client with an in-memory mock for budget/rate-limit tests."""
    fake_client = MockRedis()
    redis_client.client = fake_client
    redis_client.redis_url = "redis://mock"
    return fake_client


# 1. HITL & Multi-Turn Loops

@pytest.mark.asyncio
async def test_hitl_pause_serializes_state_and_resumes_cleanly(
    mock_postgres_store: dict[str, str],
    mock_redis_client: MockRedis,
) -> None:
    """The LangGraph state machine pauses for clarification and persists state to the DB."""
    orchestrator = Orchestrator()

    initial_state = SessionState(
        session_id="session-hitl-001",
        mode=SessionMode.OPTIMIZER,
        status=SessionStatus.ROUTING,
        budget_spent_usd=0.0,
        max_budget_usd=1.25,
        steps_taken=0,
        max_steps=15,
        messages=[Message(role="user", content="Too short")],
    )

    with patch("app.core.orchestrator.HAS_ANTHROPIC", False):
        paused_state = await orchestrator.run_pipeline(initial_state)

    assert paused_state.status == SessionStatus.AWAITING_CLARIFICATION
    assert paused_state.clarification_questions
    assert mock_postgres_store[initial_state.session_id] is not None

    resumed_state = SessionState(
        session_id="session-hitl-001",
        mode=SessionMode.OPTIMIZER,
        status=SessionStatus.PLANNING,
        budget_spent_usd=0.0,
        max_budget_usd=1.25,
        steps_taken=0,
        max_steps=15,
        messages=[
            Message(role="user", content="Too short"),
            Message(role="user", content="Please help me design a practical route planning workflow for our delivery team."),
        ],
        clarification_responses={"How many drivers": "12"},
        playback_confirmed=True,
        process_components=ProcessComponents(
            trigger="New order arrives",
            actor="Dispatcher",
            activity="Assign routes",
            system="Spreadsheets",
            friction="Manual address lookups"
        ),
    )

    with patch("app.core.orchestrator.HAS_ANTHROPIC", False):
        completed_state = await orchestrator.run_pipeline(resumed_state)

    assert completed_state.status == SessionStatus.COMPLETED
    assert any("Too short" in msg.content for msg in completed_state.messages)
    assert completed_state.clarification_responses["How many drivers"] == "12"


# 2. Budget Cap Enforcement & BYOK Bypass

@pytest.mark.asyncio
async def test_redis_budget_increment_is_atomic_under_concurrent_requests(mock_redis_client: MockRedis) -> None:
    """Simulates concurrent budget updates on the same Redis daily spend key."""
    tasks = [
        redis_client.increment_global_spend(1.00),
        redis_client.increment_global_spend(2.50),
        redis_client.increment_global_spend(0.75),
    ]

    results = await asyncio.gather(*tasks)
    assert results == [1.0, 3.5, 4.25]

    current_date_key = redis_client._get_current_date_key()
    daily_key = f"buildsense:global_spend:{current_date_key}"
    assert float(mock_redis_client.data[daily_key]) == pytest.approx(4.25)


@pytest.mark.asyncio
async def test_byok_bypasses_global_budget_increment_logic() -> None:
    """A valid BYOK key should prevent any internal global spend increments."""
    orchestrator = Orchestrator()
    state = SessionState(
        session_id="session-byok-001",
        mode=SessionMode.OPTIMIZER,
        status=SessionStatus.EXECUTING,
        budget_spent_usd=0.0,
        max_budget_usd=1.25,
        steps_taken=0,
        max_steps=15,
        messages=[Message(role="user", content="Continue with the next task.")],
        dag_plan=[{"task_id": "1", "task": "deconstruct_workflows", "persona": "Process Analyst Persona", "done": False}],
    )

    with patch.object(orchestrator.cache, "increment_global_spend", AsyncMock(return_value=0.0)) as increment_spend:
        with patch("app.core.orchestrator.HAS_ANTHROPIC", False):
            orchestrator.user_key = "sk-test-byok"
            await orchestrator._execute_task_loop(state, user_key="sk-test-byok")

    increment_spend.assert_not_awaited()
    assert state.status != SessionStatus.FAILED


# 3. Tool Failure & Fallback

@pytest.mark.asyncio
@pytest.mark.parametrize(
    "side_effect",
    [
        RuntimeError("500 Internal Server Error"),
        TimeoutError("Request timed out after 30 seconds"),
        RuntimeError("429 Too Many Requests")
    ]
)
async def test_synthesize_report_fails_visibly_on_external_llm_failure(side_effect: Exception) -> None:
    """External LLM synthesis failures must not produce healthy-looking fallback reports."""
    orchestrator = Orchestrator()
    state = {
        "session_id": "session-fallback-001",
        "mode": SessionMode.OPTIMIZER,
        "status": SessionStatus.SYNTHESIZING,
        "budget_spent_usd": 0.0,
        "max_budget_usd": 1.25,
        "steps_taken": 3,
        "max_steps": 15,
        "messages": [Message(role="assistant", content="Analysis complete")],
        "metadata": {},
        "clarification_questions": [],
        "clarification_responses": {},
        "dag_plan": [],
        "company_name": "Mock Logistics",
        "company_industry": "LOGISTICS",
        "company_core_tools": "Excel",
        "process_components": {},
        "user_constraints": [],
        "lang": "en",
        "playback_confirmed": True,
        "clarification_turns": 0,
    }

    with patch("app.core.orchestrator.AsyncAnthropic", create=True) as mock_anthropic, \
         patch("app.core.orchestrator.HAS_ANTHROPIC", True), \
         patch("app.core.orchestrator.postgres_client.save_graph", AsyncMock()):
        client_mock = MagicMock()
        client_mock.messages.create = AsyncMock(side_effect=side_effect)
        mock_anthropic.return_value = client_mock

        updates = await orchestrator._node_synthesize_report(state)

    assert updates["status"] == SessionStatus.FAILED
    assert updates["failure"]["category"] == "provider_call_failed"
    assert updates["failure"]["severity"] == FailureSeverity.INTEGRITY_CRITICAL
    assert "quick_insights" not in updates["metadata"]
    assert updates["metadata"]["failure_reason"] == "AI provider call failed before BuildSense could safely continue."


# 4. Auth Fallback & Global Rate Limiting

@pytest.mark.asyncio
async def test_orchestrate_endpoint_bypasses_global_spend_with_byok_header(authenticated_user: AuthenticatedUser) -> None:
    """Requests containing a valid BYOK header skip the global spend budget middleware."""
    app.dependency_overrides[get_current_user] = lambda: authenticated_user

    with patch("app.main.redis_client.has_exceeded_daily_spend_limit", AsyncMock(return_value=True)) as mock_has_exceeded, \
         patch("app.core.orchestrator.orchestrator.run_pipeline", AsyncMock(return_value=SessionState(
             session_id="session-byok-api-001",
             mode=SessionMode.OPTIMIZER,
             status=SessionStatus.ROUTING,
             budget_spent_usd=0.0,
             max_budget_usd=1.25,
             steps_taken=0,
             max_steps=15,
             messages=[]
         ))), \
         patch("app.main.postgres_client.create_user_if_not_exists", AsyncMock()), \
         patch("app.main.postgres_client.create_project", AsyncMock(return_value="project-byok-001")), \
         patch("app.main.postgres_client.get_user_companies", AsyncMock(return_value=[])), \
         patch("app.main.postgres_client.get_project", AsyncMock(return_value={
             "id": "project-byok-001",
             "user_id": authenticated_user.id,
             "mode": "OPTIMIZER",
             "motivation": "EFFICIENCY",
             "user_persona": "SMB Operator"
         })), \
         patch("app.main.postgres_client.get_session_state", AsyncMock(return_value=None)), \
         patch("app.main.postgres_client.save_session_state", AsyncMock()), \
         patch("app.main.postgres_client.save_chat_messages", AsyncMock()):
        response = client.post(
            "/api/v1/orchestrate",
            headers={"x-user-anthropic-key": "sk-test-key"},
            json={"prompt": "Test bypass budget"}
        )

    assert response.status_code == 200
    assert mock_has_exceeded.await_count == 0
    assert response.json()["session_id"] == "session-byok-api-001"


def test_orchestrate_rate_limiting_rejects_after_threshold(authenticated_user: AuthenticatedUser) -> None:
    """Validates the FastAPI IP rate limiter returns HTTP 429 once the daily threshold is exceeded."""
    app.dependency_overrides[get_current_user] = lambda: authenticated_user

    with patch("app.main.redis_client.has_exceeded_daily_spend_limit", AsyncMock(return_value=False)), \
         patch("app.core.orchestrator.orchestrator.run_pipeline", AsyncMock(return_value=SessionState(
             session_id="session-rate-limit-001",
             mode=SessionMode.OPTIMIZER,
             status=SessionStatus.ROUTING,
             budget_spent_usd=0.0,
             max_budget_usd=1.25,
             steps_taken=0,
             max_steps=15,
             messages=[]
         ))), \
         patch("app.main.postgres_client.create_user_if_not_exists", AsyncMock()), \
         patch("app.main.postgres_client.create_project", AsyncMock(return_value="project-rate-001")), \
         patch("app.main.postgres_client.get_user_companies", AsyncMock(return_value=[])), \
         patch("app.main.postgres_client.get_project", AsyncMock(return_value={
             "id": "project-rate-001",
             "user_id": authenticated_user.id,
             "mode": "OPTIMIZER",
             "motivation": "EFFICIENCY",
             "user_persona": "SMB Operator"
         })), \
         patch("app.main.postgres_client.get_session_state", AsyncMock(return_value=None)), \
         patch("app.main.postgres_client.save_session_state", AsyncMock()), \
         patch("app.main.postgres_client.save_chat_messages", AsyncMock()):
        final_response = None
        for _ in range(6):
            response = client.post(
                "/api/v1/orchestrate",
                headers={"X-Forwarded-For": "198.51.100.42"},
                json={"prompt": "Rate limit test"}
            )
            if response.status_code == 429:
                final_response = response
                break
            assert response.status_code == 200

    assert final_response is not None
    assert final_response.status_code == 429


# 5. Untrusted Output Wrapping & Context Pruning

def test_untrusted_output_wrapping_and_pruning_truncates_oversized_payload() -> None:
    """
    Ensures tool outputs are wrapped as untrusted XML, that moderate-sized
    real tool output survives context pruning unmodified (so the model can
    ground synthesis citations in it), and that only a genuinely oversized
    payload gets bounded. See BUG-030 / BUG-033 / audit cycle 2: the prior
    ~20-char stub discarded real tool output regardless of size.
    """
    orchestrator = Orchestrator()
    raw_payload = "<broken><xml>" + "A" * 200 + "</xml>" + "</broken>"

    wrapped = orchestrator._wrap_untrusted_output(raw_payload, source="external_tool")
    assert wrapped.startswith('<untrusted_tool_output source="external_tool">')
    assert wrapped.endswith("</untrusted_tool_output>")
    assert raw_payload in wrapped

    # A moderate-sized payload (well under the preservation cap) must survive
    # pruning unmodified.
    pruned = orchestrator._prune_context(wrapped)
    assert pruned == wrapped

    # A genuinely oversized payload must still be bounded.
    oversized_raw_payload = "<broken><xml>" + "A" * 10000 + "</xml>" + "</broken>"
    oversized_wrapped = orchestrator._wrap_untrusted_output(oversized_raw_payload, source="external_tool")
    pruned_oversized = orchestrator._prune_context(oversized_wrapped)
    assert pruned_oversized.startswith("Summary:")
    assert len(pruned_oversized) < len(oversized_wrapped)
