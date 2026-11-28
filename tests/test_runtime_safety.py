"""Behavioral regression tests for runtime, fork, lock, console, clean, and path safety."""

import io
import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path
from unittest import mock

import pytest

import pubrun
from pubrun.capture.console import ConsoleInterceptor, TqdmSafeTee
from pubrun.capture.liveness import (
    _check_command_linux,
    _get_cpu_windows,
    _get_rss_windows,
    _get_start_time_windows,
    _is_pid_alive_windows,
)
from pubrun.capture.redaction import redact_value
from pubrun.capture.signals import SignalExitCapture
from pubrun.status import (
    can_safely_auto_close_crashed_run,
    clean_runs,
    close_out_crashed_run,
    scan_runs,
)


@pytest.mark.skipif(not hasattr(os, "fork"), reason="POSIX fork() only")
def test_forked_child_exit_does_not_clobber_parent_lock_or_manifest(tmp_path: Path) -> None:
    """A forked child exiting cleanly or via SIGTERM must not touch parent lock/manifest."""
    script = tmp_path / "fork_parent.py"
    out_dir = tmp_path / "runs"
    script.write_text(
        f"""
import json, os, signal, sys, time
import pubrun.noauto as pubrun
pubrun.start(output_dir={str(out_dir)!r})
run = pubrun.get_current_run()
run_dir = run.run_dir
lock_path = run_dir / ".pubrun.lock"
assert lock_path.exists(), "parent lock missing before fork"

# Child 1: normal sys.exit(0) (runs atexit)
pid1 = os.fork()
if pid1 == 0:
    sys.exit(0)
_, st1 = os.waitpid(pid1, 0)
assert os.WIFEXITED(st1) and os.WEXITSTATUS(st1) == 0
assert lock_path.exists(), "child1 atexit removed parent lock"

# Child 2: killed by SIGTERM (hits signal handler)
pid2 = os.fork()
if pid2 == 0:
    os.kill(os.getpid(), signal.SIGTERM)
    os._exit(99)
_, st2 = os.waitpid(pid2, 0)
assert os.WIFSIGNALED(st2) and os.WTERMSIG(st2) == signal.SIGTERM
assert lock_path.exists(), "child2 SIGTERM removed parent lock"

manifest_during = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
assert manifest_during["status"]["outcome"] == "running"

pubrun.stop()
assert not lock_path.exists(), "parent stop did not remove its own lock"
manifest_final = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
assert manifest_final["status"]["outcome"] == "completed"
""",
        encoding="utf-8",
    )
    proc = subprocess.run(
        [sys.executable, str(script)],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert proc.returncode == 0, f"stdout={proc.stdout}\nstderr={proc.stderr}"


def test_auto_close_refuses_unreadable_and_remote_locks(tmp_path: Path) -> None:
    """Unreadable/empty locks and >48h remote-host locks must never be auto-closed."""
    runs_dir = tmp_path / "runs"

    # 1. Empty/truncated lock (simulating startup race)
    empty_dir = runs_dir / "pubrun-train-20261126T000000Z-999999-empty001"
    empty_dir.mkdir(parents=True)
    (empty_dir / ".pubrun.lock").write_text("", encoding="utf-8")
    assert can_safely_auto_close_crashed_run(empty_dir, None) is False

    # 2. Remote-host lock >48h old (long HPC compute job)
    remote_dir = runs_dir / "pubrun-hpc-20261120T000000Z-424242-rem00001"
    remote_dir.mkdir(parents=True)
    remote_lock = {
        "pid": 424242,
        "started_at_utc": time.time() - 200000,
        "script": "hpc.py",
        "run_id": "rem00001",
        "hostname": "compute-node-999.cluster.invalid",
    }
    (remote_dir / ".pubrun.lock").write_text(json.dumps(remote_lock), encoding="utf-8")
    assert can_safely_auto_close_crashed_run(remote_dir, remote_lock) is False

    # 3. Close-out also refuses to overwrite an already-finalized run when lock vanished
    done_dir = runs_dir / "pubrun-done-20261126T000000Z-12345-done0001"
    done_dir.mkdir(parents=True)
    final_manifest = {
        "schema_version": "1.0",
        "manifest_type": "pubrun-manifest",
        "status": {"outcome": "completed", "capture_state": {"status": "complete"}},
    }
    (done_dir / "manifest.json").write_text(json.dumps(final_manifest), encoding="utf-8")
    close_out_crashed_run(done_dir, {"run_id": "done0001", "started_at_utc": time.time() - 10})
    after = json.loads((done_dir / "manifest.json").read_text(encoding="utf-8"))
    assert after["status"]["outcome"] == "completed"


def test_clean_skips_symlinks_and_remote_host_locks(tmp_path: Path) -> None:
    """scan_runs and clean_runs must skip symlinks and refuse deleting remote-host locked runs."""
    runs_dir = tmp_path / "runs"
    runs_dir.mkdir()
    outside = tmp_path / "outside_important_dir"
    outside.mkdir()
    (outside / "keep.txt").write_text("do not delete", encoding="utf-8")

    # Symlink disguised as a pubrun directory
    sym = runs_dir / "pubrun-evil-20261126T000000Z-1-evil0001"
    sym.symlink_to(outside, target_is_directory=True)
    assert scan_runs(str(runs_dir)) == []
    assert (outside / "keep.txt").exists()

    # Remote-host >48h locked run (classified crashed by age, must not be deleted by clean)
    remote_dir = runs_dir / "pubrun-hpc-20261120T000000Z-424242-rem00002"
    remote_dir.mkdir()
    remote_lock = {
        "pid": 424242,
        "started_at_utc": time.time() - 200000,
        "script": "hpc.py",
        "run_id": "rem00002",
        "hostname": "remote-hpc-node.invalid",
    }
    (remote_dir / ".pubrun.lock").write_text(json.dumps(remote_lock), encoding="utf-8")

    deleted = clean_runs(output_dir=str(runs_dir), status_filter="crashed", yes=True)
    assert deleted == 0
    assert remote_dir.exists()
    assert (outside / "keep.txt").exists()


def test_console_migration_updates_run_dir_and_handles_faulthandler(tmp_path: Path) -> None:
    """ConsoleInterceptor.suspend/resume safely detaches, updates run_dir, and preserves logs."""
    dir1 = tmp_path / "d1"
    dir2 = tmp_path / "d2"
    dir1.mkdir()
    dir2.mkdir()
    interceptor = ConsoleInterceptor(dir1, mode="basic")
    assert interceptor.start() is True
    try:
        sys.stdout.write("before\n")
        was_fh = interceptor.suspend_for_migration()
        assert interceptor.stdout_log is None
        assert interceptor.stderr_log is None
        assert interceptor.stdout_tee is not None and interceptor.stdout_tee.log_file is None
        interceptor.resume_after_migration(dir2, reenable_faulthandler=was_fh)
        assert interceptor.run_dir == dir2
        sys.stdout.write("after\n")
    finally:
        interceptor.stop()

    assert "before" in (dir1 / "stdout.log").read_text(encoding="utf-8")
    assert "after" in (dir2 / "stdout.log").read_text(encoding="utf-8")


def test_tqdm_safe_tee_caps_unbounded_buffer_and_handles_surrogates(tmp_path: Path) -> None:
    """TqdmSafeTee flushes newline-free bursts at cap and survives surrogateescape strings."""
    log_path = tmp_path / "out.log"
    orig = io.StringIO()
    with open(log_path, "w", encoding="utf-8", errors="backslashreplace") as lf:
        tee = TqdmSafeTee(orig, lf, timestamped=False)
        tee.write("x" * (TqdmSafeTee._MAX_BUFFER_CHARS + 100))
        assert len(tee._current_buffer) < TqdmSafeTee._MAX_BUFFER_CHARS
        assert tee.line_count >= 1
        # Surrogateescape character must not raise UnicodeEncodeError
        tee.write("bad\udce9bytes\n")
        tee.flush()
    text = log_path.read_text(encoding="utf-8")
    assert "\\udce9" in text


def test_redaction_hash_and_liveness_surrogate_safety() -> None:
    """Hashing surrogateescape strings and invalid /proc bytes must not crash."""
    res = redact_value("sec\udce9ret", {"redaction": {"representation": "hashed"}})
    assert res["representation"] == "hashed"
    assert len(res["hash_value"]) == 64

    with mock.patch("builtins.open", side_effect=ValueError("invalid")):
        assert _check_command_linux(1, "train.py") is None


def test_sys_exit_multi_arg_raises_type_error_without_recording() -> None:
    """Calling sys.exit with >1 argument raises TypeError and records no bogus exit code."""
    cap = SignalExitCapture()
    cap.install()
    try:
        with pytest.raises(TypeError):
            sys.exit(1, 2)  # type: ignore[call-arg]
        records = cap.get_records()
        assert records.get("exit_code") is None
    finally:
        cap.uninstall()


def test_report_and_artifact_reject_path_traversal(tmp_path: Path) -> None:
    """pubrun.report() and pubrun.artifact() refuse writing outside run_dir."""
    out_dir = tmp_path / "runs"
    escaped = tmp_path / "escaped.txt"
    with pubrun.tracked_run(output_dir=str(out_dir)):
        run = pubrun.get_current_run()
        assert run is not None
        pubrun.artifact("../escaped.txt", "nope")
        pubrun.artifact(str(escaped), "nope")
        pubrun.report("../escape_report", {"a": 1})
        pubrun.artifact("sub/ok.txt", "ok")
        assert (run.run_dir / "sub" / "ok.txt").read_text(encoding="utf-8") == "ok"
    assert not escaped.exists()
    assert not (tmp_path / "escape_report.json").exists()


def test_artifact_rejects_dot_targets(tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
    """pubrun.artifact() refuses '.' and './' targets pointing to the run directory itself."""
    import logging

    out_dir = tmp_path / "runs"
    with pubrun.tracked_run(
        output_dir=str(out_dir),
        console={"capture_mode": "off"},
        capture={"hardware": {"depth": "off"}},
    ) as ctx:
        assert ctx.run_dir is not None
        orig_manifest = (ctx.run_dir / "manifest.json").read_text(encoding="utf-8")
        with caplog.at_level(logging.WARNING, logger="pubrun"):
            pubrun.artifact(".", "nope")
            pubrun.artifact("./", "nope")
        assert (ctx.run_dir / "manifest.json").read_text(encoding="utf-8") == orig_manifest

    warn_msgs = [r.getMessage() for r in caplog.records if r.levelno == logging.WARNING]
    assert any("failed to write artifact '.'" in m for m in warn_msgs)
    assert any("failed to write artifact './'" in m for m in warn_msgs)


def test_artifact_and_report_reject_symlink_escapes_and_reserved_target(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    """pubrun.artifact() and pubrun.report() reject symlinks escaping run_dir or targeting manifest.json."""
    import logging

    outside_dir = tmp_path / "outside_dir"
    outside_dir.mkdir()
    out_dir = tmp_path / "runs"

    with pubrun.tracked_run(
        output_dir=str(out_dir),
        console={"capture_mode": "off"},
        capture={"hardware": {"depth": "off"}},
    ) as ctx:
        assert ctx.run_dir is not None
        manifest_path = ctx.run_dir / "manifest.json"
        orig_manifest = manifest_path.read_text(encoding="utf-8")

        escape_link = ctx.run_dir / "escape_dir"
        manifest_art_link = ctx.run_dir / "manifest_alias.txt"
        manifest_rep_link = ctx.run_dir / "manifest_alias_rep.json"
        try:
            os.symlink(outside_dir, escape_link, target_is_directory=True)
            os.symlink(manifest_path, manifest_art_link)
            os.symlink(manifest_path, manifest_rep_link)
        except (OSError, NotImplementedError) as exc:
            pytest.skip(f"symlinks unavailable on this platform: {exc}")

        with caplog.at_level(logging.WARNING, logger="pubrun"):
            pubrun.artifact("escape_dir/escaped.txt", "evil")
            pubrun.report("escape_dir/escaped_report", {"evil": True})
            pubrun.artifact("manifest_alias.txt", "tampered")
            pubrun.report("manifest_alias_rep", {"tampered": True})

        assert not (outside_dir / "escaped.txt").exists()
        assert not (outside_dir / "escaped_report.json").exists()
        assert manifest_path.read_text(encoding="utf-8") == orig_manifest

    warn_msgs = [r.getMessage() for r in caplog.records if r.levelno == logging.WARNING]
    assert any("failed to write artifact 'escape_dir/escaped.txt'" in m for m in warn_msgs)
    assert any("failed to write report 'escape_dir/escaped_report'" in m for m in warn_msgs)
    assert any("failed to write artifact 'manifest_alias.txt'" in m for m in warn_msgs)
    assert any("failed to write report 'manifest_alias_rep'" in m for m in warn_msgs)


def test_pubrun_run_directory_target_clean_error(tmp_path: Path) -> None:
    """pubrun run exits cleanly without traceback when target is a directory."""
    proc = subprocess.run(
        [sys.executable, "-m", "pubrun", "run", "--", str(tmp_path)],
        capture_output=True,
        text=True,
        timeout=20,
    )
    assert proc.returncode in (126, 127)
    assert "Cannot execute command" in proc.stderr
    assert "Traceback" not in proc.stderr


def test_windows_liveness_helpers_reject_out_of_range_pids() -> None:
    """Windows liveness helpers reject <=0 or >0xFFFFFFFF PIDs safely on any OS."""
    for bad_pid in (0, -1, 0x1_0000_0000):
        assert _is_pid_alive_windows(bad_pid) is False
        assert _get_start_time_windows(bad_pid) is None
        assert _get_rss_windows(bad_pid) is None
        assert _get_cpu_windows(bad_pid) is None


# ==========================================================================
# IPD 76z7ww: Fork/spawn, migration, console, subprocess, and resource safety
# ==========================================================================


def test_deleted_cwd_enters_ghost_mode_and_produces_valid_manifest(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Deleted CWD degrades to Ghost Mode with valid to_manifest_dict() and hint."""
    import pubrun.tracker as tracker_mod
    from pubrun.tracker import Run

    orig_active = tracker_mod._active_run

    def _raise_enoent() -> Path:
        raise FileNotFoundError(2, "No such file or directory")

    monkeypatch.setattr(Path, "cwd", staticmethod(_raise_enoent))
    try:
        run = Run()
        assert run._outcome == "ghost"
        assert run.is_active is False
        assert run.output_base_dir == Path("runs")
        assert run.run_dir.parent == Path("runs")

        manifest = run.to_manifest_dict()
        assert manifest["status"]["outcome"] == "ghost"
        assert manifest["capture"]["output_base_dir"] == "runs"

        stderr = capsys.readouterr().err
        assert "Ghost Mode" in stderr
        assert "[core].output_dir" in stderr
        assert "output_dir=" in stderr
    finally:
        tracker_mod._active_run = orig_active


def test_write_lock_file_survives_deleted_cwd(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Run._write_lock_file falls back to empty cwd string when Path.cwd() raises OSError."""
    from pubrun.tracker import Run

    run = Run(overrides={"output_dir": str(tmp_path), "capture": {"hardware": {"depth": "off"}}})
    try:
        monkeypatch.setattr(
            Path, "cwd", staticmethod(lambda: (_ for _ in ()).throw(OSError("gone")))
        )
        run._write_lock_file()
        lock_data = json.loads((run.run_dir / ".pubrun.lock").read_text(encoding="utf-8"))
        assert lock_data["cwd"] == ""
    finally:
        run.stop()


def test_script_name_normalization_cap_and_unhashed_lock_matching(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Dot/punctuation-only names normalize to interactive; >80-char names cap dir_name while keeping unhashed lock script."""
    import hashlib
    from pubrun.capture.liveness import _match_script_in_tokens
    from pubrun.tracker import Run

    for bad_arg in ("", ".", "..", "...", "!@#$.py"):
        monkeypatch.setattr(sys, "argv", [bad_arg])
        run = Run(overrides={"output_dir": str(tmp_path), "capture": {"hardware": {"depth": "off"}}})
        try:
            assert run.script_name == "interactive"
            assert run._lock_script_name == "interactive"
        finally:
            run.stop()

    long_stem = "long_training_script_" + "x" * 95
    monkeypatch.setattr(sys, "argv", [f"/work/{long_stem}.py"])
    run = Run(overrides={"output_dir": str(tmp_path), "capture": {"hardware": {"depth": "off"}}})
    try:
        expected_digest = hashlib.sha256(long_stem.encode("utf-8")).hexdigest()[:8]
        assert len(run.script_name) == 80
        assert run.script_name == f"{long_stem[:71]}-{expected_digest}"
        assert run._lock_script_name == long_stem
        lock_data = json.loads((run.run_dir / ".pubrun.lock").read_text(encoding="utf-8"))
        assert lock_data["script"] == long_stem
        assert _match_script_in_tokens(lock_data["script"], ["python", f"/work/{long_stem}.py"]) is True
    finally:
        run.stop()


def test_hardware_semaphore_saturation_and_start_failure_release(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """pubrun-hw concurrency is bounded to 4 and semaphore slots release when Thread.start() fails."""
    import threading
    import pubrun.tracker as tracker_mod
    from pubrun.tracker import Run

    # 1. Saturate all 4 slots.
    acquired = 0
    try:
        for _ in range(4):
            assert tracker_mod._HARDWARE_SEMAPHORE.acquire(blocking=False) is True
            acquired += 1
        assert tracker_mod._HARDWARE_SEMAPHORE.acquire(blocking=False) is False

        run = Run(overrides={"output_dir": str(tmp_path), "capture": {"hardware": {"depth": "basic"}}})
        try:
            assert run._hardware_thread is None
            assert run._hardware_future_done is not None and run._hardware_future_done.is_set()
            assert run._background_hardware_seconds == 0.0
            expected = {
                "status": "unavailable",
                "detail": "hardware capture skipped: concurrent thread limit reached",
            }
            assert run.hardware_data["capture_state"] == expected
            assert run.host_data["capture_state"] == expected
            assert run.filesystem_data["capture_state"] == expected
        finally:
            run.stop()
    finally:
        for _ in range(acquired):
            tracker_mod._HARDWARE_SEMAPHORE.release()

    # 2. Thread.start() failure must release the acquired semaphore slot.
    orig_start = threading.Thread.start

    def _fail_hw_start(self: threading.Thread) -> None:
        if self.name == "pubrun-hw":
            raise RuntimeError("simulated thread start failure")
        return orig_start(self)

    monkeypatch.setattr(threading.Thread, "start", _fail_hw_start)
    run2 = Run(overrides={"output_dir": str(tmp_path), "capture": {"hardware": {"depth": "basic"}}})
    try:
        assert run2._hardware_thread is None
        assert run2.hardware_data["capture_state"]["status"] == "failed"
    finally:
        run2.stop()

    # Verify all 4 semaphore slots are still available (zero leak).
    reacquired = 0
    try:
        for _ in range(4):
            assert tracker_mod._HARDWARE_SEMAPHORE.acquire(blocking=False) is True
            reacquired += 1
    finally:
        for _ in range(reacquired):
            tracker_mod._HARDWARE_SEMAPHORE.release()


def test_merge_and_migrate_noop_descendant_print_handle_and_locking(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """_merge_and_migrate handles identical resolved paths, rejects descendants, closes print handle, and avoids lock deadlock."""
    import shutil
    import threading
    import pubrun.core as core_mod
    from pubrun.tracker import Run

    out_a = tmp_path / "runs_a"
    out_b = tmp_path / "runs_b"
    out_a.mkdir()

    run = Run(
        overrides={
            "output_dir": str(out_a),
            "console": {"capture_mode": "off"},
            "capture": {"hardware": {"depth": "off"}},
        }
    )
    try:
        orig_dir = run.run_dir

        # 1. Identical resolved path (via non-normalized ".." segment) is a no-op.
        move_calls = []
        real_move = shutil.move

        def _spy_move(src: str, dst: str) -> str:
            move_calls.append((src, dst, getattr(run, "_print_log_file", None)))
            return real_move(src, dst)

        monkeypatch.setattr(shutil, "move", _spy_move)
        run._merge_and_migrate({"output_dir": str(out_a / "." / ".." / "runs_a")})
        assert run.run_dir == orig_dir
        assert move_calls == []

        # 2. Descendant target (inside run_dir) is rejected without moving.
        run._merge_and_migrate({"output_dir": str(orig_dir / "nested_child")})
        assert run.run_dir == orig_dir
        assert move_calls == []

        # 3. Cached pubrun.print() handle is closed BEFORE shutil.move and reopens in new dir.
        pubrun.print("before-migrate")
        assert getattr(run, "_print_log_file", None) is not None
        run._merge_and_migrate({"output_dir": str(out_b)})
        assert len(move_calls) == 1
        assert move_calls[0][2] is None, "cached print handle must be closed before shutil.move"
        assert run.run_dir.parent == out_b
        pubrun.print("after-migrate")
        log_text = (run.run_dir / "stdout.log").read_text(encoding="utf-8")
        assert "before-migrate" in log_text
        assert "after-migrate" in log_text
    finally:
        run.stop()

    # 4. Joining pubrun-hw outside _run_lock prevents deadlock when pubrun-hw acquires _run_lock.
    out_c = tmp_path / "runs_c"
    out_d = tmp_path / "runs_d"
    run2 = Run(
        overrides={
            "output_dir": str(out_c),
            "capture": {"hardware": {"depth": "off"}},
        }
    )
    try:
        hw_entered = threading.Event()
        hw_release = threading.Event()
        hw_done = threading.Event()

        def _fake_hw_worker() -> None:
            hw_entered.set()
            assert hw_release.wait(timeout=5.0)
            with core_mod._run_lock:
                run2.hardware_data = {"capture_state": {"status": "complete"}}
            hw_done.set()

        t_hw = threading.Thread(target=_fake_hw_worker, daemon=True)
        real_hw_join = t_hw.join

        def _signal_join(timeout=None) -> None:
            hw_release.set()
            real_hw_join(timeout=timeout)

        t_hw.join = _signal_join  # type: ignore[method-assign]
        run2._hardware_thread = t_hw
        run2._hardware_future_done = hw_done
        t_hw.start()
        assert hw_entered.wait(timeout=2.0)

        mig_done = threading.Event()

        def _do_migrate() -> None:
            run2._merge_and_migrate({"output_dir": str(out_d)})
            mig_done.set()

        t_mig = threading.Thread(target=_do_migrate, daemon=True)
        t_mig.start()
        assert mig_done.wait(timeout=5.0), "_merge_and_migrate deadlocked joining pubrun-hw"
        assert hw_release.is_set()
        assert run2.run_dir.parent == out_d
    finally:
        hw_release.set()
        run2.stop()

    # 5. Concurrent stop() racing with _merge_and_migrate() does not deadlock or reopen closed streams.
    out_e = tmp_path / "runs_e"
    out_f = tmp_path / "runs_f"
    run3 = Run(
        overrides={
            "output_dir": str(out_e),
            "events": {"enabled": True},
            "capture": {"hardware": {"depth": "off"}},
        }
    )
    barrier = threading.Barrier(2)

    def _race_migrate() -> None:
        barrier.wait(timeout=5.0)
        run3._merge_and_migrate({"output_dir": str(out_f)})

    def _race_stop() -> None:
        barrier.wait(timeout=5.0)
        run3.stop()

    t1 = threading.Thread(target=_race_migrate, daemon=True)
    t2 = threading.Thread(target=_race_stop, daemon=True)
    t1.start()
    t2.start()
    t1.join(timeout=10.0)
    t2.join(timeout=10.0)
    assert not t1.is_alive() and not t2.is_alive()
    assert run3._finalized is True
    assert run3.is_active is False


def test_rollback_owned_hooks_closes_print_handle_and_releases_yappi_once(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """_rollback_owned_hooks closes cached print handle, disables cProfile under lock, and stops yappi at most once."""
    import types
    import pubrun.core as core_mod

    stop_calls = []

    fake_yappi = types.SimpleNamespace(
        start=lambda: None,
        stop=lambda: stop_calls.append("stop"),
        clear_stats=lambda: None,
        get_func_stats=lambda: types.SimpleNamespace(save=lambda *a, **k: None),
    )
    monkeypatch.setitem(sys.modules, "yappi", fake_yappi)
    core_mod.phase._yappi_active = False

    run = pubrun.start(
        output_dir=str(tmp_path),
        console={"capture_mode": "off"},
        capture={"hardware": {"depth": "off"}, "profiling": {"enabled": True, "backend": "yappi"}},
    )
    try:
        pubrun.print("cached-line")
        print_fh = getattr(run, "_print_log_file", None)
        assert print_fh is not None

        with pubrun.phase("inner_yappi"):
            assert core_mod.phase._yappi_active is True
            assert getattr(run, "_yappi_owned", False) is True
            run.stop()
            assert getattr(run, "_print_log_file", None) is None
            assert print_fh.closed is True
            assert len(stop_calls) == 1

        # phase.__exit__ must not invoke yappi.stop() a second time.
        assert len(stop_calls) == 1
        assert core_mod.phase._yappi_active is False
    finally:
        core_mod.phase._yappi_active = False
        if run.is_active:
            run.stop()


def test_multiprocessing_spawn_suppresses_worker_auto_start_while_subprocess_auto_starts(
    tmp_path: Path,
) -> None:
    """multiprocessing spawn workers do not create run storms, while subprocess.run child scripts still auto-start."""
    src_dir = str(Path(__file__).resolve().parent.parent / "src")
    env = dict(os.environ)
    env["PYTHONPATH"] = src_dir + os.pathsep + env.get("PYTHONPATH", "")
    env["HOME"] = str(tmp_path)
    env["USERPROFILE"] = str(tmp_path)
    env["XDG_CONFIG_HOME"] = str(tmp_path / ".xdg")
    for key in (
        "PUBRUN_DISABLE",
        "PUBRUN_AUTO_START",
        "PUBRUN_IMPORT_MODE",
        "PUBRUN_PROFILE",
        "PUBRUN_META_REF",
    ):
        env.pop(key, None)

    # 1. multiprocessing spawn Pool(2): top-level import pubrun must produce exactly 1 run dir.
    mp_runs = tmp_path / "mp_runs"
    mp_runs.mkdir()
    (tmp_path / ".pubrun.toml").write_text(
        f'[core]\noutput_dir = "{mp_runs.as_posix()}"\n[capture.hardware]\ndepth = "off"\n',
        encoding="utf-8",
    )
    mp_script = tmp_path / "mp_spawn_job.py"
    mp_script.write_text(
        """
import multiprocessing
import pubrun


def worker(x):
    return (x * 2, pubrun.get_current_run() is None)


if __name__ == "__main__":
    ctx = multiprocessing.get_context("spawn")
    with ctx.Pool(2) as pool:
        results = pool.map(worker, [1, 2, 3, 4])
    assert results == [(2, True), (4, True), (6, True), (8, True)], results
""",
        encoding="utf-8",
    )
    proc = subprocess.run(
        [sys.executable, str(mp_script)],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert proc.returncode == 0, f"stdout={proc.stdout}\nstderr={proc.stderr}"
    created = [p for p in mp_runs.iterdir() if p.is_dir() and p.name.startswith("pubrun-")]
    assert len(created) == 1, f"Expected 1 run dir from spawn Pool(2), found {created}"

    # 2. subprocess.run([sys.executable, child_script]) from tracked parent MUST still auto-start.
    sub_runs = tmp_path / "sub_runs"
    sub_runs.mkdir()
    (tmp_path / ".pubrun.toml").write_text(
        f'[core]\noutput_dir = "{sub_runs.as_posix()}"\n[capture.hardware]\ndepth = "off"\n',
        encoding="utf-8",
    )
    child_script = tmp_path / "child_job.py"
    child_script.write_text(
        """
import pubrun
assert pubrun.get_current_run() is not None, "child script did not auto-start"
""",
        encoding="utf-8",
    )
    parent_script = tmp_path / "parent_job.py"
    parent_script.write_text(
        f"""
import subprocess, sys
import pubrun
assert pubrun.get_current_run() is not None
res = subprocess.run([sys.executable, {str(child_script)!r}], check=True)
assert res.returncode == 0
""",
        encoding="utf-8",
    )
    proc2 = subprocess.run(
        [sys.executable, str(parent_script)],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert proc2.returncode == 0, f"stdout={proc2.stdout}\nstderr={proc2.stderr}"
    created_sub = [p for p in sub_runs.iterdir() if p.is_dir() and p.name.startswith("pubrun-")]
    assert len(created_sub) == 2, f"Expected 2 run dirs (parent + child), found {created_sub}"


@pytest.mark.skipif(not hasattr(os, "fork"), reason="POSIX fork() only")
def test_posix_fork_no_duplicate_buffers_no_fd_reuse_corruption_and_no_lock_deadlock(
    tmp_path: Path,
) -> None:
    """POSIX fork() child drops parent buffers without duplicating, avoids reused-FD corruption, and resets held locks."""
    src_dir = str(Path(__file__).resolve().parent.parent / "src")
    env = dict(os.environ)
    env["PYTHONPATH"] = src_dir + os.pathsep + env.get("PYTHONPATH", "")

    out_dir = tmp_path / "fork_runs"
    child_file = tmp_path / "child_reused_fd.txt"
    script = tmp_path / "fork_safety.py"
    script.write_text(
        f"""
import gc, json, os, subprocess, sys, threading
import pubrun.noauto as pubrun
import pubrun.core as core_mod
from pubrun.capture.subprocesses import SubprocessSpy

run = pubrun.start(
    output_dir={str(out_dir)!r},
    console={{"capture_mode": "basic", "non_tty_mode": "basic"}},
    events={{"enabled": True, "flush_interval_events": 1000}},
    capture={{"hardware": {{"depth": "off"}}, "subprocesses": {{"enabled": True}}}},
)

# 1. Create unflushed buffered bytes in stdout.log, events.jsonl, and _print_log_file.
sys.stdout.write("parent-stdout-unique-line\\n")
run.event_stream.emit("annotation", name="parent-event-unique")
# Open a separate buffered _print_log_file handle to verify raw-FD close without flush.
pf = open(run.run_dir / "print_buf.log", "w", encoding="utf-8", buffering=8192)
pf.write("parent-print-unique-line\\n")
run._print_log_file = pf

# Hold TqdmSafeTee._lock, SubprocessSpy._lock, and core._run_lock in a background
# thread while forking to prove the child resets locks and disarms SubprocessSpy lock-free.
locks_held = threading.Event()
release_locks = threading.Event()

def _hold_locks():
    with core_mod._run_lock:
        with SubprocessSpy._lock:
            with run.console_interceptor.stdout_tee._lock:
                locks_held.set()
                release_locks.wait(timeout=10)

holder = threading.Thread(target=_hold_locks, daemon=True)
holder.start()
assert locks_held.wait(timeout=5)

pid = os.fork()
if pid == 0:
    # Child: inherited locks must be reset, SubprocessSpy disarmed, streams restored.
    assert pubrun.get_current_run() is None
    assert SubprocessSpy._installed is False
    assert sys.stdout is run.console_interceptor.original_stdout

    # Open a brand-new file (kernel reuses lowest closed FDs), write to it,
    # trigger GC so any inherited wrappers cannot flush into or close this reused FD.
    with open({str(child_file)!r}, "w", encoding="utf-8") as cf:
        cf.write("child-clean-line\\n")
        gc.collect()
        cf.write("child-after-gc\\n")

    # Run a subprocess and start/stop a child run to prove locks and hooks work cleanly.
    res = subprocess.run([sys.executable, "-c", "pass"], check=True)
    assert res.returncode == 0
    child_run = pubrun.start(
        output_dir={str(tmp_path / "child_runs")!r},
        capture={{"hardware": {{"depth": "off"}}}},
    )
    child_run.stop()
    sys.exit(0)

release_locks.set()
holder.join(timeout=5)
_, st = os.waitpid(pid, 0)
assert os.WIFEXITED(st) and os.WEXITSTATUS(st) == 0, f"child exited abnormally: {{st}}"

# Flush parent's print_buf.log before stopping so parent writes its line exactly once.
pf.flush()
pf.close()
run._print_log_file = None
run.stop()

stdout_text = (run.run_dir / "stdout.log").read_text(encoding="utf-8")
assert stdout_text.count("parent-stdout-unique-line") == 1, stdout_text

events_text = (run.run_dir / "events.jsonl").read_text(encoding="utf-8")
assert events_text.count("parent-event-unique") == 1, events_text

print_buf_text = (run.run_dir / "print_buf.log").read_text(encoding="utf-8")
assert print_buf_text.count("parent-print-unique-line") == 1, print_buf_text

child_text = open({str(child_file)!r}, encoding="utf-8").read()
assert child_text == "child-clean-line\\nchild-after-gc\\n", repr(child_text)
""",
        encoding="utf-8",
    )
    proc = subprocess.run(
        [sys.executable, str(script)],
        env=env,
        capture_output=True,
        text=True,
        timeout=45,
    )
    assert proc.returncode == 0, f"stdout={proc.stdout}\nstderr={proc.stderr}"


def test_subprocess_spy_windows_shlex_and_drain_reaping() -> None:
    """SubprocessSpy._safe_shlex_split preserves Windows backslashes and _drain reaps exited unwaited children."""
    from pubrun.capture.subprocesses import SubprocessSpy

    cmd = r"""C:\work\app.exe "C:\my dir\file.txt" 'D:\a\b'"""
    assert SubprocessSpy._safe_shlex_split(cmd, posix=False) == [
        r"C:\work\app.exe",
        r"C:\my dir\file.txt",
        r"D:\a\b",
    ]
    assert SubprocessSpy._safe_shlex_split('echo "hello world"', posix=True) == [
        "echo",
        "hello world",
    ]

    SubprocessSpy.uninstall()
    assert SubprocessSpy.install(owner="drain_test") is True
    try:
        # Launch a short-lived child and simulate an unwaited Popen resurrected in pending_running
        # whose returncode is still None until prev_poll(proc) reaps it.
        p = subprocess.Popen([sys.executable, "-c", "import sys; sys.exit(7)"])
        # Wait on OS side via os.waitpid? Better: wait briefly for exit without calling p.wait()/p.poll()
        # by polling the process state via /proc or letting the tiny child finish, then invoking _drain().
        state = SubprocessSpy._active_state
        assert state is not None
        state["pending_running"].append(p)
        deadline = time.monotonic() + 5.0
        while time.monotonic() < deadline:
            state["drain"]()
            if not state["pending_running"]:
                break
            time.sleep(0.02)
        assert len(state["pending_running"]) == 0
        recs = SubprocessSpy.get_records()
        assert len(recs) == 1
        assert recs[0]["exit_code"] == 7
        assert recs[0]["capture_state"]["status"] == "failed"
    finally:
        SubprocessSpy.uninstall(owner="drain_test")


def test_tqdm_safe_tee_writelines_flush_fast_path_and_cleanup_safety(tmp_path: Path) -> None:
    """TqdmSafeTee supports writelines, lock-free closed flush, fast-path/CR parity, and FD-safe migration/cleanup."""
    import threading

    # 1. writelines() captures all lines.
    orig = io.StringIO()
    log = io.StringIO()
    tee = TqdmSafeTee(orig, log, timestamped=False)
    tee.writelines(["alpha\n", "beta\n", "gamma"])
    tee.flush()
    assert orig.getvalue() == "alpha\nbeta\ngamma"
    assert log.getvalue() == "alpha\nbeta\ngamma\n"
    assert tee.line_count == 3

    # 2. flush() checks closed/None log_file BEFORE acquiring _lock.
    disarmed = TqdmSafeTee(io.StringIO(), None, timestamped=False)
    locked = threading.Event()
    release = threading.Event()

    def _hold() -> None:
        with disarmed._lock:
            locked.set()
            release.wait(timeout=5)

    t = threading.Thread(target=_hold, daemon=True)
    t.start()
    try:
        assert locked.wait(timeout=2)
        done = threading.Event()

        def _flush() -> None:
            disarmed.flush()
            done.set()

        tf = threading.Thread(target=_flush, daemon=True)
        tf.start()
        assert done.wait(timeout=2.0), "flush() blocked on _lock when log_file was None"
    finally:
        release.set()
        t.join(timeout=2)

    # 3. Fast path (no CR) and CRLF / split-CR / bare-CR parity.
    log2 = io.StringIO()
    tee2 = TqdmSafeTee(io.StringIO(), log2, timestamped=True)
    tee2.write("part1 ")
    tee2.write("part2\nline2\nline3")
    tee2.write("\r\n")
    tee2.write("progress 10%\rprogress 100%\r")
    tee2.write("\n")
    tee2.flush()
    out_lines = log2.getvalue().splitlines()
    assert len(out_lines) == 4
    assert out_lines[0].endswith("Z] part1 part2")
    assert out_lines[1].endswith("Z] line2")
    assert out_lines[2].endswith("Z] line3")
    assert out_lines[3].endswith("Z] progress 100%")
    assert tee2.line_count == 4

    # 4. suspend_for_migration closes handle even when flush() raises.
    class _FlushFailHandle:
        def __init__(self) -> None:
            self.closed = False

        def flush(self) -> None:
            raise OSError("flush failed")

        def close(self) -> None:
            self.closed = True

    interceptor = ConsoleInterceptor(tmp_path, mode="basic")
    fh_out = _FlushFailHandle()
    fh_err = _FlushFailHandle()
    interceptor.stdout_log = fh_out  # type: ignore[assignment]
    interceptor.stderr_log = fh_err  # type: ignore[assignment]
    interceptor.suspend_for_migration()
    assert fh_out.closed is True
    assert fh_err.closed is True
    assert interceptor.stdout_log is None
    assert interceptor.stderr_log is None

    # 5. _cleanup_resources under concurrent writers completes cleanly.
    cdir = tmp_path / "concurrent_console"
    cdir.mkdir()
    ci = ConsoleInterceptor(cdir, mode="basic")
    assert ci.start() is True
    wrote_first = threading.Event()
    stop_flag = threading.Event()
    errors: list = []

    def _writer() -> None:
        while not stop_flag.is_set():
            try:
                if ci.stdout_tee is not None:
                    ci.stdout_tee.write("concurrent line\n")
                    wrote_first.set()
            except Exception as exc:
                errors.append(exc)

    wt = threading.Thread(target=_writer, daemon=True)
    wt.start()
    try:
        assert wrote_first.wait(timeout=5.0)
        res = ci.stop()
        assert res["capture_state"]["status"] in ("complete", "partial")
    finally:
        stop_flag.set()
        wt.join(timeout=5)
    assert errors == []


def test_resource_watcher_bounds_linux_rparen_and_windows_ctypes_cache(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """ResourceWatcher validates numeric bounds, skips malformed /proc stat, and caches Windows ctypes/WinDLL."""
    import ctypes
    from types import SimpleNamespace
    import pubrun.capture.resources as resources_mod
    from pubrun.capture.resources import ResourceWatcher, set_poll_timeout

    class _FakeTracker:
        event_stream = None

    # 1. interval_seconds validation and clamping.
    for low in (0, -1, -5.5, 0.001):
        w = ResourceWatcher(_FakeTracker(), interval_seconds=low, system_metrics=False)
        assert w.interval == 0.05

    for invalid in (float("nan"), float("inf"), float("-inf"), True, False, "bad"):
        w = ResourceWatcher(_FakeTracker(), interval_seconds=invalid, system_metrics=False)  # type: ignore[arg-type]
        assert w.interval == 15.0

    # 2. max_failures validation.
    for bad_mf in (0, -3, True, False, "3"):
        w = ResourceWatcher(_FakeTracker(), interval_seconds=1.0, max_failures=bad_mf, system_metrics=False)  # type: ignore[arg-type]
        assert w.max_failures == 3

    # 3. set_poll_timeout validation.
    orig_timeout = resources_mod._poll_timeout
    try:
        for bad_t in (0, -2, float("nan"), float("inf"), True, "nope"):
            set_poll_timeout(bad_t)  # type: ignore[arg-type]
            assert resources_mod._poll_timeout == 3.0
        set_poll_timeout(7.5)
        assert resources_mod._poll_timeout == 7.5
    finally:
        resources_mod._poll_timeout = orig_timeout

    # 4. Linux _get_tree_cpu_jiffies_linux skips malformed /proc/<pid>/stat with rparen == -1.
    def _fake_open(path: str, *a, **kw):
        if str(path).endswith("/stat"):
            return io.StringIO("1234 broken_no_paren 1 2 3 4 5 6 7 8 9 10 999 888 777")
        raise OSError("not found")

    monkeypatch.setattr("builtins.open", _fake_open)
    monkeypatch.setattr(resources_mod, "_get_linux_child_pids", lambda pid: [])
    assert resources_mod._get_tree_cpu_jiffies_linux() == 0

    # 5. Windows _PROCESS_MEMORY_COUNTERS single-class reuse and cached private WinDLL.
    monkeypatch.setattr(resources_mod.sys, "platform", "win32")
    monkeypatch.setattr(resources_mod, "_WIN_RSS_API", None)
    # Remove any non-LibraryLoader ctypes.windll if present (on Windows it's a LibraryLoader).
    if hasattr(ctypes, "windll") and not isinstance(ctypes.windll, ctypes.LibraryLoader):
        monkeypatch.delattr(ctypes, "windll", raising=False)

    windll_calls = []
    seen_struct_types = []

    def _fake_get_current_process() -> int:
        return 42

    def _fake_k32_mem(handle: int, counters_ptr, size: int) -> int:
        seen_struct_types.append(type(counters_ptr._obj))
        counters_ptr._obj.WorkingSetSize = 123456
        return 1

    def _fake_windll(name: str, use_last_error: bool = False):
        windll_calls.append((name, use_last_error))
        return SimpleNamespace(
            GetCurrentProcess=_fake_get_current_process,
            K32GetProcessMemoryInfo=_fake_k32_mem,
        )

    monkeypatch.setattr(ctypes, "WinDLL", _fake_windll, raising=False)
    try:
        for _ in range(6):
            assert resources_mod._get_rss_windows() == 123456
        assert windll_calls == [("kernel32", True)]
        assert len(seen_struct_types) == 6
        assert all(t is resources_mod._PROCESS_MEMORY_COUNTERS for t in seen_struct_types)
    finally:
        resources_mod._WIN_RSS_API = None
