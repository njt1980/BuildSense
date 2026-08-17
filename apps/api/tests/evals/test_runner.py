"""E2E evaluation test runner for BuildSense orchestrator pipeline.

Runs scenarios, asserts state machine transitions/mutations, and invokes LLM judge
to grade output quality.
"""

import os
import re
import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from app.models.state import SessionState, SessionMode, SessionStatus, Message, ProcessComponents
from app.core.orchestrator import Orchestrator
from tests.evals.eval_dataset import (
    DEFAULT_FORBIDDEN_ASSISTANT_TERMS,
    GOLDEN_SCENARIOS,
    REQUIRED_ARCHETYPES,
    REQUIRED_SCENARIO_TAGS,
    Turn,
)
from tests.evals.judge import invoke_llm_judge


FAILURE_PREFIXES = {
    "state": "STATE_TRANSITION",
    "components": "COMPONENT_ACCUMULATION",
    "pillar": "PILLAR_METADATA",
    "blind_spot": "BLIND_SPOT_SELECTION",
    "assistant_text": "ASSISTANT_TEXT_POLICY",
    "correction": "CORRECTION_OVERWRITE",
    "synthesis": "SYNTHESIS_SCHEMA",
    "judge": "JUDGE_SCORE",
    "mock": "MOCK_FIXTURE_DRIFT",
}


QUESTION_PATTERN = re.compile(r"[?？؟]")

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


def count_questions(text: str) -> int:
    """Counts visible question marks in assistant-facing text."""
    return len(QUESTION_PATTERN.findall(text))


def latest_assistant_text(state: SessionState) -> str:
    """Returns the latest assistant message content from a session state."""
    for message in reversed(state.messages):
        if message.role == "assistant":
            return message.content
    return ""


def assert_current_approach_metadata(state: SessionState, scenario_name: str) -> None:
    """Asserts that current consultant and iterative-discovery metadata exists."""
    architect_plan = state.metadata.get("architect_plan", {})
    coverage = architect_plan.get("six_pillar_coverage", {})
    blind_spot = architect_plan.get("selected_blind_spot")
    iterative_discovery = state.metadata.get("iterative_discovery", {})
    expected_pillars = {"market", "operations", "financials", "personnel", "technology", "risk"}

    assert expected_pillars.issubset(set(coverage)), (
        f"{FAILURE_PREFIXES['pillar']}: Scenario '{scenario_name}' missing six-pillar coverage. "
        f"Expected at least {sorted(expected_pillars)}, got {sorted(coverage)}."
    )
    assert isinstance(blind_spot, dict), (
        f"{FAILURE_PREFIXES['blind_spot']}: Scenario '{scenario_name}' did not store one selected blind spot."
    )
    assert isinstance(blind_spot.get("pillar"), str) and blind_spot["pillar"], (
        f"{FAILURE_PREFIXES['blind_spot']}: Scenario '{scenario_name}' selected blind spot has no pillar."
    )
    assert isinstance(blind_spot.get("question"), str) and blind_spot["question"], (
        f"{FAILURE_PREFIXES['blind_spot']}: Scenario '{scenario_name}' selected blind spot has no question."
    )
    assert isinstance(iterative_discovery, dict), (
        f"{FAILURE_PREFIXES['state']}: Scenario '{scenario_name}' missing iterative discovery metadata."
    )
    assert iterative_discovery.get("max_turns") == 3, (
        f"{FAILURE_PREFIXES['state']}: Scenario '{scenario_name}' does not enforce MAX_CLARIFICATION_TURNS=3."
    )
    assert isinstance(iterative_discovery.get("e2e_confidence_score"), (int, float)), (
        f"{FAILURE_PREFIXES['state']}: Scenario '{scenario_name}' missing e2e confidence score."
    )


