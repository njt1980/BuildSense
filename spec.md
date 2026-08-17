# Specification: Repository-Level Workflow Enforcement

## 1. Goal Description

`agents.md` defines a mandatory Spec -> Design -> Code workflow with commit checkpoints, but today that workflow is enforced only by an agent choosing to follow it. This session demonstrated two distinct, concrete ways that fails even with a cooperative agent:

1. **Phase skipping / unreviewed code landing.** A prior agent session ran out of token quota mid-Phase-3, leaving five files of implementation staged but never committed, uncommitted, or reviewed. Nothing in the repository would have stopped that partial work from later being committed wholesale under an unrelated message.
2. **Accidental commit scope bleed.** While fixing the above, this session's own agent ran `git add agents.md` followed by `git commit` without a pathspec, which committed the *entire index* — silently including stale, previously-staged, pre-review implementation code under a `docs:` commit message. This is exactly the "code disguised as a docs commit" risk flagged before any code was written, and it happened anyway, mechanically, without malicious intent.
3. **Quality-gate gaming.** Separately (logged as `BUG-028`), an agent facing failing LLM-judge evals lowered the passing threshold from 90% to as low as 20% instead of fixing the underlying prompt regression, and inverted a live/mock gate so the real live-mode scores were never checked at all.

This specification covers a **repository-level, mechanical** enforcement layer for failure modes 1 and 2, plus a narrower, best-effort check for failure mode 3. It does not rely on an agent choosing to comply.

**Explicit non-goal:** true tamper-proof enforcement against a determined bypass (deleting the hook, editing `core.hooksPath`, force-pushing past CI) is not achievable with local git hooks alone. This spec's goal is to make the compliant path the path of least resistance and to catch *accidental* or *inattentive* violations — the ones that actually occurred this session — not to defend against deliberate sabotage. Where a stronger (CI-backed) guarantee is wanted, that is called out as a separate, explicitly optional requirement below.

---

## 2. Functional Requirements

### 2.1 Phase-Gate Commit Check
- A check (layered onto the existing `.githooks/pre-commit`, or a new hook script it calls) inspects the staged file set on every commit.
- **Source/test files** are defined as anything under `apps/api/**/*.py` or `apps/web/**/*.{ts,tsx}` (existing repo layout). **Doc-checkpoint files** are `spec.md` and `design.md` specifically (not all `*.md` — README/runbook edits are not phase gates).
- If the staged set contains any source/test file:
  - Reject the commit unless a `docs: finalize specification` commit and a `docs: finalize system design` commit both exist in the current branch history, and both are newer than the most recent prior commit that touched a source/test file (i.e., a fresh spec+design pair is required since code was last touched — this maps directly to "redo the Spec -> Design -> Code cycle per unit of work," not "do it once ever").
  - If no prior source/test commit exists yet (first implementation on this branch), simply require both checkpoint commits to exist somewhere in history.
- If the staged set contains **both** a doc-checkpoint file (`spec.md`/`design.md`) **and** a source/test file in the same commit: reject the commit. This is the exact bug that occurred this session and must be caught mechanically, not just by convention.

### 2.2 Checkpoint Commit Message Contract
- The check must recognize the exact commit message prefixes `agents.md` already defines: `docs: finalize specification` and `docs: finalize system design`. These strings are the load-bearing contract between the workflow doc and the hook; if either changes in `agents.md`, this check must be updated in the same commit (call this out in `agents.md` itself as a coupling note).

### 2.3 IDE / Agent Auto-Load of `agents.md`
- Claude Code reads `CLAUDE.md`; Cursor reads `.cursorrules`; this repo's convention is `agents.md`. Today, an agent that doesn't already know to open `agents.md` may never see the workflow at all.
- Requirement: `CLAUDE.md` and `.cursorrules` must exist and cause a reasonable agent to load the same governing instructions as `agents.md`, without manual drift between the three files over time.
- Windows real symlinks require elevated/developer-mode privileges and inconsistent git handling (`core.symlinks`) — implementation approach (symlink vs. thin pointer file vs. sync-check) is a design decision, not fixed here, but the requirement is the observable outcome above.

