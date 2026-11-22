"""Behavioral tests for safe diagnostic redaction and hook ownership rollback (IPD p6pon8)."""
import faulthandler
import io
import logging
import os
import signal
import subprocess
import sys
import threading
import time
from pathlib import Path

import pytest

from pubrun.capture import redaction as redaction_mod
from pubrun.capture.console import ConsoleInterceptor, TqdmSafeTee
from pubrun.capture.invocation import get_invocation
from pubrun.capture.redaction import format_safe_error_detail
from pubrun.capture.resources import ResourceWatcher
from pubrun.capture.signals import SignalExitCapture
from pubrun.capture.subprocesses import SubprocessSpy


# ==========================================================================
# Safe diagnostic error formatting and invocation fallback
# ==========================================================================


class TestFormatSafeErrorDetail:
    """Behavioral tests for format_safe_error_detail()."""

    @pytest.mark.parametrize(
        "raw_msg,secret",
        [
            ("failed with --api-key=supersecret_123 --epochs 5", "supersecret_123"),
            ("failed with --api-key='quoted secret val' ok", "quoted secret val"),
            ("failed with --token tok_value_999 --verbose", "tok_value_999"),
            ("auth rejected password: my_db_password_42", "my_db_password_42"),
            ("db url https://alice:hunter2@db.example.com/prod", "hunter2"),
            ("header Authorization: Bearer eyJhbGciOiJIUzI1NiJ9", "eyJhbGciOiJIUzI1NiJ9"),
            ("invalid key sk-proj-abc123_def456-7890xyz", "sk-proj-abc123_def456-7890xyz"),
            ("env secret_key=very_hidden_val done", "very_hidden_val"),
        ],
    )
    def test_redacts_secrets(self, raw_msg, secret):
        detail = format_safe_error_detail(RuntimeError(raw_msg))
        assert detail.startswith("RuntimeError: ")
        assert secret not in detail
        assert "[REDACTED]" in detail

    def test_empty_message_returns_exc_type(self):
        assert format_safe_error_detail(ValueError("")) == "ValueError"
        assert format_safe_error_detail(ValueError("   \r\n  ")) == "ValueError"

    def test_multiline_message_collapsed_to_single_line(self):
        detail = format_safe_error_detail(OSError("line one\nline two\r\nline three"))
        assert "\n" not in detail
        assert "\r" not in detail
        assert detail == "OSError: line one line two line three"

    def test_long_message_bounded_to_max_len(self):
        long_msg = "x" * 500
        detail = format_safe_error_detail(RuntimeError(long_msg))
        assert len(detail) == 240
        assert detail.endswith("...")
        assert detail.startswith("RuntimeError: ")

    def test_small_max_len_handling(self):
        exc = ValueError("some message")
        assert format_safe_error_detail(exc, max_len=10) == "ValueEr..."
        assert format_safe_error_detail(exc, max_len=3) == "Val"
        assert format_safe_error_detail(exc, max_len=2) == "Va"
        assert format_safe_error_detail(exc, max_len=0) == ""

    def test_invalid_custom_regex_falls_back_to_default_redaction(self):
        bad_cfg = {"redaction": {"sensitive_keys_regex": "[unclosed_regex"}}
        fake_secret = "dummy" + "value"
        exc = RuntimeError(f"failed with --api-key={fake_secret}")
        detail = format_safe_error_detail(exc, config=bad_cfg)
        assert detail.startswith("RuntimeError: ")
        assert fake_secret not in detail
        assert "[REDACTED]" in detail

    def test_broken_redaction_falls_back_to_exc_type_only(self, monkeypatch):
        def boom(*args, **kwargs):
            raise RuntimeError("redactor exploded")

        monkeypatch.setattr(redaction_mod, "_redact_value_string_heuristics", boom)
        exc = ValueError("raw secret password=never_leak_this")
        detail = format_safe_error_detail(exc)
        assert detail == "ValueError"
        assert "never_leak_this" not in detail


