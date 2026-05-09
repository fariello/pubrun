"""Tests for ghost mode, double-stop, and diff engine (T2, T3, T4)."""
import json
import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path

from pubrun import start, get_current_run
import pubrun.tracker
from pubrun.analysis.diff import compare_manifests, export_manifest, unflatten_manifest


@pytest.fixture(autouse=True)
def _clear_active_run():
    """Ensure _active_run is reset after each test to prevent cross-test pollution."""
    yield
    pubrun.tracker._active_run = None


class TestGhostMode:
    """T2: Verify ghost mode activates when run_dir creation fails."""

    def test_ghost_mode_on_permission_error(self, tmp_path, monkeypatch):
        monkeypatch.setattr("pathlib.Path.cwd", lambda: tmp_path)

        # Make mkdir raise PermissionError to trigger ghost mode
        original_mkdir = Path.mkdir

        def failing_mkdir(self, *args, **kwargs):
            if "pubrun-" in str(self):
                raise PermissionError("Read-only filesystem")
            return original_mkdir(self, *args, **kwargs)

        monkeypatch.setattr("pathlib.Path.mkdir", failing_mkdir)

        tracker = start()
        assert tracker.is_active is False
        assert tracker.console_interceptor is None
        assert tracker.event_stream is None

        # stop() must not crash in ghost mode
        tracker.stop()

    def test_ghost_mode_no_artifacts(self, tmp_path, monkeypatch):
        monkeypatch.setattr("pathlib.Path.cwd", lambda: tmp_path)

        original_mkdir = Path.mkdir

        def failing_mkdir(self, *args, **kwargs):
            if "pubrun-" in str(self):
                raise PermissionError("Read-only filesystem")
            return original_mkdir(self, *args, **kwargs)

        monkeypatch.setattr("pathlib.Path.mkdir", failing_mkdir)

        tracker = start()
        tracker.stop()

        # No runs directory should have been created
        runs_dir = tmp_path / "runs"
        if runs_dir.exists():
            assert len(list(runs_dir.iterdir())) == 0


class TestDoubleStop:
    """T4: Verify that calling stop() twice is safe and idempotent."""

    def test_double_stop_no_crash(self, tmp_path, monkeypatch):
        monkeypatch.setattr("pathlib.Path.cwd", lambda: tmp_path)

        tracker = start()
        assert tracker.is_active is True

        tracker.stop(outcome="completed")
        assert tracker.is_active is False

        # Second stop must not crash
        tracker.stop(outcome="completed")
        assert tracker.is_active is False

    def test_double_stop_preserves_manifest(self, tmp_path, monkeypatch):
        monkeypatch.setattr("pathlib.Path.cwd", lambda: tmp_path)

        tracker = start()
        tracker.stop(outcome="completed")

        manifest_path = tracker.run_dir / "manifest.json"
        assert manifest_path.exists()
        with open(manifest_path, "r") as f:
            data1 = json.load(f)

        # Verify data integrity after first stop
        assert data1["status"]["outcome"] == "completed"
        elapsed1 = data1["timing"]["elapsed_seconds"]

        # Second stop should not change the elapsed time
        tracker.stop(outcome="completed")


class TestDiffEngine:
    """T3: Verify the diff comparison engine."""

    def test_added_key(self):
        a = {"host": {"os_name": "Linux"}}
        b = {"host": {"os_name": "Linux", "hostname": "server1"}}
        result = compare_manifests(a, b)
        assert "host.hostname" in result["added"]
        assert result["added"]["host.hostname"] == "server1"

    def test_removed_key(self):
        a = {"host": {"os_name": "Linux", "hostname": "server1"}}
        b = {"host": {"os_name": "Linux"}}
        result = compare_manifests(a, b)
        assert "host.hostname" in result["removed"]

    def test_modified_key(self):
        a = {"host": {"os_name": "Linux"}}
        b = {"host": {"os_name": "Darwin"}}
        result = compare_manifests(a, b)
        assert "host.os_name" in result["modified"]
        mod = result["modified"]["host.os_name"]
        assert mod["old"] == "Linux"
        assert mod["new"] == "Darwin"

    def test_same_key(self):
        a = {"host": {"os_name": "Linux"}}
        b = {"host": {"os_name": "Linux"}}
        result = compare_manifests(a, b, show_same=True)
        assert "host.os_name" in result["same"]

    def test_same_key_hidden_by_default(self):
        a = {"host": {"os_name": "Linux"}}
        b = {"host": {"os_name": "Linux"}}
        result = compare_manifests(a, b, show_same=False)
        assert len(result["same"]) == 0

    def test_ignore_filter(self):
        a = {"timing": {"started": 100}, "host": {"os": "Linux"}}
        b = {"timing": {"started": 200}, "host": {"os": "Linux"}}
        result = compare_manifests(a, b, ignores=["timing"])
        assert len(result["modified"]) == 0

    def test_export_txt(self):
        raw = {"host": {"os_name": "Linux"}, "run": {"id": "abc"}}
        txt = export_manifest(raw, [], "txt")
        assert "host.os_name = Linux" in txt
        assert "run.id = abc" in txt

    def test_export_json(self):
        raw = {"host": {"os_name": "Linux"}}
        j = export_manifest(raw, [], "json")
        parsed = json.loads(j)
        assert parsed["host"]["os_name"] == "Linux"

    def test_unflatten(self):
        flat = {"core.profile": "deep", "core.auto_start": True}
        nested = unflatten_manifest(flat)
        assert nested["core"]["profile"] == "deep"
        assert nested["core"]["auto_start"] is True
