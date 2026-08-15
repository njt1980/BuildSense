# Run And Test Guide

This guide explains how to run BuildSense locally and execute the main validation commands.

## Prerequisites

- Python 3.11+
- Node.js 18+ and npm
- Git
- PowerShell on Windows, or a Unix-like shell on macOS/Linux

## Repository Layout

- `apps/api` - FastAPI backend
- `apps/web` - Next.js frontend
- `docs` - product and operational documentation
- `scripts` - utility scripts

## 1. Backend Setup

Create and activate a virtual environment:

```powershell
cd apps/api
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Install dependencies:

```powershell
pip install -r requirements.txt
```

Start the backend:

```powershell
uvicorn app.main:app --reload --host 0.0.0.0 --port 8001
```

The frontend code currently falls back to `http://localhost:8001`, so `8001` is the recommended local backend port. The backend settings default to `9000`; either port is fine if `NEXT_PUBLIC_API_BASE_URL` points to the same address.

## 2. Frontend Setup

Install dependencies:

```powershell
cd apps/web
npm install
```

Start the frontend:

```powershell
npm run dev -- --hostname 0.0.0.0 --port 3000
```

Open `http://localhost:3000`.

If the backend is not running on `8001`, create `apps/web/.env.local` and set:

```text
NEXT_PUBLIC_API_BASE_URL=http://localhost:<backend-port>
```

## 3. Stop Servers

Press `Ctrl+C` in the terminal running each server.

To find and stop a process by port on Windows:

```powershell
netstat -ano | Select-String ":3000"
Stop-Process -Id <PID>
```

## 4. Backend Tests

Run the backend test suite from `apps/api`:

```powershell
pytest tests/ -v
```

Run a focused test file:

```powershell
pytest tests/test_orchestrator.py -q
```

Run FastMCP/tool verification:

```powershell
pytest tests/test_mcp_tools.py -v
```

Run type checking:

```powershell
mypy app/
```

## 5. Agentic Evals

Run the eval suite from `apps/api`:

```powershell
pytest evals/ -v --run-evals
```

Run the E2E eval tests:

```powershell
pytest tests/evals -v
```

## 6. Frontend Checks

Run these commands from `apps/web`:

```powershell
npm run type-check
npm run lint
```

## 7. Environment Configuration

Copy the root `.env.example` to `.env` and update local values as needed.

Important settings:

- `DATABASE_URL` - PostgreSQL connection string.
- `REDIS_URL` - Redis connection string.
- `ANTHROPIC_API_KEY` - Optional for live LLM-backed orchestration.
- `MAX_GLOBAL_DAILY_SPEND` - Global budget kill switch.
- `NEXT_PUBLIC_API_BASE_URL` - Frontend API base URL.

The backend can fall back to in-memory stores when Postgres or Redis are unreachable. This is useful for local development, but integration testing should use real backing services.

## 8. Troubleshooting

- If `npm run dev` fails, check for missing environment variables or port collisions.
- If the frontend cannot create companies or projects, verify `NEXT_PUBLIC_API_BASE_URL` matches the backend port.
- If backend startup reports Redis or Postgres warnings, confirm whether you intended to run with real services or local fallback mode.
- If Windows blocks `0.0.0.0`, use `localhost`.
- If tests fail, rerun the specific failing file with `-q` for focused output.
