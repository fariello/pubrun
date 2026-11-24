"""Behavioral tests for startup write coalescing, durability policy, and capture budgets."""
import json
import os
import subprocess
import threading
import time
from pathlib import Path

import pytest

import pubrun
import pubrun.capture.filesystem as fs_mod
import pubrun.capture.hardware as hw_mod
import pubrun.tracker as tracker_mod
import pubrun.writer as writer_mod
from pubrun.config import load_default_config
from pubrun.tracker import Run


def _stub_fast_hw_and_git(monkeypatch):
    monkeypatch.setattr(
        tracker_mod,
        "get_git",
        lambda cfg: {"capture_state": {"status": "unavailable"}},
    )
    monkeypatch.setattr(
        tracker_mod,
        "get_hardware",
        lambda cfg: (
            {"capture_state": {"status": "suppressed"}}
            if cfg.get("capture", {}).get("hardware", {}).get("depth") == "off"
            else {
                "cpu": {"architecture": "x86_64", "logical_cores": 4, "model": "Test CPU"},
                "memory_total_bytes": 1024 * 1024 * 1024,
                "gpus": [],
                "capture_state": {"status": "complete"},
            }
        ),
    )
    monkeypatch.setattr(
        tracker_mod,
        "get_host",
        lambda cfg: {
            "os_name": "Linux",
            "os_version": "6.0",
            "hostname": {"representation": "plain", "value": "test-host"},
            "capture_state": {"status": "complete"},
        },
    )
    monkeypatch.setattr(
        fs_mod,
        "get_filesystem",
        lambda cfg, paths: {"capture_state": {"status": "complete"}},
    )


def test_default_config_declares_durability_and_capture_budgets():
    """default.toml exposes [core].artifact_durability and total_timeout capture budgets."""
    cfg = load_default_config()
    assert cfg["core"]["artifact_durability"] == "fsync"
    assert cfg["capture"]["git"]["total_timeout"] == 5
    assert cfg["capture"]["hardware"]["total_timeout"] == 10


def test_unchanged_config_written_once_across_lifecycle(tmp_path, monkeypatch):
    """Unchanged config.resolved.json is written once at startup, skipped on refresh and stop."""
    monkeypatch.setattr("pathlib.Path.cwd", lambda: tmp_path)
    _stub_fast_hw_and_git(monkeypatch)

    hw_release = threading.Event()
    real_get_hw = tracker_mod.get_hardware

    def gated_hw(cfg):
        hw_release.wait(timeout=2.0)
        return real_get_hw(cfg)

    monkeypatch.setattr(tracker_mod, "get_hardware", gated_hw)

    config_writes = []
    real_atomic = writer_mod._atomic_json_write

    def spy_atomic(path, data, **kwargs):
        if Path(path).name == "config.resolved.json":
            config_writes.append(Path(path))
        return real_atomic(path, data, **kwargs)

    monkeypatch.setattr(writer_mod, "_atomic_json_write", spy_atomic)

    run = pubrun.start()
    try:
        config_path = run.run_dir / "config.resolved.json"
        assert config_path.exists()
        assert len(config_writes) == 1
        startup_mtime_ns = config_path.stat().st_mtime_ns
        startup_content = json.loads(config_path.read_text(encoding="utf-8"))

        # Let hardware thread finish and trigger refresh manifest write.
        hw_release.set()
        run._hardware_thread.join(timeout=2.0)
        assert len(config_writes) == 1
        assert config_path.stat().st_mtime_ns == startup_mtime_ns
    finally:
        hw_release.set()
        run.stop(outcome="completed")

    assert len(config_writes) == 1
    assert config_path.stat().st_mtime_ns == startup_mtime_ns
    assert json.loads(config_path.read_text(encoding="utf-8")) == startup_content


