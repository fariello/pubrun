#!/usr/bin/env python3
"""Test 02: Context manager lifecycle.

Verifies that tracked_run() scopes tracking to the with-block.
"""
import os
os.environ["PUBRUN_AUTO_START"] = "false"
import json
import pubrun


def main() -> None:
    print("Testing 02_context_manager...")
    run_dir = None
    with pubrun.tracked_run(profile="minimal") as active_run:
        tracker = getattr(active_run, "run_tracker", None)
        run_dir = getattr(tracker, "run_dir", getattr(tracker, "_run_dir", None))
        assert run_dir is not None, "Run directory not accessible inside context."
        print(f"Tracking active in {run_dir}")

    # After the context block, the manifest should exist
    manifest_path = os.path.join(run_dir, "manifest.json")
    assert os.path.exists(manifest_path), "Manifest not written on context exit."
    with open(manifest_path, "r", encoding="utf-8") as f:
        payload = json.load(f)
        assert payload.get("status", {}).get("outcome") != "failed", "Clean exit incorrectly recorded as failed."

    print("[PASS] PASS: 02_context_manager.py")


if __name__ == "__main__":
    main()
