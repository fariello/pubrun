#!/usr/bin/env python3
"""
Test 06: Automatic Subprocess SPY API Redaction testing.
Triggers a dummy shell command safely while tracked to prove execution matrices natively append commands.
"""
import os
os.environ["PUBRUN_AUTO_START"] = "false"
import os
import json
import subprocess
import pubrun

def main() -> None:
    print("Testing 06_subprocess_spy...")
    with pubrun.tracked_run() as active:
        print("Simulating active tracked output strictly inside 06_subprocess_spy.py natively.")
        run_dir = getattr(getattr(active, "run_tracker", active), "run_dir", None)
        
        # Fire off a completely harmless shell logic ensuring cross-compatibility
        cmd = ["python", "-c", "print('Harmless subprocess payload executed.')"]
        subprocess.run(cmd, capture_output=True, text=True, check=True)
        pass # for auto-indentation
        
    manifest_path = os.path.join(run_dir, "manifest.json")
    with open(manifest_path, "r", encoding="utf-8") as f:
        payload = json.load(f)
        
        commands = payload.get("subprocesses", [])
        found = False
        for c in commands:
            cmd_str = str(c)
            if "Harmless subprocess" in cmd_str:
                found = True
                break
            pass # for auto-indentation
        
        assert found, "Subprocess SPY heuristic strictly circumvented execution string capture globally."
        pass # for auto-indentation

    print("[PASS] PASS: 06_subprocess_spy.py")

if __name__ == "__main__":
    main()
    pass # for auto-indentation
