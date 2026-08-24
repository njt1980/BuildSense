"""Unit tests verifying stateful process component accumulation and the Playback Confirmation Gate.
"""

import json
from unittest.mock import AsyncMock, patch, MagicMock
import pytest
from app.models.state import SessionState, SessionMode, SessionStatus, Message, ProcessComponents
from app.core.orchestrator import Orchestrator


def make_mock_response(text: str) -> MagicMock:
    block = MagicMock()
    block.text = text
    block.type = "text"
    response = MagicMock()
    response.content = [block]
    response.usage = MagicMock()
    response.usage.input_tokens = 100
    response.usage.output_tokens = 50
    response.usage.cache_read_input_tokens = 0
    response.usage.cache_creation_input_tokens = 0
    return response


@pytest.mark.asyncio
async def test_stateful_accumulator_accumulation_turns() -> None:
    """
    Verifies that the orchestrator accumulates Trigger, Actor, Activity, System, Friction
    across multiple turns and generates targeted questions for the missing ones.
    """
    session_id = "test-accumulator-turn-1"

    # Turn 1: User provides trigger and actor
    state_turn1 = SessionState(
        session_id=session_id,
        mode=SessionMode.OPTIMIZER,
        status=SessionStatus.ROUTING,
        max_budget_usd=1.25,
        max_steps=15,
        messages=[Message(role="user", content="When a new order comes in, dispatchers manually handle it.")],
        process_components=ProcessComponents(),
        playback_confirmed=False
    )

    # Mock Claude response for Turn 1
    mock_extract_response_1 = make_mock_response(json.dumps({
        "trigger": "New order comes in",
        "actor": "Dispatcher",
        "activity": "Manually handle order",
        "system": None,
        "friction": None
    }))
    mock_extract_response_1.usage.input_tokens = 100
    mock_extract_response_1.usage.output_tokens = 50

    mock_question_response_1 = make_mock_response("That helps. What tool or place does your team use to track those orders today?")
    mock_question_response_1.usage.input_tokens = 120
    mock_question_response_1.usage.output_tokens = 40

    # Mock Claude API calls
    mock_messages_create = AsyncMock()
    # First call is extract, second call is generate question
    mock_messages_create.side_effect = [mock_extract_response_1, mock_question_response_1]

    with patch("app.core.orchestrator.AsyncAnthropic", create=True) as mock_anthropic_class, \
         patch("app.core.orchestrator.HAS_ANTHROPIC", True), \
         patch("app.core.orchestrator.Orchestrator._node_sanitize_input", AsyncMock(return_value={})), \
         patch("app.core.orchestrator.Orchestrator._save_intermediate_state", AsyncMock()):
        
        orchestrator = Orchestrator()
        mock_client = MagicMock()
        mock_client.messages.create = mock_messages_create
        mock_anthropic_class.return_value = mock_client

        updated_state = await orchestrator.run_pipeline(state_turn1, user_key="mock-key")

        # Verify components accumulated
        assert updated_state.status == SessionStatus.AWAITING_CLARIFICATION
        assert updated_state.process_components.trigger == "New order comes in"
        assert updated_state.process_components.actor == "Dispatcher"
        assert updated_state.process_components.activity == "Manually handle order"
        assert updated_state.process_components.system is None
        assert updated_state.process_components.friction is None

        # Verify targeted question appended to messages list
        assert len(updated_state.messages) == 2
        assert updated_state.messages[-1].role == "assistant"
        assistant_question = updated_state.messages[-1].content
        assert "what tool" in assistant_question.lower()
        assert "primary friction" not in assistant_question.lower()
        assert assistant_question.count("?") == 1


