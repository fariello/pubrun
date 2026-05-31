import json
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
