"""Deterministic behavioral tests for monotonic timing and overhead separation.

All tests drive Run, ArtifactWriter, and public lifecycle helpers with a
controlled fake wall/monotonic clock patched onto pubrun.tracker.time and
pubrun.writer.time so pytest's own clock is untouched and zero real-time sleeps
are needed.
"""
import json
import threading
import time as real_time
from pathlib import Path

import pytest

import pubrun.tracker as tracker_mod
import pubrun.writer as writer_mod
from pubrun.core import audit_run, start, stop, tracked_run
from pubrun.tracker import Run


class FakeClock:
    """Thread-safe deterministic wall and monotonic clock for pubrun.tracker/writer."""

    def __init__(self, wall: float = 1_750_000_000.0, mono: float = 100.0) -> None:
        self._lock = threading.Lock()
        self._wall = float(wall)
        self._mono = float(mono)

    def time(self) -> float:
        with self._lock:
            return self._wall

    def perf_counter(self) -> float:
        with self._lock:
            return self._mono

    def advance(self, seconds: float) -> None:
        """Advance both monotonic and wall clocks by the same positive delta."""
        with self._lock:
            self._mono += seconds
            self._wall += seconds

    def advance_mono(self, seconds: float) -> None:
        """Advance only the monotonic clock."""
        with self._lock:
            self._mono += seconds

    def jump_wall(self, delta: float) -> None:
        """Step the wall clock forward or backward without moving monotonic time."""
        with self._lock:
            self._wall += delta

    def __getattr__(self, name: str):
        return getattr(real_time, name)


def _install_fake_clock(monkeypatch, wall: float = 1_750_000_000.0, mono: float = 100.0) -> FakeClock:
    clock = FakeClock(wall=wall, mono=mono)
    monkeypatch.setattr(tracker_mod, "time", clock)
    monkeypatch.setattr(writer_mod, "time", clock)
    return clock


def _stub_fast_hardware(monkeypatch, on_collect=None) -> None:
    """Stub background hardware/host/filesystem capture for fast deterministic runs."""

    def fake_hw(config):
        if on_collect is not None:
            on_collect()
        return {"capture_state": {"status": "complete"}}

    monkeypatch.setattr(tracker_mod, "get_hardware", fake_hw)
    monkeypatch.setattr(
        tracker_mod,
        "get_host",
        lambda config: {"capture_state": {"status": "complete"}},
    )
    import pubrun.capture.filesystem as fs_mod

    monkeypatch.setattr(
        fs_mod,
        "get_filesystem",
        lambda config, paths: {"capture_state": {"status": "complete"}},
    )


def _read_manifest(run_dir: Path) -> dict:
    return json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))


def test_forward_wall_clock_jump_does_not_distort_duration(monkeypatch):
    clock = _install_fake_clock(monkeypatch, wall=1_750_000_000.0, mono=50.0)
    _stub_fast_hardware(monkeypatch)

    run = start()
    run._hardware_future_done.wait(timeout=2.0)

    clock.advance(0.25)
    clock.jump_wall(7200.0)
    run.stop(outcome="completed")

    timing = _read_manifest(run.run_dir)["timing"]
    assert timing["workload_seconds"] == pytest.approx(0.25, abs=1e-9)
    assert timing["elapsed_seconds"] == pytest.approx(0.25, abs=1e-9)
    assert timing["ended_at_utc"] - timing["started_at_utc"] == pytest.approx(7200.25, abs=1e-9)
    assert timing["duration_clock"] == "monotonic"
    assert timing["elapsed_basis"] == "workload"
    assert timing["interval_scope"] == "tracked_interval"
    assert timing["capture_state"] == {"status": "complete"}


def test_backward_wall_clock_jump_keeps_durations_nonnegative(monkeypatch):
    clock = _install_fake_clock(monkeypatch, wall=1_750_000_000.0, mono=50.0)
    _stub_fast_hardware(monkeypatch)

    run = start()
    run._hardware_future_done.wait(timeout=2.0)

    clock.advance(0.40)
    clock.jump_wall(-7200.0)
    run.stop(outcome="completed")

    timing = _read_manifest(run.run_dir)["timing"]
    assert timing["ended_at_utc"] < timing["started_at_utc"]
    assert timing["workload_seconds"] == pytest.approx(0.40, abs=1e-9)
    assert timing["elapsed_seconds"] == pytest.approx(0.40, abs=1e-9)
    for key in (
        "startup_overhead_seconds",
        "workload_seconds",
        "elapsed_seconds",
        "finalization_overhead_seconds",
        "session_seconds",
        "hardware_wait_seconds",
    ):
        assert timing[key] is not None
        assert timing[key] >= 0.0


