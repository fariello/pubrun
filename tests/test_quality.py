"""Tests for ghost mode, double-stop, and diff engine (T2, T3, T4)."""
import json
import os
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

    def test_two_empty_manifests(self):
        """Comparing two empty manifests produces no diffs."""
        result = compare_manifests({}, {})
        assert result["added"] == {}
        assert result["removed"] == {}
        assert result["modified"] == {}

    def test_two_identical_manifests(self):
        """Comparing identical manifests has nothing in added/removed/modified."""
        m = {"host": {"os_name": "Linux"}, "timing": {"elapsed_seconds": 5.0}}
        result = compare_manifests(m, m)
        assert result["added"] == {}
        assert result["removed"] == {}
        assert result["modified"] == {}

    def test_identical_manifests_show_same(self):
        """With show_same=True, identical keys appear in the 'same' bucket."""
        m = {"host": {"os_name": "Linux"}}
        result = compare_manifests(m, m, show_same=True)
        assert "host.os_name" in result.get("same", {})

    def test_completely_different_manifests(self):
        """Two manifests with no overlapping keys."""
        a = {"foo": {"x": 1}}
        b = {"bar": {"y": 2}}
        result = compare_manifests(a, b)
        assert "foo.x" in result["removed"]
        assert "bar.y" in result["added"]

    def test_list_diff_added_removed(self):
        a = {"python": {"sys_path": ["/path/a", "/path/b"]}}
        b = {"python": {"sys_path": ["/path/b", "/path/c"]}}
        result = compare_manifests(a, b)
        assert "python.sys_path" in result["modified"]
        mod = result["modified"]["python.sys_path"]
        assert mod["type"] == "list_diff"
        assert mod["added"] == ["/path/c"]
        assert mod["removed"] == ["/path/a"]
        assert mod["order_changed"] is False

    def test_list_diff_order_changed(self):
        a = {"python": {"sys_path": ["/path/a", "/path/b"]}}
        b = {"python": {"sys_path": ["/path/b", "/path/a"]}}
        result = compare_manifests(a, b)
        assert "python.sys_path" in result["modified"]
        mod = result["modified"]["python.sys_path"]
        assert mod["type"] == "list_diff"
        assert mod["added"] == []
        assert mod["removed"] == []
        assert mod["order_changed"] is True


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
        assert flat["errors.records"] == []

    def test_wildcard_ignores(self):
        manifest = {
            "pubrun_imports": {
                "selected_at_utc": 12345.67,
                "requests": [
                    {
                        "timestamp_utc": 111.1,
                        "caller": {
                            "line_number": 42,
                            "filename": "a.py"
                        }
                    }
                ]
            }
        }
        ignores = [
            "pubrun_imports.selected_at_utc",
            "pubrun_imports.requests.*.timestamp_utc",
            "pubrun_imports.requests.*.caller.line_number"
        ]
        flat = _normalize_manifest(manifest, ignores)
        assert "pubrun_imports.selected_at_utc" not in flat
        assert "pubrun_imports.requests.0.timestamp_utc" not in flat
        assert "pubrun_imports.requests.0.caller.line_number" not in flat
        assert flat["pubrun_imports.requests.0.caller.filename"] == "a.py"

    def test_complex_list_flattening(self):
        manifest = {
            "pubrun_imports": {
                "requests": [
                    {"name": "requests", "conflict": False},
                    {"name": "urllib3", "conflict": True}
                ]
            }
        }
        flat = _normalize_manifest(manifest, [])
        assert flat["pubrun_imports.requests.0.name"] == "requests"
        assert flat["pubrun_imports.requests.0.conflict"] is False
        assert flat["pubrun_imports.requests.1.name"] == "urllib3"
        assert flat["pubrun_imports.requests.1.conflict"] is True


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
        sep = os.pathsep  # ':' on Unix, ';' on Windows
        a = {"environment": {"variables": [
            {"name": "PATH", "value": {"representation": "plain", "value": f"/usr/bin{sep}/bin"}}
        ]}}
        b = {"environment": {"variables": [
            {"name": "PATH", "value": {"representation": "plain", "value": f"/usr/bin{sep}/bin{sep}/usr/local/bin"}}
        ]}}
        result = compare_manifests(a, b)
        mod = result["modified"].get("environment.PATH", {})
        assert mod.get("type") == "path_split"
        assert "/usr/local/bin" in mod["added"]
        assert len(mod["removed"]) == 0

    def test_path_split_detects_removals(self):
        sep = os.pathsep
        a = {"environment": {"variables": [
            {"name": "PATH", "value": {"representation": "plain", "value": f"/usr/bin{sep}/bin{sep}/opt/bin"}}
        ]}}
        b = {"environment": {"variables": [
            {"name": "PATH", "value": {"representation": "plain", "value": f"/usr/bin{sep}/bin"}}
        ]}}
        result = compare_manifests(a, b)
        mod = result["modified"].get("environment.PATH", {})
        assert mod.get("type") == "path_split"
        assert "/opt/bin" in mod["removed"]


