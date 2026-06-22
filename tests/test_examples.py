import os
import subprocess
import sys
import json
import tempfile
from pathlib import Path

def test_minimal_research_workflow():
    # Setup temporary directory for runs to avoid cluttering workspace
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        runs_dir = tmp_path / "runs"
        
        # Determine paths
        example_dir = Path(__file__).parent.parent / "examples" / "minimal-research-workflow"
        analysis_script = example_dir / "analysis.py"
        
        assert analysis_script.exists(), f"Example script not found at {analysis_script}"
        
        # Run example script with pubrun via subprocess, configuring runs output directory
        env = os.environ.copy()
        # Ensure the package is importable
        env["PYTHONPATH"] = str(Path(__file__).parent.parent / "src")
        
        result = subprocess.run(
            [sys.executable, str(analysis_script)],
            capture_output=True,
            text=True,
            env=env,
            cwd=str(tmp_path),
            check=True
        )
        
        # Assert clean exit
        assert result.returncode == 0
        assert "Analysis complete." in result.stdout
        
        # Assert run directory was created
        assert runs_dir.exists()
        run_dirs = list(runs_dir.glob("pubrun-*"))
        assert len(run_dirs) == 1
        run_dir = run_dirs[0]
        
        # Assert required files exist inside run directory
        manifest_path = run_dir / "manifest.json"
        stdout_log_path = run_dir / "stdout.log"
        raw_data_path = run_dir / "raw_data.csv"
        predictions_path = run_dir / "predictions.csv"
        metrics_path = run_dir / "evaluation_metrics.json"
        
        assert manifest_path.exists()
        assert stdout_log_path.exists()
        assert raw_data_path.exists()
        assert predictions_path.exists()
        assert metrics_path.exists()
        
        # Verify manifest content
        with open(manifest_path, "r", encoding="utf-8") as f:
            manifest = json.load(f)
            
        # Verify outcome
        assert manifest["status"]["outcome"] == "completed"
        
        # Verify custom annotations and phases exist in events.jsonl
        events = []
        with open(run_dir / "events.jsonl", "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    events.append(json.loads(line))
                    
        # Verify phases recorded (type: phase_start)
        phase_starts = [e["name"] for e in events if e.get("type") == "phase_start"]
        assert "data_generation" in phase_starts
        assert "model_fitting" in phase_starts
        assert "model_evaluation" in phase_starts
        
        # Verify custom annotations (type: annotation)
        annotations = [e for e in events if e.get("type") == "annotation"]
        annotation_names = [ann["name"] for ann in annotations]
        
        assert "Generated synthetic dataset." in annotation_names
        assert "Linear model fitting complete." in annotation_names
        assert "Evaluation complete and artifacts saved." in annotation_names
        
        # Verify reports and artifacts logged in annotations
        assert "report: evaluation_metrics" in annotation_names
        assert "artifact: raw_data.csv" in annotation_names
        assert "artifact: predictions.csv" in annotation_names
        
        # Verify metrics file content
        with open(metrics_path, "r", encoding="utf-8") as f:
            metrics = json.load(f)
        assert metrics["model_type"] == "LinearRegression"
        assert "coefficients" in metrics
        assert "metrics" in metrics
