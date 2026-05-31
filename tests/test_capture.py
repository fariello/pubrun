"""Tests for capture subsystems: invocation, subprocess spy, and console interceptor."""
import os
import sys
import json
import subprocess
from pathlib import Path

from pubrun import start, get_current_run
from pubrun.capture.subprocesses import SubprocessSpy, disable_spy


class TestInvocationCapture:

    def test_rerun_command_present(self):
        tracker = start()
        tracker.stop()
        manifest_path = tracker.run_dir / "manifest.json"
        with open(manifest_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        inv = data["invocation"]
        assert "rerun_command" in inv
        assert "cd " in inv["rerun_command"]
        assert "python" in inv["rerun_command"]
        assert inv["capture_state"]["status"] == "complete"

    def test_argv_is_list(self):
        tracker = start()
        tracker.stop()
        manifest_path = tracker.run_dir / "manifest.json"
        with open(manifest_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        assert isinstance(data["invocation"]["argv"], list)

    def test_working_directory_captured(self):
        tracker = start()
        tracker.stop()
        manifest_path = tracker.run_dir / "manifest.json"
        with open(manifest_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        wd = data["invocation"]["working_directory"]
        assert "path" in wd
        assert isinstance(wd["path"], str)


class TestSubprocessInterceptor:

    def test_waited_subprocess_captured(self):
        overrides = {"capture": {"subprocesses": {"enabled": True}}}
        tracker = start(**overrides)
        subprocess.run([sys.executable, "-c", "print('hello pubrun')"])
        tracker.stop()
        with open(tracker.run_dir / "manifest.json", "r", encoding="utf-8") as f:
            data = json.load(f)
        subs = data["subprocesses"]
        assert len(subs) >= 1
        assert subs[0]["exit_code"] == 0
        assert subs[0]["capture_state"]["status"] == "complete"

    def test_detached_subprocess_finalized(self):
        overrides = {"capture": {"subprocesses": {"enabled": True}}}
        tracker = start(**overrides)
        p = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(0.1)"])
        tracker.stop()
        with open(tracker.run_dir / "manifest.json", "r", encoding="utf-8") as f:
            data = json.load(f)
        subs = data["subprocesses"]
        assert len(subs) >= 1
        # Detached process was finalized by finalize_all
        unwatched = [s for s in subs if s["exit_code"] is None]
        for s in unwatched:
            assert s["capture_state"]["status"] == "complete"

    def test_os_system_captured(self):
        overrides = {"capture": {"subprocesses": {"enabled": True}}}
        tracker = start(**overrides)
        os.system("echo hello_os_system")
        tracker.stop()
        with open(tracker.run_dir / "manifest.json", "r", encoding="utf-8") as f:
            data = json.load(f)
        subs = data["subprocesses"]
        assert len(subs) >= 1
        # Find the echo command
        echo_subs = [s for s in subs if "echo" in str(s.get("argv", []))]
        assert len(echo_subs) >= 1
        assert echo_subs[0]["exit_code"] == 0

    def test_disable_spy_context_manager(self):
        overrides = {"capture": {"subprocesses": {"enabled": True}}}
        tracker = start(**overrides)
        with disable_spy():
            subprocess.run([sys.executable, "-c", "print('bypassed')"])
        subprocess.run([sys.executable, "-c", "print('tracked')"])
        tracker.stop()
        with open(tracker.run_dir / "manifest.json", "r", encoding="utf-8") as f:
            data = json.load(f)
        subs = data["subprocesses"]
        # Only the tracked one should appear
        assert len(subs) == 1

    def test_shlex_fallback_on_bad_quotes(self):
        """SubprocessSpy._safe_shlex_split should handle unterminated quotes."""
        result = SubprocessSpy._safe_shlex_split("echo 'unterminated")
        assert isinstance(result, list)
        assert len(result) >= 1

    def test_shlex_split_normal_string(self):
        result = SubprocessSpy._safe_shlex_split("echo hello world")
        assert result == ["echo", "hello", "world"]

    def test_shlex_split_list_input(self):
        result = SubprocessSpy._safe_shlex_split(["python3", "-c", "pass"])
        assert result == ["python3", "-c", "pass"]


class TestConsoleInterceptor:

    def test_tqdm_compression(self):
        overrides = {"console": {"capture_mode": "basic"}}
        tracker = start(**overrides)
        sys.stdout.write("Epoch 1/10\r")
        sys.stdout.write("Epoch 2/10\r")
        sys.stdout.write("Epoch 3/10\n")
        sys.stdout.write("Done!\n")
        tracker.stop()

        stdout_log = tracker.run_dir / "stdout.log"
        assert stdout_log.exists()
        content = stdout_log.read_text(encoding="utf-8")
        lines = content.splitlines()
        assert len(lines) == 2
        assert "Epoch 3/10" in lines[0]
        assert "Done!" in lines[1]

    def test_console_manifest_structure(self):
        overrides = {"console": {"capture_mode": "basic"}}
        tracker = start(**overrides)
        sys.stdout.write("test output\n")
        tracker.stop()
        with open(tracker.run_dir / "manifest.json", "r", encoding="utf-8") as f:
            data = json.load(f)
        console = data["console"]
        assert console["capture_mode"] == "basic"
        assert "stdout" in console
        assert console["stdout"]["path"] == "stdout.log"
        assert console["stdout"]["lines_captured"] >= 1

    def test_console_off_mode(self):
        overrides = {"console": {"capture_mode": "off"}}
        tracker = start(**overrides)
        sys.stdout.write("this should not be captured\n")
        tracker.stop()
        stdout_log = tracker.run_dir / "stdout.log"
        assert not stdout_log.exists()

    def test_multi_line_write(self):
        overrides = {"console": {"capture_mode": "basic"}}
        tracker = start(**overrides)
        sys.stdout.write("line1\nline2\nline3\n")
        tracker.stop()
        stdout_log = tracker.run_dir / "stdout.log"
        content = stdout_log.read_text(encoding="utf-8")
        lines = content.splitlines()
        assert len(lines) == 3
        assert lines[0] == "line1"
        assert lines[1] == "line2"
        assert lines[2] == "line3"


# ==========================================================================
# SubprocessSpy unit tests: finalize_all, overflow, Popen failure, disable_spy nesting
# ==========================================================================

class TestFinalizeAll:
    """Unit tests for SubprocessSpy.finalize_all() state transitions."""

    def test_upgrades_partial_to_complete(self):
        """finalize_all() upgrades records with status 'partial' to 'complete'."""
        SubprocessSpy._records = [
            {"argv": ["cmd1"], "exit_code": None, "capture_state": {"status": "partial"}},
            {"argv": ["cmd2"], "exit_code": None, "capture_state": {"status": "partial"}},
        ]
        SubprocessSpy.finalize_all()
        for rec in SubprocessSpy._records:
            assert rec["capture_state"]["status"] == "complete"
            assert "ended_at_utc" in rec

    def test_does_not_modify_completed_records(self):
        """finalize_all() leaves records with exit_code already set untouched."""
        original_time = 12345.0
        SubprocessSpy._records = [
            {"argv": ["done"], "exit_code": 0, "ended_at_utc": original_time,
             "capture_state": {"status": "complete"}},
        ]
        SubprocessSpy.finalize_all()
        assert SubprocessSpy._records[0]["ended_at_utc"] == original_time

    def test_does_not_modify_failed_records_with_exit_code(self):
        """Records that already have exit_code != None are left alone."""
        SubprocessSpy._records = [
            {"argv": ["fail"], "exit_code": 1, "capture_state": {"status": "failed"}},
        ]
        SubprocessSpy.finalize_all()
        assert SubprocessSpy._records[0]["capture_state"]["status"] == "failed"


class TestSubprocessSpyOverflow:
    """Tests for the _max_records overflow mechanism."""

    def test_max_records_limits_capture(self):
        """After max_records, new subprocesses are not recorded."""
        SubprocessSpy.install(max_records=2)
        try:
            # Trigger 4 subprocess calls
            for _ in range(4):
                subprocess.run([sys.executable, "-c", "pass"])
            records = SubprocessSpy.get_records()
            assert len(records) == 2
            assert SubprocessSpy._truncated is True
        finally:
            SubprocessSpy.uninstall()
            SubprocessSpy._records = []
            SubprocessSpy._truncated = False


class TestDisableSpyNesting:
    """Tests for nested disable_spy() context managers."""

    def test_nested_disable_spy(self):
        """Nested disable_spy() maintains bypass through both levels."""
        SubprocessSpy.install(max_records=100)
        try:
            with disable_spy():
                subprocess.run([sys.executable, "-c", "pass"])
                with disable_spy():
                    subprocess.run([sys.executable, "-c", "pass"])
                # Still bypassed after inner exits
                subprocess.run([sys.executable, "-c", "pass"])
            # After outer exits, spy is active again
            subprocess.run([sys.executable, "-c", "pass"])
            records = SubprocessSpy.get_records()
            # Only the last one (after outer exits) should be captured
            assert len(records) == 1
        finally:
            SubprocessSpy.uninstall()
            SubprocessSpy._records = []


# ==========================================================================
# TqdmSafeTee advanced tests: multi-CR, line_count, __getattr__
# ==========================================================================

class TestTqdmSafeTeeAdvanced:
    """Advanced tests for TqdmSafeTee edge cases."""

    def test_multiple_cr_in_single_write(self):
        """Multiple \\r in one write() call correctly squashes intermediate buffers."""
        import io
        from pubrun.capture.console import TqdmSafeTee

        original = io.StringIO()
        log_file = io.StringIO()
        tee = TqdmSafeTee(original, log_file)

        # Simulate tqdm: "10%\r50%\r100%\n"
        tee.write("10%\r50%\r100%\n")

        log_content = log_file.getvalue()
        # Only the final line after the last \r should be logged
        assert "100%" in log_content
        # Intermediate progress should be squashed
        assert "10%" not in log_content
        assert "50%" not in log_content

    def test_line_count_after_flush(self):
        """flush() with pending buffer increments line_count."""
        import io
        from pubrun.capture.console import TqdmSafeTee

        original = io.StringIO()
        log_file = io.StringIO()
        tee = TqdmSafeTee(original, log_file)

        tee.write("partial data without newline")
        assert tee.line_count == 0  # No newline yet

        tee.flush()
        assert tee.line_count == 1  # Flush writes pending buffer as a line

    def test_line_count_accuracy_with_newlines(self):
        """line_count accurately counts newline-terminated lines."""
        import io
        from pubrun.capture.console import TqdmSafeTee

        original = io.StringIO()
        log_file = io.StringIO()
        tee = TqdmSafeTee(original, log_file)

        tee.write("line1\nline2\nline3\n")
        assert tee.line_count == 3

    def test_getattr_delegation(self):
        """__getattr__ delegates to the original stream."""
        import io
        from pubrun.capture.console import TqdmSafeTee

        original = io.StringIO()
        log_file = io.StringIO()
        tee = TqdmSafeTee(original, log_file)

        # StringIO has these attributes
        assert hasattr(tee, "getvalue")  # delegated from original
        assert tee.closed is False  # delegated

    def test_write_to_closed_log_file(self):
        """Writing when log_file is closed still passes through to original."""
        import io
        from pubrun.capture.console import TqdmSafeTee

        original = io.StringIO()
        log_file = io.StringIO()
        tee = TqdmSafeTee(original, log_file)

        log_file.close()
        # Should not raise
        tee.write("after log closed\n")
        assert "after log closed" in original.getvalue()
