"""Exhaustive CLI tests for pubrun command-line interface."""
import json
import os
import sys
import subprocess
import pytest
from pathlib import Path

PYTHON = sys.executable


def run_pubrun(*args, cwd=None):
    """Helper to invoke pubrun CLI and return the completed process."""
    cmd = [PYTHON, "-m", "pubrun"] + list(args)
    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        cwd=cwd or os.getcwd(),
        timeout=30
    )


class TestCliHelp:

    def test_help_exits_zero(self):
        result = run_pubrun("--help")
        assert result.returncode == 0

    def test_help_mentions_pubrun(self):
        result = run_pubrun("--help")
        assert "pubrun" in result.stdout.lower()

    def test_help_command_translation_root(self):
        result = run_pubrun("help")
        assert result.returncode == 0
        assert "usage: pubrun" in result.stdout.lower()

    def test_help_command_translation_subcommand(self):
        result = run_pubrun("help", "report")
        assert result.returncode == 0
        assert "usage: pubrun report" in result.stdout.lower()

    def test_report_help(self):
        result = run_pubrun("report", "--help")
        assert result.returncode == 0
        assert "report" in result.stdout.lower()

    def test_methods_help(self):
        result = run_pubrun("methods", "--help")
        assert result.returncode == 0

    def test_diff_help(self):
        result = run_pubrun("diff", "--help")
        assert result.returncode == 0

    def test_rerun_help(self):
        result = run_pubrun("rerun", "--help")
        assert result.returncode == 0

    def test_meta_help(self):
        result = run_pubrun("meta", "--help")
        assert result.returncode == 0

    def test_cite_help(self):
        result = run_pubrun("cite", "--help")
        assert result.returncode == 0

    def test_version_exits_zero(self):
        result = run_pubrun("--version")
        assert result.returncode == 0

    def test_version_prints_version_string(self):
        result = run_pubrun("--version")
        assert "pubrun" in result.stdout.lower()
        # Should contain a version-like pattern (digits and dots)
        import re
        assert re.search(r"\d+\.\d+", result.stdout)


class TestCliInfo:

    def test_info_exits_zero(self):
        result = run_pubrun("--info")
        assert result.returncode == 0

    def test_info_prints_system_info(self):
        result = run_pubrun("--info")
        output = result.stdout.lower()
        assert "python" in output or "system" in output or "pubrun" in output


class TestCliShowConfig:

    def test_show_config_exits_zero(self):
        result = run_pubrun("--show-config")
        assert result.returncode == 0

    def test_show_config_prints_toml(self):
        result = run_pubrun("--show-config")
        # Should contain TOML section headers
        assert "[core]" in result.stdout or "core" in result.stdout


class TestCliCreateConfig:

    def test_create_config_writes_file(self, tmp_path):
        dest = str(tmp_path / ".pubrun.toml")
        result = run_pubrun("--create-config", dest, cwd=str(tmp_path))
        assert result.returncode == 0
        assert Path(dest).exists()
        content = Path(dest).read_text(encoding="utf-8")
        assert "[core]" in content

    def test_create_config_refuses_overwrite(self, tmp_path):
        dest = str(tmp_path / ".pubrun.toml")
        # Create file first
        Path(dest).write_text("existing content", encoding="utf-8")
        result = run_pubrun("--create-config", dest, cwd=str(tmp_path))
        assert result.returncode == 1
        # Original content should be preserved
        assert Path(dest).read_text(encoding="utf-8") == "existing content"


class TestCliCite:

    def test_cite_apa(self):
        result = run_pubrun("cite", "--style", "apa")
        assert result.returncode == 0
        assert "pubrun" in result.stdout.lower() or "fariello" in result.stdout.lower()

    def test_cite_bibtex(self):
        result = run_pubrun("cite", "--style", "bibtex")
        assert result.returncode == 0
        assert "pubrun" in result.stdout.lower() or "@" in result.stdout

    def test_cite_mla(self):
        result = run_pubrun("cite", "--style", "mla")
        assert result.returncode == 0

    def test_cite_chicago(self):
        result = run_pubrun("cite", "--style", "chicago")
        assert result.returncode == 0


