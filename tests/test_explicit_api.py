import os
import sys
import json
import pytest
from pathlib import Path
import pubrun

def test_report_and_artifact(tmp_path):
    import pubrun.tracker
    pubrun.tracker._active_run = None
    
    old_cwd = Path.cwd
    try:
        Path.cwd = staticmethod(lambda: tmp_path)
        tracker = pubrun.start(console={"capture_mode": "off"})
        
        # Test report
        pubrun.report("eval_metrics", {"accuracy": 0.985})
        report_file = tracker.run_dir / "eval_metrics.json"
        assert report_file.exists()
        with open(report_file, "r") as f:
            data = json.load(f)
        assert data["accuracy"] == 0.985
        
        # Test string report
        pubrun.report("raw_text", "some plain text")
        txt_file = tracker.run_dir / "raw_text.txt"
        assert txt_file.exists()
        assert txt_file.read_text().strip() == "some plain text"
        
        # Test artifact
        pubrun.artifact("output.bin", b"\x00\x01\x02")
        bin_file = tracker.run_dir / "output.bin"
        assert bin_file.exists()
        assert bin_file.read_bytes() == b"\x00\x01\x02"
        
        # Test text artifact
        pubrun.artifact("output.txt", "hello")
        artifact_txt = tracker.run_dir / "output.txt"
        assert artifact_txt.exists()
        assert artifact_txt.read_text().strip() == "hello"
        
        tracker.stop()
    finally:
        Path.cwd = old_cwd
        pubrun.tracker._active_run = None


def test_pubrun_print(tmp_path):
    import pubrun.tracker
    pubrun.tracker._active_run = None
    old_cwd = Path.cwd
    try:
        Path.cwd = staticmethod(lambda: tmp_path)
        tracker = pubrun.start(console={"capture_mode": "off"})
        
        pubrun.print("hello", "world", sep="-")
        
        log_file = tracker.run_dir / "stdout.log"
        assert log_file.exists()
        content = log_file.read_text()
        assert "hello-world" in content
        
        tracker.stop()
    finally:
        Path.cwd = old_cwd
        pubrun.tracker._active_run = None


def test_pubrun_open_provenance(tmp_path):
    import pubrun.tracker
    pubrun.tracker._active_run = None
    old_cwd = Path.cwd
    try:
        Path.cwd = staticmethod(lambda: tmp_path)
        
        input_file = tmp_path / "dataset.txt"
        input_file.write_text("dataset content line 1\nline 2", encoding="utf-8")
        
        tracker = pubrun.start(console={"capture_mode": "off"})
        
        with pubrun.open(input_file, "r") as f:
            lines = f.readlines()
        assert len(lines) == 2
        
        output_file = tmp_path / "output_data.bin"
        with pubrun.open(output_file, "wb") as f:
            f.write(b"output data content")
            
        tracker.stop()
        
        manifest_path = tracker.run_dir / "manifest.json"
        assert manifest_path.exists()
        with open(manifest_path, "r") as f:
            manifest = json.load(f)
            
        assert "data_files" in manifest
        inputs = manifest["data_files"]["inputs"]
        outputs = manifest["data_files"]["outputs"]
        
        assert len(inputs) == 1
        assert inputs[0]["path"] == str(input_file.resolve())
        assert inputs[0]["size_bytes"] == len("dataset content line 1\nline 2")
        import hashlib
        expected_sha = hashlib.sha256(b"dataset content line 1\nline 2").hexdigest()
        assert inputs[0]["sha256"] == expected_sha
        
        assert len(outputs) == 1
        assert outputs[0]["path"] == str(output_file.resolve())
        assert outputs[0]["size_bytes"] == len(b"output data content")
        expected_out_sha = hashlib.sha256(b"output data content").hexdigest()
        assert outputs[0]["sha256"] == expected_out_sha
        
    finally:
        Path.cwd = old_cwd
        pubrun.tracker._active_run = None


def test_explicit_subprocess_and_popen(tmp_path):
    import pubrun.tracker
    pubrun.tracker._active_run = None
    old_cwd = Path.cwd
    try:
        Path.cwd = staticmethod(lambda: tmp_path)
        tracker = pubrun.start(console={"capture_mode": "off"})
        
        res = pubrun.subprocess.run([sys.executable, "-c", "print('explicit subprocess')"], capture_output=True, text=True)
        assert res.returncode == 0
        assert "explicit subprocess" in res.stdout
        
        with pubrun.popen(f"{sys.executable} -c \"print('explicit popen')\"") as pipe:
            out = pipe.read()
        assert "explicit popen" in out
        
        tracker.stop()
        
        manifest_path = tracker.run_dir / "manifest.json"
        assert manifest_path.exists()
        with open(manifest_path, "r") as f:
            manifest = json.load(f)
            
        subprocs = manifest.get("subprocesses", [])
        assert len(subprocs) == 2
        cmd_argvs = [s["argv"] for s in subprocs]
        assert any("explicit subprocess" in str(arg) for arg in cmd_argvs)
        assert any("explicit popen" in str(arg) for arg in cmd_argvs)
        
    finally:
        Path.cwd = old_cwd
        pubrun.tracker._active_run = None
