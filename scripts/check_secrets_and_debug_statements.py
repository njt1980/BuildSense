#!/usr/bin/env python3
"""Secrets and stray-debug-statement lint for application source only.

See /spec.md section 2.1 and /design.md Step 1 for the requirements this
implements. Pure stdlib, git-plumbing only, independent of the apps/api
virtualenv so it can run from the pre-commit hook without any project
dependencies installed — mirrors scripts/check_phase_gate.py's approach.

Scope is deliberately narrow: only apps/api/app/**/*.py and
apps/web/src/**/*.{ts,tsx} are scanned. scripts/, apps/api/tests/,
apps/api/evals/, and .env.example are excluded because print()/placeholder
key names are legitimate there.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys

SOURCE_PATTERNS = [r"^apps/api/app/.*\.py$", r"^apps/web/src/.*\.(ts|tsx)$"]

DEBUG_STATEMENT_RES = {
    ".py": re.compile(r"print\("),
    ".ts": re.compile(r"console\.log\("),
    ".tsx": re.compile(r"console\.log\("),
}

SECRET_RES = {
    "aws-access-key": re.compile(r"AKIA[0-9A-Z]{16}"),
    "private-key-header": re.compile(
        r"-----BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY-----"
    ),
    "assigned-secret-literal": re.compile(
        r"""(api[_-]?key|secret|token|password)\s*[:=]\s*["'][A-Za-z0-9+/=_-]{16,}["']""",
        re.IGNORECASE,
    ),
}


def run_git(args: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], capture_output=True, text=True)


def is_scoped_file(path: str) -> bool:
    return any(re.match(pattern, path) for pattern in SOURCE_PATTERNS)


def get_staged_files() -> list[str]:
    result = run_git(["diff", "--cached", "--name-only", "--diff-filter=ACM"])
    return [line for line in result.stdout.splitlines() if line]


def file_extension(path: str) -> str:
    for ext in (".tsx", ".ts", ".py"):
        if path.endswith(ext):
            return ext
    return ""


def scan_file(path: str) -> list[str]:
    """Return finding lines ('file:line: category') for one scoped file."""
    try:
        with open(path, encoding="utf-8") as handle:
            lines = handle.readlines()
    except OSError:
        return []

    ext = file_extension(path)
    debug_re = DEBUG_STATEMENT_RES.get(ext)
    findings = []

    for lineno, line in enumerate(lines, start=1):
        if debug_re and debug_re.search(line):
            category = "print(" if ext == ".py" else "console.log("
            findings.append(f"{path}:{lineno}: debug-statement ({category})")
        for category, pattern in SECRET_RES.items():
            if pattern.search(line):
                findings.append(f"{path}:{lineno}: secret ({category})")

    return findings


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--staged-files",
        nargs="*",
        default=None,
        help="Override the staged file list (test harness use only, bypasses git diff --cached).",
    )
    args = parser.parse_args()

    staged = args.staged_files if args.staged_files is not None else get_staged_files()
    scoped_files = [f for f in staged if is_scoped_file(f)]

    all_findings: list[str] = []
    for path in scoped_files:
        all_findings.extend(scan_file(path))

    if not all_findings:
        return 0

    print("SECRETS/DEBUG LINT: found the following issues:", file=sys.stderr)
    for finding in all_findings:
        print(f"  {finding}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
