"""Tests for pubrun.capture.signals -- signal and exit-code capture."""
import os
import signal
import sys
import threading
import time

import pytest

from pubrun.capture.signals import SignalExitCapture


class TestSignalExitCaptureBasic:
    """Basic lifecycle tests for SignalExitCapture."""

    def test_install_and_uninstall(self):
        """Install and uninstall without error."""
        cap = SignalExitCapture()
        cap.install()
        assert cap._installed is True
        cap.uninstall()
        assert cap._installed is False

    def test_double_install_is_safe(self):
        """Calling install() twice does not raise and restores original handlers on uninstall."""
        import pubrun.capture.signals as signals_mod

        orig_excepthook = sys.excepthook
        orig_handlers = {}
        for sig_name in signals_mod._TARGET_SIGNALS:
            sig = getattr(signal, sig_name, None)
            if sig is not None:
                orig_handlers[sig] = signal.getsignal(sig)

        cap = SignalExitCapture()
        cap.install()
        assert cap._installed is True
        cap.install()  # no-op
        assert cap._installed is True
        cap.uninstall()
        assert cap._installed is False
        assert sys.excepthook is orig_excepthook
        for sig, orig_handler in orig_handlers.items():
            assert signal.getsignal(sig) == orig_handler

    def test_double_uninstall_is_safe(self):
        """Calling uninstall() twice does not raise."""
        cap = SignalExitCapture()
        cap.install()
        assert cap._installed is True
        cap.uninstall()
        assert cap._installed is False
        cap.uninstall()  # no-op
        assert cap._installed is False

    def test_get_records_empty_initially(self):
        """Records are empty before any signals are received."""
        cap = SignalExitCapture()
        cap.install()
        records = cap.get_records()
        assert records["signals_received"] == []
        assert records["exit_code"] is None
        assert records["exit_exception"] is None
        assert records["capture_state"]["status"] == "complete"
        cap.uninstall()

    def test_record_exit_code(self):
        """Explicit exit code recording works."""
        cap = SignalExitCapture()
        cap.record_exit_code(42)
        assert cap.get_records()["exit_code"] == 42

    def test_record_exit_code_only_first(self):
        """First recorded exit code wins (idempotent)."""
        cap = SignalExitCapture()
        cap.record_exit_code(1)
        cap.record_exit_code(2)
        assert cap.get_records()["exit_code"] == 1


