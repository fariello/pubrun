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


class TestTqdmSafeTeeBrokenPipe:
    """P3-T1: BrokenPipeError handling in write() and flush()."""

    def test_write_catches_broken_pipe(self):
        """write() does not raise when original stream has a broken pipe."""
        import io
        from pubrun.capture.console import TqdmSafeTee

        class BrokenStream:
            def write(self, data):
                raise BrokenPipeError("pipe closed")
            def flush(self):
                raise BrokenPipeError("pipe closed")

        log_file = io.StringIO()
        tee = TqdmSafeTee(BrokenStream(), log_file)

        # Should NOT raise
        ret = tee.write("hello\n")
        assert ret == 6  # len("hello\n")
        # Log file should still receive the data
        assert "hello" in log_file.getvalue()

    def test_flush_catches_broken_pipe(self):
        """flush() does not raise when original stream has a broken pipe."""
        import io
        from pubrun.capture.console import TqdmSafeTee

        class BrokenFlush:
            def write(self, data):
                return len(data)
            def flush(self):
                raise BrokenPipeError("pipe closed")

        log_file = io.StringIO()
        tee = TqdmSafeTee(BrokenFlush(), log_file)
        tee.write("data\n")

        # flush should NOT raise
        tee.flush()


class _FakeClock:
    """Thread-safe deterministic wall and monotonic clock for capture timing tests."""

    def __init__(self, wall: float = 1_750_000_000.0, mono: float = 987654.321) -> None:
        import threading
        import time as _real_time

        self._lock = threading.Lock()
        self._real_time = _real_time
        self._wall = float(wall)
        self._mono = float(mono)

    def time(self) -> float:
        with self._lock:
            return self._wall

    def perf_counter(self) -> float:
        with self._lock:
            return self._mono

    def advance(self, seconds: float) -> None:
        with self._lock:
            self._mono += seconds
            self._wall += seconds

    def jump_wall(self, delta: float) -> None:
        with self._lock:
            self._wall += delta

    def __getattr__(self, name: str):
        return getattr(self._real_time, name)


