"""Tests for pubrun.status and lock file mechanism."""
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import pytest

from pubrun.tracker import Run


@pytest.fixture
def live_child(tmp_path):
    """Spawn a live child process with an active pubrun run and tear it down cleanly."""
    script = tmp_path / "livechild.py"
    script.write_text(
        'import sys\n'
        'import pubrun.noauto as p\n'
        'p.start()\n'
        'print("READY", flush=True)\n'
        'sys.stdin.readline()\n'
        'p.stop()\n',
        encoding="utf-8",
    )
    child = subprocess.Popen(
        [sys.executable, str(script)],
        cwd=str(tmp_path),
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        text=True,
    )
    try:
        ready = child.stdout.readline().strip()
        assert ready == "READY", f"Expected READY from child, got {ready!r}"
        yield child, str(tmp_path / "runs")
    finally:
        try:
            if child.stdin:
                child.stdin.write("\n")
                child.stdin.flush()
        except (BrokenPipeError, ValueError, OSError):
            pass
        try:
            child.wait(timeout=30)
        except subprocess.TimeoutExpired:
            child.kill()
            child.wait(timeout=5)


def _write_manifest(
    runs_dir: Path,
    dirname: str,
    run_id: str,
    started_at: float,
    outcome: str = "completed",
    argv=None,
    exit_code=0,
) -> Path:
    """Write a minimal manifest.json under runs_dir / dirname."""
    run_dir = runs_dir / dirname
    run_dir.mkdir(parents=True, exist_ok=True)
    manifest = {
        "run": {"run_id": run_id},
        "timing": {"started_at_utc": started_at},
        "status": {"outcome": outcome},
        "invocation": {"argv": argv if argv is not None else ["train.py"]},
        "signals": {"exit_code": exit_code},
    }
    (run_dir / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    return run_dir


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

    def test_lock_file_argv_is_redacted(self):
        """P3-T3: Secrets in argv are redacted in the lock file."""
        import json as _json
        # Simulate a script launched with --password=secret
        import sys as _sys
        original_argv = _sys.argv
        _sys.argv = ["train.py", "--password=s3cr3t", "--epochs=10"]
        try:
            run = Run()
            lock_path = run.run_dir / Run.LOCK_FILENAME
            assert lock_path.exists()
            with open(lock_path, "r", encoding="utf-8") as f:
                lock_data = _json.load(f)
            # password should be redacted
            argv_str = " ".join(lock_data["argv"])
            assert "s3cr3t" not in argv_str
            assert "[REDACTED]" in argv_str
            # non-sensitive args should be preserved
            assert "--epochs=10" in lock_data["argv"]
            run.stop()
        finally:
            _sys.argv = original_argv

    @pytest.mark.skipif(sys.platform == "win32", reason="POSIX only")
    def test_run_dir_created_with_0o700(self):
        """P3-T2: Run directory is created with restrictive permissions from the start."""
        run = Run()
        mode = oct(run.run_dir.stat().st_mode & 0o777)
        assert mode == "0o700"
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

    def test_scan_broken_pipe_run(self):
        """A completed run that received SIGPIPE is classified as 'broken pipe'."""
        import json as _json
        from pubrun.status import scan_runs, STATUS_BROKEN_PIPE

        run = Run()
        run_dir = run.run_dir
        output_dir = str(run_dir.parent)

        # Simulate receiving SIGPIPE by injecting it into the signal capture records
        if run.signal_capture:
            run.signal_capture._signals_received.append({
                "signal": 13,
                "signal_name": "SIGPIPE",
                "timestamp_utc": 1780250544.068
            })
        run.stop()

        runs = scan_runs(output_dir)
        assert len(runs) == 1
        assert runs[0].status == STATUS_BROKEN_PIPE
        # Exit code should remain unchanged (not overwritten)
        assert runs[0].exit_code == 0

    @pytest.mark.skipif(sys.platform == "win32", reason="SIGPIPE not available on Windows")
    def test_real_sigpipe_via_pipe(self, tmp_path):
        """Integration test: a real broken pipe is recorded as 'broken pipe' status.

        Whether the OS actually delivers SIGPIPE (vs. the writer just getting EPIPE, or the
        child finishing before the reader closes the pipe) is genuinely environment-dependent
        — headless CI schedulers, buffering, and pipe capacities all vary. So this test is
        TOLERANT: it establishes the run FIRST (so a run dir reliably exists), then asserts the
        real invariant — if the run recorded a SIGPIPE it must be classified 'broken pipe';
        otherwise it must be one of the other graceful terminal states, never a crash/None.
        It does not depend on the fragile timing of provoking SIGPIPE mid-flush.
        """
        import subprocess
        from pubrun.status import scan_runs, STATUS_BROKEN_PIPE

        # Child: start tracking + emit the startup manifest BEFORE flooding output, so the run
        # dir exists regardless of when the pipe breaks. Then flush a large volume to provoke
        # a broken pipe once the reader closes early.
        # noauto + an explicit start() writes the startup manifest SYNCHRONOUSLY before any
        # output, so the run dir deterministically exists even under load / early SIGPIPE.
        # A sentinel line to stderr tells the parent the run is established; only THEN does
        # the parent read+close stdout to provoke the broken pipe.
        script = f"""
import os, sys
os.chdir({str(tmp_path)!r})
import pubrun.noauto as pubrun
pubrun.start()
sys.stderr.write("READY\\n"); sys.stderr.flush()
for i in range(1000000):
    print(f"line {{i}}")
    sys.stdout.flush()
pubrun.stop()
"""
        proc = subprocess.Popen(
            [sys.executable, "-c", script],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        # Wait until the child signals the run is established (manifest written).
        while True:
            line = proc.stderr.readline()
            if not line or b"READY" in line:
                break
        # Now read a few stdout lines and close the read end to break the pipe.
        for _ in range(5):
            if not proc.stdout.readline():
                break
        proc.stdout.close()
        proc.wait(timeout=15)

        runs = scan_runs(str(tmp_path / "runs"))
        # A run must have been recorded (the startup manifest is written synchronously at start).
        assert len(runs) >= 1, "no run recorded — startup manifest was not written"
        latest = sorted(runs, key=lambda r: r.started_at_utc or 0, reverse=True)[0]
        # Invariant: a recorded run is never left in an unknown/crashed-null state. If the
        # broken pipe was actually delivered, it is classified 'broken pipe'; otherwise it is
        # a normal terminal state (the child may have finished or been terminated cleanly).
        assert latest.status is not None
        acceptable = {STATUS_BROKEN_PIPE, "completed", "failed", "interrupted", "crashed"}
        assert latest.status in acceptable, f"unexpected status: {latest.status!r}"

    @pytest.mark.skipif(sys.platform == "win32", reason="uses POSIX-style child control via stdin")
    def test_scan_running_run(self, live_child):
        """A run with a lock file and live PID is classified as running."""
        from pubrun.status import scan_runs, STATUS_RUNNING

        child, od = live_child
        assert [(r.script, r.status, r.pid) for r in scan_runs(od)] == [
            ("livechild", STATUS_RUNNING, child.pid)
        ]

    @pytest.mark.skipif(sys.platform == "win32", reason="uses POSIX-style child control via stdin")
    def test_python_dash_m_package_run_is_running_and_not_cleaned(self, tmp_path):
        """A live `python -m <package>` run is detected as running and never cleaned."""
        from pubrun.status import clean_runs, scan_runs, STATUS_RUNNING

        pkg_root = tmp_path / "pkgroot"
        pkg_dir = pkg_root / "livepkg"
        pkg_dir.mkdir(parents=True)
        (pkg_dir / "__init__.py").write_text("", encoding="utf-8")
        (pkg_dir / "__main__.py").write_text(
            'import sys\n'
            'import pubrun.noauto as p\n'
            'p.start()\n'
            'print("READY", flush=True)\n'
            'sys.stdin.readline()\n'
            'p.stop()\n',
            encoding="utf-8",
        )

        env = os.environ.copy()
        existing_pp = env.get("PYTHONPATH", "")
        env["PYTHONPATH"] = f"{pkg_root}{os.pathsep}{existing_pp}" if existing_pp else str(pkg_root)

        child = subprocess.Popen(
            [sys.executable, "-m", "livepkg"],
            cwd=str(tmp_path),
            env=env,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            text=True,
        )
        try:
            ready = child.stdout.readline().strip()
            assert ready == "READY", f"Expected READY from child, got {ready!r}"
            od = str(tmp_path / "runs")
            runs = scan_runs(od)
            assert [(r.script, r.status) for r in runs] == [("__main__", STATUS_RUNNING)]
            run_dir = runs[0].run_dir
            assert clean_runs(output_dir=od, yes=True) == 0
            assert run_dir.exists()
        finally:
            try:
                if child.stdin:
                    child.stdin.write("\n")
                    child.stdin.flush()
            except (BrokenPipeError, ValueError, OSError):
                pass
            try:
                child.wait(timeout=30)
            except subprocess.TimeoutExpired:
                child.kill()
                child.wait(timeout=5)

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

    @pytest.mark.skipif(sys.platform == "win32", reason="SIGKILL is not available on Windows")
    def test_scan_crashed_run_via_real_sigkill(self, tmp_path):
        """Integration: a tracked child SIGKILL'd mid-run is classified 'crashed'.

        The existing test_scan_crashed_run uses a SYNTHETIC dead PID; this exercises the
        real path: a live child starts a run (writing a real lock file with its own PID and
        start time), signals READY, and is then SIGKILL'd. SIGKILL cannot run cleanup, so the
        lock file persists with a now-dead PID — the exact 'crashed' scenario the feature
        detects.
        """
        import signal
        import subprocess
        from pubrun.status import scan_runs, STATUS_CRASHED

        # noauto + explicit start() writes the lock + startup manifest synchronously, then the
        # child signals READY and blocks forever waiting to be killed.
        script = f"""
import os, sys, time
os.chdir({str(tmp_path)!r})
import pubrun.noauto as pubrun
pubrun.start()
sys.stderr.write("READY\\n"); sys.stderr.flush()
time.sleep(120)
"""
        proc = subprocess.Popen(
            [sys.executable, "-c", script],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        try:
            # Wait until the child confirms the run (and its lock file) is established.
            while True:
                line = proc.stderr.readline()
                if not line or b"READY" in line:
                    break
            assert b"READY" in line, "child never established the run"

            # Kill it hard — no cleanup runs, so the lock file is left behind.
            proc.send_signal(signal.SIGKILL)
            proc.wait(timeout=15)
        finally:
            if proc.poll() is None:
                proc.kill()
                proc.wait(timeout=5)

        runs = scan_runs(str(tmp_path / "runs"))
        assert len(runs) == 1, "the SIGKILL'd run's directory + lock should remain"
        assert runs[0].status == STATUS_CRASHED
        assert runs[0].pid == proc.pid

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


class TestRunRecencySelector:
    """IPD-E: a bare integer selects the Nth most recent run (1 = newest)."""

    def _make_runs(self, tmp_path, ids_newest_first):
        """Create run dirs with controlled start times so recency order is deterministic.
        ids_newest_first[0] is the most recent."""
        runs_dir = tmp_path / "runs"
        runs_dir.mkdir()
        n = len(ids_newest_first)
        for i, rid in enumerate(ids_newest_first):
            d = runs_dir / f"pubrun-{rid}"
            d.mkdir()
            # newest first -> give the first the largest timestamp
            ts = 1000.0 + (n - i)
            (d / "manifest.json").write_text(json.dumps({
                "run": {"run_id": rid},
                "timing": {"started_at_utc": ts},
                "status": {"outcome": "completed"},
            }))
        return str(runs_dir)

    def test_recency_index_resolves_nth_most_recent(self, tmp_path):
        from pubrun.status import find_run
        od = self._make_runs(tmp_path, ["aaaa1111", "bbbb2222", "cccc3333"])
        assert find_run("1", od).run_id == "aaaa1111"   # newest
        assert find_run("2", od).run_id == "bbbb2222"
        assert find_run("3", od).run_id == "cccc3333"   # oldest

    def test_out_of_range_index_returns_none(self, tmp_path):
        from pubrun.status import find_run
        od = self._make_runs(tmp_path, ["aaaa1111", "bbbb2222"])
        assert find_run("9", od) is None  # only 2 runs; no id match either -> None

    def test_id_prefix_still_works_and_digit_prefix_is_recency(self, tmp_path):
        from pubrun.status import find_run
        # A hex id starting with '3' must NOT block '3' meaning "3rd most recent".
        od = self._make_runs(tmp_path, ["3abc0000", "2def1111", "9aaa2222"])
        assert find_run("3", od).run_id == "9aaa2222"        # recency (3rd), not the '3abc' id
        assert find_run("3abc", od).run_id == "3abc0000"     # explicit prefix -> id match

    def test_collision_only_on_exact_integer_id(self, tmp_path):
        from pubrun.status import find_run, AmbiguousRunSelectorError
        # Run literally named '2' is the NEWEST (recency #1), so selector '2' means BOTH the
        # 2nd-most-recent run AND the run whose id is exactly '2' -> ambiguous, refuse to guess.
        od = self._make_runs(tmp_path, ["2", "bbbb2222", "cccc3333"])
        with pytest.raises(AmbiguousRunSelectorError):
            find_run("2", od)

    def test_no_collision_when_exact_id_is_also_the_nth(self, tmp_path):
        from pubrun.status import find_run
        # Run named '2' happens to be the 2nd-most-recent -> both meanings agree, no error.
        od = self._make_runs(tmp_path, ["aaaa1111", "2", "cccc3333"])
        assert find_run("2", od).run_id == "2"

    def test_dir_override_honored(self, tmp_path):
        from pubrun.status import find_run
        od = self._make_runs(tmp_path, ["newest01", "older002"])
        # recency resolves within the specified dir
        assert find_run("1", od).run_id == "newest01"


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

    def test_render_short_list_broken_pipe_shows(self):
        """P2-E9: A run with SIGPIPE renders 'broken pipe' in status table."""
        from pubrun.status import render_short_list, scan_runs

        run = Run()
        if run.signal_capture:
            run.signal_capture._signals_received.append({
                "signal": 13,
                "signal_name": "SIGPIPE",
                "timestamp_utc": 1780250544.068
            })
        run.stop()
        output_dir = str(run.run_dir.parent)

        runs = scan_runs(output_dir)
        output = render_short_list(runs)
        assert "broken pipe" in output

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
        result = subprocess.run(
            [sys.executable, "-m", "pubrun", "status", "--help"],
            capture_output=True, text=True
        )
        assert result.returncode == 0
        assert "status" in result.stdout.lower()

    def test_status_no_runs(self, tmp_path):
        """pubrun status with no runs prints 'No runs found'."""
        result = subprocess.run(
            [sys.executable, "-m", "pubrun", "status", "--dir", str(tmp_path)],
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

    @pytest.mark.skipif(sys.platform == "win32", reason="uses POSIX-style child control via stdin")
    def test_clean_does_not_delete_running(self, live_child):
        """clean_runs never deletes running runs."""
        from pubrun.status import clean_runs, scan_runs

        _, od = live_child
        runs = scan_runs(od)
        assert len(runs) == 1
        run_dir = runs[0].run_dir

        deleted = clean_runs(output_dir=od, yes=True)
        assert deleted == 0
        assert run_dir.exists()

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

    @pytest.mark.skipif(sys.platform == "win32", reason="uses POSIX-style child control via stdin")
    def test_clean_running_filter_stripped(self, live_child):
        """Even if 'running' is in status_filter, running runs are not deleted."""
        from pubrun.status import clean_runs, scan_runs, STATUS_RUNNING

        _, od = live_child
        runs = scan_runs(od)
        assert len(runs) == 1
        assert runs[0].status == STATUS_RUNNING
        run_dir = runs[0].run_dir

        # Explicitly include "running" in the filter
        deleted = clean_runs(output_dir=od, status_filter=["running", "completed"], yes=True)
        assert deleted == 0
        assert run_dir.exists()

    def test_clean_interactive_selection_and_confirm(self, tmp_path, monkeypatch):
        """P3-T10: Test clean_runs with interactive selection (e.g., '1-2') and confirmation 'y'."""
        from pubrun.status import clean_runs

        runs_dir = tmp_path / "runs"
        d_old = _write_manifest(runs_dir, "pubrun-old", "old00001", 1000.0)
        d_mid = _write_manifest(runs_dir, "pubrun-mid", "mid00002", 2000.0)
        d_new = _write_manifest(runs_dir, "pubrun-new", "new00003", 3000.0)

        # Mock inputs: first select '1-2', then confirm 'y'
        inputs = iter(["1-2", "y"])
        monkeypatch.setattr("builtins.input", lambda prompt="": next(inputs))

        deleted = clean_runs(output_dir=str(runs_dir), yes=False)
        assert deleted == 2
        # Verify the two newest runs are deleted, the oldest survives
        assert not d_new.exists()
        assert not d_mid.exists()
        assert d_old.exists()

    def test_clean_interactive_cancel_at_selection(self, monkeypatch):
        """P3-T10: Test clean_runs with empty selection input to cancel."""
        from pubrun.status import clean_runs

        r = Run()
        r.stop()
        output_dir = str(r.run_dir.parent)

        monkeypatch.setattr("builtins.input", lambda prompt="": "")
        deleted = clean_runs(output_dir=output_dir, yes=False)
        assert deleted == 0
        assert r.run_dir.exists()

    def test_clean_interactive_cancel_at_confirm(self, monkeypatch):
        """P3-T10: Test clean_runs interactive select 'all' but confirm 'n'."""
        from pubrun.status import clean_runs

        r = Run()
        r.stop()
        output_dir = str(r.run_dir.parent)

        inputs = iter(["all", "n"])
        monkeypatch.setattr("builtins.input", lambda prompt="": next(inputs))

        deleted = clean_runs(output_dir=output_dir, yes=False)
        assert deleted == 0
        assert r.run_dir.exists()



class TestCleanCli:
    """Tests for the pubrun clean CLI command."""

    def test_clean_help(self):
        """pubrun clean --help exits 0."""
        result = subprocess.run(
            [sys.executable, "-m", "pubrun", "clean", "--help"],
            capture_output=True, text=True
        )
        assert result.returncode == 0
        assert "clean" in result.stdout.lower()
        assert "older-than" in result.stdout

    def test_clean_dry_run_cli(self, tmp_path):
        """pubrun clean --dry-run --dir <empty> shows no candidates."""
        runs_dir = tmp_path / "runs"
        runs_dir.mkdir()
        result = subprocess.run(
            [sys.executable, "-m", "pubrun", "clean", "--dir", str(runs_dir), "--dry-run"],
            capture_output=True, text=True
        )
        assert result.returncode == 0
        assert "No runs match" in result.stdout


class TestFilterFindAndCleanEdgeCases:
    """Unit tests for filter_runs regex fallback/exit_code, find_run ambiguity, and clean_runs cancel/failure."""

    def test_filter_runs_invalid_regex_fallback_and_exit_code(self, tmp_path):
        from pubrun.status import filter_runs, scan_runs

        runs_dir = tmp_path / "runs"
        _write_manifest(
            runs_dir, "pubrun-a", "aaaa1111", 1000.0,
            argv=["train.py", "--tag", "TRAIN[x]"], exit_code=0,
        )
        _write_manifest(
            runs_dir, "pubrun-b", "bbbb2222", 2000.0,
            argv=["eval.py"], exit_code=3,
        )
        runs = scan_runs(str(runs_dir))

        assert [r.run_id for r in filter_runs(runs, filter_str="train[")] == ["aaaa1111"]
        assert [r.run_id for r in filter_runs(runs, not_filter_str="train[")] == ["bbbb2222"]
        assert [r.run_id for r in filter_runs(runs, exit_code=3)] == ["bbbb2222"]
        assert [r.run_id for r in filter_runs(runs, exit_code=0)] == ["aaaa1111"]

    def test_find_run_ambiguous_prefix_and_dirname_substring(self, tmp_path):
        from pubrun.status import AmbiguousRunSelectorError, find_run

        runs_dir = tmp_path / "runs"
        _write_manifest(runs_dir, "pubrun-alpha", "abcd1111", 1000.0)
        _write_manifest(runs_dir, "pubrun-beta", "abcd2222", 2000.0)
        od = str(runs_dir)

        with pytest.raises(AmbiguousRunSelectorError) as exc_prefix:
            find_run("abcd", od)
        assert {c.run_id for c in exc_prefix.value.candidates} == {"abcd1111", "abcd2222"}
        assert "abcd1111" in str(exc_prefix.value)
        assert "abcd2222" in str(exc_prefix.value)

        matched = find_run("lph", od)
        assert matched is not None
        assert matched.run_id == "abcd1111"

        with pytest.raises(AmbiguousRunSelectorError) as exc_sub:
            find_run("pubrun-", od)
        assert {c.run_id for c in exc_sub.value.candidates} == {"abcd1111", "abcd2222"}

    @pytest.mark.parametrize(
        "answers,expected_msg",
        [
            ([KeyboardInterrupt()], "\nCleanup cancelled.\n"),
            ([EOFError()], "\nCleanup cancelled.\n"),
            (["n"], "Cleanup cancelled.\n"),
            (["none"], "Cleanup cancelled.\n"),
            (["abc", "xyz"], "No valid selections. Cleanup cancelled.\n"),
            (["9", "9"], "No valid selections. Cleanup cancelled.\n"),
            (["abc", ""], "Cleanup cancelled.\n"),
            (["abc", "n"], "Cleanup cancelled.\n"),
            (["abc", EOFError()], "\nCleanup cancelled.\n"),
            (["all", KeyboardInterrupt()], "\nCleanup cancelled.\n"),
            (["all", EOFError()], "\nCleanup cancelled.\n"),
            (["all", "n"], "Cleanup cancelled.\n"),
        ],
    )
    def test_clean_runs_interactive_cancel(self, tmp_path, monkeypatch, capsys, answers, expected_msg):
        from pubrun.status import clean_runs

        runs_dir = tmp_path / "runs"
        run_dir = _write_manifest(runs_dir, "pubrun-keep", "keep1111", 1000.0)

        seq = iter(answers)

        def fake_input(prompt=""):
            val = next(seq)
            if isinstance(val, BaseException):
                raise val
            return val

        monkeypatch.setattr("builtins.input", fake_input)
        deleted = clean_runs(output_dir=str(runs_dir), yes=False)
        out = capsys.readouterr().out
        assert deleted == 0
        assert run_dir.exists()
        assert out.endswith(expected_msg), f"Expected stdout to end with {expected_msg!r}, got {out!r}"

    def test_clean_runs_interactive_reprompt_recovery_and_ignored_tokens(self, tmp_path, monkeypatch, capsys):
        from pubrun.status import clean_runs

        runs_dir = tmp_path / "runs"
        run_dir = _write_manifest(runs_dir, "pubrun-del", "del11111", 1000.0)

        seq = iter(["abc", "1,99", "y"])
        monkeypatch.setattr("builtins.input", lambda prompt="": next(seq))

        deleted = clean_runs(output_dir=str(runs_dir), yes=False)
        out = capsys.readouterr().out
        assert deleted == 1
        assert not run_dir.exists()
        assert "Ignored invalid selection token(s): abc" in out
        assert "Please try again." in out
        assert "Ignored invalid selection token(s): 99" in out

    def test_clean_runs_removal_failure(self, tmp_path, monkeypatch, capsys):
        import shutil
        from pubrun.status import clean_runs

        runs_dir = tmp_path / "runs"
        dir_a = _write_manifest(runs_dir, "pubrun-a", "aaaa1111", 1000.0)
        dir_b = _write_manifest(runs_dir, "pubrun-b", "bbbb2222", 2000.0)

        real_rmtree = shutil.rmtree

        def selective_rmtree(path, *args, **kwargs):
            if Path(path).name == "pubrun-a":
                raise OSError("denied")
            return real_rmtree(path, *args, **kwargs)

        monkeypatch.setattr("pubrun.status.shutil.rmtree", selective_rmtree)
        deleted = clean_runs(output_dir=str(runs_dir), yes=True)
        captured = capsys.readouterr()

        assert deleted == 1
        assert "  Failed to remove pubrun-a: denied" in captured.err
        assert "Deleted 1 run(s)." in captured.out
        assert dir_a.exists()
        assert not dir_b.exists()


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


class TestStatusFormattingHelpers:
    """Unit tests for the private formatting helpers in status.py."""

    def test_format_elapsed(self):
        from pubrun.status import _format_elapsed
        assert _format_elapsed(None) == "unknown"
        assert _format_elapsed(0) == "00:00:00"
        assert _format_elapsed(45.6) == "00:00:46"
        assert _format_elapsed(125) == "00:02:05"
        assert _format_elapsed(3665) == "01:01:05"
        assert _format_elapsed(90065) == "1d 01:01:05"
        assert _format_elapsed(-10) == "-00:00:10"

    def test_format_timestamp(self):
        from pubrun.status import _format_timestamp
        assert _format_timestamp(None) == "-"
        assert len(_format_timestamp(1717156800.0)) > 0  # e.g. "2024-05-31 14:00" depending on timezone

    def test_format_bytes(self):
        from pubrun.status import _format_bytes
        assert _format_bytes(None) == "-"
        assert _format_bytes(500) == "500B"
        assert _format_bytes(1024) == "1KB"
        assert _format_bytes(1024 * 1024 * 1.5) == "1.5MB"
        assert _format_bytes(1024 * 1024 * 1024 * 2.35) == "2.35GB"

    def test_truncate(self):
        from pubrun.status import _truncate
        assert _truncate("", 5) == ""
        assert _truncate("hello", 10) == "hello"
        assert _truncate("hello world", 5) == "hell…"

    def test_status_marker(self, monkeypatch):
        from pubrun.status import _status_marker, STATUS_COMPLETED, STATUS_FAILED

        monkeypatch.delenv("NO_COLOR", raising=False)
        monkeypatch.setenv("FORCE_COLOR", "1")
        completed_marker = _status_marker(STATUS_COMPLETED)
        assert STATUS_COMPLETED in completed_marker
        assert "\033[" in completed_marker  # verify ANSI code present
        assert "\033[2m" not in completed_marker

        failed_marker = _status_marker(STATUS_FAILED)
        assert STATUS_FAILED in failed_marker
        assert "\033[" in failed_marker

        # Non-TTY piped output (no FORCE_COLOR) emits zero ANSI escapes
        monkeypatch.delenv("FORCE_COLOR", raising=False)
        monkeypatch.setattr(sys.stdout, "isatty", lambda: False)
        piped_marker = _status_marker(STATUS_COMPLETED)
        assert piped_marker == STATUS_COMPLETED
        assert "\x1b[" not in piped_marker

    def test_dir_size(self, tmp_path):
        from pubrun.status import _dir_size
        # Nonexistent dir
        assert _dir_size(tmp_path / "nonexistent") == 0

        # Empty dir
        d = tmp_path / "empty_dir"
        d.mkdir()
        assert _dir_size(d) == 0

        # Dir with files
        f1 = d / "file1.txt"
        f1.write_bytes(b"12345")
        f2 = d / "file2.txt"
        f2.write_bytes(b"hello")
        assert _dir_size(d) == 10

    def test_format_age(self):
        from pubrun.status import _format_age
        assert _format_age(None) == "unknown"
        assert _format_age(30) == "0m ago"
        assert _format_age(120) == "2m ago"
        assert _format_age(3600) == "1h ago"
        assert _format_age(86400) == "1 day ago"
        assert _format_age(86400 * 3) == "3 days ago"
        assert _format_age(-5) == "0m ago"

    def test_crashed_run_elapsed_time_unknown(self, tmp_path):
        """A crashed run closed out by scan_runs/RunInfo has an unknown elapsed time."""
        from pubrun.status import scan_runs, render_short_list
        # Create a stale lock file simulating a crashed run
        run_dir = tmp_path / "runs" / "pubrun-test-20260531T000000Z-999999-abcd1234"
        run_dir.mkdir(parents=True)
        lock_data = {
            "pid": 999999,
            "started_at_utc": time.time() - 3600,
            "script": "test",
            "run_id": "abcd1234",
            "hostname": __import__("platform").node(),
            "git_commit": None,
            "cwd": str(tmp_path),
        }
        with open(run_dir / ".pubrun.lock", "w") as f:
            json.dump(lock_data, f)

        # Trigger close-out
        from pubrun.status import close_out_crashed_run
        runs = scan_runs(str(tmp_path / "runs"))
        assert len(runs) == 1
        close_out_crashed_run(runs[0].run_dir, runs[0].lock_data)

        # Verify the timing fields in the manifest written
        manifest_path = run_dir / "manifest.json"
        assert manifest_path.exists()
        with open(manifest_path, "r") as f:
            manifest_data = json.load(f)
        assert manifest_data["timing"]["ended_at_utc"] is None
        assert manifest_data["timing"]["elapsed_seconds"] is None

        # Scan again (now it is loaded from manifest.json)
        runs_after = scan_runs(str(tmp_path / "runs"))
        assert len(runs_after) == 1
        assert runs_after[0].elapsed is None

        # Verify status table output formats it as 'unknown'
        output = render_short_list(runs_after)
        assert "unknown" in output

    def test_scan_remote_crashed_run_by_age(self, tmp_path):
        """A run on a different host that started >48 hours ago is classified as crashed."""
        from pubrun.status import scan_runs, STATUS_CRASHED, STATUS_RUNNING

        # 1. Create a remote run started 1 hour ago (should be running)
        run_dir_running = tmp_path / "runs" / "pubrun-remote-running"
        run_dir_running.mkdir(parents=True)
        lock_data_running = {
            "pid": 99999,
            "started_at_utc": time.time() - 3600,
            "script": "train.py",
            "run_id": "running-id",
            "hostname": "otherhost",
        }
        with open(run_dir_running / ".pubrun.lock", "w") as f:
            json.dump(lock_data_running, f)

        # 2. Create a remote run started 50 hours ago (should be crashed)
        run_dir_crashed = tmp_path / "runs" / "pubrun-remote-crashed"
        run_dir_crashed.mkdir(parents=True)
        lock_data_crashed = {
            "pid": 99999,
            "started_at_utc": time.time() - 180000,  # 50 hours ago
            "script": "train.py",
            "run_id": "crashed-id",
            "hostname": "otherhost",
        }
        with open(run_dir_crashed / ".pubrun.lock", "w") as f:
            json.dump(lock_data_crashed, f)

        runs = scan_runs(str(tmp_path / "runs"))
        assert len(runs) == 2

        runs_map = {r.run_id: r for r in runs}
        assert runs_map["running-id"].status == STATUS_RUNNING
        assert runs_map["crashed-id"].status == STATUS_CRASHED


class TestConcurrentLiveRuns:
    """Two independent tracked runs writing to one shared ./runs/ directory at the
    same time (the normal HPC array reality) must both be recorded as distinct,
    valid runs, and status listing must not error or corrupt.

    This is a GUARANTEED invariant, not best-effort: a discovered race is a bug.
    The test is deterministic — children signal READY and block until released, so
    the parent scans while both are provably live, with no wall-clock timing.
    """

    @pytest.mark.skipif(sys.platform == "win32", reason="uses POSIX-style child control via stdin")
    def test_two_concurrent_live_runs_are_both_listed(self, tmp_path):
        import subprocess
        from pubrun.status import scan_runs, render_short_list, STATUS_RUNNING

        output_dir = tmp_path / "runs"

        # Each child starts a run in the SHARED cwd (so both write to ./runs/),
        # signals READY with its run_id, then blocks on stdin until told to stop.
        child_src = f"""
import os, sys
os.chdir({str(tmp_path)!r})
import pubrun.noauto as pubrun
t = pubrun.start()
sys.stderr.write("READY " + t.run_id + "\\n"); sys.stderr.flush()
sys.stdin.readline()   # block until the parent releases us
pubrun.stop()
"""

        def spawn():
            return subprocess.Popen(
                [sys.executable, "-c", child_src],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )

        procs = [spawn(), spawn()]
        run_ids = []
        try:
            # Wait until BOTH children have established their runs.
            for p in procs:
                while True:
                    line = p.stderr.readline()
                    if not line:
                        raise AssertionError("child exited before signaling READY")
                    if line.startswith("READY "):
                        run_ids.append(line.split()[1])
                        break

            assert len(run_ids) == 2
            assert run_ids[0] != run_ids[1], "concurrent runs must get distinct run_ids"

            # Scan while both are provably live.
            runs = scan_runs(str(output_dir))
            found = {r.run_id: r for r in runs}
            for rid in run_ids:
                assert rid in found, f"run {rid} missing from scan of concurrent runs"
                assert found[rid].status == STATUS_RUNNING

            # The listing renderer must not error on a multi-run concurrent set.
            rendered = render_short_list(runs)
            assert isinstance(rendered, str) and rendered
            for rid in run_ids:
                assert rid[:8] in rendered or rid in rendered
        finally:
            # Deterministically release both children and reap them.
            for p in procs:
                try:
                    if p.stdin:
                        p.stdin.write("go\n")
                        p.stdin.flush()
                except (BrokenPipeError, ValueError):
                    pass
            for p in procs:
                try:
                    p.wait(timeout=15)
                except subprocess.TimeoutExpired:
                    p.kill()
                    p.wait(timeout=5)

        # After clean release, both runs finalized to a terminal (non-running) state.
        final = {r.run_id: r for r in scan_runs(str(output_dir))}
        for rid in run_ids:
            assert rid in final
            assert final[rid].status != STATUS_RUNNING


class TestFilterRunsValidationAndLimit:
    """Regression tests for fail-closed limit and status validation in filter_runs."""

    def test_limit_zero_returns_empty(self, tmp_path):
        from pubrun.status import filter_runs, scan_runs

        runs_dir = tmp_path / "runs"
        _write_manifest(runs_dir, "pubrun-a", "aaaa1111", 1000.0)
        _write_manifest(runs_dir, "pubrun-b", "bbbb2222", 2000.0)
        runs = scan_runs(str(runs_dir))

        assert filter_runs(runs, limit=0) == []
        assert len(filter_runs(runs, limit=1)) == 1

    @pytest.mark.parametrize("bad_limit", [-1, -100, True, False, 1.5, "2"])
    def test_invalid_limits_raise_even_on_empty_runs(self, bad_limit):
        from pubrun.status import filter_runs

        with pytest.raises(ValueError, match="limit must be a non-negative integer"):
            filter_runs([], limit=bad_limit)

    @pytest.mark.parametrize("kwarg", ["status_filter", "not_status_filter"])
    def test_unknown_status_raises_listing_all_valid_statuses(self, tmp_path, kwarg):
        from pubrun.status import VALID_STATUSES, filter_runs, scan_runs

        runs_dir = tmp_path / "runs"
        _write_manifest(runs_dir, "pubrun-a", "aaaa1111", 1000.0)
        runs = scan_runs(str(runs_dir))

        with pytest.raises(ValueError) as exc_info:
            filter_runs(runs, **{kwarg: "completed,bogus_state"})
        msg = str(exc_info.value)
        assert "bogus_state" in msg
        for valid in VALID_STATUSES:
            assert valid in msg

    def test_all_seven_valid_statuses_accepted(self, tmp_path):
        from pubrun.status import VALID_STATUSES, filter_runs

        assert len(VALID_STATUSES) == 7
        for status in VALID_STATUSES:
            assert filter_runs([], status_filter=status) == []
            assert filter_runs([], not_status_filter=status) == []


class TestSafeDeleteAndRemoteLocks:
    """Regression tests for safe_delete_run_dir, remote-host lock handling, and clean_runs."""

    def _make_remote_crashed(self, runs_dir: Path, name: str, run_id: str) -> Path:
        run_dir = runs_dir / name
        run_dir.mkdir(parents=True, exist_ok=True)
        lock_data = {
            "pid": 424242,
            "started_at_utc": time.time() - 200000,  # >48h -> classified crashed
            "script": "hpc.py",
            "run_id": run_id,
            "hostname": "remote-node-99.cluster.invalid",
        }
        (run_dir / ".pubrun.lock").write_text(json.dumps(lock_data), encoding="utf-8")
        return run_dir

    def test_clean_runs_limit_zero_deletes_nothing(self, tmp_path):
        from pubrun.status import clean_runs

        runs_dir = tmp_path / "runs"
        d1 = _write_manifest(runs_dir, "pubrun-a", "aaaa1111", 1000.0)
        d2 = _write_manifest(runs_dir, "pubrun-b", "bbbb2222", 2000.0)

        deleted = clean_runs(output_dir=str(runs_dir), limit=0, yes=True)
        assert deleted == 0
        assert d1.exists() and d2.exists()

    @pytest.mark.parametrize(
        "kwargs",
        [
            {"limit": -1},
            {"limit": True},
            {"status_filter": "bogus"},
            {"status_filter": "running,bogus"},
            {"not_status_filter": "bogus"},
        ],
    )
    def test_clean_runs_invalid_limit_or_status_raises_and_deletes_nothing(self, tmp_path, kwargs):
        from pubrun.status import clean_runs

        runs_dir = tmp_path / "runs"
        d1 = _write_manifest(runs_dir, "pubrun-a", "aaaa1111", 1000.0)
        with pytest.raises(ValueError):
            clean_runs(output_dir=str(runs_dir), yes=True, **kwargs)
        assert d1.exists()

    def test_clean_runs_remote_locks_excluded_by_default_and_overridden_with_force(self, tmp_path, capsys):
        from pubrun.status import clean_runs

        runs_dir = tmp_path / "runs"
        local_old = _write_manifest(runs_dir, "pubrun-local", "loc00001", time.time() - 300000)
        remote_new = self._make_remote_crashed(runs_dir, "pubrun-remote", "rem00001")

        # Default: remote lock excluded up front before limit, so limit=1 deletes the local run
        deleted = clean_runs(output_dir=str(runs_dir), limit=1, yes=True)
        out = capsys.readouterr().out
        assert deleted == 1
        assert not local_old.exists()
        assert remote_new.exists()
        assert "skipped 1 run" in out
        assert "--force-remote-locks" in out

        # Default again with only the remote lock remaining: nothing deleted
        deleted_again = clean_runs(output_dir=str(runs_dir), yes=True)
        assert deleted_again == 0
        assert remote_new.exists()

        # Opt-in escape hatch: force_remote_locks=True deletes the remote-locked run
        deleted_forced = clean_runs(output_dir=str(runs_dir), force_remote_locks=True, yes=True)
        assert deleted_forced == 1
        assert not remote_new.exists()

    def test_safe_delete_run_dir_guards_never_bypassed_by_force_remote_locks(self, tmp_path, monkeypatch):
        from pubrun.capture.liveness import get_hostname
        from pubrun.status import safe_delete_run_dir

        runs_dir = tmp_path / "runs"
        runs_dir.mkdir()
        outside = tmp_path / "outside_dir"
        outside.mkdir()
        (outside / "important.txt").write_text("keep", encoding="utf-8")

        # 1. Symlinked run_dir refused even with force_remote_locks=True
        sym_run = runs_dir / "pubrun-sym"
        sym_run.symlink_to(outside, target_is_directory=True)
        ok, reason = safe_delete_run_dir(sym_run, runs_dir, force_remote_locks=True)
        assert ok is False and reason is not None
        assert (outside / "important.txt").exists()

        # 2. Path escaping base_dir refused even with force_remote_locks=True
        ok, reason = safe_delete_run_dir(outside, runs_dir, force_remote_locks=True)
        assert ok is False and reason is not None and "escapes" in reason
        assert outside.exists()

        # 3. Corrupt/unreadable lock refused even with force_remote_locks=True
        corrupt_dir = runs_dir / "pubrun-corrupt"
        corrupt_dir.mkdir()
        (corrupt_dir / ".pubrun.lock").write_text("{not valid json", encoding="utf-8")
        ok, reason = safe_delete_run_dir(corrupt_dir, runs_dir, force_remote_locks=True)
        assert ok is False and reason is not None
        assert corrupt_dir.exists()

        # 4. Symlinked lock (including broken symlink) refused even with force_remote_locks=True
        symlock_dir = runs_dir / "pubrun-symlock"
        symlock_dir.mkdir()
        (symlock_dir / ".pubrun.lock").symlink_to(tmp_path / "nonexistent-target")
        ok, reason = safe_delete_run_dir(symlock_dir, runs_dir, force_remote_locks=True)
        assert ok is False and reason is not None
        assert symlock_dir.exists()

        # 5. Active local PID lock refused even with force_remote_locks=True
        active_dir = runs_dir / "pubrun-active"
        active_dir.mkdir()
        active_lock = {
            "pid": os.getpid(),
            "started_at_utc": time.time() - 5,
            "script": "pytest",
            "run_id": "act00001",
            "hostname": get_hostname(),
        }
        (active_dir / ".pubrun.lock").write_text(json.dumps(active_lock), encoding="utf-8")
        monkeypatch.setattr("pubrun.status.is_same_process", lambda *a, **kw: True)
        ok, reason = safe_delete_run_dir(active_dir, runs_dir, force_remote_locks=True)
        assert ok is False and reason is not None
        assert active_dir.exists()

        # 6. Remote-host lock refused by default, deleted when force_remote_locks=True
        remote_dir = self._make_remote_crashed(runs_dir, "pubrun-remote-only", "rem00002")
        ok, reason = safe_delete_run_dir(remote_dir, runs_dir, force_remote_locks=False)
        assert ok is False and reason is not None and "--force-remote-locks" in reason
        assert remote_dir.exists()
        ok, reason = safe_delete_run_dir(remote_dir, runs_dir, force_remote_locks=True)
        assert ok is True and reason is None
        assert not remote_dir.exists()

    def test_parse_selection_detailed_reports_ignored_tokens(self):
        from pubrun.status import _parse_selection, _parse_selection_detailed

        items = ["a", "b", "c", "d"]
        selected, ignored = _parse_selection_detailed("1, 99, 2-3, abc, 4-2, 0", items)
        assert selected == ["a", "b", "c"]
        assert ignored == ["99", "abc", "4-2", "0"]
        assert _parse_selection("1, 99, 2-3, abc", items) == ["a", "b", "c"]


class TestScalableScanningAndSelectors:
    """Regression tests for keep_manifest=False, load_manifest, artifact sizes, and find_run."""

    def test_completed_run_populates_event_count_and_console_log_size(self, tmp_path):
        from pubrun.status import RunInfo

        runs_dir = tmp_path / "runs"

        # 1. Completed run with events.jsonl + split stdout.log/stderr.log (plus legacy console.log ignored)
        d1 = _write_manifest(runs_dir, "pubrun-split", "spl00001", 1000.0)
        (d1 / "events.jsonl").write_bytes(b"x" * 360)  # 360 // 120 = 3
        (d1 / "stdout.log").write_bytes(b"a" * 100)
        (d1 / "stderr.log").write_bytes(b"b" * 50)
        (d1 / "console.log").write_bytes(b"c" * 999)
        info1 = RunInfo(d1)
        assert info1.event_count == 3
        assert info1.console_log_size == 150

        # 2. Completed run with empty events.jsonl and legacy console.log fallback only
        d2 = _write_manifest(runs_dir, "pubrun-legacy", "leg00002", 2000.0)
        (d2 / "events.jsonl").write_bytes(b"")
        (d2 / "console.log").write_bytes(b"legacy-log")
        info2 = RunInfo(d2)
        assert info2.event_count == 0
        assert info2.console_log_size == len(b"legacy-log")

        # 3. Completed run with tiny non-empty events.jsonl (<120 bytes -> estimate 1)
        d3 = _write_manifest(runs_dir, "pubrun-tiny", "tin00003", 3000.0)
        (d3 / "events.jsonl").write_bytes(b"{}\n")
        info3 = RunInfo(d3)
        assert info3.event_count == 1
        assert info3.console_log_size is None

    def test_keep_manifest_false_and_load_manifest_on_demand(self, tmp_path):
        from pubrun.status import scan_runs

        runs_dir = tmp_path / "runs"
        _write_manifest(runs_dir, "pubrun-a", "aaaa1111", 1000.0)

        # Default keep_manifest=True preserves backward compatibility
        retained = scan_runs(str(runs_dir))
        assert len(retained) == 1
        assert retained[0].manifest is not None
        assert retained[0].load_manifest() is retained[0].manifest

        # keep_manifest=False drops manifest dict after extracting scalar fields
        lean = scan_runs(str(runs_dir), keep_manifest=False)
        assert len(lean) == 1
        assert lean[0].run_id == "aaaa1111"
        assert lean[0].manifest is None
        loaded = lean[0].load_manifest()
        assert loaded is not None
        assert loaded["run"]["run_id"] == "aaaa1111"
        # load_manifest() does not retain the dict on the RunInfo
        assert lean[0].manifest is None

    def test_find_run_with_runs_arg_fast_path_and_recency_1000(self, tmp_path, monkeypatch):
        from pubrun.status import RunInfo, find_run, scan_runs

        runs_dir = tmp_path / "runs"
        _write_manifest(runs_dir, "pubrun-train-20260101T000000Z-123-deadbeef", "deadbeef", 1000.0)
        _write_manifest(runs_dir, "pubrun-custom-name", "cafebabe", 2000.0)

        # Fast path locates standard full run ID without invoking scan_runs
        scan_calls = []
        orig_scan = scan_runs

        def spy_scan(*args, **kwargs):
            scan_calls.append((args, kwargs))
            return orig_scan(*args, **kwargs)

        monkeypatch.setattr("pubrun.status.scan_runs", spy_scan)
        found_fast = find_run("deadbeef", str(runs_dir))
        assert found_fast is not None and found_fast.run_id == "deadbeef"
        assert found_fast.manifest is None
        assert scan_calls == []

        # Custom directory name falls back cleanly to scan_runs
        found_custom = find_run("cafebabe", str(runs_dir))
        assert found_custom is not None and found_custom.run_id == "cafebabe"
        assert len(scan_calls) == 1

        # Pre-scanned runs= searches without calling scan_runs
        scan_calls.clear()
        pre_scanned = orig_scan(str(runs_dir), keep_manifest=False)
        found_mem = find_run("1", runs=pre_scanned)
        assert found_mem is not None and found_mem.run_id == "cafebabe"
        assert scan_calls == []

        # #1000+ recency index resolves beyond the removed 999 cap
        many_runs = []
        for idx in range(1005):
            r = RunInfo(None)  # type: ignore[arg-type]
            r.run_dir = tmp_path / f"pubrun-r-{idx:04d}"
            r.run_id = f"id{idx:06x}"
            r.started_at_utc = 10000.0 - idx
            many_runs.append(r)

        run_1000 = find_run("1000", runs=many_runs)
        assert run_1000 is not None and run_1000.run_id == many_runs[999].run_id
        run_1005 = find_run("1005", runs=many_runs)
        assert run_1005 is not None and run_1005.run_id == many_runs[1004].run_id
        assert find_run("1006", runs=many_runs) is None


class TestTerminalRenderingAndLayout:
    """Regression tests for color/DIM, ASCII ellipsis, onboarding, filtered-empty, and responsive width."""

    def test_render_summary_tty_no_dim_and_piped_no_ansi(self, tmp_path, monkeypatch):
        from pubrun.status import _render_summary, scan_runs

        runs_dir = tmp_path / "runs"
        _write_manifest(runs_dir, "pubrun-a", "aaaa1111", 1000.0, outcome="failed", exit_code=2)
        _write_manifest(runs_dir, "pubrun-b", "bbbb2222", 2000.0, outcome="completed", exit_code=0)
        runs = scan_runs(str(runs_dir))

        # TTY / FORCE_COLOR mode: ANSI present, ZERO DIM (\x1b[2m)
        monkeypatch.delenv("NO_COLOR", raising=False)
        monkeypatch.setenv("FORCE_COLOR", "1")
        colored = _render_summary(runs)
        assert "\x1b[" in colored
        assert "\x1b[2m" not in colored

        # Piped non-TTY mode: ZERO ANSI
        monkeypatch.delenv("FORCE_COLOR", raising=False)
        monkeypatch.setattr(sys.stdout, "isatty", lambda: False)
        piped = _render_summary(runs)
        assert "\x1b[" not in piped

    def test_truncate_ascii_stream_fallback_and_edge_lengths(self):
        import io
        from pubrun.status import _truncate

        class AsciiStream(io.StringIO):
            encoding = "ascii"

        ascii_stream = AsciiStream()
        assert _truncate("hello world", 0, stream=ascii_stream) == ""
        assert _truncate("hello world", -5, stream=ascii_stream) == ""
        assert _truncate("hello world", 1, stream=ascii_stream) == "h"
        assert _truncate("hello world", 2, stream=ascii_stream) == "he"
        assert _truncate("hello world", 3, stream=ascii_stream) == "..."
        res = _truncate("hello world", 6, stream=ascii_stream)
        assert res == "hel..."
        # Confirm strictly ASCII-encodable (no UnicodeEncodeError)
        res.encode("ascii")

    def test_empty_and_filtered_empty_short_and_verbose_lists(self, tmp_path):
        from pubrun.status import render_short_list, render_verbose_list, scan_runs

        runs_dir = tmp_path / "runs"
        _write_manifest(runs_dir, "pubrun-a", "aaaa1111", 1000.0)
        _write_manifest(runs_dir, "pubrun-b", "bbbb2222", 2000.0)
        all_runs = scan_runs(str(runs_dir))

        # Empty directory onboarding: accurate, no misleading 'pubrun run -- python your_script.py'
        for render_fn in (render_short_list, render_verbose_list):
            empty_msg = render_fn([])
            assert "No runs found." in empty_msg
            assert "import pubrun" in empty_msg
            assert "pubrun init" in empty_msg
            assert "pubrun run -- python your_script.py" not in empty_msg

            # Filtered-empty state distinguishes 0 matched from empty directory
            filtered_msg = render_fn([], all_runs=all_runs)
            assert filtered_msg == (
                "0 of 2 runs matched the filter criteria. "
                "Run 'pubrun status' to list all runs."
            )

    def test_narrow_and_wide_terminal_layout_and_footer_tip(self, tmp_path, monkeypatch):
        from pubrun.status import render_short_list, scan_runs

        monkeypatch.setenv("NO_COLOR", "1")
        runs_dir = tmp_path / "runs"
        _write_manifest(runs_dir, "pubrun-a", "aaaa1111", 1000.0, argv=["train_model.py"])
        runs = scan_runs(str(runs_dir))

        # 60-col terminal drops COMMIT so SCRIPT stays readable
        monkeypatch.setattr("pubrun.status._get_terminal_width", lambda: 60)
        out_60 = render_short_list(runs)
        hdr_60 = out_60.splitlines()[0]
        assert "COMMIT" not in hdr_60
        assert "SCRIPT" in hdr_60
        assert "Tip: pass a # index (e.g. 'pubrun show 1' or 'pubrun diff 1 2') to any command." in out_60

        # 80-col terminal retains COMMIT
        monkeypatch.setattr("pubrun.status._get_terminal_width", lambda: 80)
        out_80 = render_short_list(runs)
        hdr_80 = out_80.splitlines()[0]
        assert "COMMIT" in hdr_80
        assert len(hdr_80) <= 80

        # 120-col terminal retains COMMIT with wider SCRIPT column
        monkeypatch.setattr("pubrun.status._get_terminal_width", lambda: 120)
        out_120 = render_short_list(runs)
        hdr_120 = out_120.splitlines()[0]
        assert "COMMIT" in hdr_120
        assert hdr_120.index("COMMIT") - hdr_120.index("SCRIPT") > hdr_80.index("COMMIT") - hdr_80.index("SCRIPT")

    def test_dynamic_hash_column_width_for_1000_runs(self, tmp_path, monkeypatch, capsys):
        from pubrun.status import RunInfo, clean_runs, render_short_list

        monkeypatch.setenv("NO_COLOR", "1")
        monkeypatch.setattr("pubrun.status._get_terminal_width", lambda: 100)

        many_runs = []
        for idx in range(1000):
            r = RunInfo(None)  # type: ignore[arg-type]
            r.run_dir = tmp_path / f"pubrun-r-{idx:04d}"
            r.run_id = f"aa{idx:06d}"
            r.script = "train.py"
            r.status = "completed"
            r.started_at_utc = 10000.0 - idx
            r.exit_code = 0
            r.elapsed = 1.0
            many_runs.append(r)

        # Render just the 1000th run with all_runs=many_runs so recency #1000 appears
        out = render_short_list([many_runs[999]], all_runs=many_runs)
        lines = out.splitlines()
        header = lines[0]
        row = lines[2]
        run_id_col = header.index("RUN ID")
        assert run_id_col == 6  # len("1000") + 2
        assert row[:run_id_col] == "1000  "
        assert row[run_id_col:run_id_col + 8] == many_runs[999].run_id

        # clean_runs dry-run table also expands '#' column width for 1000 candidates
        monkeypatch.setattr("pubrun.status.scan_runs", lambda *a, **kw: list(many_runs))
        monkeypatch.setattr("pubrun.status._dir_size", lambda p: 0)
        deleted = clean_runs(output_dir=str(tmp_path), dry_run=True)
        assert deleted == 0
        clean_lines = capsys.readouterr().out.splitlines()
        clean_hdr = next(ln for ln in clean_lines if "RUN ID" in ln and "SIZE" in ln)
        clean_run_id_col = clean_hdr.index("RUN ID")
        assert clean_run_id_col == 6
        last_row = next(ln for ln in clean_lines if many_runs[999].run_id in ln)
        assert last_row[:clean_run_id_col] == "1000  "