class TestInvocationFallbackRedaction:
    """Verify get_invocation() fallback redacts argv and error detail."""

    def test_fallback_redacts_argv_and_detail(self, monkeypatch):
        monkeypatch.setattr(
            sys, "argv", ["train.py", "--api-key=secret_arg_val", "--epochs", "10"]
        )

        def fail_cwd():
            raise PermissionError("denied at https://user:secret_pw@host/path")

        monkeypatch.setattr(Path, "cwd", staticmethod(fail_cwd))
        res = get_invocation()
        assert res["capture_state"]["status"] == "failed"
        assert "secret_pw" not in res["capture_state"]["detail"]
        assert "[REDACTED]" in res["capture_state"]["detail"]
        assert "secret_arg_val" not in " ".join(res["argv"])
        assert "--api-key=[REDACTED]" in res["argv"]

    def test_fallback_returns_empty_argv_if_redaction_fails(self, monkeypatch):
        monkeypatch.setattr(sys, "argv", ["train.py", "--token=supersecret"])
        monkeypatch.setattr(
            Path, "cwd", staticmethod(lambda: (_ for _ in ()).throw(OSError("cwd failed")))
        )
        monkeypatch.setattr(
            redaction_mod,
            "redact_argv",
            lambda *a, **k: (_ for _ in ()).throw(RuntimeError("redact broken")),
        )
        res = get_invocation()
        assert res["capture_state"]["status"] == "failed"
        assert res["argv"] == []


# ==========================================================================
# SubprocessSpy transactional install, chaining, ownership, and races
# ==========================================================================


