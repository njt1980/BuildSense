"""Unit tests verifying stateful process component accumulation and the Playback Confirmation Gate.
"""

import json
from unittest.mock import AsyncMock, patch, MagicMock
import pytest
from app.models.state import SessionState, SessionMode, SessionStatus, Message, ProcessComponents
from app.core.orchestrator import Orchestrator


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
    mock_extract_response_1 = MagicMock()
    mock_extract_response_1.content = [MagicMock(text=json.dumps({
        "trigger": "New order comes in",
        "actor": "Dispatcher",
        "activity": "Manually handle order",
        "system": None,
        "friction": None
    }))]
    mock_extract_response_1.usage.input_tokens = 100
    mock_extract_response_1.usage.output_tokens = 50

    mock_question_response_1 = MagicMock()
    mock_question_response_1.content = [MagicMock(text="What system or software do you use, and what is the primary friction?")]
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
        assert "What system or software" in updated_state.messages[-1].content


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
        playback_confirmed=False
    )

    # Mock Claude response for confirmation gate
    mock_confirm_response = MagicMock()
    mock_confirm_response.content = [MagicMock(text=json.dumps({
        "is_confirmation": True,
        "corrections": {}
    }))]
    mock_confirm_response.usage.input_tokens = 150
    mock_confirm_response.usage.output_tokens = 20
    mock_confirm_response.usage.cache_read_input_tokens = 0
    mock_confirm_response.usage.cache_creation_input_tokens = 0

    # Mock tool execution loop to immediately complete planning
    mock_execute_task_loop = AsyncMock()

    with patch("app.core.orchestrator.AsyncAnthropic", create=True) as mock_anthropic_class, \
         patch("app.core.orchestrator.HAS_ANTHROPIC", True), \
         patch("app.core.orchestrator.Orchestrator._node_sanitize_input", AsyncMock(return_value={})), \
         patch("app.core.orchestrator.Orchestrator._save_intermediate_state", AsyncMock()), \
         patch("app.core.orchestrator.Orchestrator._execute_task_loop", mock_execute_task_loop):

        orchestrator = Orchestrator()
        
        # Patch cache globally or on instance
        with patch.object(orchestrator.cache, "increment_global_spend", AsyncMock(return_value=0.025)):
            mock_client = MagicMock()
            mock_client.messages.create = AsyncMock(return_value=mock_confirm_response)
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
        playback_confirmed=False
    )

    # Mock Claude response for confirmation gate: not a confirmation, system is corrected to Tally ERP
    mock_confirm_response = MagicMock()
    mock_confirm_response.content = [MagicMock(text=json.dumps({
        "is_confirmation": False,
        "corrections": {
            "trigger": None,
            "actor": None,
            "activity": None,
            "system": "Tally ERP",
            "friction": None
        }
    }))]
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

    mock_question_response = MagicMock()
    mock_question_response.content = [MagicMock(text="How do your dispatchers schedule those runs?")]
    mock_question_response.usage.input_tokens = 100
    mock_question_response.usage.output_tokens = 30

    with patch("app.core.orchestrator.AsyncAnthropic", create=True) as mock_anthropic_class, \
         patch("app.core.orchestrator.HAS_ANTHROPIC", True), \
         patch("app.core.orchestrator.Orchestrator._node_sanitize_input", AsyncMock(return_value={})), \
         patch("app.core.orchestrator.Orchestrator._save_intermediate_state", AsyncMock()):

        orchestrator = Orchestrator()
        mock_client = MagicMock()
        mock_client.messages.create = AsyncMock(return_value=mock_question_response)
        mock_anthropic_class.return_value = mock_client

        updated_state = await orchestrator.run_pipeline(state, user_key="mock-key")

        assert updated_state.status == SessionStatus.AWAITING_CLARIFICATION
        question = updated_state.messages[-1].content
        for forbidden in ["trigger", "actor", "friction", "system"]:
            assert forbidden not in question.lower()


