# Defect And Resolution Ledger

This ledger records defects discovered during development, their root causes, and their resolution status.

## BUG-001 - 2026-08-09

**Issue:** FastAPI backend startup failed with `ValueError: REDIS_URL environment variable is not defined.`

**Root Cause:** `redis.py` and `postgres.py` queried `os.environ` directly for `REDIS_URL` and `DATABASE_URL`, but these variables were only parsed into the Pydantic `settings` object.

**Resolution:** Updated `redis.py` and `postgres.py` to fall back to `settings.redis_url` and `settings.database_url`.

**Files Touched:** `apps/api/app/db/redis.py`, `apps/api/app/db/postgres.py`

## BUG-002 - 2026-08-12

**Issue:** Onboarding baseline creation failed in the browser with `Failed to establish business baseline.` even though the backend was running locally.

**Root Cause:** Frontend fetch calls were hard-coded to `http://localhost:9000`, while the local backend was running on `http://localhost:8001`.

**Resolution:** Added a shared `NEXT_PUBLIC_API_BASE_URL` environment variable, updated frontend API calls to use it, and documented local backend host/port configuration in `.env.example`.

**Files Touched:** `apps/web/src/components/company-provider.tsx`, `apps/web/src/app/[lang]/page.tsx`, `apps/web/src/app/[lang]/projects/[id]/page.tsx`, `apps/web/src/lib/useOrchestratorStream.ts`, `.env.example`

## BUG-003 - 2026-08-13

**Issue:** The defect-tracking directive in `AGENTS.MD` was not consistently followed, so ledger updates were missing after some failed tests and fixes.

**Root Cause:** No automated enforcement required `docs/DEFECT_LEDGER.md` updates when tests failed or defects were fixed.

**Impact:** Missing historical defect records reduce traceability and make postmortems harder.

**Proposed Resolution:** Add lightweight enforcement through a pre-commit hook, CI check, and contributor documentation requiring ledger updates for bug fixes.

**Files/Places Touched:** `.git/hooks/pre-commit` (proposal), `.github/workflows/ci.yml` (proposal), `AGENTS.MD`

## BUG-004 - 2026-08-13

**Issue:** Test output surfaced FastAPI deprecation warnings for `@app.on_event("startup")` and `@app.on_event("shutdown")`.

**Root Cause:** `apps/api/app/main.py` uses older FastAPI lifecycle decorators instead of a lifespan context manager.

**Impact:** Future FastAPI versions may remove `on_event` support, and current tests include noisy warning output.

**Resolution:** Replace startup and shutdown event decorators with an async lifespan context manager using FastAPI's `lifespan` parameter.

**Files Touched:** `apps/api/app/main.py`

## BUG-005 - Date: 2026-08-14
* **Issue:** Browser onboarding showed `Failed to establish business baseline. Please try again.` while the backend health endpoint was online.
* **Root Cause:** The backend `/api/v1/companies` route was healthy and accepted the payload with `Bearer mock-jwt-token`; the failing browser path indicates the frontend can enter the baseline form with missing, stale, or invalid local auth session state.
* **Resolution:** Verified backend health, CORS preflight, and authenticated baseline creation against `http://localhost:8001`; advised refreshing the local mock login session before retrying. A follow-up frontend fix should surface the actual HTTP/auth error instead of the generic alert and redirect to login when token state is invalid.
* **Files Touched:** `docs/DEFECT_LEDGER.md`

## [BUG-006] - Date: 2026-08-14
* **Issue:** Local onboarding baseline setup could still fail behind a generic alert after entering company details.
* **Root Cause:** Local backend defaults and examples were split across ports (`8000`, `8001`, and `9000`), and the frontend swallowed the backend response status and detail when company creation failed.
* **Resolution:** Standardized the local backend default and sample configuration on `8001`, added an ignored local frontend API base file, and surfaced the actual company creation HTTP status/detail in the onboarding alert.
* **Files Touched:** `.env`, `.env.example`, `apps/api/app/core/config.py`, `apps/web/.env.local`, `apps/web/src/components/company-provider.tsx`, `apps/web/src/app/[lang]/page.tsx`, `docs/DEFECT_LEDGER.md`

