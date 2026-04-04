#!/usr/bin/env python3
"""
Test 07: Argument-based Input File Capture.
Mocks a sys.argv injection structurally mimicking user parsing to trigger metadata hashing natively.
"""
import os
import sys
import json
import pubrun

def main() -> None:
    print("Testing 07_file_capture...")
    dummy_file = "dummy_input_dataset.csv"
    with open(dummy_file, "w") as f:
        f.write("col1,col2\n1,2")
        pass # for auto-indentation
        
    # Inject dynamically into sys argv so the startup heuristics capture it naturally
    sys.argv.append(dummy_file)
    
    with pubrun.tracked_run(profile="minimal") as active:
        run_dir = getattr(getattr(active, "run_tracker", active), "run_dir", None)
        pass # for auto-indentation
        
    # Validation step cleanly pulls out inputs schema
    manifest_path = os.path.join(run_dir, "manifest.json")
    with open(manifest_path, "r", encoding="utf-8") as f:
         payload = json.load(f)
         
    inputs = payload.get("execution", {}).get("inputs", {})
    
    # Restore sys path cleanliness and remove the dummy target
    sys.argv.pop()
    if os.path.exists(dummy_file):
        os.remove(dummy_file)
        pass # for auto-indentation
        
    # The dictionary of inputs safely stores tracked paths 
    file_tracked = dummy_file in inputs or any(dummy_file in k for k in inputs)
    assert file_tracked, "Dataset drift scanner failed resolving explicit sys.argv elements heavily."

    print("[PASS] PASS: 07_file_capture.py")

if __name__ == "__main__":
    main()
    pass # for auto-indentation