class TestSignalCapture:
    """Tests for actual signal recording."""

    def test_captures_sigusr1(self):
        """SIGUSR1 is recorded and user handler still fires."""
        if sys.platform == "win32":
            pytest.skip("SIGUSR1 not available on Windows")

        user_called = []

        def user_handler(sig, frame):
            user_called.append(sig)

        # Install user handler first
        old = signal.signal(signal.SIGUSR1, user_handler)
        try:
            cap = SignalExitCapture()
            cap.install()

            # Call handler directly
            handler = signal.getsignal(signal.SIGUSR1)
            assert callable(handler)
            handler(signal.SIGUSR1, None)

            # Verify recording
            records = cap.get_records()
            assert len(records["signals_received"]) == 1
            assert records["signals_received"][0]["signal"] == signal.SIGUSR1
            assert records["signals_received"][0]["signal_name"] == "SIGUSR1"
            assert isinstance(records["signals_received"][0]["timestamp_utc"], float)

            # Verify user handler was called (chaining works)
            assert len(user_called) == 1
            assert user_called[0] == signal.SIGUSR1

            cap.uninstall()
        finally:
            signal.signal(signal.SIGUSR1, old)

    def test_captures_sigint_as_keyboard_interrupt(self):
        """SIGINT raises KeyboardInterrupt after recording."""
        if sys.platform == "win32":
            pytest.skip("Signal behavior differs on Windows")

        cap = SignalExitCapture()
        cap.install()

        try:
            handler = signal.getsignal(signal.SIGINT)
            assert callable(handler)
            with pytest.raises(KeyboardInterrupt):
                handler(signal.SIGINT, None)

            records = cap.get_records()
            assert len(records["signals_received"]) == 1
            assert records["signals_received"][0]["signal_name"] == "SIGINT"
        finally:
            cap.uninstall()

    def test_multiple_signals_recorded(self):
        """Multiple signals are all captured in order."""
        if sys.platform == "win32":
            pytest.skip("SIGUSR1/SIGUSR2 not available on Windows")

        cap = SignalExitCapture()
        old1 = signal.signal(signal.SIGUSR1, signal.SIG_IGN)
        old2 = signal.signal(signal.SIGUSR2, signal.SIG_IGN)
        try:
            cap.install()

            handler_usr1 = signal.getsignal(signal.SIGUSR1)
            handler_usr2 = signal.getsignal(signal.SIGUSR2)
            assert callable(handler_usr1)
            assert callable(handler_usr2)

            handler_usr1(signal.SIGUSR1, None)
            handler_usr2(signal.SIGUSR2, None)
            handler_usr1(signal.SIGUSR1, None)

            records = cap.get_records()
            assert len(records["signals_received"]) == 3
            assert records["signals_received"][0]["signal_name"] == "SIGUSR1"
            assert records["signals_received"][1]["signal_name"] == "SIGUSR2"
            assert records["signals_received"][2]["signal_name"] == "SIGUSR1"

            cap.uninstall()
        finally:
            signal.signal(signal.SIGUSR1, old1)
            signal.signal(signal.SIGUSR2, old2)

    def test_restores_original_handlers(self):
        """Uninstall restores the handler that was in place before install."""
        if sys.platform == "win32":
            pytest.skip("SIGUSR1 not available on Windows")

        def my_handler(sig, frame):
            pass

        old = signal.signal(signal.SIGUSR1, my_handler)
        try:
            cap = SignalExitCapture()
            cap.install()

            # During install, our shim is active
            current = signal.getsignal(signal.SIGUSR1)
            assert current is not my_handler

            cap.uninstall()

            # After uninstall, original handler is back
            restored = signal.getsignal(signal.SIGUSR1)
            assert restored is my_handler
        finally:
            signal.signal(signal.SIGUSR1, old)

    def test_chains_to_sig_ign(self):
        """If previous handler was SIG_IGN, signal is silently ignored."""
        if sys.platform == "win32":
            pytest.skip("SIGUSR1 not available on Windows")

        old = signal.signal(signal.SIGUSR1, signal.SIG_IGN)
        try:
            cap = SignalExitCapture()
            cap.install()

            handler = signal.getsignal(signal.SIGUSR1)
            assert callable(handler)
            handler(signal.SIGUSR1, None)

            records = cap.get_records()
            assert len(records["signals_received"]) == 1

            cap.uninstall()
        finally:
            signal.signal(signal.SIGUSR1, old)


class TestExcepthookCapture:
    """Tests for sys.excepthook wrapping."""

    def test_excepthook_captures_system_exit_code(self):
        """SystemExit code is captured via excepthook."""
        cap = SignalExitCapture()
        cap.install()

        # Simulate excepthook being called with SystemExit
        try:
            raise SystemExit(42)
        except SystemExit as e:
            # Call the hook manually (normally Python calls it for unhandled exceptions)
            sys.excepthook(type(e), e, e.__traceback__)

        records = cap.get_records()
        assert records["exit_code"] == 42
        assert records["exit_exception"] == "SystemExit(42)"

        cap.uninstall()

    def test_excepthook_captures_generic_exception(self):
        """Unhandled exceptions record exit code 1."""
        cap = SignalExitCapture()
        cap.install()

        try:
            raise ValueError("test error")
        except ValueError as e:
            sys.excepthook(type(e), e, e.__traceback__)

        records = cap.get_records()
        assert records["exit_code"] == 1
        assert "ValueError: test error" in records["exit_exception"]

        cap.uninstall()

    def test_excepthook_restores_on_uninstall(self):
        """Original sys.excepthook is restored after uninstall."""
        original = sys.excepthook
        cap = SignalExitCapture()
        cap.install()
        assert sys.excepthook is not original
        cap.uninstall()
        assert sys.excepthook is original


class TestSignalOutcomeDetermination:
    """Tests that received signals affect the run outcome."""

    def test_sigint_sets_outcome_interrupted(self):
        """A run that received SIGINT is marked 'interrupted' not 'completed'."""
        if sys.platform == "win32":
            pytest.skip("SIGUSR1 not available on Windows")

        from pubrun.tracker import Run

        run = Run()
        # Simulate receiving SIGINT (directly invoke the handler)
        handler = signal.getsignal(signal.SIGINT)
        assert callable(handler)
        try:
            handler(signal.SIGINT, None)
        except KeyboardInterrupt:
            pass  # User caught it

        run.stop()

        # Outcome should be "interrupted", not "completed"
        assert run._outcome == "interrupted"

        # Manifest should reflect this
        import json
        with open(run.run_dir / "manifest.json") as f:
            manifest = json.load(f)
        assert manifest["status"]["outcome"] == "interrupted"

    def test_no_signal_stays_completed(self):
        """A run with no signals received stays 'completed'."""
        from pubrun.tracker import Run

        run = Run()
        run.stop()
        assert run._outcome == "completed"


