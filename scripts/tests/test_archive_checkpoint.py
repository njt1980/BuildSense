"""Tests for scripts/archive_checkpoint.py against disposable scratch git repos.

Run via: pytest scripts/tests/ -q (deliberately independent of apps/api/pyproject.toml).
See spec.md section 4.2 and design.md section 4.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT = str(Path(__file__).resolve().parent.parent / "archive_checkpoint.py")


def run_git(repo: Path, *args: str) -> subprocess.CompletedProcess:
    result = subprocess.run(["git", *args], cwd=repo, capture_output=True, text=True)
    assert result.returncode == 0, f"git {' '.join(args)} failed: {result.stderr}"
    return result


def write(repo: Path, rel_path: str, content: str) -> None:
    path = repo / rel_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def commit(repo: Path, message: str, files: list[str]) -> None:
    run_git(repo, "add", *files)
    run_git(repo, "commit", "-q", "-m", message)


def run_archive(repo: Path, phase: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, SCRIPT, "--phase", phase],
        cwd=repo,
        capture_output=True,
        text=True,
    )


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    run_git(tmp_path, "init", "-q")
    run_git(tmp_path, "config", "user.email", "test@example.com")
    run_git(tmp_path, "config", "user.name", "Test")
    return tmp_path


def test_phase_spec_creates_first_ticket(repo: Path) -> None:
    write(repo, "spec.md", "# Specification: Widget Thing\n\nBody.\n")
    commit(repo, "docs: finalize specification", ["spec.md"])

    result = run_archive(repo, "spec")
    assert result.returncode == 0, result.stderr

    assert (repo / "docs/tickets/.next_id").read_text(encoding="utf-8").strip() == "2"

    index = json.loads((repo / "docs/cycles/index.json").read_text(encoding="utf-8"))
    assert len(index) == 1
    assert index[0]["ticket"] == "BS-1"
    assert index[0]["slug"] == "widget-thing"
    assert index[0]["design_commit"] is None
    assert index[0]["source_commits"] == []

    archived_spec = repo / "docs/cycles/BS-1-widget-thing/spec.md"
    assert archived_spec.exists()
    assert "Widget Thing" in archived_spec.read_text(encoding="utf-8")

    index_md = (repo / "docs/cycles/INDEX.md").read_text(encoding="utf-8")
    assert "BS-1" in index_md
    assert "widget-thing" in index_md


def test_phase_design_fills_in_open_ticket(repo: Path) -> None:
    write(repo, "spec.md", "# Specification: Widget Thing\n\nBody.\n")
    commit(repo, "docs: finalize specification", ["spec.md"])
    spec_result = run_archive(repo, "spec")
    assert spec_result.returncode == 0, spec_result.stderr

    write(repo, "design.md", "# System Design: Widget Thing\n\nBody.\n")
    commit(repo, "docs: finalize system design", ["design.md"])

    result = run_archive(repo, "design")
    assert result.returncode == 0, result.stderr

    index = json.loads((repo / "docs/cycles/index.json").read_text(encoding="utf-8"))
    assert len(index) == 1
    assert index[0]["ticket"] == "BS-1"
    assert index[0]["design_commit"] is not None

    archived_design = repo / "docs/cycles/BS-1-widget-thing/design.md"
    assert archived_design.exists()
    assert "Widget Thing" in archived_design.read_text(encoding="utf-8")

    index_md = (repo / "docs/cycles/INDEX.md").read_text(encoding="utf-8")
    assert index_md.count("BS-1") == 1


def test_phase_design_with_no_open_ticket_errors(repo: Path) -> None:
    result = run_archive(repo, "design")
    assert result.returncode == 1
    assert "no open ticket" in result.stderr
