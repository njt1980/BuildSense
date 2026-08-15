# AGENTS.MD

> **Role & Operating Mode**: You are an autonomous software engineering agent working within **Google Antigravity**. 
> You are responsible for building, testing, and maintaining **BuildSense** (an Agentic Ideation & Workflow Optimizer platform). 
> Follow the guidelines, operational constraints, and verification protocols below to ensure high-precision code execution and zero regressions.

---

## 1. <MANDATORY_WORKFLOW> (Plan-First, Code-Second)
You must strictly follow a sequential workflow: Spec → Design → Code. You are explicitly forbidden from writing, generating, or modifying executable source code until the specification and design phases are fully documented and committed to version control.

Execute these phases in exact order:

### PHASE 1: SPECIFICATION
1. Draft or update `spec.md` detailing the precise requirements, scope, and acceptance criteria.
2. Pause and wait for user approval.
3. Once approved, execute: `git add spec.md` followed by `git commit -m "docs: finalize specification"`
*STOP: Do not proceed to Phase 2 until this commit is successfully executed.*

### PHASE 2: SYSTEM DESIGN
1. Draft or update `design.md` outlining the architecture, data flow, and file structures required to satisfy `spec.md`.
2. Pause and wait for user approval.
3. Once approved, execute: `git add design.md` followed by `git commit -m "docs: finalize system design"`
*STOP: Do not proceed to Phase 3 until this commit is successfully executed.*

### PHASE 3: IMPLEMENTATION (CODE)
1. You are now authorized to write and modify source code. 
2. **Pre-flight requirement:** Before executing any file creation or modification command, you must output a `<directive_check>` XML block containing exactly one sentence confirming how the code you are about to write aligns with `design.md`.
3. Generate the code, run necessary tests, and commit the final working code logically.
</MANDATORY_WORKFLOW>

---

## 2. Google Antigravity Artifact Guidelines

When executing tasks in this repository, you must generate verifiable artifacts to prove correctness before marking any sub-task complete:

1. **Task List Artifacts**: Generate a detailed Task List artifact in the Antigravity Manager view before initiating multi-file edits or structural refactors.
2. **Code Diff Artifacts**: Present clean, isolated Code Diffs for review before committing backend logic or database schema changes.
3. **Test Results Artifacts**: For every new FastMCP tool or orchestrator update, run `pytest` locally and output a Test Results artifact verifying JSON schema parsing and error handling.
4. **Browser Screenshot Artifacts**: When building or updating Next.js UI components, use Antigravity's integrated headless browser to capture Screenshot artifacts verifying visual layout (e.g., the Dual-View toggle and Human-in-the-Loop clarification modal).
5. **Eval Report Artifacts**: When modifying the Supervisor prompt, the Orchestrator engine, or the Synthesis logic, you must run the LLM-as-a-judge eval suite and output the scoring report to prove output quality has not regressed.

---

## 3. Project Overview & Context

- **Domain**: BuildSense is an agentic business intelligence platform focused on SMB Workflow Optimization.
- **Core Architecture**:
  - **Frontend**: Next.js 14 (App Router), TypeScript, Tailwind CSS, Shadcn UI.
  - **Backend**: FastAPI (Python 3.11+), Uvicorn, Pydantic v2.
  - **Orchestration**: Native Python `while` loop (Anthropic Tool Use API) — *No LangGraph or external agent frameworks*.
  - **Tool Layer**: Model Context Protocol (`mcp-python-sdk`) connecting off-the-shelf and custom FastMCP tools.
  - **Database / Infra**: PostgreSQL with `pgvector` (Cloud hosted via Neon/Supabase), Redis (Cloud hosted via Upstash), AWS ECS (Fargate).
  - **Local development note**: Port `8000` may be restricted on some Windows laptops; if so, configure the backend to run on another available port and update the frontend API URL accordingly.

---

## 4. Repository Structure

