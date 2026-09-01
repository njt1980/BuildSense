# System Design: Scope Approval-Evidence Check to Local-Only Enforcement

Implements `spec.md` (`BS-1` / `BUG-040`, commit `3802d59`).

## 1. Architecture Overview

One CLI flag on the existing `check_phase_gate.py`, consumed by exactly one
caller (the CI workflow). No new files, no change to the local hook.

- **`--skip-approval-evidence`** â€” new `argparse` boolean flag. When passed,
  `main()` builds its check list without `check_approval_evidence`; every
  other check runs unchanged, in the same order as today.
- `.githooks/pre-commit` keeps calling `check_phase_gate.py` with no flags
  â€” full enforcement, unchanged.
- `.github/workflows/reliability-phase1.yml`'s phase-gate step adds the flag
  to its existing invocation.

```
Local commit:  .githooks/pre-commit -> check_phase_gate.py
                 (no flag: check_approval_evidence runs, as today)

CI push/PR:    reliability-phase1.yml -> check_phase_gate.py
                 --skip-approval-evidence --staged-files $CHANGED
                 (check_approval_evidence excluded; every other check runs)
```

`--skip-approval-evidence` is placed *before* `--staged-files` in the CI
invocation specifically so `--staged-files`'s `nargs="*"` has no ambiguity
about where its value list ends.

## 2. `check_phase_gate.py` changes

```python
parser.add_argument(
    "--skip-approval-evidence",
    action="store_true",
    help=(
        "Skip check_approval_evidence(). Git notes (refs/notes/approvals) "
        "are not transferred by a plain 'git push' or fetched by a default "
        "clone/checkout, so this check can only be meaningfully evaluated "
        "in the same local clone where the approval command ran. Pass this "
        "flag in CI, where that is never true (BUG-040)."
    ),
)
```

`main()`'s check-list construction changes from a fixed tuple to a list
built conditionally:

```python
checks = [check_utf8_encoding, check_mixed_staging, check_checkpoint_recency]
if not args.skip_approval_evidence:
    checks.append(check_approval_evidence)
checks += [check_threshold_regression, check_agents_md_coupling]

for check in checks:
    messages = check(staged)
    if messages:
        for line in messages:
            print(line, file=sys.stderr)
        return 1
return 0
```

Check order relative to each other is unchanged from today (`check_approval_evidence`
still runs immediately after `check_checkpoint_recency` when it runs at all)
â€” only its presence/absence changes.

## 3. `.github/workflows/reliability-phase1.yml` change

The existing phase-gate step's `run:` block changes one line:

```diff
-          python scripts/check_phase_gate.py --staged-files $CHANGED
+          # check_approval_evidence() cannot pass here: git notes are not
+          # transferred by a plain push or fetched by a default checkout,
+          # so this fresh actions/checkout@v4 clone will never have
+          # refs/notes/approvals. Do NOT "fix" this by trying to push/fetch
+          # notes into CI without re-reading spec.md/design.md for BS-1
+          # (BUG-040) first -- that tradeoff was deliberately declined.
+          python scripts/check_phase_gate.py --skip-approval-evidence --staged-files $CHANGED
```

No other step in the job changes.

## 4. Test changes

`scripts/tests/test_check_phase_gate.py`'s `run_phase_gate()` helper gains
an `*extra_args` passthrough so a test can invoke the script with flags:

```python
def run_phase_gate(repo: Path, *extra_args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, SCRIPT, *extra_args], cwd=repo, capture_output=True, text=True
    )
```

Existing call sites (`run_phase_gate(repo)`) are unaffected since
`extra_args` defaults to empty.

New test, placed after the existing `test_approval_evidence_*` tests:

```python
def test_skip_approval_evidence_flag_bypasses_check(repo: Path) -> None:
    write(repo, "spec.md", "spec\n")
    commit(repo, "docs: finalize specification", ["spec.md"])
    # deliberately no approval note on the spec commit

    write(repo, "design.md", "design\n")
    run_git(repo, "add", "design.md")

    result = run_phase_gate(repo, "--skip-approval-evidence")
    assert result.returncode == 0, result.stderr

    result = run_phase_gate(repo)
    assert result.returncode == 1
    assert "missing human approval evidence" in result.stderr
```

The second half of that test (no flag -> still rejected) is redundant with
`test_approval_evidence_rejects_design_without_spec_note` but is kept
inline so this one test alone proves the flag's effect in both directions
without relying on test ordering/isolation assumptions.

## 5. Atomic Implementation Steps

1. **`--skip-approval-evidence` flag.**
   Reads: `scripts/check_phase_gate.py`.
   Modifies: `scripts/check_phase_gate.py`, `scripts/tests/test_check_phase_gate.py`.
   Implements section 2 (flag + conditional check list) and section 4
   (`run_phase_gate` passthrough + new test).

2. **CI workflow wiring.**
   Reads: `.github/workflows/reliability-phase1.yml`.
   Modifies: `.github/workflows/reliability-phase1.yml`.
   Implements section 3 exactly (one-line change plus the explanatory
   comment guarding against a future "just push the notes" regression).

3. **Verification and single commit.**
   Reads/modifies: `docs/DEFECT_LEDGER.md` (mark `BUG-040` resolved), plus
   everything from Steps 1-2 already staged.
   Run `pytest scripts/tests/ -q` (new test green, full suite green).
   `apps/api` is untouched by this cycle, so `pytest apps/api/tests/ -q`
   and `mypy app/` are not required for this cycle's own change (BUG-039's
   pre-existing, unrelated `mypy` failure remains open, untouched).
   Then one commit covering Steps 1-2's files plus the ledger update,
   matching the established one-source-commit-per-checkpoint convention.
   This commit is itself gated by `check_approval_evidence()` against this
   cycle's own `design.md` approval note â€” the same mechanism BS-1 is
   fixing the CI-side blast radius of, still fully enforced locally.

## 6. Non-Functional Requirements Recap (from spec.md section 6)

All six spec acceptance-criteria bullets map onto the steps above: flag
behavior (both directions) -> Step 1; CI wiring -> Step 2; hook file
untouched -> verified in Step 2 (no edit to `.githooks/pre-commit`); test
suite green -> Step 3; ledger entry -> Step 3.