def test_finalize_mode_fsyncs_unchanged_config_in_place_without_second_replace(
    tmp_path, monkeypatch
):
    """finalize policy skips startup fsync and fsyncs unchanged config in place on stop()."""
    monkeypatch.setattr("pathlib.Path.cwd", lambda: tmp_path)
    _stub_fast_hw_and_git(monkeypatch)

    atomic_events = []
    fsync_existing_events = []
    real_atomic = writer_mod._atomic_json_write
    real_fsync_existing = writer_mod._fsync_existing_file

    def spy_atomic(path, data, **kwargs):
        atomic_events.append((Path(path).name, kwargs.get("durability")))
        return real_atomic(path, data, **kwargs)

    def spy_fsync_existing(path, *, durability):
        fsync_existing_events.append((Path(path).name, durability))
        return real_fsync_existing(path, durability=durability)

    monkeypatch.setattr(writer_mod, "_atomic_json_write", spy_atomic)
    monkeypatch.setattr(writer_mod, "_fsync_existing_file", spy_fsync_existing)

    run = pubrun.start(core={"artifact_durability": "finalize"})
    if run._hardware_thread is not None:
        run._hardware_thread.join(timeout=2.0)
    run.stop(outcome="completed")

    config_atomic_writes = [e for e in atomic_events if e[0] == "config.resolved.json"]
    assert config_atomic_writes == [("config.resolved.json", "atomic")]
    assert fsync_existing_events == [("config.resolved.json", "fsync")]
    # Final manifest write used fsync
    manifest_writes = [e for e in atomic_events if e[0] == "manifest.json"]
    assert manifest_writes[-1] == ("manifest.json", "fsync")


def test_mid_run_reconfiguration_persists_in_place_and_after_output_dir_migration(
    tmp_path, monkeypatch
):
    """Mid-run overrides via pubrun.start(...) update config.resolved.json before and after stop."""
    monkeypatch.setattr("pathlib.Path.cwd", lambda: tmp_path)
    _stub_fast_hw_and_git(monkeypatch)

    run = pubrun.start()
    try:
        cfg_before = json.loads((run.run_dir / "config.resolved.json").read_text(encoding="utf-8"))
        assert cfg_before["events"]["flush_interval_events"] == 100

        # 1. In-place override
        pubrun.start(events={"flush_interval_events": 25})
        cfg_mid = json.loads((run.run_dir / "config.resolved.json").read_text(encoding="utf-8"))
        assert cfg_mid["events"]["flush_interval_events"] == 25

        # 2. output_dir migration
        migrated_base = tmp_path / "migrated_runs"
        pubrun.start(
            core={"output_dir": str(migrated_base)},
            events={"flush_interval_events": 40},
        )
        assert run.run_dir.parent == migrated_base
        cfg_migrated = json.loads(
            (run.run_dir / "config.resolved.json").read_text(encoding="utf-8")
        )
        assert cfg_migrated["core"]["output_dir"] == str(migrated_base)
        assert cfg_migrated["events"]["flush_interval_events"] == 40
    finally:
        # Balance the 3 start() ref_counts
        run.stop()
        run.stop()
        run.stop()

    cfg_final = json.loads((run.run_dir / "config.resolved.json").read_text(encoding="utf-8"))
    assert cfg_final["core"]["output_dir"] == str(migrated_base)
    assert cfg_final["events"]["flush_interval_events"] == 40


