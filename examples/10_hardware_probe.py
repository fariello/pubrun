#!/usr/bin/env python3
"""Test 10: Hardware capture with deep profile.

Creates a deep-profile run that allocates memory, then verifies the manifest
contains hardware data (cpu, memory).
"""
import os
os.environ["PUBRUN_AUTO_START"] = "false"
import json
import pubrun


def main() -> None:
    print("Testing 10_hardware_probe...")
    with pubrun.tracked_run(profile="deep") as active:
        run_dir = getattr(getattr(active, "run_tracker", active), "run_dir", None)

        # Allocate some memory so resource monitoring has something to see
        _ = [list(range(5000)) for _ in range(500)]

    manifest_path = os.path.join(run_dir, "manifest.json")
    with open(manifest_path, "r", encoding="utf-8") as f:
        payload = json.load(f)

    hardware = payload.get("hardware", {})
    assert "cpu" in hardware, "Hardware section missing cpu data."
    mem_flag = any("mem" in k.lower() for k in hardware.keys())
    assert mem_flag, "Hardware section missing memory data."

    print("[PASS] PASS: 10_hardware_probe.py")


if __name__ == "__main__":
    main()
