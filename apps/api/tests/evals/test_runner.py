"""E2E evaluation test runner for BuildSense orchestrator pipeline.

Runs scenarios, asserts state machine transitions/mutations, and invokes LLM judge
to grade output quality.
"""

import os
import json
import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from app.models.state import SessionState, SessionMode, SessionStatus, Message, ProcessComponents
from app.core.orchestrator import Orchestrator
from tests.evals.eval_dataset import GOLDEN_SCENARIOS, Turn
from tests.evals.judge import invoke_llm_judge

class MockResponse:
    """Mock structure mimicking Anthropic API client message response."""
    def __init__(self, text, input_tokens=100, output_tokens=50, stop_reason="end_turn"):
        class ContentBlock:
            def __init__(self, text_val):
                self.text = text_val
                self.type = "text"
        self.content = [ContentBlock(text)]
        class Usage:
            def __init__(self, in_tok, out_tok):
                self.input_tokens = in_tok
                self.output_tokens = out_tok
                self.cache_read_input_tokens = 0
                self.cache_creation_input_tokens = 0
        self.usage = Usage(input_tokens, output_tokens)
        self.stop_reason = stop_reason


def make_mock_anthropic(scenario_turn: Turn):
    """
    Creates a mock Anthropic client with a messages.create method that returns
    the matched pre-recorded mock response for each node.
    """
    async def mock_messages_create(*args, **kwargs):
        system_prompt = kwargs.get("system", "")
        
        user_prompt = ""
        messages = kwargs.get("messages", [])
        if messages:
            user_prompt = messages[-1].get("content", "")

        node_name = None
        # Classify the node based on system or user prompt contents
        if "sanitization" in system_prompt or "sanitization" in user_prompt or "INVALID" in system_prompt or "INVALID" in user_prompt:
            node_name = "sanitize_input"
        elif "completeness classifier" in system_prompt or "completeness classifier" in user_prompt:
            node_name = "route_intent"
        elif "intake confirmation classifier" in system_prompt or "intake confirmation classifier" in user_prompt:
            node_name = "confirm_gate"
        elif "process mapping assistant" in system_prompt or "process mapping assistant" in user_prompt:
            node_name = "extractor"
        elif "plain-spoken operational consultant" in system_prompt or "plain-spoken operational consultant" in user_prompt:
            node_name = "question_generator"
        elif "report writer" in system_prompt or "report writer" in user_prompt:
            node_name = "synthesize_report"

        # Search for corresponding mock response
        if node_name:
            for resp in scenario_turn.get("mock_llm_responses", []):
                if resp["node"] == node_name:
                    return MockResponse(resp["response_content"])

        # Default fallback
        return MockResponse("{}")

    mock_client = MagicMock()
    mock_client.messages.create = AsyncMock(side_effect=mock_messages_create)
    return mock_client


@pytest.mark.asyncio
@pytest.mark.parametrize("scenario", GOLDEN_SCENARIOS, ids=lambda s: s["name"])
async def test_orchestrator_scenario(scenario, mock_postgres_and_redis) -> None:
    """
    E2E scenario test executing turns and validating routing, state accumulation,
    and semantic quality.
    """
    orchestrator = Orchestrator()
    company_context = scenario.get("company_context", {})
    company_name = company_context.get("name")
    company_industry = company_context.get("industry")
    company_core_tools = company_context.get("core_tools")

    if company_context:
        mock_postgres_and_redis["get_company"].side_effect = None
        mock_postgres_and_redis["get_company"].return_value = {
            "id": "mock-company-id",
            "name": company_name,
            "industry_vertical": company_industry,
            "industry": company_industry,
            "core_tools": company_core_tools,
        }
    
    # Initialize session state
    state = SessionState(
        session_id=f"e2e-session-{scenario['name'].replace(' ', '-')}",
        mode=SessionMode(scenario["mode"]),
        status=SessionStatus.ROUTING,
        max_budget_usd=1.25,
        max_steps=15,
        messages=[],
        clarification_turns=scenario.get("initial_turns_count", 0),
        process_components=ProcessComponents(),
        company_name=company_name,
        company_industry=company_industry,
        company_core_tools=company_core_tools,
        user_constraints=scenario.get("user_constraints") or [],
        metadata={
            "motivation": scenario["motivation"],
            "backstory": scenario.get("backstory", ""),
        },
    )

    # Variables to collect outputs for semantic grading
    playback_summary = ""
    synthesized_report = ""

    # Execute each turn in the scenario
    for turn in scenario["turns"]:
        # Mock Anthropic client for this specific turn
        mock_client = make_mock_anthropic(turn)
        
        # Append user input
        state.messages.append(Message(role="user", content=turn["user_input"]))
        
        # Override clarification turns if specified
        if turn.get("clarification_turns") is not None:
            state.clarification_turns = turn["clarification_turns"]
        
        with patch("app.core.orchestrator.AsyncAnthropic", return_value=mock_client, create=True), \
             patch("app.core.orchestrator.HAS_ANTHROPIC", True):
            
            # Execute pipeline
            state = await orchestrator.run_pipeline(state, user_key="eval-key")
            
        # Assertions: state status
        assert state.status.value == turn["expected_status"], (
            f"Scenario '{scenario['name']}' status mismatch. Expected {turn['expected_status']}, got {state.status.value}"
        )
        
        # Assertions: process components accumulation
        expected_comps = turn["expected_components"]
        for k, v in expected_comps.items():
            actual_val = getattr(state.process_components, k)
            assert actual_val == v, (
                f"Scenario '{scenario['name']}' component '{k}' mismatch. Expected '{v}', got '{actual_val}'"
            )

        # Check messages for playback summary to save for the judge
        for msg in reversed(state.messages):
            if "Here is a summary of what I understand" in msg.content or "🚚" in msg.content:
                playback_summary = msg.content
                break

    # If the scenario finishes the full synthesis workflow, grade the output using the judge
    if scenario["expect_synthesis"]:
        synthesized_report = (
            f"### Current Manual Process (As-Is)\n"
            f"{state.metadata.get('as_is_workflow', '')}\n\n"
            f"### Friction Analysis\n"
            f"{state.metadata.get('friction_analysis', '')}\n\n"
            f"### Technology Neutral Recommendations\n"
            f"{state.metadata.get('technology_neutral_recommendations', '')}\n\n"
            f"### ROI Economics\n"
            f"{state.metadata.get('roi_economics', '')}"
        )
        for expected_text in scenario.get("expected_report_contains", []):
            assert expected_text.lower() in synthesized_report.lower(), (
                f"Scenario '{scenario['name']}' report missing expected text: {expected_text}"
            )
        
        constraints_str = ", ".join(scenario["user_constraints"]) if scenario["user_constraints"] else "None"
        
        # Call the LLM judge (Claude 3.5 Haiku)
        grades = await invoke_llm_judge(
            playback_summary=playback_summary,
            synthesized_report=synthesized_report,
            user_constraints=constraints_str
        )
        
        from app.core.config import settings
        api_key = settings.anthropic_api_key or os.environ.get("ANTHROPIC_API_KEY")
        if api_key:
            # Assert semantic criteria are scored >= 0.90 (passing threshold)
            assert grades["zero_jargon_score"] >= 0.90, (
                f"Zero Jargon compliance failed with score {grades['zero_jargon_score']}. Justification: {grades['justification']}"
            )
            assert grades["hierarchy_integrity_score"] >= 0.90, (
                f"Hierarchy integrity compliance failed with score {grades['hierarchy_integrity_score']}. Justification: {grades['justification']}"
            )
            assert grades["consultant_intake_score"] >= 0.90, (
                f"Consultant intake behavior failed with score {grades['consultant_intake_score']}. Justification: {grades['justification']}"
            )
        else:
            # When API key is absent, verify mocked fallback scores are returned
            assert grades["zero_jargon_score"] == 1.0
            assert grades["hierarchy_integrity_score"] == 1.0
            assert grades["consultant_intake_score"] == 1.0


