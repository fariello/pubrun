#!/usr/bin/env python3
"""Test 00: Auto-start on import.

Verifies that `import pubrun` starts tracking without explicit API calls.
"""
import pubrun
from pubrun.tracker import get_current_run


def main() -> None:
    print("Testing 00_auto_start...")

    tracker = get_current_run()
    assert tracker is not None, "Auto-start did not initialize a run."

    run_dir = getattr(tracker, "run_dir", None)
    assert run_dir is not None, "Run directory not created."

    print("[PASS] PASS: 00_auto_start.py")


if __name__ == "__main__":
    main()
