# Specification: Reconcile secure-checkpoint.md with the Phase Gate (Audit Cycle 4 of 5)

## 1. Goal Description

`AGENTS.md` (the canonical agent-instructions file, mechanically mirrored into `CLAUDE.md`/`.cursorrules` by `scripts/sync_agent_rules.py`) explicitly directs agents to use `.antigravity/skills/secure-checkpoint.md` as part of its own Definition of Done ("All work has been committed using the `.antigravity/skills/secure-checkpoint.md` skill") and its Defect Tracking directive ("you must fix the issue and immediately invoke the `.antigravity/skills/log-defect.md` skill before attempting to commit again"). But `secure-checkpoint.md` itself, read fresh in this worktree, actively contradicts the workflow AGENTS.md and `scripts/check_phase_gate.py` enforce:

1. **Step 3 says `git add .`** (`.antigravity/skills/secure-checkpoint.md:11`). AGENTS.md's "Commit And Validation Scope" section says to "stage only the intended documentation files" for doc checkpoints, and `scripts/check_phase_gate.py`'s `check_mixed_staging` function exists specifically to reject a commit that stages `spec.md`/`design.md` together with source files — exactly the failure mode a blanket `git add .` invites.
2. **It never mentions `scripts/check_phase_gate.py` or `scripts/sync_agent_rules.py --check`**, both of which `.githooks/pre-commit` now runs on every commit (added well after this skill file was last touched — it is dated 2026-08-09, and the phase-gate/commit-contract system was built 2026-08-17 through 2026-08-19 per `docs/DEFECT_LEDGER.md`'s CHANGE-002 through BUG-032 entries).
3. **Step 2 says "HALT if any tests fail. Do not commit,"** with no escape hatch — but the actual, current, enforced behavior (`.githooks/pre-commit`, and AGENTS.md's own "If a test fails during a code checkpoint, log the defect in `docs/DEFECT_LEDGER.md` before retrying the commit") is that a failing test **can** still be committed, provided `docs/DEFECT_LEDGER.md` is updated with a dated entry explaining the failure in the same commit. The skill's unconditional "do not commit" reads as flatly wrong against actual repo practice, which this remediation effort's own Cycles 1-3 relied on repeatedly.
4. **It gives no guidance on doc-checkpoint vs. source-change commits** — AGENTS.md distinguishes "Documentation-only phase commits" (`spec.md`, `design.md`, README, etc. — staged narrowly, committed with `--no-verify`) from "Executable source changes" (must go through the normal hook, no `--no-verify`). `secure-checkpoint.md`'s single undifferentiated `git add .` / `git commit` flow collapses this distinction entirely.

This cycle rewrites `.antigravity/skills/secure-checkpoint.md` so it is accurate and consistent with `AGENTS.md`, `scripts/check_phase_gate.py`, and `.githooks/pre-commit` as they actually exist today, rather than as they existed on 2026-08-09. It does not touch `.antigravity/skills/log-defect.md` (a separate, lower-severity finding about ledger-entry format drift, out of scope for this cycle), `scripts/check_phase_gate.py` itself, or any other file — this is a narrowly-scoped documentation-accuracy fix, not a process redesign.

---

## 2. Functional Requirements

### 2.1 Replace the blanket `git add .` with explicit, scoped staging
- In `.antigravity/skills/secure-checkpoint.md`'s "Commit" step (currently step 3), replace `git add .` with guidance to stage only the specific files that were actually changed for the current unit of work (e.g. `git add <file1> <file2> ...`), explicitly warning against `git add .`/`git add -A` for the same reason AGENTS.md already gives elsewhere in the repo: it risks staging unrelated files, secrets, or a doc-checkpoint file alongside source changes.

### 2.2 Add the missing local guardrail checks
- Add a step (or extend the existing "Verification" step) instructing the agent to run `python scripts/check_phase_gate.py` and `python scripts/sync_agent_rules.py --check` from the repo root before committing, and to treat a non-zero exit from either as a hard stop, matching what `.githooks/pre-commit` actually enforces.

### 2.3 Fix the "HALT if tests fail" step to reflect the real escape hatch
- Replace the unconditional "HALT if any tests fail. Do not commit." instruction with guidance matching actual repo practice: if tests fail, either fix the underlying issue, or — if the failure is a known/accepted issue that shouldn't block the commit — add a dated entry to `docs/DEFECT_LEDGER.md` describing the failure and its root cause (following the existing ledger's format) and stage it alongside the commit, which the pre-commit hook accepts as an intentional, logged exception. Do not commit past a failing test silently, with neither a fix nor a ledger entry.

### 2.4 Distinguish doc-checkpoint commits from source-change commits
- Add a brief note distinguishing the two commit types AGENTS.md already defines: documentation-only phase checkpoints (`spec.md`/`design.md`/README/runbook updates — narrowly staged, committed with `git commit --no-verify`) versus executable source changes (must go through the normal hook path described in 2.2/2.3, never `--no-verify`). Point to AGENTS.md's "Commit And Validation Scope" section as the authoritative source rather than duplicating its full text.

### 2.5 Update the "Trigger" line's staleness (minor)
- The skill's trigger line currently reads generically ("When the user says 'checkpoint your work'... or at the end of a major phase"). Add a one-line pointer noting that for the Spec → Design → Code workflow specifically, `AGENTS.md`'s own Phase 1-3 instructions (including the Micro-Commit Rule and its currently-adopted one-commit-per-checkpoint convention, `docs/DEFECT_LEDGER.md` BUG-032) take precedence over this generic checkpoint skill where they differ — this skill is a general-purpose checkpoint helper, not a replacement for the phase-specific commit rules.

---

## 3. Non-Functional Requirements

- This is a pure documentation change. No source code, tests, or CI configuration are touched in this cycle.
- The rewritten `secure-checkpoint.md` must not contradict anything in the current `AGENTS.md` (verify by re-reading `AGENTS.md`'s "Commit And Validation Scope" and Phase 1-3 sections immediately before finalizing the rewrite, since this cycle's own commits will themselves need to follow those same rules).
- Keep the file's existing format (a short, scannable "Trigger" + numbered "Execution Steps" skill file) rather than expanding it into a long document — the goal is accuracy, not exhaustiveness; AGENTS.md remains the authoritative full source.

---

## 4. Acceptance Criteria

1. `.antigravity/skills/secure-checkpoint.md` no longer instructs `git add .` or any other blanket-staging command.
2. `.antigravity/skills/secure-checkpoint.md` instructs running `scripts/check_phase_gate.py` and `scripts/sync_agent_rules.py --check` before committing.
3. `.antigravity/skills/secure-checkpoint.md` no longer says to unconditionally halt and not commit on a test failure; it describes the documented `docs/DEFECT_LEDGER.md`-entry escape hatch.
4. `.antigravity/skills/secure-checkpoint.md` distinguishes documentation-only checkpoint commits from executable-source commits, consistent with AGENTS.md's "Commit And Validation Scope" section.
5. No other file is modified in this cycle.
6. `python scripts/check_phase_gate.py` and `python scripts/sync_agent_rules.py --check`, run locally against the final staged commit, both exit 0 (this commit touches a file outside `apps/api/*.py` and `apps/web/*.ts(x)`, so it is not classified as "source" by the phase gate's own patterns — verify this holds and the commit does not require a fresh spec/design pair of its own, consistent with how `docs/DEFECT_LEDGER.md` entries and other non-classified files have committed cleanly in prior cycles).

---

## 5. Verification Plan

- Manual read-through of the rewritten `.antigravity/skills/secure-checkpoint.md` against AGENTS.md's "Commit And Validation Scope" section, confirming no contradiction remains.
- `python scripts/check_phase_gate.py` (repo root)
- `python scripts/sync_agent_rules.py --check` (repo root)
- `git status` / `git diff --stat` confirming only `.antigravity/skills/secure-checkpoint.md` changed.
