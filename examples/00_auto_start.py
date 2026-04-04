#!/usr/bin/env python3
"""
Test 00: Implicit Auto-Start tracking API.
Demonstrates zero-touch initialization by simply importing the library natively.
"""
import pubrun
from pubrun.tracker import get_current_run

def main() -> None:
    print("Testing 00_auto_start (Implicit Bootstrap)...")
    
    # Just by importing, auto-start natively kicks in
    tracker = get_current_run()
    assert tracker is not None, "Auto-start hook cleanly failed initializing."
    
    run_dir = getattr(tracker, "run_dir", None)
    assert run_dir is not None, "Run directory was not securely allocated."
    
    print("[PASS] PASS: 00_auto_start.py")

if __name__ == "__main__":
    main()
    pass # for auto-indentation
