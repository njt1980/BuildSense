"""Deterministic evals for analyst-like multi-turn intake behavior.

These tests guard the product contract that BuildSense should behave like a
careful business analyst: gather the minimum required facts, ask one natural
question at a time, and avoid recommendations until the intake is confirmed.
"""

from typing import Iterable
from unittest.mock import AsyncMock, patch

import pytest

from app.core.orchestrator import Orchestrator
from app.models.state import Message, ProcessComponents, SessionMode, SessionState, SessionStatus


FORBIDDEN_PREMATURE_SOLUTION_TERMS = [
    "recommendation",
    "automate",
    "zapier",
    "gen ai",
    "roi",
    "deploy",
]

FORBIDDEN_MACHINE_LABELS = [
    "Trigger:",
    "Actor:",
    "Activity:",
    "System:",
    "Friction:",
]


def assert_no_terms(text: str, terms: Iterable[str]) -> None:
    """Assert that none of the provided terms appear in text."""
    lower_text = text.lower()
    for term in terms:
        assert term.lower() not in lower_text


async def run_offline_pipeline(state: SessionState) -> SessionState:
    """Run the orchestrator with LLM calls disabled and persistence mocked."""
    with patch("app.core.orchestrator.HAS_ANTHROPIC", False), \
         patch("app.core.orchestrator.Orchestrator._node_sanitize_input", AsyncMock(return_value={})), \
         patch("app.core.orchestrator.Orchestrator._save_intermediate_state", AsyncMock()):
        return await Orchestrator().run_pipeline(state)


@pytest.mark.asyncio
async def test_physical_business_missing_location_pauses_before_solution() -> None:
    """Physical businesses must supply location before analysis starts."""
    state = SessionState(
        session_id="analyst-eval-pet-shop-location-missing",
        mode=SessionMode.OPTIMIZER,
        status=SessionStatus.ROUTING,
        max_budget_usd=1.25,
        max_steps=15,
        messages=[Message(role="user", content="We run a small pet shop and take orders via WhatsApp.")],
        company_core_tools="WhatsApp",
        process_components=ProcessComponents(),
    )

    output = await run_offline_pipeline(state)
    assistant_text = output.messages[-1].content

    assert output.status == SessionStatus.AWAITING_CLARIFICATION
    assert output.metadata["architect_plan"]["requires_location"] is True
    assert output.process_components.location is None
    assert "Where is your business based" in assistant_text
    assert_no_terms(assistant_text, FORBIDDEN_MACHINE_LABELS)
    assert_no_terms(assistant_text, FORBIDDEN_PREMATURE_SOLUTION_TERMS)


@pytest.mark.asyncio
async def test_physical_business_with_location_gets_human_confirmation_not_solution() -> None:
    """Complete intake should ask for confirmation, not immediately synthesize."""
    state = SessionState(
        session_id="analyst-eval-pet-shop-location-present",
        mode=SessionMode.OPTIMIZER,
        status=SessionStatus.ROUTING,
        max_budget_usd=1.25,
        max_steps=15,
        messages=[
            Message(
                role="user",
                content="We run a small pet shop based in Koramangala and take orders via WhatsApp.",
            )
        ],
        company_core_tools="WhatsApp",
        process_components=ProcessComponents(),
    )

    with patch("app.core.orchestrator.HAS_ANTHROPIC", False), \
         patch("app.core.orchestrator.Orchestrator._node_sanitize_input", AsyncMock(return_value={})), \
         patch("app.core.orchestrator.Orchestrator._save_intermediate_state", AsyncMock()), \
         patch("app.core.orchestrator.Orchestrator._execute_mock_simulation_loop", AsyncMock()) as execute_loop:
        output = await Orchestrator().run_pipeline(state)

    assistant_text = output.messages[-1].content
    assert output.status == SessionStatus.AWAITING_CLARIFICATION
    assert output.process_components.location == "Koramangala"
    assert "If that sounds right" in assistant_text
    assert execute_loop.await_count == 0
    assert_no_terms(assistant_text, FORBIDDEN_MACHINE_LABELS)