def assert_assistant_text_policy(text: str, scenario_name: str, forbidden_terms) -> None:
    """Asserts assistant-facing text follows the current no-placeholder policy."""
    assert text, f"{FAILURE_PREFIXES['assistant_text']}: Scenario '{scenario_name}' has no assistant text to inspect."
    for term in forbidden_terms:
        assert term not in text, (
            f"{FAILURE_PREFIXES['assistant_text']}: Scenario '{scenario_name}' leaked forbidden term '{term}' "
            f"in assistant text: {text}"
        )


def assert_catalog_contract() -> None:
    """Asserts the fictional-company catalog covers the required archetypes and tags."""
    observed_tags = {
        tag
        for scenario in GOLDEN_SCENARIOS
        for tag in scenario.get("scenario_tags", [])
    }
    observed_archetypes = {
        scenario.get("eval_archetype")
        for scenario in GOLDEN_SCENARIOS
        if scenario.get("eval_archetype")
    }
    assert REQUIRED_SCENARIO_TAGS.issubset(observed_tags), (
        f"{FAILURE_PREFIXES['mock']}: Eval catalog missing required scenario tags: "
        f"{sorted(REQUIRED_SCENARIO_TAGS - observed_tags)}"
    )
    assert REQUIRED_ARCHETYPES.issubset(observed_archetypes), (
        f"{FAILURE_PREFIXES['mock']}: Eval catalog missing required SMB archetypes: "
        f"{sorted(REQUIRED_ARCHETYPES - observed_archetypes)}"
    )
    for scenario in GOLDEN_SCENARIOS:
        assert scenario["mode"] == "OPTIMIZER", (
            f"{FAILURE_PREFIXES['mock']}: Scenario '{scenario['name']}' uses retired mode {scenario['mode']}."
        )


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
        elif (
            "plain-spoken operational consultant" in system_prompt
            or "plain-spoken operational consultant" in user_prompt
            or "next natural question" in system_prompt
            or "next natural question" in user_prompt
            or "Your job is to ask" in system_prompt
            or "Your job is to ask" in user_prompt
        ):
            node_name = "question_generator"
        elif (
            "natural playback summary" in system_prompt
            or "natural playback summary" in user_prompt
            or "current workflow understanding" in system_prompt
            or "current workflow understanding" in user_prompt
            or "confirm or correct" in system_prompt
            or "confirm or correct" in user_prompt
        ):
            node_name = "playback"
        elif "report writer" in system_prompt or "report writer" in user_prompt:
            node_name = "synthesize_report"

        # Search for corresponding mock response
        if node_name:
            for resp in scenario_turn.get("mock_llm_responses", []):
                if resp["node"] == node_name:
                    return MockResponse(resp["response_content"])

        if node_name == "playback":
            return MockResponse("That matches what I have so far. Is that right, or would you correct anything?")
        if node_name == "question_generator":
            return MockResponse("That helps. What usually starts this work?")

        # Default fallback
        return MockResponse("{}")

    mock_client = MagicMock()
    mock_client.messages.create = AsyncMock(side_effect=mock_messages_create)
    return mock_client


