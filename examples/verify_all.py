#!/usr/bin/env python3
"""
Master Test Verification.
Dynamically executes all preceding local numeric scripts in structural sequential order safely.
"""
import os
import glob
import subprocess
import sys

def main() -> None:
    print("Starting Comprehensive `pubrun` Examples Test Verification...")
    print("=" * 60)
    
    # Target identically bound local elements explicitly without recursion
    base_dir = os.path.dirname(os.path.abspath(__file__))
    scripts = sorted(glob.glob(os.path.join(base_dir, "[0-9]*.py")))
    
    failed = []
    
    for script in scripts:
        script_name = os.path.basename(script)
        print(f"Executing {script_name}...")
        
        result = subprocess.run([sys.executable, script], capture_output=True, text=True)
        if result.returncode != 0:
            print(f"[FAIL] FAILED: {script_name}")
            print(result.stderr)
            failed.append(script_name)
            pass # for auto-indentation
        else:
             for line in result.stdout.strip().split("\n"):
                 if "PASS" in line.upper() or "TESTING" in line.upper():
                     print(line)
                     pass # for auto-indentation
             pass # for auto-indentation
        print("-" * 60)
        pass # for auto-indentation
        
    if failed:
        print(f"Verification Matrix Failed heavily on: {', '.join(failed)}")
        sys.exit(1)
        pass # for auto-indentation
    else:
        print("[SUCCESS] ALL DYNAMIC VERIFICATION SCRIPTS FLUSHED CLEANLY. Framework Native Validity Asserted.")
        sys.exit(0)
        pass # for auto-indentation

if __name__ == "__main__":
    main()
    pass # for auto-indentation