def test_hardware_worker_delay_isolated_from_workload(monkeypatch):
    clock = _install_fake_clock(monkeypatch, wall=1_750_000_000.0, mono=200.0)
    hw_started = threading.Event()
    release_hw = threading.Event()

    def blocked_hw(config):
        hw_started.set()
        release_hw.wait(timeout=2.0)
        return {"capture_state": {"status": "complete"}}

    monkeypatch.setattr(tracker_mod, "get_hardware", blocked_hw)
    monkeypatch.setattr(
        tracker_mod,
        "get_host",
        lambda config: {"capture_state": {"status": "complete"}},
    )
    import pubrun.capture.filesystem as fs_mod

    monkeypatch.setattr(
        fs_mod,
        "get_filesystem",
        lambda config, paths: {"capture_state": {"status": "complete"}},
    )

    run = start()
    assert hw_started.wait(timeout=2.0)

    # Simulate short workload while hardware thread is still running concurrently.
    clock.advance(0.05)

    # Intercept _hardware_future_done.wait so finalization deterministically
    # advances the fake monotonic clock by +1.5s while waiting on hardware.
    real_event = run._hardware_future_done

    class ControlledWaitEvent:
        def wait(self, timeout=None):
            clock.advance(1.5)
            release_hw.set()
            return real_event.wait(timeout=2.0)

        def set(self):
            return real_event.set()

        def is_set(self):
            return real_event.is_set()

    run._hardware_future_done = ControlledWaitEvent()
    run.stop(outcome="completed")

    timing = _read_manifest(run.run_dir)["timing"]
    assert timing["workload_seconds"] == pytest.approx(0.05, abs=1e-9)
    assert timing["elapsed_seconds"] == pytest.approx(0.05, abs=1e-9)
    assert timing["hardware_wait_seconds"] == pytest.approx(1.5, abs=1e-9)
    assert timing["finalization_overhead_seconds"] == pytest.approx(1.5, abs=1e-9)
    # Background hardware overlapped both workload (0.05s) and finalization wait (1.5s).
    assert timing["background_hardware_seconds"] == pytest.approx(1.55, abs=1e-9)
    assert timing["session_seconds"] == pytest.approx(
        timing["startup_overhead_seconds"]
        + timing["workload_seconds"]
        + timing["finalization_overhead_seconds"],
        abs=1e-9,
    )


def test_hardware_timeout_leaves_background_hardware_seconds_none(monkeypatch):
    clock = _install_fake_clock(monkeypatch, wall=1_750_000_000.0, mono=300.0)
    hw_started = threading.Event()
    release_hw = threading.Event()

    def stuck_hw(config):
        hw_started.set()
        release_hw.wait(timeout=5.0)
        return {"capture_state": {"status": "complete"}}

    monkeypatch.setattr(tracker_mod, "get_hardware", stuck_hw)
    monkeypatch.setattr(
        tracker_mod,
        "get_host",
        lambda config: {"capture_state": {"status": "complete"}},
    )
    import pubrun.capture.filesystem as fs_mod

    monkeypatch.setattr(
        fs_mod,
        "get_filesystem",
        lambda config, paths: {"capture_state": {"status": "complete"}},
    )

    try:
        run = start()
        assert hw_started.wait(timeout=2.0)
        clock.advance(0.02)

        real_event = run._hardware_future_done

        class TimeoutWaitEvent:
            def wait(self, timeout=None):
                clock.advance(2.0)
                return False

            def set(self):
                return real_event.set()

            def is_set(self):
                return real_event.is_set()

        run._hardware_future_done = TimeoutWaitEvent()
        run.stop(outcome="completed")

        timing = _read_manifest(run.run_dir)["timing"]
        assert timing["workload_seconds"] == pytest.approx(0.02, abs=1e-9)
        assert timing["hardware_wait_seconds"] == pytest.approx(2.0, abs=1e-9)
        assert timing["background_hardware_seconds"] is None
    finally:
        release_hw.set()
        if "run" in locals() and getattr(run, "_hardware_thread", None):
            run._hardware_thread.join(timeout=2.0)