```text
.
├── apps/
│   ├── web/                         # Next.js 14 Frontend Application
│   │   ├── src/app/                 # App Router pages & SSE streams
│   │   ├── src/components/          # Shadcn UI (Dual-View, Clarification Modal)
│   │   └── src/lib/                 # SSE client & LocalStorage session helpers
│   └── api/                         # FastAPI Backend Engine
│       ├── app/
│       │   ├── core/                # Orchestrator while loop & OTEL middleware
│       │   ├── mcp/                 # MCP Client Hub & Custom FastMCP Server
│       │   ├── models/              # Pydantic state schemas (SessionState)
│       │   ├── db/                  # Postgres + pgvector dual-namespace client
│       │   └── middleware/          # Slowapi rate-limiting & Redis budget caps
│       ├── tests/                   # Deterministic Pytest suite (MCP tools)
│       └── evals/                   # LLM-as-a-judge evaluation scripts & datasets
├── .env.example
└── AGENTS.MD                        # Agent instructions (this file)
```

---

## 5. Operational Constraints & Security Guardrails

<CRITICAL_DIRECTIVES>
**Prompt Injection Isolation**: ALL unstructured text returned by external MCP servers (Web Search, GitHub READMEs) MUST be wrapped in XML tags before appending to the conversation history:
```xml
<untrusted_tool_output source="web_search_mcp">
  [RAW SEARCH CONTENT HERE]
</untrusted_tool_output>
```

**Context Pruning**: Never keep massive raw HTML/JSON tool outputs in `SessionState.messages` across iterations. Once an execution step completes, summarize key findings using a lightweight pass and drop the raw payload to keep token consumption flat.

**Optimizer-Only Budget**:
- `SessionMode.OPTIMIZER`: `max_budget_usd = $1.25` | `max_steps = 15`
- Do not reintroduce `SUGGESTER` or `EVALUATOR` modes in prompts, eval fixtures, schema comments, frontend copy, or agent instructions unless a documented product decision and defect/change-ledger entry explicitly approves that architecture change.

**Abuse Protection (No-Auth Environment)**:
- Enforce IP rate-limiting via `slowapi` (Max 3 full runs per IP per 24 hours).
- Enforce a global Redis kill-switch (`MAX_GLOBAL_DAILY_SPEND = $10.00`). Reject new runs with HTTP 503 if cap is reached.

**Dual Vector Namespaces**:
- `global_knowledge`: Shared, read-only benchmark data.
- `session_memory`: Session-isolated vector storage. All RAG queries on `session_memory` MUST mandate `WHERE session_id = :current_session_id`.

**Plain-English Rule**: System prompts for synthesis MUST enforce zero-jargon rules. Any industry term (CAC, LTV, Moat, 90/10 MVP) must include an immediate everyday analogy.

**Defect Tracking**: If a bug is discovered, or if a test fails during the Secure Checkpoint phase, you must fix the issue and immediately invoke the `.antigravity/skills/log-defect.md` skill before attempting to commit again.

**Change Management Ledger**: All future agents modifying this codebase MUST track approach shifts, persona adjustments, and bug fixes in `docs/DEFECT_LEDGER.md` without fail before marking a task as complete. Do not alter core orchestrator state routing or system prompts without logging the architectural reasoning.
</CRITICAL_DIRECTIVES>

---

## 6. Engineering Patterns & Code Standards

### Python / FastAPI / Pydantic
- Write explicit type hints on all function signatures (`mypy` strict mode).
- State must strictly conform to the `SessionState` Pydantic v2 schema.
- Structure custom MCP servers using the `FastMCP` decorator pattern:

```python
from fastmcp import FastMCP

mcp = FastMCP("CustomMetricsServer")

@mcp.tool()
def calculate_financial_metrics(users: int, avg_revenue_per_user: float) -> dict:
    """Calculates deterministic unit economics and ROI."""
    return {"projected_mrr": users * avg_revenue_per_user}
```

