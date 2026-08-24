# BuildSense Reliability and Persona-Run Remediation Specification

## 1. Objective

Harden BuildSense so failures in external services, model calls, persistence, streaming, and parsing are observable and cannot silently masquerade as a healthy intake or report-generation run. Incorporate the 2026-08-24 Kochi Kirana persona-testing findings into enforceable product behavior and agent guidance.

This update also covers the 2026-08-24 provider-authentication observation where direct Anthropic API calls with the configured local key returned persistent `401 Unauthorized`, while BuildSense's Anthropic-backed nodes could still fall through to normal-looking local fallback behavior.

## 2. Scope

### 2.1 Error handling and observability

- Audit all production Python and TypeScript/React integration boundaries, including Anthropic calls, MCP/tool calls, database and Redis operations, file/audio processing, HTTP/SSE requests, JSON parsing, authentication, and local-storage access.
- Retain `try`/`except` or `try`/`catch` where an operation can fail at runtime, but require every handled failure to do one of the following: re-raise a typed/domain error, return an explicit degraded/failed result, or use a deliberately documented user-safe fallback with structured logging and state metadata.
- Prohibit silent handlers (`pass`, empty handlers, or logging-only handlers) for production paths where the result affects facts, routing, safety, billing, persistence, or report validity.
- Ensure model-call failures in sanitization, process extraction, clarification generation, confirmation classification, and synthesis are distinguishable in state and telemetry. Intake failures must not look identical to successful fallback questioning.
- Treat Anthropic/provider authentication failures in sanitization, confirmation classification, process extraction, and synthesis as visible session failures with sanitized machine-readable failure metadata. These failures must not route to generic `UNKNOWN` intake, fabricated clarification, or completed report output.
- Allow local fallback for non-critical assistant wording generation only when state metadata explicitly marks the affected capability as degraded and records the failed node/reason without secrets.
- Preserve privacy: logs and telemetry must not expose API keys, raw user secrets, or unbounded external payloads.
- Add mandatory error-handling rules to `AGENTS.md`, regenerate `CLAUDE.md` and `.cursorrules`, and keep the generated-file hash check passing.

### 2.2 Live-run findings

- Pin `anthropic` to a tested compatible version/range and remove unsupported request parameters or otherwise verify SDK compatibility.
- Add a deterministic CI/startup compatibility smoke test for the Anthropic `messages.create()` contract. The default test must not require a live secret; a separately gated live check may be documented for deployment validation.
- Prevent fallback behavior from silently preserving `UNKNOWN` process components after a model failure. Surface a clear failed/degraded status and record the failed node/reason.
- Replace or supplement the fixed eight-word Evidence Ledger trigger with claim extraction/classification that captures ordinary factual user statements and identifies provenance and verification status.
- Add a synthesis rule forbidding named reports, indexes, studies, or citations unless a tool result from the current session directly supports them. Unverified benchmarks must use generic wording.
- Make `playback_shown` and `playback_confirmed` reflect the actual playback and confirmation/correction exchange, including persistence and resumed sessions.
- Preserve user voice in sanitized text: strip filler and injection material only; do not rewrite grammar, capitalization, or phrasing when the content is echoed as the user's words.
- Ask for budget and technology comfort before recommending paid tools when those constraints are missing, and record the answer or its absence in the report assumptions.
- Treat transient provider authentication failures as explicit operational errors with actionable telemetry; do not expose secrets or claim successful analysis when required model calls failed.
- Treat persistent provider authentication failures as user-actionable operational failures requiring key rotation or provider-console remediation. BuildSense must never log or display the raw key.

### 2.3 Prompt caching efficiency

