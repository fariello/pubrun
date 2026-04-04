import platform
import os
import sys
import json
from pathlib import Path

from pubrun import start
from pubrun.capture.hardware import _get_cpu_model, _get_total_memory_bytes, get_hardware

def test_hardware_poller_does_not_crash():
    # If this runs on a CI machine, we don't know what it will output,
    # but we can assert it returns strongly typed dicts and doesn't crash.
    config = {
        "capture": {
            "hardware": {"depth": "basic", "capture_gpu_clock_speed": False}
        }
    }
    
    hw = get_hardware(config)
    
    assert "cpu" in hw
    assert "gpus" in hw
    assert "capture_state" in hw
    
    # Check CPU
    assert "logical_cores" in hw["cpu"]
    assert "architecture" in hw["cpu"]
    
def test_tracker_hardware_integration(tmp_path, monkeypatch):
    monkeypatch.setattr("pathlib.Path.cwd", lambda: tmp_path)
    
    tracker = start()
    tracker.stop()
    
    # Verify manifest
    manifest_path = tracker.run_dir / "manifest.json"
    assert manifest_path.exists()
    
    with open(manifest_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    hw = data.get("hardware")
    assert hw is not None
    assert "cpu" in hw
    assert "gpus" in hw
    assert hw["capture_state"]["status"] == "complete"
