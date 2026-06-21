import json
import sys
import pytest
from pathlib import Path
from pubrun import start, get_current_run

def test_tracker_lifecycle_and_writer(tmp_path, monkeypatch):
    """Verifies that start() creates a directory and stop() dumps the manifest properly."""
    # Override the cwd to our tmp_path so runs/ generates there
    monkeypatch.setattr("pathlib.Path.cwd", lambda: tmp_path)
    
    tracker = start()
    assert tracker.is_active is True
    assert tracker.run_dir.exists()
    assert tracker.run_dir.parent.name == "runs"
    
    assert get_current_run() is tracker
    
    # Manually halt
    tracker.stop(outcome="completed")
    
    assert tracker.is_active is False
    assert tracker._outcome == "completed"
    assert get_current_run() is None
    
    # Check artifacts
    manifest_path = tracker.run_dir / "manifest.json"
    assert manifest_path.exists()
    
    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest_data = json.load(f)
        
    assert manifest_data["schema_version"] == "1.0"
    assert isinstance(manifest_data["timing"]["started_at_utc"], float)
    assert manifest_data["status"]["outcome"] == "completed"
    
    from pubrun import __version__, __commit__
    assert manifest_data["run"]["library_version"] == __version__
    assert manifest_data["run"]["library_commit"] == __commit__
    
    # Check config
    config_path = tracker.run_dir / "config.resolved.json"
    assert config_path.exists()

def test_audit_run_decorator(tmp_path, monkeypatch):
    from pubrun import audit_run
    monkeypatch.setattr("pathlib.Path.cwd", lambda: tmp_path)
    
    @audit_run(profile="deep")
    def my_logic():
        # verify active inside
        assert get_current_run() is not None
        return 42
        
    res = my_logic()
    assert res == 42
    assert get_current_run() is None # cleaned up automatically after run


def test_engine_crash_promotes_to_ghost(tmp_path, monkeypatch):
    """If a capture engine raises during init, the run enters ghost mode."""
    from pubrun.tracker import Run
    monkeypatch.setattr("pathlib.Path.cwd", lambda: tmp_path)

    # Make get_invocation raise to simulate an engine crash
    def broken_invocation(config):
        raise RuntimeError("simulated engine failure")

    monkeypatch.setattr("pubrun.tracker.get_invocation", broken_invocation)

    run = Run()
    assert run._outcome == "ghost"
    assert run.is_active is False
    assert run._finalized is True


def test_atomic_manifest_write(tmp_path, monkeypatch):
    """manifest.json is written atomically (no .tmp file left behind)."""
    monkeypatch.setattr("pathlib.Path.cwd", lambda: tmp_path)

    tracker = start()
    tracker.stop()

    # manifest.json exists, no .tmp file remains
    manifest = tracker.run_dir / "manifest.json"
    tmp_file = tracker.run_dir / "manifest.json.tmp"
    assert manifest.exists()
    assert not tmp_file.exists()

    # Manifest is valid JSON
    with open(manifest) as f:
        data = json.load(f)
    assert data["status"]["outcome"] == "completed"


def test_atomic_write_cleans_temp_on_failure(tmp_path, monkeypatch):
    """P3-T4: Temp file is cleaned up if os.replace fails."""
    from pubrun.writer import _atomic_json_write
    from pathlib import Path

    target = tmp_path / "output.json"
    # Make os.replace fail
    monkeypatch.setattr("os.replace", lambda src, dst: (_ for _ in ()).throw(OSError("cross-device link")))

    import pytest
    with pytest.raises(OSError, match="cross-device"):
        _atomic_json_write(target, {"key": "value"})

    # Temp file should NOT be left behind
    tmp_file = target.with_suffix(".json.tmp")
    assert not tmp_file.exists()


# ==========================================================================
# _merge_and_migrate tests
# ==========================================================================

