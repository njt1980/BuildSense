"""Unit tests for the BuildSense Orchestrator engine.

Tests verify state machine transitions, context pruning, cost controls,
untrusted output XML containment, and HITL check boundaries.
"""

from unittest.mock import AsyncMock, patch, MagicMock
import pytest
from app.models.state import SessionState, SessionMode, SessionStatus, Message, ProcessComponents
from app.core.orchestrator import Orchestrator


def test_orchestrator_system_prompt_includes_anti_inference_guardrail() -> None:
    """Ensures the live orchestration prompt includes the final MVC and anti-inference rules."""
    orchestrator = Orchestrator()
    system_prompt = orchestrator._build_system_guidance()

    assert "Phase 0: Triage Gate" in system_prompt
    assert "Tool Execution Constraint (Anti-Inference Trap)" in system_prompt
    assert "Single Output Execution" in system_prompt


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
        mode=SessionMode.OPTIMIZER,
        status=SessionStatus.ROUTING,
        max_budget_usd=1.25,
        max_steps=15,
        messages=[Message(role="user", content="too short")]
    )

    with patch.object(orchestrator.db, "save_session_state", AsyncMock()) as mock_save:
        updated_state = await orchestrator.run_pipeline(state)
        
        assert updated_state.status == SessionStatus.AWAITING_CLARIFICATION
        assert len(updated_state.clarification_questions) in [1, 3]
        assert mock_save.call_count >= 1


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
    components = ProcessComponents(
        trigger="New orders trigger route planning",
        actor="Dispatcher",
        activity="Schedule and optimize delivery runs",
        system="Tally ERP and Excel",
        friction="Double data entry takes 2 hours"
    )
    state = SessionState(
        session_id="test-session-456",
        mode=SessionMode.OPTIMIZER,
        status=SessionStatus.ROUTING,
        max_budget_usd=1.25,
        max_steps=15,
        messages=[Message(role="user", content="Yes, confirm.")],
        process_components=components,
        playback_confirmed=True
    )

    with patch.object(orchestrator, "_generate_task_dag", return_value=[{"task_id": "1", "task": "deconstruct_workflows", "persona": "Test Persona", "done": False}]), \
         patch.object(orchestrator.db, "save_session_state", AsyncMock()) as mock_save_db, \
         patch.object(orchestrator.cache, "increment_global_spend", AsyncMock(return_value=0.025)), \
         patch("app.core.orchestrator.HAS_ANTHROPIC", False):
        
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
        mode=SessionMode.OPTIMIZER,
        status=SessionStatus.EXECUTING,
        max_budget_usd=0.01,  # Set very small budget limit
        max_steps=15,
        messages=[Message(role="user", content="Prompt content detail text.")],
        dag_plan=[{"task_id": "1", "task": "run_test", "persona": "Test Persona", "done": False}]
    )

    with patch.object(orchestrator.db, "save_session_state", AsyncMock()), \
         patch.object(orchestrator.cache, "increment_global_spend", AsyncMock(return_value=0.025)), \
         patch("app.core.orchestrator.HAS_ANTHROPIC", False):
        
        await orchestrator._execute_task_loop(state)
        
        assert state.status == SessionStatus.FAILED
        assert "failure_reason" in state.metadata
        assert "budget cap exceeded" in state.metadata["failure_reason"]


@pytest.mark.asyncio
async def test_orchestrator_document_ingestion() -> None:
    """
    Checks that uploaded document content is parsed and injected in routing phase.

    Arguments:
        None

    Returns:
        None
    """
    orchestrator = Orchestrator()
    state = SessionState(
        session_id="test-session-doc-999",
        mode=SessionMode.OPTIMIZER,
        status=SessionStatus.ROUTING,
        max_budget_usd=1.25,
        max_steps=15,
        messages=[Message(role="user", content="Workflow optimization prompt.")],
        file_name="invoice_sop.txt",
        file_content="Step 1: Parse PDF invoices\nStep 2: Save to Excel"
    )

    with patch.object(orchestrator.db, "save_session_state", AsyncMock()), \
         patch.object(orchestrator, "_execute_task_loop", AsyncMock()), \
         patch("app.core.orchestrator.HAS_ANTHROPIC", False):
        updated_state = await orchestrator.run_pipeline(state)
        
        # Check that state has reached planning
        assert updated_state.status in [SessionStatus.PLANNING, SessionStatus.EXECUTING, SessionStatus.COMPLETED]
        
        # Search messages for document context
        doc_message = next(msg for msg in updated_state.messages if "invoice_sop.txt" in msg.content)
        assert doc_message is not None
        assert '<untrusted_tool_output source="uploaded_document">' in doc_message.content
        assert 'Parse PDF invoices' in doc_message.content


