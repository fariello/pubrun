#!/usr/bin/env python3
"""Master example verification script.

Runs all numbered example scripts in order and reports pass/fail status.
"""
import os
import glob
import subprocess
import sys
import argparse
import shutil


def main() -> None:
    parser = argparse.ArgumentParser(description="Run all pubrun examples and report results.")
    parser.add_argument("--no-clear", action="store_true", help="Do not clear previous runs from the runs/ directory")
    args = parser.parse_args()

    print("Starting pubrun examples verification...")
    print("=" * 60)

    base_dir = os.path.dirname(os.path.abspath(__file__))
    repo_root = os.path.dirname(base_dir)
    runs_dir = os.path.join(repo_root, "runs")

    if not args.no_clear:
        if os.path.exists(runs_dir):
            print("Cleaning up previous runs...")
            import time
            for _ in range(5):
                try:
                    shutil.rmtree(runs_dir, ignore_errors=False)
                    break
                except Exception:
                    if os.name == "nt":
                        subprocess.run(f'rmdir /s /q "{runs_dir}"', shell=True, capture_output=True)
                    time.sleep(0.5)

    scripts = sorted(glob.glob(os.path.join(base_dir, "[0-9]*.py")))
    scripts.append(os.path.join(base_dir, "minimal-research-workflow", "analysis.py"))

    failed = []

    for script in scripts:
        script_name = os.path.relpath(script, base_dir)
        print(f"Executing {script_name}...")

        runs_before = set(os.listdir(runs_dir)) if os.path.exists(runs_dir) else set()

        result = subprocess.run([sys.executable, script], capture_output=True, text=True)
        if result.returncode != 0:
            print(f"[FAIL] FAILED: {script_name}")
            print(result.stderr)
            failed.append(script_name)
        else:
            for line in result.stdout.strip().split("\n"):
                if "PASS" in line.upper() or "TESTING" in line.upper():
                    print(line)

            # Check if a new run directory was created
            runs_after = set(os.listdir(runs_dir)) if os.path.exists(runs_dir) else set()
            new_runs = runs_after - runs_before
            if new_runs:
                run_name = list(new_runs)[0]
                stdout_log_path = os.path.join(runs_dir, run_name, "stdout.log")
                if os.path.exists(stdout_log_path):
                    with open(stdout_log_path, "r", encoding="utf-8") as f:
                        content = f.read()
                    line_count = len(content.splitlines()) if content.strip() else 0
                    print(f"      [INFO] stdout.log captured {line_count} lines.")

        print("-" * 60)

    if failed:
        print(f"FAILED: {', '.join(failed)}")
        sys.exit(1)
    else:
        print("[SUCCESS] All examples passed.")
        sys.exit(0)


if __name__ == "__main__":
    main()