def test_hardware_off_skips_thread_spawn_and_duplicate_startup_write(tmp_path, monkeypatch):
    """hardware.depth='off' spawns no pubrun-hw thread, writes startup once, isolates host/fs."""
    monkeypatch.setattr("pathlib.Path.cwd", lambda: tmp_path)
    _stub_fast_hw_and_git(monkeypatch)

    spawned_threads = []
    real_thread_start = threading.Thread.start

    def spy_thread_start(self, *args, **kwargs):
        spawned_threads.append(self.name)
        return real_thread_start(self, *args, **kwargs)

    manifest_writes = []
    real_atomic = writer_mod._atomic_json_write

    def spy_atomic(path, data, **kwargs):
        if Path(path).name == "manifest.json":
            manifest_writes.append(data["status"]["outcome"])
        return real_atomic(path, data, **kwargs)

    monkeypatch.setattr(threading.Thread, "start", spy_thread_start)
    monkeypatch.setattr(writer_mod, "_atomic_json_write", spy_atomic)

    run = pubrun.start(
        capture={
            "hardware": {"depth": "off"},
            "resources": {"depth": "off"},
        }
    )
    try:
        assert "pubrun-hw" not in spawned_threads
        assert run._hardware_thread is None
        assert run._hardware_future_done.is_set() is True
        assert manifest_writes == ["running"]
        assert run.hardware_data["capture_state"]["status"] == "suppressed"
        assert run.host_data["capture_state"]["status"] == "complete"
        assert run.filesystem_data["capture_state"]["status"] == "complete"
    finally:
        run.stop(outcome="completed")

    assert manifest_writes == ["running", "completed"]


def test_hardware_off_isolates_host_failure_from_filesystem(tmp_path, monkeypatch):
    """When hardware.depth='off' and get_host raises, filesystem still completes independently."""
    monkeypatch.setattr("pathlib.Path.cwd", lambda: tmp_path)
    _stub_fast_hw_and_git(monkeypatch)
    monkeypatch.setattr(
        tracker_mod,
        "get_host",
        lambda cfg: (_ for _ in ()).throw(RuntimeError("host broken")),
    )

    run = pubrun.start(capture={"hardware": {"depth": "off"}, "resources": {"depth": "off"}})
    try:
        assert run.hardware_data["capture_state"]["status"] == "suppressed"
        assert run.host_data["capture_state"]["status"] == "failed"
        assert run.filesystem_data["capture_state"]["status"] == "complete"
    finally:
        run.stop(outcome="completed")