@pytest.mark.asyncio
async def test_orchestrator_byok_bypass() -> None:
    """
    Checks that user BYOK keys successfully bypass global spend limits.

    Arguments:
        None

    Returns:
        None
    """
    orchestrator = Orchestrator()
    state = SessionState(
        session_id="test-session-byok-888",
        mode=SessionMode.OPTIMIZER,
        status=SessionStatus.EXECUTING,
        max_budget_usd=1.25,
        max_steps=15,
        messages=[Message(role="user", content="Prompt content details.")],
        dag_plan=[{"task_id": "1", "task": "deconstruct_workflows", "persona": "Test Persona", "done": False}]
    )

    # We mock live execution to check is_byok bypass of global spend.
    # If is_byok=True, even when increment_global_spend returns $10.50 (limit breached),
    # the run should proceed without setting status to FAILED.
    with patch.object(orchestrator.db, "save_session_state", AsyncMock()), \
         patch.object(orchestrator.cache, "increment_global_spend", AsyncMock(return_value=10.50)), \
         patch("app.core.orchestrator.HAS_ANTHROPIC", True), \
         patch("app.core.orchestrator.AsyncAnthropic", create=True) as mock_anthropic:
        
        # Mock client responses
        mock_client = AsyncMock()
        mock_anthropic.return_value = mock_client
        mock_response = AsyncMock()
        mock_response.stop_reason = "end_turn"
        mock_response.content = [AsyncMock(text="Final suggest output")]
        mock_client.messages.create = AsyncMock(return_value=mock_response)

        # Call with user_key to trigger BYOK bypass
        await orchestrator._execute_task_loop(state, user_key="sk-ant-testkey")
        
        # Verify that session status is NOT FAILED
        assert state.status != SessionStatus.FAILED


@pytest.mark.asyncio
async def test_tiered_routing_and_caching() -> None:
    """
    Verifies that route_intent invokes Claude 3.5 Haiku, execute_tools uses Claude 3.5 Sonnet,
    and cache control parameters are correctly configured.
    """
    orchestrator = Orchestrator()
    components = ProcessComponents(
        trigger="Low stock alert",
        actor="Warehouse manager",
        activity="Order inventory replenishment",
        system="Excel spreadsheet",
        friction="Double data entry takes 2 hours"
    )
    state = SessionState(
        session_id="test-session-routing-caching",
        mode=SessionMode.OPTIMIZER,
        status=SessionStatus.ROUTING,
        max_budget_usd=1.25,
        max_steps=15,
        messages=[Message(role="user", content="Yes, confirm.")],
        process_components=components,
        playback_confirmed=False
    )

    with patch.object(orchestrator.db, "save_session_state", AsyncMock()), \
         patch.object(orchestrator.cache, "increment_global_spend", AsyncMock(return_value=0.025)), \
         patch("app.core.orchestrator.HAS_ANTHROPIC", True), \
         patch("app.core.orchestrator.AsyncAnthropic", create=True) as mock_anthropic:
        
        # Mock client responses
        mock_client = AsyncMock()
        mock_anthropic.return_value = mock_client
        
        # Mock response for sanitize_input (Haiku)
        mock_sanitize = make_mock_response("Here is a very long descriptive product idea prompt containing more than fifteen characters.")
        mock_sanitize.usage.input_tokens = 80
        mock_sanitize.usage.output_tokens = 15
        
        # Mock response for route_intent (Haiku confirmation gate check)
        mock_haiku_response = make_mock_response('{"is_confirmation": true, "corrections": {}}')
        mock_haiku_response.usage.input_tokens = 100
        mock_haiku_response.usage.output_tokens = 20
        