## [BUG-007] - Date: 2026-08-14
* **Issue:** Browser onboarding failed with `Failed to execute 'fetch' on 'Window': Failed to parse URL from http://localhost:8001 /api/v1/companies`.
* **Root Cause:** The frontend concatenated API paths directly onto `NEXT_PUBLIC_API_BASE_URL`, so any accidental trailing whitespace in the runtime environment produced an invalid URL.
* **Resolution:** Added a shared frontend API base helper that trims whitespace and trailing slashes, updated all frontend backend fetch callers to use it, and cleaned related hook dependencies.
* **Files Touched:** `apps/web/src/lib/api.ts`, `apps/web/src/components/company-provider.tsx`, `apps/web/src/app/[lang]/page.tsx`, `apps/web/src/app/[lang]/projects/[id]/page.tsx`, `apps/web/src/app/[lang]/dev/telemetry/page.tsx`, `apps/web/src/lib/useOrchestratorStream.ts`, `docs/DEFECT_LEDGER.md`

## [BUG-008] - Date: 2026-08-14
* **Issue:** Intake playback for a small pet shop using WhatsApp returned canned logistics details such as dispatcher route scheduling and showed internal schema labels.
* **Root Cause:** The offline extractor fallback used a hard-coded logistics example when LLM extraction was unavailable, and playback appended an internal `Trigger/Actor/Activity/System/Friction` summary to the user-facing message.
* **Resolution:** Replaced the canned fallback with conservative keyword/context extraction, removed the schema summary from the user-facing playback, and added regression coverage for pet shop WhatsApp intake.
* **Files Touched:** `apps/api/app/core/orchestrator.py`, `apps/api/tests/test_interview.py`, `docs/DEFECT_LEDGER.md`

## [BUG-009] - Date: 2026-08-14
* **Issue:** The orchestration prompt described an Architect node, but the LangGraph did not include one; location requirements were also checked inconsistently after extraction.
* **Root Cause:** Context planning, required field selection, and interviewer logic were bundled inside `route_intent`, and the post-extraction completeness check ignored dynamically required fields such as location.
* **Resolution:** Added a real `context_architect` graph node, moved internal intake planning and physical-business location requirements into that node, preserved geographic context during state saves, and updated completeness checks to use architect-selected requirements.
* **Files Touched:** `apps/api/app/core/orchestrator.py`, `apps/api/tests/test_interview.py`, `docs/DEFECT_LEDGER.md`

## [BUG-010] - Date: 2026-08-14
* **Issue:** Analyst-behavior evals revealed that simple explicit locations could still be over-captured, for example `Koramangala and take orders via WhatsApp`.
* **Root Cause:** The deterministic location extractor only stopped at a narrow set of conjunction patterns and missed common workflow continuations such as `and take...`.
* **Resolution:** Added a deterministic analyst-behavior eval suite covering multi-turn intake gates and tightened the location phrase splitter to stop before workflow continuation clauses.
* **Files Touched:** `apps/api/app/core/orchestrator.py`, `apps/api/tests/test_analyst_behavior.py`, `docs/DEFECT_LEDGER.md`

## [BUG-011] - Date: 2026-08-14
* **Issue:** The agentic eval suite still exercised retired `SUGGESTER` scenarios after the product design changed to expose only `OPTIMIZER`, causing a misleading failure that initially looked like a missing enum bug.
* **Root Cause:** The Optimizer-only design decision was captured in `docs/PRD.md` and frontend types, but the change was not propagated to `AGENTS.MD`, database comments, and eval fixtures. There was no change-management checklist tying product mode decisions to schema, tests, eval datasets, and agent instructions.
* **Resolution:** Treat this as a change-management drift defect rather than restoring retired modes. The eval dataset and supporting docs should be updated to test Optimizer-only conversation behavior unless the broader mode model is deliberately reintroduced.
* **Prevention:** Add a design-decision checklist for mode changes that requires updates to PRD notes, state schema, API contracts, frontend types, database comments, eval fixtures, and AGENTS instructions in the same change. Add a lightweight CI assertion that every mode used in eval datasets is accepted by the active `SessionMode` schema and is also present in the current product-mode allowlist.
* **Files Touched:** `docs/DEFECT_LEDGER.md`

## [BUG-012] - Date: 2026-08-14
* **Issue:** Existing E2E eval scenarios for physical/local workflows expected synthesis completion even though they did not provide the location now required by the `context_architect` intake plan.
* **Root Cause:** The eval fixtures were not updated after location became a required component for physical businesses such as local delivery, storefront, and filing-cabinet workflows.
* **Resolution:** Updated the Kirana and office refund-request eval fixtures to include explicit operating locations before confirmation and synthesis.
* **Prevention:** When intake requirements change, add a fixture audit step that checks every existing scenario still supplies all architect-required components before its confirmation turn.
* **Files Touched:** `apps/api/tests/evals/eval_dataset.py`, `docs/DEFECT_LEDGER.md`