class TestSignalCaptureConfig:
    """Tests that signal capture respects the config toggle."""

    def test_disabled_via_config(self):
        """When capture.signals.enabled is false, no signal capture in manifest."""
        from pubrun.tracker import Run
        run = Run(overrides={"capture": {"signals": {"enabled": False}}})
        assert run.signal_capture is None
        manifest = run.to_manifest_dict()
        assert manifest["signals"]["capture_state"]["status"] == "suppressed"
        run.stop()

    def test_enabled_via_config(self):
        """When capture.signals.enabled is true (default), signals are captured."""
        from pubrun.tracker import Run
        run = Run()
        assert run.signal_capture is not None
        manifest = run.to_manifest_dict()
        assert manifest["signals"]["capture_state"]["status"] == "complete"
        run.stop()


class TestSignalHandlerReinstallation:
    """Tests for handler re-installation after SIG_DFL chain."""

    def test_handler_reinstalled_after_sigint_caught(self):
        """After SIGINT raises KeyboardInterrupt (caught), handler is still active."""
        if sys.platform == "win32":
            pytest.skip("Signal behavior differs on Windows")

        cap = SignalExitCapture()
        cap.install()

        try:
            handler = signal.getsignal(signal.SIGINT)
            assert callable(handler)
            # First SIGINT -- caught by user
            try:
                handler(signal.SIGINT, None)
            except KeyboardInterrupt:
                pass

            # Handler should still be installed -- second signal should be recorded
            try:
                handler(signal.SIGINT, None)
            except KeyboardInterrupt:
                pass

            records = cap.get_records()
            assert len(records["signals_received"]) == 2
            assert records["signals_received"][0]["signal_name"] == "SIGINT"
            assert records["signals_received"][1]["signal_name"] == "SIGINT"
        finally:
            cap.uninstall()


class TestSignalNonMainThread:
    """Tests for non-main-thread signal registration warning."""

    def test_warns_on_non_main_thread(self, caplog, monkeypatch):
        """Installing from a non-main thread logs a warning when signal.signal raises."""
        import logging

        cap = SignalExitCapture()

        # Force signal.signal to always raise ValueError (simulating non-main thread)
        def mock_signal_signal(signum, handler):
            raise ValueError("signal only works in main thread of the main interpreter")

        monkeypatch.setattr(signal, "signal", mock_signal_signal)

        try:
            with caplog.at_level(logging.WARNING, logger="pubrun"):
                cap.install()

            # No handlers should have been installed
            assert len(cap._previous_handlers) == 0
            # Warning should have been emitted
            assert any("signal capture unavailable" in r.message for r in caplog.records)
        finally:
            cap.uninstall()


class TestFinalizeActiveRun:
    """P3-R2: Regression test -- _finalize_active_run() must call write_artifacts."""

    def test_finalize_active_run_calls_write_artifacts(self, tmp_path, monkeypatch):
        """_finalize_active_run() calls writer.write_artifacts() on the active run."""
        from pubrun.capture.signals import _finalize_active_run
        from pubrun.tracker import Run

        monkeypatch.setattr("pathlib.Path.cwd", lambda: tmp_path)
        run = Run()

        # Track whether write_artifacts was called
        called = []
        original_write = run.writer.write_artifacts
        run.writer.write_artifacts = lambda: called.append(True) or original_write()

        _finalize_active_run()
        assert len(called) == 1
        run.stop()

    def test_finalize_active_run_no_crash_without_active_run(self, monkeypatch):
        """_finalize_active_run() does not crash when no run is active."""
        import pubrun.capture.signals as signals_mod
        import pubrun.tracker
        monkeypatch.setattr(pubrun.tracker, "_active_run", None)
        # Must not raise
        signals_mod._finalize_active_run()
        assert signals_mod._finalizing_active_run is False
        assert signals_mod._timed_out_locks == set()