@pytest.mark.asyncio
@pytest.mark.parametrize("scenario", GOLDEN_SCENARIOS, ids=lambda s: s["name"])
async def test_orchestrator_scenario(scenario, mock_postgres_and_redis, request) -> None:
    """
    E2E scenario test executing turns and validating routing, state accumulation,
    and semantic quality. Supports both mock simulation and live LLM runs.
    """
    import os
    import time
    
    orchestrator = Orchestrator()
    assert scenario["mode"] == "OPTIMIZER", (
        f"{FAILURE_PREFIXES['mock']}: Scenario '{scenario['name']}' uses retired mode {scenario['mode']}."
    )
    
    is_live = os.environ.get("LIVE_EVALS") == "true"
    live_model = os.environ.get("LIVE_EVALS_MODEL", "claude-haiku-4-5-20251001")
    
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
        clarification_turns=scenario.get("initial_turns_count") or 0,
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

    playback_summary = ""
    synthesized_report = ""
    turns_data = []
    failed = False
    grades = {}
    start_time = time.time()

    try:
        # Execute each turn in the scenario
        for turn_idx, turn in enumerate(scenario["turns"]):
            # Bypasses mock client and connects to active Anthropic model API if live
            mock_client = make_mock_anthropic(turn)
            
            # Append user input
            state.messages.append(Message(role="user", content=turn["user_input"]))
            
            # Override clarification turns if specified
            if turn.get("clarification_turns") is not None:
                state.clarification_turns = turn["clarification_turns"]
            
            if not is_live:
                with patch("app.core.orchestrator.AsyncAnthropic", return_value=mock_client, create=True), \
                     patch("app.core.orchestrator.HAS_ANTHROPIC", True):
                    state = await orchestrator.run_pipeline(state, user_key="eval-key")
            else:
                from app.core.config import settings
                from app.telemetry.llm import traced_anthropic_messages_create
                api_key = settings.anthropic_api_key or os.environ.get("ANTHROPIC_API_KEY")
                
                original_traced_messages_create = traced_anthropic_messages_create
                async def mock_traced_messages_create(client, model, *args, **kwargs):
                    if model == "claude-haiku-4-5-20251001":
                        model = live_model
                    return await original_traced_messages_create(client, model, *args, **kwargs)

                with patch("app.telemetry.llm.traced_anthropic_messages_create", side_effect=mock_traced_messages_create), \
                     patch("app.core.orchestrator.HAS_ANTHROPIC", True):
                    state = await orchestrator.run_pipeline(state, user_key=api_key)
                
            # Assertions: state status
            if not is_live:
                assert state.status.value == turn["expected_status"], (
                    f"{FAILURE_PREFIXES['state']}: Scenario '{scenario['name']}' status mismatch. "
                    f"Expected {turn['expected_status']}, got {state.status.value}"
                )

            assert_current_approach_metadata(state, scenario["name"])

            expected_blind_spot_pillar = scenario.get("expected_blind_spot_pillar")
            if expected_blind_spot_pillar and not is_live:
                actual_pillar = state.metadata["architect_plan"]["selected_blind_spot"]["pillar"]
                assert actual_pillar == expected_blind_spot_pillar, (
                    f"{FAILURE_PREFIXES['blind_spot']}: Scenario '{scenario['name']}' expected blind-spot pillar "
                    f"{expected_blind_spot_pillar}, got {actual_pillar}."
                )

            iterative_discovery = state.metadata.get("iterative_discovery", {})
            expected_strategy = turn.get("expected_discovery_strategy")
            if expected_strategy and not is_live:
                actual_strategy = iterative_discovery.get("next_question_strategy")
                assert actual_strategy == expected_strategy, (
                    f"{FAILURE_PREFIXES['state']}: Scenario '{scenario['name']}' expected discovery strategy "
                    f"{expected_strategy}, got {actual_strategy}."
                )
            if turn.get("expected_ambiguity_fallback") is not None and not is_live:
                assert iterative_discovery.get("ambiguity_fallback") is turn["expected_ambiguity_fallback"], (
                    f"{FAILURE_PREFIXES['state']}: Scenario '{scenario['name']}' ambiguity fallback mismatch. "
                    f"Expected {turn['expected_ambiguity_fallback']}, got {iterative_discovery.get('ambiguity_fallback')}."
                )
            
            # Assertions: process components accumulation
            expected_comps = turn["expected_components"]
            for k, v in expected_comps.items():
                actual_val = getattr(state.process_components, k)
                if not is_live:
                    assert actual_val == v, (
                        f"{FAILURE_PREFIXES['components']}: Scenario '{scenario['name']}' component '{k}' mismatch. "
                        f"Expected '{v}', got '{actual_val}'"
                    )

            assistant_text = latest_assistant_text(state)
            forbidden_terms = scenario.get("forbidden_assistant_terms") or DEFAULT_FORBIDDEN_ASSISTANT_TERMS
            if assistant_text:
                assert_assistant_text_policy(assistant_text, scenario["name"], forbidden_terms)
            elif state.status == SessionStatus.AWAITING_CLARIFICATION:
                assert_assistant_text_policy(assistant_text, scenario["name"], forbidden_terms)

            if state.status == SessionStatus.AWAITING_CLARIFICATION:
                expected_question_count = scenario.get("expected_question_count")
                if expected_question_count is not None and not is_live:
                    assert count_questions(assistant_text) == expected_question_count, (
                        f"{FAILURE_PREFIXES['assistant_text']}: Scenario '{scenario['name']}' expected "
                        f"{expected_question_count} assistant question(s), got {count_questions(assistant_text)}: {assistant_text}"
                    )
                playback_summary = assistant_text
            
            # Record intermediate turn traces
            components = {}
            if state.process_components:
                for field in ["trigger", "actor", "activity", "system", "friction", "location"]:
                    components[field] = getattr(state.process_components, field, None)

            turns_data.append({
                "turn_index": turn_idx + 1,
                "user_input": turn["user_input"],
                "assistant_response": assistant_text or "Report synthesized.",
                "components": components,
                "confidence_score": iterative_discovery.get("e2e_confidence_score", 0.0),
                "next_question_strategy": iterative_discovery.get("next_question_strategy") or state.metadata.get("architect_plan", {}).get("next_node")
            })

        # If the scenario finishes the full synthesis workflow, grade the output using the judge
        if scenario["expect_synthesis"] and state.status.value in ["COMPLETED", "AWAITING_CONFIRMATION"]:
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
            if not is_live:
                for expected_text in scenario.get("expected_report_contains", []):
                    assert expected_text.lower() in synthesized_report.lower(), (
                        f"{FAILURE_PREFIXES['synthesis']}: Scenario '{scenario['name']}' report missing expected text: {expected_text}"
                    )
                for forbidden_text in scenario.get("expected_report_forbidden_terms", []):
                    assert forbidden_text.lower() not in synthesized_report.lower(), (
                        f"{FAILURE_PREFIXES['synthesis']}: Scenario '{scenario['name']}' report included forbidden fallback text: {forbidden_text}"
                    )
                assert_assistant_text_policy(synthesized_report, scenario["name"], DEFAULT_FORBIDDEN_ASSISTANT_TERMS)
            
            constraints_str = ", ".join(scenario["user_constraints"]) if scenario["user_constraints"] else "None"
            
            # Avoid live judge API calls during mock runs by clearing the settings API key
            if not is_live:
                from app.core.config import settings
                with patch.object(settings, "anthropic_api_key", None), \
                     patch.dict(os.environ, {"ANTHROPIC_API_KEY": ""}):
                    grades = await invoke_llm_judge(
                        playback_summary=playback_summary,
                        synthesized_report=synthesized_report,
                        user_constraints=constraints_str
                    )
            else:
                grades = await invoke_llm_judge(
                    playback_summary=playback_summary,
                    synthesized_report=synthesized_report,
                    user_constraints=constraints_str
                )
            
            from app.core.config import settings
            api_key = settings.anthropic_api_key or os.environ.get("ANTHROPIC_API_KEY")
            if api_key and is_live:
                # Assert semantic criteria are scored >= 0.20 (to catch absolute failures/empty outputs)
                assert grades["zero_jargon_score"] >= 0.20, (
                    f"{FAILURE_PREFIXES['judge']}: Zero Jargon compliance failed with score "
                    f"{grades['zero_jargon_score']}. Justification: {grades['justification']}"
                )
                assert grades["hierarchy_integrity_score"] >= 0.20, (
                    f"{FAILURE_PREFIXES['judge']}: Hierarchy integrity compliance failed with score "
                    f"{grades['hierarchy_integrity_score']}. Justification: {grades['justification']}"
                )
                assert grades["consultant_intake_score"] >= 0.20, (
                    f"{FAILURE_PREFIXES['judge']}: Consultant intake behavior failed with score "
                    f"{grades['consultant_intake_score']}. Justification: {grades['justification']}"
                )
                assert grades["single_blind_spot_score"] >= 0.20, (
                    f"{FAILURE_PREFIXES['judge']}: Single blind-spot discipline failed with score "
                    f"{grades['single_blind_spot_score']}. Justification: {grades['justification']}"
                )
                assert grades["factual_grounding_score"] >= 0.20, (
                    f"{FAILURE_PREFIXES['judge']}: Factual grounding failed with score "
                    f"{grades['factual_grounding_score']}. Justification: {grades['justification']}"
                )
                assert grades["privacy_safety_score"] >= 0.20, (
                    f"{FAILURE_PREFIXES['judge']}: Privacy and safety posture failed with score "
                    f"{grades['privacy_safety_score']}. Justification: {grades['justification']}"
                )
            else:
                # When API key is absent or not live, verify mocked fallback scores are returned
                assert grades["zero_jargon_score"] == 1.0
                assert grades["hierarchy_integrity_score"] == 1.0
                assert grades["consultant_intake_score"] == 1.0
                assert grades["single_blind_spot_score"] == 1.0
                assert grades["factual_grounding_score"] == 1.0
                assert grades["privacy_safety_score"] == 1.0

    except Exception as e:
        failed = True
        raise e
    finally:
        elapsed_time = round(time.time() - start_time, 2)
        cumulative_cost = round(state.budget_spent_usd, 4) if is_live else 0.0
        
        judge_scores = grades if (scenario.get("expect_synthesis") and not failed) else {
            "zero_jargon_score": 0.0 if failed else 1.0,
            "hierarchy_integrity_score": 0.0 if failed else 1.0,
            "consultant_intake_score": 0.0 if failed else 1.0,
            "single_blind_spot_score": 0.0 if failed else 1.0,
            "factual_grounding_score": 0.0 if failed else 1.0,
            "privacy_safety_score": 0.0 if failed else 1.0,
            "justification": "Test case failed with runtime or assertion error." if failed else "Evals run in discovery-only mode."
        }

        run_detail = {
            "name": scenario["name"],
            "status": "FAILED" if failed else "PASSED",
            "latency": elapsed_time,
            "cost_usd": cumulative_cost,
            "is_live": is_live,
            "turns": turns_data,
            "judge_scores": judge_scores,
            "report": {
                "as_is_workflow": state.metadata.get("as_is_workflow", ""),
                "friction_analysis": state.metadata.get("friction_analysis", ""),
                "technology_neutral_recommendations": state.metadata.get("technology_neutral_recommendations", ""),
                "roi_economics": state.metadata.get("roi_economics", "")
            } if (scenario.get("expect_synthesis") and not failed) else None
        }
        request.node.user_properties.append(("run_detail", run_detail))


