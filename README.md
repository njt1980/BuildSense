# BuildSense

BuildSense is an agentic workflow optimization platform for small and midsize businesses. It helps a user describe a messy operational workflow, clarifies missing context, runs structured analysis, and produces practical plain-English recommendations for improving the process.

The current product implementation is centered on `OPTIMIZER` mode: workflow intake, human-in-the-loop clarification, tool-assisted analysis, and a two-level report experience with Quick Insights and Deep Dive views.

## What It Does

- Captures company context, projects, chat history, workflow state, and graph data.
- Guides users through progressive workflow intake instead of forcing rigid forms.
- Pauses for clarification when critical details are missing.
- Uses local MCP-style tools for market signals, calculations, document parsing, and geographic enrichment.
- Wraps untrusted tool output before it enters orchestration context.
- Tracks budgets, steps, request IDs, local telemetry, and development evaluation metadata.
- Provides a local telemetry dashboard for request, node, LLM, tool, cost, and error inspection.

## Architecture

```text
apps/web  -> Next.js 14, TypeScript, Tailwind CSS
apps/api  -> FastAPI, Pydantic v2, LangGraph orchestration
docs      -> Product, runbook, telemetry, and defect documentation
scripts   -> Development and repository utility scripts
```

Backend API surface includes company, project, transcription, orchestration, session, graph, and development telemetry routes. The frontend consumes the backend through `NEXT_PUBLIC_API_BASE_URL`, which defaults locally to `http://localhost:8001`.

## Local Quick Start

Prerequisites:

- Python 3.11+
- Node.js 18+
- npm
- Git

Create local environment files:

```powershell
Copy-Item .env.example .env
```

Set secrets and service URLs in `.env` as needed. The backend can fall back to in-memory stores for local development when Postgres or Redis are unavailable.

Install and run the backend:

```powershell
cd apps/api
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --host 127.0.0.1 --port 8001
```

Install and run the frontend:

```powershell
cd apps/web
npm install
npm run dev -- --hostname 127.0.0.1 --port 3000
```

Open:

```text
Frontend: http://127.0.0.1:3000
Backend health: http://127.0.0.1:8001/health
Telemetry dashboard: http://127.0.0.1:3000/en/dev/telemetry
```

If the backend runs on another port, set:

```text
apps/web/.env.local
NEXT_PUBLIC_API_BASE_URL=http://localhost:<backend-port>
```

## Validation

Backend checks from `apps/api`:

```powershell
pytest tests/ -v
pytest tests/test_mcp_tools.py -v
pytest evals/ -v --run-evals
mypy app/
```

Frontend checks from `apps/web`:

```powershell
npm run type-check
npm run lint
```

## Local Telemetry

The local telemetry system records privacy-safe, bounded in-memory events for development and local evals. It captures request lifecycle, orchestration runs, LangGraph node execution, LLM calls, tool calls, duration, token counts, estimated costs, and sanitized errors.

Development routes are available under:

```text
/api/dev/telemetry/events
/api/dev/telemetry/runs
/api/dev/telemetry/runs/{run_id}
/api/dev/telemetry/requests/{request_id}
/api/dev/telemetry/sessions/{session_id}
```

Telemetry is intended for local debugging, not production persistence.

## Guardrails

- Keep untrusted external tool output wrapped in `<untrusted_tool_output>` tags.
- Do not store raw secrets, BYOK keys, full prompts, full LLM responses, or raw uploaded files in telemetry.
- Keep session memory scoped by `session_id`.
- Preserve the active Optimizer-only implementation unless a documented product decision reintroduces additional modes.
- Update `docs/DEFECT_LEDGER.md` when defects, behavior changes, or architectural shifts are discovered.

## Useful Docs

- `docs/PRD.md` - product requirements and current gaps
- `docs/RunAndTest.md` - detailed local run and validation guide
- `docs/telemetry/SPEC.md` - telemetry requirements
- `docs/telemetry/DESIGN.md` - telemetry architecture
- `docs/DEFECT_LEDGER.md` - defect and change history
- `AGENTS.MD` - repository operating rules for future agents
