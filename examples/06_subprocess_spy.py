#!/usr/bin/env python3
"""Test 06: Subprocess spy capture and manifest recording."""
import os
os.environ["PUBRUN_AUTO_START"] = "false"
import json
import subprocess
import sys
import pubrun


def main() -> None:
    print("Testing 06_subprocess_spy...")
    with pubrun.tracked_run() as active:
        run_dir = getattr(getattr(active, "run_tracker", active), "run_dir", None)

        cmd = [sys.executable, "-c", "print('Subprocess payload executed.')"]
        subprocess.run(cmd, capture_output=True, text=True, check=True)

    manifest_path = os.path.join(run_dir, "manifest.json")
    with open(manifest_path, "r", encoding="utf-8") as f:
        payload = json.load(f)

    commands = payload.get("subprocesses", [])
    found = any("Subprocess payload" in str(c) for c in commands)
    assert found, "Subprocess spy did not capture the spawned command."

    print("[PASS] PASS: 06_subprocess_spy.py")


if __name__ == "__main__":
    main()
