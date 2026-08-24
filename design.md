# BuildSense Reliability and Persona-Run Remediation Design

## 1. Design Goals

Implement the approved `spec.md` with explicit failure semantics. Runtime failures that affect facts, routing, billing, persistence, or report validity will be represented in state and telemetry; intentional product fallbacks will remain available only when their degraded nature is explicit. The design keeps the existing FastAPI, LangGraph, Anthropic telemetry, Pydantic, Next.js, and generated-agent-rule patterns.

## 2. Cross-Cutting Decisions

### 2.1 Failure contract

Every external boundary will classify failures into one of three outcomes:

1. Recoverable and safe: return a documented local fallback, emit structured warning telemetry, and mark the relevant capability as degraded.
2. User-actionable: return a typed/domain failure with a safe user-facing message and preserve the session for retry where possible.
3. Integrity-critical: mark the session failed, stop report generation, emit error telemetry with node and reason, and do not synthesize a healthy-looking result.

No handler may use `pass` or discard an exception when the operation influences extracted facts, routing, safety, spend, persistence, or report validity.

### 2.2 State and telemetry

Use the existing `SessionState`/`AgentState` metadata and telemetry conventions. Add narrowly scoped fields only when metadata is insufficient. Failure metadata must identify the node, category, retryability, and sanitized reason; it must never include API keys or raw provider payloads.

### 2.3 Dependency compatibility

Pin the Anthropic SDK to the version validated by the repository and add a mocked contract test that detects unsupported `messages.create()` keyword arguments without making a network call. A live provider smoke check remains separately gated and is not required for ordinary CI.

### 2.4 Documentation synchronization

`AGENTS.md` remains the source of truth. Add the mandatory error-handling policy there, then regenerate `CLAUDE.md` and `.cursorrules` with `scripts/sync_agent_rules.py`. Do not hand-edit generated mirrors.

### 2.5 Prompt-cache boundary

Construct Anthropic requests from a deterministic reusable prefix and a request-specific suffix. The prefix will contain versioned system instructions, tool definitions, and response-schema material, ending at an explicit cache breakpoint. Session content, timestamps, request identifiers, mutable counters, and other per-request values will remain outside that boundary. Cache usage will be recorded from provider response metadata without treating missing fields as zero.

### 2.6 Adaptive diagnostic and contingency gate

Represent diagnostic coverage as explicit state rather than inferring completion from the five workflow slots alone. The intake planner will identify missing dimensions and material risk signals, then select one context-specific follow-up at a time. A risk signal can indicate a dependency on a person, system, supplier, process, cash position, demand pattern, or another domain-relevant condition; the implementation must not encode a single fixed key-person question.

For a material contingency signal, the follow-up evidence will capture the scenario, expected impact, current workaround, response owner, and whether the workaround is documented. Synthesis may proceed only when the required coverage is satisfied or an explicit skip decision and user-visible report limitation are recorded. A message that combines confirmation/correction with consequential human-impact information will first produce an acknowledgment event before the planner advances or synthesis begins.

## 3. Data Flow

```text
provider/tool/database failure
        |
        v
typed boundary result + sanitized telemetry
        |
        +--> recoverable: explicit degraded metadata and documented fallback
        |
        +--> user-actionable: safe error event, session retained for retry
        |
        +--> integrity-critical: FAILED state, no healthy report
```

The frontend consumes the existing SSE state stream. It will render the backend's explicit error/degraded state and retain the connection error path for transport failures.

## 4. Atomic Implementation Steps

Each step is intentionally limited to four or fewer source files in context. Documentation and test-only files are listed explicitly so the implementation can be reviewed and micro-committed independently.

### Step 1: Define failure metadata and boundary helpers

Read:

- `apps/api/app/models/state.py`
- `apps/api/app/telemetry/llm.py`
- `apps/api/app/telemetry/logging.py`
- `apps/api/tests/test_resilience.py`

Modify:

- `apps/api/app/models/state.py`
- `apps/api/app/telemetry/llm.py`
- `apps/api/app/telemetry/logging.py`
- `apps/api/tests/test_resilience.py`

Add typed failure/degraded metadata conventions and tests for sanitized provider-error telemetry. Preserve existing cost and privacy behavior.

### Step 2: Pin and verify the Anthropic SDK contract

Read:

- `apps/api/requirements.txt`
- `apps/api/pyproject.toml`
- `apps/api/app/telemetry/llm.py`

Modify:

- `apps/api/requirements.txt`
- `apps/api/pyproject.toml`
- `apps/api/tests/test_anthropic_compatibility.py`

