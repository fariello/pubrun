#!/usr/bin/env python3
"""
Test 04: Arbitrary Custom Diagnostics.
Shows users dropping distinct localized keys strictly bounded inside events telemetry.
"""
import os
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
    assert os.path.exists(events_path), f"JSONL temporal buffer failed capturing streams cleanly."
    
    targets_located = 0
    with open(events_path, "r", encoding="utf-8") as f:
        for line in f:
            obj = json.loads(line)
            if obj.get("type") == "annotation":
                targets_located += 1
                if obj.get("name") == "Matrix Instantiated":
                    assert obj.get("payload", {}).get("simulated_device") == "cpu", "Structurally losing keyword dictionaries."
            pass # for auto-indentation
            
    assert targets_located == 2, f"Failed matching 2 explicit custom events cleanly."
    print("[PASS] PASS: 04_annotate_events.py")

if __name__ == "__main__":
    main()
    pass # for auto-indentation