## [BUG-013] - Date: 2026-08-15
* **Issue:** Intake could produce robotic slot-filling questions and hallucinated workflow details, including assumed tools or people, to satisfy process-component JSON extraction.
* **Root Cause:** Clarification logic exposed multiple missing components to the LLM and split persona rules across separate prompt paths. The extractor prompt also did not explicitly forbid filling unknown schema fields with plausible defaults.
* **Resolution:** Replaced the split clarifying/missing-component prompts with a single `CONSULTANT_INTAKE_PROMPT`, added Progressive Disclosure through Thread Pulling, explicitly forbade invented tools/workflows, and constrained `_node_route_intent` to pass only one high-priority missing component to the LLM.
* **Files Touched:** `apps/api/app/core/orchestrator.py`, `apps/api/tests/test_interview.py`, `apps/api/tests/test_analyst_behavior.py`, `docs/DEFECT_LEDGER.md`, `AGENTS.MD`

## [BUG-014] - Date: 2026-08-15
* **Issue:** The LLM-as-a-judge eval suite failed before validating intake behavior because golden fixtures still used retired `SUGGESTER` mode and the harness used an `eval-session-*` prefix that bypassed normal intake confirmation.
* **Root Cause:** Eval data and harness assumptions were not updated after the product became Optimizer-only and after eval-session IDs were reserved for pre-confirmed synthetic runs.
* **Resolution:** Converted golden fixtures to `OPTIMIZER`, updated expected routing statuses to `AWAITING_CLARIFICATION` for unconfirmed intake prompts, and changed the harness session ID prefix so golden evals exercise the real clarification path.
* **Files Touched:** `apps/api/evals/golden_dataset.json`, `apps/api/evals/test_agent_quality.py`, `docs/DEFECT_LEDGER.md`

## [BUG-015] - Date: 2026-08-15
* **Issue:** `AGENTS.MD` still documented retired `SUGGESTER` and `EVALUATOR` budget tiers even though the active `SessionMode` schema and eval fixtures are Optimizer-only.
* **Root Cause:** Product-mode documentation was not updated at the same time as the schema and routing architecture, leaving future agents with contradictory instructions.
* **Resolution:** Updated `AGENTS.MD` to describe BuildSense as Optimizer-only, documented the single `SessionMode.OPTIMIZER` budget, added a directive not to reintroduce retired modes without a logged product decision, cleaned stale state/orchestrator docstrings, removed retired-mode budget branches from the golden eval harness, and rewrote scenario fixture clarification examples to ask one thread at a time.
* **Files Touched:** `AGENTS.MD`, `apps/api/app/core/orchestrator.py`, `apps/api/app/models/state.py`, `apps/api/evals/test_agent_quality.py`, `apps/api/tests/evals/eval_dataset.py`, `docs/DEFECT_LEDGER.md`

## [CHANGE-001] - Date: 2026-08-15
* **Issue:** Local development and evaluation runs lacked a first-class way to inspect request, run, node, LLM, tool, cost, and error flow without relying on external observability services.
* **Root Cause:** Telemetry was scattered across logs and external integrations, making local debugging and eval review difficult when Docker, LangSmith, or production monitoring were unavailable.
* **Resolution:** Added a bounded in-memory local telemetry system with request correlation middleware, privacy-safe event logging, node/LLM/tool wrappers, development-only inspection APIs, a Next.js telemetry viewer, environment configuration, and dedicated tests/docs. Runtime log directories are now ignored so generated telemetry artifacts do not pollute git status.
* **Files Touched:** `.gitignore`, `.env.example`, `apps/api/app/core/config.py`, `apps/api/app/main.py`, `apps/api/app/telemetry/*`, `apps/api/tests/test_telemetry.py`, `apps/web/src/app/[lang]/dev/telemetry/page.tsx`, `apps/web/src/lib/api.ts`, `docs/telemetry/*`, `docs/DEFECT_LEDGER.md`

## [CHANGE-002] - Date: 2026-08-15
* **Issue:** Agent documentation rules required basic docstrings but did not clearly require file-level ownership context, public contract documentation, architectural reasoning notes, or synchronized human/agent-facing docs.
* **Root Cause:** Documentation expectations were present as coding-style guidance rather than an enforceable change-hygiene protocol, allowing stale examples and orphan architectural assumptions to survive code changes.
* **Resolution:** Expanded `AGENTS.MD` documentation requirements to mandate file-level context, public API/route/tool/node/hook contracts, architectural reasoning comments for core changes, and documentation drift checks whenever behavior changes.
* **Files Touched:** `AGENTS.MD`, `docs/DEFECT_LEDGER.md`

