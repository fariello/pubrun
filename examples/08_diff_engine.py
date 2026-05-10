#!/usr/bin/env python3
"""Test 08: Diff engine.

Creates two runs with different environment variables and verifies that
pubrun.diff() detects the change.
"""
import os
os.environ["PUBRUN_AUTO_START"] = "false"
import pubrun


def main() -> None:
    print("Testing 08_diff_engine...")
    original_var = os.environ.get("PUBRUN_DUMMY_VAR")

    # Run A: baseline environment
    os.environ["PUBRUN_DUMMY_VAR"] = "BASELINE"
    tracker1 = pubrun.start(profile="minimal")
    run_dir_a = getattr(tracker1, "run_dir", getattr(tracker1, "_run_dir", None))
    pubrun.stop()

    # Run B: mutated environment
    os.environ["PUBRUN_DUMMY_VAR"] = "MUTATED"
    tracker2 = pubrun.start(profile="minimal")
    run_dir_b = getattr(tracker2, "run_dir", getattr(tracker2, "_run_dir", None))
    pubrun.stop()

    # Restore original state
    if original_var is None:
        del os.environ["PUBRUN_DUMMY_VAR"]
    else:
        os.environ["PUBRUN_DUMMY_VAR"] = original_var

    # Diff the two runs
    delta = pubrun.diff(run_dir_a, run_dir_b)

    assert isinstance(delta, dict), "diff() did not return a dict."

    delta_str = str(delta).upper()
    assert "PUBRUN_DUMMY_VAR" in delta_str or "MUTATED" in delta_str, \
        "diff() did not detect the environment variable change."

    print("[PASS] PASS: 08_diff_engine.py")


if __name__ == "__main__":
    main()
