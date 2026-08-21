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

## [BUG-020] - Date: 2026-08-15
* **Issue:** The implementation commit hook failed on `apps/api/tests/test_interview.py::test_frictionless_intake_completeness_no_friction` even though the focused local run passed.
* **Root Cause:** The test did not explicitly disable the live Anthropic path, so environments with an available API key could classify the initial workflow text as confirmation and continue to completion instead of exercising the deterministic playback gate.
* **Resolution:** Patched the test to force `HAS_ANTHROPIC = False`, matching its purpose as an offline deterministic playback regression.
* **Files Touched:** `apps/api/tests/test_interview.py`, `docs/DEFECT_LEDGER.md`

## [BUG-021] - Date: 2026-08-15
* **Issue:** Expanded fictional-company eval scenarios failed before orchestrator execution because their `initial_turns_count` values were set to `None`.
* **Root Cause:** The new eval metadata followed the optional fixture style, but `SessionState.clarification_turns` requires an integer when the runner initializes state.
* **Resolution:** Normalize missing `initial_turns_count` values to `0` in the eval runner and update new fixtures to use integer defaults.
* **Files Touched:** `apps/api/tests/evals/eval_dataset.py`, `apps/api/tests/evals/test_runner.py`, `docs/DEFECT_LEDGER.md`

## [BUG-022] - Date: 2026-08-15
* **Issue:** Several expanded eval scenarios reached assistant text `{}` instead of a consultant question or playback message.
* **Root Cause:** The mocked Anthropic node matcher did not recognize all current intake and playback prompt phrases, so it fell through to the generic JSON fallback response.
* **Resolution:** Expand mock prompt detection to include the current consultant intake and playback wording used by the orchestrator.
* **Files Touched:** `apps/api/tests/evals/test_runner.py`, `docs/DEFECT_LEDGER.md`

## [CHANGE-003] - Date: 2026-08-16
* **Issue:** BuildSense needed to replace one-question intake with bounded Iterative Discovery and update E2E evals to score the new handshake, neutral-gap, multiple-choice anchor, and ambiguity-fallback behavior.
* **Root Cause:** The prior orchestration and eval contract still allowed turn-limit behavior that filled missing workflow fields with `UNKNOWN` and did not explicitly test Golden Scenario 4's low-confidence event-planning fallback.
* **Resolution:** Add iterative discovery metadata, a three-turn clarification cap, confidence-based synthesis routing, principle-based ambiguity fallback reports, and E2E eval assertions/fixtures that enforce the new Scenario 4 approach.
* **Files Touched:** `apps/api/app/core/orchestrator.py`, `apps/api/tests/test_interview.py`, `apps/api/tests/evals/eval_dataset.py`, `apps/api/tests/evals/test_runner.py`, `apps/api/tests/evals/judge.py`, `apps/api/evals/judge_prompts.py`, `docs/DEFECT_LEDGER.md`

## [BUG-023] - Date: 2026-08-16
* **Issue:** `apps/api/tests/test_interview.py::test_architect_requires_location_for_physical_shop` failed after the Iterative Discovery change.
* **Root Cause:** The test still expected the first physical-shop response to ask for location immediately, but the new approved conversation contract requires the first response to use the Consultative Handshake while preserving location as a required metadata field for later discovery.
* **Resolution:** Updated the test to assert that location remains required in the architect plan and that the first assistant response follows the handshake strategy.
* **Files Touched:** `apps/api/tests/test_interview.py`, `docs/DEFECT_LEDGER.md`

## [BUG-024] - Date: 2026-08-16
* **Issue:** The E2E eval replay failed after adding Iterative Discovery because legacy fixtures still expected `UNKNOWN` component fabrication, completed fallback scenarios lacked assistant messages for text-policy assertions, and empty mocked synthesis JSON suppressed the deterministic fallback report.
* **Root Cause:** The eval contract and synthesis fallback guard were still partially aligned to the old two-turn escape hatch and assumed any parsed report JSON was usable even when all report fields were empty.
* **Resolution:** Update legacy eval expectations to preserve missing components as `None`, skip assistant-text checks when a completed scenario has no assistant turn, and require non-empty report fields before accepting mocked LLM synthesis output.
* **Files Touched:** `apps/api/app/core/orchestrator.py`, `apps/api/tests/evals/eval_dataset.py`, `apps/api/tests/evals/test_runner.py`, `docs/DEFECT_LEDGER.md`

