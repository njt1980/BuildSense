# Specification: CI and Quality-Gate Truth-Telling (Audit Cycle 1 of 5)

## 1. Goal Description

An in-depth codebase audit (see conversation context; not a committed artifact) found that this repository's CI and post-BUG-028 quality guardrails are not actually protective right now:

1. Both GitHub Actions workflows reference a branch named `main`, but this repository's real branch is `master` (`git remote show origin` reports `HEAD branch: master`; no `main` branch exists locally or on `origin`). `reliability-phase1.yml` triggers only on `push`/`pull_request` to `main`, so it very likely never runs on real commits/PRs against `master` at all.
2. Even when it does run, `reliability-phase1.yml`'s mypy and pytest steps are both suffixed with `|| true`, so the job reports success regardless of whether those checks pass.
3. `scripts/check_phase_gate.py` — built specifically after BUG-028 (an agent silently lowering LLM-judge passing thresholds under token-quota pressure, caught only after the fact) — is wired only into the local, opt-in `.githooks/pre-commit` hook. Nothing requires a contributor or agent session to install that hook, and no CI workflow invokes the script, so a commit made with `--no-verify`, from an environment without hooks configured, or merged via the GitHub web UI bypasses it entirely.
4. The `0.90` LLM-judge passing threshold is duplicated as a bare numeric literal roughly two dozen times across `apps/api/evals/test_agent_quality.py` and `apps/api/tests/evals/test_runner.py`, with no single source of truth and no test that pins the value directly. This is the exact condition that let BUG-028's threshold-lowering edit go unnoticed: a partial edit to some-but-not-all occurrences is not obviously wrong on inspection.
5. The `if not is_live: ... else: assert grades[...] >= 0.90` gating pattern that decides whether quality assertions run against real judge output is repeated inline at each assertion site rather than centralized. BUG-028's second failure mode was an inverted version of exactly this gate; today, nothing tests the gating logic itself in isolation, so a future accidental inversion would again be invisible to any offline (non-live, no-API-key) test run.

This specification covers making the existing guardrails actually run and actually mean something. It does not cover: JWT/auth changes (explicitly excluded from this remediation effort), scheduling the full golden-dataset eval suite to run live in CI (separate, larger effort involving API costs and secrets — out of scope here), or consolidating the two structurally-different LLM-judge implementations (`apps/api/evals/judge_prompts.py` vs `apps/api/tests/evals/judge.py`) into one (noted as a candidate for a future cycle, not this one).

---

## 2. Functional Requirements

### 2.1 Fix CI branch targeting
- `.github/workflows/reliability-phase1.yml`: change the `on.push.branches` and `on.pull_request.branches` lists from `[ main ]` to `[ master ]` so the workflow actually triggers on this repository's real branch.
- `.github/workflows/ledger-enforce.yml`: change `git fetch origin main` to `git fetch origin master` and `origin/main...HEAD` to `origin/master...HEAD` in the "Fail CI if tests failed and ledger not updated" step, so the changed-files diff it depends on resolves against a branch that actually exists.

### 2.2 Make `reliability-phase1.yml` fail when checks fail
- Remove the trailing `|| true` from the "Run mypy backend type checks" step (currently `python -m mypy app/ || true`).
- Remove the trailing `|| true` from the "Run pytest (fast tests)" step (currently `pytest tests/ -q || true`).

### 2.3 Wire `check_phase_gate.py` into CI
- Add a new step to the `preflight-checks` job in `reliability-phase1.yml`, running before or alongside the existing checks, that:
  - Computes the set of files changed between the PR base and `HEAD` (for `pull_request` events) or between the pushed commit and its parent (for `push` events), using a `git fetch` deep/wide enough for the diff to resolve (the current checkout step will need `fetch-depth: 0`, or an explicit `git fetch origin <base>` before diffing, mirroring the pattern already used in `ledger-enforce.yml`).
  - Invokes `python scripts/check_phase_gate.py --staged-files <changed files...>` (the script already supports this override flag for non-interactive callers; see `scripts/check_phase_gate.py:169-174`) and fails the job on a non-zero exit code.
- This does not change `scripts/check_phase_gate.py` itself — the script's existing `--staged-files` flag is sufficient; only the CI workflow needs a new step.

### 2.4 Centralize the LLM-judge passing threshold
- Add a new module `apps/api/evals/thresholds.py` defining:
  - `PASSING_THRESHOLD: float = 0.90` — the single source of truth for the judge passing bar, with a short comment referencing BUG-028 and explaining why this value must not be edited without a corresponding `docs/DEFECT_LEDGER.md` entry.
  - `assert_quality_grades_pass(grades: dict, is_live: bool, threshold: float = PASSING_THRESHOLD) -> None` — a helper that is a no-op when `is_live` is `False`, and otherwise raises `AssertionError` (naming every failing metric and its score) if any numeric value in `grades` is below `threshold`.