@pytest.mark.asyncio
async def test_playback_confirmation_gate_yes() -> None:
    """
    Verifies that when all 5 components are present, the system stops for playback confirmation summary.
    Then, once the user responds with "Yes", the state transitions to PLANNING and launches planning/tool execution.
    """
    session_id = "test-playback-yes"

    # Turn 1: All 5 components exist but not confirmed. User sends "Yes, this is accurate."
    components = ProcessComponents(
        trigger="Low stock alert",
        actor="Warehouse manager",
        activity="Order inventory replenishment",
        system="Excel spreadsheet",
        friction="Double data entry takes 2 hours"
    )

    state = SessionState(
        session_id=session_id,
        mode=SessionMode.OPTIMIZER,
        status=SessionStatus.ROUTING,
        max_budget_usd=1.25,
        max_steps=15,
        messages=[
            Message(role="user", content="Low stock alert triggers inventory replenishment by warehouse manager using Excel spreadsheet, double entry takes 2 hours."),
            Message(role="assistant", content="Here is what I understand about your workflow... Is this accurate?"),
            Message(role="user", content="Yes, this is accurate.")
        ],
        process_components=components,
        playback_confirmed=False,
        playback_shown=True
    )

    # Mock Claude response for confirmation gate
    mock_confirm_response = make_mock_response(json.dumps({
        "is_confirmation": True,
        "corrections": {}
    }))
    mock_confirm_response.usage.input_tokens = 150
    mock_confirm_response.usage.output_tokens = 20
    mock_confirm_response.usage.cache_read_input_tokens = 0
    mock_confirm_response.usage.cache_creation_input_tokens = 0
    mock_synthesis_response = make_mock_response(json.dumps({
        "as_is_workflow": "Low stock alert leads the warehouse manager to reorder inventory in Excel.",
        "friction_analysis": "Double data entry costs about 2 hours each cycle.",
        "technology_neutral_recommendations": "Start with one shared replenishment sheet and a clear owner.",
        "roi_economics": "Track time saved per replenishment run before buying new software."
    }))
    mock_synthesis_response.usage.input_tokens = 300
    mock_synthesis_response.usage.output_tokens = 120
    mock_synthesis_response.usage.cache_read_input_tokens = 0
    mock_synthesis_response.usage.cache_creation_input_tokens = 0

    async def mark_live_task_done(t_state: dict, api_key: str, is_byok: bool, task: dict) -> None:
        """Complete one live execution task without making provider calls."""
        task["done"] = True
        t_state["steps_taken"] += 1

    with patch("app.core.orchestrator.AsyncAnthropic", create=True) as mock_anthropic_class, \
         patch("app.core.orchestrator.HAS_ANTHROPIC", True), \
         patch("app.core.orchestrator.Orchestrator._node_sanitize_input", AsyncMock(return_value={})), \
         patch("app.core.orchestrator.Orchestrator._save_intermediate_state", AsyncMock()), \
         patch("app.core.orchestrator.Orchestrator._execute_live_sdk_loop", AsyncMock(side_effect=mark_live_task_done)):

        orchestrator = Orchestrator()
        
        # Patch cache globally or on instance
        with patch.object(orchestrator.cache, "increment_global_spend", AsyncMock(return_value=0.025)):
            mock_client = MagicMock()
            mock_client.messages.create = AsyncMock(side_effect=[mock_confirm_response, mock_synthesis_response])
            mock_anthropic_class.return_value = mock_client

            updated_state = await orchestrator.run_pipeline(state, user_key="mock-key")

        # Verify confirmation sets playback_confirmed=True and moves to synthesis or tools execution
        assert updated_state.playback_confirmed is True
        assert updated_state.status == SessionStatus.COMPLETED


@pytest.mark.asyncio
async def test_playback_confirmation_gate_no_correction() -> None:
    """
    Verifies that when the user corrects a component, the system updates the accumulated components,
    presents a new summary, and remains in AWAITING_CLARIFICATION.
    """
    session_id = "test-playback-no"

    # Turn 1: All 5 components exist but user corrects Excel to Tally.
    components = ProcessComponents(
        trigger="Low stock alert",
        actor="Warehouse manager",
        activity="Order inventory replenishment",
        system="Excel spreadsheet",
        friction="Double data entry takes 2 hours"
    )

    state = SessionState(
        session_id=session_id,
        mode=SessionMode.OPTIMIZER,
        status=SessionStatus.ROUTING,
        max_budget_usd=1.25,
        max_steps=15,
        messages=[
            Message(role="user", content="Low stock alert triggers inventory..."),
            Message(role="assistant", content="Here is what I understand about your workflow... Is this accurate?"),
            Message(role="user", content="No, we don't use Excel, we use Tally ERP.")
        ],
        process_components=components,
        playback_confirmed=False,
        playback_shown=True
    )

    # Mock Claude response for confirmation gate: not a confirmation, system is corrected to Tally ERP
    mock_confirm_response = make_mock_response(json.dumps({
        "is_confirmation": False,
        "corrections": {
            "trigger": None,
            "actor": None,
            "activity": None,
            "system": "Tally ERP",
            "friction": None
        }
    }))
    mock_confirm_response.usage.input_tokens = 150
    mock_confirm_response.usage.output_tokens = 50

    with patch("app.core.orchestrator.AsyncAnthropic", create=True) as mock_anthropic_class, \
         patch("app.core.orchestrator.HAS_ANTHROPIC", True), \
         patch("app.core.orchestrator.Orchestrator._node_sanitize_input", AsyncMock(return_value={})), \
         patch("app.core.orchestrator.Orchestrator._save_intermediate_state", AsyncMock()):

        orchestrator = Orchestrator()
        mock_client = MagicMock()
        mock_client.messages.create = AsyncMock(return_value=mock_confirm_response)
        mock_anthropic_class.return_value = mock_client

        updated_state = await orchestrator.run_pipeline(state, user_key="mock-key")

        # Verify confirmation gate rejected, system updated, new summary presented
        assert updated_state.playback_confirmed is False
        assert updated_state.status == SessionStatus.AWAITING_CLARIFICATION
        assert updated_state.process_components.system == "Tally ERP"
        assert "Tally ERP" in updated_state.messages[-1].content