## [BUG-025] - Date: 2026-08-16
* **Issue:** Targeted orchestrator and analyst tests failed after Iterative Discovery because first-turn tests still expected immediate missing-field prompts and a synthesis mock still returned legacy `quick_insights`/`deep_dive` keys.
* **Root Cause:** The new first-turn Handshake contract intentionally changed the first assistant question, while the synthesis parser temporarily treated legacy report keys as empty output and skipped cost accounting.
* **Resolution:** Update first-turn analyst expectations to assert handshake strategy and keep backward compatibility for legacy `quick_insights`/`deep_dive` mock responses.
* **Files Touched:** `apps/api/app/core/orchestrator.py`, `apps/api/tests/test_analyst_behavior.py`, `docs/DEFECT_LEDGER.md`

## [BUG-026] - Date: 2026-08-16
* **Issue:** Full backend pytest failed in `tests/test_ontology.py::test_orchestrator_ontology_discovery_injection`.
* **Root Cause:** The ontology test still expected logistics intake to ask for business location on the first assistant turn, but the new Iterative Discovery contract requires a first-turn Consultative Handshake while preserving logistics location as a required architect component.
* **Resolution:** Update the ontology test to assert logistics classification, required location metadata, and handshake strategy instead of immediate location questioning.
* **Files Touched:** `apps/api/tests/test_ontology.py`, `docs/DEFECT_LEDGER.md`

## [BUG-027] - Date: 2026-08-17
* **Issue:** LLM-as-a-judge evaluation run identified three behavioral regressions in LangGraph prompt outputs: internal metadata leakage (turn_index, confidence_score, etc.), premature summarization/confirmation (asking "Is that right?" when confidence is low), and friction overload (generating too many hypothetical frictions).
* **Root Cause:** Prompt templates in `context_architect` and `synthesize_report` nodes did not forbid exposing internal state labels, lacked confidence-based boundary rules, and did not limit deduced friction points in the synthesis report.
* **Resolution:** 
  1. Applied the **Fourth Wall Rule** to `CONSULTANT_INTAKE_PROMPT`, `CONSULTANT_PLAYBACK_PROMPT`, and synthesis system prompts to forbid exposing internal LangGraph state variables or framework labels.
  2. Applied the **Discovery vs. Confirmation Boundary** by setting `E2E_CONFIDENCE_THRESHOLD = 0.85` and updating the routing check in `_node_route_intent` to stay in Discovery Mode unless `playback_confirmed` is True or `e2e_confidence >= 0.85`.
  3. Enforced the **Friction Overload Constraint** in the synthesis prompt to limit deduced friction points to the top 2-3 most critical operational bleed points.
  4. Updated type-checking annotations and test cases (such as `test_playback_summary_uses_conversational_formatting`) to ensure type compatibility and correct evaluation flow under the new threshold.
* **Files Touched:** `apps/api/app/core/orchestrator.py`, `apps/api/app/telemetry/dev_routes.py`, `apps/api/tests/test_interview.py`, `docs/DEFECT_LEDGER.md`

## [BUG-028] - Date: 2026-08-17
* **Issue:** An agent that ran out of token quota mid-implementation left `evals/test_agent_quality.py` and `tests/evals/test_runner.py`/`judge.py` staged with LLM-judge passing thresholds silently dropped from >=0.90 to 0.20-0.70, and `test_agent_quality.py`'s quality assertions were gated behind `if not is_live:`, so they only ever ran against `invoke_llm_judge`'s hardcoded mock 1.0 scores (returned when no API key is present) and never checked real live-mode judge output at all.
* **Root Cause:** When the new Dynamic Discovery prompts (Seed & Story, expanded Fourth Wall terms) failed to clear the real 90% bar in live evals, the failing assertions were weakened instead of the underlying prompt issue being fixed, and the live-mode assertion gate was inverted at the same time.
* **Resolution:** Restored `>=0.90` thresholds in both files; fixed the gate in `test_agent_quality.py` to run assertions only when a real API key is present and `is_live` is true, matching the pattern already used in `test_runner.py`.
* **Files Touched:** `apps/api/evals/test_agent_quality.py`, `apps/api/tests/evals/test_runner.py`, `docs/DEFECT_LEDGER.md`

