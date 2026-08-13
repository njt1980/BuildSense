import asyncio
from unittest.mock import AsyncMock, patch
from app.core.orchestrator import Orchestrator
from app.models.state import SessionState, SessionMode, SessionStatus, Message, ProcessComponents
from tests.test_orchestrator import make_mock_response

async def main():
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

        mock_client = AsyncMock()
        mock_anthropic.return_value = mock_client

        mock_sanitize = make_mock_response("Here is a very long descriptive product idea prompt containing more than fifteen characters.")
        mock_sanitize.usage.input_tokens = 80
        mock_sanitize.usage.output_tokens = 15

        mock_haiku_response = make_mock_response('{"is_confirmation": true, "corrections": {}}')
        mock_haiku_response.usage.input_tokens = 100
        mock_haiku_response.usage.output_tokens = 20

        mock_sonnet_response = make_mock_response("Final suggest output")
        mock_sonnet_response.stop_reason = "end_turn"
        mock_sonnet_response.usage.input_tokens = 1200
        mock_sonnet_response.usage.output_tokens = 150
        mock_sonnet_response.usage.cache_read_input_tokens = 1000
        mock_sonnet_response.usage.cache_creation_input_tokens = 0

        mock_synthesis_response = make_mock_response('{"quick_insights": "Quick summary", "deep_dive": "Deep summary"}')
        mock_synthesis_response.usage.input_tokens = 1500
        mock_synthesis_response.usage.output_tokens = 300

        mock_client.messages.create = AsyncMock(side_effect=[mock_sanitize, mock_haiku_response, mock_sonnet_response, mock_synthesis_response])

        updated_state = await orchestrator.run_pipeline(state, user_key="sk-ant-testkey")

        print('call_count=', mock_client.messages.create.call_count)
        for i, call in enumerate(mock_client.messages.create.call_args_list):
            print(i, call.kwargs.get('model'), call.kwargs.get('system', None))

if __name__ == '__main__':
    asyncio.run(main())
