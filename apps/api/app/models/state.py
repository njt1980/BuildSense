"""State schemas and enumerations for BuildSense orchestrator sessions.

This module contains strict Pydantic v2 schemas and Enum models to manage,
serialize, and deserialize session states, execution steps, budget bounds,
and conversation histories.
"""

from enum import Enum
import re
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, field_validator


class SessionMode(str, Enum):
    """
    Enumeration representing the functional operational mode of a BuildSense session.

    Attributes:
        OPTIMIZER: Mode for optimizing manual SMB workflows/SOPs.
    """
    OPTIMIZER = "OPTIMIZER"


class SessionStatus(str, Enum):
    """
    Enumeration representing the pipeline execution status of a BuildSense session.

    Attributes:
        ROUTING: Classifying user intent and completeness.
        AWAITING_CLARIFICATION: Paused for Human-in-the-Loop clarification.
        PLANNING: Constructing the step-by-step DAG execution plan.
        EXECUTING: Orchestrator loop invoking tools and gathering data.
        SYNTHESIZING: Compiling data and formatting final reports.
        COMPLETED: Session finished successfully.
        FAILED: Session execution terminated due to budget caps, errors, or limits.
    """
    ROUTING = "ROUTING"
    AWAITING_CLARIFICATION = "AWAITING_CLARIFICATION"
    PLANNING = "PLANNING"
    EXECUTING = "EXECUTING"
    SYNTHESIZING = "SYNTHESIZING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class FailureSeverity(str, Enum):
    """Classification of the user-visible impact of an operational failure."""

    DEGRADED = "DEGRADED"
    USER_ACTIONABLE = "USER_ACTIONABLE"
    INTEGRITY_CRITICAL = "INTEGRITY_CRITICAL"


class FailureMetadata(BaseModel):
    """Sanitized metadata describing a failure that affected the session.

    Attributes:
        node: Orchestrator node or boundary where the failure occurred.
        category: Stable failure category used for telemetry and UI handling.
        severity: Whether the session is degraded, retryable by the user, or failed.
        retryable: Whether retrying the affected operation may succeed.
        reason: Short, secret-free diagnostic reason safe for persistence.
    """

    node: str = Field(..., description="Orchestrator node or integration boundary.")
    category: str = Field(..., description="Stable operational failure category.")
    severity: FailureSeverity = Field(..., description="User-visible impact classification.")
    retryable: bool = Field(..., description="Whether the operation can be retried safely.")
    reason: str = Field(..., max_length=240, description="Bounded, sanitized diagnostic reason.")

    @field_validator("reason", mode="before")
    @classmethod
    def sanitize_reason(cls, value: object) -> str:
        """Redact provider keys and bound failure reasons before persistence.

        Args:
            value: Candidate diagnostic reason supplied by an integration boundary.

        Returns:
            A single-line, secret-free reason suitable for session state.

        Raises:
            ValueError: If the reason is not a string or is empty after sanitization.
        """
        if not isinstance(value, str):
            raise ValueError("failure reason must be a string")
        sanitized = re.sub(r"(?i)\bsk-[a-z0-9_-]+\b", "[REDACTED_KEY]", value)
        sanitized = re.sub(r"(?i)(secret|api[_ -]?key)\s*[:=]\s*\S+", r"\1=[REDACTED]", sanitized)
        sanitized = " ".join(sanitized.split())
        if not sanitized:
            raise ValueError("failure reason must not be empty")
        if len(sanitized) > 240:
            raise ValueError("failure reason must be at most 240 characters")
        return sanitized


class Message(BaseModel):
    """
    Pydantic schema representing a single conversation message in the orchestrator.

    Attributes:
        role: The sender role (e.g., "system", "user", "assistant", "tool").
        content: The text content of the message.
        name: Optional identifier name for the sender.
        tool_call_id: Optional ID reference for tool invocation responses.
    """
    role: str = Field(..., description="Role of the message sender.")
    content: str = Field(..., description="Text content of the message.")
    name: Optional[str] = Field(None, description="Optional name identifier.")
    tool_call_id: Optional[str] = Field(None, description="Optional tool call ID linking tool output.")


