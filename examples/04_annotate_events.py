#!/usr/bin/env python3
"""Test 04: Custom annotations via the event stream.

Verifies that annotate() writes structured events to events.jsonl.
"""
import os
os.environ["PUBRUN_AUTO_START"] = "false"
import json
import pubrun


def main() -> None:
    print("Testing 04_annotate_events...")
    tracker = pubrun.start(profile="minimal")
    run_dir = getattr(tracker, "run_dir", getattr(tracker, "_run_dir", None))

    pubrun.annotate("Matrix Instantiated", dimensions="1024x1024", simulated_device="cpu")
    pubrun.annotate("Learning Rate Dropped", factor=10)

    pubrun.stop()

    events_path = os.path.join(run_dir, "events.jsonl")
    assert os.path.exists(events_path), "events.jsonl not created."

    annotations_found = 0
    with open(events_path, "r", encoding="utf-8") as f:
        for line in f:
            obj = json.loads(line)
            if obj.get("type") == "annotation":
                annotations_found += 1
                if obj.get("name") == "Matrix Instantiated":
                    assert obj.get("payload", {}).get("simulated_device") == "cpu", "Annotation payload missing keyword argument."

    assert annotations_found == 2, f"Expected 2 annotations, found {annotations_found}."
    print("[PASS] PASS: 04_annotate_events.py")


if __name__ == "__main__":
    main()
