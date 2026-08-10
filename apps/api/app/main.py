"""Main application module for BuildSense FastAPI backend.

Initializes the FastAPI application, wires up CORS, Slowapi rate-limiting,
and registers multi-tenant project and orchestrator routes with JWT authentication.
"""

import os
import uuid
from typing import Any, Awaitable, Callable, Dict, List, Optional
from fastapi import FastAPI, HTTPException, Request, Response, status, Header, Depends, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from app.core.config import settings
from app.core.auth import get_current_user, AuthenticatedUser
from app.core.audio import transcribe_and_translate_audio
from app.db.redis import redis_client
from app.db.postgres import postgres_client
from app.models.state import SessionState, SessionMode, SessionStatus, Message

# Initialize FastAPI App
app = FastAPI(
    title="BuildSense API Engine",
    description="Agentic Intelligence Engine for Idea Suggestion, Evaluation, and SMB Process Optimization.",
    version="2.0.0",
)

# Determine Limiter storage URI
def get_limiter_storage_uri(url: str) -> str:
    if not url:
        return "memory://"
    try:
        from urllib.parse import urlparse
        import socket
        parsed = urlparse(url)
        host = parsed.hostname or "localhost"
        port = parsed.port or 6379
        with socket.create_connection((host, port), timeout=0.5):
            return url
    except Exception:
        print("Warning: Redis is unreachable. Falling back to local memory storage for rate limiting.")
        return "memory://"

