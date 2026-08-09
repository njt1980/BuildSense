"""Unit tests for the BuildSense Orchestrator engine.

Tests verify state machine transitions, context pruning, cost controls,
untrusted output XML containment, and HITL check boundaries.
"""

from unittest.mock import AsyncMock, patch
import pytest
from app.models.state import SessionState, SessionMode, SessionStatus, Message
from app.core.orchestrator import Orchestrator


@pytest.mark.asyncio
async def test_orchestrator_incomplete_input_routing() -> None:
    """
    Checks that short inputs trigger HITL clarification and pause status.

    Arguments:
        None

    Returns:
        None
    """
    orchestrator = Orchestrator()
    state = SessionState(
        session_id="test-session-123",
        mode=SessionMode.SUGGESTER,
        status=SessionStatus.ROUTING,
        max_budget_usd=0.15,
        max_steps=6,
        messages=[Message(role="user", content="too short")]
    )

    with patch.object(orchestrator.db, "save_session_state", AsyncMock()) as mock_save:
        updated_state = await orchestrator.run_pipeline(state)
        
        assert updated_state.status == SessionStatus.AWAITING_CLARIFICATION
        assert len(updated_state.clarification_questions) == 2
        mock_save.assert_called_once()


@pytest.mark.asyncio
async def test_orchestrator_complete_pipeline_run() -> None:
    """
    Checks that valid inputs transition successfully to COMPLETED status.

    Arguments:
        None

    Returns:
        None
    """
    orchestrator = Orchestrator()
    state = SessionState(
        session_id="test-session-456",
        mode=SessionMode.SUGGESTER,
        status=SessionStatus.ROUTING,
        max_budget_usd=0.15,
        max_steps=6,
        messages=[Message(role="user", content="Here is a very long descriptive product idea prompt containing more than fifteen characters.")]
    )

    with patch.object(orchestrator.db, "save_session_state", AsyncMock()) as mock_save_db, \
         patch.object(orchestrator.cache, "increment_global_spend", AsyncMock(return_value=0.025)):
        
        updated_state = await orchestrator.run_pipeline(state)
        
        assert updated_state.status == SessionStatus.COMPLETED
        assert updated_state.steps_taken == 1
        assert updated_state.budget_spent_usd == 0.025
        assert "quick_insights" in updated_state.metadata
        assert "deep_dive" in updated_state.metadata
        assert mock_save_db.call_count >= 2


def test_orchestrator_xml_untrusted_containment() -> None:
    """
    Checks that external search results are wrapped in untrusted output XML tags.

    Arguments:
        None

    Returns:
        None
    """
    orchestrator = Orchestrator()
    raw_response = "Unstructured competitor data content"
    wrapped = orchestrator._wrap_untrusted_output(raw_response, source="test_source")
    
    assert wrapped.startswith('<untrusted_tool_output source="test_source">')
    assert wrapped.endswith('</untrusted_tool_output>')
    assert raw_response in wrapped


def test_orchestrator_context_pruning_hook() -> None:
    """
    Checks that heavy payloads are summarized by the context pruning hook.

    Arguments:
        None

    Returns:
        None
    """
    orchestrator = Orchestrator()
    raw_payload = "<untrusted_tool_output source='search'>Long raw html output</untrusted_tool_output>"
    pruned = orchestrator._prune_context(raw_payload)
    
    assert "Summary:" in pruned
    assert len(pruned) < len(raw_payload)


@pytest.mark.asyncio
async def test_orchestrator_budget_exhaustion_limits() -> None:
    """
    Checks that exceeding session budget caps halts execution and transitions status to FAILED.

    Arguments:
        None

    Returns:
        None
    """
    orchestrator = Orchestrator()
    state = SessionState(
        session_id="test-session-789",
        mode=SessionMode.SUGGESTER,
        status=SessionStatus.EXECUTING,
        max_budget_usd=0.01,  # Set very small budget limit
        max_steps=6,
        messages=[Message(role="user", content="Prompt content detail text.")],
        dag_plan=[{"task_id": "1", "task": "run_test", "persona": "Test Persona", "done": False}]
    )

    with patch.object(orchestrator.db, "save_session_state", AsyncMock()), \
         patch.object(orchestrator.cache, "increment_global_spend", AsyncMock(return_value=0.025)):
        
        await orchestrator._execute_task_loop(state)
        
        assert state.status == SessionStatus.FAILED
        assert "failure_reason" in state.metadata
        assert "budget cap exceeded" in state.metadata["failure_reason"]