Pin the SDK to the tested compatible range and add a deterministic mocked `messages.create()` contract test that fails loudly for unsupported arguments such as `temperature`.

### Step 3: Make intake model failures explicit

Read:

- `apps/api/app/core/orchestrator.py`
- `apps/api/app/models/state.py`
- `apps/api/app/telemetry/llm.py`
- `apps/api/tests/test_resilience.py`

Modify:

- `apps/api/app/core/orchestrator.py`
- `apps/api/app/models/state.py`
- `apps/api/app/telemetry/llm.py`
- `apps/api/tests/test_resilience.py`

Replace silent catches around sanitization, process extraction, clarification generation, confirmation classification, and required synthesis calls with typed handling. Intentional question fallbacks must carry explicit degraded metadata; integrity-critical extraction/synthesis failures must prevent a healthy-looking report.

### Step 4: Repair evidence, playback, constraints, and adaptive contingency capture

Read:

- `apps/api/app/core/orchestrator.py`
- `apps/api/app/core/prompts.py`
- `apps/api/app/models/state.py`
- `apps/api/tests/test_interview.py`

Modify:

- `apps/api/app/core/orchestrator.py`
- `apps/api/app/core/prompts.py`
- `apps/api/app/models/state.py`
- `apps/api/tests/test_interview.py`

Replace the eight-word evidence trigger with ordinary-claim extraction and provenance, reconcile playback flag transitions and persistence, preserve the user's original voice during sanitization, and require budget/technology-comfort capture before paid recommendations.

Add risk-signal and coverage tracking that selects context-relevant contingency questions, records scenario/impact/workaround/owner/documentation evidence, and prevents report completion when a material failure mode is neither explored nor explicitly skipped. Add a pre-synthesis acknowledgment path for consequential disclosures bundled with confirmation or correction.

### Step 5: Add synthesis citation, recommendation, and completion guardrails

Read:

- `apps/api/app/core/orchestrator.py`
- `apps/api/app/core/prompts.py`
- `apps/api/tests/test_eval_guardrails.py`

Modify:

- `apps/api/app/core/orchestrator.py`
- `apps/api/app/core/prompts.py`
- `apps/api/tests/test_eval_guardrails.py`

Require current-session tool evidence for named studies, reports, indexes, or citations. Add deterministic guardrail tests for unsupported named citations, including correction-triggered re-synthesis; paid recommendations when constraints are missing; incomplete pillar/contingency coverage; and missing acknowledgment turns before synthesis.

### Step 6: Harden API, audio, MCP, and infrastructure boundaries

Read:

- `apps/api/app/main.py`
- `apps/api/app/core/audio.py`
- `apps/api/app/mcp/tools.py`
- `apps/api/app/db/redis.py`

Modify:

- `apps/api/app/main.py`
- `apps/api/app/core/audio.py`
- `apps/api/app/mcp/tools.py`
- `apps/api/app/db/redis.py`

Audit and revise broad handlers so HTTP routes, transcription, MCP/tool execution, and Redis degradation produce typed responses or explicit structured degraded signals. Keep intentional offline mocks, but identify them clearly and do not hide integrity failures.

### Step 7: Harden remaining persistence and database boundaries

Read:

- `apps/api/app/db/postgres.py`
- `apps/api/app/telemetry/middleware.py`
- `apps/api/app/telemetry/dev_routes.py`
- `apps/api/tests/test_db.py`

Modify:

- `apps/api/app/db/postgres.py`
- `apps/api/app/telemetry/middleware.py`
- `apps/api/app/telemetry/dev_routes.py`
- `apps/api/tests/test_db.py`

Ensure save/load and middleware failures are classified consistently, persistence failures cannot silently discard session state, and development-only route errors remain safe and observable.

### Step 8: Make frontend transport and integration failures actionable

Read:

- `apps/web/src/lib/useOrchestratorStream.ts`
- `apps/web/src/lib/api.ts`
- `apps/web/src/components/auth-provider.tsx`
- `apps/web/src/lib/supabase.ts`

Modify:

- `apps/web/src/lib/useOrchestratorStream.ts`
- `apps/web/src/lib/api.ts`
- `apps/web/src/components/auth-provider.tsx`
- `apps/web/src/lib/supabase.ts`

Preserve the existing SSE parser while distinguishing malformed events, backend failed/degraded states, transport errors, and local-storage/auth failures. Replace unsafe `any` error handling with `unknown` narrowing where touched and avoid leaking secrets in logs.

### Step 9: Add static error-handling audit and synchronized agent policy

Read:

