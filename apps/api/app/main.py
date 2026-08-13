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


class CompanyCreate(BaseModel):
    name: str
    industry: str
    core_tools: str
    industry_vertical: Optional[str] = None


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
    user_persona: Optional[str] = Field("SMB Operator", description="User persona for customized evaluation tone.")
    industry_vertical: Optional[str] = Field(None, description="The user-selected industry vertical.")
    raw_input_text_or_audio: Optional[str] = Field(None, description="The user's raw text description or audio transcript.")
    company_id: Optional[str] = Field(None, description="The optional associated company UUID.")
    user_constraints: Optional[List[str]] = Field(default_factory=list, description="Client operational and business constraints.")
    lang: Optional[str] = Field("en", description="User selected language code (en, hi, kn, ta, ml).")


class ProjectCreate(BaseModel):
    title: str
    description: Optional[str] = ""
    mode: SessionMode = SessionMode.OPTIMIZER
    motivation: Optional[str] = "EFFICIENCY"
    user_persona: Optional[str] = "SMB Operator"
    company_id: Optional[str] = None


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


# --- Multi-Tenant Companies Router Endpoints ---

@app.post("/api/v1/companies")
async def create_company_endpoint(
    payload: CompanyCreate,
    current_user: AuthenticatedUser = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Creates a new company associated with the user.
    """
    await postgres_client.create_user_if_not_exists(current_user.id, current_user.email)
    company_id = await postgres_client.create_company(
        user_id=current_user.id,
        name=payload.name,
        industry=payload.industry,
        core_tools=payload.core_tools,
        industry_vertical=payload.industry_vertical
    )
    return {"company_id": company_id, "status": "created"}


@app.get("/api/v1/companies")
async def list_companies_endpoint(
    current_user: AuthenticatedUser = Depends(get_current_user)
) -> List[Dict[str, Any]]:
    """
    Lists all companies associated with the user.
    """
    await postgres_client.create_user_if_not_exists(current_user.id, current_user.email)
    return await postgres_client.get_user_companies(current_user.id)


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

    # Validate company ownership
    if payload.company_id:
        company = await postgres_client.get_company(payload.company_id)
        if not company or company["user_id"] != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to specified company."
            )

    project_id = await postgres_client.create_project(
        user_id=current_user.id,
        title=payload.title,
        description=payload.description or "",
        mode=payload.mode.value,
        motivation=payload.motivation or "EFFICIENCY",
        user_persona=payload.user_persona or "SMB Operator",
        company_id=payload.company_id
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
    response: Response,
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
        prompt_text = payload.raw_input_text_or_audio or payload.prompt or ""
        title = prompt_text[:30] + "..." if prompt_text else "New Discovery Run"
        
        # Determine the company_id and company context
        company_id = payload.company_id
        if not company_id:
            companies = await postgres_client.get_user_companies(current_user.id)
            if companies:
                company_id = companies[0]["id"]

        company = None
        if company_id:
            company = await postgres_client.get_company(company_id)
            if not company or company["user_id"] != current_user.id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied to specified company."
                )

        # Parse vertical selection
        if company:
            user_vertical = company["industry_vertical"] or company["industry"]
        else:
            user_vertical = payload.industry_vertical

        db_vertical = "GENERIC"
        if user_vertical:
            v_clean = user_vertical.lower().strip()
            if "logistics" in v_clean or "fleet" in v_clean:
                db_vertical = "LOGISTICS"
            elif "manufacturing" in v_clean:
                db_vertical = "MANUFACTURING"
            elif "wholesale" in v_clean or "distribution" in v_clean:
                db_vertical = "WHOLESALE"
            elif "general" in v_clean or "business" in v_clean or "generic" in v_clean:
                db_vertical = "GENERIC"
            else:
                db_vertical = user_vertical

        # Default all analyses to business efficiency (EFFICIENCY motivation)
        motivation_val = payload.motivation or "EFFICIENCY"
        
        # Default project mode initially to OPTIMIZER
        mode_val = (payload.mode or SessionMode.OPTIMIZER).value

        # Persona defaults to "SMB Operator"
        persona_val = payload.user_persona or "SMB Operator"

        project_id = await postgres_client.create_project(
            user_id=current_user.id,
            title=title,
            description=prompt_text,
            mode=mode_val,
            motivation=motivation_val,
            user_persona=persona_val,
            company_id=company_id
        )
        project = await postgres_client.get_project(project_id)

    assert project is not None

    # Load session state mapping from database or initialize
    state = await postgres_client.get_session_state(project_id)
    if not state:
        max_budget = 1.25
        max_steps = 15

        # Fetch company info for injection
        company_name = None
        company_industry = None
        company_tools = None
        p_company_id = project.get("company_id")
        if p_company_id:
            company = await postgres_client.get_company(str(p_company_id))
            if company:
                company_name = company["name"]
                company_industry = company["industry_vertical"] or company["industry"]
                company_tools = company["core_tools"]

        state = SessionState(
            session_id=project_id,
            mode=SessionMode(project["mode"]),
            status=SessionStatus.ROUTING,
            budget_spent_usd=0.0,
            max_budget_usd=max_budget,
            steps_taken=0,
            max_steps=max_steps,
            messages=[
                Message(role="user", content=prompt_text, name=None, tool_call_id=None)
            ] if prompt_text else [],
            clarification_questions=[],
            clarification_responses={},
            dag_plan=[],
            metadata={
                "motivation": project["motivation"],
                "user_persona": project["user_persona"],
                "industry_vertical": company_industry or payload.industry_vertical or "GENERIC",
                "company_name": company_name,
                "company_industry": company_industry,
                "company_core_tools": company_tools
            },
            file_name=payload.file_name,
            file_content=payload.file_content,
            business_vertical=db_vertical,
            evidence_ledger=[],
            company_name=company_name,
            company_industry=company_industry,
            company_core_tools=company_tools,
            user_constraints=payload.user_constraints or [],
            lang=payload.lang or "en"
        )
        await postgres_client.save_session_state(state)
        await postgres_client.save_chat_messages(project_id, state.messages)
    else:
        if payload.user_constraints is not None:
            state.user_constraints = payload.user_constraints
        if payload.lang is not None:
            state.lang = payload.lang
        if payload.prompt:
            state.messages.append(Message(role="user", content=payload.prompt, name=None, tool_call_id=None))

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

    # Set CDN Caching headers to prevent cross-language responses cache pollution
    response.headers["Vary"] = "Accept-Language"
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    
    return updated_state


@app.get("/api/v1/session/{session_id}")
async def get_session(
    session_id: str,
    response: Response,
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
        max_budget = 1.25
        max_steps = 15

        # Fetch company info for injection
        company_name = None
        company_industry = None
        company_tools = None
        p_company_id = project.get("company_id")
        if p_company_id:
            company = await postgres_client.get_company(str(p_company_id))
            if company:
                company_name = company["name"]
                company_industry = company["industry_vertical"] or company["industry"]
                company_tools = company["core_tools"]

        # Build custom greeting mentioning company name
        display_company = company_name or "your company"
        greeting = (
            f"Hello! I am BuildSense, your AI operations analyst. Let's work together "
            f"to map and optimize your workflows at **{display_company}**. To get started, "
            f"could you describe a typical process or task that you perform manually, "
            f"or share a challenge you'd like to automate?"
        )

        state = SessionState(
            session_id=session_id,
            mode=SessionMode(project["mode"]),
            status=SessionStatus.AWAITING_CLARIFICATION,
            budget_spent_usd=0.0,
            max_budget_usd=max_budget,
            steps_taken=0,
            max_steps=max_steps,
            messages=[
                Message(role="assistant", content=greeting, name="BuildSense Intelligence", tool_call_id=None)
            ],
            clarification_questions=[greeting],
            clarification_responses={},
            dag_plan=[],
            metadata={
                "motivation": project["motivation"],
                "user_persona": project["user_persona"],
                "industry_vertical": company_industry or "GENERIC",
                "company_name": company_name,
                "company_industry": company_industry,
                "company_core_tools": company_tools
            },
            file_name=None,
            file_content=None,
            business_vertical="GENERIC",
            evidence_ledger=[],
            company_name=company_name,
            company_industry=company_industry,
            company_core_tools=company_tools,
            user_constraints=[],
            lang="en"
        )
        await postgres_client.save_session_state(state)
        await postgres_client.save_chat_messages(session_id, state.messages)
    
    # Set CDN Caching headers to prevent cross-language responses cache pollution
    response.headers["Vary"] = "Accept-Language"
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    
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