@pytest.mark.asyncio
async def test_llm_judge_rubrics() -> None:
    """
    Validates that the LLM judge evaluates positive and negative cases correctly.
    """
    # Only test if API key is present
    from app.core.config import settings
    api_key = settings.anthropic_api_key or os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        pytest.skip("Skipping judge rubrics check: ANTHROPIC_API_KEY is not defined.")

    # 1. Compliant Case: Zero technical jargon without explanation, proper hierarchy, consultant intake behavior
    good_playback = (
        "That helps. So the busy moment starts when high-volume customer emails arrive. "
        "Who on your team handles the first pass at those emails?"
    )
    good_synthesis = (
        "### Current Manual Process (As-Is)\n"
        "Dispatcher reads incoming order emails in Outlook and copy-pastes details to scheduling tools.\n\n"
        "### Friction Analysis\n"
        "Manual entry takes 15 minutes per order, leading to delayed bookings during peak hours.\n\n"
        "### Technology Neutral Recommendations\n"
        "We evaluate options in order of complexity:\n"
        "- Tier 1: Process/Policy Change: Have clients submit orders using standardized Excel sheets to reduce typos.\n"
        "- Tier 2: SaaS (Software as a Service: rental software, like paying a monthly fee to stream movies on Netflix instead of buying individual DVDs) / Deterministic Automation: Connect Outlook to routing tools via Zapier to fetch data automatically.\n"
        "- Tier 3: Gen AI / Agentic Workflows: A Gen AI solution is NOT recommended here, as processing is structured and a simple deterministic webhook connector solves the problem.\n\n"
        "### ROI Economics\n"
        "Implementation cost is low. Expect a ROI (Return on Investment: net benefit relative to cost) of 300%."
    )

    good_grades = await invoke_llm_judge(good_playback, good_synthesis, "Low Budget")
    if "fallback" in good_grades.get("justification", "").lower() or "mocked" in good_grades.get("justification", "").lower():
        pytest.skip("Skipping judge rubric assertions: API call returned fallback values.")
        
    assert good_grades["zero_jargon_score"] >= 0.90
    assert good_grades["hierarchy_integrity_score"] >= 0.90
    assert good_grades["consultant_intake_score"] >= 0.90

    # 2. Non-Compliant Case: Unexplained jargon (CAC, LTV), violates hierarchy by immediately building Gen AI, robotic multi-slot intake
    bad_playback = (
        "Trigger: customer email\n"
        "Actor: dispatcher\n"
        "System: Excel\n"
        "Friction: slow copy-pasting\n"
        "Who does this, what system do they use, and what is the bottleneck?"
    )
    bad_synthesis = (
        "### Current Manual Process (As-Is)\n"
        "Manual order copy pasting.\n\n"
        "### Friction Analysis\n"
        "Slow entry.\n\n"
        "### Technology Neutral Recommendations\n"
        "You must immediately deploy a Custom Multi-Agent LLM Orchestration Platform (Tier 3) with vector embeddings "
        "and auto-updating nodes. We skip standard API integrations or simple policy shifts.\n\n"
        "### ROI Economics\n"
        "Will improve LTV and CAC significantly."
    )

    bad_grades = await invoke_llm_judge(bad_playback, bad_synthesis, "Low Budget")
    assert bad_grades["zero_jargon_score"] < 0.90 or bad_grades["hierarchy_integrity_score"] < 0.90 or bad_grades["consultant_intake_score"] < 0.90