class TestCliMeta:

    def test_meta_default_creates_file(self, tmp_path):
        result = run_pubrun("meta", cwd=str(tmp_path))
        assert result.returncode == 0
        # Default output goes to runs/meta.json
        meta_path = tmp_path / "runs" / "meta.json"
        assert meta_path.exists()
        data = json.loads(meta_path.read_text(encoding="utf-8"))
        assert "host" in data or "python" in data or "hardware" in data

    def test_meta_to_file(self, tmp_path):
        out_path = str(tmp_path / "meta.json")
        result = run_pubrun("meta", "--out", out_path, cwd=str(tmp_path))
        assert result.returncode == 0
        assert Path(out_path).exists()
        data = json.loads(Path(out_path).read_text(encoding="utf-8"))
        assert isinstance(data, dict)

    def test_meta_basic_depth(self, tmp_path):
        result = run_pubrun("meta", "--basic", cwd=str(tmp_path))
        assert result.returncode == 0

    def test_meta_deep_depth(self, tmp_path):
        result = run_pubrun("meta", "--deep", cwd=str(tmp_path))
        assert result.returncode == 0


class TestCliReport:

    @pytest.fixture
    def run_dir(self, tmp_path):
        """Create a real run to test report commands against."""
        from pubrun import start as pubrun_start
        import pubrun.tracker
        pubrun.tracker._active_run = None
        old_cwd = Path.cwd
        try:
            Path.cwd = staticmethod(lambda: tmp_path)
            tracker = pubrun_start()
            tracker.stop()
            return str(tracker.run_dir)
        finally:
            Path.cwd = old_cwd
            pubrun.tracker._active_run = None

    def test_report_valid_run(self, run_dir):
        result = run_pubrun("report", run_dir)
        assert result.returncode == 0

    def test_report_basic_depth(self, run_dir):
        result = run_pubrun("report", run_dir, "--basic")
        assert result.returncode == 0

    def test_report_deep_depth(self, run_dir):
        result = run_pubrun("report", run_dir, "--deep")
        assert result.returncode == 0

    def test_report_invalid_path(self, tmp_path):
        result = run_pubrun("report", str(tmp_path / "nonexistent"))
        assert result.returncode != 0


class TestCliMethods:

    @pytest.fixture
    def run_dir(self, tmp_path):
        """Create a real run to test methods command against."""
        from pubrun import start as pubrun_start
        import pubrun.tracker
        pubrun.tracker._active_run = None
        old_cwd = Path.cwd
        try:
            Path.cwd = staticmethod(lambda: tmp_path)
            tracker = pubrun_start()
            tracker.stop()
            return str(tracker.run_dir)
        finally:
            Path.cwd = old_cwd
            pubrun.tracker._active_run = None

    def test_methods_markdown(self, run_dir):
        result = run_pubrun("methods", run_dir)
        assert result.returncode == 0
        assert "Computational Methods" in result.stdout

    def test_methods_latex(self, run_dir):
        result = run_pubrun("methods", run_dir, "--format", "latex")
        assert result.returncode == 0
        assert "\\subsection" in result.stdout


class TestCliRerun:

    @pytest.fixture
    def run_dir(self, tmp_path):
        """Create a real run to test rerun command against."""
        from pubrun import start as pubrun_start
        import pubrun.tracker
        pubrun.tracker._active_run = None
        old_cwd = Path.cwd
        try:
            Path.cwd = staticmethod(lambda: tmp_path)
            tracker = pubrun_start()
            tracker.stop()
            return str(tracker.run_dir)
        finally:
            Path.cwd = old_cwd
            pubrun.tracker._active_run = None

    def test_rerun_prints_command(self, run_dir):
        result = run_pubrun("rerun", run_dir)
        assert result.returncode == 0
        assert "cd " in result.stdout or "python" in result.stdout


