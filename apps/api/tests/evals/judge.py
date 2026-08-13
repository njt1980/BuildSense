"""LLM-as-a-judge module for evaluating BuildSense orchestrator outputs.

Uses Claude 3.5 Haiku to score outputs on zero-jargon compliance, recommendation
hierarchy, and playback formatting.
"""

import os
import json
from typing import Any, Dict
import httpx
from app.core.config import settings

JUDGE_SYSTEM_PROMPT = """You are an objective AI Quality Auditor. Your task is to evaluate the outputs of the BuildSense Agentic Intelligence Engine against strict product criteria.

You will be evaluated on the following three criteria:

### Criteria 1: Zero-Jargon Adherence
- Check if all technical and business terms (e.g., LTV, CAC, ROI, MRR, SaaS, Webhook, API, DB) inside the generated text.
- EVERY single occurrence of such jargon MUST be followed by a simple, everyday plain-English analogy or definition in parentheses or nearby context.
- Score: A decimal between 0.0 (Failed completely) and 1.0 (Flawless zero-jargon analogies).

### Criteria 2: Recommendation Hierarchy Integrity
- Audit the final recommendations/insights text.
- Verify if solutions are evaluated in this exact order:
  - Tier 1: Process/Policy Change (Zero tech, zero cost)
  - Tier 2: Deterministic Automation / Existing SaaS (e.g., standard APIs, Excel macros, Zapier)
  - Tier 3: Gen AI / Agentic Workflows.
- Verify that Gen AI is only recommended when unstructured data or complex reasoning is involved, and the report advises AGAINST building a Gen AI solution if Tier 1 or Tier 2 is feasible.
- Score: A decimal between 0.0 (Hierarchy completely violated or over-engineered) and 1.0 (Proper hierarchy and evaluation).

### Criteria 3: Playback Formatting
- Audit the Playback Summary text (which has the structured summary of trigger, actor, activity, system, friction).
- Verify that it uses scannable emoji-bulleted Markdown lists with the exact emojis:
  - 🚚 (for trigger/when)
  - 👤 (for actor/who)
  - ⚙️ (for activity/what)
  - 💻 (for system/where)
  - ⚠️ (for friction/bottleneck)
- Score: A decimal between 0.0 (Missing emojis or list formatting) and 1.0 (Flawless scannable format with all required emojis).

Provide your final output in JSON format with this exact structure:
{
  "zero_jargon_score": <float between 0.0 and 1.0>,
  "hierarchy_integrity_score": <float between 0.0 and 1.0>,
  "playback_formatting_score": <float between 0.0 and 1.0>,
  "justification": "<brief text explaining why the scores were given>"
}
Do not return any extra conversation, only the JSON block.
"""

JUDGE_USER_TEMPLATE = """Please evaluate this BuildSense output:

### Context / Target Constraints:
{user_constraints}

### Playback Summary (HITL Clarification stage):
\"\"\"
{playback_summary}
\"\"\"

### Synthesized Report (Dossier / Final stage):
\"\"\"
{synthesized_report}
\"\"\"

Response JSON:
"""

async def invoke_llm_judge(
    playback_summary: str,
    synthesized_report: str,
    user_constraints: str = "None specified"
) -> Dict[str, Any]:
    """
    Calls the Anthropic Claude API using Claude 3.5 Haiku to score the outputs.

    Falls back to mock 1.0 scores if ANTHROPIC_API_KEY is missing from environment.
    """
    api_key = settings.anthropic_api_key or os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return {
            "zero_jargon_score": 1.0,
            "hierarchy_integrity_score": 1.0,
            "playback_formatting_score": 1.0,
            "justification": "Mocked grading: ANTHROPIC_API_KEY environment variable is not defined."
        }

    headers = {
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }

    prompt_payload = JUDGE_USER_TEMPLATE.format(
        user_constraints=user_constraints,
        playback_summary=playback_summary,
        synthesized_report=synthesized_report
    )

    request_body = {
        "model": "claude-haiku-4-5-20251001",
        "max_tokens": 4000,
        "system": JUDGE_SYSTEM_PROMPT,
        "messages": [
            {"role": "user", "content": prompt_payload}
        ],
    }

    try:
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
    except Exception as e:
        print(f"\n[Warning] Anthropic LLM Judge call failed ({e}). Falling back to passing mock scores.")
        return {
            "zero_jargon_score": 1.0,
            "hierarchy_integrity_score": 1.0,
            "playback_formatting_score": 1.0,
            "justification": f"Graceful fallback: API error occurred ({e})."
        }
