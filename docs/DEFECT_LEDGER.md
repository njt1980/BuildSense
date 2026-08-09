# Defect & Resolution Ledger

## [BUG-001] - Date: 2026-08-09
* **Issue:** FastAPI backend startup failed with `ValueError: REDIS_URL environment variable is not defined.`
* **Root Cause:** `redis.py` and `postgres.py` queried `os.environ` directly for `REDIS_URL` and `DATABASE_URL`, but these variables are only parsed into the `settings` object via Pydantic and not loaded into the system environment by default.
* **Resolution:** Modified `redis.py` and `postgres.py` to dynamically fall back to `settings.redis_url` and `settings.database_url` from `app.core.config`.
* **Files Touched:** [redis.py](file:///c:/Users/nimel.thomas/Desktop/BuildSense/apps/api/app/db/redis.py), [postgres.py](file:///c:/Users/nimel.thomas/Desktop/BuildSense/apps/api/app/db/postgres.py)