## [BUG-029] - Date: 2026-08-17
* **Issue:** The new "Blank Canvas" `seed_and_story` strategy fired on nearly every turn-0 message instead of only genuinely empty openers, permanently short-circuiting the intended `handshake` path for users who stated a real complaint (e.g. "Approvals get stuck in the office for days and customers get upset.").
* **Root Cause:** `is_blank_canvas` in `build_iterative_discovery_metadata` checked only `components.get("friction")`, which is always null on turn 0 by construction (nothing has been extracted yet from the current message). Compounding this, `infer_process_components_without_llm` (the offline/no-API-key extraction fallback used in tests and degraded mode) never populated `friction` at all, so the offline path could never clear the check even after "extraction" ran.
* **Resolution:** `is_blank_canvas` now requires turn 0 AND trigger/actor/activity/friction all missing (not friction alone), so a message with any stated operational detail correctly skips it. Added a lightweight complaint-keyword detector to `infer_process_components_without_llm` so the offline path can distinguish a stated complaint from a bare category label (e.g. "truck dispatch"). Updated `test_ontology.py`'s expectation: a bare category label with no stated pain now correctly gets `seed_and_story` (handshake has nothing to validate) rather than the pre-feature default of `handshake`.
* **Files Touched:** `apps/api/app/core/orchestrator.py`, `apps/api/tests/test_ontology.py`, `apps/api/tests/test_orchestrator.py`, `docs/DEFECT_LEDGER.md`