@pytest.mark.asyncio
async def test_conversational_mask_intake_question() -> None:
    """
    Verifies that generated clarifying questions do not contain technical state-machine terms
    like 'Trigger', 'Actor', 'Activity', 'Friction', or 'System'.
    """
    session_id = "test-conversational-mask"
    state = SessionState(
        session_id=session_id,
        mode=SessionMode.OPTIMIZER,
        status=SessionStatus.ROUTING,
        max_budget_usd=1.25,
        max_steps=15,
        messages=[Message(role="user", content="We map order routes.")],
        process_components=ProcessComponents(trigger="New orders", actor="Drivers"),
        playback_confirmed=False
    )

    mock_extract = make_mock_response(json.dumps({
        "trigger": "New orders",
        "actor": "Drivers",
        "activity": "route scheduling",
        "system": None,
        "friction": None
    }))
    mock_question = make_mock_response("How do your dispatchers schedule those runs?")
    mock_extract.usage.input_tokens = 100
    mock_extract.usage.output_tokens = 50
    mock_question.usage.input_tokens = 120
    mock_question.usage.output_tokens = 40

    with patch("app.core.orchestrator.AsyncAnthropic", create=True) as mock_anthropic_class, \
         patch("app.core.orchestrator.HAS_ANTHROPIC", True), \
         patch("app.core.orchestrator.Orchestrator._node_sanitize_input", AsyncMock(return_value={})), \
         patch("app.core.orchestrator.Orchestrator._save_intermediate_state", AsyncMock()):

        orchestrator = Orchestrator()
        mock_client = MagicMock()
        mock_client.messages.create = AsyncMock(side_effect=[mock_extract, mock_question])
        mock_anthropic_class.return_value = mock_client

        updated_state = await orchestrator.run_pipeline(state, user_key="mock-key")

        assert updated_state.status == SessionStatus.AWAITING_CLARIFICATION
        question = updated_state.messages[-1].content
        for forbidden in ["trigger", "actor", "friction", "system"]:
            assert forbidden not in question.lower()


@pytest.mark.asyncio
async def test_playback_summary_uses_conversational_formatting() -> None:
    """
    Verifies that the compiled playback summary avoids internal schema labels.
    """
    session_id = "test-emoji-formatting"
    components = ProcessComponents(
        trigger="Low stock alert",
        actor="Warehouse manager",
        activity="Order inventory replenishment",
        system="Excel spreadsheet",
        friction="Double data entry takes 2 hours"
    )
    state = SessionState(
        session_id=session_id,
        mode=SessionMode.OPTIMIZER,
        status=SessionStatus.ROUTING,
        max_budget_usd=1.25,
        max_steps=15,
        messages=[Message(role="user", content="The warehouse manager triggers inventory replenishment manually using Excel.")],
        process_components=components,
        playback_confirmed=False
    )

    mock_confirm = make_mock_response(json.dumps({
        "is_confirmation": False,
        "corrections": {}
    }))

    with patch("app.core.orchestrator.AsyncAnthropic", create=True) as mock_anthropic_class, \
         patch("app.core.orchestrator.HAS_ANTHROPIC", True), \
         patch("app.core.orchestrator.Orchestrator._node_sanitize_input", AsyncMock(return_value={})), \
         patch("app.core.orchestrator.Orchestrator._save_intermediate_state", AsyncMock()):

        mock_client = MagicMock()
        mock_client.messages.create = AsyncMock(return_value=mock_confirm)
        mock_anthropic_class.return_value = mock_client

        orchestrator = Orchestrator()
        updated_state = await orchestrator.run_pipeline(state, user_key="mock-key")

        assert updated_state.status == SessionStatus.AWAITING_CLARIFICATION
        summary = updated_state.messages[-1].content
        assert "Warehouse manager" in summary
        assert "Order inventory replenishment" in summary
        assert "If that sounds right" in summary
        assert "Trigger:" not in summary
        assert "Actor:" not in summary
        assert "Activity:" not in summary
        assert "System:" not in summary