class ProcessComponents(BaseModel):
    """
    Structured operational components of a business process graph.
    """
    trigger: Optional[str] = Field(default=None, description="What event starts the process.")
    actor: Optional[str] = Field(default=None, description="Who executes the workflow activities.")
    activity: Optional[str] = Field(default=None, description="What main manual tasks are performed.")
    system: Optional[str] = Field(default=None, description="What software/hardware systems are used.")
    friction: Optional[str] = Field(default=None, description="What is the primary manual bottleneck or friction point.")
    location: Optional[str] = Field(default=None, description="Optional human-readable location or neighborhood for the business.")


class SessionState(BaseModel):
    """
    Root session state schema capturing execution progress, costs, and content.

    Attributes:
        session_id: A unique identifier for the current session.
        mode: The active SessionMode. BuildSense currently supports only OPTIMIZER.
        status: The current pipeline SessionStatus.
        budget_spent_usd: Total cumulative USD cost of API calls in this session.
        max_budget_usd: Maximum allowed USD budget cap before execution halts.
        steps_taken: Current execution step count in the loop.
        max_steps: Maximum allowed steps in the loop.
        messages: Active history of messages wrapped in the conversation context.
        clarification_questions: HITL questions presented to the user.
        clarification_responses: User responses received for the HITL questions.
        dag_plan: Structured lists representing the step-by-step execution plan.
        metadata: Flexible dictionary for storing execution findings or logs.
    """
    session_id: str = Field(..., description="Unique UUID or key identifying the session.")
    mode: SessionMode = Field(..., description="Workflow optimization mode.")
    status: SessionStatus = Field(SessionStatus.ROUTING, description="Current pipeline progress phase.")
    budget_spent_usd: float = Field(0.0, description="Accumulated LLM and tool cost.")
    max_budget_usd: float = Field(0.0, description="Safety limit on spending.")
    steps_taken: int = Field(0, description="Count of steps executed.")
    max_steps: int = Field(0, description="Safety limit on execution steps.")
    messages: List[Message] = Field(default_factory=list, description="Orchestration conversation history.")
    clarification_questions: List[str] = Field(default_factory=list, description="Pending clarifying queries.")
    clarification_responses: Dict[str, str] = Field(default_factory=dict, description="Answers from the user.")
    dag_plan: List[Dict[str, Any]] = Field(default_factory=list, description="List of tasks in the execution plan.")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Operational metadata and results.")
    file_name: Optional[str] = Field(None, description="Optional uploaded document file name.")
    file_content: Optional[str] = Field(None, description="Optional parsed uploaded document file content.")
    business_vertical: Optional[str] = Field(None, description="The classified business domain vertical (LOGISTICS, MANUFACTURING, WHOLESALE, GENERIC).")
    evidence_ledger: List[Dict[str, Any]] = Field(default_factory=list, description="Categorized user claims on the Evidence Ladder.")
    company_name: Optional[str] = Field(None, description="The name of the company.")
    company_industry: Optional[str] = Field(None, description="The industry of the company.")
    company_core_tools: Optional[str] = Field(None, description="The core tools of the company.")
    user_constraints: List[str] = Field(default_factory=list, description="User business and operational constraints.")
    lang: str = Field("en", description="User selected language code (en, hi, kn, ta, ml).")
    process_components: ProcessComponents = Field(default_factory=lambda: ProcessComponents(), description="Accumulated process components.")
    playback_confirmed: bool = Field(default=False, description="Whether the user confirmed the playback summary.")
    playback_shown: bool = Field(default=False, description="Whether a playback summary was shown to the user on the most recent non-confirmed turn.")
    clarification_turns: int = Field(default=0, description="Count of clarification turns taken during intake.")
    geographic_context: Optional[Dict[str, Any]] = Field(default=None, description="Optional enriched geographic payload (nearby hubs, arteries, constraints).")
    failure: Optional[FailureMetadata] = Field(default=None, description="Sanitized failure or degraded-operation metadata.")
