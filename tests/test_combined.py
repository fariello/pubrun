import pytest
import sys
import json
from pathlib import Path
from unittest.mock import patch
from pubrun.__main__ import _run_combined
from pubrun.status import scan_runs

def create_mock_run(runs_dir: Path, run_id: str, started_at: float, stdout_lines=None, stderr_lines=None):
    """Helper to create a mock run directory with logs and manifest."""
    run_dir = runs_dir / f"pubrun-mock-{started_at}-{run_id}"
    run_dir.mkdir(parents=True, exist_ok=True)

    # Write manifest
    manifest = {
        "run": {"run_id": run_id},
        "timing": {"started_at_utc": started_at, "ended_at_utc": started_at + 10.0, "elapsed_seconds": 10.0},
        "status": {"outcome": "completed"},
        "process": {"pid": 12345},
        "host": {"hostname": "localhost"}
    }
    with open(run_dir / "manifest.json", "w", encoding="utf-8") as f:
        json.dump(manifest, f)

    # Write stdout.log
    if stdout_lines is not None:
        with open(run_dir / "stdout.log", "w", encoding="utf-8") as f:
            for line in stdout_lines:
                f.write(line + "\n")

    # Write stderr.log
    if stderr_lines is not None:
        with open(run_dir / "stderr.log", "w", encoding="utf-8") as f:
            for line in stderr_lines:
                f.write(line + "\n")

    return run_dir

def test_combined_empty_runs(tmp_path):
    """If no runs exist, combined command exits with error."""
    runs_dir = tmp_path / "runs"
    runs_dir.mkdir()

    with pytest.raises(SystemExit) as excinfo:
        _run_combined([], dir_path=str(runs_dir), output=None, yes=True, force=False)
    assert excinfo.value.code == 1

def test_combined_latest_run_auto_detect(tmp_path, capsys):
    """If no run ID is supplied, defaults to the latest run."""
    runs_dir = tmp_path / "runs"

    # Create two runs: older and newer
    create_mock_run(runs_dir, "older", 1000.0, ["older line"])
    create_mock_run(runs_dir, "newer", 2000.0,
                    ["[2026-06-19T22:00:00.000Z] stdout line 1", "[2026-06-19T22:00:02.000Z] stdout line 2"],
                    ["[2026-06-19T22:00:01.000Z] stderr line 1"])

    # Run combined with no run ID
    _run_combined([], dir_path=str(runs_dir), output=None, yes=True, force=False)

    captured = capsys.readouterr()
    # It should automatically interleave the newer run
    expected = [
        "[stdout] [2026-06-19T22:00:00.000Z] stdout line 1",
        "[stderr] [2026-06-19T22:00:01.000Z] stderr line 1",
        "[stdout] [2026-06-19T22:00:02.000Z] stdout line 2"
    ]
    assert captured.out.strip().splitlines() == expected

def test_combined_multiple_runs(tmp_path, capsys):
    """Specifying multiple runs interleaves their streams chronologically and prefixes with run IDs."""
    runs_dir = tmp_path / "runs"

    create_mock_run(runs_dir, "runA", 1000.0,
                    ["[2026-06-19T22:00:00.000Z] A stdout 1", "[2026-06-19T22:00:03.000Z] A stdout 2"],
                    ["[2026-06-19T22:00:01.500Z] A stderr 1"])
    create_mock_run(runs_dir, "runB", 2000.0,
                    ["[2026-06-19T22:00:01.000Z] B stdout 1", "[2026-06-19T22:00:04.000Z] B stdout 2"])

    _run_combined(["runA", "runB"], dir_path=str(runs_dir), output=None, yes=True, force=False)

    captured = capsys.readouterr()
    expected = [
        "[runA][stdout] [2026-06-19T22:00:00.000Z] A stdout 1",
        "[runB][stdout] [2026-06-19T22:00:01.000Z] B stdout 1",
        "[runA][stderr] [2026-06-19T22:00:01.500Z] A stderr 1",
        "[runA][stdout] [2026-06-19T22:00:03.000Z] A stdout 2",
        "[runB][stdout] [2026-06-19T22:00:04.000Z] B stdout 2"
    ]
    assert captured.out.strip().splitlines() == expected

def test_combined_fallback_basic(tmp_path, capsys):
    """If logs lack timestamps (basic mode), falls back to sequential concatenation."""
    runs_dir = tmp_path / "runs"

    create_mock_run(runs_dir, "runC", 1000.0,
                    ["basic stdout line 1", "basic stdout line 2"],
                    ["basic stderr line 1"])

    _run_combined(["runC"], dir_path=str(runs_dir), output=None, yes=True, force=False)

    captured = capsys.readouterr()
    # Check warning on stderr
    assert "Warning: Logs lack timestamps. Falling back to sequential concatenation." in captured.err

    # Output should be sequential: stdout, then stderr
    expected = [
        "[stdout] basic stdout line 1",
        "[stdout] basic stdout line 2",
        "[stderr] basic stderr line 1"
    ]
    assert captured.out.strip().splitlines() == expected

