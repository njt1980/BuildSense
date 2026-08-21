# Specification: Scope Approval-Evidence Check to Local-Only Enforcement

## 1. Problem (BUG-040)

`check_approval_evidence()` (added in `BS-001`/`BUG-037`, commit `32b826e`)
rejects a `design.md` or source commit unless a `refs/notes/approvals` git
note reading `approved` exists on the preceding checkpoint commit. This was
verified to work correctly in the local pre-commit hook, where the note is
created and checked in the same clone.

It does not work in CI. Empirically verified (isolated scratch push/clone
test, not against this repo's real remote):

1. A plain `git push` does **not** transfer notes refs — confirmed via a
   local bare-repo test (`Everything up-to-date`, no notes ref created on
   the remote).
2. Even after an *explicit* `git push origin refs/notes/approvals`, a fresh
   `git clone` does **not** fetch notes by default — confirmed via the same
   test (`git notes show` fails on the fresh clone despite the note existing
   on the remote).

`.github/workflows/reliability-phase1.yml`'s `preflight-checks` job runs
`python scripts/check_phase_gate.py --staged-files $CHANGED` against a fresh
`actions/checkout@v4` checkout on every push and pull request to `master`.
That checkout structurally cannot have `refs/notes/approvals` under the
current setup (nothing pushes it, and default checkout wouldn't fetch it
even if something did). `get_note()` therefore returns `None` in CI for
every commit, so `check_approval_evidence()` will reject **every future
CI run** that touches `design.md` or a source file — regardless of whether
real human approval happened locally. This is a functional regression
introduced by `BS-001`, not a pre-existing issue.

## 2. Goal

Make `check_approval_evidence()` run where it can actually produce a
correct answer (the local clone where the approval command was run) and
not run where it structurally cannot (a fresh CI checkout), without
weakening any of `check_phase_gate.py`'s other checks in either
environment.

## 3. Decision

Per user direction: local-only enforcement. Do not attempt to push/fetch
notes into CI (that was considered and explicitly declined — it would make
approval notes a permanent public record on the remote for a check that
still can't verify *who* ran the command, for comparatively large added
complexity: a push step in the human approval flow, a fetch step in CI).

## 4. Requirements

- `check_phase_gate.py` gains a `--skip-approval-evidence` CLI flag. When
  passed, `check_approval_evidence` is excluded from `main()`'s check list;
  every other check (`check_utf8_encoding`, `check_mixed_staging`,
  `check_checkpoint_recency`, `check_threshold_regression`,
  `check_agents_md_coupling`) still runs unchanged.
- `.githooks/pre-commit`'s existing invocation (`python
  scripts/check_phase_gate.py`, no flags) is **unchanged** — the local hook
  keeps full enforcement, including approval evidence, exactly as today.
- `.github/workflows/reliability-phase1.yml`'s phase-gate step adds
  `--skip-approval-evidence` to its existing `check_phase_gate.py`
  invocation, so CI stops rejecting commits solely because a ref git does
  not propagate through push/clone by default is absent.
- A short comment near `check_approval_evidence()` (or immediately above
  the CI workflow's phase-gate step, design.md to decide which) records
  *why* — future readers should not "fix" this by trying to push notes into
  CI without first reading this rationale.
- `scripts/tests/test_check_phase_gate.py` gets a new test: a `design.md`
  (or source) commit with **no** approval note passes when
  `--skip-approval-evidence` is passed, and still fails without it (already
  covered by `BS-001`'s existing tests — this new test only needs to prove
  the flag's effect).
- `docs/DEFECT_LEDGER.md` gets a `BUG-040` entry documenting the gap and its
  resolution.

## 5. Non-Goals

- No change to `check_checkpoint_recency`, `check_utf8_encoding`,
  `check_mixed_staging`, `check_threshold_regression`, or
  `check_agents_md_coupling`.
- No attempt to add note-author identity or cryptographic verification —
  the self-approval limitation discussed with the user (an agent could in
  principle run the approval-note command itself, restrained only by
  `AGENTS.md` prose) is a separate, already-acknowledged limitation and is
  not addressed by this fix.
- No changes to `AGENTS.md`'s Phase 1/2 approval-note instructions — the
  human-facing command is unaffected; only the CI-side check invocation
  changes.

## 6. Acceptance Criteria

- `python scripts/check_phase_gate.py --staged-files design.md
  --skip-approval-evidence` exits 0 for a `design.md` commit with no
  approval note present.
- The same invocation without `--skip-approval-evidence` still exits 1
  (existing `BS-001` behavior, unchanged).
- `.github/workflows/reliability-phase1.yml`'s phase-gate step passes
  `--skip-approval-evidence`.
- `.githooks/pre-commit` is byte-for-byte unchanged.
- `scripts/tests/test_check_phase_gate.py`'s full suite passes, including
  the new flag test.
- `docs/DEFECT_LEDGER.md` has a `BUG-040` entry marked resolved.
