# Skill: Secure Checkpoint
**Trigger:** When the user says 'checkpoint your work', 'run secure checkpoint', or at the end of a major phase. **Note:** For the Spec → Design → Code workflow specifically, `AGENTS.md`'s own Phase 1-3 instructions take precedence over this general-purpose skill wherever they differ — see the closing note below.

**Execution Steps:**
1. **Secret Scan:** Run `git status`. Ensure no `.env` or sensitive key files are staged. If they are, run `git reset HEAD <file>` and add them to `.gitignore`.
2. **Determine commit type:** Is this a documentation-only phase checkpoint (`spec.md`, `design.md`, README/runbook updates, agent-instruction clarifications), or an executable source change (backend/frontend code)? This decides whether step 3a or step 3b applies.
3a. **Documentation-only path:**
   - Stage only the specific intended documentation files, e.g. `git add spec.md design.md` — never `git add .` or `git add -A`.
   - Commit with `git commit --no-verify -m "<type>: <description>"`. This is intentional: these commits must not trigger the full backend test suite through the Git hook (see `AGENTS.md`'s "Commit And Validation Scope").
3b. **Executable source path:**
   - Run `python scripts/check_phase_gate.py` and `python scripts/sync_agent_rules.py --check` from the repo root. Treat a non-zero exit from either as a hard stop — do not proceed to commit until it is resolved.
   - Run the project's normal validation: `cd apps/web && npm run lint`, `cd apps/api && pytest && mypy .`.
   - If a test fails, either fix the underlying issue, or — if the failure is a known/accepted issue that shouldn't block the commit — add a dated entry to `docs/DEFECT_LEDGER.md` describing the failure and its root cause (matching the existing ledger's format) and stage it alongside the commit. Never commit past a failing test with neither a fix nor a ledger entry.
   - Stage only the specific files actually changed, e.g. `git add path/to/file1.py path/to/file2.tsx` — never `git add .` or `git add -A`.
   - Commit through the normal hook (no `--no-verify`) with `git commit -m "<type>: <description>"` using Conventional Commits (feat, fix, chore, refactor, docs).
4. **Output:** Print the commit hash and message to the terminal.

**Precedence note:** For Spec → Design → Code work, `AGENTS.md`'s Phase 1-3 workflow governs — including its Micro-Commit Rule and the one-commit-per-checkpoint convention documented in `docs/DEFECT_LEDGER.md` BUG-032 (at most one source-touching commit per spec+design checkpoint pair). Where this skill's general guidance and that workflow differ, `AGENTS.md` wins.
