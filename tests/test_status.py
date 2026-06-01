"""Tests for pubrun.status and lock file mechanism."""
import json
import os
import sys
import time
from pathlib import Path

import pytest

from pubrun.tracker import Run


class TestLockFile:
    """Tests for the lock file lifecycle."""

    def test_lock_file_created_on_start(self):
        """A .pubrun.lock file is created when a run starts."""
        run = Run()
        lock_path = run.run_dir / Run.LOCK_FILENAME
        assert lock_path.exists()
        run.stop()

    def test_lock_file_contains_expected_fields(self):
        """Lock file JSON contains pid, started_at_utc, script, run_id, hostname."""
        run = Run()
        lock_path = run.run_dir / Run.LOCK_FILENAME
        with open(lock_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        assert data["pid"] == os.getpid()
        assert isinstance(data["started_at_utc"], float)
        assert data["run_id"] == run.run_id
        assert isinstance(data["hostname"], str)
        assert "cwd" in data
        run.stop()

    def test_lock_file_removed_on_stop(self):
        """Lock file is deleted when the run finalizes."""
        run = Run()
        lock_path = run.run_dir / Run.LOCK_FILENAME
        assert lock_path.exists()
        run.stop()
        assert not lock_path.exists()

    def test_lock_file_removed_on_atexit_finalization(self):
        """Lock file is removed when _finalize_state is called directly."""
        run = Run()
        lock_path = run.run_dir / Run.LOCK_FILENAME
        assert lock_path.exists()
        run._finalize_state()
        assert not lock_path.exists()
        # Clean up
        run.stop()

    @pytest.mark.skipif(sys.platform == "win32", reason="chmod 0o444 does not prevent writes on Windows")
    def test_ghost_mode_no_lock_file(self, monkeypatch, tmp_path):
        """Ghost mode does not create a lock file."""
        # Make the directory creation fail
        read_only = tmp_path / "readonly"
        read_only.mkdir()
        read_only.chmod(0o444)
        try:
            monkeypatch.setattr("pubrun.tracker.Path.cwd", lambda: tmp_path)
            run = Run(overrides={"core": {"output_dir": str(read_only / "runs")}})
            assert run._outcome == "ghost"
            assert run.signal_capture is None
        finally:
            read_only.chmod(0o755)


class TestStatusScan:
    """Tests for the status scanning and classification logic."""

    def test_scan_empty_directory(self, tmp_path):
        """Scanning an empty directory returns no runs."""
        from pubrun.status import scan_runs
        runs_dir = tmp_path / "runs"
        runs_dir.mkdir()
        result = scan_runs(str(runs_dir))
        assert result == []

    def test_scan_nonexistent_directory(self, tmp_path):
        """Scanning a directory that doesn't exist returns no runs."""
        from pubrun.status import scan_runs
        result = scan_runs(str(tmp_path / "nonexistent"))
        assert result == []

    def test_scan_completed_run(self):
        """A completed run is detected correctly."""
        from pubrun.status import scan_runs, STATUS_COMPLETED

        run = Run()
        run_dir = run.run_dir
        output_dir = str(run_dir.parent)
        run.stop()

        runs = scan_runs(output_dir)
        assert len(runs) == 1
        assert runs[0].status == STATUS_COMPLETED
        assert runs[0].run_id == run.run_id

    def test_scan_running_run(self):
        """A run with a lock file and live PID is classified as running."""
        from pubrun.status import scan_runs, STATUS_RUNNING

        run = Run()
        run_dir = run.run_dir
        output_dir = str(run_dir.parent)

        # Don't stop -- simulate an active run
        runs = scan_runs(output_dir)
        assert len(runs) == 1
        assert runs[0].status == STATUS_RUNNING
        assert runs[0].pid == os.getpid()

        # Clean up
        run.stop()

    def test_scan_crashed_run(self, tmp_path):
        """A run with a lock file but dead PID is classified as crashed."""
        from pubrun.status import scan_runs, STATUS_CRASHED

        # Create a fake run directory with a stale lock file
        run_dir = tmp_path / "runs" / "pubrun-test-20260531T000000Z-999999-abcd1234"
        run_dir.mkdir(parents=True)
        lock_data = {
            "pid": 999999,  # Very unlikely to be alive
            "started_at_utc": time.time() - 3600,
            "script": "test",
            "run_id": "abcd1234",
            "hostname": __import__("platform").node(),
            "git_commit": None,
            "cwd": str(tmp_path),
        }
        with open(run_dir / ".pubrun.lock", "w") as f:
            json.dump(lock_data, f)

        runs = scan_runs(str(tmp_path / "runs"))
        assert len(runs) == 1
        assert runs[0].status == STATUS_CRASHED
        assert runs[0].run_id == "abcd1234"

    def test_find_run_by_prefix(self):
        """find_run locates a run by ID prefix."""
        from pubrun.status import find_run

        run = Run()
        output_dir = str(run.run_dir.parent)
        run.stop()

        # Find by first 4 chars of run_id
        result = find_run(run.run_id[:4], output_dir)
        assert result is not None
        assert result.run_id == run.run_id

    def test_find_run_returns_none_for_no_match(self):
        """find_run returns None when no run matches."""
        from pubrun.status import find_run

        run = Run()
        output_dir = str(run.run_dir.parent)
        run.stop()

        result = find_run("zzzzzzzz", output_dir)
        assert result is None


class TestStatusRendering:
    """Tests for the status rendering functions."""

    def test_render_short_list_no_runs(self):
        """Short list with no runs shows a message."""
        from pubrun.status import render_short_list
        output = render_short_list([])
        assert "No runs found" in output

    def test_render_short_list_with_runs(self):
        """Short list renders a table with correct headers."""
        from pubrun.status import render_short_list, scan_runs

        run = Run()
        run.stop()
        output_dir = str(run.run_dir.parent)

        runs = scan_runs(output_dir)
        output = render_short_list(runs)
        assert "RUN ID" in output
        assert "SCRIPT" in output
        assert "STATUS" in output
        assert run.run_id[:8] in output

    def test_render_verbose_list_with_runs(self):
        """Verbose list renders detailed info per run."""
        from pubrun.status import render_verbose_list, scan_runs

        run = Run()
        run.stop()
        output_dir = str(run.run_dir.parent)

        runs = scan_runs(output_dir)
        output = render_verbose_list(runs)
        assert "Run ID:" in output
        assert "Directory:" in output
        assert run.run_id[:8] in output

    def test_render_inspect(self):
        """Inspect view shows detailed run information."""
        from pubrun.status import render_inspect, scan_runs

        run = Run()
        run.stop()
        output_dir = str(run.run_dir.parent)

        runs = scan_runs(output_dir)
        output = render_inspect(runs[0])
        assert run.run_id in output
        assert "Status:" in output
        assert "PID:" in output
        assert "Directory:" in output


class TestStatusCli:
    """Tests for the pubrun status CLI dispatch."""

    def test_status_help(self):
        """pubrun status --help exits 0."""
        import subprocess
        result = subprocess.run(
            ["python", "-m", "pubrun", "status", "--help"],
            capture_output=True, text=True
        )
        assert result.returncode == 0
        assert "status" in result.stdout.lower()

    def test_status_no_runs(self, tmp_path):
        """pubrun status with no runs prints 'No runs found'."""
        import subprocess
        result = subprocess.run(
            ["python", "-m", "pubrun", "status", "--dir", str(tmp_path)],
            capture_output=True, text=True
        )
        assert result.returncode == 0
        assert "No runs found" in result.stdout


class TestCleanRuns:
    """Tests for the pubrun clean functionality."""

    def test_clean_deletes_completed_runs(self):
        """clean_runs with yes=True deletes completed runs."""
        from pubrun.status import clean_runs

        # Create a run, stop it (completed)
        run = Run()
        run_dir = run.run_dir
        output_dir = str(run_dir.parent)
        run.stop()

        assert run_dir.exists()
        deleted = clean_runs(output_dir=output_dir, yes=True)
        assert deleted == 1
        assert not run_dir.exists()

    def test_clean_does_not_delete_running(self):
        """clean_runs never deletes running runs."""
        from pubrun.status import clean_runs

        run = Run()
        run_dir = run.run_dir
        output_dir = str(run_dir.parent)

        # Don't stop -- it's "running"
        deleted = clean_runs(output_dir=output_dir, yes=True)
        assert deleted == 0
        assert run_dir.exists()

        # Clean up
        run.stop()

    def test_clean_older_than_filter(self):
        """clean_runs with older_than_days filters out recent runs."""
        from pubrun.status import clean_runs

        run = Run()
        run_dir = run.run_dir
        output_dir = str(run_dir.parent)
        run.stop()

        # Run just created -- should not match "older than 1 day"
        deleted = clean_runs(output_dir=output_dir, older_than_days=1.0, yes=True)
        assert deleted == 0
        assert run_dir.exists()

    def test_clean_status_filter(self):
        """clean_runs with status_filter only deletes matching statuses."""
        from pubrun.status import clean_runs

        run = Run()
        run_dir = run.run_dir
        output_dir = str(run_dir.parent)
        run.stop()  # outcome = "completed"

        # Filter for "failed" only -- should not delete our "completed" run
        deleted = clean_runs(output_dir=output_dir, status_filter=["failed"], yes=True)
        assert deleted == 0
        assert run_dir.exists()

        # Now filter for "completed" -- should delete it
        deleted = clean_runs(output_dir=output_dir, status_filter=["completed"], yes=True)
        assert deleted == 1
        assert not run_dir.exists()

    def test_clean_dry_run_does_not_delete(self):
        """clean_runs with dry_run=True does not delete anything."""
        from pubrun.status import clean_runs

        run = Run()
        run_dir = run.run_dir
        output_dir = str(run_dir.parent)
        run.stop()

        deleted = clean_runs(output_dir=output_dir, yes=True, dry_run=True)
        assert deleted == 0
        assert run_dir.exists()  # Still exists

    def test_clean_no_candidates(self, tmp_path):
        """clean_runs with empty directory returns 0."""
        from pubrun.status import clean_runs

        runs_dir = tmp_path / "runs"
        runs_dir.mkdir()
        deleted = clean_runs(output_dir=str(runs_dir), yes=True)
        assert deleted == 0

    def test_clean_multiple_runs(self):
        """clean_runs deletes multiple completed runs."""
        from pubrun.status import clean_runs

        runs = []
        for _ in range(3):
            r = Run()
            runs.append(r)
            r.stop()

        output_dir = str(runs[0].run_dir.parent)
        deleted = clean_runs(output_dir=output_dir, yes=True)
        assert deleted == 3
        for r in runs:
            assert not r.run_dir.exists()

    def test_clean_running_filter_stripped(self):
        """Even if 'running' is in status_filter, running runs are not deleted."""
        from pubrun.status import clean_runs

        run = Run()
        run_dir = run.run_dir
        output_dir = str(run_dir.parent)

        # Explicitly include "running" in the filter
        deleted = clean_runs(output_dir=output_dir, status_filter=["running", "completed"], yes=True)
        assert deleted == 0
        assert run_dir.exists()

        run.stop()


class TestCleanCli:
    """Tests for the pubrun clean CLI command."""

    def test_clean_help(self):
        """pubrun clean --help exits 0."""
        import subprocess
        result = subprocess.run(
            ["python", "-m", "pubrun", "clean", "--help"],
            capture_output=True, text=True
        )
        assert result.returncode == 0
        assert "clean" in result.stdout.lower()
        assert "older-than" in result.stdout

    def test_clean_dry_run_cli(self, tmp_path):
        """pubrun clean --dry-run --dir <empty> shows no candidates."""
        import subprocess
        runs_dir = tmp_path / "runs"
        runs_dir.mkdir()
        result = subprocess.run(
            ["python", "-m", "pubrun", "clean", "--dir", str(runs_dir), "--dry-run"],
            capture_output=True, text=True
        )
        assert result.returncode == 0
        assert "No runs match" in result.stdout


class TestParseSelection:
    """Tests for the _parse_selection helper used by pubrun clean."""

    def test_single_number(self):
        from pubrun.status import _parse_selection
        items = ["a", "b", "c", "d", "e"]
        assert _parse_selection("3", items) == ["c"]

    def test_comma_separated(self):
        from pubrun.status import _parse_selection
        items = ["a", "b", "c", "d", "e"]
        assert _parse_selection("1,3,5", items) == ["a", "c", "e"]

    def test_range(self):
        from pubrun.status import _parse_selection
        items = ["a", "b", "c", "d", "e"]
        assert _parse_selection("2-4", items) == ["b", "c", "d"]

    def test_mixed_ranges_and_numbers(self):
        from pubrun.status import _parse_selection
        items = ["a", "b", "c", "d", "e"]
        assert _parse_selection("1-2,4", items) == ["a", "b", "d"]

    def test_out_of_bounds_skipped(self):
        from pubrun.status import _parse_selection
        items = ["a", "b", "c"]
        assert _parse_selection("1,99,2", items) == ["a", "b"]

    def test_invalid_input_returns_empty(self):
        from pubrun.status import _parse_selection
        items = ["a", "b", "c"]
        assert _parse_selection("xyz", items) == []

    def test_spaces_in_input(self):
        from pubrun.status import _parse_selection
        items = ["a", "b", "c", "d", "e"]
        assert _parse_selection("1, 3, 5", items) == ["a", "c", "e"]

    def test_empty_string(self):
        from pubrun.status import _parse_selection
        items = ["a", "b", "c"]
        assert _parse_selection("", items) == []

    def test_full_range(self):
        from pubrun.status import _parse_selection
        items = ["a", "b", "c", "d"]
        assert _parse_selection("1-4", items) == ["a", "b", "c", "d"]
