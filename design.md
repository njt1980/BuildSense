# System Design: Reconcile secure-checkpoint.md with the Phase Gate (Audit Cycle 4 of 5)

## 1. Architecture Overview

This is a single-file documentation rewrite. `.antigravity/skills/secure-checkpoint.md` is rewritten in place so its four execution steps match `AGENTS.md`'s "Commit And Validation Scope" section (lines 37-41) and the actual behavior of `.githooks/pre-commit` / `scripts/check_phase_gate.py`, instead of the pre-phase-gate process it was written against on 2026-08-09. No other file changes.

## 2. Data Flow

Not applicable — this cycle changes agent-facing instructions, not runtime code or data flow. The "before/after" is a text diff of one skill file's guidance.

## 3. Atomic Implementation Steps

### Step 1: Rewrite `.antigravity/skills/secure-checkpoint.md`
- **Read Path**: [`.antigravity/skills/secure-checkpoint.md`](file:///C:/Users/nimel.thomas/Desktop/BuildSense/.claude/worktrees/audit-remediation/.antigravity/skills/secure-checkpoint.md), [`AGENTS.md`](file:///C:/Users/nimel.thomas/Desktop/BuildSense/.claude/worktrees/audit-remediation/AGENTS.md) (lines 37-41, "Commit And Validation Scope")
- **Modify Path**: `.antigravity/skills/secure-checkpoint.md`
- **Description**: Rewrite the "Execution Steps" section, keeping the existing short skill-file format (Trigger + numbered steps), to read approximately as follows:
  1. **Secret Scan** (unchanged): `git status`; ensure no `.env`/key files are staged; if present, `git reset HEAD <file>` and add to `.gitignore`.
  2. **Determine commit type**: is this a documentation-only phase checkpoint (`spec.md`, `design.md`, README/runbook updates, agent-instruction clarifications) or an executable source change? This determines which of steps 3a/3b below applies. (Implements spec.md 2.4.)
  3a. **Documentation-only path**: stage only the specific intended documentation files (never `git add .`/`git add -A`); commit with `git commit --no-verify -m "<type>: <description>"`. Do not run the full backend suite for these commits (per AGENTS.md's hook-behavior note).
  3b. **Executable source path**: run `python scripts/check_phase_gate.py` and `python scripts/sync_agent_rules.py --check` from the repo root — both must exit 0. Run the project's normal test/lint/type-check validation (`cd apps/web && npm run lint`, `cd apps/api && pytest && mypy .`, as today). If a test fails: either fix the underlying issue, or add a dated entry to `docs/DEFECT_LEDGER.md` describing the failure and root cause and stage it alongside the commit (the pre-commit hook accepts this as a logged, intentional exception) — never commit past a failing test with neither a fix nor a ledger entry. Stage only the specific files actually changed (never `git add .`/`git add -A`); commit through the normal hook (no `--no-verify`) with `git commit -m "<type>: <description>"` using Conventional Commits.
  4. **Output** (unchanged): print the commit hash and message.
  - Add a closing note pointing to `AGENTS.md`'s Phase 1-3 workflow (including its Micro-Commit Rule and the one-commit-per-checkpoint convention documented in `docs/DEFECT_LEDGER.md` BUG-032) as taking precedence over this general-purpose checkpoint skill for Spec → Design → Code work specifically.
- **Targeted verification**: manual read-through comparing the new text against `AGENTS.md` lines 37-41 line by line, confirming no contradiction remains (per spec.md 2.1-2.5's acceptance criteria).

### Step 2: Verification and commit
- **Read Path**: n/a
- **Modify Path**: none
- **Description**: Confirm `git status`/`git diff --stat` shows only `.antigravity/skills/secure-checkpoint.md` changed, then run both guardrail scripts. This file matches neither `SOURCE_PATTERNS` regex in `scripts/check_phase_gate.py` (`apps/api/*.py`, `apps/web/*.ts(x)`), so it is not classified as "source" for phase-gate purposes — confirm this holds (as it did for `docs/DEFECT_LEDGER.md`-only commits in earlier cycles) before committing normally (not `--no-verify`, since this is a genuine content change being validated, not a spec/design doc-checkpoint).
- **Targeted verification**: `python scripts/check_phase_gate.py`, `python scripts/sync_agent_rules.py --check`.

---

## 4. Verification Plan

### Manual
- Line-by-line comparison of the rewritten skill file against `AGENTS.md`'s "Commit And Validation Scope" section.
- `git status` / `git diff --stat` confirming single-file change.

### Local Guardrail Scripts
- `python scripts/check_phase_gate.py` (repo root)
- `python scripts/sync_agent_rules.py --check` (repo root)
