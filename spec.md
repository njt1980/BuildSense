# BuildSense Reliability and Persona-Run Remediation Specification

## 1. Objective

Harden BuildSense so failures in external services, model calls, persistence, streaming, and parsing are observable and cannot silently masquerade as a healthy intake or report-generation run. Incorporate the 2026-08-24 Kochi Kirana persona-testing findings into enforceable product behavior and agent guidance.

## 2. Scope

### 2.1 Error handling and observability

- Audit all production Python and TypeScript/React integration boundaries, including Anthropic calls, MCP/tool calls, database and Redis operations, file/audio processing, HTTP/SSE requests, JSON parsing, authentication, and local-storage access.
- Retain `try`/`except` or `try`/`catch` where an operation can fail at runtime, but require every handled failure to do one of the following: re-raise a typed/domain error, return an explicit degraded/failed result, or use a deliberately documented user-safe fallback with structured logging and state metadata.
- Prohibit silent handlers (`pass`, empty handlers, or logging-only handlers) for production paths where the result affects facts, routing, safety, billing, persistence, or report validity.
- Ensure model-call failures in sanitization, process extraction, clarification generation, confirmation classification, and synthesis are distinguishable in state and telemetry. Intake failures must not look identical to successful fallback questioning.
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

### 2.3 Documentation and validation

- Update matching human-facing documentation and the defect ledger for behavioral or architectural changes.
- Add focused regression tests for each changed error path and each attached finding.
- Run targeted backend tests, frontend type-check/lint for changed frontend files, and the broader validation required by the repository instructions before implementation completion.

## 3. Non-goals

- Do not add blanket `try`/`catch` blocks merely to increase textual coverage.
- Do not hide expected domain fallbacks such as intentional ambiguity handling when they are explicitly represented in state and telemetry.
- Do not rotate, print, or otherwise modify the Anthropic API key as part of this work.
- Do not redesign LangGraph routing or synthesis prompts beyond the remediation requirements above.

## 4. Acceptance criteria

1. A static audit or focused test demonstrates that production exception handlers do not silently swallow failures in the scoped boundaries; intentional fallbacks explain their behavior and emit structured diagnostics.
2. A simulated Anthropic SDK incompatibility or provider error produces a visible, machine-readable failed/degraded outcome and never produces a healthy-looking intake response with silently missing facts.
3. The dependency manifest pins the tested Anthropic SDK, and the compatibility smoke test fails clearly when the supported call contract is broken.
4. Ordinary persona statements populate the Evidence Ledger with source message/provenance and an explicit verification level where applicable.
5. Unsupported named citations are absent from synthesized output unless backed by current-session tool evidence.
6. Playback flags are true at the correct points and survive state save/load.
7. Sanitization preserves factual content and user voice while still rejecting adversarial input.
8. Paid recommendations are gated by a budget/technology-comfort question or clearly marked as blocked by missing constraints.
9. `AGENTS.md` contains mandatory error-handling requirements and `python scripts/sync_agent_rules.py --check` passes for its generated mirrors.
10. Focused tests and required broader checks pass, with any test defect recorded in `docs/DEFECT_LEDGER.md` before a retry.

## 5. Deliverables

- Approved and committed `spec.md` and `design.md` following the repository phase gate.
- Source, tests, dependency, documentation, and generated-agent-rule updates described by the approved design.
- Test results and a concise change/remaining-risk report.