@pytest.mark.asyncio
async def test_escape_hatch_max_turns() -> None:
    """
    Verifies that when clarification_turns reaches the three-turn cap, the system
    routes to cautious synthesis instead of fabricating UNKNOWN playback details.
    """
    session_id = "test-escape-hatch-turns"
    state = SessionState(
        session_id=session_id,
        mode=SessionMode.OPTIMIZER,
        status=SessionStatus.ROUTING,
        max_budget_usd=1.25,
        max_steps=15,
        messages=[Message(role="user", content="We do fleet ops.")],
        process_components=ProcessComponents(trigger="dispatch alert"),
        playback_confirmed=False,
        clarification_turns=3
    )

    with patch("app.core.orchestrator.HAS_ANTHROPIC", False), \
         patch("app.core.orchestrator.Orchestrator._node_sanitize_input", AsyncMock(return_value={})), \
         patch("app.core.orchestrator.Orchestrator._save_intermediate_state", AsyncMock()):

        orchestrator = Orchestrator()
        updated_state = await orchestrator.run_pipeline(state)

        assert updated_state.status == SessionStatus.COMPLETED
        assert updated_state.metadata["iterative_discovery"]["ambiguity_fallback"] is True
        assert "Unverified Assumptions" in updated_state.metadata["friction_analysis"]
        assert updated_state.process_components.actor is None
        assert updated_state.process_components.system is None
        assert "UNKNOWN" not in updated_state.metadata["as_is_workflow"]
        assert "Trigger:" not in updated_state.metadata["as_is_workflow"]


@pytest.mark.asyncio
async def test_escape_hatch_user_dont_know() -> None:
    """
    Verifies that an early "I don't know" answer does not force fake completeness
    before the three-turn discovery cap.
    """
    session_id = "test-escape-hatch-dont-know"
    state = SessionState(
        session_id=session_id,
        mode=SessionMode.OPTIMIZER,
        status=SessionStatus.ROUTING,
        max_budget_usd=1.25,
        max_steps=15,
        messages=[Message(role="user", content="I don't know the exact software name.")],
        process_components=ProcessComponents(trigger="dispatch alert"),
        playback_confirmed=False,
        clarification_turns=0
    )

    with patch("app.core.orchestrator.HAS_ANTHROPIC", False), \
         patch("app.core.orchestrator.Orchestrator._node_sanitize_input", AsyncMock(return_value={})), \
         patch("app.core.orchestrator.Orchestrator._save_intermediate_state", AsyncMock()):

        orchestrator = Orchestrator()
        updated_state = await orchestrator.run_pipeline(state)

        assert updated_state.status == SessionStatus.AWAITING_CLARIFICATION
        assert updated_state.process_components.actor is None
        assert updated_state.metadata["iterative_discovery"]["latest_answer_quality"] == "unknown"
        assert "UNKNOWN" not in updated_state.messages[-1].content


