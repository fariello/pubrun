"""
Tests for features added in the 20260704 session.

Covers: imported-transitive packages, tree RSS (Linux/macOS mocked),
phase profiling, console mode resolution, event serialization errors,
ResourceWatcher tree scope, status summary, concurrent start(), and
write-mode provenance hash.
"""
import hashlib
import json
import logging
import os
import sys
import tempfile
import threading
import time
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest


# ---------------------------------------------------------------------------
# TST-01: imported-transitive mode
# ---------------------------------------------------------------------------

class TestImportedTransitiveMode:
    """Test the imported-transitive package capture mode."""

    def test_transitive_deps_discovered(self, monkeypatch):
        """Verify transitive deps appear with correct source and required_by."""
        from pubrun.capture.packages import get_packages

        # Mock sys.modules to contain only 'pubrun' as a top-level import
        fake_modules = {"pubrun": True, "os": True, "sys": True}
        monkeypatch.setattr("sys.modules", fake_modules)

        # Mock importlib.metadata to return known data
        import importlib.metadata

        def mock_version(name):
            versions = {"pubrun": "1.3.1", "tomli": "2.0.0"}
            if name in versions:
                return versions[name]
            raise importlib.metadata.PackageNotFoundError(name)

        class MockDist:
            def __init__(self, requires):
                self._requires = requires

            @property
            def requires(self):
                return self._requires

        def mock_distribution(name):
            if name == "pubrun":
                return MockDist(["tomli>=1.1.0; python_version < '3.11'"])
            raise importlib.metadata.PackageNotFoundError(name)

        monkeypatch.setattr("importlib.metadata.version", mock_version)
        monkeypatch.setattr("importlib.metadata.distribution", mock_distribution)

        config = {"capture": {"packages": {"mode": "imported-transitive"}}}
        result = get_packages(config)

        assert result["mode"] == "imported-transitive"
        names = {r["name"] for r in result["records"]}
        assert "pubrun" in names
        assert "tomli" in names

        # Verify source fields
        pubrun_rec = next(r for r in result["records"] if r["name"] == "pubrun")
        assert pubrun_rec["source"] == "imported"

        tomli_rec = next(r for r in result["records"] if r["name"] == "tomli")
        assert tomli_rec["source"] == "transitive"
        assert "pubrun" in tomli_rec["required_by"]

    def test_pep508_parser_edge_cases(self):
        """Verify PEP 508 name extraction from various requirement strings."""
        from pubrun.capture.packages import _parse_req_name

        cases = [
            ("numpy>=1.21", "numpy"),
            ("pytz", "pytz"),
            ("foo[extra]>=1.0", "foo"),
            ("bar ; python_version<'3.9'", "bar"),
            ("baz-qux.thing>=2.0", "baz-qux.thing"),
            ("SomePackage==1.0", "SomePackage"),
            ("", ""),
        ]
        for input_str, expected in cases:
            assert _parse_req_name(input_str) == expected, f"Failed for {input_str!r}"


# ---------------------------------------------------------------------------
# TST-02: tree RSS Linux (mocked /proc)
# ---------------------------------------------------------------------------

