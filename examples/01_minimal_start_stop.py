#!/usr/bin/env python3
"""Test 01: Explicit start/stop lifecycle.

Verifies manual initialization, tracking, and manifest generation.
"""
import os
os.environ["PUBRUN_AUTO_START"] = "false"
import json
import pubrun


def main() -> None:
    print("Testing 01_minimal_start_stop...")
    tracker = pubrun.start(profile="minimal")

    run_dir = getattr(tracker, "run_dir", getattr(tracker, "_run_dir", None))
    assert run_dir is not None, "Run directory not created."

    print(f"Tracking active in {run_dir}")

    pubrun.stop()

    manifest_path = os.path.join(run_dir, "manifest.json")
    assert os.path.exists(manifest_path), f"Manifest not found at {manifest_path}"

    with open(manifest_path, "r", encoding="utf-8") as f:
        payload = json.load(f)
        assert "environment" in payload, "Manifest missing environment section."
        assert "hardware" in payload, "Manifest missing hardware section."

    print("[PASS] PASS: 01_minimal_start_stop.py")


if __name__ == "__main__":
    main()
