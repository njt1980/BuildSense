#!/usr/bin/env python3
"""Keep CLAUDE.md and .cursorrules in sync with AGENTS.md.

See /spec.md section 2.3 and /design.md section 2.3. AGENTS.md is the single
source of truth (natively auto-loaded by Codex CLI, Google Antigravity, and
GitHub Copilot's coding agent per design.md 2.2). Claude Code and Cursor do
not have confirmed native AGENTS.md support in this environment, so CLAUDE.md
and .cursorrules are kept as generated mirrors, defense-in-depth against that
assumption being wrong for a given tool version.

Usage:
  python scripts/sync_agent_rules.py --write   # regenerate both files
  python scripts/sync_agent_rules.py --check   # verify both are up to date (hook use)
"""

from __future__ import annotations

import argparse
import hashlib
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SOURCE_FILE = REPO_ROOT / "AGENTS.md"
GENERATED_FILES = {
    "CLAUDE.md": "Claude Code",
    ".cursorrules": "Cursor",
}
MARKER_RE = re.compile(r"<!-- AGENTS\.md sha256: ([0-9a-f]{64}) -->")

BANNER_TEMPLATE = """<!-- GENERATED FILE: do not edit directly. Source of truth is AGENTS.md.
     Regenerate with: python scripts/sync_agent_rules.py --write -->

"""


def source_hash() -> str:
    return hashlib.sha256(SOURCE_FILE.read_bytes()).hexdigest()


def render_generated_content(digest: str) -> str:
    source_text = SOURCE_FILE.read_text(encoding="utf-8")
    return f"{BANNER_TEMPLATE}{source_text}\n<!-- AGENTS.md sha256: {digest} -->\n"


def write_mode() -> int:
    digest = source_hash()
    content = render_generated_content(digest)
    for filename in GENERATED_FILES:
        (REPO_ROOT / filename).write_text(content, encoding="utf-8")
        print(f"Wrote {filename} from AGENTS.md (sha256 {digest[:12]}...)")
    return 0


def check_mode() -> int:
    if not SOURCE_FILE.exists():
        print("PHASE GATE: AGENTS.md not found at repo root.", file=sys.stderr)
        return 1

    digest = source_hash()
    stale = []
    for filename, tool_name in GENERATED_FILES.items():
        path = REPO_ROOT / filename
        if not path.exists():
            stale.append(f"{filename} ({tool_name}) does not exist")
            continue
        match = MARKER_RE.search(path.read_text(encoding="utf-8"))
        if not match or match.group(1) != digest:
            stale.append(f"{filename} ({tool_name}) is stale or missing its sha256 marker")

    if not stale:
        return 0

    print(
        "PHASE GATE: AGENTS.md changed but CLAUDE.md/.cursorrules were not",
        file=sys.stderr,
    )
    print("regenerated. Run: python scripts/sync_agent_rules.py --write", file=sys.stderr)
    for line in stale:
        print(f"  - {line}", file=sys.stderr)
    return 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true", help="Regenerate CLAUDE.md and .cursorrules")
    mode.add_argument("--check", action="store_true", help="Verify both are up to date; exit 1 if stale")
    args = parser.parse_args()

    if args.write:
        return write_mode()
    return check_mode()


if __name__ == "__main__":
    sys.exit(main())
