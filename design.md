# System Design: CI and Quality-Gate Truth-Telling (Audit Cycle 1 of 5)

## 1. Architecture Overview

Today, the repository's quality signal is split across two disconnected layers:

- **Local, opt-in**: `.githooks/pre-commit` runs `check_phase_gate.py`, `sync_agent_rules.py --check`, and the backend test suite — but only for a contributor who has run `git config core.hooksPath .githooks`. Nothing enforces that.
- **CI, always-on but broken**: `reliability-phase1.yml` and `ledger-enforce.yml` run on GitHub Actions, but (a) `reliability-phase1.yml`'s triggers target a `main` branch that doesn't exist in this repo, (b) even when triggered, its mypy/pytest steps swallow failures via `|| true`, and (c) neither workflow invokes `check_phase_gate.py`, so the guardrail built after BUG-028 has no CI-side presence at all.

Separately, the specific guardrail BUG-028 exposed — LLM-judge passing thresholds — is encoded as ~23 duplicated `0.90` literals with no single source of truth and no fast offline test pinning the value or the live/mock gating logic that decides whether those literals are even checked.

This cycle closes both gaps without touching orchestration logic, auth, or the eval suite's live-run scheduling:

1. **Fix branch targeting** so CI actually runs on real commits.
2. **Remove failure-swallowing** so CI actually reports what happened.
3. **Wire the existing phase-gate script into CI** using its existing `--staged-files` override, so the guardrail applies regardless of local hook configuration.
4. **Centralize the threshold and its gating logic** into one importable module used by both eval test files.
5. **Add fast, offline tests** that would have caught both halves of BUG-028 (the lowered literal, and an inverted live/mock gate) without needing a live API key.

## 2. Data Flow

```mermaid
graph TD
    A[git commit] --> B{Hook installed?}
    B -- yes --> C[.githooks/pre-commit: check_phase_gate.py, sync_agent_rules.py --check, pytest]
    B -- no, or --no-verify --> D[Guardrail skipped locally]
    A --> E[git push]
    E --> F[GitHub Actions: reliability-phase1.yml]
    F -->|before this cycle| G[triggers on 'main' - never fires on 'master']
    F -->|after this cycle| H[triggers on 'master']
    H --> I[fetch base ref, compute changed files]
    I --> J[check_phase_gate.py --staged-files ...]
    I --> K[mypy app/ - failure now fails the job]
    I --> L[pytest tests/ -q - failure now fails the job]
    J -->|non-zero exit| M[Job fails]
    K -->|non-zero exit| M
    L -->|non-zero exit| M
```

The key structural change: **D and G are the two ways the guardrail is currently invisible**; this cycle makes the CI path (H/I/J) a reliable backstop independent of whether a contributor's local hook is installed.

## 3. Atomic Implementation Steps

