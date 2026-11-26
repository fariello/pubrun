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
