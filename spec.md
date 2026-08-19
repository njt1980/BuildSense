# Specification: Orchestrator Hallucination and Confirmation-Gate Fixes (Audit Cycle 2 of 5)

## 1. Goal Description

An in-depth codebase audit (see conversation context; not a committed artifact) reviewed `apps/api/app/core/orchestrator.py` (3,310 lines) and found several concrete, reproducible bugs that fabricate or leak details the user never actually stated, and one confirmation-routing bug that can ask a user to confirm a playback summary they were never shown. These are grounded leads on **BUG-030** (`docs/DEFECT_LEDGER.md`, still OPEN), which reports: a hallucinated tool name ("Tally") in intake, a closed-ended confirmatory question asked while still below the discovery/confirmation confidence threshold, and residual zero-jargon/grounding inconsistency in synthesis reports.

This cycle fixes seven concrete, independently-verified issues in this file (all re-confirmed against current line numbers in this worktree, not just the original audit pass):

1. **Six-pillar keyword coverage uses substring matching, not word matching** (`SIX_PILLARS` keyword lists, `build_six_pillar_coverage:923-927`). `"tally"` is a substring of the common English word `"totally"`; any user message containing "totally" (or any other keyword-as-substring collision across the six pillars' keyword lists) causes `f"Mentions {keyword}"` to be written into `six_pillar_coverage`, which is serialized directly into both the intake prompt (`six_pillar_json`) and the synthesis prompt as apparent evidence the user never provided. This is a strong, reproducible candidate root cause for BUG-030's "Tally" hallucination.
2. **`CONSULTANT_INTAKE_PROMPT` names "Tally" specifically inside a negative instruction** (line 387): `"...If the owner did not say they use Excel, Tally, WhatsApp, a notebook, an ERP, a dispatcher, or any other tool/person/process, do not mention it as fact."` Naming a brand inside a negation is a known LLM attention trap. A second, independent injection path for the same word.
3. **`_prune_context` truncates tool output to ~20 characters before it re-enters conversation history** (`_prune_context:2811-2814`, called at `3182` and `3243`). Real market-signal/web-search payloads — which contain the actual benchmark citations the synthesis prompt is told to cite — never reach the model in usable form; it is effectively forced to reproduce citation-like text from parametric memory. Plausible root cause for BUG-030's "residual... named external benchmark citations" grounding inconsistency.
4. **Confirmation-gate routing (`_node_route_intent:1880`) never checks that a playback summary was actually shown before treating the next user turn as a possible confirmation.** Routing into the confirmation/correction classifier depends only on `initial_required_present` (all required fields already filled) — a condition that stays true across multiple discovery-question turns once fields first fill up, regardless of whether the user was ever shown a playback to confirm. This is a plausible mechanism for BUG-030's premature-confirmation symptom. The same block also hardcodes the confidence threshold as a literal `0.85` (line 2154) instead of referencing the existing `E2E_CONFIDENCE_THRESHOLD` constant (line 516).
5. **Two ad hoc confirmation-detection fallbacks misclassify corrections as confirmations via substring matching.** `_node_route_intent:1963,1965` (`"correct" in user_prompt.lower()`) and `classify_answer_quality:536,544` (`confirmation_markers` checked via `in`) both treat the string `"incorrect"` as containing `"correct"` and therefore as a confirmation. The file's own `check_deterministic_confirmation` (line 793) does exact-word-set matching correctly for short replies; these two fallback sites (used for longer replies or when the LLM classifier is unavailable) do not.
6. **`extract_evidence_ledger_from_messages` (lines 215-267) fabricates specific statistics from bare keyword triggers**, regardless of what the user actually said. Any message containing "system"/"export"/"database" produces the canned claim `"Average vehicle utilization is 65%"`; "stated"/"manager"/"staff" produces `"Route planning takes 4 hours daily"`; "estimate"/"assume"/"think" produces `"5% of products are damaged during shipping"`. This is deterministic, code-level fabrication of numbers attributed to the user, and it runs unconditionally (not gated behind any LLM-unavailable fallback flag).
7. **`build_ambiguity_fallback_report` (line 1262) hardcodes a fictional example email, `contracts@starlight.com`, in a real user-facing fallback report** for the vendor-contracts ambiguity path. `apps/api/tests/evals/eval_dataset.py:336` currently asserts this exact string appears in the report output.

This specification does not cover: auth/JWT (excluded from this remediation effort), the structural DRY issues in this same file (Fourth Wall Rule triplication, message-filter triplication, the two-worker DAG sequencing gap, splitting the file into modules) — those are Cycle 5's scope — or the frontend clarification modal (Cycle 3) or `secure-checkpoint.md` (Cycle 4).

---

## 2. Functional Requirements

### 2.1 Word-boundary matching for six-pillar keyword coverage
- In `build_six_pillar_coverage` (`orchestrator.py:923-927`), replace the substring check `if keyword in combined_text:` with a word-boundary regex match (e.g. `re.search(rf"\b{re.escape(keyword)}\b", combined_text)`), so a keyword only counts as "mentioned" when it appears as a whole word.
- Apply this uniformly across all six pillars' keyword lists (`SIX_PILLARS`, lines 474-511) — the fix is generic, not specific to the `"tally"` case, since several other keywords (e.g. `"pay"`, `"order"`, `"cost"`) have the same class of substring-collision risk.

### 2.2 Remove the named brand from the intake prompt's negative instruction
- In `CONSULTANT_INTAKE_PROMPT` (line 387), replace the specific tool/brand list (`"Excel, Tally, WhatsApp, a notebook, an ERP, a dispatcher"`) with a generic instruction that does not name any specific software or brand, e.g.: `"If the owner did not explicitly state a specific tool, system, or person, do not name one as fact — describe the gap generically instead."`

### 2.3 Stop destructively truncating tool output before it re-enters context
- In `_prune_context` (`orchestrator.py:2811-2814`), remove the aggressive truncation to `raw_content[:20]`. Preserve enough of the real tool output for the model to ground citations in it (e.g. raise the budget to a few thousand characters, or pass through unmodified content under a reasonable cap) while keeping some upper bound so a single tool result cannot unboundedly grow the conversation history.
- This function is called at two sites (`3182`, `3243`, both inside SDK execution loops) — no call-site changes are needed, only the function body.

### 2.4 Gate the confirmation classifier on "a playback was actually shown"
- Add a new field `playback_shown: bool` to `SessionState` in `apps/api/app/models/state.py`, mirroring the existing `playback_confirmed` field (default `False`, similar docstring/description), so it round-trips through the existing JSON-blob persistence the same way `playback_confirmed` already does.
- Add the same field to the `AgentState` TypedDict in `orchestrator.py` (line 79-104 area), mirroring `playback_confirmed`.
- In `_node_route_intent`, read `playback_shown = bool(state.get("playback_shown", False))` alongside the existing `playback_confirmed` read (near line 1847).
- Change the branch at line 1880 from `if initial_required_present:` to a three-way structure:
  - `if initial_required_present and playback_shown:` — existing confirmation/correction-gate logic, unchanged.
  - `elif not initial_required_present:` — existing extraction logic, unchanged.
  - `else:` (i.e. all required fields present, but no playback has been shown yet this cycle) — no-op; fall through directly to the existing "determine conversational next action" step (current line ~2152) without running either the confirmation classifier or the extraction logic.
- Set `"playback_shown": False` in the `updates` dict of the "ask another discovery question" branch (current line ~2229-2242), and `"playback_shown": True` in the `updates` dict of the "show playback summary" branch (current line ~2301-2314), so the flag is always explicitly set on every turn where `not playback_confirmed`.
- Replace the hardcoded `0.85` literal at line 2154 with the existing `E2E_CONFIDENCE_THRESHOLD` module-level constant (line 516).

### 2.5 Fix substring-based confirmation misclassification
- In `_node_route_intent` (lines 1963, 1965) and `classify_answer_quality` (lines 536, 544), replace the substring-based `any(marker in prompt_lower for marker in [...])` checks with whole-word matching (e.g. tokenize `prompt_lower` into words via a regex such as `re.findall(r"[a-z']+", prompt_lower)` and check set membership/intersection against the marker words), so that `"incorrect"` (and similarly, `"disconfirmed"`, `"inaccurate"`, etc., if present in future marker lists) is never matched by a marker word that is one of its substrings.
- Do not change `check_deterministic_confirmation` (line 793) — it already does correct exact-set matching for short replies and is out of scope here.

### 2.6 Stop fabricating evidence-ledger claims
- In `extract_evidence_ledger_from_messages` (lines 215-267), replace each hardcoded canned `claim` string (e.g. `"Average vehicle utilization is 65%"`, `"Route planning takes 4 hours daily"`, `"5% of products are damaged during shipping"`) with the actual message content (or a trimmed/stripped version of it) as the `claim` value. Keep the existing keyword-based `ladder_level`/`source` categorization logic unchanged — that heuristic classification is legitimate; only the fabricated `claim` text is being replaced.
- Update `apps/api/tests/test_ontology.py::test_evidence_ladder_extraction` only if its existing assertions no longer hold after this change (they are expected to keep passing unmodified, since the test's example messages already contain the literal substrings — e.g. `"4 hours"`, `"65%"`, `"5%"` — that the assertions check for; verify this rather than assuming it).

### 2.7 Genericize the hardcoded example email in the ambiguity fallback report
- In `build_ambiguity_fallback_report` (line 1262), replace `contracts@starlight.com` with a generic placeholder that does not reference a fictional company, e.g. `contracts@yourcompany.com`.
- Update `apps/api/tests/evals/eval_dataset.py:336`'s `expected_report_contains` list to match the new placeholder string.

---

## 3. Non-Functional Requirements

- No change in this cycle may alter the pass/fail outcome of any existing test other than the two explicitly identified in 2.6 and 2.7 (whose expected literal strings are tied to the fabricated content being removed).
- The `playback_shown` field must default to `False` and must not require a database migration (state is persisted as an opaque JSON blob; confirmed no typed DB column references `playback_confirmed`, its sibling field).
- Changes in this cycle must not alter `CONSULTANT_PLAYBACK_PROMPT`, the six-pillar `open_question` text, or any other prompt content not explicitly named above.

---

## 4. Acceptance Criteria

1. `build_six_pillar_coverage` no longer records a pillar-keyword match for a keyword that appears only as a substring of an unrelated word (e.g. a message containing only "totally" does not record a "Mentions tally" evidence entry for the technology pillar).
2. `CONSULTANT_INTAKE_PROMPT` no longer names any specific software/tool brand inside its anti-hallucination instruction.
3. `_prune_context` no longer truncates tool output to ~20 characters; real tool content is preserved well beyond a `"Summary: <20 chars>..."` stub.
4. A new `playback_shown` field exists on both `SessionState` and `AgentState`, defaults to `False`, and is explicitly set (`True`/`False`) on every turn where `playback_confirmed` is `False`.
5. The confirmation/correction-gate classifier in `_node_route_intent` only runs when both `initial_required_present` and `playback_shown` are true; when fields are complete but no playback has been shown yet, the turn falls through to the existing next-action logic instead.
6. The literal `0.85` at the routing condition previously at line 2154 is replaced with `E2E_CONFIDENCE_THRESHOLD`.
7. Neither `_node_route_intent`'s fallback confirmation check nor `classify_answer_quality`'s `confirmation_markers` check classifies the standalone reply `"That's incorrect"` (or `"incorrect"`) as a confirmation.
8. `extract_evidence_ledger_from_messages` no longer returns one of the three original hardcoded canned claim strings verbatim when the input message does not contain that exact text.
9. `build_ambiguity_fallback_report`'s vendor-contracts recommendation no longer contains `contracts@starlight.com`.
10. `apps/api/tests/evals/eval_dataset.py`'s vendor-contracts scenario expects the new placeholder string instead of the old one.
11. Full backend suite (`pytest apps/api/tests/ -v` from `apps/api`) passes.
12. `python scripts/check_phase_gate.py` and `python scripts/sync_agent_rules.py --check`, run locally against the final staged commit, both exit 0.

---

## 5. Verification Plan

- `pytest apps/api/tests/ -v` (from `apps/api`)
- `pytest apps/api/tests/test_ontology.py -v` (from `apps/api`) — targeted check on evidence-ledger and six-pillar-adjacent behavior
- `pytest apps/api/tests/test_orchestrator.py apps/api/tests/test_interview.py -v` (from `apps/api`) — targeted check on confirmation-gate/routing behavior
- `python scripts/check_phase_gate.py` (repo root)
- `python scripts/sync_agent_rules.py --check` (repo root)
