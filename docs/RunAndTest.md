# Run & Test Guide

This document explains how to bring the BuildSense app up and down, and how to run unit tests and evaluations.

**Prerequisites**
- Python 3.11+ installed and on PATH
- Node.js 18+ and npm
- Git
- Recommended: PowerShell (Windows) or a Unix-like shell

**Repository layout (relevant folders)**
- `apps/api` — backend (FastAPI)
- `apps/web` — frontend (Next.js)

**1) Backend — setup & bring up**

1. Create and activate a Python virtual environment (PowerShell):

```powershell
cd apps/api
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

(On cmd.exe)

```cmd
cd apps/api
python -m venv .venv
.\.venv\Scripts\activate.bat
```

2. Install Python dependencies:

```powershell
pip install -r requirements.txt
# or, if using pyproject-based tooling
pip install -e .
```

3. Start the backend (development mode):

```powershell
cd apps/api
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The backend will be available at http://localhost:8000 by default.

**2) Frontend — setup & bring up**

1. Install Node dependencies and start dev server:

```bash
cd apps/web
npm install
npm run dev -- --hostname 0.0.0.0 --port 3000
```

2. Open the app in your browser at http://localhost:3000.

Notes:
- If port 3000 or 8000 is already in use, change the `--port` values.
- Some Windows environments restrict binding on 0.0.0.0 — remove `--hostname` or use `localhost` if needed.

**3) Bring the app down (stop servers)**

- In the terminal windows running the servers, press `Ctrl+C` to stop.
- On Windows, to kill a process by port (if needed):

```powershell
# find PID by port (PowerShell)
netstat -ano | Select-String ":3000"
# kill PID
Stop-Process -Id <PID>
```

or use `taskkill` in cmd.exe:

```cmd
taskkill /PID <PID> /F
```

**4) Run unit tests (backend)**

From `apps/api` (recommended inside the activated virtualenv):

```bash
cd apps/api
pytest tests/ -v
```

Run a single test file:

```bash
pytest tests/test_orchestrator.py -q
```

**5) Run evaluations**

The evals suite lives in `apps/api/evals`.

```bash
cd apps/api
pytest evals/ -v --run-evals
```

**6) Useful quick commands**

Start backend in background (PowerShell):

```powershell
Start-Process -NoNewWindow -FilePath python -ArgumentList "-m","uvicorn","app.main:app","--reload","--host","0.0.0.0","--port","8000"
```

Install both backend and frontend deps from repository root:

```bash
# backend
cd apps/api && python -m venv .venv && .\.venv\Scripts\Activate.ps1 && pip install -r requirements.txt
# frontend
cd apps/web && npm install
```

**7) Environment & config**

- Check `apps/api/core/config.py` or `.env` examples (if present) for environment variables the backend expects. If a `.env.example` exists at repo root, copy it to `.env` and update values.

**8) Troubleshooting tips**
- If `npm run dev` exits with code 1, check the terminal output for missing env vars or port collisions.
- If tests fail, re-run a single failing test with `-q` to get focused output.
- Use the project's `pytest` fixtures for DB and Redis tests (see `apps/api/tests/conftest.py`).

---

If you want, I can:
- Add Windows-specific troubleshooting details.
- Commit the file to git and open a PR.
