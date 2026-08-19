"""Agentic quality evaluation test suite (LLM-as-a-judge).

Loads golden dataset scenarios, executes orchestrator pipeline steps,
and invokes the LLM Judge to assert routing correctness, zero-jargon analogies,
and grounding scores.
"""

import os
import json
from typing import Any, Dict
import httpx
import pytest
from unittest.mock import AsyncMock, patch

from app.core.config import settings
from app.core.orchestrator import orchestrator
from app.models.state import SessionState, SessionMode, SessionStatus, Message
from evals.judge_prompts import JUDGE_SYSTEM_PROMPT, JUDGE_USER_TEMPLATE
from evals.thresholds import PASSING_THRESHOLD, assert_quality_grades_pass


async def invoke_llm_judge(prompt_payload: str) -> Dict[str, Any]:
    """
    Calls the Anthropic Claude API to execute judge grading on agent output.

    Falls back to mock 1.0 scores if ANTHROPIC_API_KEY is missing from environment.

    Arguments:
        prompt_payload: The user prompt containing the agent run details.

    Returns:
        Dict[str, Any]: Parsed JSON results from the LLM Judge.
    """
    api_key = settings.anthropic_api_key or os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        # Graceful fallback mock to pass execution without live API key
        return {
            "routing_accuracy": 1,
            "zero_jargon_score": 1.0,
            "factuality_score": 1.0,
            "current_consultant_score": 1.0,
            "privacy_safety_score": 1.0,
            "justification": "Mocked grading: ANTHROPIC_API_KEY environment variable is not defined."
        }

    headers = {
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }

    request_body = {
        "model": "claude-sonnet-5",
        "max_tokens": 8000,
        "system": JUDGE_SYSTEM_PROMPT,
        "messages": [
            {"role": "user", "content": prompt_payload}
        ],
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://api.anthropic.com/v1/messages",
            json=request_body,
            headers=headers,
            timeout=120.0,
        )
        response.raise_for_status()
        response_data = response.json()
        response_text = "".join(
            block["text"]
            for block in response_data.get("content", [])
            if block.get("type") == "text" and "text" in block
        )
        
        # Parse the JSON markdown block or plain text return
        cleaned_text = response_text.strip()
        if cleaned_text.startswith("```json"):
            cleaned_text = cleaned_text.split("```json")[1].split("```")[0].strip()
        elif cleaned_text.startswith("```"):
            cleaned_text = cleaned_text.split("```")[1].split("```")[0].strip()
            
        parsed_grade: Dict[str, Any] = json.loads(cleaned_text, strict=False)
        return parsed_grade


@pytest.mark.evals
@pytest.mark.asyncio
async def test_agent_eval_golden_dataset() -> None:
    """
    Pytest integration test executing evaluations over the golden dataset.

    Graded against:
    - Routing accuracy: Expected status match.
    - Zero-jargon: Analogies provided for terms.
    - Grounding: No hallucinations.

    Arguments:
        None

    Returns:
        None
    """
    # Resolve the path to golden_dataset.json relative to active test folder
    current_dir = os.path.dirname(os.path.abspath(__file__))
    dataset_filepath = os.path.join(current_dir, "golden_dataset.json")

    with open(dataset_filepath, "r", encoding="utf-8") as dataset_file:
        golden_cases = json.load(dataset_file)

    assert len(golden_cases) > 0, "Golden dataset cases are missing."

    is_live = os.environ.get("LIVE_EVALS") == "true"
    api_key_patch = patch.object(settings, "anthropic_api_key", None) if not is_live else patch.dict(os.environ, {})
    
    with api_key_patch, patch.dict(os.environ, {"ANTHROPIC_API_KEY": ""} if not is_live else {}):
        for test_case in golden_cases:
            print(f"\n--- Running Case: {test_case['name']} ---")
            # Build initial SessionState for each test prompt
            state = SessionState(
                session_id=f"quality-session-{test_case['name'].replace(' ', '-')}",
                mode=SessionMode(test_case["mode"]),
                status=SessionStatus.ROUTING,
                budget_spent_usd=0.0,
                max_budget_usd=1.25,
                steps_taken=0,
                max_steps=15,
                messages=[
                    Message(role="user", content=test_case["prompt"], name=None, tool_call_id=None)
                ],
                clarification_questions=[],
                clarification_responses={},
                dag_plan=[],
                metadata={
                    "motivation": test_case["motivation"]
                }
            )

            # Run pipeline
            with patch("app.db.postgres.postgres_client.save_session_state", AsyncMock()), \
                 patch("app.db.redis.redis_client.increment_global_spend", AsyncMock(return_value=0.025)):
                
                output_state = await orchestrator.run_pipeline(state)

                # Assert correct status classification for first turn
                expected_status_str = test_case["expected_routing_status"]
                print(f"Case '{test_case['name']}': Expected routing status: {expected_status_str}, got: {output_state.status.value}")
                if output_state.status.value == "FAILED":
                    print(f"  Failure Reason: {output_state.metadata.get('failure_reason')}")
                assert output_state.status.value == expected_status_str, (
                    f"Routing failed. Expected: {expected_status_str}, got: {output_state.status.value}. Reason: {output_state.metadata.get('failure_reason')}"
                )

                # Drive multi-turn conversation to completion if AWAITING_CLARIFICATION
                final_state = output_state
                if test_case["mode"] == "OPTIMIZER":
                    turn = 0
                    while final_state.status not in [SessionStatus.COMPLETED, SessionStatus.FAILED] and turn < 5:
                        if final_state.status == SessionStatus.AWAITING_CLARIFICATION:
                            required_keys = ["trigger", "actor", "activity", "system"]
                            components_obj = final_state.process_components
                            if hasattr(components_obj, "model_dump"):
                                components = components_obj.model_dump()
                            elif hasattr(components_obj, "dict"):
                                components = components_obj.dict()
                            elif isinstance(components_obj, dict):
                                components = components_obj
                            else:
                                components = {}
                            all_present = all(components.get(k) and str(components[k]).lower() not in ["", "unknown", "none", "null"] for k in required_keys)
                            
                            user_reply = "yep" if all_present else "We use Excel and it is based in Chicago"
                            final_state.messages.append(
                                Message(role="user", content=user_reply, name=None, tool_call_id=None)
                            )
                            final_state.status = SessionStatus.ROUTING
                            
                        final_state = await orchestrator.run_pipeline(final_state)
                        turn += 1

                # Format the judge query payload based on the final conversation state
                messages_dump = [msg.model_dump() for msg in final_state.messages]
                metadata_dump = final_state.metadata
                
                judge_query = JUDGE_USER_TEMPLATE.format(
                    mode=test_case["mode"],
                    motivation=test_case["motivation"],
                    prompt=test_case["prompt"],
                    final_status=final_state.status.value,
                    metadata_dump=json.dumps(metadata_dump),
                    messages_dump=json.dumps(messages_dump),
                )

                # Call the LLM judge to score results
                grades = await invoke_llm_judge(judge_query)

                # Assert scores are above the passing thresholds
                assert grades["routing_accuracy"] == 1, (
                    f"Case '{test_case['name']}': Routing accuracy is low. Justification: {grades.get('justification')}"
                )
                
                # Centralized threshold + live/mock gate (see evals/thresholds.py;
                # BUG-028 was caused by this exact logic being duplicated and
                # then silently weakened/inverted in place).
                assert_quality_grades_pass(grades, is_live)
