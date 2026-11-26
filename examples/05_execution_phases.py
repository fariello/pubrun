#!/usr/bin/env python3
"""Test 05: Execution phases.

Verifies that phase() context managers write start/end events to events.jsonl,
that each phase_end event carries a monotonic duration, and that the finalized
manifest separates the tracked workload from pubrun's own capture overhead.
"""
import os
import json
import time
import pubrun.noauto as pubrun


def _is_duration(value: object) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and value >= 0


def main() -> None:
    print("Testing 05_execution_phases...")
    tracker = pubrun.start()
    run_dir = getattr(tracker, "run_dir", getattr(tracker, "_run_dir", None))

    with pubrun.phase("Dataset Initialization"):
        time.sleep(0.01)

    with pubrun.phase("Epoch Optimization"):
        time.sleep(0.01)

    pubrun.stop()

    events_path = os.path.join(run_dir, "events.jsonl")
    assert os.path.exists(events_path)

    opened = 0
    phase_durations = {}
    with open(events_path, "r", encoding="utf-8") as f:
        for line in f:
            obj = json.loads(line)
            if obj.get("type") == "phase_start":
                opened += 1
            elif obj.get("type") == "phase_end":
                payload = obj.get("payload") or {}
                elapsed = payload.get("elapsed_seconds")
                assert _is_duration(elapsed), f"phase_end elapsed_seconds is not a nonnegative number: {elapsed!r}"
                assert payload.get("duration_clock") == "monotonic", (
                    f"phase_end duration_clock is {payload.get('duration_clock')!r}, expected 'monotonic'"
                )
                phase_durations[obj.get("name")] = elapsed

    closed = len(phase_durations)
    assert opened == 2 and closed == 2, f"Expected 2 phase pairs, got {opened} starts and {closed} ends."

    with open(os.path.join(run_dir, "manifest.json"), "r", encoding="utf-8") as f:
        timing = json.load(f)["timing"]
    assert timing.get("duration_clock") == "monotonic", f"timing.duration_clock is {timing.get('duration_clock')!r}"
    assert timing.get("elapsed_basis") == "workload", f"timing.elapsed_basis is {timing.get('elapsed_basis')!r}"
    assert timing.get("interval_scope") == "tracked_interval", f"timing.interval_scope is {timing.get('interval_scope')!r}"
    for key in ("workload_seconds", "startup_overhead_seconds", "finalization_overhead_seconds", "session_seconds"):
        assert _is_duration(timing.get(key)), f"timing.{key} is not a nonnegative number: {timing.get(key)!r}"
    assert timing["elapsed_seconds"] == timing["workload_seconds"]
    assert timing["workload_seconds"] >= sum(phase_durations.values()), "phases should fit inside the tracked workload"

    print("  What was measured (monotonic clock, so wall-clock changes cannot distort it):")
    for name, elapsed in phase_durations.items():
        print(f"    phase {name!r}: {elapsed * 1000:.1f} ms of your code")
    print(f"    tracked workload (start() returned to stop() called): {timing['workload_seconds'] * 1000:.1f} ms")
    print(f"    pubrun startup capture, not part of the workload: {timing['startup_overhead_seconds'] * 1000:.1f} ms")
    print(f"    pubrun finalization before manifest.json, not part of the workload: "
          f"{timing['finalization_overhead_seconds'] * 1000:.1f} ms")
    print("  Time before pubrun.start() is outside the tracked interval and is not measured.")
    print("[PASS] PASS: 05_execution_phases.py")


if __name__ == "__main__":
    main()
