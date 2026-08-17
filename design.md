# System Design: Repository-Level Workflow Enforcement

## 1. Architecture & Data Flow

Everything runs locally, at commit time, before the existing (slow, ~10 min) `pytest apps/api/tests/` step — so a rejection fails fast instead of after a long test run:

```text
git commit
  -> .githooks/pre-commit
       1. python scripts/check_phase_gate.py   (fast: git plumbing only, <1s)
            - reject on mixed doc+source staging (Scenario B)
            - reject on missing/stale spec+design checkpoint (Scenario A)
            - flag on lowered eval threshold without ledger entry (Scenario C)
       2. python scripts/sync_agent_rules.py --check   (fast: file hash compare)
            - reject if AGENTS.md changed but CLAUDE.md/.cursorrules weren't regenerated
       3. pytest apps/api/tests/ -q   (existing, slow, unchanged)
            - existing DEFECT_LEDGER.md-staged bypass on failure, unchanged
```

Two new standalone scripts live at repo root under `scripts/`, independent of the `apps/api` FastAPI codebase (this is repo governance tooling, not application logic, and must not depend on `apps/api`'s virtualenv/config to run):

- `scripts/check_phase_gate.py` — Requirements 2.1, 2.2, 2.4.
- `scripts/sync_agent_rules.py` — Requirement 2.3 (alongside the one-time `agents.md` -> `AGENTS.md` rename, which does most of 2.3's work on its own).

Both are pure-stdlib Python (subprocess calls to `git`), no new dependencies.

---

## 2. Component Design & Changes

### 2.1 `scripts/check_phase_gate.py`

**Inputs:** current git index/HEAD state via `git` subprocess calls. No arguments needed for normal hook use; a `--staged-files` override exists for the test harness (5.1) to inject a synthetic file list without needing a real staged commit.

**File classification:**
```python
SOURCE_PATTERNS = [r"^apps/api/.*\.py$", r"^apps/web/.*\.(ts|tsx)$"]
DOC_CHECKPOINT_FILES = {"spec.md", "design.md"}
```

**Step A — Mixed staging check (Scenario B):**
- Get staged files: `git diff --cached --name-only --diff-filter=ACM`.
- If the staged set intersects both `SOURCE_PATTERNS` and `DOC_CHECKPOINT_FILES`: exit 1 with:
  ```
  PHASE GATE: This commit stages both a doc checkpoint (spec.md/design.md)
  and source/test files. These must be separate commits.
    Doc files staged:    spec.md
    Source files staged: apps/api/app/core/orchestrator.py
  Unstage one group (git restore --staged <file>) and commit them separately.
  ```

**Step B — Checkpoint recency check (Scenario A):**
- Only runs if the staged set contains a source/test file (and Step A already passed, so no doc-checkpoint file is mixed in).
- Get full commit history oldest-first: `git log --format=%H --reverse` -> list `history`.
- `last_code_commit` = last entry in `git log --format=%H -- <SOURCE_PATTERNS as pathspecs>` (most recent historical commit touching a source/test file), or `None`.
- `spec_commit` = most recent commit whose message matches `^docs: finalize specification` (via `git log --grep` with `--format=%H`, first result), or `None`.
- `design_commit` = same for `^docs: finalize system design`.
- Reject with a specific, named reason if:
  - `spec_commit` is `None` -> `"missing spec.md checkpoint commit ('docs: finalize specification')"`.
  - `design_commit` is `None` -> `"missing design.md checkpoint commit ('docs: finalize system design')"`.
  - `last_code_commit` is not `None` and `history.index(spec_commit) < history.index(last_code_commit)` -> `"spec.md checkpoint is older than the last code change; redo Phase 1 for this unit of work"`.
  - Same check for `design_commit` vs `last_code_commit`.
- Using list position (topological order from `git log --reverse`) instead of commit timestamps avoids any reliance on potentially-unreliable commit dates.

**Step C — Eval-threshold regression guard (Scenario C, best-effort):**
- For each staged file matching `apps/api/**/tests/**` or `apps/api/**/evals/**` ending in `.py`:
  - Old content: `git show HEAD:<path>` (empty string if file is new).
  - New content: `git show :<path>` (the staged/index blob).
  - Extract all `>= <float>` and `> <float>` literals appearing within 40 characters of the word `score` or `threshold` (case-insensitive) in each version, via one regex pass.
  - If any such literal's value is present in the old version but the **minimum** value found in the new version is lower than the **minimum** found in the old version: flag (not hard-reject — see below) unless `docs/DEFECT_LEDGER.md` is also in the staged set.
- This is intentionally a blunt heuristic (spec 2.4 accepts false negatives). It **warns and requires confirmation** rather than hard-blocking, because a legitimate reason to lower a threshold does exist (e.g. recalibrating an overly strict bar) — the point is forcing a ledger entry to exist, not forbidding the change outright. Implementation: print the warning and the specific file/line, then check for `docs/DEFECT_LEDGER.md` in staged files; if absent, exit 1; if present, exit 0 (the ledger entry stands as the human-reviewable justification).

**Exit codes:** `0` = pass, `1` = reject (message on stderr, always human-readable, names the specific missing/violated thing — never a raw traceback).

### 2.2 Filename fix: `agents.md` -> `AGENTS.md`

Codex CLI, Google Antigravity, and GitHub Copilot's coding agent all natively auto-load a repo-root file named `AGENTS.md` (uppercase, plural) — no configuration needed on their end (Copilot added this in Aug 2025; it also reads `CLAUDE.md` directly as a bonus). This repo's file is currently tracked in git as lowercase `agents.md` (confirmed via `git ls-files`). On Windows this happens to still resolve because the filesystem is case-insensitive, but `git`'s index is case-sensitive by convention: a clone on a case-sensitive filesystem (Linux CI, WSL, Docker, some macOS/APFS configs) would simply not have a file named `AGENTS.md` and these tools would silently fall back to no project instructions at all. This is a real, not hypothetical, gap.

**Fix:** `git mv agents.md AGENTS.md`, committed as its own docs-only commit (not bundled with the phase-gate script commit). Every reference to `agents.md` in this design, in `scripts/`, and in the hook must use the new casing. Because source filesystems here are case-insensitive, a plain `git mv` between two names differing only in case can silently no-op; use the standard two-step workaround (`git mv agents.md agents.md.tmp && git mv agents.md.tmp AGENTS.md`) and verify with `git ls-files` afterward.

This one rename gives Codex, Antigravity, and Copilot full native support with **zero ongoing tooling** — no generated copy, no staleness check, nothing that can drift.

### 2.3 `scripts/sync_agent_rules.py` (Claude Code and Cursor only)

Codex and Antigravity are fully solved by 2.2 alone. Two more tools remain, both for reasons this design should not just assume away:
- **Claude Code** reads `CLAUDE.md` as its primary convention. Public sources describe emerging cross-tool `AGENTS.md` support in the broader ecosystem, but this session has no confirmed evidence Claude Code auto-loads `AGENTS.md` in this environment (this session's own system context lists no such auto-load), so relying on that would be unverified.
- **Cursor** traditionally reads `.cursorrules`; adoption of `AGENTS.md` as a drop-in replacement is reported but not something this design should take on faith either.

For these two, keep a small generated-mirror-with-staleness-check as defense-in-depth — cheap insurance if the native-support assumption above turns out wrong for a given tool version:
- `AGENTS.md` (post-rename) is the single source of truth.
- `CLAUDE.md` and `.cursorrules` are generated files: a short banner + the full verbatim content of `AGENTS.md`, plus a trailing `<!-- AGENTS.md sha256: <hash> -->` marker.
- `--write` mode: regenerates both files from the current `AGENTS.md`.
- `--check` mode (used by the hook): recomputes `AGENTS.md`'s hash and compares it to the marker stored in each generated file; exits 1 if either is missing or stale, with:
  ```
  PHASE GATE: AGENTS.md changed but CLAUDE.md/.cursorrules were not
  regenerated. Run: python scripts/sync_agent_rules.py --write
  ```
- Rationale for copy-with-hash instead of a real symlink: Windows symlinks need developer mode or admin rights and inconsistent `core.symlinks` git behavior across contributors' machines; a generated-file-plus-staleness-check is portable and testable everywhere, at the cost of needing the sync step.

### 2.4 `.githooks/pre-commit` changes

Two new lines inserted before the existing `pytest apps/api/tests/ -q` call:
```sh
python scripts/check_phase_gate.py || exit 1
python scripts/sync_agent_rules.py --check || exit 1
```
Everything after this point in the existing hook (pytest run, DEFECT_LEDGER.md bypass-on-failure) is unchanged.

### 2.5 Initial `CLAUDE.md` / `.cursorrules`

Generated once via `scripts/sync_agent_rules.py --write` as part of this implementation, then committed normally (they are themselves plain docs files, not source/test, so they don't trip the phase gate).

---

## 3. Explicitly Deferred (per spec.md Section 5.3 / 2.5)

- CI-backed hard gate (spec 2.5): not built in this pass. Needs a decision on whether this repo has/wants a GitHub remote + branch protection before it's worth the design effort — raised as an open question rather than assumed.
- 4-file cap / micro-commit enforcement: no git-observable signal distinguishes one atomic step from several; remains agent-behavior-only in `AGENTS.md`.
- Context Flush Checkpoint: concerns the LLM session, not git state; unobservable by a hook.
- Full native-`AGENTS.md`-support verification for Claude Code/Cursor: if a future session confirms both tools reliably auto-load `AGENTS.md` directly, `scripts/sync_agent_rules.py` and its two generated files can be deleted entirely, leaving only the 2.2 rename. Not assumed now; revisit later.

---

## 4. Verification & Testing Design

### 4.1 `scripts/tests/test_check_phase_gate.py`
- Spins up a disposable scratch git repo per test via `tempfile.TemporaryDirectory()` + `git init`, so tests never touch the real BuildSense repo.
- Scenario A: commit a source file with no prior checkpoint commits -> assert exit code 1, assert stderr names the missing checkpoint.
- Scenario B: stage an `AGENTS.md`-analog doc file + a source file together -> assert exit code 1, assert stderr names both groups.
- Scenario C: stage a test file whose diff lowers a `>= 0.90` literal to `>= 0.20` without staging a ledger file -> assert exit 1; re-run with the ledger file also staged -> assert exit 0.
- Positive case: full spec+design checkpoint history present and newer than the last code commit -> assert exit 0.
- Run via `pytest scripts/tests/ -q` — deliberately **not** wired into `apps/api/pyproject.toml`'s config, since this tooling is independent of the FastAPI app.

### 4.2 `scripts/tests/test_sync_agent_rules.py`
- `--write` then `--check` on a fresh scratch dir -> exit 0.
- Mutate `AGENTS.md` without re-running `--write` -> `--check` exits 1.

### 4.3 Manual Dry Run (spec 5.2)
- On a disposable branch off current `master`, reproduce Scenario A and Scenario B against this real repo and confirm rejection, before this design is considered verified.
