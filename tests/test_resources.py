import time
import json
import pytest
from pubrun import start
from pubrun.capture.resources import _get_rss_windows

def test_resources_watcher_threads(tmp_path, monkeypatch):
    monkeypatch.setattr("pathlib.Path.cwd", lambda: tmp_path)
    
    # Fast ticking to ensure the Thread successfully writes
    overrides = {
        "capture": {
            "resources": {"depth": "standard", "sample_interval_seconds": 0.05} # Fast 50ms tick
        },
        "events": {"enabled": True}
    }
    
    tracker = start(**overrides)
    
    # Sleep to ensure the thread ticks correctly in the background
    time.sleep(0.15)
    
    tracker.stop()
    
    # Verification
    manifest_path = tracker.run_dir / "manifest.json"
    assert manifest_path.exists()
    
    with open(manifest_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    res = data.get("resources")
    assert res is not None
    assert "peak_rss_bytes" in res
    assert "end_rss_bytes" in res
    assert res["capture_state"]["status"] == "complete"
    assert res["peak_rss_bytes"] is not None
    
    # Ensure background thread streamed ticks
    events_path = tracker.run_dir / "events.jsonl"
    assert events_path.exists()
    
    lines = events_path.read_text("utf-8").strip().splitlines()
    # Find all emitted sample events
    samples = [json.loads(line) for line in lines if '"resource_sample"' in line]
    
    # At least initial tick and maybe one scheduled tick
    assert len(samples) >= 1
    assert "rss_bytes" in samples[0]["payload"]
    assert samples[0]["payload"]["rss_bytes"] >= 0