def test_writer_delay_isolated_from_workload_and_single_manifest_write(monkeypatch):
    clock = _install_fake_clock(monkeypatch, wall=1_750_000_000.0, mono=400.0)
    _stub_fast_hardware(monkeypatch)

    real_atomic = writer_mod._atomic_json_write
    finalization_writes = []
    in_finalization = False

    def delayed_atomic(path: Path, data):
        if in_finalization:
            finalization_writes.append(path.name)
            if path.name == "config.resolved.json":
                clock.advance(0.30)
            elif path.name == "manifest.json":
                clock.advance(0.70)
        return real_atomic(path, data)

    monkeypatch.setattr(writer_mod, "_atomic_json_write", delayed_atomic)

    run = start()
    run._hardware_thread.join(timeout=2.0)

    clock.advance(0.02)
    # Modify config in memory so finalization writes config.resolved.json (unchanged
    # config snapshots are skipped during finalization).
    run.config["events"]["flush_interval_events"] = 42
    in_finalization = True
    run.stop(outcome="completed")

    timing = _read_manifest(run.run_dir)["timing"]
    # config.resolved.json is written before manifest.json, and manifest.json only once.
    assert finalization_writes == ["config.resolved.json", "manifest.json"]
    assert timing["workload_seconds"] == pytest.approx(0.02, abs=1e-9)
    assert timing["elapsed_seconds"] == pytest.approx(0.02, abs=1e-9)
    # Pre-manifest config write (0.30s) is in finalization_overhead_seconds,
    # whereas post-t3 manifest write (0.70s) is excluded from persisted timing.
    assert timing["finalization_overhead_seconds"] == pytest.approx(0.30, abs=1e-9)
    # Total writer overhead in memory includes both config (0.30s) and manifest (0.70s).
    assert run.writer_overhead_seconds == pytest.approx(1.00, abs=1e-9)


def test_short_run_startup_overhead_separated_and_disjoint_sum(monkeypatch):
    clock = _install_fake_clock(monkeypatch, wall=1_750_000_000.0, mono=500.0)
    _stub_fast_hardware(monkeypatch)

    real_get_git = tracker_mod.get_git

    def slow_startup_git(config):
        clock.advance(0.20)
        return real_get_git(config)

    monkeypatch.setattr(tracker_mod, "get_git", slow_startup_git)

    real_atomic = writer_mod._atomic_json_write
    add_finalize_delay = False

    def delayed_config_write(path: Path, data):
        if add_finalize_delay and path.name == "config.resolved.json":
            clock.advance(0.05)
        return real_atomic(path, data)

    monkeypatch.setattr(writer_mod, "_atomic_json_write", delayed_config_write)

    run = start()
    run._hardware_thread.join(timeout=2.0)

    clock.advance(0.001)
    # Modify config in memory so finalization exercises pre-manifest config write delay.
    run.config["events"]["flush_interval_events"] = 42
    add_finalize_delay = True
    run.stop(outcome="completed")

    timing = _read_manifest(run.run_dir)["timing"]
    assert timing["startup_overhead_seconds"] == pytest.approx(0.20, abs=1e-9)
    assert timing["workload_seconds"] == pytest.approx(0.001, abs=1e-9)
    assert timing["elapsed_seconds"] == pytest.approx(0.001, abs=1e-9)
    assert timing["finalization_overhead_seconds"] == pytest.approx(0.05, abs=1e-9)
    assert timing["session_seconds"] == pytest.approx(
        timing["startup_overhead_seconds"]
        + timing["workload_seconds"]
        + timing["finalization_overhead_seconds"],
        abs=1e-9,
    )


