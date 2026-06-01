"""Tests for the pubrun public API contract (start, stop, annotate, phase, tracked_run, audit_run, diff)."""
import json
import os
import pytest
from pathlib import Path

import pubrun
from pubrun import start, stop, annotate, get_current_run, audit_run, tracked_run, phase


class TestStart:

    def test_returns_run_object(self):
        tracker = start()
        assert tracker is not None
        assert tracker.is_active is True
        tracker.stop()

    def test_sets_active_run(self):
        tracker = start()
        assert get_current_run() is tracker
        tracker.stop()

    def test_creates_run_directory(self, tmp_path):
        tracker = start()
        assert tracker.run_dir.exists()
        tracker.stop()

    def test_run_id_is_hex(self):
        tracker = start()
        assert len(tracker.run_id) == 8
        int(tracker.run_id, 16)  # Should not raise
        tracker.stop()


class TestStop:

    def test_module_level_stop(self):
        tracker = start()
        assert get_current_run() is tracker
        stop()
        assert get_current_run() is None

    def test_stop_without_active_run_no_crash(self):
        """Calling stop() with no active run should not crash."""
        assert get_current_run() is None
        stop()  # Should be silent

    def test_stop_sets_inactive(self):
        tracker = start()
        tracker.stop()
        assert tracker.is_active is False

    def test_stop_writes_manifest(self):
        tracker = start()
        tracker.stop()
        manifest_path = tracker.run_dir / "manifest.json"
        assert manifest_path.exists()
        with open(manifest_path, "r") as f:
            data = json.load(f)
        assert data["schema_version"] == "1.0"
        assert data["status"]["outcome"] == "completed"

    def test_stop_writes_config_resolved(self):
        tracker = start()
        tracker.stop()
        config_path = tracker.run_dir / "config.resolved.json"
        assert config_path.exists()


class TestAnnotate:

    def test_annotate_with_active_run(self):
        tracker = start(events={"enabled": True})
        assert tracker.event_stream is not None, "Event stream not initialized (ghost mode?)"
        annotate("test checkpoint", loss=0.5)
        tracker.stop()
        # Event should have been written
        events_path = tracker.run_dir / "events.jsonl"
        assert events_path.exists()
        with open(events_path, "r") as f:
            lines = f.readlines()
        assert len(lines) >= 1
        record = json.loads(lines[0])
        assert record["type"] == "annotation"

    def test_annotate_without_active_run_no_crash(self):
        """Annotating with no active run should be silent."""
        assert get_current_run() is None
        annotate("orphaned annotation")  # Should not raise

    def test_annotate_message_only(self):
        tracker = start(events={"enabled": True})
        assert tracker.event_stream is not None, "Event stream not initialized (ghost mode?)"
        annotate("just a message")
        tracker.stop()
        events_path = tracker.run_dir / "events.jsonl"
        with open(events_path, "r") as f:
            record = json.loads(f.readline())
        assert record["name"] == "just a message"

    def test_annotate_payload_only(self):
        tracker = start(events={"enabled": True})
        assert tracker.event_stream is not None, "Event stream not initialized (ghost mode?)"
        annotate(epoch=5, loss=0.123)
        tracker.stop()
        events_path = tracker.run_dir / "events.jsonl"
        with open(events_path, "r") as f:
            record = json.loads(f.readline())
        assert record["payload"]["epoch"] == 5
        assert record["payload"]["loss"] == 0.123


class TestPhase:

    def test_phase_context_manager(self):
        tracker = start(events={"enabled": True})
        with phase("training"):
            pass
        tracker.stop()
        events_path = tracker.run_dir / "events.jsonl"
        with open(events_path, "r") as f:
            lines = [json.loads(l) for l in f.readlines()]
        types = [r["type"] for r in lines]
        assert "phase_start" in types or "phase_started" in types
        assert "phase_end" in types or "phase_ended" in types

    def test_phase_with_exception(self):
        tracker = start(events={"enabled": True})
        with pytest.raises(ValueError):
            with phase("failing_phase"):
                raise ValueError("simulated failure")
        tracker.stop()
        events_path = tracker.run_dir / "events.jsonl"
        with open(events_path, "r") as f:
            lines = [json.loads(l) for l in f.readlines()]
        # The phase_end event should include error info
        end_events = [r for r in lines if "phase_end" in r["type"]]
        assert len(end_events) >= 1
        assert "error" in str(end_events[0].get("payload", {}))

    def test_phase_without_active_run_no_crash(self):
        """Phase with no active run should not crash."""
        with phase("orphaned"):
            pass


