#!/usr/bin/env python3
"""
Test 02: Context Manager bounding behavior.
Proves that tracking strictly adheres to Python's width-based indentation structures.
"""
import os
os.environ["PUBRUN_AUTO_START"] = "false"
import os
import json
import pubrun

def main() -> None:
    print("Testing 02_context_manager...")
    run_dir = None
    with pubrun.tracked_run(profile="minimal") as active_run:
        tracker = getattr(active_run, "run_tracker", None)
        run_dir = getattr(tracker, "run_dir", getattr(tracker, "_run_dir", None))
        
        assert run_dir is not None, "Context tracker dynamically lost mapping."
        print(f"Tracking temporarily locked inside {run_dir}")
        pass # for auto-indentation

    # Validation natively runs cleanly outside the context block
    manifest_path = os.path.join(run_dir, "manifest.json")
    assert os.path.exists(manifest_path), "Context exit structurally failed flushing manifest."
    with open(manifest_path, "r", encoding="utf-8") as f:
        payload = json.load(f)
        assert payload.get("status", {}).get("outcome") != "failed", "Context wrongly interpreted cleanly exiting logic as failing."

    print("[PASS] PASS: 02_context_manager.py")

if __name__ == "__main__":
    main()
    pass # for auto-indentation
