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
        """Calling install() twice does not raise."""
        cap = SignalExitCapture()
        cap.install()
        cap.install()  # no-op
        cap.uninstall()

    def test_double_uninstall_is_safe(self):
        """Calling uninstall() twice does not raise."""
        cap = SignalExitCapture()
        cap.install()
        cap.uninstall()
        cap.uninstall()  # no-op

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

            # Send signal
            os.kill(os.getpid(), signal.SIGUSR1)

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
            with pytest.raises(KeyboardInterrupt):
                os.kill(os.getpid(), signal.SIGINT)

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

            os.kill(os.getpid(), signal.SIGUSR1)
            os.kill(os.getpid(), signal.SIGUSR2)
            os.kill(os.getpid(), signal.SIGUSR1)

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

            # Should not raise, should be recorded
            os.kill(os.getpid(), signal.SIGUSR1)

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
        # Simulate receiving SIGINT (caught by user code so process survives)
        try:
            os.kill(os.getpid(), signal.SIGINT)
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
            # First SIGINT -- caught by user
            try:
                os.kill(os.getpid(), signal.SIGINT)
            except KeyboardInterrupt:
                pass

            # Handler should still be installed -- second signal should be recorded
            try:
                os.kill(os.getpid(), signal.SIGINT)
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

        with caplog.at_level(logging.WARNING, logger="pubrun"):
            cap.install()

        # No handlers should have been installed
        assert len(cap._previous_handlers) == 0
        # Warning should have been emitted
        assert any("signal capture unavailable" in r.message for r in caplog.records)