def test_startup_included_hardware_suppresses_refresh_only_when_done_before_manifest(
    tmp_path, monkeypatch
):
    """Fast hardware completed before to_manifest_dict skips refresh; mid-call completion does not."""
    monkeypatch.setattr("pathlib.Path.cwd", lambda: tmp_path)
    _stub_fast_hw_and_git(monkeypatch)

    # Case 1: Hardware finishes BEFORE initial write_startup_manifest calls to_manifest_dict.
    manifest_writes_1 = []
    real_atomic = writer_mod._atomic_json_write
    real_write_startup = writer_mod.ArtifactWriter.write_startup_manifest

    def wait_then_write_startup(self, *args, **kwargs):
        if not kwargs.get("is_refresh", False) and self.run._hardware_future_done is not None:
            self.run._hardware_future_done.wait(timeout=2.0)
        return real_write_startup(self, *args, **kwargs)

    def spy_atomic_1(path, data, **kwargs):
        if Path(path).name == "manifest.json":
            manifest_writes_1.append(data["hardware"]["capture_state"]["status"])
        return real_atomic(path, data, **kwargs)

    monkeypatch.setattr(writer_mod.ArtifactWriter, "write_startup_manifest", wait_then_write_startup)
    monkeypatch.setattr(writer_mod, "_atomic_json_write", spy_atomic_1)

    run1 = Run(overrides={"capture": {"resources": {"depth": "off"}}})
    try:
        run1._hardware_thread.join(timeout=2.0)
        assert run1.writer._startup_included_hardware is True
        # Only 1 startup manifest write occurred (already had complete hardware).
        assert manifest_writes_1 == ["complete"]
    finally:
        run1.stop(outcome="completed")

    # Case 2: Hardware finishes AFTER to_manifest_dict captured "pending" -> refresh MUST happen.
    monkeypatch.undo()
    monkeypatch.setattr("pathlib.Path.cwd", lambda: tmp_path)
    _stub_fast_hw_and_git(monkeypatch)

    hw_entered = threading.Event()
    release_hw = threading.Event()
    real_get_hw = tracker_mod.get_hardware

    def gated_hw(cfg):
        hw_entered.set()
        release_hw.wait(timeout=2.0)
        return real_get_hw(cfg)

    monkeypatch.setattr(tracker_mod, "get_hardware", gated_hw)

    manifest_writes_2 = []
    config_writes_2 = []
    real_to_manifest = Run.to_manifest_dict
    first_call = [True]

    def race_to_manifest(self):
        result = real_to_manifest(self)
        if first_call[0]:
            first_call[0] = False
            # Release hardware AFTER to_manifest_dict captured "pending" but BEFORE
            # write_startup_manifest finishes writing manifest.json.
            hw_entered.wait(timeout=2.0)
            release_hw.set()
            if self._hardware_future_done is not None:
                self._hardware_future_done.wait(timeout=2.0)
        return result

    def spy_atomic_2(path, data, **kwargs):
        if Path(path).name == "manifest.json":
            manifest_writes_2.append(data["hardware"]["capture_state"]["status"])
        elif Path(path).name == "config.resolved.json":
            config_writes_2.append(Path(path))
        return real_atomic(path, data, **kwargs)

    monkeypatch.setattr(Run, "to_manifest_dict", race_to_manifest)
    monkeypatch.setattr(writer_mod, "_atomic_json_write", spy_atomic_2)

    run2 = Run(overrides={"capture": {"resources": {"depth": "off"}}})
    try:
        run2._hardware_thread.join(timeout=2.0)
        # Initial startup wrote "pending"; refresh MUST NOT be suppressed and writes "complete".
        assert manifest_writes_2 == ["pending", "complete"]
        # Unchanged config.resolved.json still written only once.
        assert len(config_writes_2) == 1
        on_disk = json.loads((run2.run_dir / "manifest.json").read_text(encoding="utf-8"))
        assert on_disk["hardware"]["capture_state"]["status"] == "complete"
    finally:
        release_hw.set()
        run2.stop(outcome="completed")


def test_crash_evidence_present_immediately_after_run_init(tmp_path, monkeypatch):
    """Immediately after Run(), both manifest.json (outcome='running') and config exist and parse."""
    monkeypatch.setattr("pathlib.Path.cwd", lambda: tmp_path)
    _stub_fast_hw_and_git(monkeypatch)

    run = Run(overrides={"capture": {"resources": {"depth": "off"}}})
    try:
        manifest_path = run.run_dir / "manifest.json"
        config_path = run.run_dir / "config.resolved.json"
        assert manifest_path.exists()
        assert config_path.exists()
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        config = json.loads(config_path.read_text(encoding="utf-8"))
        assert manifest["status"]["outcome"] == "running"
        assert config["core"]["artifact_durability"] == "fsync"
    finally:
        run.stop(outcome="completed")


def test_readonly_output_dir_enters_ghost_mode_cleanly(tmp_path, monkeypatch):
    """Read-only output directory causes Run() to enter ghost mode without raising."""
    monkeypatch.setattr("pathlib.Path.cwd", lambda: tmp_path)
    monkeypatch.setattr(
        Path,
        "mkdir",
        lambda self, *a, **kw: (_ for _ in ()).throw(PermissionError("read-only filesystem")),
    )

    run = Run()
    assert run._outcome == "ghost"
    assert run.is_active is False
    assert run.writer is None
    run.stop()


