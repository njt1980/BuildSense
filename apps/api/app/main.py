"""Main application module for BuildSense FastAPI backend.

Initializes the FastAPI application, wires up CORS, Slowapi Redis-backed rate-limiting,
and CostGuard spend limit middleware, and registers the orchestrator routes.
"""

from typing import Awaitable, Callable, Dict, Optional
from fastapi import FastAPI, HTTPException, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from app.core.config import settings
from app.db.redis import redis_client
from app.db.postgres import postgres_client
from app.models.state import SessionState, SessionMode, SessionStatus, Message

# Initialize FastAPI App
app = FastAPI(
    title="BuildSense API Engine",
    description="Agentic Intelligence Engine for Idea Suggestion, Evaluation, and SMB Process Optimization.",
    version="1.0.0",
)

# Initialize Slowapi Rate Limiter using Redis as the backend storage
limiter = Limiter(
    key_func=get_remote_address,
    storage_uri=settings.redis_url,
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)  # type: ignore

# Configure CORS Middleware
ALLOWED_ORIGINS = [
    "http://localhost:3000",
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def check_global_spend_limit_middleware(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    """
    HTTP middleware verifying that the global daily budget cap is not exceeded.

    Intercepts outgoing API calls and blocks execution if spend is >= MAX_GLOBAL_DAILY_SPEND.

    Arguments:
        request: Incoming HTTP request details.
        call_next: Next request processing callback in the chain.

    Returns:
        Response: The response returned by the request chain or 503 JSONResponse.
    """
    # Skip budget checks on health/root paths
    if request.url.path in ["/health", "/", "/health/"]:
        return await call_next(request)

    try:
        # Check if daily spend cap has been breached
        has_exceeded = await redis_client.has_exceeded_daily_spend_limit(
            settings.max_global_daily_spend
        )
        if has_exceeded:
            return JSONResponse(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                content={
                    "detail": "Global daily spend cap limit has been reached. System paused."
                },
            )
    except Exception as connection_error:
        # Log error locally and proceed or raise to prevent blocking in case of cache issues
        pass

    return await call_next(request)


class OrchestrationRequest(BaseModel):
    """
    Pydantic schema representing the user's incoming orchestration query request.
    """
    prompt: Optional[str] = Field(None, description="Initial request prompt or details.")
    motivation: Optional[str] = Field(None, description="Client primary motivation (e.g. REVENUE, EDUCATION).")
    mode: Optional[SessionMode] = Field(None, description="Chosen operational SessionMode.")
    session_id: Optional[str] = Field(None, description="Existing session UUID (for resuming workflows).")
    clarification_responses: Optional[Dict[str, str]] = Field(
        None, description="Human-in-the-loop responses to questions."
    )


@app.get("/")
async def root() -> dict[str, str]:
    """
    Root endpoint serving basic API status metadata.

    Arguments:
        None

    Returns:
        dict[str, str]: Welcome message and api status.
    """
    return {
        "message": "Welcome to BuildSense API Engine",
        "status": "online",
    }


@app.get("/health")
async def health() -> dict[str, str]:
    """
    Health check endpoint to verify backend service liveness.

    Arguments:
        None

    Returns:
        dict[str, str]: A dictionary indicating that the backend service is "ok".
    """
    return {
        "status": "ok",
    }


@app.post("/api/v1/orchestrate")
@limiter.limit("3/day")
async def orchestrate(request: Request, payload: OrchestrationRequest) -> SessionState:
    """
    Starts or resumes the orchestrator pipeline for a BuildSense session.

    Enforces slowapi IP rate-limiting (max 3 runs per IP per 24 hours).

    Arguments:
        request: FastAPI Request object required by Slowapi rate limiter.
        payload: The incoming session orchestration properties.

    Returns:
        SessionState: The updated session state model after executing the pipeline step.
    """
    # Import inside function to prevent circular imports during main module load
    from app.core.orchestrator import orchestrator

    state: Optional[SessionState] = None

    if payload.session_id:
        # Retrieve existing session state from PostgreSQL
        state = await postgres_client.get_session_state(payload.session_id)
        if not state:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Session with ID '{payload.session_id}' not found.",
            )

        # Merge clarification responses if supplied
        if payload.clarification_responses:
            state.clarification_responses.update(payload.clarification_responses)
            state.status = SessionStatus.PLANNING  # Transition directly to planning
    else:
        # Enforce required parameters for new sessions
        if not payload.prompt or not payload.mode:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Prompt and mode are required parameters to initialize a new session.",
            )

        # Build initial SessionState record
        import uuid
        session_id = str(uuid.uuid4())
        
        # Configure step/budget constraints based on operational mode
        if payload.mode == SessionMode.SUGGESTER:
            max_budget = 0.15
            max_steps = 6
        else:
            max_budget = 1.25
            max_steps = 15

        state = SessionState(
            session_id=session_id,
            mode=payload.mode,
            status=SessionStatus.ROUTING,
            budget_spent_usd=0.0,
            max_budget_usd=max_budget,
            steps_taken=0,
            max_steps=max_steps,
            messages=[
                Message(role="user", content=payload.prompt, name=None, tool_call_id=None)
            ],
            clarification_questions=[],
            clarification_responses={},
            dag_plan=[],
            metadata={
                "motivation": payload.motivation or "EDUCATION"
            }
        )
        # Store initial state in PostgreSQL
        await postgres_client.save_session_state(state)

    # Run the session through the orchestrator pipeline
    updated_state = await orchestrator.run_pipeline(state)
    return updated_state


@app.get("/api/v1/session/{session_id}")
async def get_session(session_id: str) -> SessionState:
    """
    Retrieves the current SessionState record for a given session ID.

    Arguments:
        session_id: Unique UUID string representing the target session.

    Returns:
        SessionState: The serialized session state.
    """
    state = await postgres_client.get_session_state(session_id)
    if not state:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session with ID '{session_id}' not found.",
        )
    return state


@app.on_event("startup")
async def startup_event() -> None:
    """
    Pre-connects pool resources for Postgres and Redis on app startup.

    Arguments:
        None

    Returns:
        None
    """
    await redis_client.connect()
    await postgres_client.connect()


@app.on_event("shutdown")
async def shutdown_event() -> None:
    """
    Closes pool connections on app shutdown.

    Arguments:
        None

    Returns:
        None
    """
    await redis_client.disconnect()
    await postgres_client.disconnect()
