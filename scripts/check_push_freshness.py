#!/usr/bin/env python3
"""Fail if the checked-out HEAD commit is older than a threshold.

See /spec.md section 2.3 and /design.md Step 3 for the requirements this
implements. Pure stdlib. Intended to run from a scheduled CI workflow
(.github/workflows/push-freshness.yml) against origin/master, so a stranded
local-only work stream (the incident this guards against: 76 commits sitting
unpushed for 5 days with zero CI runs against them) gets surfaced even when
nothing new is pushed to trigger push/PR-based workflows.

days_since() is kept as a standalone function (not inlined in the workflow's
shell step) specifically so it is unit-testable without waiting for an actual
stale commit.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from datetime import datetime, timezone

DEFAULT_MAX_DAYS = 3


def days_since(commit_iso_date: str, now: datetime | None = None) -> int:
    """Whole days elapsed between an ISO-8601 commit date and `now` (default: current UTC time)."""
    commit_dt = datetime.fromisoformat(commit_iso_date)
    reference = now if now is not None else datetime.now(timezone.utc)
    return (reference - commit_dt).days


def get_head_commit_date() -> str:
    result = subprocess.run(
        ["git", "log", "-1", "--format=%aI"],
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--max-days",
        type=int,
        default=DEFAULT_MAX_DAYS,
        help=f"Fail if HEAD is older than this many days (default: {DEFAULT_MAX_DAYS}).",
    )
    args = parser.parse_args()

    commit_date = get_head_commit_date()
    if not commit_date:
        print("PUSH FRESHNESS: could not determine HEAD commit date.", file=sys.stderr)
        return 1

    elapsed = days_since(commit_date)
    if elapsed > args.max_days:
        print(
            f"PUSH FRESHNESS: HEAD commit is {elapsed} day(s) old "
            f"(authored {commit_date}), exceeding the {args.max_days}-day threshold. "
            "No new commits have been pushed to this branch recently.",
            file=sys.stderr,
        )
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