class TestTreeRssLinux:
    """Test _get_tree_rss_linux with mocked /proc filesystem."""

    def test_tree_includes_children_and_grandchildren(self, monkeypatch):
        """Verify RSS is summed across self + child + grandchild."""
        from pubrun.capture.resources import _get_tree_rss_linux

        my_pid = os.getpid()
        page_size = os.sysconf("SC_PAGE_SIZE")

        # Simulate: self (100 pages), child 1001 (50 pages), grandchild 1002 (25 pages)
        proc_files = {
            f"/proc/{my_pid}/statm": f"200 100 50 10 0 30 0",
            f"/proc/1001/statm": f"100 50 25 5 0 15 0",
            f"/proc/1002/statm": f"50 25 12 3 0 8 0",
            f"/proc/{my_pid}/task/{my_pid}/children": "1001",
            f"/proc/1001/task/1001/children": "1002",
            f"/proc/1002/task/1002/children": "",
        }

        real_open = open

        def mock_open(path, *args, **kwargs):
            path_str = str(path)
            if path_str in proc_files:
                from io import StringIO
                return StringIO(proc_files[path_str])
            return real_open(path, *args, **kwargs)

        monkeypatch.setattr("builtins.open", mock_open)
        monkeypatch.setattr("os.getpid", lambda: my_pid)

        result = _get_tree_rss_linux()
        expected = (100 + 50 + 25) * page_size
        assert result == expected

    def test_tree_no_children_returns_self(self, monkeypatch):
        """With no children, tree RSS should equal self RSS."""
        from pubrun.capture.resources import _get_tree_rss_linux

        my_pid = os.getpid()
        page_size = os.sysconf("SC_PAGE_SIZE")

        proc_files = {
            f"/proc/{my_pid}/statm": "200 80 40 10 0 20 0",
            f"/proc/{my_pid}/task/{my_pid}/children": "",
        }

        real_open = open

        def mock_open(path, *args, **kwargs):
            path_str = str(path)
            if path_str in proc_files:
                from io import StringIO
                return StringIO(proc_files[path_str])
            return real_open(path, *args, **kwargs)

        monkeypatch.setattr("builtins.open", mock_open)
        monkeypatch.setattr("os.getpid", lambda: my_pid)

        result = _get_tree_rss_linux()
        assert result == 80 * page_size


# ---------------------------------------------------------------------------
# TST-03: tree RSS macOS (mocked ps)
# ---------------------------------------------------------------------------

class TestTreeRssDarwin:
    """Test _get_tree_rss_darwin with mocked subprocess output."""

    def test_tree_parse_and_sum(self, monkeypatch):
        """Verify ps output is parsed and tree is walked correctly."""
        from pubrun.capture.resources import _get_tree_rss_darwin

        my_pid = 42

        # ps -eo pid,ppid,rss output (header + 4 processes)
        ps_output = (
            "  PID  PPID   RSS\n"
            "    1     0  1000\n"  # init — not our tree
            "   42     1  5000\n"  # self
            "  100    42  2000\n"  # child of self
            "  101   100  1000\n"  # grandchild
        )

        monkeypatch.setattr("os.getpid", lambda: my_pid)

        import subprocess
        from pubrun.capture.subprocesses import disable_spy

        def mock_check_output(cmd, **kwargs):
            if "ps" in cmd:
                return ps_output
            raise FileNotFoundError("not mocked")

        monkeypatch.setattr("subprocess.check_output", mock_check_output)

        result = _get_tree_rss_darwin()
        # self (5000) + child (2000) + grandchild (1000) = 8000 KB = 8000*1024 bytes
        assert result == (5000 + 2000 + 1000) * 1024

    def test_no_children_includes_self(self, monkeypatch):
        """With no children in ps output, result should be self RSS."""
        from pubrun.capture.resources import _get_tree_rss_darwin

        my_pid = 42
        ps_output = (
            "  PID  PPID   RSS\n"
            "    1     0  1000\n"
            "   42     1  3000\n"  # only self
        )

        monkeypatch.setattr("os.getpid", lambda: my_pid)

        import subprocess

        def mock_check_output(cmd, **kwargs):
            if "ps" in cmd:
                return ps_output
            raise FileNotFoundError("not mocked")

        monkeypatch.setattr("subprocess.check_output", mock_check_output)

        result = _get_tree_rss_darwin()
        assert result == 3000 * 1024


# ---------------------------------------------------------------------------
# TST-04: phase profiling with cProfile
# ---------------------------------------------------------------------------