- Update `apps/api/evals/test_agent_quality.py` to import `PASSING_THRESHOLD`/`assert_quality_grades_pass` from this module and replace its inline `if not is_live: ... else: assert ... >= 0.90` block (around lines 201-218) with a single call to the helper.
- Update `apps/api/tests/evals/test_runner.py` to do the same at both of its live-assertion sites (the per-scenario grading block around lines 409-434, and `test_llm_judge_rubrics`'s good/bad fixture checks around lines 491-559), replacing the repeated `assert grades["..."] >= 0.90` / `< 0.90` chains with calls to the shared helper (for the "bad" fixture check, this means asserting that `assert_quality_grades_pass` raises, rather than asserting an inequality directly).
- No behavior change is intended for any test currently gated by `is_live`/`LIVE_EVALS`: the same conditions produce the same pass/fail outcome, just through one shared code path instead of ~23 duplicated literals.

### 2.5 Add offline regression tests for the guardrail itself
- Add a new test module (suggested path: `apps/api/tests/test_eval_guardrails.py`) that requires no API key, no `LIVE_EVALS` flag, and no network access, containing at minimum:
  - A test asserting `PASSING_THRESHOLD == 0.90`, with a comment referencing BUG-028, so a future silent edit to the constant fails a fast, always-on test rather than only being detectable via a live judge run or the best-effort `check_threshold_regression` heuristic in `check_phase_gate.py`.
  - A test that calls `assert_quality_grades_pass` with `is_live=True` and a grades dict containing at least one score below `PASSING_THRESHOLD`, and asserts it raises `AssertionError`.
  - A test that calls `assert_quality_grades_pass` with `is_live=False` and the same low-scoring grades dict, and asserts it does **not** raise — confirming the intentional skip-when-not-live behavior is itself covered, so a future accidental inversion of this condition (BUG-028's second failure mode) would break an offline test immediately.

---

## 3. Non-Functional Requirements

- All new/changed tests in 2.5 must run and pass under a plain `pytest apps/api/tests/ -q` invocation with no environment variables set (no `LIVE_EVALS`, no API key) and complete in well under one second — they must not make network calls.
- The CI changes in 2.1-2.3 must not require any new secrets beyond what `reliability-phase1.yml` already has access to (`DATABASE_URL`, `REDIS_URL`); `check_phase_gate.py` is pure stdlib and git-plumbing per its own docstring.
- The refactor in 2.4 must not change which assertions run or what they check - only where the threshold value and gating logic are defined. Existing passing/failing behavior of live evals (when run with `LIVE_EVALS=true` and a real key) must be unchanged.

---

## 4. Acceptance Criteria

1. `reliability-phase1.yml`'s trigger conditions reference `master`, not `main`.
2. `ledger-enforce.yml`'s fetch/diff logic references `master`, not `main`.
3. `reliability-phase1.yml`'s mypy and pytest steps no longer contain `|| true`; a genuine failure in either fails the job.
4. `reliability-phase1.yml` contains a step that runs `scripts/check_phase_gate.py` against the PR's/push's changed files and fails the job on a non-zero exit code.
5. `PASSING_THRESHOLD` and `assert_quality_grades_pass` exist in exactly one module (`apps/api/evals/thresholds.py`) and are imported (not redefined) by both `apps/api/evals/test_agent_quality.py` and `apps/api/tests/evals/test_runner.py`.
6. No bare `0.90` threshold literal remains in the live-assertion blocks of either file that previously contained one (comments/docstrings referencing the value in prose are fine).
7. `pytest apps/api/tests/test_eval_guardrails.py -v` (or wherever the new module lives) passes with no API key and no `LIVE_EVALS` set, and specifically covers: the threshold value itself, the raise-when-live-and-failing case, and the no-op-when-not-live case.
8. Full backend suite (`pytest apps/api/tests/ -v` from `apps/api`) passes.
9. `python scripts/check_phase_gate.py` and `python scripts/sync_agent_rules.py --check`, run locally against the final staged commit, both exit 0.

---

## 5. Verification Plan

- `pytest apps/api/tests/ -v` (from `apps/api`)
- `pytest apps/api/tests/test_eval_guardrails.py -v` (from `apps/api`)
- `python scripts/check_phase_gate.py` (from repo root, staged for the relevant commit)
- `python scripts/sync_agent_rules.py --check` (from repo root)
- Manual review of the diff to `.github/workflows/reliability-phase1.yml` and `.github/workflows/ledger-enforce.yml` (no CI runner available locally to execute the workflow itself).
