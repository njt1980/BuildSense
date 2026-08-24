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

## [CHANGE-005] - Date: 2026-08-22
* **Issue:** The `slowapi` rate-limiter strict 5/day limit on `/api/v1/orchestrate` restricted legitimate, multi-turn "Progressive Discovery" intra-session conversations, and penalized users who brought their own API keys (BYOK).
* **Root Cause:** A single endpoint handles both new session creation and in-session follow-up turns, and `slowapi` was applied uniformly to all requests hitting that path regardless of payload content or session status.
* **Resolution:** Removed the `@limiter.limit("5/day")` blanket decorator from `/api/v1/orchestrate`. Implemented conditional IP rate limiting via `redis_client.check_ip_rate_limit(client_ip, max_allowed_runs=3)` applied strictly to new session creation (when `session_id` is missing) and only when a BYOK (`x-user-anthropic-key`) is not provided. Applied a 3/day `slowapi` limit to the standalone `/api/v1/projects` creation endpoint for parity.
* **Files Touched:** `apps/api/app/main.py`, `AGENTS.MD`, `docs/DEFECT_LEDGER.md`

## [BUG-041] - Date: 2026-08-22 - RESOLVED (Pending Final Verification)
* **Issue:** After completing all six pillars in the dialogue panel, the backend completes orchestration successfully but no visible concluding message (e.g., "BUILDSENSE INTELLIGENCE") is sent to the chat panel. The top status control silently changes from "Evaluating..." to "Run Analysis", forcing the user to notice the change, switch to the Executive Report tab, and click the button themselves.
* **Root Cause:** The transition-out-of-dialogue UX has no explicit conversational handoff or auto-navigation mechanism once coverage is complete, leaving a gap where the app appears to stop responding.
* **Resolution:** In recent testing (2026-08-22), an explicit closing message ("I have completed my analysis... Executive Report is ready") was successfully generated and observed for multiple personas. This appears to have been resolved, potentially by a recent prompt/model shift. Marked as tentatively resolved.
* **Files Touched:** `docs/DEFECT_LEDGER.md` (this entry only).

## [BUG-042] - Date: 2026-08-22 - OPEN
* **Issue:** The consultative intake process over-indexes on operational pain points while leaving other required pillars (budget/financial constraints, personnel/key-person dependencies, market positioning) dangerously shallow before transitioning to recommendations.
* **Root Cause:** The orchestrator's missing-information detection or iterative discovery prompts lack strict gating to ensure all six pillars (market, operations, financials, personnel, technology, risk) are genuinely explored before the handoff.
* **Resolution:** Logged as a product/prompt defect. Fix pending in a future cycle.
* **Files Touched:** `docs/DEFECT_LEDGER.md` (this entry only, fix pending).

## [BUG-043] - Date: 2026-08-22 - OPEN
* **Issue:** There is no substantive cross-project memory for a single company. A second project asks foundational questions (e.g., location) already answered in the first project. Additionally, the intake-cleaning step silently drops meta-questions (e.g., "do you remember what I said last time?") before they reach the model.
* **Root Cause:** The orchestration context is scoped purely to the current `SessionState` without hydrating established company facts from a shared profile. The text extraction/cleaning prompt is also overly aggressive in discarding non-workflow conversational text.
* **Resolution:** Logged as a feature/architecture gap. Fix pending in a future cycle.
* **Files Touched:** `docs/DEFECT_LEDGER.md` (this entry only, fix pending).

