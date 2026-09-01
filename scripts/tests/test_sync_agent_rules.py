"""Tests for scripts/sync_agent_rules.py against a disposable scratch directory.

Run via: pytest scripts/tests/ -q. See spec.md section 2.3 and design.md section 4.2.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent.parent / "sync_agent_rules.py"


def run_sync(repo: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args], cwd=repo, capture_output=True, text=True
    )


def _patch_repo_root(repo: Path) -> None:
    """sync_agent_rules.py resolves REPO_ROOT from its own file location, so
    tests copy the script next to a scratch AGENTS.md instead of monkeypatching."""
    (repo / "scripts").mkdir()
    script_copy = repo / "scripts" / "sync_agent_rules.py"
    script_copy.write_text(SCRIPT.read_text(encoding="utf-8"), encoding="utf-8")


def run_sync_in_place(repo: Path, *args: str) -> subprocess.CompletedProcess:
    script_copy = repo / "scripts" / "sync_agent_rules.py"
    return subprocess.run(
        [sys.executable, str(script_copy), *args], cwd=repo, capture_output=True, text=True
    )


def test_write_then_check_passes(tmp_path: Path) -> None:
    _patch_repo_root(tmp_path)
    (tmp_path / "AGENTS.md").write_text("# Rules\n\nDo the thing.\n", encoding="utf-8")

    write_result = run_sync_in_place(tmp_path, "--write")
    assert write_result.returncode == 0, write_result.stderr
    assert (tmp_path / "CLAUDE.md").exists()
    assert (tmp_path / ".cursorrules").exists()

    check_result = run_sync_in_place(tmp_path, "--check")
    assert check_result.returncode == 0, check_result.stderr


def test_stale_after_agents_md_mutated(tmp_path: Path) -> None:
    _patch_repo_root(tmp_path)
    (tmp_path / "AGENTS.md").write_text("# Rules\n\nDo the thing.\n", encoding="utf-8")

    run_sync_in_place(tmp_path, "--write")

    (tmp_path / "AGENTS.md").write_text("# Rules\n\nDo a different thing.\n", encoding="utf-8")

    check_result = run_sync_in_place(tmp_path, "--check")
    assert check_result.returncode == 1
    assert "were not" in check_result.stderr
    assert "sync_agent_rules.py --write" in check_result.stderr


def test_check_fails_when_generated_files_missing(tmp_path: Path) -> None:
    _patch_repo_root(tmp_path)
    (tmp_path / "AGENTS.md").write_text("# Rules\n", encoding="utf-8")

    check_result = run_sync_in_place(tmp_path, "--check")
    assert check_result.returncode == 1
    assert "CLAUDE.md" in check_result.stderr
    assert ".cursorrules" in check_result.stderr