## [BUG-016] - Date: 2026-08-15
* **Issue:** A full intake review found remaining fallback and eval paths that could still reward or emit robotic slot-filling behavior after the consultant persona rewrite.
* **Root Cause:** The primary LLM prompt path had been modernized, but offline extraction, correction handling, local synthesis fallback, judge rubrics, starter UI copy, and schema comments still carried older assumptions such as generic actor/activity fillers, hard-coded logistics reports, multi-slot clarification examples, and retired mode comments.
* **Resolution:** Removed generic offline actor/activity fabrication, preserved unclassified corrections as pending review context instead of forcing them into `system`, made the escape hatch fill all dynamically required components, replaced static fallback reports with component-grounded UNKNOWN-safe output, updated eval rubrics and examples to score consultant intake behavior, aligned frontend starter copy with one-step progressive disclosure, and cleaned the active schema comment to Optimizer-only.
* **Files Touched:** `apps/api/app/core/orchestrator.py`, `apps/api/tests/evals/judge.py`, `apps/api/tests/evals/test_runner.py`, `apps/api/tests/test_interview.py`, `apps/api/app/db/schema.sql`, `apps/web/src/app/[lang]/page.tsx`, `docs/DEFECT_LEDGER.md`

## [BUG-017] - Date: 2026-08-15
* **Issue:** The repository pre-commit checkpoint failed during the specification commit for the workspace navigation performance fix because `apps/api/tests/test_interview.py::test_frictionless_intake_completeness_no_friction` failed under the global Python hook environment.
* **Root Cause:** The hook runs `pytest apps/api/tests/ -q` with the machine-level Python environment, which produced a different playback summary casing/wording than the project `.venv` run that previously passed the backend suite. The specific assertion expects `Order inventory replenishment`, while the hook environment produced `Inventory replenishment`.
* **Resolution:** Logged the checkpoint failure before retrying the documentation commit. The functional fix should include a follow-up test/code adjustment so playback summary expectations are stable across supported local Python environments.
* **Files Touched:** `docs/DEFECT_LEDGER.md`

## [BUG-018] - Date: 2026-08-15
* **Issue:** Dashboard workflow submission blocked on the first orchestration pass before navigating, then the project workspace automatically triggered another orchestration pass on mount, making `Scaffolding Workspace...` and `Evaluating...` feel unnecessarily slow.
* **Root Cause:** `apps/web/src/app/[lang]/page.tsx` used `/api/v1/orchestrate` as both project creation and analysis kickoff, and `apps/web/src/app/[lang]/projects/[id]/page.tsx` called `executeOrchestratorRequest` after loading an existing session instead of hydrating state.
* **Resolution:** Changed dashboard submission to create a project quickly through `/api/v1/projects`, persist a scoped pending intake payload in `sessionStorage`, navigate immediately, hydrate existing workspace session state without starting orchestration, and consume pending intake once after the workspace is visible.
* **Files Touched:** `apps/web/src/app/[lang]/page.tsx`, `apps/web/src/app/[lang]/projects/[id]/page.tsx`, `apps/web/src/lib/useOrchestratorStream.ts`, `docs/DEFECT_LEDGER.md`

## [BUG-019] - Date: 2026-08-15
* **Issue:** The orchestration loop could surface placeholder dialogue such as `UNKNOWN UNKNOWN when UNKNOWN` and did not consistently reason across the broader business before asking the next intake question.
* **Root Cause:** Playback and fallback synthesis paths interpolated internal `ProcessComponents` values directly into user-facing templates, while the architect plan focused on workflow slots instead of a broader consultant rubric. Correction handling also preserved some updates as generic pending context rather than explicitly treating newer user statements as overwrites.
* **Resolution:** Added six-pillar architect metadata for Market, Operations, Financials, Personnel, Technology, and Risk; selected a single blind spot for the next high-value question; sanitized internal sentinels before prompt construction; generated natural playback from known details only; expanded correction routing to overwrite prior assumptions; and replaced the local synthesis slot dump with placeholder-safe fallback prose.
* **Files Touched:** `apps/api/app/core/orchestrator.py`, `apps/api/tests/test_interview.py`, `apps/api/tests/test_resilience.py`, `apps/api/tests/evals/eval_dataset.py`, `apps/api/tests/evals/judge.py`, `docs/DEFECT_LEDGER.md`