@pytest.mark.asyncio
async def test_frictionless_intake_completeness_no_friction() -> None:
    """
    Verifies that when Trigger, Actor, Activity, and System are present,
    but Friction is missing (None), the system considers intake complete and
    presents the Playback Summary (AWAITING_CLARIFICATION with the summary question).
    """
    session_id = "test-frictionless-intake"
    components = ProcessComponents(
        trigger="Low stock alert",
        actor="Warehouse manager",
        activity="Order inventory replenishment",
        system="Excel spreadsheet",
        friction=None
    )
    state = SessionState(
        session_id=session_id,
        mode=SessionMode.OPTIMIZER,
        status=SessionStatus.ROUTING,
        max_budget_usd=1.25,
        max_steps=15,
        messages=[Message(role="user", content="Low stock alert triggers inventory replenishment...")],
        process_components=components,
        playback_confirmed=False
    )

    with patch("app.core.orchestrator.HAS_ANTHROPIC", False), \
         patch("app.core.orchestrator.Orchestrator._node_sanitize_input", AsyncMock(return_value={})), \
         patch("app.core.orchestrator.Orchestrator._save_intermediate_state", AsyncMock()):

        orchestrator = Orchestrator()
        updated_state = await orchestrator.run_pipeline(state)

        # Intake missing financials/risk/personnel, so it asks handshake question
        assert updated_state.status == SessionStatus.AWAITING_CLARIFICATION
        summary = updated_state.messages[-1].content
        assert "Can we look at how the workflow works" in summary
        assert "Trigger:" not in summary
        assert "Actor:" not in summary
        assert "Friction:" not in summary


@pytest.mark.asyncio
async def test_clarification_does_not_ask_about_bottlenecks() -> None:
    """
    Verifies that the consultant intake prompt forbids asking about bottlenecks
    and only exposes one missing component to the LLM at a time.
    """
    session_id = "test-no-bottleneck-clarify-prompt"
    state = SessionState(
        session_id=session_id,
        mode=SessionMode.OPTIMIZER,
        status=SessionStatus.ROUTING,
        max_budget_usd=1.25,
        max_steps=15,
        messages=[Message(role="user", content="We schedule truck runs.")],
        process_components=ProcessComponents(trigger="dispatch alert"),
        playback_confirmed=False
    )

    mock_client = MagicMock()
    mock_extract = make_mock_response(json.dumps({
        "trigger": "dispatch alert",
        "actor": None,
        "activity": "schedule truck runs",
        "system": None,
        "friction": None,
        "location": None,
    }))
    mock_question = make_mock_response("Which location or market do those truck runs usually start from?")
    mock_messages_create = AsyncMock(side_effect=[mock_extract, mock_question])
    mock_client.messages.create = mock_messages_create

    with patch("app.core.orchestrator.AsyncAnthropic", create=True) as mock_anthropic_class, \
         patch("app.core.orchestrator.HAS_ANTHROPIC", True), \
         patch("app.core.orchestrator.Orchestrator._node_sanitize_input", AsyncMock(return_value={})), \
         patch("app.core.orchestrator.Orchestrator._save_intermediate_state", AsyncMock()):

        mock_anthropic_class.return_value = mock_client
        orchestrator = Orchestrator()

        # Run pipeline
        try:
            await orchestrator.run_pipeline(state, user_key="mock-key")
        except Exception:
            pass  # We only care about the parameters passed to mock_messages_create

        # Verify that prompt_question contains the consultant intake constraints
        # and a single selected missing detail rather than a checklist.
        called = False
        for call in mock_messages_create.call_args_list:
            kwargs = call[1]
            # Since mock messages could be dynamically built, let's search messages content
            messages = kwargs.get("messages", [])
            prompt = ""
            if messages:
                content = messages[0].get("content", "")
                if isinstance(content, list):
                    prompt = "".join(b["text"] for b in content if isinstance(b, dict) and b.get("type") == "text")
                else:
                    prompt = content
            else:
                system_arg = kwargs.get("system", "")
                if isinstance(system_arg, list):
                    prompt = "".join(b["text"] for b in system_arg if isinstance(b, dict) and b.get("type") == "text")
                else:
                    prompt = system_arg
                
            if "McKinsey for the common man" in prompt:
                called = True
                assert "Do not ask the owner to name bottlenecks" in prompt
                assert "Ask about exactly one missing detail" in prompt
                assert "selected business blind spot" in prompt
                assert "Ask one short question only" in prompt
                assert "Do not invent, assume, or hallucinate systems" in prompt
                assert "one missing detail: location" in prompt
                assert "one missing detail: location, actor" not in prompt
        assert called, "client.messages.create was not called with the expected instructions."


