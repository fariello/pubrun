import sys
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
    
    # Poll until at least one tick has occurred (P3-T7: avoid fixed sleep)
    deadline = time.time() + 5.0  # generous 5s deadline
    while time.time() < deadline:
        if tracker.resource_watcher and tracker.resource_watcher.peak_rss_bytes > 0:
            break
        time.sleep(0.05)
    
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
    # On Windows, wmic may be unavailable on newer runners; RSS may be None
    if sys.platform != "win32":
        assert res["peak_rss_bytes"] is not None
    
    # Ensure background thread streamed ticks (skip on Windows where
    # wmic is unavailable and the thread self-terminates with no samples)
    if sys.platform != "win32":
        events_path = tracker.run_dir / "events.jsonl"
        assert events_path.exists()
        
        lines = events_path.read_text("utf-8").strip().splitlines()
        # Find all emitted sample events
        samples = [json.loads(line) for line in lines if '"resource_sample"' in line]
        
        # At least initial tick and maybe one scheduled tick
        assert len(samples) >= 1
        assert "rss_bytes" in samples[0]["payload"]
        assert samples[0]["payload"]["rss_bytes"] >= 0


def test_resource_watcher_failure_threshold(tmp_path, monkeypatch):
    """ResourceWatcher stops itself after max_consecutive_failures."""
    from pubrun.capture.resources import ResourceWatcher
    from pubrun import start

    monkeypatch.setattr("pathlib.Path.cwd", lambda: tmp_path)

    tracker = start(capture={"resources": {"depth": "standard", "sample_interval_seconds": 0.02}})

    watcher = tracker.resource_watcher
    assert watcher is not None

    # Force _poll_rss to always return 0 (simulating failure)
    monkeypatch.setattr(watcher, "_poll_rss", lambda: 0)

    # Poll until the watcher auto-stops (P3-T8: avoid fixed sleep)
    deadline = time.time() + 5.0
    while time.time() < deadline:
        if watcher._stop_event.is_set():
            break
        time.sleep(0.05)

    # The watcher should have auto-stopped itself
    assert watcher._stop_event.is_set()

    tracker.stop()


def test_resource_watcher_to_manifest_dict_zeros():
    """to_manifest_dict returns None for zero-value peaks."""
    from pubrun.capture.resources import ResourceWatcher

    class FakeTracker:
        event_stream = None

    watcher = ResourceWatcher(FakeTracker(), interval_seconds=1, max_failures=3)
    # Don't start the thread -- just test the dict builder
    result = watcher.to_manifest_dict()
    assert result["peak_rss_bytes"] is None
    assert result["end_rss_bytes"] is None
    assert result["peak_cpu_percent"] is None
    assert result["capture_state"]["status"] == "complete"


def test_resource_watcher_join(tmp_path, monkeypatch):
    """Verify that stop() calls join and the thread stops."""
    from pubrun import start

    monkeypatch.setattr("pathlib.Path.cwd", lambda: tmp_path)
    tracker = start(capture={"resources": {"depth": "standard", "sample_interval_seconds": 0.05}})
    watcher = tracker.resource_watcher
    assert watcher is not None
    assert watcher.is_alive()
    
    tracker.stop()
    assert not watcher.is_alive()

