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

    # Force _poll_rss to always return -1 (simulating an UNREADABLE poll, i.e.
    # a real error/timeout). A legitimate RSS of 0 no longer counts as a
    # failure, so only -1 triggers the self-abort. (IPD 20260705 EC-12.)
    monkeypatch.setattr(watcher, "_poll_rss", lambda: -1)

    # Poll until the watcher auto-stops (P3-T8: avoid fixed sleep)
    deadline = time.time() + 5.0
    while time.time() < deadline:
        if watcher._stop_event.is_set():
            break
        time.sleep(0.05)

    # The watcher should have auto-stopped itself
    assert watcher._stop_event.is_set()

    tracker.stop()


def test_resource_watcher_legit_zero_does_not_abort(tmp_path, monkeypatch):
    """A legitimate RSS reading of 0 must NOT count toward the failure
    threshold, so telemetry is not permanently disabled by transient zeros.
    (IPD 20260705 EC-12.)"""
    from pubrun import start

    monkeypatch.setattr("pathlib.Path.cwd", lambda: tmp_path)
    tracker = start(capture={"resources": {"depth": "standard", "sample_interval_seconds": 0.02,
                                            "max_consecutive_failures": 3}})
    watcher = tracker.resource_watcher
    assert watcher is not None

    # A readable poll that returns 0 (not the -1 unreadable sentinel).
    monkeypatch.setattr(watcher, "_poll_rss", lambda: 0)
    # Reset any state accrued BEFORE the mock was installed: on a slow runner (e.g. Windows,
    # where the real RSS poll shells out to wmic and can time out), the watcher thread may have
    # already recorded real unreadable polls between start() and this monkeypatch. Clearing here
    # isolates the actual assertion (legit 0 must not count as a failure), not the setup race.
    with watcher._lock:
        watcher._consecutive_failures = 0
    watcher._stop_event.clear()

    # Let several intervals elapse; the watcher must NOT self-abort.
    deadline = time.time() + 1.0
    while time.time() < deadline:
        if watcher._stop_event.is_set():
            break
        time.sleep(0.05)

    assert not watcher._stop_event.is_set()
    assert watcher._consecutive_failures == 0
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
    monkeypatch.setattr("pubrun.capture.resources._get_rss_windows", lambda: 1024 * 1024)

    tracker = start(capture={"resources": {"depth": "standard", "sample_interval_seconds": 0.05}})
    watcher = tracker.resource_watcher
    assert watcher is not None
    assert watcher.is_alive()

    tracker.stop()
    assert not watcher.is_alive()


def test_cpu_poll_excludes_reaped_children(monkeypatch):
    """CPU% for the main process must NOT jump when a batch of subprocesses is
    reaped (children_user/children_system spike). Regression for the observed
    5233% spike. (uri-ai-info run 31c039d0)"""
    import os as _os
    from pubrun.capture.resources import ResourceWatcher

    class FakeTracker:
        event_stream = None

    w = ResourceWatcher(FakeTracker(), interval_seconds=1)

    # A namedtuple-like times() result. First poll seeds _last_times.
    class T:
        def __init__(self, user, system, cu, cs):
            self.user = user
            self.system = system
            self.children_user = cu
            self.children_system = cs

    clock = [1000.0]
    times = [T(1.0, 0.5, 0.0, 0.0)]
    monkeypatch.setattr("pubrun.capture.resources.time.perf_counter", lambda: clock[0])
    monkeypatch.setattr("pubrun.capture.resources.os.times", lambda: times[0])

    w._poll_cpu()  # seed

    # 1s later: main process barely moved, but 6000s of CHILD cpu was just reaped.
    clock[0] = 1001.0
    times[0] = T(1.05, 0.55, 6000.0, 0.0)
    cpu = w._poll_cpu()

    cores = _os.cpu_count() or 1
    # Main-process CPU should be ~10% (0.1s over 1s), definitely not thousands.
    assert cpu <= 100.0 * cores, f"cpu={cpu} exceeded {100.0*cores}"
    assert cpu < 100.0, f"cpu={cpu} should reflect only the main process, not reaped children"


def test_cpu_poll_clamped_to_cores(monkeypatch):
    """A pathological huge main-process delta is clamped to 100%*cores."""
    import os as _os
    from pubrun.capture.resources import ResourceWatcher

    class FakeTracker:
        event_stream = None

    w = ResourceWatcher(FakeTracker(), interval_seconds=1)

    class T:
        def __init__(self, user, system):
            self.user = user
            self.system = system
            self.children_user = 0.0
            self.children_system = 0.0

    clock = [0.0]
    times = [T(0.0, 0.0)]
    monkeypatch.setattr("pubrun.capture.resources.time.perf_counter", lambda: clock[0])
    monkeypatch.setattr("pubrun.capture.resources.os.times", lambda: times[0])
    w._poll_cpu()
    clock[0] = 0.001  # 1ms window
    times[0] = T(100.0, 0.0)  # absurd 100s of cpu in 1ms
    cpu = w._poll_cpu()
    assert cpu == 100.0 * (_os.cpu_count() or 1)