@pytest.mark.asyncio
async def test_clarification_prompt_receives_one_high_priority_missing_item() -> None:
    """
    Verifies the route intent node mechanically passes one missing component
    into the consultant prompt, preventing checklist-style multi-part questions.
    """
    state = SessionState(
        session_id="test-one-missing-item-intake",
        mode=SessionMode.OPTIMIZER,
        status=SessionStatus.ROUTING,
        max_budget_usd=1.25,
        max_steps=15,
        messages=[Message(role="user", content="A customer calls and asks for an update.")],
        process_components=ProcessComponents(trigger="Customer asks for an update"),
        playback_confirmed=False,
    )

    mock_extract = make_mock_response(json.dumps({
        "trigger": "Customer asks for an update",
        "actor": None,
        "activity": None,
        "system": None,
        "friction": None,
        "location": None,
    }))
    mock_question = make_mock_response("Got it, the customer call starts the work. Who usually handles that follow-up?")

    with patch("app.core.orchestrator.AsyncAnthropic", create=True) as mock_anthropic_class, \
         patch("app.core.orchestrator.HAS_ANTHROPIC", True), \
         patch("app.core.orchestrator.Orchestrator._node_sanitize_input", AsyncMock(return_value={})), \
         patch("app.core.orchestrator.Orchestrator._save_intermediate_state", AsyncMock()):

        mock_client = MagicMock()
        mock_client.messages.create = AsyncMock(side_effect=[mock_extract, mock_question])
        mock_anthropic_class.return_value = mock_client

        updated_state = await Orchestrator().run_pipeline(state, user_key="mock-key")

    prompts = []
    for call in mock_client.messages.create.call_args_list:
        messages = call[1].get("messages", [])
        if messages:
            content = messages[0].get("content", "")
            if isinstance(content, list):
                prompts.append("".join(b["text"] for b in content if isinstance(b, dict) and b.get("type") == "text"))
            else:
                prompts.append(content)
        else:
            system_arg = call[1].get("system", "")
            if isinstance(system_arg, list):
                prompts.append("".join(b["text"] for b in system_arg if isinstance(b, dict) and b.get("type") == "text"))
            else:
                prompts.append(system_arg)
    intake_prompt = next(prompt for prompt in prompts if "McKinsey for the common man" in prompt)

    assert updated_state.status == SessionStatus.AWAITING_CLARIFICATION
    assert "one missing detail: actor" in intake_prompt
    assert "one missing detail: actor, activity" not in intake_prompt
    assert "one missing detail: actor, system" not in intake_prompt


@pytest.mark.asyncio
async def test_agentic_bottleneck_deduction_in_synthesis() -> None:
    """
    Verifies that the synthesis node system prompt contains agentic bottleneck
    deduction instructions and passes the gathered workflow components.
    """
    session_id = "test-agentic-bottleneck-synthesis"
    components = ProcessComponents(
        trigger="Invoice received",
        actor="Accountant",
        activity="Double check details and enter to ERP",
        system="Tally ERP",
        friction=None
    )
    state = SessionState(
        session_id=session_id,
        mode=SessionMode.OPTIMIZER,
        status=SessionStatus.SYNTHESIZING,
        max_budget_usd=1.25,
        max_steps=15,
        messages=[Message(role="user", content="Invoice received triggers Accountant double check...")],
        process_components=components,
        playback_confirmed=True
    )

    mock_client = MagicMock()
    mock_messages_create = AsyncMock()
    mock_client.messages.create = mock_messages_create

    with patch("app.core.orchestrator.AsyncAnthropic", create=True) as mock_anthropic_class, \
         patch("app.core.orchestrator.HAS_ANTHROPIC", True), \
         patch("app.core.orchestrator.postgres_client.save_graph", AsyncMock()), \
         patch("app.core.orchestrator.Orchestrator._save_intermediate_state", AsyncMock()):

        mock_anthropic_class.return_value = mock_client
        orchestrator = Orchestrator()

        state_dict = state.model_dump()
        orchestrator.user_key = "mock-key"
        try:
            await orchestrator._node_synthesize_report(state_dict)
        except Exception:
            pass

        # Verify that synthesize system prompt contains the instructions
        called = False
        for call in mock_messages_create.call_args_list:
            kwargs = call[1]
            system_arg = kwargs.get("system", "")
            if isinstance(system_arg, list):
                system_prompt = "".join(b["text"] for b in system_arg if isinstance(b, dict) and b.get("type") == "text")
            else:
                system_prompt = system_arg
            if system_prompt:
                called = True
                assert "Agentic Bottleneck Deduction Instruction" in system_prompt
                assert "Gathered Workflow Components (As-Is State):" in system_prompt
                assert '"trigger": "Invoice received"' in system_prompt
                assert '"actor": "Accountant"' in system_prompt
                assert "deduce the hidden friction, double-work" in system_prompt
                assert "Six-Pillar Consultant Rubric" in system_prompt
                assert "Market, Operations, Financials, Personnel, Technology, and Risk" in system_prompt
        assert called