class TestSubprocessSpyMonotonicTiming:
    """Deterministic wall-clock-step tests for SubprocessSpy monotonic durations."""

    def test_popen_forward_and_backward_wall_jumps(self, monkeypatch):
        import pytest
        import pubrun.capture.subprocesses as sub_mod

        clock = _FakeClock(wall=1_750_000_000.0, mono=987654.321)
        monkeypatch.setattr(sub_mod, "time", clock)

        SubprocessSpy.install(max_records=100)
        try:
            p_fwd = subprocess.Popen([sys.executable, "-c", "pass"])
            clock.advance(0.40)
            clock.jump_wall(7200.0)
            assert p_fwd.wait() == 0

            p_bwd = subprocess.Popen([sys.executable, "-c", "pass"])
            clock.advance(0.15)
            clock.jump_wall(-7200.0)
            assert p_bwd.wait() == 0

            records = list(SubprocessSpy.get_records())
        finally:
            SubprocessSpy.uninstall()

        assert SubprocessSpy._start_monos == {}
        assert len(records) == 2

        fwd, bwd = records
        assert fwd["elapsed_seconds"] == pytest.approx(0.40, abs=1e-9)
        assert fwd["duration_clock"] == "monotonic"
        assert fwd["ended_at_utc"] - fwd["started_at_utc"] == pytest.approx(7200.40, abs=1e-5)
        assert fwd["capture_state"]["status"] == "complete"

        assert bwd["elapsed_seconds"] == pytest.approx(0.15, abs=1e-9)
        assert bwd["duration_clock"] == "monotonic"
        assert bwd["ended_at_utc"] < bwd["started_at_utc"]
        assert bwd["capture_state"]["status"] == "complete"

        assert "987654" not in json.dumps(records)

    def test_os_system_backward_wall_jump_and_exception(self, monkeypatch):
        import pytest
        import pubrun.capture.subprocesses as sub_mod

        clock = _FakeClock(wall=1_750_000_000.0, mono=987654.321)
        monkeypatch.setattr(sub_mod, "time", clock)

        def fake_system(cmd: str) -> int:
            if cmd == "fail_cmd":
                clock.advance(0.12)
                clock.jump_wall(-7200.0)
                raise OSError("system boom")
            clock.advance(0.30)
            clock.jump_wall(-7200.0)
            return 0

        monkeypatch.setattr(os, "system", fake_system)
        SubprocessSpy.install(max_records=100)
        try:
            assert os.system("ok_cmd") == 0
            with pytest.raises(OSError, match="system boom"):
                os.system("fail_cmd")
            records = list(SubprocessSpy.get_records())
        finally:
            SubprocessSpy.uninstall()

        assert SubprocessSpy._start_monos == {}
        assert len(records) == 2

        ok_rec, err_rec = records
        assert ok_rec["exit_code"] == 0
        assert ok_rec["ended_at_utc"] < ok_rec["started_at_utc"]
        assert ok_rec["elapsed_seconds"] == pytest.approx(0.30, abs=1e-9)
        assert ok_rec["duration_clock"] == "monotonic"
        assert ok_rec["capture_state"]["status"] == "complete"

        assert err_rec["ended_at_utc"] < err_rec["started_at_utc"]
        assert err_rec["elapsed_seconds"] == pytest.approx(0.12, abs=1e-9)
        assert err_rec["duration_clock"] == "monotonic"
        assert err_rec["capture_state"]["status"] == "failed"
        assert "system boom" in err_rec["capture_state"]["detail"]

        assert "987654" not in json.dumps(records)

    def test_popen_launch_failure_records_monotonic_duration(self, monkeypatch):
        import pytest
        import pubrun.capture.subprocesses as sub_mod

        clock = _FakeClock(wall=1_750_000_000.0, mono=987654.321)
        monkeypatch.setattr(sub_mod, "time", clock)

        def failing_popen_init(self, *args, **kwargs):
            clock.advance(0.07)
            clock.jump_wall(-7200.0)
            raise FileNotFoundError("no such binary")

        monkeypatch.setattr(subprocess.Popen, "__init__", failing_popen_init)
        SubprocessSpy.install(max_records=100)
        try:
            with pytest.raises(FileNotFoundError, match="no such binary"):
                subprocess.Popen(["__missing_binary__"])
            records = list(SubprocessSpy.get_records())
        finally:
            SubprocessSpy.uninstall()

        assert len(records) == 1
        rec = records[0]
        assert rec["ended_at_utc"] < rec["started_at_utc"]
        assert rec["elapsed_seconds"] == pytest.approx(0.07, abs=1e-9)
        assert rec["duration_clock"] == "monotonic"
        assert rec["capture_state"]["status"] == "failed"
        assert "987654" not in json.dumps(records)

    def test_finalize_all_monotonic_non_collision_and_post_finalize_wait(self, monkeypatch):
        import pytest
        import pubrun.capture.subprocesses as sub_mod

        clock = _FakeClock(wall=1_750_000_000.0, mono=987654.321)
        monkeypatch.setattr(sub_mod, "time", clock)

        SubprocessSpy.install(max_records=100)
        try:
            proc = subprocess.Popen([sys.executable, "-c", "pass"])
            synthetic = {
                "argv": ["synthetic_cmd"],
                "exit_code": None,
                "capture_state": {"status": "partial"},
            }
            SubprocessSpy._records.append(synthetic)

            clock.advance(0.25)
            clock.jump_wall(-7200.0)
            SubprocessSpy.finalize_all()

            real_rec = SubprocessSpy._records[0]
            assert real_rec["ended_at_utc"] < real_rec["started_at_utc"]
            assert real_rec["elapsed_seconds"] == pytest.approx(0.25, abs=1e-9)
            assert real_rec["duration_clock"] == "monotonic"
            assert real_rec["capture_state"]["status"] == "complete"

            # Synthetic record has no monotonic entry and leaves elapsed_seconds unset.
            assert synthetic["capture_state"]["status"] == "complete"
            assert "ended_at_utc" in synthetic
            assert "elapsed_seconds" not in synthetic
            assert "duration_clock" not in synthetic

            # Waiting after finalize_all preserves the already-finalized monotonic duration.
            clock.advance(10.0)
            assert proc.wait() == 0
            assert real_rec["exit_code"] == 0
            assert real_rec["elapsed_seconds"] == pytest.approx(0.25, abs=1e-9)
            assert real_rec["duration_clock"] == "monotonic"

            serialized = json.dumps(SubprocessSpy._records)
        finally:
            SubprocessSpy.uninstall()

        assert SubprocessSpy._start_monos == {}
        assert "987654" not in serialized

    def test_subprocess_spy_manifest_validates_against_schema(self, tmp_path, monkeypatch):
        import pytest
        import pubrun.capture.subprocesses as sub_mod
        import pubrun.tracker as tracker_mod
        import pubrun.writer as writer_mod

        jsonschema = pytest.importorskip("jsonschema")
        schema_path = Path(__file__).resolve().parents[1] / "schemas" / "manifest.schema.json"
        schema = json.loads(schema_path.read_text(encoding="utf-8"))

        clock = _FakeClock(wall=1_750_000_000.0, mono=987654.321)
        monkeypatch.setattr(sub_mod, "time", clock)
        monkeypatch.setattr(tracker_mod, "time", clock)
        monkeypatch.setattr(writer_mod, "time", clock)
        monkeypatch.setattr(Path, "cwd", lambda: tmp_path)

        tracker = start(
            capture={"subprocesses": {"enabled": True}, "resources": {"depth": "off"}}
        )
        p_unwaited = None
        try:
            p_waited = subprocess.Popen([sys.executable, "-c", "pass"])
            clock.advance(0.18)
            clock.jump_wall(-7200.0)
            assert p_waited.wait() == 0

            with pytest.raises(OSError):
                subprocess.Popen(["__nonexistent_pubrun_spy_binary__"])

            p_unwaited = subprocess.Popen([sys.executable, "-c", "pass"])
            clock.advance(0.09)
            clock.jump_wall(-7200.0)
        finally:
            tracker.stop()
            if p_unwaited is not None:
                p_unwaited.wait()

        raw_text = (tracker.run_dir / "manifest.json").read_text(encoding="utf-8")
        assert "987654" not in raw_text
        manifest = json.loads(raw_text)
        jsonschema.validate(manifest, schema)

        subs = manifest["subprocesses"]
        assert len(subs) == 3
        for rec in subs:
            assert rec["elapsed_seconds"] >= 0.0
            assert rec["duration_clock"] == "monotonic"