def test_startup_manifest_and_async_hardware_snapshot_stay_partial_and_unfrozen(monkeypatch):
    clock = _install_fake_clock(monkeypatch, wall=1_750_000_000.0, mono=600.0)
    hw_entered = threading.Event()
    release_hw = threading.Event()
    startup_snapshots = []

    def gated_hw(config):
        hw_entered.set()
        release_hw.wait(timeout=2.0)
        clock.advance(0.04)
        return {"capture_state": {"status": "complete"}}

    monkeypatch.setattr(tracker_mod, "get_hardware", gated_hw)
    monkeypatch.setattr(
        tracker_mod,
        "get_host",
        lambda config: {"capture_state": {"status": "complete"}},
    )
    import pubrun.capture.filesystem as fs_mod

    monkeypatch.setattr(
        fs_mod,
        "get_filesystem",
        lambda config, paths: {"capture_state": {"status": "complete"}},
    )

    real_write_startup = writer_mod.ArtifactWriter.write_startup_manifest

    def spy_startup(self, *args, **kwargs):
        # Ensure hw_start was captured at 600.0 before advancing clock for initial startup write.
        if not startup_snapshots:
            hw_entered.wait(timeout=2.0)
            clock.advance(0.10)
        res = real_write_startup(self, *args, **kwargs)
        startup_snapshots.append(_read_manifest(self.run.run_dir)["timing"])
        return res

    monkeypatch.setattr(writer_mod.ArtifactWriter, "write_startup_manifest", spy_startup)

    run = start()
    try:
        # Initial startup snapshot was written before t1.
        assert len(startup_snapshots) == 1
        initial = startup_snapshots[0]
        assert initial["workload_started_at_utc"] is None
        assert initial["startup_overhead_seconds"] is None
        assert initial["elapsed_seconds"] is None
        assert initial["workload_seconds"] is None
        assert initial["duration_clock"] == "monotonic"
        assert initial["elapsed_basis"] == "workload"
        assert initial["interval_scope"] == "tracked_interval"
        assert initial["capture_state"] == {"status": "partial"}
        assert run._manifest_timing_frozen is False

        # Release background hardware thread so it writes its async startup snapshot.
        release_hw.set()
        run._hardware_thread.join(timeout=2.0)

        assert len(startup_snapshots) == 2
        hw_snapshot = startup_snapshots[1]
        assert hw_snapshot["workload_started_at_utc"] is not None
        assert hw_snapshot["startup_overhead_seconds"] == pytest.approx(0.10, abs=1e-9)
        # Hardware thread overlapped both the 0.10s startup write and its own 0.04s work.
        assert hw_snapshot["background_hardware_seconds"] == pytest.approx(0.14, abs=1e-9)
        assert hw_snapshot["elapsed_seconds"] is None
        assert hw_snapshot["capture_state"] == {"status": "partial"}
        assert run._manifest_timing_frozen is False

        clock.advance(0.20)
    finally:
        release_hw.set()
        run.stop(outcome="completed")

    final_timing = _read_manifest(run.run_dir)["timing"]
    assert final_timing["capture_state"] == {"status": "complete"}
    assert final_timing["workload_seconds"] == pytest.approx(0.24, abs=1e-9)
    assert final_timing["elapsed_seconds"] == pytest.approx(0.24, abs=1e-9)
    assert run._manifest_timing_frozen is True


def test_atexit_direct_write_artifacts_finalization(monkeypatch):
    clock = _install_fake_clock(monkeypatch, wall=1_750_000_000.0, mono=700.0)
    _stub_fast_hardware(monkeypatch)

    run = start()
    run._hardware_future_done.wait(timeout=2.0)

    clock.advance(0.12)
    # Simulate Python atexit invoking write_artifacts directly without stop().
    run.writer.write_artifacts()

    manifest = _read_manifest(run.run_dir)
    assert manifest["status"]["outcome"] == "completed"
    timing = manifest["timing"]
    assert timing["workload_seconds"] == pytest.approx(0.12, abs=1e-9)
    assert timing["elapsed_seconds"] == pytest.approx(0.12, abs=1e-9)
    assert timing["capture_state"] == {"status": "complete"}


def test_nested_ref_counted_start_stop_freezes_only_on_outer_stop(monkeypatch):
    clock = _install_fake_clock(monkeypatch, wall=1_750_000_000.0, mono=800.0)
    _stub_fast_hardware(monkeypatch)

    outer = start()
    outer._hardware_future_done.wait(timeout=2.0)
    clock.advance(0.10)

    inner = start()
    assert inner is outer
    assert outer.ref_count == 2
    clock.advance(0.20)

    # Inner stop must not mark t2 or finalize.
    stop()
    assert outer.ref_count == 1
    assert outer.is_active is True
    assert outer._finalized is False
    assert outer._workload_end_mono is None

    clock.advance(0.30)
    stop()

    assert outer.is_active is False
    assert outer._finalized is True
    timing = _read_manifest(outer.run_dir)["timing"]
    assert timing["workload_seconds"] == pytest.approx(0.60, abs=1e-9)
    assert timing["elapsed_seconds"] == pytest.approx(0.60, abs=1e-9)


