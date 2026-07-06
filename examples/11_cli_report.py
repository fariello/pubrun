#!/usr/bin/env python3
"""Test 11: CLI report generation.

Creates a run and invokes `pubrun report` via subprocess, then verifies
the output contains expected diagnostic headers and fields.
"""
import os
os.environ["PUBRUN_AUTO_START"] = "false"
import subprocess
import sys
import pubrun


def main() -> None:
    print("Testing 11_cli_report...")

    tracker = pubrun.start(profile="standard")
    tracker.stop()

    cmd = [sys.executable, "-m", "pubrun", "report"]
    result = subprocess.run(cmd, capture_output=True, text=True)

    output = result.stdout.strip()

    assert "PUBRUN DIAGNOSTICS" in output, "Report missing header."
    assert "Run ID" in output, "Report missing Run ID field."

    print("[PASS] PASS: 11_cli_report.py")


if __name__ == "__main__":
    main()
