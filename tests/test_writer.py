import json
import pytest
from pathlib import Path
from pubrun.writer import _atomic_json_write, ArtifactWriter

def test_atomic_json_write_success(tmp_path):
    target = tmp_path / "test.json"
    data = {"key": "value", "list": [1, 2, 3]}
    
    _atomic_json_write(target, data)
    
    assert target.exists()
    # Confirm tmp file is cleaned up
    assert not target.with_suffix(".json.tmp").exists()
    
    with open(target, "r", encoding="utf-8") as f:
        loaded = json.load(f)
    assert loaded == data

def test_atomic_json_write_failure_cleanup(tmp_path):
    target = tmp_path / "test_fail.json"
    # An object that is not JSON serializable to trigger ValueError/TypeError in json.dump
    class Unserializable:
        pass
    
    data = {"key": Unserializable()}
    
    with pytest.raises(TypeError):
        _atomic_json_write(target, data)
        
    assert not target.exists()
    # Verify that the temp file is cleaned up and does not leak
    assert not target.with_suffix(".json.tmp").exists()

class DummyRun:
    def __init__(self, run_dir, config):
        self.run_dir = run_dir
        self.config = config
        self._finalized = False
        self.finalize_called = 0
        self.to_manifest_called = 0

    def _finalize_state(self):
        self._finalized = True
        self.finalize_called += 1

    def to_manifest_dict(self):
        self.to_manifest_called += 1
        return {"run_id": "dummy_id"}

def test_artifact_writer_success(tmp_path):
    run_dir = tmp_path / "run_dir"
    config = {"methods": {"format": "markdown"}}
    run = DummyRun(run_dir, config)
    
    writer = ArtifactWriter(run)
    writer.write_artifacts()
    
    assert run.finalize_called == 1
    assert run.to_manifest_called == 1
    assert (run_dir / "manifest.json").exists()
    assert (run_dir / "config.resolved.json").exists()
    assert (run_dir / "methods.md").exists()

def test_artifact_writer_latex_format(tmp_path):
    run_dir = tmp_path / "run_dir"
    config = {"methods": {"format": "latex"}}
    run = DummyRun(run_dir, config)
    
    writer = ArtifactWriter(run)
    writer.write_artifacts()
    
    assert (run_dir / "methods.tex").exists()
