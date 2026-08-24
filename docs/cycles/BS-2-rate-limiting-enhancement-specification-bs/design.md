# Rate Limiting Enhancement Design (BS-RATE-LIMIT)

## Atomic Implementation Steps

### Step 1: Update Application Code (`apps/api/app/main.py`)
- **Files to read**: `apps/api/app/main.py`, `apps/api/app/db/redis.py`
- **Files to modify**: `apps/api/app/main.py`
- **Action**:
  1. Remove the `@limiter.limit("5/day")` decorator from `/api/v1/orchestrate` so it doesn't penalize in-session resume requests.
  2. Within the `/api/v1/orchestrate` route logic, if a request does *not* contain a `session_id` (meaning it's implicitly creating a new session) and does *not* contain a BYOK (`x-user-anthropic-key`), manually enforce the 3/day IP limit by calling `await redis_client.check_ip_rate_limit(client_ip, max_allowed_runs=3)`.
  3. Raise a `RateLimitExceeded` (or HTTP 429) if the Redis check fails.
  4. (Optional) Apply `@limiter.limit("3/day")` to the standalone POST `/api/v1/projects` creation endpoint for parity.

### Step 2: Update Documentation & Rules (`AGENTS.MD`, `docs/DEFECT_LEDGER.md`)
- **Files to read**: `AGENTS.MD`
- **Files to modify**: `AGENTS.MD`, `docs/DEFECT_LEDGER.md`
- **Action**:
  1. Update `AGENTS.MD` to clarify that the IP limit is strictly for "Max 3 *new sessions* per IP per 24 hours" and that it exempts BYOK users.
  2. Document the shift from `slowapi` turn-based limiting to Redis session-based limiting in `docs/DEFECT_LEDGER.md`.