class TestMacosHardwareSpying:
    """P3-T8: Verify macOS hardware subprocess calls are wrapped in disable_spy."""

    def test_macos_hardware_calls_wrapped_in_disable_spy(self, monkeypatch):
        from pubrun.capture.subprocesses import _spy_bypassed
        import pubrun.capture.hardware as hardware
        import subprocess

        monkeypatch.setattr(hardware, "sys", type("sys_mock", (), {"platform": "darwin"})())

        checked_bypass = []

        def mock_check_output(*args, **kwargs):
            # disable_spy now maintains a per-thread ref-count; check the
            # representation-independent helper rather than the raw field.
            checked_bypass.append(_spy_bypassed())
            return "Apple M3" if "sysctl" in args[0][0] else "SPDisplaysDataType output"

        monkeypatch.setattr(subprocess, "check_output", mock_check_output)

        cpu_model = hardware._get_cpu_model()
        assert cpu_model == "Apple M3"
        assert len(checked_bypass) == 1
        assert checked_bypass[0] is True


class TestLethalSignalFinalization:
    """P3-T5: Verify lethal signals (SIGTERM/SIGHUP) trigger run finalization."""

    @pytest.mark.skipif(sys.platform == "win32", reason="SIGTERM is Unix-specific")
    def test_lethal_signal_finalization_sigterm(self, tmp_path):
        import subprocess
        import sys
        from pathlib import Path
        import json
        import signal

        script = f"""
import time, sys
from pathlib import Path
import pubrun

# Start pubrun
run = pubrun.start(events={{"enabled": True}})
print(run.run_dir, flush=True)

try:
    time.sleep(10)
except KeyboardInterrupt:
    pass
"""
        proc = subprocess.Popen(
            [sys.executable, "-c", script],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=tmp_path,
        )
        try:
            assert proc.stdout is not None
            run_dir_str = proc.stdout.readline().strip()
            assert run_dir_str, "Subprocess failed to print run directory"
            run_dir = Path(run_dir_str)

            proc.send_signal(signal.SIGTERM)

            # Wait for exit
            proc.wait(timeout=15)
        finally:
            if proc.poll() is None:
                proc.kill()
                proc.wait()

        manifest_path = run_dir / "manifest.json"
        assert manifest_path.exists(), "manifest.json was not created on SIGTERM!"

        with open(manifest_path, "r") as f:
            manifest = json.load(f)

        assert manifest["status"]["outcome"] == "interrupted", "Outcome should be interrupted"
        assert len(manifest["signals"]["signals_received"]) >= 1
        assert manifest["signals"]["signals_received"][0]["signal_name"] == "SIGTERM"


class TestGetRecordsDoesNotBlock:
    """get_records() must not wait on the capture lock.

    A background manifest refresh calls get_records() while holding
    pubrun.core._run_lock. If the main thread holds the capture lock and a
    lethal signal makes it finalize (which needs _run_lock), a blocking
    get_records() deadlocks the process.
    """

    def test_get_records_from_other_thread_while_lock_held(self):
        cap = SignalExitCapture()
        cap.record_exit_code(3)
        result = {}

        def reader():
            result["records"] = cap.get_records()

        with cap._lock:
            t = threading.Thread(target=reader, daemon=True)
            t.start()
            t.join(timeout=5)
            assert not t.is_alive(), "get_records() blocked on the held capture lock"
        assert result["records"]["exit_code"] == 3
        assert result["records"]["capture_state"]["status"] == "complete"


