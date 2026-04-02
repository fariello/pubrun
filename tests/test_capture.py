import os
import sys
import json
import subprocess
from pathlib import Path

from runtrace import start, get_current_run

def test_invocation_capture(tmp_path, monkeypatch):
    monkeypatch.setattr("pathlib.Path.cwd", lambda: tmp_path)
    
    # Run tracing
    tracker = start()
    tracker.stop()
    
    # Verify manifest
    manifest_path = tracker.run_dir / "manifest.json"
    assert manifest_path.exists()
    
    with open(manifest_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    inv = data.get("invocation")
    assert inv is not None
    assert "rerun_command" in inv
    assert "cd " in inv["rerun_command"]
    assert "python" in inv["rerun_command"]
    assert inv["capture_state"]["status"] == "complete"

def test_subprocess_interceptor(tmp_path, monkeypatch):
    monkeypatch.setattr("pathlib.Path.cwd", lambda: tmp_path)
    
    # Enable subprocess capture
    overrides = {
        "capture": {
            "subprocesses": {"enabled": True}
        }
    }
    tracker = start(**overrides)
    
    # 1. Spawn a waited trivial process
    subprocess.run([sys.executable, "-c", "print('hello runtrace')"])
    
    # 2. Spawn a detached one that doesn't wait
    p = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(0.1)"])
    
    tracker.stop()
    
    with open(tracker.run_dir / "manifest.json", "r", encoding="utf-8") as f:
        data = json.load(f)
        
    subs = data.get("subprocesses")
    assert len(subs) == 2
    
    # The waited one
    assert subs[0]["exit_code"] == 0
    assert subs[0]["capture_state"]["status"] == "complete"
    assert "-c" in subs[0]["argv"]
    
    # The non-waited one
    assert subs[1]["exit_code"] is None
    # We gracefully marked it complete since the Tracker shut down safely
    assert subs[1]["capture_state"]["status"] == "complete"

def test_console_interceptor_tqdm(tmp_path, monkeypatch):
    monkeypatch.setattr("pathlib.Path.cwd", lambda: tmp_path)
    
    # Simulate basic capture mode via overrides
    overrides = {
        "capture": {
            "console": {"capture_mode": "basic"}
        }
    }
    tracker = start(**overrides)
    
    # Simulate a tqdm progress bar doing carriage returns to redraw the line
    sys.stdout.write("Epoch 1/10\r")
    sys.stdout.write("Epoch 2/10\r")
    sys.stdout.write("Epoch 3/10\n")
    sys.stdout.write("Done!\n")
    
    tracker.stop()
    
    # Verify the log file was safely compressed rather than logging 1000s of redraws
    stdout_log = tracker.run_dir / "stdout.log"
    assert stdout_log.exists()
    
    content = stdout_log.read_text(encoding="utf-8")
    lines = content.splitlines()
    assert len(lines) == 2
    assert "Epoch 3/10" in lines[0] 
    assert "Done!" in lines[1]
    
    # Verify manifest tracking count
    with open(tracker.run_dir / "manifest.json", "r", encoding="utf-8") as f:
        data = json.load(f)
        
    console = data.get("console")
    assert console["capture_mode"] == "basic"
    assert console["stdout"]["lines_captured"] == 2
    assert console["stdout"]["path"] == "stdout.log"