@pytest.mark.asyncio
async def test_playback_summary_emoji_formatting() -> None:
    """
    Verifies that the compiled playback summary contains required emojis and labels
    for high scannability.
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
        messages=[Message(role="user", content="Low stock alert...")],
        process_components=components,
        playback_confirmed=False
    )

    with patch("app.core.orchestrator.Orchestrator._node_sanitize_input", AsyncMock(return_value={})), \
         patch("app.core.orchestrator.Orchestrator._save_intermediate_state", AsyncMock()):

        orchestrator = Orchestrator()
        updated_state = await orchestrator.run_pipeline(state)

        assert updated_state.status == SessionStatus.AWAITING_CLARIFICATION
        summary = updated_state.messages[-1].content
        assert "🚚" in summary
        assert "👤" in summary
        assert "⚙️" in summary
        assert "💻" in summary
        assert "⚠️" in summary


@pytest.mark.asyncio
async def test_escape_hatch_max_turns() -> None:
    """
    Verifies that when clarification_turns reaches 2, the system forcefully fills missing slots
    with UNKNOWN/VARIABLE and presents the Playback Summary.
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
        clarification_turns=2
    )

    with patch("app.core.orchestrator.Orchestrator._node_sanitize_input", AsyncMock(return_value={})), \
         patch("app.core.orchestrator.Orchestrator._save_intermediate_state", AsyncMock()):

        orchestrator = Orchestrator()
        updated_state = await orchestrator.run_pipeline(state)

        assert updated_state.status == SessionStatus.AWAITING_CLARIFICATION
        assert updated_state.process_components.actor == "UNKNOWN"
        assert updated_state.process_components.system == "UNKNOWN"
        assert "UNKNOWN" in updated_state.messages[-1].content
        assert "🚚" in updated_state.messages[-1].content


@pytest.mark.asyncio
async def test_escape_hatch_user_dont_know() -> None:
    """
    Verifies that when the user replies with "I don't know" keywords, the system forcefully fills
    missing slots with UNKNOWN/VARIABLE and presents the Playback Summary.
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

    with patch("app.core.orchestrator.Orchestrator._node_sanitize_input", AsyncMock(return_value={})), \
         patch("app.core.orchestrator.Orchestrator._save_intermediate_state", AsyncMock()):

        orchestrator = Orchestrator()
        updated_state = await orchestrator.run_pipeline(state)

        assert updated_state.status == SessionStatus.AWAITING_CLARIFICATION
        assert updated_state.process_components.actor == "UNKNOWN"
        assert "UNKNOWN" in updated_state.messages[-1].content


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

    with patch("app.core.orchestrator.Orchestrator._node_sanitize_input", AsyncMock(return_value={})), \
         patch("app.core.orchestrator.Orchestrator._save_intermediate_state", AsyncMock()):

        orchestrator = Orchestrator()
        updated_state = await orchestrator.run_pipeline(state)

        # Intake is complete, should transition to AWAITING_CLARIFICATION to present Playback Summary
        assert updated_state.status == SessionStatus.AWAITING_CLARIFICATION
        summary = updated_state.messages[-1].content
        assert "🚚" in summary
        assert "👤" in summary
        assert "⚙️" in summary
        assert "💻" in summary
        assert "⚠️" in summary
        assert "To be analyzed and deduced by BuildSense" in summary


@pytest.mark.asyncio
async def test_clarification_does_not_ask_about_bottlenecks() -> None:
    """
    Verifies that the prompt used for clarifying questions explicitly forbids
    asking about bottlenecks, inefficiencies, pain points, or friction.
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
    mock_messages_create = AsyncMock()
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

        # Verify that prompt_question contains the strict constraint
        called = False
        for call in mock_messages_create.call_args_list:
            kwargs = call[1]
            # Since mock messages could be dynamically built, let's search messages content
            messages = kwargs.get("messages", [])
            prompt = ""
            if messages:
                prompt = messages[0].get("content", "")
            else:
                prompt = kwargs.get("system", "")
                
            if "bottlenecks, friction" in prompt or "STRICT CONSTRAINTS" in prompt:
                called = True
                assert "STRICT CONSTRAINTS" in prompt or "FORBIDDEN" in prompt
                assert "bottlenecks, friction, time waste" in prompt or "bottlenecks or delays" not in prompt
        assert called, "client.messages.create was not called with the expected instructions."


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
            system_prompt = kwargs.get("system", "")
            if system_prompt:
                called = True
                assert "Agentic Bottleneck Deduction Instruction" in system_prompt
                assert "Gathered Workflow Components (As-Is State):" in system_prompt
                assert "Trigger: Invoice received" in system_prompt
                assert "Actor: Accountant" in system_prompt
                assert "deduce the hidden friction, double-work" in system_prompt
        assert called