class TestPhaseProfiling:
    """Test phase-scoped cProfile integration."""

    def test_profile_file_created(self, tmp_path):
        """Verify .prof file is created and loadable with pstats."""
        import pstats
        os.environ["PUBRUN_AUTO_START"] = "false"
        import pubrun

        run = pubrun.start(
            output_dir=str(tmp_path),
            capture={"profiling": {"enabled": True, "backend": "cprofile"}}
        )

        with pubrun.phase("compute"):
            total = sum(range(1000))

        run.stop()

        prof_path = run.run_dir / "profile-compute.prof"
        assert prof_path.exists(), "Profile file should be created"
        stats = pstats.Stats(str(prof_path))
        assert stats.total_calls > 0

    def test_orphaned_profiler_cleaned_up(self, tmp_path):
        """Profiler enabled without __exit__ should be cleaned up on stop()."""
        os.environ["PUBRUN_AUTO_START"] = "false"
        import pubrun

        run = pubrun.start(
            output_dir=str(tmp_path),
            capture={"profiling": {"enabled": True, "backend": "cprofile"}}
        )

        # Enter phase without context manager
        p = pubrun.phase("orphan")
        p.__enter__()
        # Don't call __exit__

        assert hasattr(run, "_active_profilers") and len(run._active_profilers) == 1

        run.stop()
        # Verify cleanup
        assert len(getattr(run, "_active_profilers", [])) == 0


# ---------------------------------------------------------------------------
# TST-05: resolve_console_mode Jupyter + non-TTY
# ---------------------------------------------------------------------------

class TestResolveConsoleMode:
    """Test context-aware console mode resolution."""

    def test_jupyter_detected_returns_jupyter_mode(self, monkeypatch):
        """When Jupyter is detected, jupyter_mode is returned."""
        from pubrun.capture.console import resolve_console_mode

        monkeypatch.setattr(
            "pubrun.capture.console._is_jupyter_kernel", lambda: True
        )

        config = {"console": {
            "capture_mode": "standard",
            "jupyter_mode": "off",
            "non_tty_mode": "inherit",
        }}
        assert resolve_console_mode(config) == "off"

    def test_jupyter_override_to_standard(self, monkeypatch):
        """User can force capture in Jupyter via jupyter_mode."""
        from pubrun.capture.console import resolve_console_mode

        monkeypatch.setattr(
            "pubrun.capture.console._is_jupyter_kernel", lambda: True
        )

        config = {"console": {
            "capture_mode": "standard",
            "jupyter_mode": "standard",
            "non_tty_mode": "inherit",
        }}
        assert resolve_console_mode(config) == "standard"

    def test_non_tty_override(self, monkeypatch):
        """When not a TTY and non_tty_mode is set, use it."""
        from pubrun.capture.console import resolve_console_mode

        monkeypatch.setattr(
            "pubrun.capture.console._is_jupyter_kernel", lambda: False
        )
        monkeypatch.setattr("sys.stdout", MagicMock(isatty=lambda: False))

        config = {"console": {
            "capture_mode": "standard",
            "jupyter_mode": "off",
            "non_tty_mode": "off",
        }}
        assert resolve_console_mode(config) == "off"

    def test_non_tty_inherit(self, monkeypatch):
        """non_tty_mode = 'inherit' uses capture_mode as-is."""
        from pubrun.capture.console import resolve_console_mode

        monkeypatch.setattr(
            "pubrun.capture.console._is_jupyter_kernel", lambda: False
        )
        monkeypatch.setattr("sys.stdout", MagicMock(isatty=lambda: False))

        config = {"console": {
            "capture_mode": "standard",
            "jupyter_mode": "off",
            "non_tty_mode": "inherit",
        }}
        assert resolve_console_mode(config) == "standard"


# ---------------------------------------------------------------------------
# TST-06: non-serializable event payload
# ---------------------------------------------------------------------------

class TestEventSerializationError:
    """Test that non-serializable payloads are handled gracefully."""

    def test_non_serializable_payload_logged_not_crash(self, tmp_path, caplog):
        """object() payload should log a warning, not crash."""
        os.environ["PUBRUN_AUTO_START"] = "false"
        import pubrun

        run = pubrun.start(
            output_dir=str(tmp_path),
            events={"enabled": True}
        )

        with caplog.at_level(logging.WARNING, logger="pubrun"):
            pubrun.annotate("bad_event", unserializable=object())

        run.stop()

        assert any("not JSON-serializable" in msg for msg in caplog.messages), \
            "Expected warning about non-serializable payload"


# ---------------------------------------------------------------------------
# TST-07: ResourceWatcher tree scope integration
# ---------------------------------------------------------------------------