# Mock response for first execute_tools task (Sonnet)
        mock_sonnet_response_1 = make_mock_response("Final suggest output")
        mock_sonnet_response_1.stop_reason = "end_turn"
        mock_sonnet_response_1.usage.input_tokens = 1200
        mock_sonnet_response_1.usage.output_tokens = 150
        mock_sonnet_response_1.usage.cache_read_input_tokens = 1000
        mock_sonnet_response_1.usage.cache_creation_input_tokens = 0

        # Mock response for second execute_tools task (Sonnet)
        mock_sonnet_response_2 = make_mock_response("Follow-up execution output")
        mock_sonnet_response_2.stop_reason = "end_turn"
        mock_sonnet_response_2.usage.input_tokens = 1200
        mock_sonnet_response_2.usage.output_tokens = 150
        mock_sonnet_response_2.usage.cache_read_input_tokens = 1000
        mock_sonnet_response_2.usage.cache_creation_input_tokens = 0

        # Mock response for synthesize_report (Sonnet)
        mock_synthesis_response = make_mock_response('{"quick_insights": "Quick summary", "deep_dive": "Deep summary"}')
        mock_synthesis_response.usage.input_tokens = 1500
        mock_synthesis_response.usage.output_tokens = 300

        # mock_client.messages.create will be called 5 times in the full pipeline
        mock_client.messages.create = AsyncMock(side_effect=[
            mock_sanitize,
            mock_haiku_response,
            mock_sonnet_response_1,
            mock_sonnet_response_2,
            mock_synthesis_response
        ])

        # Execute - pass user_key so API key is present for routing and sanitization LLM calls
        updated_state = await orchestrator.run_pipeline(state, user_key="sk-ant-testkey")
        
        # Verify model calls
        assert mock_client.messages.create.call_count == 5

        # First call (Haiku in sanitize_input)
        call1_kwargs = mock_client.messages.create.call_args_list[0].kwargs
        assert call1_kwargs["model"] == "claude-haiku-4-5-20251001"

        # Second call (Haiku in route_intent)
        call2_kwargs = mock_client.messages.create.call_args_list[1].kwargs
        assert call2_kwargs["model"] == "claude-haiku-4-5-20251001"

        # Third call (Sonnet in execute_tools) - first task
        call3_kwargs = mock_client.messages.create.call_args_list[2].kwargs
        assert call3_kwargs["model"] == "claude-sonnet-5"

        # Fourth call (Sonnet in execute_tools) - second task
        call4_kwargs = mock_client.messages.create.call_args_list[3].kwargs
        assert call4_kwargs["model"] == "claude-sonnet-5"

        # Fifth call (Sonnet in synthesize_report)
        call5_kwargs = mock_client.messages.create.call_args_list[4].kwargs
        assert call5_kwargs["model"] == "claude-sonnet-5"

        # Verify caching control elements in tools execution (Call 3)
        system_blocks = call3_kwargs["system"]
        assert isinstance(system_blocks, list)
        assert system_blocks[1]["cache_control"] == {"type": "ephemeral"}

        # Verify last tool schema has cache control (Call 3)
        tools_schema = call3_kwargs["tools"]
        assert tools_schema[-1]["cache_control"] == {"type": "ephemeral"}

        # Verify cache metrics are tracked in metadata
        cache_metrics = updated_state.metadata.get("cache_metrics", [])
        assert len(cache_metrics) > 0

        # Find execute_tools step metrics
        execute_metrics = [m for m in cache_metrics if m.get("model") == "claude-sonnet-5" and m.get("node") == "execute_tools"]
        assert len(execute_metrics) == 2
        assert all(m["cache_read_tokens"] == 1000 for m in execute_metrics)

        # Check budget spent uses cached rate
        # Cost is calculated as:
        # Call 1 (Haiku): (80 * 0.8 + 15 * 4.0) / 1_000_000 = 0.000124
        # Call 2 (Haiku): (100 * 0.8 + 20 * 4.0) / 1_000_000 = 0.00016
        # Call 3 (Sonnet): ((1200 - 1000) * 3.0 + 1000 * 0.3 + 150 * 15.0) / 1_000_000 = 0.00315
        # Call 4 (Sonnet): ((1200 - 1000) * 3.0 + 1000 * 0.3 + 150 * 15.0) / 1_000_000 = 0.00315
        # Call 5 (Sonnet): (1500 * 3.0 + 300 * 15.0) / 1_000_000 = 0.009
        # Total cost: 0.000124 + 0.00016 + 0.00315 + 0.00315 + 0.009 = 0.015584
        assert abs(updated_state.budget_spent_usd - 0.015584) < 1e-6

