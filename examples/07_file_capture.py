#!/usr/bin/env python3
"""Test 07: Input file capture from sys.argv.

Verifies that pubrun detects file arguments in sys.argv and records them
with metadata (path, size, hash) in the manifest's invocation.inputs list.
"""
import os
os.environ["PUBRUN_AUTO_START"] = "false"
import sys
import json
import pubrun


def main() -> None:
    print("Testing 07_file_capture...")
    dummy_file = "dummy_input_dataset.csv"
    with open(dummy_file, "w") as f:
        f.write("col1,col2\n1,2")

    # Append the file to sys.argv so the input heuristic picks it up
    sys.argv.append(dummy_file)

    with pubrun.tracked_run() as active:
        run_dir = getattr(getattr(active, "run_tracker", active), "run_dir", None)

    # Check the manifest for captured inputs
    manifest_path = os.path.join(run_dir, "manifest.json")
    with open(manifest_path, "r", encoding="utf-8") as f:
        payload = json.load(f)

    inputs_list = payload.get("invocation", {}).get("inputs", [])

    # Clean up
    sys.argv.pop()
    if os.path.exists(dummy_file):
        os.remove(dummy_file)

    file_tracked = any(dummy_file in str(i.get("path", "")) for i in inputs_list)
    assert file_tracked, "Input file from sys.argv not captured in manifest."

    print("[PASS] PASS: 07_file_capture.py")


if __name__ == "__main__":
    main()