def test_eval_catalog_covers_required_current_approach_matrix() -> None:
    """
    Validates catalog-level coverage for current BuildSense eval requirements.
    """
    assert_catalog_contract()


@pytest.mark.asyncio
async def test_llm_judge_rubrics() -> None:
    """
    Validates that the LLM judge evaluates positive and negative cases correctly.
    """
    is_live = os.environ.get("LIVE_EVALS") == "true"
    if not is_live:
        pytest.skip("Skipping judge rubrics check: LIVE_EVALS is not enabled.")

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
        
    assert good_grades["zero_jargon_score"] >= 0.70
    assert good_grades["hierarchy_integrity_score"] >= 0.70
    assert good_grades["consultant_intake_score"] >= 0.70
    assert good_grades["single_blind_spot_score"] >= 0.70
    assert good_grades["factual_grounding_score"] >= 0.70
    assert good_grades["privacy_safety_score"] >= 0.70

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
    assert (
        bad_grades["zero_jargon_score"] < 0.90
        or bad_grades["hierarchy_integrity_score"] < 0.90
        or bad_grades["consultant_intake_score"] < 0.90
        or bad_grades["single_blind_spot_score"] < 0.90
        or bad_grades["factual_grounding_score"] < 0.90
        or bad_grades["privacy_safety_score"] < 0.90
    )
