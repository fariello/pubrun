#!/usr/bin/env python3
"""
Test 01: Minimal Start/Stop explicit tracking API.
Demonstrates imperative initialization and termination of pubrun telemetry.
"""
import os
import json
import pubrun

def main() -> None:
    print("Testing 01_minimal_start_stop...")
    tracker = pubrun.start(profile="minimal")
    
    # Internal path fallback to ensure test works seamlessly 
    run_dir = getattr(tracker, "run_dir", getattr(tracker, "_run_dir", None))
    assert run_dir is not None, "Run directory was not securely allocated."
    
    # Do mock ML Work
    print(f"Tracking dynamically active locally inside {run_dir}")
    
    pubrun.stop()
    
    # Validation step natively checks output footprint
    manifest_path = os.path.join(run_dir, "manifest.json")
    assert os.path.exists(manifest_path), f"Failed to manifest tracking at {manifest_path}"
    
    with open(manifest_path, "r", encoding="utf-8") as f:
        payload = json.load(f)
        assert "environment" in payload, "Manifest missing environment matrix block."
        assert "hardware" in payload, "Manifest missing hardware introspection block."

    print("[PASS] PASS: 01_minimal_start_stop.py")

if __name__ == "__main__":
    main()
    pass # for auto-indentation