## [BUG-044] - Date: 2026-08-22 - RESOLVED (Pending Final Verification)
* **Issue:** The Interactive Graph / Flowchart View renders four static, unclickable cards with no connecting lines. The content uses hardcoded, generic SaaS boilerplate (e.g., "LTV:CAC ratio > 3x") that completely contradicts the actual generated session data (e.g., custom woodworking cash jobs).
* **Root Cause:** The UI component for the flowchart view is a static, templated mockup rather than being bound to the dynamically generated `SessionState` or synthesis report.
* **Resolution:** In recent testing (2026-08-22), the Interactive Graph view showed genuinely dynamic, business-specific content (e.g., Torres Auto and Tire's cards referenced actual repair-intake process). This appears to have been resolved, potentially by a recent commit not yet logged or a model shift. Marked as tentatively resolved.
* **Files Touched:** `docs/DEFECT_LEDGER.md` (this entry only).

## [BUG-045] - Date: 2026-08-22 - OPEN
* **Issue:** Project titles in the dashboard list and navigation breadcrumbs are automatically derived from the raw text of the most recent user message (e.g., "Yes, that's exactly right. So...") rather than a summarized topic or business name.
* **Root Cause:** The project naming logic naively uses raw user messages as a display title instead of synthesizing a semantic label for the session.
* **Resolution:** Logged as a UI/data-model defect. Fix pending in a future cycle.
* **Files Touched:** `docs/DEFECT_LEDGER.md` (this entry only, fix pending).

## [BUG-046] - Date: 2026-08-22 - OPEN
* **Issue:** The intake-cleaning step hallucinated "Catering business" as the business category for a flower shop, and only self-corrected after the user explicitly stated "we're a flower shop, not catering".
* **Root Cause:** The orchestrator or LLM extraction step is hallucinating a business category when it should infer from user input or ask for clarification.
* **Resolution:** Logged as a hallucination/prompt defect. Fix pending in a future cycle.
* **Files Touched:** `docs/DEFECT_LEDGER.md` (this entry only, fix pending).

## [BUG-047] - Date: 2026-08-22 - OPEN
* **Issue:** The system exhibits same-session fact amnesia. It re-asked the user "where is your flower shop located?" even after the user explicitly stated Portland, OR in their very first message.
* **Root Cause:** Fact extraction or context management is dropping previously established facts from the current session state.
* **Resolution:** Logged as a memory/context-management defect. Fix pending in a future cycle.
* **Files Touched:** `docs/DEFECT_LEDGER.md` (this entry only, fix pending).

## [BUG-048] - Date: 2026-08-22 - OPEN
* **Issue:** Wrong company binding on new projects. When a new project is created, there's no UI path to specify a new company. The new project attaches to whichever company is currently active (e.g., "Bloom & Petal Florals"). The greeting and top-nav stayed on the old company despite the user describing a completely different business (auto shop), leading to data being filed under the wrong business entity.
* **Root Cause:** The system lacks proper multi-company support in the UI for project creation, and/or defaults to the active company without allowing the user to select or create a new one. The mock auth system might be exacerbating this.
* **Resolution:** Logged as a structural UI/data-model defect. Fix pending in a future cycle.
* **Files Touched:** `docs/DEFECT_LEDGER.md` (this entry only, fix pending).

## [BUG-049] - Date: 2026-08-22 - OPEN
* **Issue:** Message history persistence glitch. An assistant reply vanished entirely from the visible transcript on a later read, resulting in two user messages appearing back-to-back.
* **Root Cause:** Potential issue with how the frontend state syncs with the backend, or how messages are persisted in the database/session storage.
* **Resolution:** Logged as a persistence/UI defect. Fix pending in a future cycle.
* **Files Touched:** `docs/DEFECT_LEDGER.md` (this entry only, fix pending).

## [BUG-050] - Date: 2026-08-22 - OPEN
* **Issue:** The Evidence Ladder audit log attributes claims to a hardcoded label "Staff / Dispatch Manager Employee Stated", even when the business has no dispatch manager and the user explicitly speaks as the owner.
* **Root Cause:** The actor label in the evidence ladder is likely hardcoded rather than dynamically derived from the conversation or persona.
* **Resolution:** Logged as a data-binding/UI defect. Fix pending in a future cycle.
* **Files Touched:** `docs/DEFECT_LEDGER.md` (this entry only, fix pending).

## [BUG-051] - Date: 2026-08-22 - OPEN
* **Issue:** A vague budget statement ("however much it costs is however much, I don't got a real budget for this kind of thing") was initially misread as a customer-pricing philosophy rather than a software-spending constraint.
* **Root Cause:** The extraction prompt is misclassifying ambiguous user statements regarding budget constraints.
* **Resolution:** Logged as an extraction accuracy defect. Fix pending in a future cycle.
* **Files Touched:** `docs/DEFECT_LEDGER.md` (this entry only, fix pending).

## [BUG-050, BUG-046, BUG-047] - Date: 2026-08-22
* **Issue:** 
  - BUG-050: The Evidence Ladder attributes claims to a hardcoded "Staff / Dispatch Manager" even when inapplicable.
  - BUG-046: The `sanitize_input` node hallucinated a business category ("Catering business") for a flower shop.
  - BUG-047: The system exhibits same-session fact amnesia, dropping previously established facts from the conversation history.
* **Root Cause:** 
  - BUG-050: The keyword "stated" incorrectly matched generic owner statements, and the source string was hardcoded to a specific industry role.
  - BUG-046 & BUG-047: The `_node_sanitize_input` LLM prompt instructed the model to output a complete "business logic description," which led it to hallucinate categories to fill gaps and truncate conversational facts (meta-questions, details).
* **Resolution:** 
  - Fixed BUG-050 by removing the keyword "stated" and updating the hardcoded string to a generic "Staff / Employee" in `extract_evidence_ledger_from_messages`.
  - Fixed BUG-046 and BUG-047 by rewriting the `_node_sanitize_input` prompt to strictly forbid dropping factual details, dropping conversational context, and inferring business categories, explicitly scoping it to only strip conversational filler.
* **Files Touched:** `apps/api/app/core/orchestrator.py`

## Persona Testing Session (India Scenarios) - Date: 2026-08-22

Three India-context SMB personas were run end-to-end against the live local app (`127.0.0.1:8001` / `localhost:3000`) to re-verify the BUG-050/046/047 fix and re-probe all previously logged open bugs. Personas: (1) Priya Deshmukh, Deshmukh Textiles & Sarees, Nagpur, Maharashtra (Wholesale & Distribution); (2) Arjun Reddy, Reddy AutoCare Multi-Brand Garage, Hyderabad, Telangana (Automotive Repair, two projects under one company); (3) Kavita Nair, Nair Homestays & Spice Farm Tours, Wayanad, Kerala — blocked before intake by the CHANGE-005 rate limiter after the heavy multi-company/multi-project load generated by personas 1-2, and not completed this session.

### [BUG-050, BUG-046, BUG-047] - Re-Verification: Date: 2026-08-22 - PARTIALLY CONFIRMED FIXED
* **Issue:** Re-tested the fix from the entry above using two independent India personas.
* **Result:** The core fixes hold for genuine factual content: the Evidence Ladder no longer shows the hardcoded "Staff / Dispatch Manager" label (generic "Staff / Employee" / "Owner Estimate" now appear), and specific stated facts (location, family-member involvement, staffing counts, an ambiguous budget statement) were carried through faithfully turn-to-turn within a session in most turns. However, see BUG-052 below for a new, more severe fabrication failure mode discovered specifically on user meta-questions, which BUG-047's fix did not fully anticipate.
* **Files Touched:** `docs/DEFECT_LEDGER.md` (this entry only).

## [BUG-052] - Date: 2026-08-22 - OPEN - CRITICAL
* **Issue:** `_node_sanitize_input` does not just silently drop user meta-questions (the previously known BUG-043 behavior) — in at least one reproduction it fabricated a false answer to the user's meta-question and inserted it into the "USER INPUT" bubble as if the user had said it. Persona 2 (Arjun) typed: "...quick one - do you remember anything about my business already, or is this our first conversation?" The sanitized bubble shown to the user, and sent to the model as the user's own words, read: "...This is our first conversation - I have no prior context about your business." That sentence was never said by the user; it is the sanitizer inventing and attributing an assistant-perspective answer to the user. In a second occurrence later in the same persona's second project, the same category of question ("do you remember what we already discussed... or do I need to re-explain...") was instead preserved verbatim (not fabricated) — so the failure is intermittent, not deterministic.
* **Root Cause:** The `_node_sanitize_input` prompt (rewritten for BUG-046/047) still allows the model to "resolve" a conversational meta-question rather than passing it through unchanged, and it has no hard constraint against generating first-person, user-voiced content that the user never typed.
* **Resolution:** Not fixed. Logged as a critical prompt-safety defect: fabricating words in the user's own input bubble is materially worse than the original silent-drop behavior, since it misrepresents the record of what the user actually said and could mask real cross-session memory gaps from the user.
* **Files Touched:** `docs/DEFECT_LEDGER.md` (this entry only, fix pending).

## [BUG-053] - Date: 2026-08-22 - OPEN - CRITICAL
* **Issue:** Raw internal orchestration artifacts leak directly into the customer-facing Evidence Ladder Audit Log table (Deep Dive tab), appearing as literal "Stated Claim / Bottleneck" row content. Observed content includes: full base64-encoded extended-thinking signature blobs (`{"type": "thinking", "thinking": "", "signature": "Eug..."}`), raw `tool_use` JSON payloads (`market_signal`, `web_search`, `parse_sop_workflow`, `calculate_unit_economics` calls with their full input objects), and complete `<untrusted_tool_output source="web_search">...</untrusted_tool_output>` wrapper blocks (correctly wrapped per the PRD's prompt-injection guardrail internally, but that wrapped raw content is then displayed verbatim to the end user instead of being summarized). This reproduced independently and identically in two separate personas/sessions (Priya's session and Arjun's session), confirming it is a systemic defect, not a one-off glitch.
* **Root Cause:** `extract_evidence_ladder_from_messages` (or its caller) appears to be pulling directly from raw `state["messages"]` content — including assistant `tool_use`/`thinking` blocks and tool-result messages — without filtering to only human-readable claim text before rendering rows in the Evidence Ladder UI.
* **Resolution:** Not fixed. This is the most severe UX/security-adjacent finding of this session: end users are shown multi-kilobyte unreadable blobs (including cryptographic-looking signature data) in a report section meant to build trust via transparent, readable sourcing. It also risks leaking tool-call query strings and other internal implementation detail to the customer.
* **Files Touched:** `docs/DEFECT_LEDGER.md` (this entry only, fix pending).

## [BUG-054] - Date: 2026-08-22 - OPEN
* **Issue:** The Execution Dossier header shows "Vertical Focus: GENERIC" even when the active company was created with a specific, non-generic Industry Vertical (e.g., "Automotive Repair & Vehicle Servicing" for Reddy AutoCare, "Wholesale & Distribution" for Deshmukh Textiles). Reproduced independently across two personas/companies.
* **Root Cause:** Likely the synthesis/dossier-header rendering path reads vertical from a different field than the one populated by company creation (e.g., defaults to a generic enum value instead of reading `company.industry_vertical`).
* **Resolution:** Not fixed. Logged as a data-binding defect.
* **Files Touched:** `docs/DEFECT_LEDGER.md` (this entry only, fix pending).

## [BUG-045] - Re-Verification: Date: 2026-08-22 - OPEN (confirmed, expanded scope)
* **Issue:** Confirmed still fully open across three new raw-title variants in this session's personas. New finding: the SAME project shows two DIFFERENT raw/derived titles depending on where it's viewed — the project page header for Arjun's first project read "I'm Arjun Reddy, I run Reddy A...", while that same project's card on the company dashboard read "GENERIC - Mechanic discovers a wor...". Neither is a semantic summary; they are two different naive derivations from raw chat content, inconsistent with each other.
* **Root Cause:** (unchanged) raw message text used as title source; new evidence suggests two independent, non-agreeing naive-title code paths exist (one for the project header, one for the dashboard card).
* **Resolution:** Not fixed. Fix pending.
* **Files Touched:** `docs/DEFECT_LEDGER.md` (this entry only, fix pending).

## [BUG-043] - Re-Verification: Date: 2026-08-22 - OPEN (definitively confirmed)
* **Issue:** Created a second project under the same company (Reddy AutoCare) and, after the assistant's first reply, explicitly asked: "do you remember what we already discussed in my other project about the parts sourcing problem, or do I need to re-explain my shop's location and setup from scratch?" The assistant replied: "I don't have access to your previous project details, so I'd appreciate a quick refresh: where is Reddy AutoCare located?" — a direct, explicit admission of zero cross-project memory, and an immediate re-ask of a fact (location) already established in the first project. This is an unambiguous reproduction of the exact BS-3 acceptance-criteria failure.
* **Root Cause:** (unchanged) no company-profile hydration into new session context.
* **Resolution:** Not fixed. Fix pending.
* **Files Touched:** `docs/DEFECT_LEDGER.md` (this entry only, fix pending).

## [BUG-055] - Date: 2026-08-22 - OPEN
* **Issue:** Markdown syntax renders as literal, unstyled text in both the Quick Insights and Deep Dive report views instead of being parsed into HTML. Observed literal `**bold**` asterisks and `### Header` hashes throughout the "Friction Analysis," "Technology Neutral Recommendations," "Current Manual Process (As-Is)," and "ROI Economics" sections, confirmed visually via screenshot (not just text extraction).
* **Root Cause:** The report-rendering component is likely outputting the LLM's raw markdown string directly into the DOM without passing it through a markdown-to-HTML renderer (e.g., missing a `react-markdown`-style component).
* **Resolution:** Not fixed. Logged as a rendering defect.
* **Files Touched:** `docs/DEFECT_LEDGER.md` (this entry only, fix pending).

## [BUG-056] - Date: 2026-08-22 - OPEN
* **Issue:** The mock `market_signal` and `web_search` tools return near-identical, generic SaaS-industry boilerplate (HackerNews/Reddit posts about billing reminder apps, Calendly/Zapier pricing, "Tomasz Tunguz SaaS Benchmarks" ARPU/CAC/LTV figures) regardless of the actual query content. Two clearly distinct queries in the same session — "auto repair garage parts inventory bottleneck single person access spreadsheet" and "auto repair garage parts stockout delays mechanic workflow frustration" — returned structurally near-identical, topically irrelevant canned results (one set even referenced VAT/GST tax-billing SaaS tools, wholly unrelated to an auto garage's parts-sourcing problem). This contaminates downstream synthesis with irrelevant market signal.
* **Root Cause:** The simulated/mock tool implementations for `market_signal` and `web_search` appear to return static or near-static canned responses rather than genuinely varying by query.
* **Resolution:** Not fixed. Logged as a mock-tool-fidelity defect; low severity in isolation but compounds into BUG-057 below.
* **Files Touched:** `docs/DEFECT_LEDGER.md` (this entry only, fix pending).

## [BUG-057] - Date: 2026-08-22 - OPEN
* **Issue:** `calculate_unit_economics` was invoked during synthesis for a brick-and-mortar auto repair garage using SaaS-subscription-style inputs (`ltv: 40800, cac: 1000, average_revenue_per_customer: 3400, gross_margin_percent: 100`) derived from the generic canned "SaaS Benchmarks" data in BUG-056, producing a nonsensical `"ltv_cac_ratio": 40.8` / `"payback_months": 0.29` for a business with no recurring "customer acquisition" funnel or subscription revenue. To the synthesizer's credit, this specific raw output was NOT surfaced verbatim to the user — the final Deep Dive report reasonably reframed cost/benefit in plain rupee terms (₹0 implementation cost, "payback period is effectively immediate") rather than quoting the LTV:CAC figure directly — so user-facing harm was mitigated in this instance, but the underlying calculation is still conceptually mismatched to the business type and could surface directly in other runs.
* **Root Cause:** The economics/ROI tool step is applying a SaaS unit-economics framework (LTV:CAC, payback period against a recurring subscription) uncritically to a one-time-transaction local service business, compounded by BUG-056's irrelevant benchmark data being fed in as if authoritative.
* **Resolution:** Not fixed. Logged as a tool-applicability/prompt defect.
* **Files Touched:** `docs/DEFECT_LEDGER.md` (this entry only, fix pending).

## [BUG-058] - Date: 2026-08-22 - OPEN - UX
* **Issue:** Explicit, repeated user requests to skip ahead and generate the report immediately (e.g., "Can you go ahead and generate the report now based on what I've told you?", later "Please go ahead and generate the full report now.") are not honored on the first ask. Instead the orchestrator performs one additional recap/confirmation turn ("Does that capture it accurately, or is there anything I should adjust?") before synthesizing — observed consistently across two personas. This may be an intentional design step, but there is no faster explicit override, and the header "Run Analysis" button does not force synthesis either (it re-enters routing and can re-trigger more discovery questions rather than jumping straight to the report).
* **Root Cause:** The routing/gating logic treats "generate the report now" as a normal turn subject to standard discovery-completeness gating (per the BUG-042 fix) rather than as an explicit synthesis-override signal, and no chat-based fast path to force synthesis exists.
* **Resolution:** Not fixed. Logged as a UX-friction finding; may be intentional but should be confirmed with product intent, and a documented override (e.g., "confirm and generate" quick-reply) would reduce friction for time-pressed SMB users.
* **Files Touched:** `docs/DEFECT_LEDGER.md` (this entry only, fix pending).

## [BUG-059] - Date: 2026-08-22 - OPEN - Minor
* **Issue:** The "Industry Vertical" field is a fixed set of ~4 preset options during the initial company-onboarding flow, but becomes an unconstrained free-text field ("e.g. E-commerce, Real Estate") in the separate "Create New Company" modal reached via the dashboard's company switcher. The two entry points for the same underlying field behave inconsistently.
* **Root Cause:** Two independent UI implementations of company creation (initial onboarding vs. "Create New Company" modal) were built without sharing a common form/validation component.
* **Resolution:** Not fixed. Logged as a minor UI-consistency defect.
* **Files Touched:** `docs/DEFECT_LEDGER.md` (this entry only, fix pending).

## Operational Note - Date: 2026-08-22
* **Observation:** The CHANGE-005 rate limiter (`redis_client.check_ip_rate_limit`, max 3 new-session/new-company creations per day per IP without BYOK) functioned as designed and blocked further workspace creation ("Workspace creation error: Too Many Requests") after this session's rapid creation of 2 companies and 3 projects for persona testing. The limiter did not visibly reset within roughly 2 minutes of waiting, preventing Persona 3 (Kavita Nair, Wayanad homestay) from being run to completion this session — her company was created successfully, but the first intake message could not be submitted. Not logged as a bug (the guardrail is working as intended per PRD Section 7), but noted so a future testing session knows to pace project/company creation across a longer wall-clock window, or use a BYOK key, to complete the full persona suite in one sitting.

## Fix Re-Verification Session - Date: 2026-08-22 (same day, later)

A second pass was run the same day against a live local rebuild that had picked up code changes to `apps/api/app/core/orchestrator.py` and `apps/api/app/main.py` (confirmed via direct source inspection, not assumption). Source-level inspection showed genuine, targeted fixes present for BUG-052, BUG-053, BUG-054, and BUG-043, and a partial fix candidate for BUG-045. Live re-verification in the running app was attempted for all five.

**Canary result:** Persona 3 (Kavita Nair) intake was attempted first specifically to probe rate-limiter state. It was blocked again with "Workspace creation error: Too Many Requests" — confirming the CHANGE-005 daily counter (keyed per-IP per UTC-calendar-day, `time_window_seconds=86400`, checked only in the `POST /api/v1/orchestrate` new-session branch) had not reset since the original testing session earlier the same day, and would not reset until UTC midnight. Because the rate limiter only gates *new* session/company creation (an existing `session_id` bypasses it entirely, confirmed by reading `main.py` lines ~392-411), re-verification pivoted to reusing Arjun Reddy's existing first project (session `869a81ff-8ff4-4b9f-977f-1664ba9b5b74`) by sending new chat turns into it, which triggers a full synthesizer re-run without counting against the limiter.

### [BUG-052] - Re-Verification: Date: 2026-08-22 - RESOLVED
* **Issue:** (see original entry above) Sanitizer fabricated a false answer to a user meta-question and inserted it into the "USER INPUT" bubble as if the user had said it.
* **Verification method:** Sent a new message into Arjun's existing project, worded as a meta-question almost identical in spirit to the original repro: *"Quick check before we wrap up - do you actually remember any of what I told you earlier in this conversation, like my location and the parts problem, or would you need me to repeat it?"*
* **Result:** The sanitized USER INPUT bubble read: *"Quick check before we wrap up - do you actually remember any of what I told you earlier in this conversation, my location and the parts problem, or would you need me to repeat it?"* — identical to the original except the filler word "like" was stripped, which is exactly the sanitizer's intended job per the rewritten prompt ("ONLY strip conversational filler e.g., um, uh, like"). No fabricated answer, no invented first-person content, no truncation of the question itself. Confirmed fixed.
* **Files Touched:** `apps/api/app/core/orchestrator.py` (`_node_sanitize_input` prompt, read and confirmed at lines ~1565-1576 — added explicit "DO NOT resolve or answer user questions or meta-questions" / "DO NOT generate first-person user statements or hallucinate conversational responses" constraints).

### [BUG-053] - Re-Verification: Date: 2026-08-22 - RESOLVED
* **Issue:** (see original entry above) Raw internal orchestration artifacts (base64 thinking-signature blobs, `tool_use` JSON payloads, `<untrusted_tool_output>` wrapper blocks) leaked directly into the customer-facing Evidence Ladder Audit Log.
* **Verification method:** First confirmed the Evidence Ladder section is legitimately absent (not broken) when no user message matches an Evidence Ladder trigger keyword, ruling out stale cached data. Then sent a new message into the same project deliberately containing a trigger keyword: *"One more data point for the record - my rough estimate is we lose about 2 vehicle-days a month to these parts delays. That's just my gut estimate though, not something I've tracked on paper."*
* **Result:** The Deep Dive tab's Evidence Ladder Audit Log rendered exactly one row: the claim text verbatim as quoted above, Stated Source "Owner Estimate," Reliability Level "Owner Estimate." No raw JSON, no base64 signature data, no `tool_use` payloads, no `untrusted_tool_output` wrapper text anywhere on the page. Confirmed fixed.
* **Files Touched:** `apps/api/app/core/orchestrator.py` (`extract_evidence_ledger_from_messages`, read and confirmed at lines ~224-257 — now filters to `role in ("user", "human")` / string `content` only before keyword-matching, excluding assistant `tool_use`/`thinking` blocks entirely).

### [BUG-054] - Re-Verification: Date: 2026-08-22 - FIX PRESENT, NOT YET RE-VERIFIED LIVE (blocked)
* **Issue:** (see original entry above) Execution Dossier header shows "Vertical Focus: GENERIC" regardless of the company's actual Industry Vertical.
* **Status:** Source inspection of `main.py` (~lines 433-451) shows the vertical-mapping `if/elif` chain now falls through to the raw `user_vertical` string instead of defaulting to `"GENERIC"` when no keyword bucket matches — a plausible fix. However, this logic only runs in the `POST /api/v1/orchestrate` branch that creates a **new** project/session; re-running an existing project (as used above for BUG-052/053) does not touch it, and Arjun's existing project still correctly shows "GENERIC" (its stored, pre-fix value) after the re-run. Live confirmation requires creating a **new** project, which is blocked by the still-active CHANGE-005 rate limiter (see canary result above). Not yet re-verified in-app.

### [BUG-045] - Re-Verification: Date: 2026-08-22 - PARTIAL FIX PRESENT, NOT YET RE-VERIFIED LIVE (blocked)
* **Issue:** (see original entry above) Same project shows two different raw/non-matching titles in different views.
* **Status:** Source inspection shows `_generate_semantic_title()` is now a single shared function called from both code paths (project-header title at creation, line ~257, and fallback title at line ~415), which should at minimum make the two views agree. However, the heuristic itself is still regex/trigger-phrase-based (strips leading phrases like "I want to" / "can you" / "help me" and appends " Workflow"), not true semantic summarization — so a persona opening message that doesn't happen to contain a trigger phrase could still produce a raw-looking title. This only runs at new-project creation, so live confirmation is blocked by the same rate limiter as BUG-054. Not yet re-verified in-app.

### [BUG-043] - Re-Verification: Date: 2026-08-22 - FIX PRESENT, NOT YET RE-VERIFIED LIVE (blocked)
* **Issue:** (see original entry above) A second project under the same company has zero awareness of facts established in a sibling project.
* **Status:** Source inspection of `main.py` (~lines 486-535) shows a genuine, real implementation added: on new-project creation under an existing company, the code now looks up the user's other projects under that `company_id`, pulls each prior project's stored `process_components` (location, system), and assembles a `company_context` string that is written into the new session's `metadata`, presumably intended to be surfaced to the model. This directly targets the exact reproduction from the original entry (a second Reddy AutoCare project not knowing the first project's location). However, this only runs at new-project creation, so live confirmation (creating a third project under Reddy AutoCare or Deshmukh Textiles and checking whether it now avoids re-asking for location) is blocked by the same rate limiter. Not yet re-verified in-app; also unconfirmed whether `company_context` is actually consumed anywhere downstream (e.g., injected into the assistant's system/context) versus merely stored and unused — this should be checked alongside the live re-test.

### [BUG-055] - Incidental observation: Date: 2026-08-22 - POSSIBLY FIXED, NOT DELIBERATELY RE-TESTED
* **Issue:** (see original entry above) Markdown syntax (`**bold**`, `### Header`) rendered as literal unstyled text.
* **Observation:** Not part of this session's targeted re-test list, but incidentally, both re-run reports on Arjun's project rendered **bold** text and *italic* text correctly as styled HTML in the Deep Dive tab (screenshot-confirmed), where the underlying LLM response (checked via the telemetry dashboard's raw JSON) did contain literal `**...**` markdown syntax. This suggests a markdown renderer may now be in place, but no deliberate test of header syntax (`###`) or other markdown constructs was performed, and no code was inspected for this specific bug. Flagged for a real re-test in the next session rather than marked resolved.

**Unresolved this pass:** BUG-054, BUG-045, BUG-043 have plausible/genuine fixes in source but could not be exercised live because verifying them requires creating a new project/session, and the CHANGE-005 rate limiter (reset at UTC midnight, per-IP, per-calendar-day) was already exhausted by this session's own testing activity before the fixes could be re-tested. Persona 3 (Kavita Nair) intake remains incomplete for the same reason. Recommended next step: either wait for the UTC-midnight reset and re-run the three blocked checks plus complete Kavita's persona, or supply a BYOK (`x-user-anthropic-key`) key for this testing session to bypass the limiter entirely.

### [BUG-056] - 2026-08-24 - OPEN
* **Issue:** The first Step 1 resilience test showed that free-form provider exception text containing a key-like value (for example, `secret-key=sk-test`) was not redacted by the generic telemetry sanitizer.
* **Impact:** Persisting the raw exception reason could expose a credential-like substring in operational telemetry.
* **Remediation:** Add explicit key-like token redaction in the bounded LLM error-reason helper and retain a regression assertion before retrying the checkpoint.