class TestMergeAndMigrate:
    """Tests for the _merge_and_migrate directory migration mechanism."""

    @pytest.mark.skipif(sys.platform == "win32", reason="Open file handles prevent shutil.move on Windows")
    def test_migrate_moves_directory(self, tmp_path, monkeypatch):
        """Changing output_dir mid-run moves the run directory."""
        from pubrun.tracker import Run
        monkeypatch.setattr("pathlib.Path.cwd", lambda: tmp_path)

        run = Run()
        original_dir = run.run_dir
        assert original_dir.exists()

        # Migrate to a new output directory
        new_output = tmp_path / "new_output"
        run._merge_and_migrate({"core": {"output_dir": str(new_output)}})

        # Old directory should be gone, new one should exist
        assert not original_dir.exists()
        expected_new = new_output / original_dir.name
        assert expected_new.exists()
        assert run.run_dir == expected_new

        run.stop()

    def test_migrate_preserves_files(self, tmp_path, monkeypatch):
        """Files created in the run directory survive migration."""
        from pubrun.tracker import Run
        monkeypatch.setattr("pathlib.Path.cwd", lambda: tmp_path)

        run = Run()
        # Create a test file in the run dir
        test_file = run.run_dir / "test_artifact.txt"
        test_file.write_text("hello", encoding="utf-8")

        new_output = tmp_path / "migrated"
        run._merge_and_migrate({"core": {"output_dir": str(new_output)}})

        # File should exist in new location
        migrated_file = run.run_dir / "test_artifact.txt"
        assert migrated_file.exists()
        assert migrated_file.read_text(encoding="utf-8") == "hello"

        run.stop()

    def test_migrate_empty_overrides_is_noop(self, tmp_path, monkeypatch):
        """Empty overrides dict does nothing."""
        from pubrun.tracker import Run
        monkeypatch.setattr("pathlib.Path.cwd", lambda: tmp_path)

        run = Run()
        original_dir = run.run_dir
        run._merge_and_migrate({})
        assert run.run_dir == original_dir
        run.stop()

    def test_migrate_same_dir_is_noop(self, tmp_path, monkeypatch):
        """If output_dir resolves to the same location, no move happens."""
        from pubrun.tracker import Run
        monkeypatch.setattr("pathlib.Path.cwd", lambda: tmp_path)

        run = Run()
        original_dir = run.run_dir
        # Point to the same base dir (./runs)
        run._merge_and_migrate({"core": {"output_dir": str(original_dir.parent)}})
        assert run.run_dir == original_dir
        assert original_dir.exists()
        run.stop()

    def test_migrate_enables_subprocess_spy(self, tmp_path, monkeypatch):
        """Enabling subprocess spy mid-run via _merge_and_migrate works."""
        from pubrun.tracker import Run
        from pubrun.capture.subprocesses import SubprocessSpy
        monkeypatch.setattr("pathlib.Path.cwd", lambda: tmp_path)

        run = Run(overrides={"capture": {"subprocesses": {"enabled": False}}})
        assert run._spying_subprocesses is False

        run._merge_and_migrate({"capture": {"subprocesses": {"enabled": True}}})
        assert run._spying_subprocesses is True

        run.stop()

    def test_migrate_failure_does_not_crash(self, tmp_path, monkeypatch):
        """If shutil.move fails, migration logs a warning but doesn't crash."""
        from pubrun.tracker import Run
        import shutil
        monkeypatch.setattr("pathlib.Path.cwd", lambda: tmp_path)

        run = Run()
        original_dir = run.run_dir

        # Make shutil.move fail
        def failing_move(src, dst):
            raise PermissionError("cannot move")

        monkeypatch.setattr(shutil, "move", failing_move)

        new_output = tmp_path / "nope"
        run._merge_and_migrate({"core": {"output_dir": str(new_output)}})

        # Should NOT crash; run_dir stays at the original
        assert run.run_dir == original_dir
        assert original_dir.exists()
        run.stop()


# ==========================================================================
# _bootstrap_engines multi-failure tests
# ==========================================================================

class TestBootstrapEnginesFailures:
    """Test that each engine failure individually promotes to ghost mode."""

    def test_git_failure_ghost_mode(self, tmp_path, monkeypatch):
        """get_git raising promotes to ghost mode."""
        from pubrun.tracker import Run
        monkeypatch.setattr("pathlib.Path.cwd", lambda: tmp_path)
        monkeypatch.setattr("pubrun.tracker.get_git", lambda c: (_ for _ in ()).throw(RuntimeError("git broken")))
        run = Run()
        assert run._outcome == "ghost"

    def test_hardware_failure_ghost_mode(self, tmp_path, monkeypatch):
        """get_hardware raising promotes to ghost mode."""
        from pubrun.tracker import Run
        monkeypatch.setattr("pathlib.Path.cwd", lambda: tmp_path)
        monkeypatch.setattr("pubrun.tracker.get_hardware", lambda c: (_ for _ in ()).throw(RuntimeError("hw broken")))
        run = Run()
        assert run._outcome == "ghost"

    def test_environment_failure_ghost_mode(self, tmp_path, monkeypatch):
        """get_environment raising promotes to ghost mode."""
        from pubrun.tracker import Run
        monkeypatch.setattr("pathlib.Path.cwd", lambda: tmp_path)
        monkeypatch.setattr("pubrun.tracker.get_environment", lambda c: (_ for _ in ()).throw(RuntimeError("env broken")))
        run = Run()
        assert run._outcome == "ghost"

    def test_ghost_run_stop_is_safe(self, tmp_path, monkeypatch):
        """A ghost-mode run can be stopped without error."""
        from pubrun.tracker import Run
        monkeypatch.setattr("pathlib.Path.cwd", lambda: tmp_path)
        monkeypatch.setattr("pubrun.tracker.get_invocation", lambda c: (_ for _ in ()).throw(RuntimeError("fail")))
        run = Run()
        assert run._outcome == "ghost"
        # stop() should not raise
        run.stop()

    def test_ghost_outcome_preserved_after_stop(self, tmp_path, monkeypatch):
        """P3-R5: Ghost outcome must not be overwritten to 'completed' by stop()."""
        from pubrun.tracker import Run
        monkeypatch.setattr("pathlib.Path.cwd", lambda: tmp_path)
        monkeypatch.setattr("pubrun.tracker.get_invocation", lambda c: (_ for _ in ()).throw(RuntimeError("fail")))
        run = Run()
        assert run._outcome == "ghost"
        run.stop()
        assert run._outcome == "ghost"  # Must remain ghost, not overwritten