def test_concurrent_hardware_refresh_vs_finalize_no_deadlock_or_clobber(tmp_path, monkeypatch):
    """Stress race between pubrun-hw refresh and stop()/write_artifacts(): zero deadlocks or clobber."""
    monkeypatch.setattr("pathlib.Path.cwd", lambda: tmp_path)
    _stub_fast_hw_and_git(monkeypatch)
    real_get_hw = tracker_mod.get_hardware

    for iteration in range(15):
        hw_gate = threading.Event()
        hw_started = threading.Event()

        def gated_hw(cfg, _gate=hw_gate, _started=hw_started):
            _started.set()
            _gate.wait(timeout=2.0)
            return real_get_hw(cfg)

        monkeypatch.setattr(tracker_mod, "get_hardware", gated_hw)

        run = Run(
            overrides={
                "core": {"artifact_durability": "atomic"},
                "capture": {"resources": {"depth": "off"}},
            }
        )
        hw_started.wait(timeout=2.0)

        # Shorten _finalize_state wait on alternating iterations so slow hardware
        # also finishes AFTER stop() has finalized and written manifest.json.
        if iteration % 2 == 1:
            real_wait = run._hardware_future_done.wait
            monkeypatch.setattr(
                run._hardware_future_done,
                "wait",
                lambda timeout=None, _rw=real_wait: _rw(timeout=0.005),
            )

        stop_done = threading.Event()
        stop_errors = []

        def _do_stop(_run=run, _done=stop_done, _errs=stop_errors):
            try:
                _run.stop(outcome="completed")
            except Exception as exc:
                _errs.append(exc)
            finally:
                _done.set()

        stopper = threading.Thread(target=_do_stop)
        stopper.start()
        if iteration % 2 == 1:
            # Let stop() finish before releasing hardware so hw thread tries to refresh post-finalize
            assert stop_done.wait(timeout=5.0), f"Deadlock on iteration {iteration}"
            hw_gate.set()
        else:
            # Release hardware right alongside stop() to race refresh vs finalize
            hw_gate.set()
            assert stop_done.wait(timeout=5.0), f"Deadlock on iteration {iteration}"

        stopper.join(timeout=2.0)
        assert not stopper.is_alive(), f"stop() thread hung on iteration {iteration}"
        if run._hardware_thread is not None:
            run._hardware_thread.join(timeout=2.0)
            assert not run._hardware_thread.is_alive(), f"pubrun-hw hung on iteration {iteration}"
        assert stop_errors == []

        manifest = json.loads((run.run_dir / "manifest.json").read_text(encoding="utf-8"))
        config = json.loads((run.run_dir / "config.resolved.json").read_text(encoding="utf-8"))
        assert manifest["status"]["outcome"] == "completed"
        assert config["core"]["artifact_durability"] == "atomic"


@pytest.mark.parametrize("durability", ["fsync", "atomic"])
def test_concurrent_readers_always_see_valid_json_and_zero_tmp_leftovers(
    tmp_path, monkeypatch, durability
):
    """Concurrent reader threads see only complete valid JSON during rapid writes."""
    monkeypatch.setattr("pathlib.Path.cwd", lambda: tmp_path)
    _stub_fast_hw_and_git(monkeypatch)

    run = Run(
        overrides={
            "core": {"artifact_durability": durability},
            "capture": {"resources": {"depth": "off"}},
        }
    )
    manifest_path = run.run_dir / "manifest.json"
    config_path = run.run_dir / "config.resolved.json"

    stop_readers = threading.Event()
    read_errors = []
    reads_completed = [0]
    read_lock = threading.Condition()

    def _reader():
        while not stop_readers.is_set():
            for target in (manifest_path, config_path):
                try:
                    raw = target.read_text(encoding="utf-8")
                    json.loads(raw)
                    with read_lock:
                        reads_completed[0] += 1
                        read_lock.notify_all()
                except FileNotFoundError:
                    pass
                except PermissionError:
                    # On Windows, concurrent os.replace() can raise transient
                    # sharing violations when a reader opens the target file.
                    if os.name != "nt":
                        with read_lock:
                            read_errors.append((target.name, "PermissionError", "unexpected on POSIX"))
                except Exception as exc:
                    with read_lock:
                        read_errors.append((target.name, type(exc).__name__, str(exc)))

    readers = [threading.Thread(target=_reader, daemon=True) for _ in range(3)]
    for t in readers:
        t.start()

    try:
        for i in range(15):
            run.config["events"]["flush_interval_events"] = 10 + i
            run.writer.sync_config_if_changed()
            run.writer.write_startup_manifest(is_refresh=False)
        run.stop(outcome="completed")
        with read_lock:
            target_reads = reads_completed[0] + len(readers) + 1
            reached = read_lock.wait_for(
                lambda: reads_completed[0] >= target_reads,
                timeout=5.0,
            )
        assert reached, "readers did not complete post-stop reads within timeout"
    finally:
        stop_readers.set()
        for t in readers:
            t.join(timeout=2.0)

    assert reads_completed[0] > 0
    assert read_errors == []
    assert list(run.run_dir.glob("*.tmp")) == []


