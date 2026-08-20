# Specification: Orchestrator Dedup — Fourth Wall Rule, Message Filter, Required-Components, prompts.py (Audit Cycle 5 of 5)

## 1. Goal Description

`apps/api/app/core/orchestrator.py` (3,310+ lines) has three mechanisms that must stay consistent across multiple independently-maintained copies, which is the structural reason fixes in this file keep not sticking (per the original audit and the defect ledger's own history: BUG-009, BUG-023, BUG-026 all trace back to the required-components duplication specifically). This cycle centralizes three of them and takes one small, self-contained first step toward splitting this file into modules. Re-verified against the current worktree (all line numbers below are current, not from the original audit pass, since Cycles 2-4 have shifted the file):

1. **The Fourth Wall Rule is copy-pasted three times with drifted wording**, at lines 348-351 (`CONSULTANT_INTAKE_PROMPT`), 415-418 (`CONSULTANT_PLAYBACK_PROMPT`), and 2561-2564 (inline in the synthesis system prompt inside `_node_synthesize_report`). The first bullet is now identical across all three; the second and third bullets still differ (e.g. "under any circumstances" vs. "in any user-facing text values"; "internal state logic, completeness rules, or internal structures" vs. "state logic, internal fields, and operational classifications" vs. "state terminology and internal categories").
2. **The user-facing message filter predicate is reimplemented three times**: an imperative loop in `_save_intermediate_state` (lines 1526-1528) and two separate list comprehensions in `run_pipeline` (lines 3332, 3344), all expressing the same logic (`role != "tool" and not (role == "assistant" and name not in {None, "BuildSense Intelligence"})`) independently.
3. **Required-components/location logic is computed in two places.** `_node_context_architect` (lines 1755-1761) is the authoritative computation — it builds `required_components` and already appends `"location"` when `requires_location` is true, storing both in `architect_plan`. `_node_route_intent` (lines 1874-1876) redundantly re-derives this: it reads `architect_plan.get("required_components")` but then re-checks `requires_location` and re-appends `"location"` again. Tracing this confirms the second append is currently a no-op in every real code path (the architect node's output already satisfies the condition that would make it fire) — but nothing enforces that invariant, which is exactly the seam BUG-009/023/026 broke.
4. **The file has no internal module boundaries.** As a small, low-risk first step (not the full multi-module split), extract the file's cleanly-isolated top-level prompt-string constants — `CONSULTANT_INTAKE_PROMPT`, `CONSULTANT_PLAYBACK_PROMPT`, `PROCESS_ANALYST_WORKER_PROMPT`, `AUTOMATION_ARCHITECT_WORKER_PROMPT` (lines 337-459) — into a new `apps/api/app/core/prompts.py` module, alongside the new centralized `FOURTH_WALL_RULE` constant from item 1. The two worker prompts (`PROCESS_ANALYST_WORKER_PROMPT`, `AUTOMATION_ARCHITECT_WORKER_PROMPT`) have no `.format()` placeholders at all and are trivial to move; the two consultant prompts already use `.format()`-style placeholders and gain one more (`{fourth_wall_rule}`) as part of this cycle. The synthesis prompt (inline, dynamically built in `_node_synthesize_report`) is **not** moved in this cycle — it stays inline in `orchestrator.py` but imports and splices in the same `FOURTH_WALL_RULE` constant, so its wording is centralized even though its surrounding template isn't relocated yet.

Explicitly out of scope for this cycle (deferred, per discussion): fixing the two-worker task DAG's lack of real sequencing (a behavioral/execution-loop change, not dedup — a candidate for a future cycle), and the rest of the file-module split (node methods, extraction/confidence-scoring helpers, deterministic fallback builders, SDK execution loops all remain in `orchestrator.py`). Auth/JWT remains out of scope for the whole remediation effort.

---

## 2. Functional Requirements

### 2.1 Create `apps/api/app/core/prompts.py`
- New module containing, in this order:
  - `FOURTH_WALL_RULE: str` — one canonical version of the rule, synthesizing the most complete wording found across the three current copies (all three specific forbidden-word examples; the strongest phrasing from each of the three drifted third-bullet variants, merged into one clear instruction). Written as a plain multi-line string (not an f-string), safe to interpolate into both `.format()`-style templates (via a `{fourth_wall_rule}` placeholder) and directly into runtime-built f-strings/concatenation.
  - `CONSULTANT_INTAKE_PROMPT` — moved verbatim from `orchestrator.py:337-405`, with its existing Fourth Wall Rule block (lines 348-351) replaced by a `{fourth_wall_rule}` placeholder consistent with its other existing `.format()` placeholders.
  - `CONSULTANT_PLAYBACK_PROMPT` — moved verbatim from `orchestrator.py:406-443`, with its existing Fourth Wall Rule block (lines 415-418) replaced by a `{fourth_wall_rule}` placeholder the same way.
  - `PROCESS_ANALYST_WORKER_PROMPT` — moved verbatim from `orchestrator.py:446-451` (no placeholders, no change needed to its content).
  - `AUTOMATION_ARCHITECT_WORKER_PROMPT` — moved verbatim from `orchestrator.py:454-459` (no placeholders, no change needed to its content).

### 2.2 Update `orchestrator.py` to import from `prompts.py`
- Remove the four moved constants' definitions from `orchestrator.py`; import them (plus `FOURTH_WALL_RULE`) from `app.core.prompts` instead.
- At the `CONSULTANT_INTAKE_PROMPT.format(...)` call site (currently `orchestrator.py:2196-2207`), add `fourth_wall_rule=FOURTH_WALL_RULE` to the keyword arguments.
- At the `CONSULTANT_PLAYBACK_PROMPT.format(...)` call site (currently `orchestrator.py:2286` area), add `fourth_wall_rule=FOURTH_WALL_RULE` to the keyword arguments.
- In `_node_synthesize_report`'s inline synthesis system prompt (currently `orchestrator.py:2561-2564`), replace the three hardcoded Fourth Wall Rule lines with an interpolation of the imported `FOURTH_WALL_RULE` constant, preserving the rest of that prompt's content and structure unchanged.

### 2.3 Centralize the user-facing message filter
- Add a helper function `is_user_facing_message(m: Message) -> bool` in `orchestrator.py` (module level, near the other message-coercion helpers), implementing the shared predicate: not a `"tool"` role, and not an `"assistant"` message whose `name` is set to something other than `None`/`"BuildSense Intelligence"`.
- Replace the imperative filtering logic in `_save_intermediate_state` (lines 1526-1528) with a call to this helper.
- Replace both list-comprehension predicates in `run_pipeline` (lines 3332, 3344) with calls to this helper.
- No behavior change: the helper must implement exactly the same predicate as all three existing call sites currently do.

### 2.4 Remove the redundant required-components re-derivation
- In `_node_route_intent` (currently lines 1874-1876), remove the `if architect_plan.get("requires_location") and "location" not in required_keys: required_keys.append("location")` block. Keep the existing line that reads `required_keys` from `architect_plan.get("required_components")` (with its existing fallback default when `required_components` is missing/not a list) — that remains the single source of truth, now populated exclusively by `_node_context_architect`.
- Do not change `_node_context_architect` itself (lines 1755-1761 are already correct and become the sole authority).

---

## 3. Non-Functional Requirements

- No prompt text visible to the LLM may change in substance for `CONSULTANT_INTAKE_PROMPT` or `CONSULTANT_PLAYBACK_PROMPT` beyond the Fourth Wall Rule wording itself becoming the new centralized version (i.e. do not alter tone rules, discovery/confirmation boundary text, or any other section while moving these constants).
- `is_user_facing_message` must be a pure function with no side effects, callable identically from both `_save_intermediate_state` and `run_pipeline`.
- This cycle must not touch the two-worker task DAG (`_generate_task_dag`), the SDK execution loops, or any node method's control flow beyond the specific lines named in 2.4.
- `apps/api/app/core/prompts.py` must have no import dependency on `orchestrator.py` (one-directional: `orchestrator.py` imports from `prompts.py`, never the reverse), to avoid introducing a circular import.

---

## 4. Acceptance Criteria

1. `apps/api/app/core/prompts.py` exists and defines `FOURTH_WALL_RULE`, `CONSULTANT_INTAKE_PROMPT`, `CONSULTANT_PLAYBACK_PROMPT`, `PROCESS_ANALYST_WORKER_PROMPT`, `AUTOMATION_ARCHITECT_WORKER_PROMPT`.
2. `orchestrator.py` no longer defines any of those five names itself; it imports them from `app.core.prompts`.
3. All three Fourth Wall Rule sites (the two moved prompts, plus the still-inline synthesis prompt) render the same canonical wording at runtime.
4. `is_user_facing_message` exists once in `orchestrator.py` and is the only place implementing this predicate; `_save_intermediate_state` and both `run_pipeline` filter sites call it instead of reimplementing it.
5. `_node_route_intent` no longer contains a `requires_location`-based re-append of `"location"`; `required_keys` comes solely from `architect_plan.get("required_components")`.
6. `_node_context_architect` is unchanged.
7. Full backend suite (`pytest apps/api/tests/ -v` from `apps/api`) passes.
8. `mypy app/` (from `apps/api`) passes.
9. `python scripts/check_phase_gate.py` and `python scripts/sync_agent_rules.py --check`, run locally against the final staged commit, both exit 0.

---

## 5. Verification Plan

- `pytest apps/api/tests/ -v` (from `apps/api`)
- `pytest apps/api/tests/test_interview.py apps/api/tests/test_orchestrator.py apps/api/tests/test_ontology.py apps/api/tests/test_analyst_behavior.py -v` (from `apps/api`) — targeted check on intake/routing/architect behavior, where 2.3 and 2.4 have the most surface area
- `mypy app/` (from `apps/api`)
- `python scripts/check_phase_gate.py` (repo root)
- `python scripts/sync_agent_rules.py --check` (repo root)
- Manual: `grep -n "THE FOURTH WALL RULE" apps/api/app/core/orchestrator.py apps/api/app/core/prompts.py` — confirm the rule text appears once in `prompts.py` (as `FOURTH_WALL_RULE`) and the three usage sites all reference it rather than hardcoding it.
