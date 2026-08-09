"""Orchestrator pipeline module for BuildSense.

Implements the central native Python state machine, handling intent routing,
HITL clarification steps, worker personas execution, context pruning,
untrusted output XML boundaries, and cost controls.
"""

from typing import Any, Dict, List, Tuple
from app.db.postgres import postgres_client
from app.db.redis import redis_client
from app.models.state import SessionState, SessionMode, SessionStatus, Message


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

    async def run_pipeline(self, state: SessionState) -> SessionState:
        """
        Executes state machine transitions for the BuildSense orchestrator.

        Arguments:
            state: The active SessionState to process.

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
                state.status = SessionStatus.PLANNING

            # 2. Planning Phase
            if state.status == SessionStatus.PLANNING:
                state.dag_plan = await self._generate_task_dag(state)
                state.status = SessionStatus.EXECUTING
                await self.db.save_session_state(state)

            # 3. Execution Phase
            if state.status == SessionStatus.EXECUTING:
                await self._execute_task_loop(state)
                
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

    async def _execute_task_loop(self, state: SessionState) -> None:
        """
        Native execution loop running tasks sequentially while checking budgets and steps limits.

        Arguments:
            state: The active SessionState.

        Returns:
            None
        """
        # Run loop until all plan tasks are finished
        while any(not task["done"] for task in state.dag_plan):
            # Locate the next uncompleted task in the plan
            next_task = next(task for task in state.dag_plan if not task["done"])
            
            # Simulate execution step
            step_cost = 0.025  # Hypothetical cost in USD for this mock execution step
            
            # Atomic cost update in Redis
            total_spend_today = await self.cache.increment_global_spend(step_cost)
            
            # Update state counters
            state.steps_taken += 1
            state.budget_spent_usd += step_cost

            # Check maximum steps safety guardrail
            if state.steps_taken > state.max_steps:
                state.status = SessionStatus.FAILED
                state.metadata["failure_reason"] = "Maximum execution step limit exceeded."
                return

            # Check maximum budget safety guardrail
            if state.budget_spent_usd > state.max_budget_usd:
                state.status = SessionStatus.FAILED
                state.metadata["failure_reason"] = "Maximum session budget cap exceeded."
                return

            # Check if global cap has been breached during run
            if total_spend_today >= 10.00:
                state.status = SessionStatus.FAILED
                state.metadata["failure_reason"] = "Global daily system budget limit reached."
                return

            # Simulate raw search result output (treated as untrusted input)
            raw_tool_output = f"Raw API search results for task: {next_task['task']}"

            # 1. Wrap raw output inside security boundaries to prevent injection
            wrapped_output = self._wrap_untrusted_output(raw_tool_output, source="web_search_mcp")

            # 2. Apply context pruning to summarize output
            pruned_summary = self._prune_context(wrapped_output)

            # Store the pruned output in message history
            state.messages.append(
                Message(
                    role="tool",
                    content=pruned_summary,
                    name=next_task["persona"],
                    tool_call_id=None,
                )
            )

            # Mark the active task as completed
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
        # Context pruning simulation: return a light, concise summary
        return f"Summary: Successful execution. Extracted key signals from source."

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
            "4. Unit Economics: Strong LTV:CAC projections with low CAC requirements."
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