@pytest.mark.asyncio
async def test_ambiguous_office_approval_asks_for_process_context() -> None:
    """Vague pain statements should lead to a clarifying question, not a solution."""
    state = SessionState(
        session_id="analyst-eval-ambiguous-approval",
        mode=SessionMode.OPTIMIZER,
        status=SessionStatus.ROUTING,
        max_budget_usd=1.25,
        max_steps=15,
        messages=[
            Message(
                role="user",
                content="Approvals get stuck in the office for days and customers get upset.",
            )
        ],
        process_components=ProcessComponents(),
    )

    output = await run_offline_pipeline(state)
    assistant_text = output.messages[-1].content

    assert output.status == SessionStatus.AWAITING_CLARIFICATION
    assert output.playback_confirmed is False
    assert output.process_components.system is None
    assert "What usually starts this work" in assistant_text
    assert_no_terms(assistant_text, FORBIDDEN_MACHINE_LABELS)
    assert_no_terms(assistant_text, FORBIDDEN_PREMATURE_SOLUTION_TERMS)


@pytest.mark.asyncio
async def test_online_business_does_not_require_location() -> None:
    """Purely online workflows should not be forced through a location question."""
    state = SessionState(
        session_id="analyst-eval-online-no-location",
        mode=SessionMode.OPTIMIZER,
        status=SessionStatus.ROUTING,
        max_budget_usd=1.25,
        max_steps=15,
        messages=[
            Message(
                role="user",
                content="We run an online newsletter and manually copy Stripe payments into Google Sheets.",
            )
        ],
        company_core_tools="Stripe, Google Sheets",
        process_components=ProcessComponents(),
    )

    output = await run_offline_pipeline(state)
    architect_plan = output.metadata["architect_plan"]

    assert architect_plan["requires_location"] is False
    assert "location" not in architect_plan["required_components"]
    assert output.process_components.location is None


@pytest.mark.asyncio
async def test_confirmed_intake_is_required_before_execution() -> None:
    """Only a user confirmation should move a complete intake into execution."""
    async def complete_execution_loop(state_dict: dict) -> None:
        """Mark the execution DAG complete so this eval can observe routing."""
        state_dict["dag_plan"] = [
            {"task_id": "1", "task": "deconstruct_workflows", "persona": "Process Analyst Persona", "done": True},
            {"task_id": "2", "task": "design_automations", "persona": "Automation Architect Persona", "done": True},
        ]
        state_dict["status"] = SessionStatus.EXECUTING
        state_dict["steps_taken"] = int(state_dict.get("steps_taken", 0)) + 1

    components = ProcessComponents(
        trigger="Customer order received on WhatsApp",
        actor="Shop staff",
        activity="Review and fulfill customer orders",
        system="WhatsApp and notebook",
        friction=None,
        location="Koramangala",
    )
    state = SessionState(
        session_id="analyst-eval-confirmation-required",
        mode=SessionMode.OPTIMIZER,
        status=SessionStatus.ROUTING,
        max_budget_usd=1.25,
        max_steps=15,
        messages=[Message(role="user", content="Yes, that is correct.")],
        process_components=components,
        playback_confirmed=False,
        metadata={
            "architect_plan": {
                "business_vertical": "GENERIC",
                "requires_location": True,
                "required_components": ["trigger", "actor", "activity", "system", "location"],
            }
        },
    )

    with patch("app.core.orchestrator.HAS_ANTHROPIC", False), \
         patch("app.core.orchestrator.Orchestrator._node_sanitize_input", AsyncMock(return_value={})), \
         patch("app.core.orchestrator.Orchestrator._save_intermediate_state", AsyncMock()), \
         patch("app.core.orchestrator.Orchestrator._execute_mock_simulation_loop", AsyncMock(side_effect=complete_execution_loop)) as execute_loop:
        output = await Orchestrator().run_pipeline(state)

    assert output.playback_confirmed is True
    assert execute_loop.await_count >= 1