def test_combined_write_to_file(tmp_path, capsys):
    """Output option writes combined logs to the specified file."""
    runs_dir = tmp_path / "runs"
    out_file = tmp_path / "combined.log"

    create_mock_run(runs_dir, "runD", 1000.0,
                    ["[2026-06-19T22:00:00.000Z] stdout line"])

    _run_combined(["runD"], dir_path=str(runs_dir), output=str(out_file), yes=True, force=False)

    captured = capsys.readouterr()
    assert "[ OK  ] Combined logs written to" in captured.err
    assert captured.out == ""

    assert out_file.exists()
    assert out_file.read_text("utf-8").strip() == "[stdout] [2026-06-19T22:00:00.000Z] stdout line"

def test_combined_size_checks_force(tmp_path):
    """Files > 500 MB require --force."""
    runs_dir = tmp_path / "runs"

    # Create large files (virtually by patching)
    create_mock_run(runs_dir, "runE", 1000.0, ["line"], ["line"])

    original_stat = Path.stat
    def mock_stat_func(self, *args, **kwargs):
        if self.name in ("stdout.log", "stderr.log"):
            class FakeStat:
                st_size = 300 * 1024 * 1024  # 300 MB each, total 600 MB
            return FakeStat()
        return original_stat(self, *args, **kwargs)

    with patch.object(Path, "stat", mock_stat_func):
        # Without force, should exit with 1
        with pytest.raises(SystemExit) as excinfo:
            _run_combined(["runE"], dir_path=str(runs_dir), output=None, yes=True, force=False)
        assert excinfo.value.code == 1

        # With force, should proceed (and skip prompt since yes=True)
        with patch("pubrun.__main__.open") as mock_open:
            # just mock to verify execution proceeds to reading
            mock_open.side_effect = Exception("Stop execution here")
            with pytest.raises(Exception, match="Stop execution here"):
                _run_combined(["runE"], dir_path=str(runs_dir), output=None, yes=True, force=True)

def test_combined_size_checks_warning_yes(tmp_path):
    """Files > 250 MB skip warning prompt if --yes is passed."""
    runs_dir = tmp_path / "runs"
    create_mock_run(runs_dir, "runF", 1000.0, ["line"], ["line"])

    original_stat = Path.stat
    def mock_stat_func(self, *args, **kwargs):
        if self.name in ("stdout.log", "stderr.log"):
            class FakeStat:
                st_size = 130 * 1024 * 1024  # 130 MB each, total 260 MB
            return FakeStat()
        return original_stat(self, *args, **kwargs)

    with patch.object(Path, "stat", mock_stat_func):
        # With yes=True, it should proceed (not try to call input())
        with patch("pubrun.__main__.open") as mock_open:
            mock_open.side_effect = Exception("Stop execution here")
            with pytest.raises(Exception, match="Stop execution here"):
                _run_combined(["runF"], dir_path=str(runs_dir), output=None, yes=True, force=False)

def test_combined_size_checks_warning_prompt_accept(tmp_path):
    """Files > 250 MB prompt user and proceed if accepted."""
    runs_dir = tmp_path / "runs"
    create_mock_run(runs_dir, "runG", 1000.0, ["line"], ["line"])

    original_stat = Path.stat
    def mock_stat_func(self, *args, **kwargs):
        if self.name in ("stdout.log", "stderr.log"):
            class FakeStat:
                st_size = 130 * 1024 * 1024  # 260 MB total
            return FakeStat()
        return original_stat(self, *args, **kwargs)

    with patch.object(Path, "stat", mock_stat_func):
        with patch("builtins.input", return_value="yes"):
            with patch("pubrun.__main__.open") as mock_open:
                mock_open.side_effect = Exception("Stop execution here")
                with pytest.raises(Exception, match="Stop execution here"):
                    _run_combined(["runG"], dir_path=str(runs_dir), output=None, yes=False, force=False)

def test_combined_size_checks_warning_prompt_reject(tmp_path):
    """Files > 250 MB prompt user and cancel if rejected."""
    runs_dir = tmp_path / "runs"
    create_mock_run(runs_dir, "runH", 1000.0, ["line"], ["line"])

    original_stat = Path.stat
    def mock_stat_func(self, *args, **kwargs):
        if self.name in ("stdout.log", "stderr.log"):
            class FakeStat:
                st_size = 130 * 1024 * 1024  # 260 MB total
            return FakeStat()
        return original_stat(self, *args, **kwargs)

    with patch.object(Path, "stat", mock_stat_func):
        with patch("builtins.input", return_value="no"):
            with pytest.raises(SystemExit) as excinfo:
                _run_combined(["runH"], dir_path=str(runs_dir), output=None, yes=False, force=False)
            assert excinfo.value.code == 0
