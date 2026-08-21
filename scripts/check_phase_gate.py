#!/usr/bin/env python3
"""Repository-level Spec -> Design -> Code phase-gate check.

See /spec.md (Repository-Level Workflow Enforcement) and /design.md section 2.1
for the requirements and design this implements. Pure stdlib, git-plumbing only,
independent of the apps/api virtualenv so it can run from the pre-commit hook
without any project dependencies installed.

Coupling note: the commit-message prefixes this script greps for
("docs: finalize specification", "docs: finalize system design") are defined
in AGENTS.md's MANDATORY_WORKFLOW. If those strings change there, update the
patterns below in the same commit.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys

SOURCE_PATTERNS = [r"^apps/api/.*\.py$", r"^apps/web/.*\.(ts|tsx)$"]
DOC_CHECKPOINT_FILES = {"spec.md", "design.md"}
EVAL_TEST_PATH_RE = re.compile(r"^apps/api/(.*/)?(tests|evals)/.*\.py$")
LEDGER_FILE = "docs/DEFECT_LEDGER.md"

SPEC_GREP = "^docs: finalize specification"
DESIGN_GREP = "^docs: finalize system design"

NOTES_REF = "refs/notes/approvals"
APPROVAL_TEXT = "approved"

AGENTS_MD_PATH = "AGENTS.md"
AGENTS_MD_COMMIT_RE = re.compile(
    r'git commit --no-verify -m "([^"]+)"'
)

COMPARISON_RE = re.compile(r"[><]=?\s*([0-9]+(?:\.[0-9]+)?)")
KEYWORD_RE = re.compile(r"(score|threshold)", re.IGNORECASE)


def run_git(args: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], capture_output=True, text=True)


def is_source_file(path: str) -> bool:
    return any(re.match(pattern, path) for pattern in SOURCE_PATTERNS)


def is_doc_checkpoint_file(path: str) -> bool:
    return path in DOC_CHECKPOINT_FILES


def get_staged_files() -> list[str]:
    result = run_git(["diff", "--cached", "--name-only", "--diff-filter=ACM"])
    return [line for line in result.stdout.splitlines() if line]


def check_utf8_encoding(staged: list[str]) -> list[str]:
    """Reject a staged spec.md/design.md blob that isn't valid UTF-8.

    Fetches the staged blob's raw bytes directly (not via run_git(), whose
    text=True would itself raise/mangle non-UTF-8 bytes before this check
    could inspect them). Also rejects embedded NUL bytes: plain ASCII text
    saved as UTF-16 (the actual incident behind BUG-037/spec.md 4.3) decodes
    "successfully" under UTF-8 with a NUL interleaved after every character,
    so a bare decode() call would miss it. NUL-byte presence is checked
    directly instead, mirroring git's own binary-blob heuristic.
    """
    bad = []
    for path in staged:
        if not is_doc_checkpoint_file(path):
            continue
        result = subprocess.run(["git", "show", f":{path}"], capture_output=True)
        raw = result.stdout
        if b"\x00" in raw:
            bad.append(path)
            continue
        try:
            raw.decode("utf-8")
        except UnicodeDecodeError:
            bad.append(path)
    if not bad:
        return []
    return ["PHASE GATE: checkpoint file is not valid UTF-8:"] + [f"  {p}" for p in bad]


def check_mixed_staging(staged: list[str]) -> list[str]:
    """Step A (Scenario B): reject doc-checkpoint + source files staged together."""
    doc_files = [f for f in staged if is_doc_checkpoint_file(f)]
    source_files = [f for f in staged if is_source_file(f)]
    if not (doc_files and source_files):
        return []
    return [
        "PHASE GATE: This commit stages both a doc checkpoint (spec.md/design.md)",
        "and source/test files. These must be separate commits.",
        f"  Doc files staged:    {', '.join(doc_files)}",
        f"  Source files staged: {', '.join(source_files)}",
        "Unstage one group (git restore --staged <file>) and commit them separately.",
    ]


def get_commit_history_oldest_first() -> list[str]:
    result = run_git(["log", "--format=%H", "--reverse"])
    return [line for line in result.stdout.splitlines() if line]


def find_most_recent_commit_by_grep(pattern: str) -> str | None:
    result = run_git(["log", "--format=%H", f"--grep={pattern}"])
    hashes = [line for line in result.stdout.splitlines() if line]
    return hashes[0] if hashes else None


def get_note(commit: str) -> str | None:
    result = run_git(["notes", f"--ref={NOTES_REF}", "show", commit])
    return result.stdout.strip() if result.returncode == 0 else None


def find_last_source_commit(history_oldest_first: list[str]) -> str | None:
    """Most recent commit (scanning newest-first) that touched a source/test file."""
    for commit in reversed(history_oldest_first):
        result = run_git(["show", "--name-only", "--format=", commit])
        files = [line for line in result.stdout.splitlines() if line]
        if any(is_source_file(f) for f in files):
            return commit
    return None


def check_checkpoint_recency(staged: list[str]) -> list[str]:
    """Step B (Scenario A): require a fresh, in-history spec+design pair."""
    source_files = [f for f in staged if is_source_file(f)]
    if not source_files:
        return []

    history = get_commit_history_oldest_first()
    last_code_commit = find_last_source_commit(history)
    last_code_idx = history.index(last_code_commit) if last_code_commit else None

    spec_commit = find_most_recent_commit_by_grep(SPEC_GREP)
    design_commit = find_most_recent_commit_by_grep(DESIGN_GREP)
    spec_idx = history.index(spec_commit) if spec_commit else None
    design_idx = history.index(design_commit) if design_commit else None

    errors = []
    if spec_commit is None:
        errors.append("missing spec.md checkpoint commit ('docs: finalize specification')")
    if design_commit is None:
        errors.append("missing design.md checkpoint commit ('docs: finalize system design')")

    if last_code_idx is not None:
        if spec_idx is not None and spec_idx < last_code_idx:
            errors.append(
                "spec.md checkpoint is older than the last code change; redo Phase 1 for this unit of work"
            )
        if design_idx is not None and design_idx < last_code_idx:
            errors.append(
                "design.md checkpoint is older than the last code change; redo Phase 2 for this unit of work"
            )

    if not errors:
        return []
    return ["PHASE GATE: cannot commit source/test changes."] + [f"  - {e}" for e in errors]


def check_approval_evidence(staged: list[str]) -> list[str]:
    """Require a human-added git-notes approval marker between checkpoints.

    check_checkpoint_recency() only verifies a spec/design commit pair
    exists and is fresh; it cannot tell whether a human actually reviewed
    the content in between (BUG-037). A `refs/notes/approvals` note is
    added only by a documented user-run command (never by an agent's own
    commit), so its presence on a checkpoint commit is evidence a human
    acted on it.
    """
    doc_files = [f for f in staged if is_doc_checkpoint_file(f)]
    source_files = [f for f in staged if is_source_file(f)]
    errors = []

    if "design.md" in doc_files:
        spec_commit = find_most_recent_commit_by_grep(SPEC_GREP)
        if spec_commit and get_note(spec_commit) != APPROVAL_TEXT:
            errors.append(
                f"spec.md checkpoint ({spec_commit[:7]}) has no approval note. "
                f"Run: git notes --ref={NOTES_REF} add -m {APPROVAL_TEXT} {spec_commit}"
            )
    if source_files:
        design_commit = find_most_recent_commit_by_grep(DESIGN_GREP)
        if design_commit and get_note(design_commit) != APPROVAL_TEXT:
            errors.append(
                f"design.md checkpoint ({design_commit[:7]}) has no approval note. "
                f"Run: git notes --ref={NOTES_REF} add -m {APPROVAL_TEXT} {design_commit}"
            )

    if not errors:
        return []
    return ["PHASE GATE: missing human approval evidence."] + [f"  - {e}" for e in errors]


def extract_threshold_values(text: str) -> list[float]:
    values = []
    for match in COMPARISON_RE.finditer(text):
        window_start = max(0, match.start() - 40)
        window = text[window_start : match.start()]
        if KEYWORD_RE.search(window):
            values.append(float(match.group(1)))
    return values


def get_file_at_head(path: str) -> str:
    result = run_git(["show", f"HEAD:{path}"])
    return result.stdout if result.returncode == 0 else ""


def get_staged_blob(path: str) -> str:
    result = run_git(["show", f":{path}"])
    return result.stdout if result.returncode == 0 else ""


def check_threshold_regression(staged: list[str]) -> list[str]:
    """Step C (Scenario C, best-effort): flag lowered pass thresholds without a ledger entry."""
    ledger_staged = LEDGER_FILE in staged
    warnings = []
    for path in staged:
        if not EVAL_TEST_PATH_RE.match(path):
            continue
        old_values = extract_threshold_values(get_file_at_head(path))
        new_values = extract_threshold_values(get_staged_blob(path))
        if old_values and new_values and min(new_values) < min(old_values):
            warnings.append((path, min(old_values), min(new_values)))

    if not warnings or ledger_staged:
        return []

    lines = [
        "PHASE GATE: a passing-threshold literal was lowered without a",
        f"{LEDGER_FILE} entry in this commit:",
    ]
    lines += [f"  {path}: {old} -> {new}" for path, old, new in warnings]
    lines.append(f"Add a {LEDGER_FILE} entry justifying the change, or restore the threshold.")
    return lines


def check_agents_md_coupling(staged: list[str]) -> list[str]:
    """AGENTS.md's own coupling note: its two literal checkpoint commit-message
    strings must match SPEC_GREP/DESIGN_GREP (anchor stripped), or this script's
    Phase 1/Phase 2 detection has silently drifted from what AGENTS.md documents.
    Runs unconditionally, not gated on staged files, since it's a single-file
    text comparison independent of what this commit touches.
    """
    try:
        with open(AGENTS_MD_PATH, encoding="utf-8") as handle:
            text = handle.read()
    except OSError:
        return [f"PHASE GATE: could not read {AGENTS_MD_PATH} to verify coupling."]

    matches = AGENTS_MD_COMMIT_RE.findall(text)
    expected = {SPEC_GREP.lstrip("^"), DESIGN_GREP.lstrip("^")}
    found = set(matches)

    if expected <= found:
        return []

    lines = [
        f"PHASE GATE: {AGENTS_MD_PATH} checkpoint commit messages no longer match",
        "check_phase_gate.py's SPEC_GREP/DESIGN_GREP constants.",
        f"  AGENTS.md commit messages found: {sorted(found)}",
        f"  Script expects:                  {sorted(expected)}",
        "Update SPEC_GREP/DESIGN_GREP in this script to match AGENTS.md, or fix AGENTS.md.",
    ]
    return lines


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--staged-files",
        nargs="*",
        default=None,
        help="Override the staged file list (test harness use only, bypasses git diff --cached).",
    )
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
    args = parser.parse_args()

    staged = args.staged_files if args.staged_files is not None else get_staged_files()

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


if __name__ == "__main__":
    sys.exit(main())
