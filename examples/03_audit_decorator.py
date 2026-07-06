#!/usr/bin/env python3
"""Test 03: audit_run decorator.

Verifies that the decorator tracks both successful and failing functions.
"""
import os
os.environ["PUBRUN_AUTO_START"] = "false"
import json
import pubrun
from pubrun.tracker import get_current_run


@pubrun.audit_run(profile="minimal")
def success_task() -> str:
    """Return the run directory path."""
    tracker = get_current_run()
    return getattr(tracker, "run_dir", getattr(tracker, "_run_dir", None))


@pubrun.audit_run(profile="minimal")
def failing_task() -> None:
    """Raise an exception to test failure recording."""
    tracker = get_current_run()
    global global_fail_dir
    global_fail_dir = getattr(tracker, "run_dir", getattr(tracker, "_run_dir", None))
    raise ValueError("Intentional test crash.")


global_fail_dir = None


def main() -> None:
    print("Testing 03_audit_decorator...")

    # Test successful execution
    success_dir = success_task()
    assert os.path.exists(os.path.join(success_dir, "manifest.json")), "Success run did not write manifest."

    # Test failing execution
    try:
        failing_task()
    except ValueError:
        pass

    assert global_fail_dir is not None, "Failing task did not record run directory."
    fail_manifest = os.path.join(global_fail_dir, "manifest.json")
    assert os.path.exists(fail_manifest), "Failing run did not write manifest."

    with open(fail_manifest, "r", encoding="utf-8") as f:
        payload = json.load(f)
        assert payload.get("status", {}).get("outcome") == "failed", "Failure not recorded in manifest outcome."

    print("[PASS] PASS: 03_audit_decorator.py")


if __name__ == "__main__":
    main()