limiter = Limiter(
    key_func=get_remote_address,
    storage_uri=get_limiter_storage_uri(settings.redis_url),
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
    """
    # Skip budget checks on health/root paths, CORS preflight OPTIONS requests, and custom user keys
    user_key = request.headers.get("x-user-anthropic-key")
    if user_key or request.method == "OPTIONS" or request.url.path in ["/health", "/", "/health/"]:
        return await call_next(request)

    try:
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
    except Exception:
        pass

    return await call_next(request)


class OrchestrationRequest(BaseModel):
    """
    Pydantic schema representing the user's incoming orchestration query request.
    """
    prompt: Optional[str] = Field(None, description="Initial request prompt or details.")
    motivation: Optional[str] = Field(None, description="Client primary motivation (e.g. REVENUE, EDUCATION).")
    mode: Optional[SessionMode] = Field(None, description="Chosen operational SessionMode.")
    session_id: Optional[str] = Field(None, description="Existing session/project UUID.")
    clarification_responses: Optional[Dict[str, str]] = Field(
        None, description="Human-in-the-loop responses to questions."
    )
    file_name: Optional[str] = Field(None, description="Optional uploaded document file name.")
    file_content: Optional[str] = Field(None, description="Optional parsed uploaded document file content.")
    user_persona: Optional[str] = Field("Solo Founder", description="User persona for customized evaluation tone.")


class ProjectCreate(BaseModel):
    title: str
    description: Optional[str] = ""
    mode: SessionMode
    motivation: str
    user_persona: str


@app.get("/")
async def root() -> dict[str, str]:
    return {
        "message": "Welcome to BuildSense API Engine",
        "status": "online",
    }


@app.get("/health")
async def health() -> dict[str, str]:
    return {
        "status": "ok",
    }


# --- Multi-Tenant Projects Router Endpoints ---

@app.post("/api/v1/projects")
async def create_project(
    payload: ProjectCreate,
    current_user: AuthenticatedUser = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Creates a new project record mapped to the authenticated user.
    """
    await postgres_client.create_user_if_not_exists(current_user.id, current_user.email)
    project_id = await postgres_client.create_project(
        user_id=current_user.id,
        title=payload.title,
        description=payload.description or "",
        mode=payload.mode.value,
        motivation=payload.motivation,
        user_persona=payload.user_persona
    )
    return {"project_id": project_id, "status": "created"}


@app.get("/api/v1/projects")
async def list_projects(
    current_user: AuthenticatedUser = Depends(get_current_user)
) -> List[Dict[str, Any]]:
    """
    Lists all projects belonging to the authenticated user.
    """
    await postgres_client.create_user_if_not_exists(current_user.id, current_user.email)
    return await postgres_client.get_user_projects(current_user.id)


@app.get("/api/v1/projects/{project_id}")
async def get_project(
    project_id: str,
    current_user: AuthenticatedUser = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Retrieves project details after validating owner credentials.
    """
    await postgres_client.create_user_if_not_exists(current_user.id, current_user.email)
    project = await postgres_client.get_project(project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project with ID '{project_id}' not found."
        )
    if project["user_id"] != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to requested project resources."
        )
    return project


@app.delete("/api/v1/projects/{project_id}")
async def delete_project(
    project_id: str,
    current_user: AuthenticatedUser = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Deletes project workspace after validation.
    """
    await postgres_client.create_user_if_not_exists(current_user.id, current_user.email)
    project = await postgres_client.get_project(project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found."
        )
    if project["user_id"] != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Unauthorized deletion request."
        )
    await postgres_client.delete_project(project_id)
    return {"status": "deleted"}


@app.post("/api/v1/transcribe")
async def transcribe_audio(
    file: UploadFile = File(...),
    language: str = Form("Auto-Detect"),
    current_user: AuthenticatedUser = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Accepts uploaded regional audio files, transcribes & translates them to English,
    and returns the plain English transcript text.
    """
    await postgres_client.create_user_if_not_exists(current_user.id, current_user.email)
    try:
        content = await file.read()
        transcript = transcribe_and_translate_audio(
            file_bytes=content,
            filename=file.filename or "audio.webm",
            language=language
        )
        return {"transcript": transcript}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Audio transcription error: {str(e)}"
        )


@app.get("/api/v1/projects/{project_id}/graph")
async def get_project_graph(
    project_id: str,
    current_user: AuthenticatedUser = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Retrieves the React Flow nodes and edges configuration.
    """
    await postgres_client.create_user_if_not_exists(current_user.id, current_user.email)
    project = await postgres_client.get_project(project_id)
    if not project or project["user_id"] != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")
    
    nodes, edges = await postgres_client.get_graph(project_id)
    return {"nodes": nodes, "edges": edges}


# --- Mapped /orchestrate endpoints (handles backward compatibility) ---

@app.post("/api/v1/orchestrate")
@limiter.limit("5/day")
async def orchestrate(
    request: Request, 
    payload: OrchestrationRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
    x_user_anthropic_key: Optional[str] = Header(None)
) -> SessionState:
    """
    Starts or resumes the orchestrator pipeline mapping requests to the user's projects.
    """
    from app.core.orchestrator import orchestrator

    # Ensure user is tracked in users database table
    await postgres_client.create_user_if_not_exists(current_user.id, current_user.email)

    project_id = payload.session_id
    project = None

    if project_id:
        project = await postgres_client.get_project(project_id)
        if not project or project["user_id"] != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to requested project session."
            )
    else:
        # Create a new project corresponding to this request run
        title = payload.prompt[:30] + "..." if payload.prompt else "New Ideation Run"
        project_id = await postgres_client.create_project(
            user_id=current_user.id,
            title=title,
            description=payload.prompt or "",
            mode=(payload.mode or SessionMode.SUGGESTER).value,
            motivation=payload.motivation or "EDUCATION",
            user_persona=payload.user_persona or "Solo Founder"
        )
        project = await postgres_client.get_project(project_id)

    assert project is not None

    # Load session state mapping from database or initialize
    state = await postgres_client.get_session_state(project_id)
    if not state:
        max_budget = 0.15 if project["mode"] == "SUGGESTER" else 1.25
        max_steps = 6 if project["mode"] == "SUGGESTER" else 15

        state = SessionState(
            session_id=project_id,
            mode=SessionMode(project["mode"]),
            status=SessionStatus.ROUTING,
            budget_spent_usd=0.0,
            max_budget_usd=max_budget,
            steps_taken=0,
            max_steps=max_steps,
            messages=[
                Message(role="user", content=payload.prompt, name=None, tool_call_id=None)
            ] if payload.prompt else [],
            clarification_questions=[],
            clarification_responses={},
            dag_plan=[],
            metadata={
                "motivation": project["motivation"],
                "user_persona": project["user_persona"]
            },
            file_name=payload.file_name,
            file_content=payload.file_content,
            business_vertical=None,
            evidence_ledger=[]
        )
        await postgres_client.save_session_state(state)
        await postgres_client.save_chat_messages(project_id, state.messages)

    # If resuming clarification answers
    if payload.clarification_responses:
        state.clarification_responses.update(payload.clarification_responses)
        # Add user answers to chat messages log
        for q, ans in payload.clarification_responses.items():
            state.messages.append(Message(role="user", content=f"Q: {q}\nA: {ans}", name=None, tool_call_id=None))
        await postgres_client.save_chat_messages(project_id, state.messages)
        state.status = SessionStatus.PLANNING

    # Run the session orchestrator pipeline
    updated_state = await orchestrator.run_pipeline(state, user_key=x_user_anthropic_key)
    
    # Sync messages back to DB
    await postgres_client.save_chat_messages(project_id, updated_state.messages)
    return updated_state


@app.get("/api/v1/session/{session_id}")
async def get_session(
    session_id: str,
    current_user: AuthenticatedUser = Depends(get_current_user)
) -> SessionState:
    """
    Retrieves the current SessionState record for a given session ID (verifying tenant permissions).
    """
    await postgres_client.create_user_if_not_exists(current_user.id, current_user.email)
    project = await postgres_client.get_project(session_id)
    if not project or project["user_id"] != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Unauthorized access to requested session state details."
        )

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
    Connects pool resources for Postgres/Redis and runs tables migrations on startup.
    """
    await redis_client.connect()
    await postgres_client.connect()
    
    # Run SQL migration setup
    schema_path = os.path.join(os.path.dirname(__file__), "db", "schema.sql")
    if os.path.exists(schema_path):
        try:
            await postgres_client.init_db(schema_path)
            print("Successfully verified PostgreSQL schema tables and RLS configurations.")
        except Exception as e:
            print(f"Warning: PostgreSQL migrations setup aborted ({e})")
            
@app.on_event("shutdown")
async def shutdown_event() -> None:
    await redis_client.disconnect()
    await postgres_client.disconnect()
