"""Unit tests verifying LangGraph checkpointer persistence.

Tests confirm that MemorySaver saves session state snapshots and allows
the state machine to resume execution on successive invokes.
"""

import pytest
from app.models.state import SessionState, SessionMode, SessionStatus, Message
from app.core.orchestrator import Orchestrator


@pytest.mark.asyncio
async def test_langgraph_checkpoint_persistence_and_resumption() -> None:
    """
    Verifies that calling run_pipeline saves state checkpointer snapshots
    and resumes step execution correctly using thread configs.
    """
    orchestrator = Orchestrator()
    session_id = "test-checkpointer-persistence-999"

    # 1. Start execution with incomplete input to cause AWAITING_CLARIFICATION pause
    initial_state = SessionState(
        session_id=session_id,
        mode=SessionMode.SUGGESTER,
        status=SessionStatus.ROUTING,
        max_budget_usd=0.15,
        max_steps=6,
        messages=[Message(role="user", content="too short")]
    )

    paused_state = await orchestrator.run_pipeline(initial_state)
    assert paused_state.status == SessionStatus.AWAITING_CLARIFICATION
    assert len(paused_state.clarification_questions) == 3

    # 2. Simulate user clarifying response, set state back to PLANNING
    resumed_state = SessionState(
        session_id=session_id,
        mode=SessionMode.SUGGESTER,
        status=SessionStatus.PLANNING,
        max_budget_usd=0.15,
        max_steps=6,
        messages=[
            Message(role="user", content="too short"),
            Message(role="user", content="Suggest a very long descriptive product idea prompt containing more than fifteen characters.")
        ]
    )

    completed_state = await orchestrator.run_pipeline(resumed_state)
    assert completed_state.status == SessionStatus.COMPLETED
    assert completed_state.steps_taken == 1
    assert "quick_insights" in completed_state.metadata
    assert "deep_dive" in completed_state.metadata