class TestSubprocessSpyOwnershipRollback:
    """Behavioral tests for SubprocessSpy ownership, chaining, and rollback."""

    def setup_method(self):
        SubprocessSpy.uninstall()

    def teardown_method(self):
        SubprocessSpy.uninstall()

    def test_preexisting_third_party_wrappers_chained_and_restored(self):
        orig_init = subprocess.Popen.__init__
        orig_wait = subprocess.Popen.wait
        orig_system = os.system

        events = []

        def pre_init(self, args, *a, **kw):
            events.append(("pre_init", args))
            return orig_init(self, args, *a, **kw)

        def pre_wait(self, *a, **kw):
            events.append("pre_wait")
            return orig_wait(self, *a, **kw)

        def pre_system(cmd):
            events.append(("pre_system", cmd))
            return 0

        subprocess.Popen.__init__ = pre_init
        subprocess.Popen.wait = pre_wait
        os.system = pre_system
        try:
            assert SubprocessSpy.install(owner="run1") is True
            assert subprocess.Popen.__init__ is not pre_init
            assert subprocess.Popen.wait is not pre_wait
            assert os.system is not pre_system

            p = subprocess.Popen([sys.executable, "-c", "pass"])
            rc = p.wait()
            assert rc == 0
            assert os.system("echo hello") == 0

            assert any(e[0] == "pre_init" for e in events if isinstance(e, tuple))
            assert "pre_wait" in events
            assert ("pre_system", "echo hello") in events
            assert len(SubprocessSpy.get_records()) == 2

            SubprocessSpy.uninstall(owner="run1")
            assert subprocess.Popen.__init__ is pre_init
            assert subprocess.Popen.wait is pre_wait
            assert os.system is pre_system
        finally:
            SubprocessSpy.uninstall()
            subprocess.Popen.__init__ = orig_init
            subprocess.Popen.wait = orig_wait
            os.system = orig_system

    def test_post_install_third_party_wrappers_survive_uninstall_and_passthrough(self):
        orig_init = subprocess.Popen.__init__
        orig_wait = subprocess.Popen.wait
        orig_system = os.system

        try:
            assert SubprocessSpy.install(owner="run1") is True
            pubrun_init = subprocess.Popen.__init__
            pubrun_wait = subprocess.Popen.wait
            pubrun_system = os.system

            third_party_calls = []

            def tp_init(self, args, *a, **kw):
                third_party_calls.append("tp_init")
                return pubrun_init(self, args, *a, **kw)

            def tp_wait(self, *a, **kw):
                third_party_calls.append("tp_wait")
                return pubrun_wait(self, *a, **kw)

            def tp_system(cmd):
                third_party_calls.append(("tp_system", cmd))
                return pubrun_system(cmd)

            subprocess.Popen.__init__ = tp_init
            subprocess.Popen.wait = tp_wait
            os.system = tp_system

            SubprocessSpy.uninstall(owner="run1")

            # Post-install third-party wrappers must remain intact.
            assert subprocess.Popen.__init__ is tp_init
            assert subprocess.Popen.wait is tp_wait
            assert os.system is tp_system

            # Calling through the third-party wrappers into the deactivated pubrun
            # wrappers must pass through cleanly without recording.
            p = subprocess.Popen([sys.executable, "-c", "pass"])
            assert p.wait() == 0
            assert "tp_init" in third_party_calls
            assert "tp_wait" in third_party_calls
            assert SubprocessSpy.get_records() == []
        finally:
            SubprocessSpy.uninstall()
            subprocess.Popen.__init__ = orig_init
            subprocess.Popen.wait = orig_wait
            os.system = orig_system

    def test_old_popen_wait_does_not_corrupt_new_run_records(self):
        SubprocessSpy.install(owner="run1")
        p1 = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(0.05)"])
        SubprocessSpy.uninstall(owner="run1")

        SubprocessSpy.install(owner="run2")
        p2 = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(0.2)"])
        try:
            # Waiting on p1 (from run1) must not touch run2's record at index 0.
            assert p1.wait() == 0
            run2_recs = SubprocessSpy.get_records()
            assert len(run2_recs) == 1
            assert run2_recs[0]["exit_code"] is None
            assert run2_recs[0]["capture_state"]["status"] == "partial"

            assert p2.wait() == 0
            assert run2_recs[0]["exit_code"] == 0
            assert run2_recs[0]["capture_state"]["status"] == "complete"
        finally:
            p2.wait()
            SubprocessSpy.uninstall(owner="run2")

    def test_concurrent_uninstall_during_os_system_does_not_raise_index_error(self):
        orig_system = os.system

        def uninstalling_system(cmd):
            # Simulate another thread uninstalling SubprocessSpy mid-call.
            SubprocessSpy.uninstall(owner="run1")
            return 0

        os.system = uninstalling_system
        try:
            SubprocessSpy.install(owner="run1")
            rc = os.system("echo concurrent")
            assert rc == 0
            assert SubprocessSpy._installed is False
        finally:
            SubprocessSpy.uninstall()
            os.system = orig_system

    def test_failed_popen_and_os_system_redact_secrets(self):
        orig_init = subprocess.Popen.__init__
        orig_system = os.system

        def failing_init(self, args, *a, **kw):
            raise FileNotFoundError("no binary --api-key=secret_popen_val")

        def failing_system(cmd):
            raise OSError("shell failed https://u:secret_sys_pw@host/x")

        subprocess.Popen.__init__ = failing_init
        os.system = failing_system
        try:
            SubprocessSpy.install(owner="run1")
            with pytest.raises(FileNotFoundError):
                subprocess.Popen(["missing", "--token=secret_arg"])
            with pytest.raises(OSError):
                os.system("broken --password=secret_cmd")

            recs = SubprocessSpy.get_records()
            assert len(recs) == 2
            assert recs[0]["capture_state"]["status"] == "failed"
            assert "secret_popen_val" not in recs[0]["capture_state"]["detail"]
            assert "[REDACTED]" in recs[0]["capture_state"]["detail"]
            assert recs[1]["capture_state"]["status"] == "failed"
            assert "secret_sys_pw" not in recs[1]["capture_state"]["detail"]
            assert "[REDACTED]" in recs[1]["capture_state"]["detail"]
        finally:
            SubprocessSpy.uninstall(owner="run1")
            subprocess.Popen.__init__ = orig_init
            os.system = orig_system

    def test_mid_install_failure_rolls_back_earlier_targets(self, monkeypatch):
        orig_init = subprocess.Popen.__init__
        orig_wait = subprocess.Popen.wait
        orig_system = os.system

        real_setattr = setattr

        def failing_setattr(obj, name, val):
            if obj is os and name == "system":
                raise RuntimeError("cannot patch os.system")
            return real_setattr(obj, name, val)

        monkeypatch.setattr("builtins.setattr", failing_setattr)
        try:
            with pytest.raises(RuntimeError, match="cannot patch os.system"):
                SubprocessSpy.install(owner="run1")

            assert SubprocessSpy._installed is False
            assert SubprocessSpy._owner is None
            assert subprocess.Popen.__init__ is orig_init
            assert subprocess.Popen.wait is orig_wait
            assert os.system is orig_system
        finally:
            monkeypatch.undo()
            SubprocessSpy.uninstall()
            subprocess.Popen.__init__ = orig_init
            subprocess.Popen.wait = orig_wait
            os.system = orig_system

    def test_wrong_owner_cannot_uninstall_active_spy(self):
        token_a = object()
        token_b = object()
        assert SubprocessSpy.install(owner=token_a) is True
        try:
            # Second install by another caller returns False.
            assert SubprocessSpy.install(owner=token_b) is False
            # Wrong owner cannot uninstall.
            SubprocessSpy.uninstall(owner=token_b)
            assert SubprocessSpy._installed is True
            assert SubprocessSpy._owner is token_a

            # Correct owner uninstalls cleanly.
            SubprocessSpy.uninstall(owner=token_a)
            assert SubprocessSpy._installed is False
            assert SubprocessSpy._owner is None
        finally:
            SubprocessSpy.uninstall()


