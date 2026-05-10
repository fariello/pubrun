#!/usr/bin/env python3
"""Test 05: Execution phases.

Verifies that phase() context managers write start/end events to events.jsonl.
"""
import os
os.environ["PUBRUN_AUTO_START"] = "false"
import json
import time
import pubrun


def main() -> None:
    print("Testing 05_execution_phases...")
    tracker = pubrun.start(profile="minimal")
    run_dir = getattr(tracker, "run_dir", getattr(tracker, "_run_dir", None))

    with pubrun.phase("Dataset Initialization"):
        time.sleep(0.01)

    with pubrun.phase("Epoch Optimization"):
        time.sleep(0.01)

    pubrun.stop()

    events_path = os.path.join(run_dir, "events.jsonl")
    assert os.path.exists(events_path)

    opened = 0
    closed = 0
    with open(events_path, "r", encoding="utf-8") as f:
        for line in f:
            obj = json.loads(line)
            if obj.get("type") == "phase_start":
                opened += 1
            elif obj.get("type") == "phase_end":
                closed += 1

    assert opened == 2 and closed == 2, f"Expected 2 phase pairs, got {opened} starts and {closed} ends."
    print("[PASS] PASS: 05_execution_phases.py")


if __name__ == "__main__":
    main()