class TestFinalizationLock:
    """Unit tests for the bounded ``finalization_lock`` helper."""

    def test_blocks_normally_outside_signal_finalization(self):
        """Outside signal finalization, the helper blocks until the lock is released."""
        import pubrun.capture.signals as signals_mod

        lock = threading.Lock()
        locked = threading.Event()

        def holder():
            with lock:
                locked.set()
                time.sleep(0.3)

        orig_latch = signals_mod._finalizing_active_run
        t = threading.Thread(target=holder, daemon=True)
        try:
            signals_mod._finalizing_active_run = False
            signals_mod._timed_out_locks.clear()
            t.start()
            assert locked.wait(timeout=5)
            with signals_mod.finalization_lock(lock, 0.05) as acquired:
                assert acquired is True
        finally:
            t.join(timeout=5)
            signals_mod._timed_out_locks.clear()
            signals_mod._finalizing_active_run = orig_latch

    def test_gives_up_within_bound_during_signal_finalization(self):
        """During signal finalization, a busy lock yields False within timeout + 1.0 s."""
        import pubrun.capture.signals as signals_mod

        lock = threading.Lock()
        locked = threading.Event()
        release = threading.Event()

        def holder():
            with lock:
                locked.set()
                release.wait(timeout=5)

        orig_latch = signals_mod._finalizing_active_run
        timeout = 0.15
        t = threading.Thread(target=holder, daemon=True)
        try:
            signals_mod._finalizing_active_run = True
            signals_mod._timed_out_locks.clear()
            t.start()
            assert locked.wait(timeout=5)
            start = time.monotonic()
            with signals_mod.finalization_lock(lock, timeout) as acquired:
                elapsed = time.monotonic() - start
                assert acquired is False
            assert elapsed < timeout + 1.0
        finally:
            release.set()
            t.join(timeout=5)
            signals_mod._timed_out_locks.clear()
            signals_mod._finalizing_active_run = orig_latch

    def test_skips_wait_for_lock_that_already_timed_out(self):
        """A lock that already timed out during this finalization is not waited on again."""
        import pubrun.capture.signals as signals_mod

        lock = threading.Lock()
        locked = threading.Event()
        release = threading.Event()

        def holder():
            with lock:
                locked.set()
                release.wait(timeout=5)

        orig_latch = signals_mod._finalizing_active_run
        t = threading.Thread(target=holder, daemon=True)
        try:
            signals_mod._finalizing_active_run = True
            signals_mod._timed_out_locks.clear()
            t.start()
            assert locked.wait(timeout=5)
            with signals_mod.finalization_lock(lock, 0.1) as first_acquired:
                assert first_acquired is False
            start = time.monotonic()
            with signals_mod.finalization_lock(lock, 2.0) as second_acquired:
                elapsed = time.monotonic() - start
                assert second_acquired is False
            assert elapsed < 0.1
        finally:
            release.set()
            t.join(timeout=5)
            signals_mod._timed_out_locks.clear()
            signals_mod._finalizing_active_run = orig_latch

    def test_finalize_active_run_clears_timed_out_locks(self, monkeypatch):
        """_finalize_active_run resets both _timed_out_locks and _finalizing_active_run."""
        import pubrun.capture.signals as signals_mod
        import pubrun.tracker as tracker_mod

        lock = threading.Lock()
        locked = threading.Event()
        release = threading.Event()

        def holder():
            with lock:
                locked.set()
                release.wait(timeout=5)

        class _DummyWriter:
            def write_artifacts(self):
                with signals_mod.finalization_lock(lock, 0.05) as acquired:
                    assert acquired is False
                    assert id(lock) in signals_mod._timed_out_locks

        class _DummyRun:
            writer = _DummyWriter()

        monkeypatch.setattr(tracker_mod, "_active_run", _DummyRun())
        t = threading.Thread(target=holder, daemon=True)
        try:
            t.start()
            assert locked.wait(timeout=5)
            signals_mod._finalize_active_run()
            assert len(signals_mod._timed_out_locks) == 0
            assert signals_mod._finalizing_active_run is False
            assert signals_mod.in_signal_finalization() is False
        finally:
            release.set()
            t.join(timeout=5)
            signals_mod._timed_out_locks.clear()