# ==========================================================================
# ConsoleInterceptor and TqdmSafeTee ownership, rollback, and faulthandler
# ==========================================================================


class TestConsoleInterceptorOwnershipRollback:
    """Behavioral tests for ConsoleInterceptor transactional start, faulthandler, and stop."""

    def test_partial_start_failure_rolls_back_and_reports_failed(self, tmp_path, monkeypatch):
        orig_stdout = sys.stdout
        orig_stderr = sys.stderr
        opened_handles = []
        real_open = open

        def fail_on_stderr_open(path, *args, **kwargs):
            if str(path).endswith("stderr.log"):
                raise PermissionError("cannot open stderr.log --token=secret_err_tok")
            fh = real_open(path, *args, **kwargs)
            opened_handles.append(fh)
            return fh

        monkeypatch.setattr("builtins.open", fail_on_stderr_open)
        interceptor = ConsoleInterceptor(tmp_path, "basic")
        started = interceptor.start()

        assert started is False
        assert len(opened_handles) == 1
        assert opened_handles[0].closed is True
        assert sys.stdout is orig_stdout
        assert sys.stderr is orig_stderr

        result = interceptor.stop()
        assert result["stdout"]["captured"] is False
        assert result["stderr"]["captured"] is False
        assert result["stdout"]["path"] is None
        assert result["stderr"]["path"] is None
        assert result["capture_state"]["status"] == "failed"
        assert "secret_err_tok" not in result["capture_state"]["detail"]
        assert "[REDACTED]" in result["capture_state"]["detail"]

    def test_preserves_preexisting_faulthandler_and_owns_disabled_faulthandler(self, tmp_path):
        was_enabled_before_test = faulthandler.is_enabled()
        try:
            # Case 1: faulthandler already enabled before start() -> stays enabled after stop().
            if not faulthandler.is_enabled():
                faulthandler.enable()
            assert faulthandler.is_enabled() is True

            ci1 = ConsoleInterceptor(tmp_path / "run1", "basic")
            (tmp_path / "run1").mkdir()
            assert ci1.start() is True
            assert ci1._faulthandler_owned is False
            ci1.stop()
            assert faulthandler.is_enabled() is True

            # Case 2: faulthandler disabled before start() -> enabled on start(), disabled on stop().
            faulthandler.disable()
            assert faulthandler.is_enabled() is False

            ci2 = ConsoleInterceptor(tmp_path / "run2", "basic")
            (tmp_path / "run2").mkdir()
            assert ci2.start() is True
            assert ci2._faulthandler_owned is True
            assert faulthandler.is_enabled() is True
            ci2.stop()
            assert faulthandler.is_enabled() is False
        finally:
            if was_enabled_before_test and not faulthandler.is_enabled():
                faulthandler.enable()
            elif not was_enabled_before_test and faulthandler.is_enabled():
                faulthandler.disable()

    def test_third_party_stream_wrapper_survives_stop_and_writes_cleanly(self, tmp_path):
        orig_stdout = sys.stdout
        orig_stderr = sys.stderr

        class StreamWrapper:
            def __init__(self, inner):
                self.inner = inner

            def write(self, s):
                return self.inner.write(s)

            def flush(self):
                return self.inner.flush()

        ci = ConsoleInterceptor(tmp_path, "basic")
        try:
            assert ci.start() is True
            tp_out = StreamWrapper(sys.stdout)
            tp_err = StreamWrapper(sys.stderr)
            sys.stdout = tp_out
            sys.stderr = tp_err

            ci.stop()

            assert sys.stdout is tp_out
            assert sys.stderr is tp_err
            assert ci.stdout_tee.log_file is None
            assert ci.stderr_tee.log_file is None

            # Continuing to write through the third-party wrappers after log files
            # are closed must succeed with no errors.
            tp_out.write("after stop stdout\n")
            tp_out.flush()
            tp_err.write("after stop stderr\n")
            tp_err.flush()
        finally:
            sys.stdout = orig_stdout
            sys.stderr = orig_stderr

    def test_stop_runs_cleanup_independently_and_is_idempotent(self, tmp_path):
        was_enabled_before_test = faulthandler.is_enabled()
        try:
            faulthandler.disable()
            ci = ConsoleInterceptor(tmp_path, "basic")
            assert ci.start() is True
            sys.stdout.write("out line 1\n")
            sys.stderr.write("err line 1\n")

            stdout_log_ref = ci.stdout_log
            stderr_log_ref = ci.stderr_log
            stderr_flushed = []
            orig_err_flush = ci.stderr_tee.flush

            def failing_out_flush():
                raise OSError("stdout flush exploded")

            def tracked_err_flush():
                stderr_flushed.append(True)
                return orig_err_flush()

            ci.stdout_tee.flush = failing_out_flush
            ci.stderr_tee.flush = tracked_err_flush

            res1 = ci.stop()
            assert stderr_flushed == [True]
            assert faulthandler.is_enabled() is False
            assert stdout_log_ref.closed is True
            assert stderr_log_ref.closed is True
            assert res1["stdout"]["lines_captured"] == 1
            assert res1["stderr"]["lines_captured"] == 1
            assert res1["capture_state"]["status"] == "partial"

            # Second stop() is idempotent and returns identical metrics.
            res2 = ci.stop()
            assert res2 == res1
        finally:
            if was_enabled_before_test and not faulthandler.is_enabled():
                faulthandler.enable()
            elif not was_enabled_before_test and faulthandler.is_enabled():
                faulthandler.disable()

    def test_tee_runtime_log_error_detaches_and_avoids_stderr_recursion(self):
        orig_stream = io.StringIO()
        write_attempts = []

        class FailingLog:
            closed = False

            def write(self, data):
                write_attempts.append(data)
                raise OSError("disk full")

            def flush(self):
                raise OSError("disk full")

        tee = TqdmSafeTee(orig_stream, FailingLog())

        # Attach a DEBUG handler that writes directly to tee (simulating wrapped sys.stderr).
        pubrun_logger = logging.getLogger("pubrun")
        orig_level = pubrun_logger.level
        handler = logging.StreamHandler(tee)
        handler.setLevel(logging.DEBUG)
        pubrun_logger.addHandler(handler)
        pubrun_logger.setLevel(logging.DEBUG)

        orig_stderr = sys.stderr
        sys.stderr = tee
        try:
            ret1 = tee.write("first line\n")
            ret2 = tee.write("second line\n")
            tee.flush()
        finally:
            sys.stderr = orig_stderr
            pubrun_logger.removeHandler(handler)
            pubrun_logger.setLevel(orig_level)

        assert ret1 == len("first line\n")
        assert ret2 == len("second line\n")
        assert tee._log_write_failed is True
        assert tee.log_file is None
        # Broken log was attempted only once, never retried on second write.
        assert len(write_attempts) == 1
        # Original stream received only the caller's text, not recursive logger output.
        assert orig_stream.getvalue() == "first line\nsecond line\n"

    def test_tee_flush_handles_closed_original_and_failing_log(self):
        class ClosedOrig:
            def write(self, data):
                return len(data)

            def flush(self):
                raise ValueError("I/O operation on closed file")

        class BadFlushLog:
            closed = False

            def write(self, data):
                return len(data)

            def flush(self):
                raise OSError("flush failed")

        tee = TqdmSafeTee(ClosedOrig(), BadFlushLog())
        tee.write("buffered")
        tee.flush()  # Must not raise
        assert tee._log_write_failed is True
        assert tee.log_file is None


