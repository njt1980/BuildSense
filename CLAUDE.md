<!-- GENERATED FILE: do not edit directly. Source of truth is AGENTS.md.
     Regenerate with: python scripts/sync_agent_rules.py --write -->

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
3. Once approved, execute: `git add spec.md` followed by `git commit --no-verify -m "docs: finalize specification"` because this is a documentation-only phase checkpoint. Then run `python scripts/archive_checkpoint.py --phase spec` to assign this cycle a `BS-<N>` ticket ID and archive `spec.md` under `docs/cycles/`. Finally, state the exact approval command the user must run — `git notes --ref=refs/notes/approvals add -m approved <spec-commit-sha>` — and wait for the user to confirm they ran it. Never run this `git notes` command yourself: it must be a human action, since `scripts/check_phase_gate.py`'s `check_approval_evidence()` check treats its presence as the only evidence a human actually reviewed the content (see BUG-037).
*STOP: Do not proceed to Phase 2 until this commit is successfully executed and the user has confirmed they added the approval note.*

### PHASE 2: SYSTEM DESIGN
1. Draft or update `design.md` outlining the architecture, data flow, and file structures required to satisfy `spec.md`. `design.md` must break the Phase 3 work into a numbered list of **Atomic Implementation Steps**; each step must explicitly list the exact file paths it will read and the exact file paths it will modify, and must be scoped narrowly enough to finish inside a single context window.
2. Pause and wait for user approval.
3. Once approved, execute: `git add design.md` followed by `git commit --no-verify -m "docs: finalize system design"` because this is a documentation-only phase checkpoint. Then run `python scripts/archive_checkpoint.py --phase design` to archive `design.md` under this cycle's existing `BS-<N>` ticket in `docs/cycles/`. Finally, state the exact approval command the user must run — `git notes --ref=refs/notes/approvals add -m approved <design-commit-sha>` — and wait for the user to confirm they ran it. Never run this `git notes` command yourself, for the same reason as the spec.md approval note in Phase 1 step 3. This design.md approval note is what `check_approval_evidence()` requires before it will accept Phase 3's first source-touching commit.
4. **Context Flush Checkpoint:** Before requesting a new chat session, verify that both `spec.md` and `design.md` exist on disk, are fully populated with the approved specification and design, and have been successfully committed to version control. Once verified, pause and instruct the user to open a new conversation/chat session in Antigravity to flush the conversational history and free context space. Do not begin Phase 3 work in the same context window that carried the Phase 1/2 discussion.
*STOP: Do not proceed to Phase 3 until this commit is successfully executed and the user has confirmed they added the approval note.*

> **Coupling note:** the exact strings `docs: finalize specification` and `docs: finalize system design` above are read literally by `scripts/check_phase_gate.py`. If either commit message prefix changes, update that script in the same commit — otherwise the phase gate will silently stop recognizing checkpoint commits.

### PHASE 3: IMPLEMENTATION (CODE)
1. **Bootstrapping in a New Chat Session:** Since you are starting in a fresh conversation session with no chat history, you **MUST** immediately read `spec.md`, `design.md`, and run `git status` / `git log -n 5` to reconstruct the context of the work. Align your understanding of the current atomic step with the committed design before modifying any files.
2. You are now authorized to write and modify source code, one Atomic Implementation Step from `design.md` at a time.
3. **Pre-flight requirement:** Before touching files for an atomic step, output a `<directive_check>` XML block that (a) confirms in one sentence how the step aligns with `design.md`, and (b) lists the exact source files you intend to read or modify for this step. **File Cap:** Never hold more than 4 source files in context at once for a single atomic step. If a step genuinely needs more than 4 files, halt and split it into smaller atomic steps in `design.md` before continuing.
4. Generate the code and run the targeted tests for that atomic step only.
5. **Micro-Commit Rule:** Immediately after an atomic step's code passes its targeted tests, commit it (`git add <changed files>` + `git commit`) before starting the next atomic step. This checkpoints progress so a token-quota crash mid-implementation loses at most one atomic step's work, not the whole phase.
</MANDATORY_WORKFLOW>

### Commit And Validation Scope
- **Documentation-only phase commits** (`spec.md`, `design.md`, README updates, runbook updates, and agent-instruction clarifications) must not trigger the full backend test suite through the Git hook. Before these commits, run `git status`, confirm no secrets or runtime files are staged, stage only the intended documentation files, and commit with `--no-verify`.
- **Executable source changes** must use the normal pre-commit/secure-checkpoint path unless the user explicitly authorizes a documented exception. Run targeted validation during development and the broader validation set before marking the implementation complete.
- **Hook behavior note:** `.githooks/pre-commit` currently runs `pytest apps/api/tests/ -q` for every commit, regardless of changed file type. Treat that as too broad for documentation-only commits; do not spend full-suite runtime on spec/design bookkeeping commits.
- If a test fails during a code checkpoint, log the defect in `docs/DEFECT_LEDGER.md` before retrying the commit.

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
  - **Orchestration**: LangGraph for stateful multi-agent routing and execution. LangSmith for tracing, evals, and observability. (Anthropic Tool Use API integrated via LangChain/LangGraph ecosystem).
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
│       │   ├── core/                # LangGraph orchestrator nodes & LangSmith middleware
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

**Change Management Ledger**: All future agents modifying this codebase MUST track approach shifts, persona adjustments, and bug fixes in `docs/DEFECT_LEDGER.md` without fail before marking a task as complete. Do not alter core LangGraph state routing or system prompts without logging the architectural reasoning.
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
- **Python (Backend)**: Every function, class, and method MUST have a complete PEP 257 compliant docstring explaining its purpose, arguments, and return types. Complex logic within LangGraph nodes and conditional edges must have inline comments explaining why a state transition or guardrail is happening.
- **TypeScript (Frontend)**: Use JSDoc comments (`/** ... */`) for all React components, custom hooks, and shared interfaces.
- **File-Level Context**: Every new source file MUST start with a concise module/file docstring or header comment explaining what the file owns, where it fits in the architecture, and what it deliberately does not own.
- **Public Contracts**: Public APIs, FastAPI routes, MCP tools, telemetry wrappers, orchestration nodes, eval fixtures, React page components, shared hooks, and exported helpers MUST document inputs, outputs, side effects, error behavior, and privacy/security assumptions where relevant.
- **Architectural Reasoning**: Any change to prompts, LangGraph state routing, budget controls, telemetry, eval harnesses, or persistence boundaries MUST include a short code comment or nearby documentation note explaining the reason for the design, not just what the code does.
- **Documentation Drift Check**: When code behavior changes, update all matching human/agent-facing docs in the same change (`AGENTS.MD`, `docs/DEFECT_LEDGER.md`, `docs/PRD.md`, `docs/RunAndTest.md`, feature specs, eval docs, or inline docstrings as applicable). Do not leave stale examples, retired modes, old ports, or outdated prompt behavior in docs or tests.
- **Self-Documenting Code**: Prioritize descriptive variable names (e.g., use `has_exceeded_token_budget` instead of `limit_hit`).

---

## 7. Testing & Validation Commands

Run validation commands according to the change scope. Running tests is not required nor recommended when simply bringing up, starting, or running the application. Documentation-only commits require a status/secret-staging check. Executable source changes require targeted checks while developing and broader checks before marking the task resolved.

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

<!-- AGENTS.md sha256: 3f2b235fd28734d418a24a098ab95a41cf01c42bbf7e59acfc582cfa9e8588e0 -->