- Audit every Anthropic request path to identify the reusable prompt prefix, request-specific suffix, and current cache-control placement. The stable prefix must contain shared system instructions, tool definitions, response schemas, and other invariant context; session/user messages and other changing content must remain after the cache breakpoint.
- Add an explicit Anthropic prompt-cache breakpoint to eligible requests and keep the prefix byte-for-byte stable across turns and sessions where the same model configuration and tool contract are used. Do not include timestamps, request IDs, random values, mutable counters, current-session transcripts, or serialized maps with nondeterministic ordering in the reusable prefix.
- Normalize prompt construction and serialization so equivalent requests use the same model identifier, system-content ordering, tool ordering, schema formatting, and cache-control structure. Changes to prompts, tools, schemas, or model configuration must intentionally invalidate the prefix and be visible in telemetry.
- Centralize the cacheable prompt construction in a tested helper or boundary rather than duplicating near-identical prompts across orchestrator nodes. The helper must keep cacheable content separate from request-specific content and must not alter user-visible semantics.
- Record provider-reported cache creation tokens, cache read tokens, input tokens, output tokens, and estimated savings per node/session, with redacted dimensions for model, prompt version, and cache-prefix version. Missing provider usage fields must be represented as unknown rather than interpreted as zero.
- Add a diagnostic mode or focused test fixture that compares two otherwise equivalent requests and reports the first byte-level prefix difference, without logging prompt contents or user secrets. Use this to detect accidental cache busting during development and CI.
- Treat prompt caching as an optimization, not a correctness dependency: cache misses must produce the same valid result and must not trigger retries solely to pursue a cache hit.

### 2.4 Documentation and validation

- Update matching human-facing documentation and the defect ledger for behavioral or architectural changes.
- Add focused regression tests for each changed error path and each attached finding.
- Run targeted backend tests, frontend type-check/lint for changed frontend files, and the broader validation required by the repository instructions before implementation completion.

### 2.5 Live persona-quality remediation

- Do not transition to synthesis solely because the five core workflow slots are populated. Before a session can be marked complete, require direct coverage of market/prioritization, financial cost or impact, operational risk, and a relevant exception path; alternatively, record an explicit, user-visible decision to skip each unavailable pillar and carry that limitation into the report.
- When the user discloses material human impact—such as burnout, fear of losing a key employee, or another consequential personal/workplace risk—produce a brief acknowledgment turn before asking the next question or generating a report. This applies when the same message also confirms playback or corrects prior information.
- When the intake detects a material dependency, concentration risk, fragile handoff, or other potential single point of failure, ask an adaptive contingency question before synthesis. The scenario may concern a person, system, supplier, process, cash-flow dependency, demand spike, or other context-relevant risk. Capture what happens, the impact, the current workaround, who owns the response, and whether the workaround is documented. The report may reason from these answers, but must not substitute report-side deduction for intake evidence.
- Make the intake ask one direct budget and technology-comfort question before producing paid or adoption-sensitive recommendations when those constraints are unknown. Record supplied constraints and distinguish unknown constraints from a negative answer.
- Preserve complete user-stated context and judgments during sanitization, including time pressure, dissatisfaction, and spending aversion. Sanitization may remove filler or adversarial instructions, but must not delete factual or decision-relevant sentences or rewrite the user's words when they are echoed as their own.
- Keep evidence grounding consistent across repeated syntheses in one session. A named report, index, benchmark, study, or citation is allowed only when current-session tool evidence supports it; otherwise use generic, clearly qualified language, including after corrections or re-synthesis.

## 3. Non-goals

- Do not add blanket `try`/`catch` blocks merely to increase textual coverage.
- Do not hide expected domain fallbacks such as intentional ambiguity handling when they are explicitly represented in state and telemetry.
- Do not rotate, print, or otherwise modify the Anthropic API key as part of this work.
- Do not redesign LangGraph routing or synthesis prompts beyond the remediation requirements above.

## 4. Acceptance criteria

