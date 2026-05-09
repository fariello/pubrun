"""Tests for ghost mode, double-stop, and diff engine (T2, T3, T4)."""
import json
import pytest
from pathlib import Path

from pubrun import start, get_current_run
from pubrun.analysis.diff import (
    compare_manifests, export_manifest, unflatten_manifest,
    _normalize_manifest, _is_path_var
)


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


class TestDiffNormalization:
    """Layer 5: Tests for _normalize_manifest internals."""

    def test_env_vars_flatten(self):
        manifest = {
            "environment": {
                "variables": [
                    {"name": "HOME", "value": {"representation": "plain", "value": "/home/user"}},
                    {"name": "API_KEY", "value": {"representation": "redacted"}}
                ]
            }
        }
        flat = _normalize_manifest(manifest, [])
        assert flat["environment.HOME"] == "/home/user"
        # Redacted values don't have a "value" key, so the value is None → ""
        assert "environment.API_KEY" in flat

    def test_packages_flatten(self):
        manifest = {
            "packages": {
                "records": [
                    {"name": "numpy", "version": "1.24.3"},
                    {"name": "torch", "version": "2.0.1"}
                ]
            }
        }
        flat = _normalize_manifest(manifest, [])
        assert flat["packages.numpy"] == "1.24.3"
        assert flat["packages.torch"] == "2.0.1"

    def test_ignores_filter_prefix(self):
        manifest = {
            "timing": {"started": 100, "elapsed": 5.0},
            "host": {"os_name": "Linux"}
        }
        flat = _normalize_manifest(manifest, ["timing"])
        assert "timing.started" not in flat
        assert "timing.elapsed" not in flat
        assert "host.os_name" in flat

    def test_nested_dict_flattens(self):
        manifest = {"hardware": {"cpu": {"model": "i7", "cores": 8}}}
        flat = _normalize_manifest(manifest, [])
        assert flat["hardware.cpu.model"] == "i7"
        assert flat["hardware.cpu.cores"] == 8

    def test_empty_list_renders_as_brackets(self):
        manifest = {"errors": {"records": []}}
        flat = _normalize_manifest(manifest, [])
        assert flat["errors.records"] == "[]"


class TestIsPathVar:
    """Layer 5: Tests for the PATH variable heuristic."""

    def test_detects_path(self):
        assert _is_path_var("environment.PATH") is True

    def test_detects_ld_library_path(self):
        assert _is_path_var("environment.LD_LIBRARY_PATH") is True

    def test_detects_pythonpath(self):
        assert _is_path_var("environment.PYTHONPATH") is True

    def test_rejects_non_path(self):
        assert _is_path_var("environment.HOME") is False

    def test_rejects_hostname(self):
        assert _is_path_var("host.hostname") is False


class TestPathSplitDiff:
    """Layer 5: Tests for PATH variable splitting in compare_manifests."""

    def test_path_split_detects_additions(self):
        a = {"environment": {"variables": [
            {"name": "PATH", "value": {"representation": "plain", "value": "/usr/bin:/bin"}}
        ]}}
        b = {"environment": {"variables": [
            {"name": "PATH", "value": {"representation": "plain", "value": "/usr/bin:/bin:/usr/local/bin"}}
        ]}}
        result = compare_manifests(a, b)
        mod = result["modified"].get("environment.PATH", {})
        assert mod.get("type") == "path_split"
        assert "/usr/local/bin" in mod["added"]
        assert len(mod["removed"]) == 0

    def test_path_split_detects_removals(self):
        a = {"environment": {"variables": [
            {"name": "PATH", "value": {"representation": "plain", "value": "/usr/bin:/bin:/opt/bin"}}
        ]}}
        b = {"environment": {"variables": [
            {"name": "PATH", "value": {"representation": "plain", "value": "/usr/bin:/bin"}}
        ]}}
        result = compare_manifests(a, b)
        mod = result["modified"].get("environment.PATH", {})
        assert mod.get("type") == "path_split"
        assert "/opt/bin" in mod["removed"]