def test_hardware_timeout_expired_and_budget_exhaustion_report_partial_and_timeout(monkeypatch):
    """Hardware capture catches TimeoutExpired explicitly and bounds total probe time."""
    # Scenario 1: CPU and RAM succeed (darwin sysctl), nvidia-smi times out exhausting budget ->
    # system_profiler fallback is skipped and capture_state reports "partial".
    now = [200.0]
    calls_1 = []

    def fake_mono_1():
        return now[0]

    def fake_check_output_1(cmd, **kwargs):
        calls_1.append(list(cmd))
        if cmd[:2] == ["sysctl", "-n"] and "brand_string" in cmd[2]:
            now[0] += 0.1
            return "Apple M3\n"
        if cmd[:2] == ["sysctl", "-n"] and "memsize" in cmd[2]:
            now[0] += 0.1
            return "17179869184\n"
        if cmd[0] == "nvidia-smi":
            now[0] += 1.0
            raise subprocess.TimeoutExpired(cmd=cmd, timeout=kwargs.get("timeout", 1.0))
        return "Chipset Model: Apple M3\n"

    monkeypatch.setattr(hw_mod.sys, "platform", "darwin")
    monkeypatch.setattr(hw_mod.time, "monotonic", fake_mono_1)
    monkeypatch.setattr(hw_mod.subprocess, "check_output", fake_check_output_1)

    res_partial = hw_mod.get_hardware(
        {"capture": {"hardware": {"depth": "basic", "timeout": 1.0, "total_timeout": 1.0}}}
    )
    assert res_partial["capture_state"]["status"] == "partial"
    assert res_partial["cpu"]["model"] == "Apple M3"
    assert res_partial["memory_total_bytes"] == 17179869184
    assert res_partial["gpus"] == []
    # system_profiler must be skipped after budget exhausted
    assert all(c[0] != "system_profiler" for c in calls_1)

    # Scenario 2: CPU probe times out and exhausts total_timeout -> RAM and GPU probes skipped,
    # zero probed fields succeeded -> capture_state reports "timeout" with schema-valid shape.
    now_2 = [300.0]
    calls_2 = []

    def fake_mono_2():
        return now_2[0]

    def fake_check_output_2(cmd, **kwargs):
        calls_2.append(list(cmd))
        now_2[0] += 1.0
        raise subprocess.TimeoutExpired(cmd=cmd, timeout=kwargs.get("timeout", 0.5))

    monkeypatch.setattr(hw_mod.time, "monotonic", fake_mono_2)
    monkeypatch.setattr(hw_mod.subprocess, "check_output", fake_check_output_2)

    res_timeout = hw_mod.get_hardware(
        {"capture": {"hardware": {"depth": "basic", "timeout": 0.5, "total_timeout": 0.5}}}
    )
    assert res_timeout["capture_state"]["status"] == "timeout"
    assert res_timeout["cpu"]["model"] is None
    assert res_timeout["memory_total_bytes"] is None
    assert res_timeout["gpus"] == []
    assert len(calls_2) == 1