def test_tracked_run_normal_and_exception_paths(monkeypatch):
    clock = _install_fake_clock(monkeypatch, wall=1_750_000_000.0, mono=900.0)
    _stub_fast_hardware(monkeypatch)

    with tracked_run() as ctx:
        ctx.run_tracker._hardware_future_done.wait(timeout=2.0)
        clock.advance(0.35)
        ok_dir = ctx.run_tracker.run_dir

    ok_manifest = _read_manifest(ok_dir)
    assert ok_manifest["status"]["outcome"] == "completed"
    assert ok_manifest["timing"]["workload_seconds"] == pytest.approx(0.35, abs=1e-9)
    assert ok_manifest["timing"]["elapsed_seconds"] == pytest.approx(0.35, abs=1e-9)

    fail_dir = None
    with pytest.raises(ValueError, match="boom"):
        with tracked_run() as ctx:
            ctx.run_tracker._hardware_future_done.wait(timeout=2.0)
            fail_dir = ctx.run_tracker.run_dir
            clock.advance(0.15)
            raise ValueError("boom")

    fail_manifest = _read_manifest(fail_dir)
    assert fail_manifest["status"]["outcome"] == "failed"
    assert fail_manifest["timing"]["workload_seconds"] == pytest.approx(0.15, abs=1e-9)
    assert fail_manifest["timing"]["elapsed_seconds"] == pytest.approx(0.15, abs=1e-9)


def test_audit_run_normal_and_exception_paths(monkeypatch):
    clock = _install_fake_clock(monkeypatch, wall=1_750_000_000.0, mono=1000.0)
    _stub_fast_hardware(monkeypatch)
    recorded_dirs = []

    @audit_run()
    def succeed():
        r = tracker_mod.get_current_run()
        r._hardware_future_done.wait(timeout=2.0)
        recorded_dirs.append(r.run_dir)
        clock.advance(0.22)
        return "ok"

    assert succeed() == "ok"
    ok_manifest = _read_manifest(recorded_dirs[0])
    assert ok_manifest["status"]["outcome"] == "completed"
    assert ok_manifest["timing"]["workload_seconds"] == pytest.approx(0.22, abs=1e-9)

    @audit_run()
    def fail():
        r = tracker_mod.get_current_run()
        r._hardware_future_done.wait(timeout=2.0)
        recorded_dirs.append(r.run_dir)
        clock.advance(0.08)
        raise RuntimeError("audit failure")

    with pytest.raises(RuntimeError, match="audit failure"):
        fail()

    fail_manifest = _read_manifest(recorded_dirs[1])
    assert fail_manifest["status"]["outcome"] == "failed"
    assert fail_manifest["timing"]["workload_seconds"] == pytest.approx(0.08, abs=1e-9)


def test_keyboard_interrupt_and_signal_interruption_paths(monkeypatch):
    clock = _install_fake_clock(monkeypatch, wall=1_750_000_000.0, mono=1100.0)
    _stub_fast_hardware(monkeypatch)

    # Path 1: Active KeyboardInterrupt during atexit/write_artifacts finalization.
    run1 = start()
    run1._hardware_future_done.wait(timeout=2.0)
    clock.advance(0.18)
    try:
        raise KeyboardInterrupt()
    except KeyboardInterrupt:
        run1.writer.write_artifacts()

    m1 = _read_manifest(run1.run_dir)
    assert m1["status"]["outcome"] == "interrupted"
    assert m1["timing"]["workload_seconds"] == pytest.approx(0.18, abs=1e-9)
    assert m1["timing"]["elapsed_seconds"] == pytest.approx(0.18, abs=1e-9)
    assert m1["timing"]["capture_state"] == {"status": "complete"}
    tracker_mod._active_run = None

    # Path 2: Recorded SIGINT in SignalExitCapture upgraded on stop().
    run2 = start()
    run2._hardware_future_done.wait(timeout=2.0)
    assert run2.signal_capture is not None
    run2.signal_capture._signals_received.append(
        {"signal_number": 2, "signal_name": "SIGINT", "timestamp_utc": clock.time()}
    )
    clock.advance(0.27)
    run2.stop(outcome="completed")

    m2 = _read_manifest(run2.run_dir)
    assert m2["status"]["outcome"] == "interrupted"
    assert m2["timing"]["workload_seconds"] == pytest.approx(0.27, abs=1e-9)
    assert m2["timing"]["elapsed_seconds"] == pytest.approx(0.27, abs=1e-9)