class TestTrackedRun:

    def test_context_manager_lifecycle(self):
        with tracked_run() as ctx:
            assert get_current_run() is not None
        assert get_current_run() is None

    def test_context_manager_writes_manifest(self, tmp_path):
        with tracked_run() as ctx:
            run_dir = ctx.run_tracker.run_dir
        manifest_path = run_dir / "manifest.json"
        assert manifest_path.exists()

    def test_context_manager_with_exception(self):
        with pytest.raises(RuntimeError):
            with tracked_run() as ctx:
                run_dir = ctx.run_tracker.run_dir
                raise RuntimeError("boom")
        manifest_path = run_dir / "manifest.json"
        assert manifest_path.exists()
        with open(manifest_path, "r") as f:
            data = json.load(f)
        assert data["status"]["outcome"] == "failed"

    def test_context_manager_with_overrides(self):
        with tracked_run(events={"enabled": True}) as ctx:
            tracker = ctx.run_tracker
        assert tracker.config.get("events", {}).get("enabled") is True


class TestAuditRun:

    def test_decorator_returns_value(self):
        @audit_run
        def my_logic():
            return 42
        assert my_logic() == 42

    def test_decorator_with_kwargs(self):
        @audit_run(events={"enabled": True})
        def my_logic():
            return "ok"
        assert my_logic() == "ok"

    def test_decorator_writes_manifest(self, tmp_path):
        @audit_run
        def my_logic():
            run_dir = get_current_run().run_dir
            return run_dir
        run_dir = my_logic()
        assert (run_dir / "manifest.json").exists()

    def test_decorator_handles_exception(self):
        @audit_run
        def crashing():
            raise ValueError("test crash")
        with pytest.raises(ValueError):
            crashing()