class TestResourceWatcherMonotonicSampling:
    """Regression tests confirming ResourceWatcher CPU sampling stays monotonic."""

    def test_poll_cpu_unaffected_by_backward_wall_clock_jump(self, monkeypatch):
        from types import SimpleNamespace
        import pubrun.capture.resources as res_mod
        from pubrun.capture.resources import ResourceWatcher

        clock = _FakeClock(wall=1_750_000_000.0, mono=987654.321)
        monkeypatch.setattr(res_mod, "time", clock)

        samples = iter([
            SimpleNamespace(user=1.0, system=0.2),
            SimpleNamespace(user=1.6, system=0.4),
        ])
        monkeypatch.setattr(res_mod.os, "times", lambda: next(samples))

        watcher = ResourceWatcher(
            run_tracker=None, interval_seconds=1.0, system_metrics=False
        )
        assert watcher._poll_cpu() == 0.0

        clock.advance(2.0)
        clock.jump_wall(-7200.0)
        assert watcher._poll_cpu() == 40.0

    def test_poll_tree_cpu_unaffected_by_backward_wall_clock_jump_linux(self, monkeypatch):
        import pytest
        import pubrun.capture.resources as res_mod
        from pubrun.capture.resources import ResourceWatcher

        if not sys.platform.startswith("linux"):
            pytest.skip("_poll_tree_cpu is Linux-only")

        clock = _FakeClock(wall=1_750_000_000.0, mono=987654.321)
        monkeypatch.setattr(res_mod, "time", clock)

        watcher = ResourceWatcher(
            run_tracker=None, interval_seconds=1.0, scope="tree", system_metrics=False
        )
        assert watcher._clk_tck > 0

        base_jiffies = 1000
        delta_jiffies = int(round(1.5 * watcher._clk_tck))
        jiffy_samples = iter([base_jiffies, base_jiffies + delta_jiffies])
        monkeypatch.setattr(res_mod, "_get_tree_cpu_jiffies_linux", lambda: next(jiffy_samples))

        assert watcher._poll_tree_cpu() == 0.0

        clock.advance(2.0)
        clock.jump_wall(-7200.0)
        assert watcher._poll_tree_cpu() == 75.0