@pytest.mark.asyncio
async def test_correction_overwrites_prior_assumption_before_replayback() -> None:
    """
    Verifies direct corrections overwrite old assumptions and regenerate playback.
    """
    components = ProcessComponents(
        trigger="Weekly ranking meeting",
        actor="Drivers",
        activity="Vote on customer priority",
        system="Spreadsheet",
        friction=None,
    )
    state = SessionState(
        session_id="test-correction-overwrite-actor",
        mode=SessionMode.OPTIMIZER,
        status=SessionStatus.ROUTING,
        max_budget_usd=1.25,
        max_steps=15,
        messages=[
            Message(role="assistant", content="Drivers vote on priority. If that sounds right, reply Yes."),
            Message(role="user", content="No, customers vote, not drivers."),
        ],
        process_components=components,
        playback_confirmed=False,
        playback_shown=True,
    )

    mock_confirm = make_mock_response(json.dumps({
        "is_confirmation": False,
        "corrections": {
            "trigger": None,
            "actor": "Customers",
            "activity": None,
            "system": None,
            "friction": None,
            "location": None,
        },
        "unmapped_correction": None,
    }))
    mock_playback = make_mock_response(
        "Thanks, I have updated that: customers vote on customer priority using the spreadsheet. "
        "If that sounds right, reply with 'Yes' to confirm, or correct any part."
    )

    with patch("app.core.orchestrator.AsyncAnthropic", create=True) as mock_anthropic_class, \
         patch("app.core.orchestrator.HAS_ANTHROPIC", True), \
         patch("app.core.orchestrator.Orchestrator._node_sanitize_input", AsyncMock(return_value={})), \
         patch("app.core.orchestrator.Orchestrator._save_intermediate_state", AsyncMock()):

        mock_client = MagicMock()
        mock_client.messages.create = AsyncMock(side_effect=[mock_confirm, mock_playback])
        mock_anthropic_class.return_value = mock_client

        updated_state = await Orchestrator().run_pipeline(state, user_key="mock-key")

    assert updated_state.status == SessionStatus.AWAITING_CLARIFICATION
    assert updated_state.playback_confirmed is False
    assert updated_state.process_components.actor == "Customers"
    assert "customers vote" in updated_state.messages[-1].content.lower()
    assert "UNKNOWN" not in updated_state.messages[-1].content


@pytest.mark.asyncio
async def test_offline_extractor_uses_user_context_for_pet_shop_whatsapp() -> None:
    """
    Verifies offline extraction does not fall back to canned logistics examples
    for small retail workflows described by the user.
    """
    state = SessionState(
        session_id="test-pet-shop-whatsapp-offline",
        mode=SessionMode.OPTIMIZER,
        status=SessionStatus.ROUTING,
        max_budget_usd=1.25,
        max_steps=15,
        messages=[
            Message(
                role="user",
                content="We are a small pet shop and we take orders via Whatsapp",
            )
        ],
        company_industry="General Business / Other",
        company_core_tools="Whatsapp",
        process_components=ProcessComponents(),
        playback_confirmed=False,
    )

    with patch("app.core.orchestrator.HAS_ANTHROPIC", False), \
         patch("app.core.orchestrator.Orchestrator._node_sanitize_input", AsyncMock(return_value={})), \
         patch("app.core.orchestrator.Orchestrator._save_intermediate_state", AsyncMock()):
        orchestrator = Orchestrator()
        updated_state = await orchestrator.run_pipeline(state)

    assert updated_state.status == SessionStatus.AWAITING_CLARIFICATION
    assert updated_state.process_components.trigger == "Customer order received on WhatsApp"
    assert updated_state.process_components.actor == "Shop staff"
    assert updated_state.process_components.activity == "Review and fulfill customer orders"
    assert updated_state.process_components.system == "WhatsApp"
    assert updated_state.process_components.friction is None

    assistant_message = updated_state.messages[-1].content
    assert "Dispatcher" not in assistant_message
    assert "Manual route scheduling" not in assistant_message
    assert "Trigger:" not in assistant_message
    assert "Actor:" not in assistant_message


