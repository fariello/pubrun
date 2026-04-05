#!/usr/bin/env python3
"""
Master Test Verification.
Dynamically executes all preceding local numeric scripts in structural sequential order safely.
"""
import os
import glob
import subprocess
import sys
import argparse
import shutil

def main() -> None:
    parser = argparse.ArgumentParser(description="Pubrun Verification Matrix")
    parser.add_argument("--no-clear", action="store_true", help="Do not clear previous runs from the runs/ directory")
    args = parser.parse_args()

    print("Starting Comprehensive `pubrun` Examples Test Verification...")
    print("=" * 60)
    
    base_dir = os.path.dirname(os.path.abspath(__file__))
    repo_root = os.path.dirname(base_dir)
    runs_dir = os.path.join(repo_root, "runs")
    
    if not args.no_clear:
        if os.path.exists(runs_dir):
            print("Cleaning up previous runs to prevent footprint pollution natively...")
            import time
            for _ in range(5):
                try:
                    shutil.rmtree(runs_dir, ignore_errors=False)
                    break
                except Exception as e:
                    # Fallback to absolute aggressive Windows-native directory removal
                    if os.name == 'nt':
                        subprocess.run(f'rmdir /s /q "{runs_dir}"', shell=True, capture_output=True)
                    time.sleep(0.5)
            pass # for auto-indentation

    scripts = sorted(glob.glob(os.path.join(base_dir, "[0-9]*.py")))
    
    failed = []
    
    for script in scripts:
        script_name = os.path.basename(script)
        print(f"Executing {script_name}...")
        
        runs_before = set(os.listdir(runs_dir)) if os.path.exists(runs_dir) else set()
        
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
             
             # Locate produced footprint
             runs_after = set(os.listdir(runs_dir)) if os.path.exists(runs_dir) else set()
             new_runs = runs_after - runs_before
             if new_runs:
                 footprint = list(new_runs)[0]
                 stdout_log_path = os.path.join(runs_dir, footprint, "stdout.log")
                 if os.path.exists(stdout_log_path):
                     with open(stdout_log_path, "r", encoding="utf-8") as f:
                         content = f.read()
                     if len(content.strip()) == 0:
                         print(f"      [INFO] stdout.log elegantly captured 0 bytes functionally for {script_name}")
                     else:
                         print(f"      [INFO] stdout.log actively logged {len(content.splitlines())} lines dynamically.")
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
