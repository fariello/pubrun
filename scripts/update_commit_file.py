#!/usr/bin/env python3
"""Refresh the packaged commit-hash file (`src/pubrun/COMMIT`) to the current HEAD.

A file cannot record its own commit's hash, so this runs as a git POST-COMMIT hook: after a
commit lands, it stamps `src/pubrun/COMMIT` with that commit's hash and stages the file so the
value is carried into the NEXT commit (and into any wheel built from this checkout). At
runtime `pubrun.__commit__` prefers the LIVE `git rev-parse HEAD`, so a checkout always
reports the exact commit; this file is the fallback for installed wheels.

Idempotent and side-effect-light: if `COMMIT` already matches HEAD, it does nothing (so it
does not create churn or restage on every commit). stdlib only.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
_COMMIT_FILE = _REPO / "src" / "pubrun" / "COMMIT"


def _head() -> str:
    proc = subprocess.run(
        ["git", "-C", str(_REPO), "rev-parse", "HEAD"],
        capture_output=True, text=True, timeout=10,
    )
    if proc.returncode != 0:
        raise SystemExit(0)  # not a git context; nothing to do (never block)
    return proc.stdout.strip()


def main() -> int:
    try:
        head = _head()
    except Exception:
        return 0  # best-effort; never block or fail a commit
    if not head:
        return 0
    current = _COMMIT_FILE.read_text(encoding="utf-8").strip() if _COMMIT_FILE.exists() else ""
    if current == head:
        return 0  # already current; no churn
    _COMMIT_FILE.write_text(head + "\n", encoding="utf-8")
    # Stage it so the refreshed value rides along with the next commit / build.
    subprocess.run(["git", "-C", str(_REPO), "add", "--", str(_COMMIT_FILE)],
                   capture_output=True, text=True, timeout=10)
    print(f"[update_commit_file] src/pubrun/COMMIT -> {head}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