@pytest.mark.asyncio
async def test_orchestrator_starter_chip_routing() -> None:
    """
    Checks that starter chip inputs like "Walk through a typical customer order"
    evaluate as incomplete and route to AWAITING_CLARIFICATION.
    """
    orchestrator = Orchestrator()
    state = SessionState(
        session_id="test-session-starter-chip",
        mode=SessionMode.OPTIMIZER,
        status=SessionStatus.ROUTING,
        max_budget_usd=1.25,
        max_steps=15,
        messages=[Message(role="user", content="Walk through a typical customer order")]
    )

    with patch.object(orchestrator.db, "save_session_state", AsyncMock()) as mock_save:
        updated_state = await orchestrator.run_pipeline(state)
        
        assert updated_state.status == SessionStatus.AWAITING_CLARIFICATION
        assert len(updated_state.clarification_questions) in [1, 3]
        assert mock_save.call_count >= 1


def test_zero_jargon_analogy_parentheses_repeated() -> None:
    """Verifies that all repeat occurrences of jargon are parenthesized with analogies."""
    from app.core.orchestrator import ensure_jargon_analogies
    
    text = "We want to improve our LTV. Also, our LTV is currently low. Our CAC is $50, which increases the CAC."
    result = ensure_jargon_analogies(text)
    
    # Assert LTV and CAC analogies are repeated for every occurrence
    assert result.count("LTV (Lifetime Value: total customer value, like the total amount of milk a cow gives over its entire life)") == 2
    assert result.count("CAC (Customer Acquisition Cost: marketing cost to get one client, like the price of bait needed to catch one fish)") == 2


@pytest.mark.asyncio
async def test_orchestrator_system_prompt_weaves_constraints() -> None:
    """Checks that the synthesis node system prompt includes active user constraints."""
    orchestrator = Orchestrator()
    state = SessionState(
        session_id="test-session-constraints",
        mode=SessionMode.OPTIMIZER,
        status=SessionStatus.SYNTHESIZING,
        max_budget_usd=1.25,
        max_steps=15,
        messages=[Message(role="user", content="Workflow info")],
        user_constraints=["Strict Data Privacy", "No Budget"],
        metadata={"motivation": "EFFICIENCY", "user_persona": "Solo Founder"}
    )
    from app.core.config import settings
    with patch("app.core.orchestrator.AsyncAnthropic", create=True) as mock_anthropic, \
         patch("app.core.orchestrator.HAS_ANTHROPIC", True), \
         patch.object(settings, "anthropic_api_key", "mock-api-key"), \
         patch.object(orchestrator.db, "save_session_state", AsyncMock()):
        
        mock_client = AsyncMock()
        mock_anthropic.return_value = mock_client
        mock_response = make_mock_response(
            '{"as_is_workflow": "As-is", "friction_analysis": "Friction", "technology_neutral_recommendations": "Recommendations", "roi_economics": "ROI"}'
        )
        mock_client.messages.create = AsyncMock(return_value=mock_response)
        
        agent_state = state.model_dump()
        await orchestrator._node_synthesize_report(agent_state)
        
        assert mock_client.messages.create.called
        called_kwargs = mock_client.messages.create.call_args.kwargs
        system_arg = called_kwargs.get("system", "")
        if isinstance(system_arg, list):
            system_prompt = "".join(b["text"] for b in system_arg if isinstance(b, dict) and b.get("type") == "text")
        else:
            system_prompt = system_arg
        
        assert "Strict Data Privacy" in system_prompt
        assert "No Budget" in system_prompt
        assert "If a constraint like 'No Budget' or 'No/Low Budget' is present" in system_prompt
        assert "If a constraint like 'Strict Data Privacy' is present" in system_prompt