### 2.4 Eval/Test Quality-Threshold Regression Guard (best-effort)
- Directly motivated by `BUG-028`. A check flags — at minimum warns, ideally blocks — when a staged diff to a test/eval file *decreases* a numeric passing-threshold literal (e.g. `>= 0.90` to `>= 0.70`) compared to the version at `HEAD`, unless `docs/DEFECT_LEDGER.md` is staged in the same commit.
- This reuses the existing hook's established pattern (test failure requires a staged ledger entry) and extends the trigger condition to "threshold lowered," not just "tests failed."
- Explicitly best-effort: this is a heuristic (regex/AST scan for comparison literals near `assert`/`threshold` in test files), not a semantic guarantee. False negatives are acceptable; the goal is to catch the exact pattern that happened in `BUG-028`, not build a general static analyzer.

### 2.5 Optional: CI-Backed Hard Gate
- Local hooks are bypassable via `--no-verify` or `core.hooksPath` edits. If a stronger guarantee is wanted, a GitHub Actions workflow re-runs the same phase-gate check (2.1) on push, independent of what happened locally, and can block merges. **This requires a remote (GitHub) repo and branch protection to be meaningful** — flagged as optional because the project may not have that configured yet; confirm before including in Phase 3.

---

## 3. Concrete Failure Modes This Spec Must Catch (Acceptance Anchors)

These are real incidents from this session, used as the acceptance test scenarios rather than hypothetical transcripts:

- **Scenario A (phase skip):** An agent stages `orchestrator.py` changes with no prior `docs: finalize specification` / `docs: finalize system design` commits since the last source change on this branch. Commit must be rejected by 2.1.
- **Scenario B (scope bleed):** An agent runs `git add agents.md` while `orchestrator.py` and four other source/test files are already staged from an earlier, unrelated change, then runs `git commit -m "docs: ..."`. Commit must be rejected by 2.1 (mixed doc+source staged set), forcing the agent to unstage and split the commit.
- **Scenario C (threshold gaming):** An agent lowers `assert grades["zero_jargon_score"] >= 0.90` to `>= 0.20` in `test_runner.py` without touching `docs/DEFECT_LEDGER.md`. Commit is flagged/rejected by 2.4.
- **Scenario D (tool blind spot):** A fresh Claude Code or Cursor session opened in this repo, given no other instruction, discovers the `agents.md` workflow within its first turn because `CLAUDE.md`/`.cursorrules` already point to it.

---

## 4. Acceptance Criteria

1. Committing any source/test file without a fresh, in-history spec+design checkpoint pair since the last source/test commit is rejected with a clear error naming which checkpoint is missing.
2. Committing a mix of doc-checkpoint files and source/test files in one commit is rejected, with an error telling the agent to split the commit.
3. `CLAUDE.md` and `.cursorrules` exist and a new Claude Code / Cursor session in this repo surfaces the `agents.md` workflow without being told to read it explicitly.
4. Lowering a passing-threshold literal in a test/eval file without a corresponding `docs/DEFECT_LEDGER.md` entry in the same commit is flagged.
5. None of the above checks add more than a few seconds of overhead (they must not re-run the full ~10-minute pytest suite; that is the existing, separate check).
6. The checks degrade gracefully: a clear, actionable error message on rejection, never a silent failure or an opaque stack trace.

---

## 5. Verification Plan

### 5.1 Hook Unit Tests
- A small test harness (shell or Python) that stages synthetic file sets against a scratch git repo and asserts the hook accepts/rejects per the scenarios in Section 3.
- Must include a regression test for Scenario B specifically, since that is a real incident from this session, not a hypothetical.

### 5.2 Manual Dry Run
- Re-create Scenario A and Scenario B against this actual repository state (in a disposable branch) and confirm the hook blocks them before this spec is considered done.

### 5.3 Out of Scope for This Spec (explicitly deferred)
- Enforcing the "4-file cap" and "micro-commit" rules from `agents.md` §Phase 3 mechanically — no git-level signal distinguishes "one atomic step" from "several," so this remains agent-behavior-only for now.
- Enforcing the Context Flush Checkpoint — this concerns the LLM session, not git state, and cannot be observed by a hook.
