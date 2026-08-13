# Defect & Resolution Ledger

## [BUG-001] - Date: 2026-08-09
* **Issue:** FastAPI backend startup failed with `ValueError: REDIS_URL environment variable is not defined.`
* **Root Cause:** `redis.py` and `postgres.py` queried `os.environ` directly for `REDIS_URL` and `DATABASE_URL`, but these variables are only parsed into the `settings` object via Pydantic and not loaded into the system environment by default.
* **Resolution:** Modified `redis.py` and `postgres.py` to dynamically fall back to `settings.redis_url` and `settings.database_url` from `app.core.config`.
* **Files Touched:** [redis.py](file:///c:/Users/nimel.thomas/Desktop/BuildSense/apps/api/app/db/redis.py), [postgres.py](file:///c:/Users/nimel.thomas/Desktop/BuildSense/apps/api/app/db/postgres.py)

## [BUG-002] - Date: 2026-08-12
* **Issue:** Onboarding baseline creation failed in the browser with `Failed to establish business baseline.` despite the backend running locally.
* **Root Cause:** Frontend fetch calls were hard-coded to `http://localhost:9000`, while the local backend was running on `http://localhost:8001` due to port restrictions. This was a frontend/backend integration configuration issue.
* **Resolution:** Added a shared `NEXT_PUBLIC_API_BASE_URL` environment variable, updated frontend API calls to use it, and added `.env.example` documentation for local backend host/port configuration.
* **Files Touched:** [apps/web/src/components/company-provider.tsx](file:///c:/Users/nimel.thomas/Desktop/BuildSense/apps/web/src/components/company-provider.tsx), [apps/web/src/app/[lang]/page.tsx](file:///c:/Users/nimel.thomas/Desktop/BuildSense/apps/web/src/app/[lang]/page.tsx), [apps/web/src/app/[lang]/projects/[id]/page.tsx](file:///c:/Users/nimel.thomas/Desktop/BuildSense/apps/web/src/app/[lang]/projects/[id]/page.tsx), [apps/web/src/lib/useOrchestratorStream.ts](file:///c:/Users/nimel.thomas/Desktop/BuildSense/apps/web/src/lib/useOrchestratorStream.ts), [.env.example](file:///c:/Users/nimel.thomas/Desktop/BuildSense/.env.example)

## [BUG-003] - Date: 2026-08-13
* **Issue:** Defect-tracking directive in `AGENTS.MD` (`Defect Tracking` → invoke `.antigravity/skills/log-defect.md`) is not consistently followed; ledger updates are missing after recent work and replications.
* **Root Cause:** No automated enforcement (pre-commit hook or CI check) requiring `docs/DEFECT_LEDGER.md` updates, and contributors/agents may have skipped the Secure Checkpoint step that mandates invoking the log-defect skill.
* **Impact:** Missing historical defect records reduce traceability and make postmortems harder.
* **Proposed Resolution:** Add a lightweight enforcement layer: (1) a Git pre-commit hook that runs tests and prompts/blocks commits when tests fail and `docs/DEFECT_LEDGER.md` hasn't been updated; (2) a CI job that fails if tests fail and the ledger wasn't amended; (3) update PR templates and contributor docs to require ledger updates for bugs/enhancements.
* **Files/Places Touched:** `.git/hooks/pre-commit` (proposal), `.github/workflows/ci.yml` (proposal), [AGENTS.MD](AGENTS.MD)

## [BUG-004] - Date: 2026-08-13
* **Issue:** Test run surfaces DeprecationWarnings in `apps/api/app/main.py` about using `@app.on_event("startup"/"shutdown")` which is deprecated in FastAPI; recommended migration to lifespan handlers.
* **Root Cause:** `app/main.py` uses the older `on_event` decorators for startup/shutdown lifecycle management.
* **Impact:** Future FastAPI upgrades may remove `on_event` support causing runtime errors; also noisy test output.
* **Resolution:** Replace `@app.on_event("startup")` and `@app.on_event("shutdown")` with an async lifespan context manager using `asynccontextmanager` or FastAPI's `lifespan` parameter; add a small test ensuring the app starts/stops without the deprecated hooks.
* **Files Touched:** [apps/api/app/main.py](apps/api/app/main.py)