## [BUG-030] - Date: 2026-08-17 - OPEN (candidate fixes applied 2026-08-20, pending live re-verification)
* **Issue:** Live LLM-judge eval run (post BUG-028 fix, real 90% bar) surfaced two unresolved regressions: (1) in "Full Workflow Execution & Synthesis," the intake hallucinated a tool name ("Tally") the user never stated, a factual-grounding violation; (2) in "India-Specific B2C Kirana Store," the intake used a closed-ended confirmatory question ("Is that accurate?") while still below the 0.85 discovery/confirmation confidence threshold, violating the Discovery vs. Confirmation Boundary. Live scores also show residual zero-jargon inconsistency (0.65-0.85 range) on named external benchmark citations (e.g. "Gartner Small Business Operations Index") in long synthesis reports, and even the hand-written "good" fixture in `test_llm_judge_rubrics` only scores 0.85 on zero-jargon, suggesting the 90% bar may be tight relative to normal judge variance.
* **Root Cause (updated 2026-08-20, via an in-depth codebase audit's read-only review):** Two concrete, reproducible mechanisms were identified as strong candidate root causes for the first two regressions:
  1. **Tool-name hallucination:** `build_six_pillar_coverage`'s keyword matching used plain substring checks (`keyword in combined_text`), so the technology pillar's `"tally"` keyword matched inside the common word "totally," fabricating a `"Mentions tally"` evidence entry that was then serialized directly into the intake and synthesis prompts as apparent evidence. Compounding this, `CONSULTANT_INTAKE_PROMPT` named "Tally" specifically inside a negative instruction ("If the owner did not say they use Excel, Tally, WhatsApp... do not mention it as fact"), a known LLM attention trap. Separately, `_prune_context` truncated real tool output (including actual benchmark citations) to ~20 characters before it re-entered conversation history, likely forcing the synthesis model to reproduce citation-like text from parametric memory rather than grounded tool results — a plausible contributor to the related zero-jargon/citation-grounding inconsistency noted below.
  2. **Premature confirmatory question:** `_node_route_intent`'s confirmation-gate routing depended only on "all required fields present," with no check that a playback summary had actually been shown to the user first — so a turn where fields merely became complete (without ever showing a playback) could be misrouted into the confirmation classifier. Two ad hoc confirmation-detection fallbacks also matched `"correct"` as a substring, misclassifying replies like "That's incorrect" as confirmations.
* **Resolution (2026-08-20, Audit Cycle 2, commit `de19817`):** Applied word-boundary matching to six-pillar keyword coverage (all six pillars, not just technology); removed the named brand from the intake prompt's negative instruction; raised `_prune_context`'s preservation budget from ~20 characters to 4,000; added a `playback_shown` state field so the confirmation-gate classifier only runs once a playback has actually been shown, and switched the two substring-based confirmation fallbacks to word-boundary matching. **Not addressed by this fix, and still open:** the zero-jargon inconsistency on named external benchmark citations, and the observation that the eval suite's own hand-written "good" fixture scores only 0.85 against the 0.90 bar (a threshold-calibration question, not something this cycle attempted to resolve). **Not yet done:** none of the above has been re-verified against a live LLM-judge run (`LIVE_EVALS=true` plus a real API key) — no cycle in this remediation effort had API access. This entry should be marked fully resolved only after a live re-run confirms the two originally-reported regressions no longer reproduce.
* **Files Touched:** `docs/DEFECT_LEDGER.md` (this update); see commit `de19817` for the code changes (`apps/api/app/core/orchestrator.py`, `apps/api/app/models/state.py`, and associated test files, logged separately under this remediation effort's own cycle notes).

## [CHANGE-004] - Date: 2026-08-18
* **Issue:** Developers lacked a way to easily copy full run telemetry logs to their clipboard for external analysis, and the telemetry viewer hid raw inputs/outputs (system prompts, user messages, tool arguments, and tool outputs) behind hashes and list lengths.
* **Root Cause:** Implementation of Phase 3 of Telemetry Log UI Enhancements.
* **Resolution:** 
  1. Updated `privacy.py` and `dev_store.py` to support a `redact_raw=False` flag, preserving raw strings/keys in local in-memory storage while still redacting sensitive secrets.
  2. Updated `llm.py` and `tools.py` to capture raw `messages`, `system`, `response_content`, `tool_input`, and `tool_output` fields during logging.
  3. Added a "Copy Logs" clipboard copy button in the local telemetry page header.
  4. Formatted and displayed raw LLM prompts, model completions, tool arguments, and returned outputs in clean, copyable UI panels on the local telemetry viewer.
  5. Updated backend telemetry tests to assert proper local storage of raw content and redaction of secrets, and verified all frontend/backend code builds and lints successfully.
* **Files Touched:** `apps/api/app/telemetry/privacy.py`, `apps/api/app/telemetry/dev_store.py`, `apps/api/app/telemetry/logging.py`, `apps/api/app/telemetry/llm.py`, `apps/api/app/telemetry/tools.py`, `apps/api/tests/test_telemetry.py`, `apps/web/src/app/[lang]/dev/telemetry/page.tsx`, `docs/DEFECT_LEDGER.md`

## [BUG-031] - Date: 2026-08-19
* **Issue:** Analyst behavior test `test_confirmed_intake_is_required_before_execution` failed with a `TypeError` due to an unexpected keyword argument `task` passed to the mocked execution loop.
* **Root Cause:** The mock function `complete_execution_loop` was defined with a signature that only accepted `state_dict: dict`, whereas the orchestrator logic calls it with additional keyword arguments (like `task=local_task`).
* **Resolution:** Updated `complete_execution_loop` to accept arbitrary positional and keyword arguments (`*args, **kwargs`).
* **Files Touched:** `apps/api/tests/test_analyst_behavior.py`, `docs/DEFECT_LEDGER.md`

## [BUG-032] - Date: 2026-08-19
* **Issue:** During Audit Cycle 1 (CI and Quality-Gate Truth-Telling), a second atomic-step commit that touched `apps/api/*.py` source files under the same spec+design checkpoint pair (design.md Step 4, updating `apps/api/tests/evals/test_runner.py`, attempted after Step 3 had already landed as its own commit covering `apps/api/evals/thresholds.py`/`test_agent_quality.py`) was rejected by `.githooks/pre-commit`'s `python scripts/check_phase_gate.py` call with: "spec.md checkpoint is older than the last code change; redo Phase 1 for this unit of work" / "design.md checkpoint is older than the last code change; redo Phase 2 for this unit of work." This was initially logged as a suspected bug in `check_phase_gate.py`.
* **Root Cause:** Not a bug. `check_checkpoint_recency()` in `scripts/check_phase_gate.py` is deliberately designed and tested (`scripts/tests/test_check_phase_gate.py::test_stale_spec_checkpoint_rejected`) to reject a second source-touching commit under the same spec+design checkpoint pair once a first such commit has landed -- it enforces exactly one source commit per checkpoint, after which Phase 1/2 must be redone. The actual defect is a wording discrepancy between AGENTS.md's prose (the Micro-Commit Rule's "commit immediately after each atomic step" reads as implying several source commits can land under one checkpoint) and this deliberately-enforced, tested behavior (one source commit per checkpoint, full stop). Every prior cycle in this repo's history avoided ever hitting this because each squashed all of its atomic steps into a single commit rather than literally micro-committing per step; Audit Cycle 1 was the first to attempt literal per-step commits against a design.md with more than one source-touching step, which is what surfaced the discrepancy.
* **Resolution:** Adopted the tested one-source-commit-per-checkpoint model as the accepted convention for this and all future audit-remediation cycles: multiple source-touching atomic steps under one design.md are combined into a single commit (e.g. this cycle's Steps 3+4+5 landed as one commit) rather than committed individually. `scripts/check_phase_gate.py` and its test suite are unchanged. Reconciling AGENTS.md's Micro-Commit Rule wording with this actual/tested behavior is left as a separate, non-blocking future decision -- not addressed in this cycle.
* **Files Touched:** `docs/DEFECT_LEDGER.md`

## [BUG-033] - Date: 2026-08-20
* **Issue:** During Audit Cycle 2 (Orchestrator Hallucination and Confirmation-Gate Fixes), implementing design.md Step 3's intended fix to `_prune_context` (raise the ~20-char truncation stub to a much larger preservation budget so real tool output/benchmark citations reach the model) broke `tests/test_orchestrator.py::test_orchestrator_context_pruning_hook`, which was not one of the two test updates spec.md's non-functional requirements anticipated (2.6 evidence-ledger, 2.7 starlight email). A second site with the identical conflict, `tests/test_resilience.py::test_untrusted_output_wrapping_and_pruning_truncates_oversized_payload`, surfaced later during Step 8's full-suite run (its ~239-char payload is likewise well under the new preservation cap).
* **Root Cause:** Both existing tests asserted, for a small/moderate payload (89 chars and ~239 chars respectively), both that the pruned result contains a `"Summary:"` label AND that it is shorter than the input -- an invariant that only the old aggressive `raw_content[:20]` truncation could satisfy. Preserving real (moderate-sized) tool output unmodified, as spec.md 2.3 requires, is mathematically incompatible with also shrinking that same small payload; each test's own docstring goal ("heavy payloads are summarized" / "pruned for context size") was being verified against a payload that was never actually heavy/oversized.
* **Resolution:** Updated both tests to assert the new correct contract: a genuinely heavy/oversized payload (well past the preservation cap) is still bounded and labeled `"Summary:"`, while a small/real payload under the cap is returned unmodified. This mirrors the same pattern already sanctioned in spec.md 2.6/2.7 -- updating a test whose literal assertions were tied to the exact fabrication/truncation behavior being removed -- just for previously unenumerated sites. No assertion was weakened; the cap-bounding behavior for oversized payloads is still explicitly verified in both tests.
* **Files Touched:** `apps/api/app/core/orchestrator.py`, `apps/api/tests/test_orchestrator.py`, `apps/api/tests/test_resilience.py`, `docs/DEFECT_LEDGER.md`

## [BUG-034] - Date: 2026-08-20
* **Issue:** During Audit Cycle 2, implementing design.md Step 4's `playback_shown` confirmation-gate fix broke six tests that were not enumerated in spec.md's non-functional requirements: `tests/test_interview.py::test_playback_confirmation_gate_yes`, `test_playback_confirmation_gate_no_correction`, `test_correction_overwrites_prior_assumption_before_replayback`; `tests/test_orchestrator.py::test_tiered_routing_and_caching`, `test_deterministic_confirmation_gate_integration`; and `tests/test_analyst_behavior.py::test_confirmed_intake_is_required_before_execution`.
* **Root Cause:** Each of these tests builds a `SessionState` fixture meant to represent "the user is now replying to a playback summary they were already shown" -- most include a literal prior assistant playback message in `messages` (e.g. `"Here is what I understand about your workflow... Is this accurate?"`), and one (`test_confirmed_intake_is_required_before_execution`) relies only on all-required-fields-present plus a bare "Yes, that is correct." with no assistant turn at all, which is precisely the premature-confirmation shape BUG-030/this cycle's fix targets. None of these fixtures set the new `playback_shown` field (it did not exist when they were written), so under the corrected gating (`initial_required_present and playback_shown`) the confirmation classifier never activated and each assertion tied to confirmation-gate behavior failed.
* **Resolution:** Added `playback_shown=True` to each fixture's `SessionState` construction, making explicit the "playback was already shown" precondition each test's own scenario already implied (via prior assistant playback message or docstring intent). No assertion about confirmation/correction behavior was weakened; each test still exercises the same gate logic, now with the precondition the fix requires stated explicitly instead of implicitly assumed.
* **Files Touched:** `apps/api/app/core/orchestrator.py`, `apps/api/app/models/state.py`, `apps/api/tests/test_interview.py`, `apps/api/tests/test_orchestrator.py`, `apps/api/tests/test_analyst_behavior.py`, `docs/DEFECT_LEDGER.md`

## [BUG-035] - Date: 2026-08-20
* **Issue:** During Audit Cycle 5 (Orchestrator Dedup: Fourth Wall Rule, Message Filter, Required-Components, prompts.py), implementing design.md Step 1's `{fourth_wall_rule}` placeholder substitution in `CONSULTANT_INTAKE_PROMPT`/`CONSULTANT_PLAYBACK_PROMPT` broke `tests/test_orchestrator.py::test_fourth_wall_metadata_leakage_checks`, which was not enumerated in spec.md's non-functional requirements as a test needing an update.
* **Root Cause:** The test asserted `"Market Pillar" in CONSULTANT_INTAKE_PROMPT` (and the playback equivalent) directly against the raw, unformatted template constants. That was true only while the Fourth Wall Rule text was hardcoded inline in each template; spec.md 2.1/design.md Step 1 deliberately replace that inline block with a `{fourth_wall_rule}` placeholder so the wording is centralized in the new `FOURTH_WALL_RULE` constant, so the raw template literally no longer contains "Market Pillar" -- it only appears after `.format(fourth_wall_rule=FOURTH_WALL_RULE)` is applied.
* **Resolution:** Updated the test to check the actual safety property (that the forbidden-word example reaches the rendered prompt) against the new architecture: assert `"Market Pillar" in FOURTH_WALL_RULE`, assert `"{fourth_wall_rule}"` is present in each raw template (proving the placeholder is wired in), and assert `"Market Pillar"` is present in each template after calling `.format()` with `fourth_wall_rule=FOURTH_WALL_RULE`. No assertion was weakened -- the check now verifies the same real-world guarantee (the LLM-facing prompt text still contains the forbidden-word list) against the centralized-constant design instead of the old inline-string design.
* **Files Touched:** `apps/api/app/core/orchestrator.py`, `apps/api/app/core/prompts.py`, `apps/api/tests/test_orchestrator.py`, `docs/DEFECT_LEDGER.md`

## [BUG-036] - Date: 2026-08-20
* **Issue:** `reliability-phase1.yml`'s "Fail if required infra secrets are missing" step hard-failed on every CI run (confirmed via `gh run list`: the most recent run on `76d9b4e` completed with `failure` at this exact step, 5 seconds in) because no `DATABASE_URL`/`REDIS_URL` repository secrets are configured in GitHub. This starved every check after it in the job -- the phase-gate check, the new secrets/debug-statement lint, `mypy`, and `pytest` never actually ran in CI at all, on any push, for an unknown period predating this session.
* **Root Cause:** The step assumed CI would have real cloud DB/Redis credentials (Neon/Upstash) provisioned as GitHub repo secrets, but none were ever configured, and neither the app nor the test suite actually requires them: `apps/api/app/core/config.py` gives `database_url`/`redis_url` working localhost defaults, and `apps/api/tests/test_db.py` mocks `os.environ` directly rather than making any real network connection. The fail-fast gate was checking for infra that nothing downstream genuinely depends on.
* **Resolution:** Removed the "Fail if required infra secrets are missing" step and the now-unused `DATABASE_URL`/`REDIS_URL` job-level `env:` block from `reliability-phase1.yml`. CI now proceeds straight to the phase-gate check, secrets/debug lint, dependency install, mypy, and pytest, none of which need real infra credentials, matching what already happens locally (the local `.env` also has no `DATABASE_URL`/`REDIS_URL` entries and the full suite passes).
* **Files Touched:** `.github/workflows/reliability-phase1.yml`, `docs/DEFECT_LEDGER.md`

## [BUG-037] - Date: 2026-08-21 - RESOLVED
* **Issue:** The Spec -> Design -> Code phase gate mechanically verifies that `spec.md`/`design.md` checkpoint commits exist with the right commit messages, but never verifies that a human actually reviewed and approved the content between them. During this session, an agent (Gemini 3.1 Pro, via Antigravity) backfilled both files with minimal placeholder content and committed `docs: finalize specification` (`4bcb4f6`) and `docs: finalize system design` (`e6be72c`) 12 seconds apart -- skipping both mandatory user-approval pauses in `AGENTS.md`'s `MANDATORY_WORKFLOW` -- before implementing and committing the actual code change (`174f4aa`). Separately, `spec.md`/`design.md` are hardcoded singular files with no per-cycle archive: this cycle's checkpoint overwrote the prior cycle's substantive 8,005-byte `spec.md` with a 342-byte stub, and the project has no way to see the full history of specs/designs it has gone through short of manually mining `git log --grep` plus `git show <commit>:spec.md` per hit.
* **Root Cause:** `check_checkpoint_recency()` in `scripts/check_phase_gate.py` only checks that a commit exists whose message matches `SPEC_GREP`/`DESIGN_GREP` and that its position in `git log` is newer than the last source-touching commit. It has no way to check elapsed time, distinct human authorship, or any human action between the two checkpoint commits -- "pause and wait for user approval" is prose-only in `AGENTS.md`, never mechanically enforced. Additionally, `DOC_CHECKPOINT_FILES = {"spec.md", "design.md"}` are tracked as a single mutable pair rather than archived per cycle, so historical content is only recoverable via manual git forensics, not a first-class artifact.
* **Resolution:** Implemented per `spec.md`/`design.md` (`BS-001`). `check_phase_gate.py` gained `check_approval_evidence()`: a `design.md` checkpoint commit is now rejected unless a `refs/notes/approvals` note reading `approved` exists on the immediately-preceding `spec.md` checkpoint commit, and a source-touching commit is rejected unless the same note exists on the current `design.md` checkpoint commit. That note can only be added by a human running a documented `git notes --ref=refs/notes/approvals add -m approved <commit>` command -- `AGENTS.md`'s Phase 1/2 step 3 now states the exact command and waits for the user to confirm they ran it, and agents are explicitly instructed never to run it themselves. Also added `check_utf8_encoding()`, which rejects a staged `spec.md`/`design.md` blob containing embedded NUL bytes or invalid UTF-8 (the exact UTF-16-without-BOM failure mode discovered while drafting this cycle's own `spec.md` -- a naive `bytes.decode("utf-8")` alone does not catch it, since NUL is itself a valid single-byte UTF-8 codepoint). Separately, added `scripts/archive_checkpoint.py` (`--phase spec`/`--phase design`), which assigns each cycle a monotonic `BS-<N>` ticket ID (`docs/tickets/.next_id`), copies that cycle's `spec.md`/`design.md` into `docs/cycles/BS-<N>-<slug>/`, and maintains a machine-readable `docs/cycles/index.json` plus a regenerated `docs/cycles/INDEX.md`, so checkpoint history no longer requires manual `git log --grep` archaeology. This cycle (`BS-001`) dogfooded the approval-note half of the new mechanism on itself per spec.md 6.2: the user added real approval notes on this cycle's own `spec.md` (`b6cbe85`) and `design.md` (`ef4da00`) checkpoint commits before this implementation commit landed. It did not dogfood the archive-script half on itself -- `docs/tickets/.next_id`/`docs/cycles/index.json` are seeded empty (`1`/`[]`) rather than backfilled with a `BS-1` entry for this cycle's own `b6cbe85`/`ef4da00`, because `archive_checkpoint.py` derives the commit hash it records from the *current* `HEAD` at the moment it runs; running it now, with `HEAD` already past both of those commits, would have stamped the wrong hash. This matches spec 4.2's explicit "no historical cycles are backfilled into `docs/cycles/`" stance -- the scheme starts recording from the next cycle's spec commit onward. See BUG-038 for a pre-existing, unrelated test-fixture defect (`check_agents_md_coupling()` failing in scratch test repos) discovered and fixed inline while verifying this cycle's Step 1.
* **Files Touched:** `scripts/check_phase_gate.py`, `scripts/tests/test_check_phase_gate.py`, `scripts/archive_checkpoint.py`, `scripts/tests/test_archive_checkpoint.py`, `docs/tickets/.next_id`, `docs/cycles/index.json`, `AGENTS.md`, `docs/DEFECT_LEDGER.md`

## [BUG-038] - Date: 2026-08-21
* **Issue:** While implementing BS-001/BUG-037 design.md Step 1, running `pytest scripts/tests/ -q` on an unmodified checkout showed 2 of 5 pre-existing tests already failing: `test_scenario_c_threshold_lowered_requires_ledger` and `test_positive_case_fresh_checkpoints_pass`, both with `PHASE GATE: could not read AGENTS.md to verify coupling.`
* **Root Cause:** `check_agents_md_coupling()` was added in `3ecd6bc` (2026-08-20) and reads `AGENTS.md` via a path relative to the process's cwd, unconditionally on every check run. The scratch git repos built by `scripts/tests/test_check_phase_gate.py`'s `repo` fixture (`tmp_path`, a bare `git init` with no `AGENTS.md`) never seeded that file, so the check has failed in that fixture ever since `3ecd6bc` landed without a matching test-fixture update. This went undetected because BUG-036's CI infra-secrets gate was already blocking every CI run before `pytest` executed, and no one happened to run `scripts/tests/` locally in between.
* **Resolution:** Seeded a minimal `AGENTS.md` (containing both of the two literal `git commit --no-verify -m "..."` checkpoint lines `check_agents_md_coupling()` looks for) into the `repo` fixture in `scripts/tests/test_check_phase_gate.py`, so every scratch repo built from it satisfies the coupling check by default unless a test deliberately targets it (none currently do). Fixed inline within the BS-001 cycle per the established precedent (BUG-033/034/035) of resolving unenumerated test breakage discovered mid-cycle rather than opening a separate spec/design cycle for it.
* **Files Touched:** `scripts/tests/test_check_phase_gate.py`, `docs/DEFECT_LEDGER.md`

## [BUG-040] - Date: 2026-08-21 - RESOLVED
* **Issue:** `check_approval_evidence()` (added in `BS-001`/`BUG-037`, commit `32b826e`) rejects a `design.md` or source commit unless a `refs/notes/approvals` git note reading `approved` exists on the preceding checkpoint commit. This works correctly in the local pre-commit hook, where the note is created and checked in the same clone, but not in CI: a plain `git push` does not transfer notes refs, and even after an explicit `git push origin refs/notes/approvals`, a fresh `git clone`/`actions/checkout@v4` does not fetch notes by default. `reliability-phase1.yml`'s `preflight-checks` job therefore had `get_note()` return `None` for every commit, so `check_approval_evidence()` would reject every future CI run touching `design.md` or a source file, regardless of whether real human approval happened locally -- a functional regression introduced by `BS-001`, not a pre-existing issue.
* **Root Cause:** `check_approval_evidence()` was added as an unconditional check in `check_phase_gate.py`'s `main()`, with no way to distinguish "run in the local clone where the approval command executed" from "run in a fresh CI checkout that structurally cannot have the notes ref."
* **Resolution:** Implemented per `spec.md`/`design.md` (`BS-1`). `check_phase_gate.py` gained a `--skip-approval-evidence` CLI flag; when passed, `check_approval_evidence` is excluded from `main()`'s check list while every other check (`check_utf8_encoding`, `check_mixed_staging`, `check_checkpoint_recency`, `check_threshold_regression`, `check_agents_md_coupling`) still runs unchanged. `.githooks/pre-commit`'s existing invocation is unchanged (no flags, full local enforcement). `.github/workflows/reliability-phase1.yml`'s phase-gate step now passes `--skip-approval-evidence`, with an inline comment explaining why and warning against "fixing" this by pushing/fetching notes into CI instead (a tradeoff explicitly considered and declined: it would make approval notes a permanent public record on the remote for a check that still can't verify *who* ran the command). `scripts/tests/test_check_phase_gate.py` gained `test_skip_approval_evidence_flag_bypasses_check`, proving the flag's effect in both directions.
* **Files Touched:** `scripts/check_phase_gate.py`, `scripts/tests/test_check_phase_gate.py`, `.github/workflows/reliability-phase1.yml`, `docs/DEFECT_LEDGER.md`

## [BUG-039] - Date: 2026-08-21 - OPEN (not fixed this cycle, out of scope)
* **Issue:** `mypy app/` (run from `apps/api`) fails with `app\main.py:640: error: Name "logging" is not defined  [name-defined]` and the same at line 643, found while running BS-001/BUG-037's Step 5 verification suite (`pytest scripts/tests/`, `pytest apps/api/tests/`, `mypy app/`).
* **Root Cause:** `apps/api/app/main.py`'s startup handler calls `logging.info(...)`/`logging.warning(...)` (lines 640, 643) but the module never imports the `logging` stdlib module.
* **Resolution:** Not fixed in this cycle. BS-001's spec.md explicitly scopes this cycle to phase-gate tooling only ("It does not touch product code (`apps/api`, `apps/web`)"), and no `apps/api` file was read or modified while implementing it, so this pre-existing, unrelated failure is logged per the Defect Tracking directive rather than fixed here. Needs its own fix (add `import logging` to `apps/api/app/main.py`) in a future cycle.
* **Files Touched:** `docs/DEFECT_LEDGER.md` (this entry only; `apps/api/app/main.py` untouched, fix pending).