### Step 1: Fix and harden `reliability-phase1.yml`
- **Read Path**: [`.github/workflows/reliability-phase1.yml`](file:///C:/Users/nimel.thomas/Desktop/BuildSense/.claude/worktrees/audit-remediation/.github/workflows/reliability-phase1.yml)
- **Modify Path**: [`.github/workflows/reliability-phase1.yml`](file:///C:/Users/nimel.thomas/Desktop/BuildSense/.claude/worktrees/audit-remediation/.github/workflows/reliability-phase1.yml)
- **Description**:
  - Change `on.push.branches` and `on.pull_request.branches` from `[ main ]` to `[ master ]`.
  - Add `fetch-depth: 0` to the existing `actions/checkout@v4` step (needed so the base-ref diff in the next bullet has history to compare against).
  - Add a new step, after checkout and before the Python setup, that: on `pull_request` events, runs `git diff --name-only origin/${{ github.event.pull_request.base.ref }}...HEAD`; on `push` events, runs `git diff --name-only HEAD~1...HEAD` (falling back to an empty change set on a repo's first commit, e.g. via `|| true` on this diff step only — the diff step, not the check itself); then runs `python scripts/check_phase_gate.py --staged-files <the resulting file list>` and fails the step (`exit 1`) on non-zero.
  - Remove `|| true` from the "Run mypy backend type checks" step.
  - Remove `|| true` from the "Run pytest (fast tests)" step.
- **Targeted verification**: no local runner for GitHub Actions; verify by inspecting the diff and confirming `python scripts/check_phase_gate.py --staged-files spec.md design.md` (a mixed doc+non-existent-source case) still behaves as expected when run manually from repo root.

### Step 2: Fix `ledger-enforce.yml` branch reference
- **Read Path**: [`.github/workflows/ledger-enforce.yml`](file:///C:/Users/nimel.thomas/Desktop/BuildSense/.claude/worktrees/audit-remediation/.github/workflows/ledger-enforce.yml)
- **Modify Path**: [`.github/workflows/ledger-enforce.yml`](file:///C:/Users/nimel.thomas/Desktop/BuildSense/.claude/worktrees/audit-remediation/.github/workflows/ledger-enforce.yml)
- **Description**: Change `git fetch origin main` to `git fetch origin master`, and `origin/main...HEAD` to `origin/master...HEAD`, in the "Fail CI if tests failed and ledger not updated" step.
- **Targeted verification**: manual inspection only (no local Actions runner).

### Step 3: Create the shared threshold module and update `test_agent_quality.py`
- **Read Path**: [`apps/api/evals/test_agent_quality.py`](file:///C:/Users/nimel.thomas/Desktop/BuildSense/.claude/worktrees/audit-remediation/apps/api/evals/test_agent_quality.py)
- **Modify Path**: `apps/api/evals/thresholds.py` (new file), [`apps/api/evals/test_agent_quality.py`](file:///C:/Users/nimel.thomas/Desktop/BuildSense/.claude/worktrees/audit-remediation/apps/api/evals/test_agent_quality.py)
- **Description**:
  - Create `apps/api/evals/thresholds.py` with `PASSING_THRESHOLD: float = 0.90` (comment referencing BUG-028) and `assert_quality_grades_pass(grades: dict, is_live: bool, threshold: float = PASSING_THRESHOLD) -> None`, which no-ops when `is_live` is `False` and otherwise raises `AssertionError` listing every metric below `threshold`.
  - In `test_agent_quality.py`, replace the inline `if not is_live: ... else: assert grades["zero_jargon_score"] >= 0.90 ... assert grades["privacy_safety_score"] >= 0.90` block (around lines 201-218) with `assert_quality_grades_pass(grades, is_live)`, importing both names from `evals.thresholds`.
- **Targeted verification**: `pytest apps/api/evals/test_agent_quality.py -v` (offline path only; live path requires `LIVE_EVALS=true` + API key and is unchanged in behavior, not re-verified here).

### Step 4: Update `test_runner.py` to use the shared module
- **Read Path**: [`apps/api/tests/evals/test_runner.py`](file:///C:/Users/nimel.thomas/Desktop/BuildSense/.claude/worktrees/audit-remediation/apps/api/tests/evals/test_runner.py)
- **Modify Path**: [`apps/api/tests/evals/test_runner.py`](file:///C:/Users/nimel.thomas/Desktop/BuildSense/.claude/worktrees/audit-remediation/apps/api/tests/evals/test_runner.py)
- **Description**:
  - Import `PASSING_THRESHOLD`/`assert_quality_grades_pass` from `evals.thresholds`.
  - Replace the per-scenario grading block's `assert grades["..."] >= 0.90` chain (around lines 409-434) with `assert_quality_grades_pass(grades, is_live)`.
  - In `test_llm_judge_rubrics`, replace the "good fixture" `assert good_grades["..."] >= 0.90` chain (around lines 524-529) with `assert_quality_grades_pass(good_grades, is_live=True)`, and replace the "bad fixture" `assert (... < 0.90 or ...)` chain (around lines 553-558) with an explicit `pytest.raises(AssertionError)` around `assert_quality_grades_pass(bad_grades, is_live=True)`.
- **Targeted verification**: `pytest apps/api/tests/evals/test_runner.py -v` (offline-gated portions only; this file's `LIVE_EVALS`-gated assertions are unchanged in behavior).

### Step 5: Add offline guardrail regression tests
- **Read Path**: `apps/api/evals/thresholds.py` (created in Step 3)
- **Modify Path**: `apps/api/tests/test_eval_guardrails.py` (new file)
- **Description**: Add three tests, none requiring `LIVE_EVALS` or an API key:
  1. `test_passing_threshold_is_090` — asserts `PASSING_THRESHOLD == 0.90`, with a comment referencing BUG-028.
  2. `test_assert_quality_grades_pass_raises_when_live_and_failing` — calls `assert_quality_grades_pass({"zero_jargon_score": 0.5}, is_live=True)` inside `pytest.raises(AssertionError)`.
  3. `test_assert_quality_grades_pass_noop_when_not_live` — calls `assert_quality_grades_pass({"zero_jargon_score": 0.5}, is_live=False)` and asserts no exception is raised (directly covering BUG-028's gate-inversion failure mode).
- **Targeted verification**: `pytest apps/api/tests/test_eval_guardrails.py -v`

### Step 6: Full verification pass
- **Read Path**: n/a (verification only, no source reads beyond what prior steps already covered)
- **Modify Path**: none
- **Description**: Run the full backend suite and both local guardrail scripts to confirm nothing regressed and the phase-gate/sync checks are satisfied for the final commit of this cycle.
- **Targeted verification**: `pytest apps/api/tests/ -v`, `python scripts/check_phase_gate.py`, `python scripts/sync_agent_rules.py --check`.

---

## 4. Verification Plan

### Automated Tests
- `pytest apps/api/tests/ -v` (run from `apps/api`)
- `pytest apps/api/tests/test_eval_guardrails.py -v`
- `pytest apps/api/evals/test_agent_quality.py -v`
- `pytest apps/api/tests/evals/test_runner.py -v`

### Local Guardrail Scripts
- `python scripts/check_phase_gate.py` (repo root)
- `python scripts/sync_agent_rules.py --check` (repo root)

### Manual
- Diff review of both workflow YAML files (no local GitHub Actions runner available).