class TestResourceWatcherTreeScope:
    """Test that tree scope reports tree fields in manifest."""

    def test_tree_scope_manifest_fields(self, tmp_path, monkeypatch):
        """With scope='tree', manifest should have peak_tree_rss_bytes."""
        os.environ["PUBRUN_AUTO_START"] = "false"
        import pubrun

        # Mock tree RSS to return a known value
        monkeypatch.setattr(
            "pubrun.capture.resources._get_tree_rss_linux",
            lambda: 100_000_000
        )

        run = pubrun.start(
            output_dir=str(tmp_path),
            capture={"resources": {"depth": "standard", "scope": "tree", "sample_interval_seconds": 0.1}}
        )
        time.sleep(0.3)  # Let at least 2 samples fire
        run.stop()

        manifest_path = run.run_dir / "manifest.json"
        with open(manifest_path) as f:
            manifest = json.load(f)

        resources = manifest["resources"]
        assert resources["scope"] == "tree"
        assert "peak_tree_rss_bytes" in resources


# ---------------------------------------------------------------------------
# TST-08: status summary line
# ---------------------------------------------------------------------------

class TestStatusSummaryLine:
    """Test _render_summary output."""

    def test_summary_contains_count_and_statuses(self):
        """Summary should show run count and status breakdown."""
        from pubrun.status import _render_summary, RunInfo
        from unittest.mock import MagicMock

        # Create mock RunInfo objects
        runs = []
        for i in range(5):
            r = MagicMock()
            r.status = "completed"
            r.started_at_utc = 1720000000.0 + i * 3600
            r.exit_code = 0
            runs.append(r)
        # Add one failed
        r = MagicMock()
        r.status = "failed"
        r.started_at_utc = 1720020000.0
        r.exit_code = 1
        runs.append(r)

        # Force NO_COLOR for predictable output
        os.environ["NO_COLOR"] = "1"
        try:
            summary = _render_summary(runs)
        finally:
            del os.environ["NO_COLOR"]

        assert "6 runs" in summary
        assert "5 completed" in summary
        assert "1 failed" in summary
        assert "exit 1" in summary


# ---------------------------------------------------------------------------
# TST-09: concurrent start()
# ---------------------------------------------------------------------------

class TestConcurrentStart:
    """Test that concurrent start() calls produce only one Run."""

    def test_only_one_run_created(self, tmp_path):
        """5 threads calling start() simultaneously should yield 1 Run."""
        os.environ["PUBRUN_AUTO_START"] = "false"
        import pubrun
        from pubrun.tracker import _active_run, get_current_run

        # Ensure no existing run
        if get_current_run():
            pubrun.stop()

        barrier = threading.Barrier(5, timeout=5)
        runs = []
        errors = []

        def worker():
            try:
                barrier.wait()
                r = pubrun.start(output_dir=str(tmp_path))
                runs.append(r)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10)

        assert not errors, f"Unexpected errors: {errors}"
        # All threads should have gotten the same Run instance
        unique_runs = set(id(r) for r in runs)
        assert len(unique_runs) == 1, f"Expected 1 unique Run, got {len(unique_runs)}"

        pubrun.stop()


# ---------------------------------------------------------------------------
# TST-10: write-mode provenance hash
# ---------------------------------------------------------------------------

class TestProvenanceWriteHash:
    """Test that write-mode ProvenanceFileProxy tracks hash correctly."""

    def test_write_hash_matches_file(self, tmp_path):
        """Hash in data_files.outputs should match actual file content."""
        os.environ["PUBRUN_AUTO_START"] = "false"
        import pubrun

        run = pubrun.start(output_dir=str(tmp_path))

        test_file = tmp_path / "output.txt"
        with pubrun.open(str(test_file), "w") as f:
            f.write("hello world\n")
            f.write("second line\n")

        run.stop()

        # Compute expected hash
        expected_hash = hashlib.sha256(
            test_file.read_bytes()
        ).hexdigest()

        # Check manifest
        manifest_path = run.run_dir / "manifest.json"
        with open(manifest_path) as f:
            manifest = json.load(f)

        outputs = manifest["data_files"]["outputs"]
        assert len(outputs) >= 1
        recorded_hash = outputs[0]["sha256"]
        assert recorded_hash == expected_hash, \
            f"Expected {expected_hash}, got {recorded_hash}"