- `AGENTS.md`
- `scripts/sync_agent_rules.py`
- `scripts/check_phase_gate.py`
- `scripts/tests/test_check_phase_gate.py`

Modify:

- `AGENTS.md`
- `scripts/tests/test_check_phase_gate.py`
- `scripts/tests/test_error_handling_policy.py`
- `docs/DEFECT_LEDGER.md`

Add mandatory rules stating where catches are required, when fallbacks are allowed, and that silent swallowing is prohibited. Add a focused static policy test for production `pass`/empty exception handlers and document the architectural reasoning/defect entries.

Generated after this step, using the existing script rather than manual edits:

- `CLAUDE.md`
- `.cursorrules`

### Step 10: Validation and checkpoint artifacts

Read:

- `apps/api/pyproject.toml`
- `apps/web/package.json`
- `docs/DEFECT_LEDGER.md`
- `AGENTS.md`

Modify only when required by validation findings:

- `docs/DEFECT_LEDGER.md`
- `docs/RunAndTest.md`

Run targeted tests after each prior step, then backend tests/type checks, frontend type-check/lint, the phase-gate checks, and applicable evals. Record any failed-test defect before retrying a checkpoint. Produce the required test-results and code-diff artifacts before final completion.

### Step 11: Improve Anthropic prompt-cache reuse and savings telemetry

Read:

- `apps/api/app/telemetry/llm.py`
- `apps/api/app/core/orchestrator.py`
- `apps/api/app/models/state.py`
- `apps/api/tests/test_resilience.py`

Modify:

- `apps/api/app/telemetry/llm.py`
- `apps/api/app/core/orchestrator.py`
- `apps/api/app/models/state.py`
- `apps/api/tests/test_resilience.py`

Introduce a deterministic cache-prefix builder and request assembly boundary for eligible Anthropic calls. Add explicit cache-control metadata at the stable-prefix breakpoint, keep session-specific content in the uncached suffix, and version the prefix based on prompt/tool/schema configuration. Extend sanitized LLM usage telemetry with cache creation tokens, cache read tokens, and estimated savings while preserving unknown values when the provider omits usage fields. Add focused tests that compare equivalent requests byte-for-byte, detect dynamic or nondeterministically ordered prefix content, verify intentional version invalidation, and confirm that cache misses do not alter correctness or trigger cache-chasing retries.

## 5. Verification Matrix

| Requirement | Verification |
|---|---|
| No silent critical catches | Static policy test plus focused exception-path tests |
| SDK compatibility | Mocked `messages.create()` contract test and dependency inspection |
| Visible intake failure | Resilience tests asserting failed/degraded state and metadata |
| Evidence Ledger recall | Interview tests using ordinary Kochi persona statements |
| Citation grounding | Prompt/guardrail tests with and without tool evidence |
| Playback persistence | State save/load and multi-turn interview tests |
| Voice preservation | Sanitization tests comparing factual and stylistic content |
| Paid recommendation constraints | Interview/synthesis tests with missing and supplied budget answers |
| Adaptive contingency probing | Risk-signal fixtures covering person, system, supplier, and process dependencies; assert structured evidence and completion gating |
| Consequential disclosure acknowledgment | Mixed confirmation/disclosure interview fixture asserting acknowledgment precedes synthesis |
| Prompt-cache reuse and savings | Deterministic request-fixture tests, explicit cache breakpoint assertions, and cache usage telemetry tests |
| Frontend handling | `npm run type-check`, `npm run lint`, and SSE integration verification |
| Rule synchronization | `python scripts/sync_agent_rules.py --check` |

## 6. Risks and Mitigations

- Existing user changes overlap with `design.md`, tests, and documentation. Inspect and preserve them before each edit; stage only files belonging to the current atomic step.
- Some current fallback tests may encode silent behavior. Update them to assert explicit degraded metadata rather than removing intentional product fallbacks.
- A live provider smoke test can be flaky and can spend money. Keep the default contract test offline and document live validation as separately gated.
- The repository requires Phase 3 in a fresh chat. After design approval, verify both checkpoint commits and approval notes, then stop for the user to open a new task before source edits.

## 7. Phase 3 Continuation Addendum — 2026-08-24

The remaining implementation continues with the atomic steps already defined
in Section 4. Step 2’s dependency and offline contract test are prepared but
must be committed after this refreshed design checkpoint. Steps 3–11 then
proceed in order, with no more than four source files in context per step,
targeted validation before each micro-commit, and defect-ledger entries before
retrying any failed checkpoint. Existing unrelated persona-report and cycle
artifacts remain outside the implementation commits.