# ==========================================================================
# SignalExitCapture ownership, rollback, and passive passthrough
# ==========================================================================


class TestSignalExitCaptureOwnershipRollback:
    """Behavioral tests for SignalExitCapture identity restore, rollback, and deactivation."""

    @pytest.mark.skipif(sys.platform == "win32", reason="SIGUSR1 is Unix-only")
    def test_post_install_third_party_signal_handler_survives_and_shim_deactivates(self, monkeypatch):
        pre_calls = []
        tp_calls = []
        finalize_calls = []

        def pre_handler(sig, frame):
            pre_calls.append(sig)

        monkeypatch.setattr(
            "pubrun.capture.signals._finalize_active_run",
            lambda: finalize_calls.append(True),
        )

        old = signal.signal(signal.SIGUSR1, pre_handler)
        cap = SignalExitCapture()
        try:
            cap.install()
            pubrun_shim = signal.getsignal(signal.SIGUSR1)

            def third_party_handler(sig, frame):
                tp_calls.append(sig)
                pubrun_shim(sig, frame)

            signal.signal(signal.SIGUSR1, third_party_handler)
            cap.uninstall()

            # Third-party handler installed after install() must remain intact.
            assert signal.getsignal(signal.SIGUSR1) is third_party_handler

            # Calling the third-party handler chains into deactivated pubrun_shim,
            # which must forward passively to pre_handler without recording or finalizing.
            third_party_handler(signal.SIGUSR1, None)
            assert tp_calls == [signal.SIGUSR1]
            assert pre_calls == [signal.SIGUSR1]
            assert cap.get_records()["signals_received"] == []
            assert finalize_calls == []
        finally:
            cap.uninstall()
            signal.signal(signal.SIGUSR1, old)

    def test_post_install_excepthook_chains_to_prev_hook_after_uninstall(self):
        orig_hook = sys.excepthook
        prev_calls = []
        tp_calls = []

        def pre_hook(exc_type, exc_value, exc_tb):
            prev_calls.append((exc_type.__name__, str(exc_value)))

        sys.excepthook = pre_hook
        cap = SignalExitCapture()
        try:
            cap.install()
            pubrun_hook = sys.excepthook

            def third_party_hook(exc_type, exc_value, exc_tb):
                tp_calls.append(exc_type.__name__)
                pubrun_hook(exc_type, exc_value, exc_tb)

            sys.excepthook = third_party_hook
            cap.uninstall()

            # Third-party excepthook must remain installed.
            assert sys.excepthook is third_party_hook

            # Firing it after uninstall must chain cleanly to pre_hook (via closure)
            # without recording _exit_code or _exit_exception.
            try:
                raise RuntimeError("after uninstall error")
            except RuntimeError as exc:
                sys.excepthook(type(exc), exc, exc.__traceback__)

            assert tp_calls == ["RuntimeError"]
            assert prev_calls == [("RuntimeError", "after uninstall error")]
            records = cap.get_records()
            assert records["exit_code"] is None
            assert records["exit_exception"] is None
        finally:
            cap.uninstall()
            sys.excepthook = orig_hook

    def test_active_excepthook_redacts_secrets_and_preserves_int_system_exit(self):
        orig_hook = sys.excepthook
        sys.excepthook = lambda *a: None
        cap = SignalExitCapture()
        try:
            cap.install()

            try:
                raise ValueError("failed connecting with --api-key=secret_exc_val")
            except ValueError as exc:
                sys.excepthook(type(exc), exc, exc.__traceback__)

            rec = cap.get_records()
            assert rec["exit_code"] == 1
            assert "secret_exc_val" not in rec["exit_exception"]
            assert "[REDACTED]" in rec["exit_exception"]

            # Separate capture for integer SystemExit parity.
            cap.uninstall()
            cap2 = SignalExitCapture()
            cap2.install()
            try:
                raise SystemExit(42)
            except SystemExit as exc:
                sys.excepthook(type(exc), exc, exc.__traceback__)
            assert cap2.get_records()["exit_code"] == 42
            assert cap2.get_records()["exit_exception"] == "SystemExit(42)"
            cap2.uninstall()
        finally:
            cap.uninstall()
            sys.excepthook = orig_hook

    @pytest.mark.skipif(sys.platform == "win32", reason="SIGUSR1 is Unix-only")
    def test_excepthook_install_failure_rolls_back_signal_handlers(self, monkeypatch):
        def my_handler(sig, frame):
            pass

        old = signal.signal(signal.SIGUSR1, my_handler)
        cap = SignalExitCapture()
        monkeypatch.setattr(
            cap,
            "_install_excepthook",
            lambda: (_ for _ in ()).throw(RuntimeError("excepthook failed --token=sec123")),
        )
        try:
            with pytest.raises(RuntimeError, match="excepthook failed"):
                cap.install()

            assert cap._installed is False
            assert signal.getsignal(signal.SIGUSR1) is my_handler
            rec = cap.get_records()
            assert rec["capture_state"]["status"] == "failed"
            assert "sec123" not in rec["capture_state"]["detail"]
        finally:
            signal.signal(signal.SIGUSR1, old)

    def test_signal_restore_failure_still_restores_excepthook(self, monkeypatch):
        orig_hook = sys.excepthook
        cap = SignalExitCapture()
        try:
            cap.install()
            assert sys.excepthook is not orig_hook

            monkeypatch.setattr(
                cap,
                "_restore_signal_handlers",
                lambda: (_ for _ in ()).throw(RuntimeError("signal restore broke")),
            )
            # Must not raise and must still restore sys.excepthook.
            cap.uninstall()
            assert sys.excepthook is orig_hook
        finally:
            sys.excepthook = orig_hook

    def test_non_main_thread_records_partial_capture_state(self, monkeypatch):
        cap = SignalExitCapture()
        monkeypatch.setattr(
            signal,
            "signal",
            lambda *a, **k: (_ for _ in ()).throw(ValueError("not main thread")),
        )
        try:
            cap.install()
            rec = cap.get_records()
            assert rec["capture_state"]["status"] == "partial"
            assert "main thread" in rec["capture_state"]["detail"]
        finally:
            cap.uninstall()