@pytest.mark.skipif(sys.platform == "win32", reason="SIGTERM is Unix-specific")
class TestLethalSignalWhileLockHeld:
    """Real-SIGTERM regression tests for every finalization-path lock."""

    @pytest.mark.parametrize(
        "case",
        [
            "errors_lock",
            "data_files_lock",
            "file_io_budget_lock",
            "event_stream_lock",
            "subprocess_spy_lock",
            "resource_watcher_lock",
            "write_lock_vs_hw_refresh",
            "errors_lock_vs_hw_refresh",
        ],
    )
    def test_sigterm_finalizes_while_lock_held(self, tmp_path, case):
        """A child holding a pubrun lock exits promptly on SIGTERM and writes manifest.json."""
        import json
        import subprocess
        from pathlib import Path

        script_path = tmp_path / f"sigterm_{case}.py"
        script_path.write_text(
            f"""
import sys
import threading
import time
import pubrun
import pubrun.core
from pubrun.capture.file_io import get_or_create_budget_tracker
from pubrun.capture.subprocesses import SubprocessSpy

case = {case!r}
run = pubrun.start(events={{"enabled": True}})
if run._hardware_future_done is not None:
    run._hardware_future_done.wait(5)
if run._hardware_thread is not None:
    run._hardware_thread.join(5)
print(run.run_dir, flush=True)

if case == "errors_lock":
    lock = run._errors_lock
elif case == "data_files_lock":
    lock = run._data_files_lock
elif case == "file_io_budget_lock":
    lock = get_or_create_budget_tracker(run)._lock
elif case == "event_stream_lock":
    assert run.event_stream is not None
    lock = run.event_stream._lock
elif case == "subprocess_spy_lock":
    assert run._spying_subprocesses
    lock = SubprocessSpy._lock
elif case == "resource_watcher_lock":
    assert run.resource_watcher is not None
    lock = run.resource_watcher._lock
elif case == "write_lock_vs_hw_refresh":
    lock = run.writer._write_lock
elif case == "errors_lock_vs_hw_refresh":
    lock = run._errors_lock
else:
    raise AssertionError(f"Unknown case: {{case}}")

with lock:
    if case == "write_lock_vs_hw_refresh":
        run.writer._startup_included_hardware = False
        ready = threading.Event()
        entering = threading.Event()
        _orig_write_startup = run.writer.write_startup_manifest
        def _wrapped_write_startup(*args, **kwargs):
            entering.set()
            return _orig_write_startup(*args, **kwargs)
        run.writer.write_startup_manifest = _wrapped_write_startup
        def _bg():
            with pubrun.core._run_lock:
                ready.set()
                run.writer.write_startup_manifest(is_refresh=True)
        t = threading.Thread(target=_bg, daemon=True)
        t.start()
        assert ready.wait(5)
        assert entering.wait(5)
    elif case == "errors_lock_vs_hw_refresh":
        ready = threading.Event()
        entering = threading.Event()
        _orig_check_failed = run._check_section_failed
        def _wrapped_check_failed(*args, **kwargs):
            entering.set()
            return _orig_check_failed(*args, **kwargs)
        run._check_section_failed = _wrapped_check_failed
        def _bg():
            with pubrun.core._run_lock:
                ready.set()
                run._check_section_failed(
                    "hardware", {{"capture_state": {{"status": "failed"}}}}
                )
        t = threading.Thread(target=_bg, daemon=True)
        t.start()
        assert ready.wait(5)
        assert entering.wait(5)

    print("held", flush=True)
    time.sleep(60)
""",
            encoding="utf-8",
        )

        proc = subprocess.Popen(
            [sys.executable, str(script_path)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=tmp_path,
        )
        try:
            assert proc.stdout is not None
            run_dir_line = proc.stdout.readline().strip()
            held_line = proc.stdout.readline().strip()
            if not run_dir_line or held_line != "held":
                proc.kill()
                _, stderr = proc.communicate(timeout=5)
                pytest.fail(
                    f"Child failed handshake for {case}: "
                    f"run_dir={run_dir_line!r}, held={held_line!r}, stderr={stderr!r}"
                )

            proc.send_signal(signal.SIGTERM)
            try:
                proc.wait(timeout=30)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait(timeout=5)
                pytest.fail(f"process hung after SIGTERM while holding {case}")

            assert proc.returncode == -signal.SIGTERM
            manifest_path = Path(run_dir_line) / "manifest.json"
            assert manifest_path.exists(), f"manifest.json missing for {case}"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            assert manifest["status"]["outcome"] == "interrupted"
            sig_names = [
                entry.get("signal_name")
                for entry in manifest["signals"]["signals_received"]
            ]
            assert "SIGTERM" in sig_names
        finally:
            if proc.poll() is None:
                proc.kill()
                proc.wait(timeout=5)


class TestSignalHardeningAndRecovery:
    """IPD 76z7ww tests for __slots__ finalization_lock, SIGUSR1/2, raise_signal, signal cap, and caught sys.exit."""

    def test_finalization_lock_uses_slots_and_releases_on_exception(self):
        """finalization_lock is a lightweight __slots__ class with no __dict__ and releases on exception."""
        from pubrun.capture.signals import finalization_lock

        lock = threading.Lock()
        ctx = finalization_lock(lock, 0.1)
        assert not hasattr(ctx, "__dict__")

        with pytest.raises(RuntimeError, match="boom"):
            with finalization_lock(lock, 0.1) as acquired:
                assert acquired is True
                raise RuntimeError("boom")

        assert lock.acquire(blocking=False) is True
        lock.release()

    @pytest.mark.skipif(sys.platform == "win32", reason="SIGUSR1 is Unix-specific")
    def test_sigusr1_sig_dfl_finalizes_as_interrupted_while_user_handler_completes(self, tmp_path):
        """SIGUSR1 with SIG_DFL finalizes as interrupted; user-handled SIGUSR1 finishes completed."""
        import json
        import subprocess
        from pathlib import Path

        src_dir = str(Path(__file__).resolve().parent.parent / "src")
        env = dict(os.environ)
        env["PYTHONPATH"] = src_dir + os.pathsep + env.get("PYTHONPATH", "")

        # 1. Default SIG_DFL SIGUSR1 kills process and finalizes as "interrupted".
        dfl_script = tmp_path / "sigusr1_dfl.py"
        dfl_script.write_text(
            f"""
import signal, time
import pubrun.noauto as pubrun
signal.signal(signal.SIGUSR1, signal.SIG_DFL)
run = pubrun.start(output_dir={str(tmp_path / "dfl_runs")!r}, capture={{"hardware": {{"depth": "off"}}}})
print(run.run_dir, flush=True)
time.sleep(30)
""",
            encoding="utf-8",
        )
        proc = subprocess.Popen(
            [sys.executable, str(dfl_script)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=env,
        )
        try:
            assert proc.stdout is not None
            run_dir = Path(proc.stdout.readline().strip())
            proc.send_signal(signal.SIGUSR1)
            proc.wait(timeout=15)
        finally:
            if proc.poll() is None:
                proc.kill()
                proc.wait(timeout=5)

        assert proc.returncode == -signal.SIGUSR1
        manifest = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
        assert manifest["status"]["outcome"] == "interrupted"
        assert any(s["signal_name"] == "SIGUSR1" for s in manifest["signals"]["signals_received"])

        # 2. User-handled SIGUSR1 stays "completed".
        handled_script = tmp_path / "sigusr1_handled.py"
        handled_script.write_text(
            f"""
import os, signal
import pubrun.noauto as pubrun

handled = []
signal.signal(signal.SIGUSR1, lambda s, f: handled.append(s))
run = pubrun.start(output_dir={str(tmp_path / "handled_runs")!r}, capture={{"hardware": {{"depth": "off"}}}})
os.kill(os.getpid(), signal.SIGUSR1)
assert handled == [signal.SIGUSR1]
print(run.run_dir, flush=True)
run.stop()
""",
            encoding="utf-8",
        )
        res = subprocess.run(
            [sys.executable, str(handled_script)],
            env=env,
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert res.returncode == 0, res.stderr
        h_run_dir = Path(res.stdout.strip())
        h_manifest = json.loads((h_run_dir / "manifest.json").read_text(encoding="utf-8"))
        assert h_manifest["status"]["outcome"] == "completed"
        assert any(s["signal_name"] == "SIGUSR1" for s in h_manifest["signals"]["signals_received"])

    @pytest.mark.skipif(sys.platform == "win32", reason="SIGUSR2 is Unix-specific")
    def test_sig_dfl_reraise_uses_signal_raise_signal(self, monkeypatch):
        """Both active and passive-passthrough SIG_DFL paths re-raise via signal.raise_signal."""
        raised = []
        os_kill_called = []

        monkeypatch.setattr(signal, "raise_signal", lambda s: raised.append(s))
        monkeypatch.setattr(os, "kill", lambda p, s: os_kill_called.append((p, s)))
        monkeypatch.setattr("pubrun.capture.signals._finalize_active_run", lambda: None)

        old = signal.signal(signal.SIGUSR2, signal.SIG_DFL)
        cap = SignalExitCapture()
        try:
            cap.install()
            shim = signal.getsignal(signal.SIGUSR2)
            assert callable(shim)
            # Active SIG_DFL path
            shim(signal.SIGUSR2, None)
            assert raised == [signal.SIGUSR2]
            assert cap.fatal_signal_name() == "SIGUSR2"
            assert os_kill_called == []

            # Passive passthrough after uninstall
            cap.uninstall()
            shim(signal.SIGUSR2, None)
            assert raised == [signal.SIGUSR2, signal.SIGUSR2]
            assert os_kill_called == []
        finally:
            cap.uninstall()
            signal.signal(signal.SIGUSR2, old)

    @pytest.mark.skipif(sys.platform == "win32", reason="SIGUSR1 is Unix-specific")
    def test_signals_received_cap_and_schema_validation(self, tmp_path):
        """_signals_received caps at MAX_SIGNALS_RECORDED (1000) and signals_truncated validates against manifest schema."""
        import json
        from pathlib import Path
        from pubrun.capture.signals import MAX_SIGNALS_RECORDED
        from pubrun.tracker import Run

        old = signal.signal(signal.SIGUSR1, signal.SIG_IGN)
        run = Run(overrides={"output_dir": str(tmp_path), "capture": {"hardware": {"depth": "off"}}})
        try:
            assert run.signal_capture is not None
            # When not truncated, signals_truncated must be omitted.
            assert "signals_truncated" not in run.signal_capture.get_records()

            shim = signal.getsignal(signal.SIGUSR1)
            assert callable(shim)
            for _ in range(MAX_SIGNALS_RECORDED + 5):
                shim(signal.SIGUSR1, None)

            recs = run.signal_capture.get_records()
            assert len(recs["signals_received"]) == MAX_SIGNALS_RECORDED
            assert recs["signals_truncated"] == 5
            assert recs["capture_state"] == {
                "status": "partial",
                "detail": "5 additional signal(s) omitted",
            }
            run.stop()

            manifest = json.loads((run.run_dir / "manifest.json").read_text(encoding="utf-8"))
            assert manifest["signals"]["signals_truncated"] == 5
            assert len(manifest["signals"]["signals_received"]) == MAX_SIGNALS_RECORDED

            schema_path = Path(__file__).resolve().parent.parent / "schemas" / "manifest.schema.json"
            schema = json.loads(schema_path.read_text(encoding="utf-8"))
            jsonschema = pytest.importorskip("jsonschema")
            jsonschema.validate(instance=manifest, schema=schema)
        finally:
            if run.is_active:
                run.stop()
            signal.signal(signal.SIGUSR1, old)

    def test_caught_sys_exit_recovers_while_uncaught_stays_failed(self, tmp_path):
        """Caught sys.exit(5) followed by stop() or annotate()+atexit completes cleanly; uncaught stays failed."""
        import json
        import subprocess
        from pathlib import Path
        import pubrun

        # 1. Caught sys.exit(5) followed by explicit pubrun.stop()
        run = pubrun.start(
            output_dir=str(tmp_path / "stop_recovery"),
            capture={"hardware": {"depth": "off"}},
        )
        try:
            with pytest.raises(SystemExit) as exc_info:
                sys.exit(5)
            assert exc_info.value.code == 5
        finally:
            pubrun.stop()

        m1 = json.loads((run.run_dir / "manifest.json").read_text(encoding="utf-8"))
        assert m1["status"]["outcome"] == "completed"
        assert m1["signals"]["exit_code"] == 0

        # 2. Subprocess: caught sys.exit(5) + pubrun.annotate() + normal atexit exit -> completed
        src_dir = str(Path(__file__).resolve().parent.parent / "src")
        env = dict(os.environ)
        env["PYTHONPATH"] = src_dir + os.pathsep + env.get("PYTHONPATH", "")

        recover_script = tmp_path / "caught_exit_annotate.py"
        recover_script.write_text(
            f"""
import sys
import pubrun.noauto as pubrun

run = pubrun.start(
    output_dir={str(tmp_path / "atexit_recovery")!r},
    events={{"enabled": True}},
    capture={{"hardware": {{"depth": "off"}}}},
)
print(run.run_dir, flush=True)
try:
    sys.exit(5)
except SystemExit:
    pass
pubrun.annotate("recovered after caught sys.exit")
""",
            encoding="utf-8",
        )
        res = subprocess.run(
            [sys.executable, str(recover_script)],
            env=env,
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert res.returncode == 0, res.stderr
        m2 = json.loads((Path(res.stdout.strip()) / "manifest.json").read_text(encoding="utf-8"))
        assert m2["status"]["outcome"] == "completed"
        assert m2["signals"]["exit_code"] == 0

        # 3. Subprocess: uncaught sys.exit(5) via atexit -> failed with exit_code == 5
        uncaught_script = tmp_path / "uncaught_exit.py"
        uncaught_script.write_text(
            f"""
import sys
import pubrun.noauto as pubrun

run = pubrun.start(
    output_dir={str(tmp_path / "uncaught_exit")!r},
    capture={{"hardware": {{"depth": "off"}}}},
)
print(run.run_dir, flush=True)
sys.exit(5)
""",
            encoding="utf-8",
        )
        res3 = subprocess.run(
            [sys.executable, str(uncaught_script)],
            env=env,
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert res3.returncode == 5
        m3 = json.loads((Path(res3.stdout.strip()) / "manifest.json").read_text(encoding="utf-8"))
        assert m3["status"]["outcome"] == "failed"
        assert m3["signals"]["exit_code"] == 5
