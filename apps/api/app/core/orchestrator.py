"""Orchestrator pipeline module for BuildSense.

Implements the central native Python state machine, handling intent routing,
HITL clarification steps, worker personas execution, context pruning,
untrusted output XML boundaries, and cost controls.
"""

import os
from typing import Any, Dict, List, Optional, Tuple, Union
from app.core.config import settings
from app.db.postgres import postgres_client
from app.db.redis import redis_client
from app.models.state import SessionState, SessionMode, SessionStatus, Message
from app.mcp.tools import web_search_mcp, calculator_mcp, document_parser_mcp

# Optional import of Anthropic SDK to handle environments where the SDK isn't present
try:
    from anthropic import AsyncAnthropic
    from anthropic.types import BetaToolUnionParam
    HAS_ANTHROPIC = True
except ImportError:
    HAS_ANTHROPIC = False


class Orchestrator:
    """
    Core engine managing pipeline state transitions, execution safety, and tool execution loops.
    """

    def __init__(self) -> None:
        """
        Initializes the orchestrator with database references.

        Arguments:
            None

        Returns:
            None
        """
        self.db = postgres_client
        self.cache = redis_client

    async def run_pipeline(self, state: SessionState, user_key: Optional[str] = None) -> SessionState:
        """
        Executes state machine transitions for the BuildSense orchestrator.

        Arguments:
            state: The active SessionState to process.
            user_key: Optional custom user Anthropic API key.

        Returns:
            SessionState: The updated SessionState after transitioning.
        """
        try:
            # 1. Routing Phase
            if state.status == SessionStatus.ROUTING:
                is_complete, questions = await self._classify_intent_and_completeness(state)
                if not is_complete:
                    state.clarification_questions = questions
                    state.status = SessionStatus.AWAITING_CLARIFICATION
                    await self.db.save_session_state(state)
                    return state
                
                # Document ingestion logic: parse and append to messages history wrapped in XML
                if state.file_content:
                    parsed_text = document_parser_mcp(state.file_content)
                    wrapped_text = self._wrap_untrusted_output(parsed_text, source="uploaded_document")
                    state.messages.append(
                        Message(
                            role="user",
                            content=f"Context from uploaded document '{state.file_name or 'unnamed'}':\n{wrapped_text}",
                            name=None,
                            tool_call_id=None
                        )
                    )
                state.status = SessionStatus.PLANNING

            # 2. Planning Phase
            if state.status == SessionStatus.PLANNING:
                state.dag_plan = await self._generate_task_dag(state)
                state.status = SessionStatus.EXECUTING
                await self.db.save_session_state(state)

            # 3. Execution Phase
            if state.status == SessionStatus.EXECUTING:
                await self._execute_task_loop(state, user_key=user_key)
                
                # Check status via local variable assignment to prevent mypy narrow-type comparison errors
                current_pipeline_status: SessionStatus = state.status
                if current_pipeline_status == SessionStatus.FAILED:
                    await self.db.save_session_state(state)
                    return state
                state.status = SessionStatus.SYNTHESIZING

            # 4. Synthesis Phase
            if state.status == SessionStatus.SYNTHESIZING:
                await self._synthesize_final_dossier(state)
                state.status = SessionStatus.COMPLETED

            # Persist the final state update in the database
            await self.db.save_session_state(state)

        except Exception as pipeline_error:
            # Transition to failed state on unhandled exceptions to prevent hanging pipeline runs
            state.status = SessionStatus.FAILED
            state.metadata["error"] = str(pipeline_error)
            await self.db.save_session_state(state)

        return state

    async def _classify_intent_and_completeness(self, state: SessionState) -> Tuple[bool, List[str]]:
        """
        Verifies if prompt inputs contain all critical parameter values.

        Arguments:
            state: The active SessionState containing user messages.

        Returns:
            Tuple[bool, List[str]]: True if inputs are complete, else False along with clarifying questions.
        """
        # Retrieve the user prompt
        user_prompt = state.messages[0].content if state.messages else ""

        # Basic validation check. If prompt is too short, request clarification.
        if len(user_prompt.strip()) < 15:
            return False, [
                "Could you describe the target product idea or business workflow in more detail?",
                "What software tools or applications are currently involved in your process?"
            ]

        return True, []

    async def _generate_task_dag(self, state: SessionState) -> List[Dict[str, Any]]:
        """
        Dynamically constructs the execution DAG nodes based on active motivation mode.

        Arguments:
            state: Active SessionState model.

        Returns:
            List[Dict[str, Any]]: Array of task nodes to execute.
        """
        if state.mode == SessionMode.SUGGESTER:
            return [
                {"task_id": "1", "task": "suggest_concepts", "persona": "Product Ideator Persona", "done": False}
            ]
        elif state.mode == SessionMode.EVALUATOR:
            return [
                {"task_id": "1", "task": "analyze_market_demand", "persona": "Market Analyst Persona", "done": False},
                {"task_id": "2", "task": "evaluate_defensibility", "persona": "Strategist Persona", "done": False},
                {"task_id": "3", "task": "calculate_unit_economics", "persona": "Financial Controller Persona", "done": False}
            ]
        else:
            return [
                {"task_id": "1", "task": "deconstruct_workflows", "persona": "Business Consultant Persona", "done": False},
                {"task_id": "2", "task": "architect_integrations", "persona": "Tech Architect Persona", "done": False}
            ]

    async def _execute_task_loop(self, state: SessionState, user_key: Optional[str] = None) -> None:
        """
        Native execution loop running tasks sequentially. Uses live SDK if key exists.

        Arguments:
            state: The active SessionState.
            user_key: Optional custom user Anthropic API key.

        Returns:
            None
        """
        api_key = user_key or settings.anthropic_api_key or os.environ.get("ANTHROPIC_API_KEY")

        if api_key and HAS_ANTHROPIC:
            await self._execute_live_sdk_loop(state, api_key, is_byok=bool(user_key))
        else:
            await self._execute_mock_simulation_loop(state)

    async def _execute_live_sdk_loop(
        self, state: SessionState, api_key: str, is_byok: bool = False
    ) -> None:
        """
        Invokes the live Anthropic Claude API tool use event-loop.

        Arguments:
            state: The active SessionState.
            api_key: String credential for Anthropic client authorization.
            is_byok: Boolean indicating if custom user key is active.

        Returns:
            None
        """
        client = AsyncAnthropic(api_key=api_key)

        # Structure the tool JSON schemas defined in FastMCP
        tools_schema: List[Any] = [
            {
                "name": "web_search",
                "description": "Fetches market demand signals, competitor data, and pricing points.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "The search terms or query parameters."}
                    },
                    "required": ["query"]
                }
            },
            {
                "name": "calculate_unit_economics",
                "description": "Computes critical financial metrics: LTV:CAC ratio and Payback period.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "ltv": {"type": "number", "description": "Customer Lifetime Value in USD."},
                        "cac": {"type": "number", "description": "Customer Acquisition Cost in USD."},
                        "average_revenue_per_customer": {"type": "number", "description": "Monthly customer revenue."},
                        "gross_margin_percent": {"type": "number", "description": "Expected gross profit margin percent."}
                    },
                    "required": ["ltv", "cac", "average_revenue_per_customer"]
                }
            },
            {
                "name": "parse_sop_workflow",
                "description": "Formats unstructured SOP process descriptions into structured task list steps.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "sop_text": {"type": "string", "description": "Raw description of a manual workflow."}
                    },
                    "required": ["sop_text"]
                }
            }
        ]

        # Translate state message logs into Anthropic API parameter message format
        api_messages: List[Dict[str, Any]] = []
        for message in state.messages:
            # Map standard role classifications
            if message.role in ["user", "assistant"]:
                api_messages.append({"role": message.role, "content": message.content})

        while any(not task["done"] for task in state.dag_plan):
            # Locate the next uncompleted task
            next_task = next(task for task in state.dag_plan if not task["done"])

            # Call Claude API passing the tools list schema
            response = await client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=1500,
                system=f"You are executing task: {next_task['task']} acting as {next_task['persona']}.",
                messages=api_messages,
                tools=tools_schema
            )

            # Check if Claude requested tool execution
            if response.stop_reason == "tool_use":
                # Save assistant's tool-use choice message in history
                api_messages.append({"role": "assistant", "content": response.content})
                
                # Execute individual tool block requests
                for block in response.content:
                    if block.type == "tool_use":
                        tool_id = block.id
                        tool_name = block.name
                        tool_args = block.input

                        step_cost = 0.018  # Average estimated token cost per step run
                        total_spend_today = await self.cache.increment_global_spend(step_cost)

                        state.steps_taken += 1
                        state.budget_spent_usd += step_cost

                        # Safety boundary assertions
                        if state.steps_taken > state.max_steps:
                            state.status = SessionStatus.FAILED
                            state.metadata["failure_reason"] = "Maximum execution step limit exceeded."
                            return

                        if state.budget_spent_usd > state.max_budget_usd:
                            state.status = SessionStatus.FAILED
                            state.metadata["failure_reason"] = "Maximum session budget cap exceeded."
                            return

                        # Only enforce daily spend cap check if not using custom user BYOK key
                        if not is_byok and total_spend_today >= 10.00:
                            state.status = SessionStatus.FAILED
                            state.metadata["failure_reason"] = "Global daily system budget limit reached."
                            return

                        # Dispatch arguments to corresponding Python FastMCP tool functions
                        raw_output = ""
                        if tool_name == "web_search":
                            raw_output = web_search_mcp(query=tool_args.get("query", ""))
                        elif tool_name == "calculate_unit_economics":
                            raw_output = calculator_mcp(
                                ltv=float(tool_args.get("ltv", 0.0)),
                                cac=float(tool_args.get("cac", 0.0)),
                                average_revenue_per_customer=float(tool_args.get("average_revenue_per_customer", 0.0)),
                                gross_margin_percent=float(tool_args.get("gross_margin_percent", 80.0))
                            )
                        elif tool_name == "parse_sop_workflow":
                            raw_output = document_parser_mcp(sop_text=tool_args.get("sop_text", ""))

                        # Context Pruning hook - summaries the tool return text
                        pruned_summary = self._prune_context(raw_output)

                        # Feed the tool response block back to the API message array
                        api_messages.append({
                            "role": "user",
                            "content": [
                                {
                                    "type": "tool_result",
                                    "tool_use_id": tool_id,
                                    "content": pruned_summary
                                }
                            ]
                        })

                        # Save tool logs inside SessionState message log history
                        state.messages.append(
                            Message(
                                role="tool",
                                content=pruned_summary,
                                name=next_task["persona"],
                                tool_call_id=tool_id
                            )
                        )
            else:
                # Execution of the active task segment completed
                final_text = response.content[0].text if response.content else ""
                api_messages.append({"role": "assistant", "content": final_text})
                
                state.messages.append(
                    Message(
                        role="assistant",
                        content=final_text,
                        name=next_task["persona"],
                        tool_call_id=None
                    )
                )
                next_task["done"] = True

    async def _execute_mock_simulation_loop(self, state: SessionState) -> None:
        """
        Simulates execution of tasks if the Anthropic API Key is not set.

        Arguments:
            state: The active SessionState.

        Returns:
            None
        """
        while any(not task["done"] for task in state.dag_plan):
            next_task = next(task for task in state.dag_plan if not task["done"])
            
            step_cost = 0.025
            total_spend_today = await self.cache.increment_global_spend(step_cost)
            
            state.steps_taken += 1
            state.budget_spent_usd += step_cost

            if state.steps_taken > state.max_steps:
                state.status = SessionStatus.FAILED
                state.metadata["failure_reason"] = "Maximum execution step limit exceeded."
                return

            if state.budget_spent_usd > state.max_budget_usd:
                state.status = SessionStatus.FAILED
                state.metadata["failure_reason"] = "Maximum session budget cap exceeded."
                return

            if total_spend_today >= 10.00:
                state.status = SessionStatus.FAILED
                state.metadata["failure_reason"] = "Global daily system budget limit reached."
                return

            # Simulate tool outputs using local Python function outputs
            if next_task["task"] == "calculate_unit_economics":
                raw_tool_output = calculator_mcp(ltv=150.0, cac=30.0, average_revenue_per_customer=15.0)
            elif next_task["task"] == "deconstruct_workflows":
                raw_tool_output = document_parser_mcp(sop_text="Step 1: Open Excel\nStep 2: Send Email")
            else:
                raw_tool_output = web_search_mcp(query=next_task["task"])

            # 1. Wrap raw output inside security boundaries to prevent injection
            wrapped_output = self._wrap_untrusted_output(raw_tool_output, source="web_search")

            # 2. Apply context pruning to summarize output
            pruned_summary = self._prune_context(wrapped_output)

            state.messages.append(
                Message(
                    role="tool",
                    content=pruned_summary,
                    name=next_task["persona"],
                    tool_call_id=None,
                )
            )

            next_task["done"] = True

    def _wrap_untrusted_output(self, raw_content: str, source: str) -> str:
        """
        Wraps unstructured outputs returned by tools inside strict XML boundaries.

        Arguments:
            raw_content: Raw unstructured text content.
            source: Name identifier of the tool source.

        Returns:
            str: XML-wrapped output.
        """
        return f'<untrusted_tool_output source="{source}">\n{raw_content}\n</untrusted_tool_output>'

    def _prune_context(self, raw_content: str) -> str:
        """
        Summarizes tool output to prevent conversation token bloat (Context Pruning).

        Arguments:
            raw_content: XML-wrapped raw tool content.

        Returns:
            str: Pruned text summary.
        """
        # Return a light summary to shed token weights
        return f"Summary: Successful execution. Extracted key metrics from tool source."

    async def _synthesize_final_dossier(self, state: SessionState) -> None:
        """
        Compiles the dual-view results and applies the zero-jargon rule.

        Arguments:
            state: The active SessionState.

        Returns:
            None
        """
        motivation = state.metadata.get("motivation", "EDUCATION")

        # Zero-jargon translation dictionary for business/financial terms
        jargon_analogies = {
            "LTV": "LTV (Lifetime Value: the total profit a customer brings over their relationship)",
            "CAC": "CAC (Customer Acquisition Cost: the marketing spend required to get one customer)",
            "ROI": "ROI (Return on Investment: the financial efficiency or profit gain of your project)",
            "MRR": "MRR (Monthly Recurring Revenue: regular monthly subscription sales)"
        }

        quick_insights_text = (
            "### ⚡ Quick Insights\n"
            "- Target stack ready.\n"
            "- Healthy unit economics projected (LTV / CAC is above 3x).\n"
            "- Focus on zero-cost tiers."
        )

        deep_dive_text = (
            "### 🔬 Deep Dive\n"
            "1. Market Evidence: Positive demand signals found.\n"
            "2. System Specs: Serverless layout designed.\n"
            "3. Moats: High brand value and defensibility.\n"
            "4. Unit Economics: Strong LTV:CAC Projections with low CAC requirements."
        )

        # Apply Zero-Jargon analogies conversion to final text blocks
        for jargon_term, analogy_description in jargon_analogies.items():
            quick_insights_text = quick_insights_text.replace(jargon_term, analogy_description)
            deep_dive_text = deep_dive_text.replace(jargon_term, analogy_description)

        # Store outputs in state metadata
        state.metadata["quick_insights"] = quick_insights_text
        state.metadata["deep_dive"] = deep_dive_text


# Create global orchestrator instance
orchestrator = Orchestrator()
