#!/usr/bin/env python3
"""Per-cycle checkpoint archive for spec.md/design.md (BS-<N> ticket scheme).

See /spec.md section 4.2 and /design.md section 4 for the requirements and
design this implements. Run explicitly by the agent right after each
"docs: finalize specification"/"docs: finalize system design" commit
succeeds -- not wired into the git hook, so archiving stays a visible,
deliberate step (spec 4.2) rather than silent hook behavior. Pure stdlib,
git-plumbing only, independent of the apps/api virtualenv, matching
check_phase_gate.py's own dependency-free design.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

TICKETS_DIR = Path("docs/tickets")
NEXT_ID_FILE = TICKETS_DIR / ".next_id"
CYCLES_DIR = Path("docs/cycles")
INDEX_JSON = CYCLES_DIR / "index.json"
INDEX_MD = CYCLES_DIR / "INDEX.md"

HEADING_PREFIX_RE = re.compile(r"^(specification|system design):\s*", re.IGNORECASE)
NON_ALNUM_RE = re.compile(r"[^a-z0-9]+")


def run_git(args: list[str]) -> str:
    result = subprocess.run(["git", *args], capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed: {result.stderr}")
    return result.stdout


def slugify(first_heading: str) -> str:
    """Deterministic slug per design.md 4.5: strip a leading "Specification:"
    or "System Design:" prefix, lowercase, collapse non-alphanumerics to a
    single hyphen, and keep the first 5 hyphen-separated words.
    """
    text = HEADING_PREFIX_RE.sub("", first_heading).lower()
    text = NON_ALNUM_RE.sub("-", text).strip("-")
    return "-".join(text.split("-")[:5])


def first_heading(markdown_text: str) -> str:
    for line in markdown_text.splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return "untitled"


def allocate_ticket_id() -> int:
    """Single monotonic counter, never derived from directory counts or
    commit hashes (spec 4.2), so it survives manual cleanup of old archive
    folders.
    """
    TICKETS_DIR.mkdir(parents=True, exist_ok=True)
    if NEXT_ID_FILE.exists():
        n = int(NEXT_ID_FILE.read_text(encoding="utf-8").strip())
    else:
        n = 1
    NEXT_ID_FILE.write_text(f"{n + 1}\n", encoding="utf-8")
    return n


def load_index() -> list[dict]:
    if INDEX_JSON.exists():
        return json.loads(INDEX_JSON.read_text(encoding="utf-8"))
    return []


def save_index(entries: list[dict]) -> None:
    CYCLES_DIR.mkdir(parents=True, exist_ok=True)
    INDEX_JSON.write_text(json.dumps(entries, indent=2) + "\n", encoding="utf-8")
    regenerate_index_md(entries)


def regenerate_index_md(entries: list[dict]) -> None:
    """Human-readable table, fully rewritten from index.json each run --
    index.json (not this file) is the source of truth (design.md section 1).
    """
    lines = [
        "# Checkpoint Cycle Index",
        "",
        "Generated from `docs/cycles/index.json` by `scripts/archive_checkpoint.py`. Do not hand-edit.",
        "",
        "| Ticket | Slug | Spec Commit | Design Commit | Date | Source Commits |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for entry in entries:
        source_commits = ", ".join(entry.get("source_commits") or []) or "-"
        design_commit = entry.get("design_commit") or "-"
        lines.append(
            f"| {entry['ticket']} | {entry['slug']} | {entry['spec_commit']} | "
            f"{design_commit} | {entry['date']} | {source_commits} |"
        )
    INDEX_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def archive_spec() -> None:
    head = run_git(["rev-parse", "HEAD"]).strip()
    spec_content = run_git(["show", "HEAD:spec.md"])
    slug = slugify(first_heading(spec_content))
    ticket = f"BS-{allocate_ticket_id()}"

    cycle_dir = CYCLES_DIR / f"{ticket}-{slug}"
    cycle_dir.mkdir(parents=True, exist_ok=True)
    (cycle_dir / "spec.md").write_text(spec_content, encoding="utf-8")

    entries = load_index()
    entries.append(
        {
            "ticket": ticket,
            "slug": slug,
            "spec_commit": head,
            "design_commit": None,
            "source_commits": [],
            "date": datetime.now(timezone.utc).date().isoformat(),
        }
    )
    save_index(entries)
    print(f"Archived spec.md as {ticket} ({slug}) at {cycle_dir}")


def archive_design() -> None:
    entries = load_index()
    open_entries = [e for e in entries if e.get("design_commit") is None]
    if not open_entries:
        print(
            "archive_checkpoint.py --phase design: no open ticket "
            "(design_commit is null) found in docs/cycles/index.json. "
            "Run '--phase spec' first.",
            file=sys.stderr,
        )
        sys.exit(1)
    entry = open_entries[-1]

    head = run_git(["rev-parse", "HEAD"]).strip()
    design_content = run_git(["show", "HEAD:design.md"])

    cycle_dir = CYCLES_DIR / f"{entry['ticket']}-{entry['slug']}"
    cycle_dir.mkdir(parents=True, exist_ok=True)
    (cycle_dir / "design.md").write_text(design_content, encoding="utf-8")
    entry["design_commit"] = head

    save_index(entries)
    print(f"Archived design.md for {entry['ticket']} ({entry['slug']}) at {cycle_dir}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--phase", choices=["spec", "design"], required=True)
    args = parser.parse_args()

    if args.phase == "spec":
        archive_spec()
    else:
        archive_design()
    return 0


if __name__ == "__main__":
    sys.exit(main())
