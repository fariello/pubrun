#!/usr/bin/env python3
"""Test 09: CLI methods generation.

Creates a run, then invokes `pubrun methods --format markdown` via subprocess
and verifies the output contains expected methodology text.
"""
import os
os.environ["PUBRUN_AUTO_START"] = "false"
import subprocess
import sys
import pubrun


def main() -> None:
    print("Testing 09_cli_methods...")

    tracker = pubrun.start(profile="minimal")
    tracker.stop()

    cmd = [sys.executable, "-m", "pubrun", "methods", "--format", "markdown"]
    result = subprocess.run(cmd, capture_output=True, text=True)

    output = result.stdout.strip()

    checks = [
        "environment" in output.lower(),
        "python" in output.lower(),
        "executed on" in output.lower(),
        "computational" in output.lower(),
    ]

    assert any(checks), "Methods output did not contain expected methodology text."

    print("[PASS] PASS: 09_cli_methods.py")


if __name__ == "__main__":
    main()