# ==========================================================================
# ResourceWatcher teardown safety and honest failure states
# ==========================================================================


class TestResourceWatcherTeardownSafety:
    """Behavioral tests for ResourceWatcher.stop() idempotence, error isolation, and status."""

    def test_stop_on_unstarted_watcher_does_not_raise_or_poll(self, monkeypatch):
        class FakeTracker:
            event_stream = None

        watcher = ResourceWatcher(FakeTracker(), interval_seconds=1.0, max_failures=3)
        poll_calls = []
        monkeypatch.setattr(watcher, "_poll_rss", lambda: poll_calls.append(1) or 1024)

        watcher.stop()
        watcher.stop()  # idempotent
        assert poll_calls == []
        assert watcher.to_manifest_dict()["capture_state"]["status"] == "complete"

    def test_stop_isolates_final_poll_exception_and_is_idempotent(self, monkeypatch):
        class FakeTracker:
            event_stream = None

        watcher = ResourceWatcher(FakeTracker(), interval_seconds=0.02, max_failures=5)
        call_count = [0]

        def poll_rss():
            call_count[0] += 1
            if call_count[0] >= 2 and watcher._stop_event.is_set():
                raise RuntimeError("poll exploded during shutdown")
            return 4096

        monkeypatch.setattr(watcher, "_poll_rss", poll_rss)
        watcher.start()
        deadline = time.time() + 2.0
        while call_count[0] < 1 and time.time() < deadline:
            time.sleep(0.01)

        # stop() must swallow the shutdown poll exception cleanly.
        watcher.stop()
        count_after_first_stop = call_count[0]
        watcher.stop()
        assert call_count[0] == count_after_first_stop

    def test_event_stream_emit_exception_isolated_and_stopped_after_stop(self, monkeypatch):
        emitted = []

        class FailingEventStream:
            def emit(self, name, payload=None):
                emitted.append((name, payload))
                raise OSError("event stream broken")

        class FakeTracker:
            event_stream = FailingEventStream()

        watcher = ResourceWatcher(FakeTracker(), interval_seconds=1.0, max_failures=3)
        monkeypatch.setattr(watcher, "_poll_rss", lambda: 2048)
        monkeypatch.setattr(watcher, "_poll_cpu", lambda: 5.0)

        # Must not raise when emit() raises.
        watcher._update_metrics()
        assert len(emitted) == 1
        assert watcher.peak_rss_bytes == 2048

        # After stop, _update_metrics() must not emit events.
        watcher.stop()
        watcher._update_metrics()
        assert len(emitted) == 1

    def test_consecutive_failures_yield_failed_and_partial_states(self, monkeypatch):
        class FakeTracker:
            event_stream = None

        # Case 1: every sample fails -> "failed", skips final poll on stop().
        w_fail = ResourceWatcher(FakeTracker(), interval_seconds=0.01, max_failures=2)
        fail_polls = [0]

        def always_fail():
            fail_polls[0] += 1
            return -1

        monkeypatch.setattr(w_fail, "_poll_rss", always_fail)
        w_fail.start()
        deadline = time.time() + 2.0
        while w_fail.is_alive() and time.time() < deadline:
            time.sleep(0.01)

        polls_after_abort = fail_polls[0]
        w_fail.stop()
        assert fail_polls[0] == polls_after_abort
        manifest_fail = w_fail.to_manifest_dict()
        assert manifest_fail["capture_state"]["status"] == "failed"

        # Case 2: one good sample followed by consecutive failures -> "partial".
        w_partial = ResourceWatcher(FakeTracker(), interval_seconds=0.01, max_failures=2)
        samples = iter([8192, -1, -1, -1])
        monkeypatch.setattr(w_partial, "_poll_rss", lambda: next(samples, -1))
        w_partial.start()
        deadline = time.time() + 2.0
        while w_partial.is_alive() and time.time() < deadline:
            time.sleep(0.01)

        w_partial.stop()
        manifest_partial = w_partial.to_manifest_dict()
        assert manifest_partial["peak_rss_bytes"] == 8192
        assert manifest_partial["capture_state"]["status"] == "partial"
