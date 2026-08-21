"""Tests for scripts/check_phase_gate.py against disposable scratch git repos.

Run via: pytest scripts/tests/ -q (deliberately independent of apps/api/pyproject.toml).
See spec.md section 5.1 and design.md section 4.1.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT = str(Path(__file__).resolve().parent.parent / "check_phase_gate.py")


def run_git(repo: Path, *args: str) -> subprocess.CompletedProcess:
    result = subprocess.run(["git", *args], cwd=repo, capture_output=True, text=True)
    assert result.returncode == 0, f"git {' '.join(args)} failed: {result.stderr}"
    return result


def write(repo: Path, rel_path: str, content: str) -> None:
    path = repo / rel_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def write_bytes(repo: Path, rel_path: str, content: bytes) -> None:
    path = repo / rel_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)


def commit(repo: Path, message: str, files: list[str]) -> None:
    run_git(repo, "add", *files)
    run_git(repo, "commit", "-q", "-m", message)


def run_phase_gate(repo: Path) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, SCRIPT], cwd=repo, capture_output=True, text=True)


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    run_git(tmp_path, "init", "-q")
    run_git(tmp_path, "config", "user.email", "test@example.com")
    run_git(tmp_path, "config", "user.name", "Test")
    # check_agents_md_coupling() reads AGENTS.md unconditionally (BUG-038):
    # seed a minimal one so scratch repos pass it unless a test targets it.
    write(
        tmp_path,
        "AGENTS.md",
        'git commit --no-verify -m "docs: finalize specification"\n'
        'git commit --no-verify -m "docs: finalize system design"\n',
    )
    return tmp_path


def test_scenario_a_missing_checkpoints_rejected(repo: Path) -> None:
    write(repo, "README.md", "seed\n")
    commit(repo, "chore: seed repo", ["README.md"])

    write(repo, "apps/api/app/foo.py", "x = 1\n")
    run_git(repo, "add", "apps/api/app/foo.py")

    result = run_phase_gate(repo)
    assert result.returncode == 1
    assert "missing spec.md checkpoint commit" in result.stderr
    assert "missing design.md checkpoint commit" in result.stderr


def test_scenario_b_mixed_staging_rejected(repo: Path) -> None:
    write(repo, "README.md", "seed\n")
    commit(repo, "chore: seed repo", ["README.md"])

    write(repo, "spec.md", "spec content\n")
    write(repo, "apps/api/app/foo.py", "x = 1\n")
    run_git(repo, "add", "spec.md", "apps/api/app/foo.py")

    result = run_phase_gate(repo)
    assert result.returncode == 1
    assert "Doc files staged:    spec.md" in result.stderr
    assert "Source files staged: apps/api/app/foo.py" in result.stderr


def test_scenario_c_threshold_lowered_requires_ledger(repo: Path) -> None:
    write(repo, "apps/api/tests/test_x.py", 'assert grades["score"] >= 0.90\n')
    commit(repo, "chore: seed test", ["apps/api/tests/test_x.py"])
    write(repo, "spec.md", "spec\n")
    commit(repo, "docs: finalize specification", ["spec.md"])
    spec_commit = run_git(repo, "rev-parse", "HEAD").stdout.strip()
    run_git(repo, "notes", "--ref=approvals", "add", "-m", "approved", spec_commit)
    write(repo, "design.md", "design\n")
    commit(repo, "docs: finalize system design", ["design.md"])
    design_commit = run_git(repo, "rev-parse", "HEAD").stdout.strip()
    run_git(repo, "notes", "--ref=approvals", "add", "-m", "approved", design_commit)

    write(repo, "apps/api/tests/test_x.py", 'assert grades["score"] >= 0.20\n')
    run_git(repo, "add", "apps/api/tests/test_x.py")

    result = run_phase_gate(repo)
    assert result.returncode == 1
    assert "passing-threshold literal was lowered" in result.stderr

    write(repo, "docs/DEFECT_LEDGER.md", "## [BUG-XXX]\n")
    run_git(repo, "add", "docs/DEFECT_LEDGER.md")

    result = run_phase_gate(repo)
    assert result.returncode == 0, result.stderr


def test_positive_case_fresh_checkpoints_pass(repo: Path) -> None:
    write(repo, "apps/api/app/foo.py", "x = 1\n")
    commit(repo, "feat: initial", ["apps/api/app/foo.py"])
    write(repo, "spec.md", "spec\n")
    commit(repo, "docs: finalize specification", ["spec.md"])
    spec_commit = run_git(repo, "rev-parse", "HEAD").stdout.strip()
    run_git(repo, "notes", "--ref=approvals", "add", "-m", "approved", spec_commit)
    write(repo, "design.md", "design\n")
    commit(repo, "docs: finalize system design", ["design.md"])
    design_commit = run_git(repo, "rev-parse", "HEAD").stdout.strip()
    run_git(repo, "notes", "--ref=approvals", "add", "-m", "approved", design_commit)

    write(repo, "apps/api/app/foo.py", "x = 2\n")
    run_git(repo, "add", "apps/api/app/foo.py")

    result = run_phase_gate(repo)
    assert result.returncode == 0, result.stderr


def test_stale_spec_checkpoint_rejected(repo: Path) -> None:
    """spec/design committed once, then code changes again -> must redo Phase 1/2."""
    write(repo, "spec.md", "spec\n")
    commit(repo, "docs: finalize specification", ["spec.md"])
    write(repo, "design.md", "design\n")
    commit(repo, "docs: finalize system design", ["design.md"])
    write(repo, "apps/api/app/foo.py", "x = 1\n")
    commit(repo, "feat: initial", ["apps/api/app/foo.py"])

    write(repo, "apps/api/app/foo.py", "x = 2\n")
    run_git(repo, "add", "apps/api/app/foo.py")

    result = run_phase_gate(repo)
    assert result.returncode == 1
    assert "spec.md checkpoint is older than the last code change" in result.stderr
    assert "design.md checkpoint is older than the last code change" in result.stderr


def test_utf8_check_rejects_non_utf8_checkpoint(repo: Path) -> None:
    write(repo, "README.md", "seed\n")
    commit(repo, "chore: seed repo", ["README.md"])

    write_bytes(repo, "spec.md", "spec content\n".encode("utf-16-le"))
    run_git(repo, "add", "spec.md")

    result = run_phase_gate(repo)
    assert result.returncode == 1
    assert "not valid UTF-8" in result.stderr
    assert "spec.md" in result.stderr


def test_utf8_check_passes_valid_utf8_checkpoint(repo: Path) -> None:
    write(repo, "README.md", "seed\n")
    commit(repo, "chore: seed repo", ["README.md"])

    write(repo, "spec.md", "spec content\n")
    run_git(repo, "add", "spec.md")

    result = run_phase_gate(repo)
    assert result.returncode == 0, result.stderr


def test_approval_evidence_rejects_design_without_spec_note(repo: Path) -> None:
    write(repo, "spec.md", "spec\n")
    commit(repo, "docs: finalize specification", ["spec.md"])

    write(repo, "design.md", "design\n")
    run_git(repo, "add", "design.md")

    result = run_phase_gate(repo)
    assert result.returncode == 1
    assert "missing human approval evidence" in result.stderr
    assert "spec.md checkpoint" in result.stderr
    assert "has no approval note" in result.stderr


def test_approval_evidence_accepts_design_with_spec_note(repo: Path) -> None:
    write(repo, "spec.md", "spec\n")
    commit(repo, "docs: finalize specification", ["spec.md"])
    spec_commit = run_git(repo, "rev-parse", "HEAD").stdout.strip()
    run_git(repo, "notes", "--ref=approvals", "add", "-m", "approved", spec_commit)

    write(repo, "design.md", "design\n")
    run_git(repo, "add", "design.md")

    result = run_phase_gate(repo)
    assert result.returncode == 0, result.stderr


def test_approval_evidence_gates_source_commit_on_design_note(repo: Path) -> None:
    write(repo, "spec.md", "spec\n")
    commit(repo, "docs: finalize specification", ["spec.md"])
    spec_commit = run_git(repo, "rev-parse", "HEAD").stdout.strip()
    run_git(repo, "notes", "--ref=approvals", "add", "-m", "approved", spec_commit)

    write(repo, "design.md", "design\n")
    commit(repo, "docs: finalize system design", ["design.md"])
    design_commit = run_git(repo, "rev-parse", "HEAD").stdout.strip()

    write(repo, "apps/api/app/foo.py", "x = 1\n")
    run_git(repo, "add", "apps/api/app/foo.py")

    result = run_phase_gate(repo)
    assert result.returncode == 1
    assert "missing human approval evidence" in result.stderr
    assert "design.md checkpoint" in result.stderr

    run_git(repo, "notes", "--ref=approvals", "add", "-m", "approved", design_commit)
    result = run_phase_gate(repo)
    assert result.returncode == 0, result.stderr


def test_approval_evidence_note_on_wrong_commit_rejected(repo: Path) -> None:
    write(repo, "README.md", "seed\n")
    commit(repo, "chore: seed repo", ["README.md"])
    wrong_commit = run_git(repo, "rev-parse", "HEAD").stdout.strip()
    run_git(repo, "notes", "--ref=approvals", "add", "-m", "approved", wrong_commit)

    write(repo, "spec.md", "spec\n")
    commit(repo, "docs: finalize specification", ["spec.md"])

    write(repo, "design.md", "design\n")
    run_git(repo, "add", "design.md")

    result = run_phase_gate(repo)
    assert result.returncode == 1
    assert "missing human approval evidence" in result.stderr
