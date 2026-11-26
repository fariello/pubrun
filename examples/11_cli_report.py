#!/usr/bin/env python3
"""Test 11: CLI diagnostic output via `pubrun show`.

Creates a run and invokes `pubrun show` via subprocess (`pubrun report`
remains a hidden legacy alias), then verifies the output contains expected
diagnostic headers and fields.
"""
import subprocess
import sys
import pubrun.noauto as pubrun


def main() -> None:
    print("Testing 11_cli_report...")

    tracker = pubrun.start()
    tracker.stop()

    cmd = [sys.executable, "-m", "pubrun", "show"]
    result = subprocess.run(cmd, capture_output=True, text=True)

    output = result.stdout.strip()

    assert "PUBRUN DIAGNOSTICS" in output, "Report missing header."
    assert "Run ID" in output, "Report missing Run ID field."

    print("[PASS] PASS: 11_cli_report.py")


if __name__ == "__main__":
    main()