def test_double_stop_idempotency_preserves_timing_and_skips_rewrite(monkeypatch):
    clock = _install_fake_clock(monkeypatch, wall=1_750_000_000.0, mono=1200.0)
    _stub_fast_hardware(monkeypatch)

    real_atomic = writer_mod._atomic_json_write
    manifest_writes = []

    def count_manifest_writes(path: Path, data):
        if path.name == "manifest.json":
            manifest_writes.append(data["timing"])
        return real_atomic(path, data)

    monkeypatch.setattr(writer_mod, "_atomic_json_write", count_manifest_writes)

    run = start()
    run._hardware_thread.join(timeout=2.0)
    writes_after_start = len(manifest_writes)

    clock.advance(0.15)
    run.stop(outcome="completed")
    writes_after_first_stop = len(manifest_writes)
    assert writes_after_first_stop == writes_after_start + 1

    first_manifest = _read_manifest(run.run_dir)

    # Advance both clocks dramatically and invoke stop/write_artifacts/_mark_finalization_end again.
    clock.advance(10.0)
    clock.jump_wall(500.0)
    run.stop(outcome="failed")
    run.writer.write_artifacts()
    run._mark_finalization_end()

    assert len(manifest_writes) == writes_after_first_stop
    second_manifest = _read_manifest(run.run_dir)
    assert second_manifest["timing"] == first_manifest["timing"]
    assert second_manifest["status"]["outcome"] == "completed"
    assert run.to_manifest_dict()["timing"] == first_manifest["timing"]


def test_partial_startup_ghost_mode_unwritable_dir_and_engine_crash(monkeypatch):
    _install_fake_clock(monkeypatch, wall=1_750_000_000.0, mono=1300.0)

    # Case 1: Unwritable run_dir (mkdir raises PermissionError).
    monkeypatch.setattr(
        Path,
        "mkdir",
        lambda self, *a, **kw: (_ for _ in ()).throw(PermissionError("read-only fs")),
    )
    ghost_fs = Run()
    assert ghost_fs._outcome == "ghost"
    assert ghost_fs._finalized is True
    assert ghost_fs._workload_start_mono is None
    assert ghost_fs._workload_end_mono is None
    timing_fs = ghost_fs.to_manifest_dict()["timing"]
    assert timing_fs["capture_state"] == {
        "status": "partial",
        "detail": "ghost mode: startup did not complete",
    }
    assert timing_fs["elapsed_seconds"] is None
    assert timing_fs["workload_seconds"] is None
    assert timing_fs["startup_overhead_seconds"] is None
    assert timing_fs["finalization_overhead_seconds"] is None
    assert timing_fs["session_seconds"] is None
    assert timing_fs["duration_clock"] is None
    assert timing_fs["elapsed_basis"] is None
    assert timing_fs["interval_scope"] == "tracked_interval"
    ghost_fs.stop()

    # Case 2: Post-bootstrap startup manifest write failure (unusable output -> ghost rollback).
    monkeypatch.undo()
    _install_fake_clock(monkeypatch, wall=1_750_000_000.0, mono=1400.0)

    def _fail_startup(self, *args, **kwargs):
        self.last_error = "PermissionError: read-only output"
        return False

    monkeypatch.setattr(writer_mod.ArtifactWriter, "write_startup_manifest", _fail_startup)
    ghost_eng = Run()
    assert ghost_eng._outcome == "ghost"
    assert ghost_eng._finalized is True
    assert ghost_eng._workload_start_mono is None
    assert ghost_eng._workload_end_mono is None
    timing_eng = ghost_eng.to_manifest_dict()["timing"]
    assert timing_eng["capture_state"] == {
        "status": "partial",
        "detail": "ghost mode: startup did not complete",
    }
    assert timing_eng["elapsed_seconds"] is None
    assert timing_eng["workload_seconds"] is None
    assert timing_eng["duration_clock"] is None
    assert timing_eng["elapsed_basis"] is None
    assert timing_eng["interval_scope"] == "tracked_interval"
    ghost_eng.stop()