### TypeScript / Next.js
- Use strict TypeScript typing; avoid `any`.
- Consume real-time "Agent Thoughts" via Server-Sent Events (SSE) from `POST /api/v1/orchestrate`.
- UI must feature the **Dual-View Toggle**:
  - `⚡ Quick Insights` (Default 2-minute read, bullet points, traffic-light status badges).
  - `🔬 Deep Dive` (Full 4-pillar dossier).

### Code Documentation & Comments
- **Python (Backend)**: Every function, class, and method MUST have a complete PEP 257 compliant docstring explaining its purpose, arguments, and return types. Complex logic within the orchestrator while loop must have inline comments explaining why a state transition or guardrail is happening.
- **TypeScript (Frontend)**: Use JSDoc comments (`/** ... */`) for all React components, custom hooks, and shared interfaces.
- **File-Level Context**: Every new source file MUST start with a concise module/file docstring or header comment explaining what the file owns, where it fits in the architecture, and what it deliberately does not own.
- **Public Contracts**: Public APIs, FastAPI routes, MCP tools, telemetry wrappers, orchestration nodes, eval fixtures, React page components, shared hooks, and exported helpers MUST document inputs, outputs, side effects, error behavior, and privacy/security assumptions where relevant.
- **Architectural Reasoning**: Any change to prompts, while-loop state routing, budget controls, telemetry, eval harnesses, or persistence boundaries MUST include a short code comment or nearby documentation note explaining the reason for the design, not just what the code does.
- **Documentation Drift Check**: When code behavior changes, update all matching human/agent-facing docs in the same change (`AGENTS.MD`, `docs/DEFECT_LEDGER.md`, `docs/PRD.md`, `docs/RunAndTest.md`, feature specs, eval docs, or inline docstrings as applicable). Do not leave stale examples, retired modes, old ports, or outdated prompt behavior in docs or tests.
- **Self-Documenting Code**: Prioritize descriptive variable names (e.g., use `has_exceeded_token_budget` instead of `limit_hit`).

---

## 7. Testing & Validation Commands

Always run these validation commands in your Antigravity terminal session before marking a task resolved:

### Backend Engine (`apps/api`)
- **Run Unit & Integration Tests**: `pytest tests/ -v`
- **Run Agentic Evals**: `pytest evals/ -v --run-evals`
- **Type Checking**: `mypy app/`
- **FastMCP Tool Verification**: `pytest tests/test_mcp_tools.py -v`
- **Integration Testing**: include frontend/backend wiring checks for key flows such as onboarding, project creation, and orchestration endpoint connectivity.

### Frontend UI (`apps/web`)
- **Type Checking**: `npm run type-check`
- **Linting**: `npm run lint`
- **Runtime Integration**: validate `NEXT_PUBLIC_API_BASE_URL` and local backend connectivity before declaring the UI ready.

---

## 8. Definition of Done Checklist

Before presenting a task as complete in Antigravity:
- [ ] Phase 1 (Spec) and Phase 2 (Design) have been documented and committed via `git`.
- [ ] A `<directive_check>` block was output before any code modifications were made.
- [ ] Code compiles with zero TypeScript errors and passes `mypy app/`.
- [ ] All new FastMCP tools are covered by passing `pytest` unit tests.
- [ ] Untrusted tool outputs are properly wrapped in `<untrusted_tool_output>` XML boundaries.
- [ ] Context pruning hook operates correctly on step completion.
- [ ] If orchestrator or prompt logic was altered, the `evals/` suite passes with >90% on the Zero-Jargon and Hallucination metrics.
- [ ] Runtime frontend/backend integration flows are validated, especially onboarding and API endpoint connectivity.
- [ ] UI rendered in Antigravity browser confirms the Dual-View toggle works seamlessly.
- [ ] No hardcoded secrets, API keys, or unhandled debug logs (`print()`, `console.log()`) remain.
- [ ] All changes have been committed to git with a descriptive conventional commit message.
- [ ] All work has been committed using the `.antigravity/skills/secure-checkpoint.md` skill.