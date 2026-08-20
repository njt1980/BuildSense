# Specification: Restore the Human-in-the-Loop Clarification Modal (Audit Cycle 3 of 5)

## 1. Goal Description

An in-depth codebase audit found that `apps/web/src/app/[lang]/projects/[id]/page.tsx`'s `ClarificationModal` — the product's documented human-in-the-loop clarification UI — can never open. The `useEffect` that reacts to session status (lines 192-198) sets `isClarificationOpen` to `false` in **both** branches of its `if (status === "AWAITING_CLARIFICATION")` check:

```tsx
if (activeSessionState?.status === "AWAITING_CLARIFICATION") {
  setActiveTab("chat");
  setIsClarificationOpen(false);   // <- almost certainly should be true
} else {
  setIsClarificationOpen(false);
}
```

`isClarificationOpen` is never set `true` anywhere else in the file. This was verified as a real, currently-broken code path: `AWAITING_CLARIFICATION` is the status the backend sets on every discovery-question turn (`apps/api/app/core/orchestrator.py`'s `_node_route_intent`), so the modal is meant to open on ordinary intake turns, not some rare edge case.

Before committing to a fix, two follow-up questions were investigated and resolved:

1. **Does the modal's submit path conflict with the intake/confirmation-gate logic fixed in Audit Cycle 2?** `ClarificationModal`'s `onSubmit` posts a `clarification_responses: Record<string, string>` payload (`page.tsx:354-361`), which `apps/api/app/main.py:486-493` handles by appending `Q: {q}\nA: {ans}`-formatted user messages and then setting `state.status = SessionStatus.PLANNING` before calling `run_pipeline`. Tracing the LangGraph wiring (`orchestrator.py:1459-1513`, `_route_after_sanitize`, `_route_after_intent`) confirms this forced status is **not** a functional bypass: the graph's entry point is unconditionally `sanitize_input`, which always reaches `route_intent` via a static edge regardless of the incoming status, and `_node_route_intent` never reads the incoming status at all — only the status it itself returns matters for the next routing decision. So a clarification-modal submission goes through the exact same confirmation-gate/extraction logic as a normal chat message; the `state.status = SessionStatus.PLANNING` line is misleading dead weight (it implies a skip that does not happen), not an active bug.
2. **Does the modal's multi-question form UI conflict with the one-question-at-a-time "Iterative Discovery" design** (`docs/DEFECT_LEDGER.md` BUG-013, CHANGE-003)? No: `_node_route_intent` always sets `clarification_questions = [question]` (a single-item list) under the current architecture, so the modal renders exactly one input field per turn in practice — compatible with the current design, not a relic of an abandoned multi-slot flow.

Given both, this cycle restores the modal (rather than removing it) and cleans up the one piece of genuinely misleading backend code found along the way. This is a small, low-risk cycle.

This specification does not cover: auth/JWT, `secure-checkpoint.md` (Cycle 4), or the orchestrator structural refactors (Cycle 5).

---

## 2. Functional Requirements

### 2.1 Fix the modal open/close toggle
- In `apps/web/src/app/[lang]/projects/[id]/page.tsx`, change the `useEffect` at lines 192-198 so that `setIsClarificationOpen(true)` is called in the `AWAITING_CLARIFICATION` branch, and `setIsClarificationOpen(false)` remains in the `else` branch. No other logic in this effect changes.

### 2.2 Remove the misleading forced-PLANNING status line
- In `apps/api/app/main.py`, remove the `state.status = SessionStatus.PLANNING` line (currently line 492) from the `if payload.clarification_responses:` block. Leave `state.status` unchanged in this branch, matching how the ordinary `payload.prompt` resume path (lines 478-483) already leaves status untouched and lets `run_pipeline`/`_node_route_intent` determine the next status from scratch. Keep everything else in this block (appending `Q:/A:` messages, updating `state.clarification_responses`, saving chat messages, the `log_event` call) unchanged.

---

## 3. Non-Functional Requirements

- This cycle changes UI-visible behavior (the modal will now actually appear) but must not change any backend routing/confirmation-gate logic touched by Audit Cycle 2 — 2.2 removes a line that was already functionally inert, it does not alter `_node_route_intent`, `_route_after_intent`, or any confidence/threshold logic.
- No new automated frontend test infrastructure is introduced in this cycle (none currently exists in `apps/web`); verification for 2.1 is manual/visual plus a code-level check that the toggle now differs between branches.

---

## 4. Acceptance Criteria

1. `apps/web/src/app/[lang]/projects/[id]/page.tsx`'s status-sync effect sets `isClarificationOpen` to `true` when `activeSessionState?.status === "AWAITING_CLARIFICATION"`, and to `false` otherwise.
2. `apps/api/app/main.py` no longer sets `state.status = SessionStatus.PLANNING` inside the `clarification_responses` handling block; the block still appends `Q:/A:` messages, updates `clarification_responses`, saves chat messages, and logs the `clarification_responses_received` event.
3. Full backend suite (`pytest apps/api/tests/ -v` from `apps/api`) passes.
4. `npm run type-check` and `npm run lint` (from `apps/web`) pass.
5. `python scripts/check_phase_gate.py` and `python scripts/sync_agent_rules.py --check`, run locally against the final staged commit, both exit 0.

---

## 5. Verification Plan

- `pytest apps/api/tests/ -v` (from `apps/api`) — confirms 2.2 did not change any backend test outcome.
- `npm run type-check` (from `apps/web`)
- `npm run lint` (from `apps/web`)
- Manual/visual check: start the dev server, drive a session into `AWAITING_CLARIFICATION` status, confirm the modal opens with the current question pre-filled as a label and an empty input, and that submitting or cancelling closes it correctly.
- `python scripts/check_phase_gate.py` (repo root)
- `python scripts/sync_agent_rules.py --check` (repo root)
