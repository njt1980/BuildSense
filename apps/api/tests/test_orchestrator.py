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
        assert len(updated_state.clarification_questions) == 3
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

    with patch.object(orchestrator.db, "save_session_state", AsyncMock()):
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
        mode=SessionMode.SUGGESTER,
        status=SessionStatus.EXECUTING,
        max_budget_usd=0.15,
        max_steps=6,
        messages=[Message(role="user", content="Prompt content details.")],
        dag_plan=[{"task_id": "1", "task": "suggest_concepts", "persona": "Test Persona", "done": False}]
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
    state = SessionState(
        session_id="test-session-routing-caching",
        mode=SessionMode.SUGGESTER,
        status=SessionStatus.ROUTING,
        max_budget_usd=0.15,
        max_steps=6,
        messages=[Message(role="user", content="Here is a very long descriptive product idea prompt containing more than fifteen characters.")]
    )

    with patch.object(orchestrator.db, "save_session_state", AsyncMock()), \
         patch.object(orchestrator.cache, "increment_global_spend", AsyncMock(return_value=0.025)), \
         patch("app.core.orchestrator.HAS_ANTHROPIC", True), \
         patch("app.core.orchestrator.AsyncAnthropic", create=True) as mock_anthropic:
        
        # Mock client responses
        mock_client = AsyncMock()
        mock_anthropic.return_value = mock_client
        
        # Mock response for sanitize_input (Haiku)
        mock_sanitize = AsyncMock()
        mock_sanitize.content = [AsyncMock(text="Here is a very long descriptive product idea prompt containing more than fifteen characters.")]
        mock_sanitize.usage = AsyncMock(input_tokens=80, output_tokens=15)
        
        # Mock response for route_intent (Haiku)
        mock_haiku_response = AsyncMock()
        mock_haiku_response.content = [AsyncMock(text='{"vertical": "LOGISTICS", "is_complete": true, "clarification_questions": []}')]
        mock_haiku_response.usage = AsyncMock(input_tokens=100, output_tokens=20)
        
        # Mock response for execute_tools (Sonnet)
        mock_sonnet_response = AsyncMock()
        mock_sonnet_response.stop_reason = "end_turn"
        mock_sonnet_response.content = [AsyncMock(text="Final suggest output")]
        mock_sonnet_response.usage = AsyncMock(input_tokens=1200, output_tokens=150, cache_read_input_tokens=1000, cache_creation_input_tokens=0)
        
        # Mock response for synthesize_report (Sonnet)
        mock_synthesis_response = AsyncMock()
        mock_synthesis_response.content = [AsyncMock(text='{"quick_insights": "Quick summary", "deep_dive": "Deep summary"}')]
        mock_synthesis_response.usage = AsyncMock(input_tokens=1500, output_tokens=300)
        
        # mock_client.messages.create will be called 4 times in the full pipeline
        mock_client.messages.create = AsyncMock(side_effect=[
            mock_sanitize,
            mock_haiku_response,
            mock_sonnet_response,
            mock_synthesis_response
        ])

        # Execute - pass user_key so API key is present for routing and sanitization LLM calls
        updated_state = await orchestrator.run_pipeline(state, user_key="sk-ant-testkey")
        
        # Verify model calls
        assert mock_client.messages.create.call_count == 4
        
        # First call (Haiku in sanitize_input)
        call1_kwargs = mock_client.messages.create.call_args_list[0].kwargs
        assert call1_kwargs["model"] == "claude-3-5-haiku-20241022"
        
        # Second call (Haiku in route_intent)
        call2_kwargs = mock_client.messages.create.call_args_list[1].kwargs
        assert call2_kwargs["model"] == "claude-3-5-haiku-20241022"
        
        # Third call (Sonnet in execute_tools)
        call3_kwargs = mock_client.messages.create.call_args_list[2].kwargs
        assert call3_kwargs["model"] == "claude-3-5-sonnet-20241022"
        
        # Fourth call (Sonnet in synthesize_report)
        call4_kwargs = mock_client.messages.create.call_args_list[3].kwargs
        assert call4_kwargs["model"] == "claude-3-5-sonnet-20241022"
        
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
        sonnet_metrics = next(m for m in cache_metrics if m.get("model") == "claude-3-5-sonnet-20241022" and m.get("node") == "execute_tools")
        assert sonnet_metrics["cache_read_tokens"] == 1000
        
        # Check budget spent uses cached rate
        # Cost is calculated as:
        # Call 1 (Haiku): (80 * 0.8 + 15 * 4.0) / 1_000_000 = 0.000124
        # Call 2 (Haiku): (100 * 0.8 + 20 * 4.0) / 1_000_000 = 0.00016
        # Call 3 (Sonnet): ((1200 - 1000) * 3.0 + 1000 * 0.3 + 150 * 15.0) / 1_000_000 = 0.00315
        # Call 4 (Sonnet): (1500 * 3.0 + 300 * 15.0) / 1_000_000 = 0.009
        # Total cost: 0.000124 + 0.00016 + 0.00315 + 0.009 = 0.012434
        assert abs(updated_state.budget_spent_usd - 0.012434) < 1e-6


@pytest.mark.asyncio
async def test_orchestrator_starter_chip_routing() -> None:
    """
    Checks that starter chip inputs like "Walk through a typical customer order"
    evaluate as incomplete and route to AWAITING_CLARIFICATION.
    """
    orchestrator = Orchestrator()
    state = SessionState(
        session_id="test-session-starter-chip",
        mode=SessionMode.SUGGESTER,
        status=SessionStatus.ROUTING,
        max_budget_usd=0.15,
        max_steps=6,
        messages=[Message(role="user", content="Walk through a typical customer order")]
    )

    with patch.object(orchestrator.db, "save_session_state", AsyncMock()) as mock_save:
        updated_state = await orchestrator.run_pipeline(state)
        
        assert updated_state.status == SessionStatus.AWAITING_CLARIFICATION
        assert len(updated_state.clarification_questions) == 3
        assert mock_save.call_count >= 1

