#!/usr/bin/env python3
"""Safe cleanup no-op for retired post-commit `src/pubrun/COMMIT` stamping.

`hatch_build.py` now stamps ownership-verified, version-tagged commit metadata
into wheel and source distribution artifacts at build time without writing files
into the working tree. This script remains in place as a quiet, deterministic
no-op for existing `post-commit` hook installations: it removes any stale
untracked `src/pubrun/COMMIT` file best-effort and exits 0 without launching
`git` or creating `src/pubrun/COMMIT`.
"""
from __future__ import annotations

from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
_COMMIT_FILE = _REPO / "src" / "pubrun" / "COMMIT"


def main() -> int:
    """Remove any stale `src/pubrun/COMMIT` file best-effort and exit 0."""
    try:
        _COMMIT_FILE.unlink()
    except (FileNotFoundError, OSError):
        pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
