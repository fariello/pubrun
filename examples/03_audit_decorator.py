#!/usr/bin/env python3
"""
Test 03: The Function Audit Decorator.
Verifies programmatic telemetry bound structurally to pure functional components automatically.
"""
import os
import json
import pubrun
from pubrun.tracker import get_current_run

@pubrun.audit_run(profile="minimal")
def success_task() -> str:
    """A purely successful simulated functional branch."""
    tracker = get_current_run()
    return getattr(tracker, "run_dir", getattr(tracker, "_run_dir", None))

@pubrun.audit_run(profile="minimal")
def failing_task() -> None:
    """A functionally destructive trace explicitly simulating execution crash."""
    tracker = get_current_run()
    global global_fail_dir
    global_fail_dir = getattr(tracker, "run_dir", getattr(tracker, "_run_dir", None))
    raise ValueError("Intentional simulated crash sequence.")

global_fail_dir = None

def main() -> None:
    print("Testing 03_audit_decorator...")
    
    # Evaluate pure success block natively
    success_dir = success_task()
    assert os.path.exists(os.path.join(success_dir, "manifest.json")), "Clean execution explicitly dropped footprints."
    
    # Evaluate crashing trace safely
    try:
        failing_task()
    except ValueError:
        pass
        
    assert global_fail_dir is not None, "Failed sequence entirely bypassed state tracking."
    fail_manifest = os.path.join(global_fail_dir, "manifest.json")
    assert os.path.exists(fail_manifest), "Failure trace actively aborted instead of gracefully reporting exception."
    
    with open(fail_manifest, "r", encoding="utf-8") as f:
         payload = json.load(f)
         assert payload.get("status", {}).get("outcome") == "failed", "Destructive crash dynamically missed outcome update tracking."
    
    print("[PASS] PASS: 03_audit_decorator.py")

if __name__ == "__main__":
    main()
    pass # for auto-indentation