class TestCliDiff:

    @pytest.fixture
    def two_runs(self, tmp_path):
        """Create two runs to diff."""
        from pubrun import start as pubrun_start
        import pubrun.tracker

        dirs = []
        old_cwd = Path.cwd
        try:
            Path.cwd = staticmethod(lambda: tmp_path)
            for _ in range(2):
                pubrun.tracker._active_run = None
                tracker = pubrun_start()
                tracker.stop()
                dirs.append(str(tracker.run_dir))
        finally:
            Path.cwd = old_cwd
            pubrun.tracker._active_run = None
        return dirs

    def test_diff_two_valid_runs(self, two_runs):
        result = run_pubrun("diff", two_runs[0], two_runs[1])
        assert result.returncode == 0

    def test_diff_no_color(self, two_runs):
        result = run_pubrun("diff", two_runs[0], two_runs[1], "--no-color")
        assert result.returncode == 0

    def test_diff_export_txt(self, two_runs):
        result = run_pubrun("diff", two_runs[0], two_runs[1], "--export", "txt")
        assert result.returncode == 0

    def test_diff_export_json(self, two_runs):
        result = run_pubrun("diff", two_runs[0], two_runs[1], "--export", "json")
        assert result.returncode == 0

    def test_diff_invalid_paths(self, tmp_path):
        result = run_pubrun("diff", "/nonexistent/a", "/nonexistent/b")
        assert result.returncode != 0


class TestCliRunTests:

    def test_run_tests_exits_zero(self, tmp_path):
        result = run_pubrun("--run-tests", cwd=str(tmp_path))
        assert result.returncode == 0


class TestCliNoCommand:

    def test_no_args_prints_help(self):
        result = run_pubrun()
        # Should print help and exit 0 (no error)
        assert result.returncode == 0
        assert "pubrun" in result.stdout.lower() or "usage" in result.stdout.lower()


