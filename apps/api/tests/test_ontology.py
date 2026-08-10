"""Unit and integration tests verifying dynamic ontology routing and evidence tracking.

Tests check keyword classifiers, ladder extractors, and LangGraph integration.
"""

import pytest
from unittest.mock import AsyncMock, patch
from app.models.state import SessionState, SessionMode, SessionStatus, Message
from app.core.orchestrator import (
    Orchestrator,
    classify_vertical,
    extract_evidence_ledger_from_messages
)


def test_classify_vertical_keywords() -> None:
    """
    Verifies that business descriptions are classified into correct industry verticals.
    """
    assert classify_vertical("We manage a fleet of container trucks and delivery routes") == "LOGISTICS"
    assert classify_vertical("A batch packaging factory line with assembly machinery") == "MANUFACTURING"
    assert classify_vertical("A wholesale clothing distributor and suppliers POs") == "WHOLESALE"
    assert classify_vertical("A generic software consulting agency") == "GENERIC"


def test_evidence_ladder_extraction() -> None:
    """
    Verifies that conversation claims are graded accurately on the Evidence Ladder.
    """
    messages = [
        Message(role="user", content="My staff stated that route planning takes 4 hours daily."),
        Message(role="user", content="The warehouse database export shows average utilization of 65%."),
        Message(role="user", content="We estimate that 5% of products are damaged during transport.")
    ]
    
    ledger = extract_evidence_ledger_from_messages(messages)
    
    assert len(ledger) == 3
    
    # Assert Level 2: Employee Stated
    employee_claim = next(c for c in ledger if c["ladder_level"] == "Employee Stated")
    assert "4 hours" in employee_claim["claim"]
    assert "Staff" in employee_claim["source"]
    
    # Assert Level 3: System Export
    system_claim = next(c for c in ledger if c["ladder_level"] == "System Export")
    assert "65%" in system_claim["claim"]
    assert "Database" in system_claim["source"]
    
    # Assert Level 1: Owner Estimate
    owner_claim = next(c for c in ledger if c["ladder_level"] == "Owner Estimate")
    assert "5%" in owner_claim["claim"]
    assert "Owner" in owner_claim["source"]


@pytest.mark.asyncio
async def test_orchestrator_ontology_discovery_injection() -> None:
    """
    Verifies that vertical ontology routing injects industry-specific questions
    when a newly created project prompt is incomplete.
    """
    orchestrator = Orchestrator()
    state = SessionState(
        session_id="test-ontology-session-123",
        mode=SessionMode.OPTIMIZER,
        status=SessionStatus.ROUTING,
        max_budget_usd=0.20,
        max_steps=5,
        messages=[Message(role="user", content="truck dispatch")]
    )

    with patch.object(orchestrator.db, "save_session_state", AsyncMock()):
        updated_state = await orchestrator.run_pipeline(state)
        
        # Verify vertical was classified as LOGISTICS
        assert updated_state.business_vertical == "LOGISTICS"
        
        # Verify logistics discovery questions were injected into the awaiting loop
        assert updated_state.status == SessionStatus.AWAITING_CLARIFICATION
        assert any("WMS" in q or "transportation" in q for q in updated_state.clarification_questions)
