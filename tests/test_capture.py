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