1. A static audit or focused test demonstrates that production exception handlers do not silently swallow failures in the scoped boundaries; intentional fallbacks explain their behavior and emit structured diagnostics.
2. A simulated Anthropic SDK incompatibility or provider error produces a visible, machine-readable failed/degraded outcome and never produces a healthy-looking intake response with silently missing facts.
3. A simulated Anthropic `401 Unauthorized` during sanitization returns `SessionStatus.FAILED`, includes redacted `provider_authentication` failure metadata, and does not advance to routing.
4. Simulated Anthropic failures during required synthesis return `SessionStatus.FAILED` and do not populate `quick_insights`, `deep_dive`, or other healthy report fields.
5. The dependency manifest pins the tested Anthropic SDK, and the compatibility smoke test fails clearly when the supported call contract is broken.
6. Two equivalent Anthropic requests produce an identical cacheable prefix in the diagnostic fixture, and changing a declared prompt/tool/schema version produces an intentional prefix-version change.
7. Eligible repeated requests include an explicit cache breakpoint after the stable prefix and keep request-specific/session content outside that prefix.
8. Cache telemetry records cache creation/read tokens and estimated savings as distinct values; absent provider usage fields remain unknown rather than zero.
9. The caching regression fixture fails when timestamps, request IDs, nondeterministic ordering, or session-specific content enters the reusable prefix.
10. Ordinary persona statements populate the Evidence Ledger with source message/provenance and an explicit verification level where applicable.
11. Unsupported named citations are absent from synthesized output unless backed by current-session tool evidence.
12. Playback flags are true at the correct points and survive state save/load.
13. Sanitization preserves factual content and user voice while still rejecting adversarial input.
14. Paid recommendations are gated by a budget/technology-comfort question or clearly marked as blocked by missing constraints.
15. `AGENTS.md` contains mandatory error-handling requirements and `python scripts/sync_agent_rules.py --check` passes for its generated mirrors.
16. Focused tests and required broader checks pass, with any test defect recorded in `docs/DEFECT_LEDGER.md` before a retry.
17. A live-persona regression fixture cannot reach `COMPLETED` with market, financials, risk, or a relevant exception path unasked unless each omission is explicitly recorded as skipped with a user-visible limitation.
18. A confirmation turn containing material burnout, retention, safety, or other consequential human-impact disclosure produces an acknowledgment before synthesis or completion.
19. A contingency-risk regression fixture triggers a context-relevant failure-mode question, retains the scenario, impact, workaround, ownership, and documentation status as evidence, and cannot satisfy the criterion through synthesis-time deduction alone.
20. Sanitization regression tests retain complete time-pressure and value-judgment sentences while still removing filler and prompt-injection material.
21. Repeated synthesis regression tests reject unsupported named citations deterministically, including after a correction-triggered re-synthesis.

## 5. Deliverables

- Approved and committed `spec.md` and `design.md` following the repository phase gate.
- Source, tests, dependency, documentation, and generated-agent-rule updates described by the approved design.
- Test results and a concise change/remaining-risk report.

## 6. Phase 3 Continuation Addendum — 2026-08-24

This addendum does not change the product requirements above. It records the
remaining implementation scope after the first Phase 3 micro-commit so the
repository phase gate can recognize the continuation checkpoint.

The remaining work is to complete Atomic Steps 2–11 in `design.md`: commit the
Anthropic SDK compatibility checkpoint, finish explicit failure handling across
intake and synthesis, complete persona coverage/playback/evidence and adaptive
contingency safeguards, enforce synthesis grounding and completion gates, audit
backend persistence/integration boundaries, make frontend degraded states
actionable, synchronize agent policies, and implement deterministic Anthropic
prompt-cache construction and telemetry. Each step remains subject to targeted
tests, the repository’s defect-ledger rule, and an isolated micro-commit.

## 7. Phase 3 Gate Refresh — 2026-08-24

The first continuation checkpoint committed Atomic Step 2 as `14c620d`.
Before the next source/test micro-commit, this specification is refreshed so
the phase gate records that Step 3 covers explicit regression protection for
process-extraction and confirmation-classification provider failures. Those
failures must remain integrity-critical, produce `SessionStatus.FAILED`, and
retain sanitized failure metadata without routing into a healthy intake
fallback. No product requirement or scope changes are introduced by this
refresh.