class TestDiff:

    def test_diff_two_runs(self, tmp_path):
        """Integration test: create two runs and diff them."""
        t1 = start()
        t1.stop()
        dir_a = str(t1.run_dir)

        t2 = start()
        t2.stop()
        dir_b = str(t2.run_dir)

        result = pubrun.diff(dir_a, dir_b)
        assert "added" in result
        assert "removed" in result
        assert "modified" in result

    def test_diff_with_ignores(self, tmp_path):
        t1 = start()
        t1.stop()
        dir_a = str(t1.run_dir)

        t2 = start()
        t2.stop()
        dir_b = str(t2.run_dir)

        result = pubrun.diff(dir_a, dir_b, ignores=["timing", "run", "capture"])
        # With timing/run/capture ignored, most volatile fields are excluded
        assert isinstance(result, dict)

    def test_diff_invalid_path(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            pubrun.diff("/nonexistent/path/a", "/nonexistent/path/b")


class TestManifestSchema:
    """Integration test: validates that a real start→stop produces a schema-compliant manifest."""

    REQUIRED_TOP_LEVEL_KEYS = {
        "schema_version", "manifest_type", "run", "timing", "invocation",
        "console", "subprocesses", "process", "python", "packages",
        "environment", "git", "errors", "config", "hardware", "host",
        "resources", "capture", "status"
    }

    SECTIONS_WITH_CAPTURE_STATE = {
        "run", "timing", "invocation", "process", "python", "packages",
        "environment", "git", "errors", "config", "hardware", "host",
        "resources", "capture", "status"
    }

    def test_manifest_has_all_required_keys(self):
        tracker = start()
        tracker.stop()
        manifest_path = tracker.run_dir / "manifest.json"
        with open(manifest_path, "r") as f:
            manifest = json.load(f)
        missing = self.REQUIRED_TOP_LEVEL_KEYS - set(manifest.keys())
        assert missing == set(), f"Missing top-level keys: {missing}"

    def test_capture_state_present_in_sections(self):
        tracker = start()
        tracker.stop()
        manifest_path = tracker.run_dir / "manifest.json"
        with open(manifest_path, "r") as f:
            manifest = json.load(f)
        for section in self.SECTIONS_WITH_CAPTURE_STATE:
            data = manifest.get(section, {})
            if isinstance(data, dict):
                assert "capture_state" in data, f"Section '{section}' missing capture_state"

    def test_timing_values_are_floats(self):
        tracker = start()
        tracker.stop()
        manifest_path = tracker.run_dir / "manifest.json"
        with open(manifest_path, "r") as f:
            manifest = json.load(f)
        timing = manifest["timing"]
        assert isinstance(timing["started_at_utc"], float)
        assert isinstance(timing["ended_at_utc"], float)
        assert isinstance(timing["elapsed_seconds"], float)
        assert timing["elapsed_seconds"] >= 0

    def test_schema_version_is_1_0(self):
        tracker = start()
        tracker.stop()
        manifest_path = tracker.run_dir / "manifest.json"
        with open(manifest_path, "r") as f:
            manifest = json.load(f)
        assert manifest["schema_version"] == "1.0"
        assert manifest["manifest_type"] == "pubrun-manifest"

    def test_outcome_is_completed(self):
        tracker = start()
        tracker.stop()
        manifest_path = tracker.run_dir / "manifest.json"
        with open(manifest_path, "r") as f:
            manifest = json.load(f)
        assert manifest["status"]["outcome"] == "completed"


class TestModuleExports:
    """Regression test: __all__ must match actual module exports."""

    def test_all_symbols_exist(self):
        for name in pubrun.__all__:
            assert hasattr(pubrun, name), f"__all__ declares '{name}' but it does not exist on the module"

    def test_all_contains_expected_api(self):
        expected = {"start", "stop", "annotate", "phase", "diff", "audit_run", "tracked_run", "get_current_run", "__version__"}
        actual = set(pubrun.__all__)
        missing = expected - actual
        assert missing == set(), f"Expected public API symbols missing from __all__: {missing}"


class TestAutoStartBootSequence:
    """Tests for the import-time auto-start mechanism."""

    def test_auto_start_true_creates_run(self, tmp_path):
        """PUBRUN_AUTO_START=true triggers a run on import."""
        import subprocess
        import sys

        script = f"""
import os, sys, json
os.chdir({str(tmp_path)!r})
os.environ['PUBRUN_AUTO_START'] = 'true'
# Force reimport by clearing the module
for mod in list(sys.modules.keys()):
    if 'pubrun' in mod:
        del sys.modules[mod]
import pubrun
run = pubrun.get_current_run()
print(json.dumps({{"active": run is not None, "run_dir": str(run.run_dir) if run else None}}))
if run:
    run.stop()
"""
        result = subprocess.run(
            [sys.executable, "-c", script],
            capture_output=True, text=True, timeout=15,
            env={**__import__("os").environ, "PUBRUN_AUTO_START": "true"}
        )
        assert result.returncode == 0, f"stderr: {result.stderr}"
        data = json.loads(result.stdout.strip())
        assert data["active"] is True

    def test_auto_start_false_no_run(self, tmp_path):
        """PUBRUN_AUTO_START=false suppresses auto-start."""
        import subprocess
        import sys

        script = f"""
import os, sys, json
os.chdir({str(tmp_path)!r})
os.environ['PUBRUN_AUTO_START'] = 'false'
for mod in list(sys.modules.keys()):
    if 'pubrun' in mod:
        del sys.modules[mod]
import pubrun
run = pubrun.get_current_run()
print(json.dumps({{"active": run is not None}}))
"""
        result = subprocess.run(
            [sys.executable, "-c", script],
            capture_output=True, text=True, timeout=15,
            env={**__import__("os").environ, "PUBRUN_AUTO_START": "false"}
        )
        assert result.returncode == 0, f"stderr: {result.stderr}"
        data = json.loads(result.stdout.strip())
        assert data["active"] is False


class TestAutoStartResilience:
    """P3-T4: Regression test -- auto-start failure must not crash import."""

    def test_auto_start_failure_does_not_crash_import(self, tmp_path):
        """If start() raises during auto-start, import pubrun still succeeds.

        P3-T4: Regression test for the try/except around start() in __init__.py.
        Strategy: import pubrun with auto-start disabled, poison Run, then purge
        and re-import with auto-start enabled.
        """
        import subprocess
        import sys

        script = f"""
import os, sys, json
os.chdir({str(tmp_path)!r})

# Phase 1: Import pubrun with auto-start OFF so we can patch
os.environ['PUBRUN_AUTO_START'] = 'false'
import pubrun
import pubrun.tracker

# Phase 2: Poison Run.__init__ so start() always raises
_Orig = pubrun.tracker.Run
class _Broken(_Orig):
    def __init__(self, **kw):
        raise RuntimeError("simulated catastrophic failure")
pubrun.tracker.Run = _Broken

# Phase 3: Reset state and re-import with auto-start ON
pubrun.tracker._active_run = None
os.environ['PUBRUN_AUTO_START'] = 'true'
# Purge only the top-level pubrun module to re-execute __init__.py
del sys.modules['pubrun']
import pubrun  # Re-runs __init__.py auto-start path with poisoned Run

run = pubrun.get_current_run()
print(json.dumps({{"imported": True, "active": run is not None}}))
"""
        result = subprocess.run(
            [sys.executable, "-c", script],
            capture_output=True, text=True, timeout=15,
            env={**os.environ, "PUBRUN_AUTO_START": "false"}
        )
        # The critical assertion: process must not crash (returncode 0)
        assert result.returncode == 0, f"Auto-start crash! stderr: {result.stderr}"
        data = json.loads(result.stdout.strip())
        assert data["imported"] is True
        assert data["active"] is False  # start() failed gracefully


class TestAuditRunMetadata:
    """Test that audit_run preserves function metadata via functools.wraps."""

    def test_preserves_name(self):
        @audit_run
        def my_training_function():
            """Docstring for training."""
            pass

        assert my_training_function.__name__ == "my_training_function"
        assert my_training_function.__doc__ == "Docstring for training."

    def test_preserves_qualname(self):
        @audit_run(profile="basic")
        def another_function():
            pass

        assert "another_function" in another_function.__qualname__


class TestHandleInactivePolicy:
    """Test on_inactive_annotate policy enforcement."""

    def test_error_policy_raises_runtime_error(self, monkeypatch):
        """on_inactive_annotate='error' raises RuntimeError with no active run."""
        from pubrun import config as config_module

        original_resolve = config_module.resolve_config

        def mock_resolve(overrides=None):
            cfg = original_resolve(overrides)
            cfg.setdefault("events", {})["on_inactive_annotate"] = "error"
            return cfg

        monkeypatch.setattr(config_module, "resolve_config", mock_resolve)

        assert get_current_run() is None
        with pytest.raises(RuntimeError, match="no run is active"):
            annotate("should raise")

    def test_warn_policy_logs_warning(self, monkeypatch, caplog):
        """on_inactive_annotate='warn' logs a warning with no active run."""
        import logging
        from pubrun import config as config_module

        original_resolve = config_module.resolve_config

        def mock_resolve(overrides=None):
            cfg = original_resolve(overrides)
            cfg.setdefault("events", {})["on_inactive_annotate"] = "warn"
            return cfg

        monkeypatch.setattr(config_module, "resolve_config", mock_resolve)

        assert get_current_run() is None
        with caplog.at_level(logging.WARNING, logger="pubrun"):
            annotate("should warn")

        assert any("dropped" in r.message.lower() or "no active run" in r.message.lower()
                   for r in caplog.records)

    def test_ignore_policy_is_silent(self):
        """on_inactive_annotate='ignore' (default) does nothing."""
        assert get_current_run() is None
        # Should not raise, should not log (just return silently)
        annotate("silently dropped")

    def test_phase_error_policy_raises(self, monkeypatch):
        """on_inactive_annotate='error' also affects phase()."""
        from pubrun import config as config_module

        original_resolve = config_module.resolve_config

        def mock_resolve(overrides=None):
            cfg = original_resolve(overrides)
            cfg.setdefault("events", {})["on_inactive_annotate"] = "error"
            return cfg

        monkeypatch.setattr(config_module, "resolve_config", mock_resolve)

        assert get_current_run() is None
        with pytest.raises(RuntimeError, match="no run is active"):
            with phase("should_raise"):
                pass

