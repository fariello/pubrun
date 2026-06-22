#!/usr/bin/env python3
"""
Smoke test for the minimal research workflow example.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def test_minimal_research_workflow_runs(tmp_path: Path) -> None:
    """
    Verify that the minimal research workflow example executes successfully.

    Args:
        tmp_path:
            Pytest-provided temporary directory.

    Returns:
        None.
    """
    repo_root = Path(__file__).resolve().parents[1]
    example_dir = repo_root / "examples" / "minimal-research-workflow"
    script_path = example_dir / "analysis.py"

    completed = subprocess.run(
        [
            sys.executable,
            str(script_path),
            "--seed",
            "42",
            "--n",
            "100",
        ],
        cwd=tmp_path,
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    assert "Synthetic analysis complete." in completed.stdout
    assert (tmp_path / "outputs" / "summary.json").exists()

    run_dirs = sorted((tmp_path / "runs").glob("pubrun-analysis-*"))
    assert run_dirs, "Expected pubrun to create at least one run directory."

    latest_run = run_dirs[-1]
    assert (latest_run / "manifest.json").exists()
    assert (latest_run / "config.resolved.json").exists()

    pass # for auto-indentation
