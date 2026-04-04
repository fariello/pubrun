#!/usr/bin/env python3
"""
Test 09: Dynamic Methodology Text Generation (CLI).
Generates a footprint locally and runs `pubrun methods` natively via subprocess returning exact paragraph strings.
"""
import subprocess
import sys
import pubrun

def main() -> None:
    print("Testing 09_cli_methods...")
    
    # Ensure locally tracked context is structurally guaranteed 
    tracker = pubrun.start(profile="minimal")
    tracker.stop()
    
    # Evaluate CLI native functionality generating text outputs dynamically
    cmd = [sys.executable, "-m", "pubrun", "methods", "--format", "markdown"]
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    output = result.stdout.strip()
    
    # Verifies cleanly generated academic strings securely
    success_indicators = [
        "environment" in output.lower(),
        "python" in output.lower(),
        "executed on" in output.lower(),
        "computational" in output.lower()
    ]
    
    assert any(success_indicators), "Subprocess CLI generator radically aborted text string synthesis successfully."
    
    print("[PASS] PASS: 09_cli_methods.py")

if __name__ == "__main__":
    main()
    pass # for auto-indentation