class TestCliErrorExitCodes:
    """Test that CLI commands exit 1 on error conditions."""

    def test_methods_missing_manifest_exits_1(self, tmp_path):
        """pubrun methods with non-existent run dir exits 1."""
        result = run_pubrun("methods", str(tmp_path / "nonexistent"), cwd=str(tmp_path))
        assert result.returncode == 1

    def test_rerun_missing_manifest_exits_1(self, tmp_path):
        """pubrun rerun with non-existent run dir exits 1."""
        result = run_pubrun("rerun", str(tmp_path / "nonexistent"), cwd=str(tmp_path))
        assert result.returncode == 1

    def test_rerun_manifest_without_rerun_command_exits_1(self, tmp_path):
        """pubrun rerun with a manifest lacking rerun_command exits 1."""
        run_dir = tmp_path / "runs" / "pubrun-test"
        run_dir.mkdir(parents=True)
        manifest = {"invocation": {"rerun_command": None}}
        (run_dir / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
        result = run_pubrun("rerun", str(run_dir), cwd=str(tmp_path))
        assert result.returncode == 1

    def test_diff_export_bad_format_exits_1(self, tmp_path):
        """pubrun diff --export badformat exits 1."""
        # Need two valid run dirs with manifests for diff to get to format check
        for name in ("a", "b"):
            d = tmp_path / name
            d.mkdir()
            (d / "manifest.json").write_text(json.dumps({
                "schema_version": "1.0", "manifest_type": "pubrun-manifest",
                "status": {"outcome": "completed"}
            }), encoding="utf-8")

        result = run_pubrun("diff", str(tmp_path / "a"), str(tmp_path / "b"),
                           "--export", "yaml", cwd=str(tmp_path))
        assert result.returncode == 1
        assert "unsupported" in result.stderr.lower() or "error" in result.stderr.lower()

    def test_status_nonexistent_run_id_exits_1(self, tmp_path):
        """pubrun status <nonexistent_id> exits 1."""
        result = run_pubrun("status", "zzzznonexistent", "--dir", str(tmp_path),
                           cwd=str(tmp_path))
        assert result.returncode == 1
        assert "no run found" in result.stderr.lower() or "error" in result.stderr.lower()

    def test_cite_unknown_style_exits_1(self, tmp_path):
        """pubrun cite --style unknown exits 1."""
        result = run_pubrun("cite", "--style", "unknown_style", cwd=str(tmp_path))
        # argparse rejects unknown choices with exit code 2
        assert result.returncode != 0

    def test_report_running_or_crashed_run(self, tmp_path):
        """pubrun report when the run is running or crashed (only has lock file)."""
        run_dir = tmp_path / "runs" / "pubrun-crashed"
        run_dir.mkdir(parents=True)
        # Create a mock lock file
        lock_data = {
            "run_id": "crashed-id",
            "pid": 99999,
            "started_at_utc": 1782000000.0,
            "script": "train.py",
            "args": ["--epochs", "10"],
            "hostname": "localhost"
        }
        with open(run_dir / ".pubrun.lock", "w", encoding="utf-8") as f:
            json.dump(lock_data, f)

        # Let's run `pubrun report` with the path
        result = run_pubrun("report", str(run_dir), cwd=str(tmp_path))
        assert result.returncode == 1
        assert "crashed" in result.stderr or "running" in result.stderr
        assert "crashed-id" in result.stderr
        assert "train.py" in result.stderr
        assert "localhost" in result.stderr

    def test_report_auto_detected_crashed_run_with_suggestion(self, tmp_path):
        """pubrun report auto-detection gets a crashed run and suggests the latest completed run."""
        # 1. Create a completed run
        completed_dir = tmp_path / "runs" / "pubrun-completed"
        completed_dir.mkdir(parents=True)
        manifest = {
            "schema_version": "1.0",
            "manifest_type": "pubrun-manifest",
            "run": {"run_id": "completed-id"},
            "status": {"outcome": "completed"}
        }
        with open(completed_dir / "manifest.json", "w", encoding="utf-8") as f:
            json.dump(manifest, f)

        # 2. Create a crashed run (more recent)
        crashed_dir = tmp_path / "runs" / "pubrun-crashed"
        crashed_dir.mkdir(parents=True)
        lock_data = {
            "run_id": "crashed-id",
            "pid": 99999,
            "started_at_utc": 1782000000.0,
            "script": "train.py",
            "args": ["--epochs", "10"],
            "hostname": "localhost"
        }
        with open(crashed_dir / ".pubrun.lock", "w", encoding="utf-8") as f:
            json.dump(lock_data, f)
        
        # Set mtime of crashed run to be greater
        import time
        os.utime(completed_dir, (time.time() - 100, time.time() - 100))
        os.utime(crashed_dir, (time.time(), time.time()))

        # Run report without arguments
        result = run_pubrun("report", cwd=str(tmp_path))
        assert result.returncode == 1
        assert "crashed" in result.stderr or "running" in result.stderr
        assert "Suggestion:" in result.stderr
        assert "pubrun-completed" in result.stderr


class TestCliColorControl:

    def test_status_no_color_env(self, tmp_path):
        # Create a run in tmp_path
        from pubrun import start as pubrun_start
        import pubrun.tracker
        pubrun.tracker._active_run = None
        old_cwd = Path.cwd
        try:
            Path.cwd = staticmethod(lambda: tmp_path)
            tracker = pubrun_start()
            tracker.stop()
        finally:
            Path.cwd = old_cwd
            pubrun.tracker._active_run = None
            
        # Run pubrun status WITH color (default)
        env_with_color = os.environ.copy()
        env_with_color.pop("NO_COLOR", None)
        cmd = [sys.executable, "-m", "pubrun", "status", "--dir", str(tmp_path / "runs")]
        res_color = subprocess.run(cmd, capture_output=True, text=True, env=env_with_color, cwd=str(tmp_path))
        
        # Run pubrun status WITHOUT color (env var)
        env_no_color = os.environ.copy()
        env_no_color["NO_COLOR"] = "1"
        res_no_color = subprocess.run(cmd, capture_output=True, text=True, env=env_no_color, cwd=str(tmp_path))
        
        # Run pubrun status WITHOUT color (global flag)
        cmd_flag = [sys.executable, "-m", "pubrun", "--no-color", "status", "--dir", str(tmp_path / "runs")]
        res_flag = subprocess.run(cmd_flag, capture_output=True, text=True, env=env_with_color, cwd=str(tmp_path))
        
        # Check that ANSI escape sequences are present in res_color and NOT in res_no_color/res_flag
        assert "\033[" in res_color.stdout
        assert "\033[" not in res_no_color.stdout
        assert "\033[" not in res_flag.stdout

    def test_report_no_color_any_position(self, tmp_path):
        # Create a run in tmp_path
        from pubrun import start as pubrun_start
        import pubrun.tracker
        pubrun.tracker._active_run = None
        old_cwd = Path.cwd
        try:
            Path.cwd = staticmethod(lambda: tmp_path)
            tracker = pubrun_start()
            tracker.stop()
        finally:
            Path.cwd = old_cwd
            pubrun.tracker._active_run = None

        run_dirs = list((tmp_path / "runs").glob("pubrun-*"))
        assert len(run_dirs) == 1
        run_dir = run_dirs[0]

        env_with_color = os.environ.copy()
        env_with_color.pop("NO_COLOR", None)

        # Run pubrun report <run_dir> --no-color (flag after subcommand args)
        cmd_report = [sys.executable, "-m", "pubrun", "report", str(run_dir), "--no-color"]
        res_report = subprocess.run(cmd_report, capture_output=True, text=True, env=env_with_color, cwd=str(tmp_path))
        assert res_report.returncode == 0
        assert "\033[" not in res_report.stdout

    def test_run_preserves_no_color_arg(self, tmp_path):
        cmd = [
            sys.executable, "-m", "pubrun", "run", "--", 
            sys.executable, "-c", "import sys; print(' '.join(sys.argv))", "arg1", "--no-color"
        ]
        res = subprocess.run(cmd, capture_output=True, text=True, cwd=str(tmp_path))
        assert res.returncode == 0
        assert "--no-color" in res.stdout

    def test_global_no_color_with_run_preserves_arg(self, tmp_path):
        cmd = [
            sys.executable, "-m", "pubrun", "--no-color", "run", "--", 
            sys.executable, "-c", "import sys; print(' '.join(sys.argv))", "arg1", "--no-color"
        ]
        res = subprocess.run(cmd, capture_output=True, text=True, cwd=str(tmp_path))
        assert res.returncode == 0
        assert "--no-color" in res.stdout


class TestCliReportUsabilityDetails:

    def test_report_failed_run_with_details(self, tmp_path):
        run_dir = tmp_path / "runs" / "pubrun-failed"
        run_dir.mkdir(parents=True)
        manifest = {
            "schema_version": "1.0",
            "manifest_type": "pubrun-manifest",
            "run": {"run_id": "failed-run-id"},
            "status": {"outcome": "failed"},
            "signals": {
                "exit_code": 1,
                "exit_exception": "ValueError: Invalid parameter",
                "signals_received": [
                    {"signal": 15, "signal_name": "SIGTERM", "timestamp_utc": 1234567.0}
                ]
            }
        }
        with open(run_dir / "manifest.json", "w", encoding="utf-8") as f:
            json.dump(manifest, f)

        # Print report WITH color
        env_with_color = os.environ.copy()
        env_with_color.pop("NO_COLOR", None)
        cmd = [sys.executable, "-m", "pubrun", "report", str(run_dir)]
        res_color = subprocess.run(cmd, capture_output=True, text=True, env=env_with_color)
        assert res_color.returncode == 0
        assert "PUBRUN DIAGNOSTICS" in res_color.stdout
        assert "failed" in res_color.stdout
        assert "Exit Code" in res_color.stdout
        assert "1" in res_color.stdout
        assert "Exception" in res_color.stdout
        assert "ValueError: Invalid parameter" in res_color.stdout
        assert "Signals" in res_color.stdout
        assert "SIGTERM" in res_color.stdout
        # Unicode box boundaries or fallback ASCII should be present
        if sys.platform == "win32":
            assert "┌" in res_color.stdout or "+" in res_color.stdout
            assert "└" in res_color.stdout or "+" in res_color.stdout
        else:
            assert "┌" in res_color.stdout
            assert "└" in res_color.stdout

        # Print report WITHOUT color
        env_no_color = os.environ.copy()
        env_no_color["NO_COLOR"] = "1"
        res_no_color = subprocess.run(cmd, capture_output=True, text=True, env=env_no_color)
        assert res_no_color.returncode == 0
        assert "PUBRUN DIAGNOSTICS" in res_no_color.stdout
        assert "Exit Code   : 1" in res_no_color.stdout
        assert "Exception   : ValueError: Invalid parameter" in res_no_color.stdout
        assert "Signals     : SIGTERM" in res_no_color.stdout
        # ASCII boundary instead of Unicode box
        assert "===" in res_no_color.stdout
        assert "┌" not in res_no_color.stdout
        # No ANSI escape codes
        assert "\033[" not in res_no_color.stdout

    def test_report_crashed_run_tails_stderr(self, tmp_path):
        from pubrun.capture.liveness import get_hostname
        current_host = get_hostname()
        run_dir = tmp_path / "runs" / "pubrun-crashed"
        run_dir.mkdir(parents=True)
        # Create a mock lock file to simulate crashed run
        lock_data = {
            "run_id": "crashed-id",
            "pid": 99999,
            "started_at_utc": 1782000000.0,
            "script": "train.py",
            "args": ["--epochs", "10"],
            "hostname": current_host
        }
        with open(run_dir / ".pubrun.lock", "w", encoding="utf-8") as f:
            json.dump(lock_data, f)

        # Write more than 10 lines to stderr.log
        stderr_lines = [f"Line {i}\n" for i in range(1, 15)]
        with open(run_dir / "stderr.log", "w", encoding="utf-8") as f:
            f.writelines(stderr_lines)

        # Run report
        cmd = [sys.executable, "-m", "pubrun", "report", str(run_dir)]
        res = subprocess.run(cmd, capture_output=True, text=True)
        assert res.returncode == 1
        assert "Error: Run directory 'pubrun-crashed' is currently crashed" in res.stderr
        assert "Last 10 lines of stderr.log:" in res.stderr
        # Check that we only see lines 5 to 14 (which are the last 10 lines)
        assert "Line 1\n" not in res.stderr
        assert "Line 4\n" not in res.stderr
        assert "Line 5\n" in res.stderr
        assert "Line 14\n" in res.stderr

    def test_report_crashed_run_tails_stdout_fallback(self, tmp_path):
        from pubrun.capture.liveness import get_hostname
        current_host = get_hostname()
        run_dir = tmp_path / "runs" / "pubrun-crashed-fallback"
        run_dir.mkdir(parents=True)
        # Create a mock lock file to simulate crashed run
        lock_data = {
            "run_id": "crashed-id",
            "pid": 99999,
            "started_at_utc": 1782000000.0,
            "script": "train.py",
            "args": ["--epochs", "10"],
            "hostname": current_host
        }
        with open(run_dir / ".pubrun.lock", "w", encoding="utf-8") as f:
            json.dump(lock_data, f)

        # Write more than 10 lines to stdout.log
        stdout_lines = [f"Out Line {i}\n" for i in range(1, 15)]
        with open(run_dir / "stdout.log", "w", encoding="utf-8") as f:
            f.writelines(stdout_lines)

        # Run report
        cmd = [sys.executable, "-m", "pubrun", "report", str(run_dir)]
        res = subprocess.run(cmd, capture_output=True, text=True)
        assert res.returncode == 1
        assert "Last 10 lines of stdout.log:" in res.stderr
        assert "Out Line 1\n" not in res.stderr
        assert "Out Line 4\n" not in res.stderr
        assert "Out Line 5\n" in res.stderr
        assert "Out Line 14\n" in res.stderr


class TestCliNewFeatures:

    def test_faulthandler_segfault_captured(self, tmp_path):
        script = f"""
import os, sys, ctypes
import pubrun
tracker = pubrun.start(profile="standard")
# trigger segfault
ctypes.string_at(0)
"""
        script_file = tmp_path / "segfault.py"
        script_file.write_text(script, encoding="utf-8")
        
        env = os.environ.copy()
        res = subprocess.run([sys.executable, str(script_file)], env=env, capture_output=True, text=True, cwd=str(tmp_path))
        
        runs_dir = tmp_path / "runs"
        assert runs_dir.exists()
        run_folders = list(runs_dir.iterdir())
        assert len(run_folders) == 1
        run_dir = run_folders[0]
        
        stderr_log = run_dir / "stderr.log"
        assert stderr_log.exists()
        content = stderr_log.read_text(encoding="utf-8")
        # Under different platforms/interpreters, faulthandler might dump different headers or tracebacks.
        # We assert either standard segfault output or string_at / ctypes reference.
        assert any(x in content for x in ("Segmentation fault", "string_at", "ctypes"))

    def test_excepthook_stream_flushing(self, tmp_path):
        script = f"""
import sys, pubrun
tracker = pubrun.start(profile="standard")
sys.stdout.write("FLUSH_TEST_STDOUT")
sys.stderr.write("FLUSH_TEST_STDERR")
raise ValueError("TEST_EXCEPTION")
"""
        script_file = tmp_path / "flushing.py"
        script_file.write_text(script, encoding="utf-8")
        
        env = os.environ.copy()
        subprocess.run([sys.executable, str(script_file)], env=env, capture_output=True, text=True, cwd=str(tmp_path))
        
        runs_dir = tmp_path / "runs"
        assert runs_dir.exists()
        run_dir = list(runs_dir.iterdir())[0]
        
        stdout_log = run_dir / "stdout.log"
        stderr_log = run_dir / "stderr.log"
        
        assert stdout_log.exists()
        assert stderr_log.exists()
        
        assert "FLUSH_TEST_STDOUT" in stdout_log.read_text(encoding="utf-8")
        assert "FLUSH_TEST_STDERR" in stderr_log.read_text(encoding="utf-8")
        assert "TEST_EXCEPTION" in stderr_log.read_text(encoding="utf-8")

    def test_status_filtering_options(self, tmp_path):
        runs_dir = tmp_path / "runs"
        runs_dir.mkdir(parents=True)
        
        # Create completed run
        run_completed = runs_dir / "pubrun-completed"
        run_completed.mkdir()
        (run_completed / "manifest.json").write_text(json.dumps({
            "schema_version": "1.0", "manifest_type": "pubrun-manifest",
            "run": {"run_id": "comp-id"},
            "status": {"outcome": "completed"},
            "invocation": {"script": {"basename": "train.py"}, "argv": ["train.py", "--lr", "0.01"]},
            "timing": {"started_at_utc": 1782000000.0}
        }), encoding="utf-8")
        
        # Create failed run
        run_failed = runs_dir / "pubrun-failed"
        run_failed.mkdir()
        (run_failed / "manifest.json").write_text(json.dumps({
            "schema_version": "1.0", "manifest_type": "pubrun-manifest",
            "run": {"run_id": "fail-id"},
            "status": {"outcome": "failed"},
            "invocation": {"script": {"basename": "eval.py"}, "argv": ["eval.py", "--batch", "32"]},
            "timing": {"started_at_utc": 1782000100.0}
        }), encoding="utf-8")

        # Create crashed run
        run_crashed = runs_dir / "pubrun-crashed"
        run_crashed.mkdir()
        (run_crashed / ".pubrun.lock").write_text(json.dumps({
            "run_id": "crash-id", "pid": 99999, "started_at_utc": 1782000200.0,
            "script": "preprocess.py", "argv": ["preprocess.py", "--split", "train"],
            "hostname": "otherhost"
        }), encoding="utf-8")

        # Verify status filter: completed
        cmd = [sys.executable, "-m", "pubrun", "status", "--dir", str(runs_dir), "--status", "completed"]
        res = subprocess.run(cmd, capture_output=True, text=True)
        assert res.returncode == 0
        assert "comp-id" in res.stdout
        assert "fail-id" not in res.stdout

        # Verify status filter: failed
        cmd = [sys.executable, "-m", "pubrun", "status", "--dir", str(runs_dir), "--status", "failed"]
        res = subprocess.run(cmd, capture_output=True, text=True)
        assert res.returncode == 0
        assert "fail-id" in res.stdout
        assert "comp-id" not in res.stdout

        # Verify limit: 1
        cmd = [sys.executable, "-m", "pubrun", "status", "--dir", str(runs_dir), "--limit", "1"]
        res = subprocess.run(cmd, capture_output=True, text=True)
        assert res.returncode == 0
        assert "crash-id" in res.stdout
        assert "fail-id" not in res.stdout
        assert "comp-id" not in res.stdout

        # Verify filter: "train"
        cmd = [sys.executable, "-m", "pubrun", "status", "--dir", str(runs_dir), "-f", "train"]
        res = subprocess.run(cmd, capture_output=True, text=True)
        assert res.returncode == 0
        assert "comp-id" in res.stdout
        assert "crash-id" in res.stdout
        assert "fail-id" not in res.stdout

    def test_subcommand_help_examples(self):
        for sub in ("report", "methods", "rerun", "diff", "meta", "status", "clean", "combined", "cite", "run", "tui"):
            cmd = [sys.executable, "-m", "pubrun", sub, "--help"]
            res = subprocess.run(cmd, capture_output=True, text=True)
            assert res.returncode == 0
            assert "Examples:" in res.stdout
            assert "pubrun " in res.stdout or "pbr " in res.stdout

    def test_pbr_alias_registered_in_pyproject(self):
        pyproject_path = Path(__file__).parent.parent / "pyproject.toml"
        assert pyproject_path.exists()
        content = pyproject_path.read_text(encoding="utf-8")
        assert 'pbr = "pubrun.__main__:main"' in content

    def test_pbr_me_easter_egg(self):
        # Invoke main directly with modified argv[0] and argv[1]
        import sys
        from unittest.mock import patch
        from pubrun.__main__ import main
        
        with patch.object(sys, 'argv', ['/path/to/pbr', 'me']):
            # Capture stdout
            import io
            from contextlib import redirect_stdout
            f = io.StringIO()
            with redirect_stdout(f):
                with pytest.raises(SystemExit) as exc_info:
                    main()
            assert exc_info.value.code == 0
            assert f.getvalue().strip() == "ASAP"

    def test_empty_invocation_shows_help_and_run_count(self):
        import sys
        from unittest.mock import patch
        from pubrun.__main__ import main
        
        with patch("pubrun.status.scan_runs") as mock_scan:
            mock_scan.return_value = [object()]
            
            with patch.object(sys, 'argv', ['pubrun']):
                import io
                from contextlib import redirect_stdout
                f = io.StringIO()
                with redirect_stdout(f):
                    main()
                output = f.getvalue()
                assert "usage: pubrun" in output or "usage: pbr" in output
                assert "Found 1 run(s) in the output directory." in output