@pytest.mark.asyncio
async def test_architect_requires_location_for_physical_shop() -> None:
    """
    Verifies the architect creates a location-aware intake plan for physical shops.
    """
    state = SessionState(
        session_id="test-architect-location-required",
        mode=SessionMode.OPTIMIZER,
        status=SessionStatus.ROUTING,
        max_budget_usd=1.25,
        max_steps=15,
        messages=[
            Message(
                role="user",
                content="We are a small pet shop and we take orders via Whatsapp",
            )
        ],
        company_core_tools="Whatsapp",
        process_components=ProcessComponents(),
        playback_confirmed=False,
    )

    with patch("app.core.orchestrator.HAS_ANTHROPIC", False), \
         patch("app.core.orchestrator.Orchestrator._node_sanitize_input", AsyncMock(return_value={})), \
         patch("app.core.orchestrator.Orchestrator._save_intermediate_state", AsyncMock()):
        orchestrator = Orchestrator()
        updated_state = await orchestrator.run_pipeline(state)

    architect_plan = updated_state.metadata["architect_plan"]
    assert architect_plan["requires_location"] is True
    assert "location" in architect_plan["required_components"]
    assert updated_state.process_components.location is None
    assert updated_state.metadata["iterative_discovery"]["next_question_strategy"] == "handshake"
    assert "look at how" in updated_state.messages[-1].content.lower()


@pytest.mark.asyncio
async def test_architect_extracts_explicit_location_and_schedules_enrichment() -> None:
    """
    Verifies explicit locations are captured before analysis and queued for enrichment.
    """
    state = SessionState(
        session_id="test-architect-location-present",
        mode=SessionMode.OPTIMIZER,
        status=SessionStatus.ROUTING,
        max_budget_usd=1.25,
        max_steps=15,
        messages=[
            Message(
                role="user",
                content="We are a small pet shop based in Koramangala and we take orders via Whatsapp",
            )
        ],
        company_core_tools="Whatsapp",
        process_components=ProcessComponents(),
        playback_confirmed=False,
    )

    with patch("app.core.orchestrator.HAS_ANTHROPIC", False), \
         patch("app.core.orchestrator.Orchestrator._node_sanitize_input", AsyncMock(return_value={})), \
         patch("app.core.orchestrator.Orchestrator._save_intermediate_state", AsyncMock()), \
         patch("app.core.orchestrator.Orchestrator._background_geographic_enrichment", AsyncMock()) as mock_enrich:
        orchestrator = Orchestrator()
        updated_state = await orchestrator.run_pipeline(state)

    assert updated_state.process_components.location == "Koramangala"
    assert mock_enrich.call_count >= 1

@pytest.mark.asyncio
async def test_six_pillar_gating_blocks_synthesis() -> None:
    """
    Verifies that BUG-042 gating requires Financials, Risk, and Personnel coverage
    before allowing synthesis, even if core components (trigger/actor/system) are present.
    """
    components = ProcessComponents(
        trigger="Low stock alert",
        actor="Warehouse manager",
        activity="Order inventory replenishment",
        system="Excel spreadsheet",
        friction="Double data entry takes 2 hours"
    )
    state = SessionState(
        session_id="test-six-pillar-gating",
        mode=SessionMode.OPTIMIZER,
        status=SessionStatus.ROUTING,
        max_budget_usd=1.25,
        max_steps=15,
        messages=[Message(role="user", content="Low stock alert triggers inventory replenishment manually using Excel.")],
        process_components=components,
        playback_confirmed=False,
        clarification_turns=1
    )

    with patch("app.core.orchestrator.HAS_ANTHROPIC", False), \
         patch("app.core.orchestrator.Orchestrator._node_sanitize_input", AsyncMock(return_value={})), \
         patch("app.core.orchestrator.Orchestrator._save_intermediate_state", AsyncMock()):
         
        # We manually inject the architect plan without financials/risk to trigger the gate
        with patch("app.core.orchestrator.build_iterative_discovery_metadata") as mock_build_meta:
            # We bypass the actual build metadata to just test routing, or we let it run and check state
            pass
            
        orchestrator = Orchestrator()
        updated_state = await orchestrator.run_pipeline(state)
        
        # It should still be routing/clarification because required pillars are missing
        assert updated_state.status == SessionStatus.AWAITING_CLARIFICATION
        assert updated_state.metadata["iterative_discovery"]["should_synthesize_now"] is False
        assert any("Missing core pillars" in reason for reason in updated_state.metadata["iterative_discovery"]["confidence_reasons"])