def test_no_raw_monotonic_counter_values_leaked_in_manifest(monkeypatch):
    sentinel_offset = 987654.321
    clock = _install_fake_clock(monkeypatch, wall=1_750_000_000.0, mono=sentinel_offset)
    _stub_fast_hardware(monkeypatch)

    run = start()
    run._hardware_thread.join(timeout=2.0)
    clock.advance(0.05)
    run.stop(outcome="completed")

    raw_text = (run.run_dir / "manifest.json").read_text(encoding="utf-8")
    manifest = json.loads(raw_text)

    assert "987654" not in raw_text

    def _walk(obj):
        if isinstance(obj, dict):
            for k, v in obj.items():
                assert not k.endswith("_mono"), f"raw monotonic key leaked: {k}"
                assert "perf_counter" not in k, f"raw perf_counter key leaked: {k}"
                _walk(v)
        elif isinstance(obj, list):
            for item in obj:
                _walk(item)
        elif isinstance(obj, (int, float)) and not isinstance(obj, bool):
            assert abs(obj - sentinel_offset) > 1000.0, f"raw monotonic value leaked: {obj}"

    _walk(manifest)
    assert manifest["timing"]["workload_seconds"] == pytest.approx(0.05, abs=1e-9)


def _stall_refresh_write(monkeypatch, clock: FakeClock, stall_seconds: float):
    """Stall the coalesced hardware refresh write, advancing the fake clock by the stall."""
    refresh_entered = threading.Event()
    release_refresh = threading.Event()
    original = writer_mod.ArtifactWriter.write_startup_manifest

    def stalled(self, *args, is_refresh: bool = False, **kwargs):
        if is_refresh:
            refresh_entered.set()
            release_refresh.wait(timeout=5.0)
            clock.advance(stall_seconds)
        return original(self, *args, is_refresh=is_refresh, **kwargs)

    monkeypatch.setattr(writer_mod.ArtifactWriter, "write_startup_manifest", stalled)
    return refresh_entered, release_refresh


def _start_with_pending_hardware(monkeypatch):
    """Start a run whose hardware capture completes only after start() returns."""
    release_hw = threading.Event()

    def pending_hw(config):
        release_hw.wait(timeout=5.0)
        return {"capture_state": {"status": "complete"}}

    monkeypatch.setattr(tracker_mod, "get_hardware", pending_hw)
    monkeypatch.setattr(
        tracker_mod,
        "get_host",
        lambda config: {"capture_state": {"status": "complete"}},
    )
    import pubrun.capture.filesystem as fs_mod

    monkeypatch.setattr(
        fs_mod,
        "get_filesystem",
        lambda config, paths: {"capture_state": {"status": "complete"}},
    )

    try:
        run = start()
    finally:
        release_hw.set()
    return run


@pytest.mark.parametrize("entry", ["run_stop", "write_artifacts"])
def test_stalled_hardware_refresh_write_isolated_from_workload(monkeypatch, entry):
    clock = _install_fake_clock(monkeypatch, wall=1_750_000_000.0, mono=1100.0)
    refresh_entered, release_refresh = _stall_refresh_write(monkeypatch, clock, 0.40)

    run = None
    try:
        run = _start_with_pending_hardware(monkeypatch)
        assert refresh_entered.wait(timeout=5.0)

        clock.advance(0.02)
        if entry == "run_stop":
            target = lambda: run.stop(outcome="completed")  # noqa: E731
        else:
            target = run.writer.write_artifacts
        finisher = threading.Thread(target=target, name="test-finisher")
        finisher.start()

        # The finishing call must be blocked behind the refresh holding _run_lock.
        finisher.join(timeout=0.2)
        assert finisher.is_alive()

        release_refresh.set()
        finisher.join(timeout=5.0)
        assert not finisher.is_alive()
        run._hardware_thread.join(timeout=5.0)

        timing = _read_manifest(run.run_dir)["timing"]
        assert timing["workload_seconds"] == pytest.approx(0.02, abs=1e-9)
        assert timing["elapsed_seconds"] == pytest.approx(0.02, abs=1e-9)
        assert timing["finalization_overhead_seconds"] == pytest.approx(0.40, abs=1e-9)
        assert timing["session_seconds"] == pytest.approx(
            timing["startup_overhead_seconds"]
            + timing["workload_seconds"]
            + timing["finalization_overhead_seconds"],
            abs=1e-9,
        )
    finally:
        release_refresh.set()
        if run is not None and getattr(run, "_hardware_thread", None):
            run._hardware_thread.join(timeout=5.0)
