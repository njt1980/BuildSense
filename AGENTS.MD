# AGENTS.MD

> **Role & Operating Mode**: You are an autonomous software engineering agent working within **Google Antigravity**. 
> You are responsible for building, testing, and maintaining **BuildSense** (an Agentic Ideation & Workflow Optimizer platform). 
> Follow the guidelines, operational constraints, and verification protocols below to ensure high-precision code execution and zero regressions.

---

## 1. Google Antigravity Artifact Guidelines

When executing tasks in this repository, you must generate verifiable artifacts to prove correctness before marking any sub-task complete:

1. **Task List Artifacts**: Generate a detailed Task List artifact in the Antigravity Manager view before initiating multi-file edits or structural refactors.
2. **Code Diff Artifacts**: Present clean, isolated Code Diffs for review before committing backend logic or database schema changes.
3. **Test Results Artifacts**: For every new FastMCP tool or orchestrator update, run `pytest` locally and output a Test Results artifact verifying JSON schema parsing and error handling.
4. **Browser Screenshot Artifacts**: When building or updating Next.js UI components, use Antigravity's integrated headless browser to capture Screenshot artifacts verifying visual layout (e.g., the Dual-View toggle and Human-in-the-Loop clarification modal).
5. **Eval Report Artifacts**: When modifying the Supervisor prompt, the Orchestrator engine, or the Synthesis logic, you must run the LLM-as-a-judge eval suite and output the scoring report to prove output quality has not regressed.

---

## 2. Project Overview & Context

- **Domain**: BuildSense is an agentic business intelligence platform offering Idea Suggestion, Idea Evaluation, and SMB Workflow Optimization.
- **Core Architecture**:
  - **Frontend**: Next.js 14 (App Router), TypeScript, Tailwind CSS, Shadcn UI.
  - **Backend**: FastAPI (Python 3.11+), Uvicorn, Pydantic v2.
  - **Orchestration**: Native Python `while` loop (Anthropic Tool Use API) — *No LangGraph or external agent frameworks*.
  - **Tool Layer**: Model Context Protocol (`mcp-python-sdk`) connecting off-the-shelf and custom FastMCP tools.
  - **Database / Infra**: PostgreSQL with `pgvector` (Cloud hosted via Neon/Supabase), Redis (Cloud hosted via Upstash), AWS ECS (Fargate).

---

## 3. Repository Structure

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

## 4. Operational Constraints & Security Guardrails

### 🚫 Non-Negotiable Rules

**Prompt Injection Isolation**: ALL unstructured text returned by external MCP servers (Web Search, GitHub READMEs) MUST be wrapped in XML tags before appending to the conversation history:

```xml
<untrusted_tool_output source="web_search_mcp">
  [RAW SEARCH CONTENT HERE]
</untrusted_tool_output>
```

**Context Pruning**: Never keep massive raw HTML/JSON tool outputs in `SessionState.messages` across iterations. Once an execution step completes, summarize key findings using a lightweight pass and drop the raw payload to keep token consumption flat.

**Strict Tiered Budgets**:
- `SessionMode.SUGGESTER`: `max_budget_usd = $0.15` | `max_steps = 6`
- `SessionMode.EVALUATOR` & `OPTIMIZER`: `max_budget_usd = $1.25` | `max_steps = 15`

**Abuse Protection (No-Auth Environment)**:
- Enforce IP rate-limiting via `slowapi` (Max 3 full runs per IP per 24 hours).
- Enforce a global Redis kill-switch (`MAX_GLOBAL_DAILY_SPEND = $10.00`). Reject new runs with HTTP 503 if cap is reached.

**Dual Vector Namespaces**:
- `global_knowledge`: Shared, read-only benchmark data.
- `session_memory`: Session-isolated vector storage. All RAG queries on `session_memory` MUST mandate `WHERE session_id = :current_session_id`.

**Plain-English Rule**: System prompts for synthesis MUST enforce zero-jargon rules. Any industry term (CAC, LTV, Moat, 90/10 MVP) must include an immediate everyday analogy.

**Defect Tracking**: If a bug is discovered, or if a test fails during the Secure Checkpoint phase, you must fix the issue and immediately invoke the '.antigravity/skills/log-defect.md' skill before attempting to commit again.

---

## 5. Engineering Patterns & Code Standards

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
- **Self-Documenting Code**: Prioritize descriptive variable names (e.g., use `has_exceeded_token_budget` instead of `limit_hit`).

---

## 6. Testing & Validation Commands

Always run these validation commands in your Antigravity terminal session before marking a task resolved:

### Backend Engine (`apps/api`)
- **Run Unit & Integration Tests**: `pytest tests/ -v`
- **Run Agentic Evals**: `pytest evals/ -v --run-evals`
- **Type Checking**: `mypy app/`
- **FastMCP Tool Verification**: `pytest tests/test_mcp_tools.py -v`

### Frontend UI (`apps/web`)
- **Type Checking**: `npm run type-check`
- **Linting**: `npm run lint`

---

## 7. Definition of Done Checklist

Before presenting a task as complete in Antigravity:
- [ ] Code compiles with zero TypeScript errors and passes `mypy app/`.
- [ ] All new FastMCP tools are covered by passing `pytest` unit tests.
- [ ] Untrusted tool outputs are properly wrapped in `<untrusted_tool_output>` XML boundaries.
- [ ] Context pruning hook operates correctly on step completion.
- [ ] If orchestrator or prompt logic was altered, the `evals/` suite passes with >90% on the Zero-Jargon and Hallucination metrics.
- [ ] UI rendered in Antigravity browser confirms the Dual-View toggle works seamlessly.
- [ ] No hardcoded secrets, API keys, or unhandled debug logs (`print()`, `console.log()`) remain.
- [ ] All changes have been committed to git with a descriptive conventional commit message.
- [ ] All work has been committed using the '.antigravity/skills/secure-checkpoint.md' skill.