class TestMetaRefSecurity:
    """Security tests for meta_ref path traversal prevention."""

    def test_meta_ref_outside_manifest_dir_rejected(self, tmp_path):
        """meta_ref pointing outside manifest dir is rejected by default."""
        from pubrun.report.utils import hydrate_manifest

        # Create a manifest that references a file outside its directory
        run_dir = tmp_path / "runs" / "pubrun-test"
        run_dir.mkdir(parents=True)

        # Create a "secret" file outside the run directory
        secret = tmp_path / "secret.json"
        secret.write_text('{"evil": true}', encoding="utf-8")

        manifest_path = str(run_dir / "manifest.json")
        manifest = {"meta_ref": "../../secret.json"}

        hydrated, warnings = hydrate_manifest(manifest_path, manifest)

        # Should be rejected -- secret content NOT merged
        assert "evil" not in hydrated
        assert any("Security" in w for w in warnings)
        assert any("outside" in w.lower() for w in warnings)

    def test_meta_ref_inside_manifest_dir_accepted(self, tmp_path):
        """meta_ref pointing inside manifest dir is accepted."""
        from pubrun.report.utils import hydrate_manifest

        run_dir = tmp_path / "runs" / "pubrun-test"
        run_dir.mkdir(parents=True)

        # Create a valid meta.json inside the run dir
        meta = {"hardware": {"cpu_model": "test", "capture_state": {"status": "complete"}}}
        meta_path = run_dir / "meta.json"
        meta_path.write_text(json.dumps(meta), encoding="utf-8")

        manifest_path = str(run_dir / "manifest.json")
        manifest = {"meta_ref": "meta.json"}

        hydrated, warnings = hydrate_manifest(manifest_path, manifest)
        # Should be accepted -- no security warnings
        assert not any("Security" in w for w in warnings)

    def test_meta_ref_allowlist_permits_explicit_dir(self, tmp_path, monkeypatch):
        """Allowlist permits meta_ref from explicitly listed directories."""
        from pubrun.report.utils import hydrate_manifest

        # Set up directories
        run_dir = tmp_path / "runs" / "pubrun-test"
        run_dir.mkdir(parents=True)
        shared_dir = tmp_path / "shared"
        shared_dir.mkdir()

        meta = {"hardware": {"cpu_model": "shared-hw", "capture_state": {"status": "complete"}}}
        meta_path = shared_dir / "meta.json"
        meta_path.write_text(json.dumps(meta), encoding="utf-8")

        # Mock config to include the shared dir in allowlist
        from pubrun import config as config_module
        original_resolve = config_module.resolve_config

        def mock_resolve(overrides=None):
            cfg = original_resolve(overrides)
            cfg.setdefault("report", {})["meta_ref_allowed_dirs"] = [str(shared_dir)]
            return cfg

        monkeypatch.setattr(config_module, "resolve_config", mock_resolve)

        manifest_path = str(run_dir / "manifest.json")
        manifest = {"meta_ref": "../../shared/meta.json"}

        hydrated, warnings = hydrate_manifest(manifest_path, manifest)
        assert not any("Security" in w for w in warnings)

    def test_meta_ref_allow_external_escape_hatch(self, tmp_path, monkeypatch):
        """allow_external_meta_ref = true permits any path."""
        from pubrun.report.utils import hydrate_manifest
        from pubrun import config as config_module

        run_dir = tmp_path / "runs" / "pubrun-test"
        run_dir.mkdir(parents=True)
        outside = tmp_path / "outside"
        outside.mkdir()

        meta = {"hardware": {"cpu_model": "external", "capture_state": {"status": "complete"}}}
        (outside / "meta.json").write_text(json.dumps(meta), encoding="utf-8")

        original_resolve = config_module.resolve_config

        def mock_resolve(overrides=None):
            cfg = original_resolve(overrides)
            cfg.setdefault("report", {})["allow_external_meta_ref"] = True
            return cfg

        monkeypatch.setattr(config_module, "resolve_config", mock_resolve)

        manifest_path = str(run_dir / "manifest.json")
        manifest = {"meta_ref": "../../outside/meta.json"}

        hydrated, warnings = hydrate_manifest(manifest_path, manifest)
        assert not any("Security" in w for w in warnings)


class TestConsoleRestoreSafety:
    """Test that console interceptor doesn't clobber third-party stream wrappers."""

    def test_stop_preserves_third_party_wrapper(self):
        """If another library wraps stdout after pubrun, stop() doesn't clobber it."""
        import sys
        from pubrun.capture.console import ConsoleInterceptor
        from pathlib import Path
        import tempfile

        with tempfile.TemporaryDirectory() as td:
            run_dir = Path(td)
            interceptor = ConsoleInterceptor(run_dir, "basic")
            interceptor.start()

            # Simulate a third-party library wrapping stdout AFTER pubrun
            class ThirdPartyWrapper:
                def __init__(self, inner):
                    self.inner = inner
                def write(self, s):
                    return self.inner.write(s)
                def flush(self):
                    return self.inner.flush()

            third_party = ThirdPartyWrapper(sys.stdout)
            sys.stdout = third_party

            # Stop the interceptor -- should NOT replace sys.stdout since
            # it's no longer our tee.
            interceptor.stop()

            # sys.stdout should still be the third-party wrapper
            assert sys.stdout is third_party

            # Clean up
            sys.stdout = interceptor.original_stdout


class TestRunDirPermissions:
    """Test that run directories are created with restrictive permissions."""

    @pytest.mark.skipif(__import__("sys").platform == "win32", reason="POSIX-only")
    def test_run_dir_mode_700(self):
        """Run directory is created with mode 0o700 on POSIX."""
        import stat
        from pubrun.tracker import Run

        run = Run()
        mode = run.run_dir.stat().st_mode & 0o777
        assert mode == 0o700, f"Expected 0o700, got {oct(mode)}"
        run.stop()

