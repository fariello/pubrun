#!/usr/bin/env python3
"""Master example verification script.

Runs all numbered example scripts and the minimal research workflow inside a
fresh temporary working directory and reports pass/fail status.
"""
import argparse
import glob
import os
import subprocess
import sys
import tempfile

EXAMPLE_TIMEOUT_SECONDS = 120


def main() -> None:
    parser = argparse.ArgumentParser(description="Run all pubrun examples and report results.")
    parser.add_argument(
        "--no-clear",
        action="store_true",
        help="Accepted for compatibility; has no effect because each run uses a fresh temporary directory.",
    )
    parser.parse_args()

    print("Starting pubrun examples verification...")
    print("=" * 60)

    base_dir = os.path.dirname(os.path.abspath(__file__))
    repo_root = os.path.dirname(base_dir)
    src_dir = os.path.join(repo_root, "src")

    env = os.environ.copy()
    for key in list(env):
        if key.startswith("PUBRUN_"):
            del env[key]
    existing_pythonpath = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = (
        f"{src_dir}{os.pathsep}{existing_pythonpath}" if existing_pythonpath else src_dir
    )

    analysis_script = os.path.join(base_dir, "minimal-research-workflow", "analysis.py")
    scripts = sorted(glob.glob(os.path.join(base_dir, "[0-9]*.py")))
    scripts.append(analysis_script)

    failed = []

    with tempfile.TemporaryDirectory(prefix="pubrun-examples-") as tmp_dir:
        config_home = os.path.join(tmp_dir, "config_home")
        os.makedirs(config_home, exist_ok=True)
        env["XDG_CONFIG_HOME"] = config_home
        env["APPDATA"] = config_home
        runs_dir = os.path.join(tmp_dir, "runs")
        outputs_dir = os.path.join(tmp_dir, "outputs")

        for script in scripts:
            script_name = os.path.relpath(script, base_dir)
            print(f"Executing {script_name}...")

            runs_before = set(os.listdir(runs_dir)) if os.path.exists(runs_dir) else set()

            cmd = [sys.executable, script]
            if script == analysis_script:
                cmd.extend(["--output-dir", outputs_dir])

            try:
                result = subprocess.run(
                    cmd,
                    cwd=tmp_dir,
                    env=env,
                    capture_output=True,
                    text=True,
                    timeout=EXAMPLE_TIMEOUT_SECONDS,
                )
            except subprocess.TimeoutExpired:
                print(f"[FAIL] TIMED OUT after {EXAMPLE_TIMEOUT_SECONDS}s: {script_name}")
                failed.append(script_name)
                print("-" * 60)
                continue

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
                    run_name = sorted(new_runs)[0]
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