# ==========================================================================
# P3-T6: resolve_config failure fallback
# ==========================================================================

class TestResolveConfigFallback:
    """P3-T6: Regression test -- broken resolve_config must not crash Run()."""

    def test_resolve_config_failure_falls_back_to_defaults(self, tmp_path, monkeypatch):
        """If resolve_config() raises, Run() uses default config and proceeds."""
        from pubrun.tracker import Run
        from pubrun.config import load_default_config
        monkeypatch.setattr("pathlib.Path.cwd", lambda: tmp_path)
        monkeypatch.setattr("pubrun.tracker.resolve_config", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("TOML parse error")))

        run = Run()
        # Should not crash -- should use defaults
        assert run.is_active is True
        expected_defaults = load_default_config()
        assert run.config == expected_defaults
        run.stop()

    def test_resolve_config_failure_logs_warning(self, tmp_path, monkeypatch, caplog):
        """A failing resolve_config emits a warning log."""
        import logging
        from pubrun.tracker import Run
        monkeypatch.setattr("pathlib.Path.cwd", lambda: tmp_path)
        monkeypatch.setattr("pubrun.tracker.resolve_config", lambda *a, **k: (_ for _ in ()).throw(ValueError("bad config")))

        with caplog.at_level(logging.WARNING, logger="pubrun"):
            run = Run()

        assert any("config resolution failed" in r.message for r in caplog.records)
        run.stop()


class TestStartupManifestAndCrashedFallback:
    """Tests startup manifest writing and updating existing manifests during crashed closeout."""

    def test_startup_manifest_written_immediately(self, tmp_path, monkeypatch):
        """Verifies that starting a run immediately writes manifest.json with outcome 'running'."""
        from pubrun.tracker import Run
        monkeypatch.setattr("pathlib.Path.cwd", lambda: tmp_path)

        run = Run()
        manifest_path = run.run_dir / "manifest.json"
        config_path = run.run_dir / "config.resolved.json"

        assert manifest_path.exists(), "Startup manifest.json was not created!"
        assert config_path.exists(), "Startup config.resolved.json was not created!"

        with open(manifest_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        assert data["status"]["outcome"] == "running"
        assert "git" in data
        assert "host" in data
        
        # Stop tracking cleanly
        run.stop()
        
        with open(manifest_path, "r", encoding="utf-8") as f:
            data_final = json.load(f)
        assert data_final["status"]["outcome"] == "completed"

    def test_crashed_closeout_preserves_and_updates_manifest(self, tmp_path, monkeypatch):
        """Verifies that close_out_crashed_run updates an existing manifest rather than clobbering it."""
        from pubrun.status import close_out_crashed_run
        monkeypatch.setattr("pathlib.Path.cwd", lambda: tmp_path)

        # Create a mock run directory structure
        run_dir = tmp_path / "mock_run"
        run_dir.mkdir()
        
        # Write a mock manifest representing startup state
        manifest_data = {
            "schema_version": "1.0",
            "run": {"run_id": "test-run-123"},
            "status": {"outcome": "running"},
            "timing": {"started_at_utc": 1000.0},
            "host": {"hostname": {"value": "my-mock-host"}},
            "git": {"commit": "mockcommit123"},
            "environment": {"captured_vars": {"FOO": "BAR"}}
        }
        
        manifest_path = run_dir / "manifest.json"
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest_data, f)
            
        # Write a mock lock file
        from pubrun.tracker import Run
        lock_path = run_dir / Run.LOCK_FILENAME
        lock_data = {
            "run_id": "test-run-123",
            "pid": 9999,
            "started_at_utc": 1000.0,
            "script": "sleep.py"
        }
        with open(lock_path, "w", encoding="utf-8") as f:
            json.dump(lock_data, f)

        # Perform closeout
        close_out_crashed_run(run_dir, lock_data)

        # Assert lock file is removed
        assert not lock_path.exists()
        assert manifest_path.exists()

        with open(manifest_path, "r", encoding="utf-8") as f:
            updated_data = json.load(f)

        # The outcome must be updated to crashed
        assert updated_data["status"]["outcome"] == "crashed"
        
        # Timing must be filled
        assert updated_data["timing"]["started_at_utc"] == 1000.0
        assert updated_data["timing"]["ended_at_utc"] is not None
        assert updated_data["timing"]["elapsed_seconds"] is not None
        
        # The other pre-captured static metadata must be fully preserved
        assert updated_data["host"]["hostname"]["value"] == "my-mock-host"
        assert updated_data["git"]["commit"] == "mockcommit123"
        assert updated_data["environment"]["captured_vars"]["FOO"] == "BAR"
