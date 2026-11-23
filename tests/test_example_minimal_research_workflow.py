#!/usr/bin/env python3
"""
Behavior tests for the minimal research workflow example.

Every test runs the example in a pytest temporary directory, so nothing is
written into the repository tree.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import List

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / "examples" / "minimal-research-workflow" / "analysis.py"


def _run(script: Path, cwd: Path, extra_args: List[str]) -> subprocess.CompletedProcess:
    """
    Run an analysis script copy with a small, fast argument set.

    Args:
        script:
            Path to the ``analysis.py`` file to run.
        cwd:
            Working directory for the child process.
        extra_args:
            Additional command-line arguments appended after the defaults.

    Returns:
        subprocess.CompletedProcess:
            The completed child process with captured text output.
    """
    return subprocess.run(
        [sys.executable, str(script), "--seed", "42", "--n", "100", *extra_args],
        cwd=cwd,
        text=True,
        capture_output=True,
        check=False,
    )


def test_minimal_research_workflow_runs(tmp_path: Path) -> None:
    """
    The example runs and writes outputs to ``--output-dir``, not the cwd.

    Args:
        tmp_path:
            Pytest-provided temporary directory.

    Returns:
        None.
    """
    out_dir = tmp_path / "out"

    completed = _run(SCRIPT_PATH, tmp_path, ["--output-dir", str(out_dir)])

    assert completed.returncode == 0, completed.stderr
    assert "Synthetic analysis complete." in completed.stdout
    assert (out_dir / "summary.json").exists()
    assert (out_dir / "synthetic_data.csv").exists()
    assert not (tmp_path / "outputs").exists()

    run_dirs = sorted((tmp_path / "runs").glob("pubrun-analysis-*"))
    assert run_dirs, "Expected pubrun to create at least one run directory."

    latest_run = run_dirs[-1]
    assert (latest_run / "manifest.json").exists()
    assert (latest_run / "config.resolved.json").exists()


def test_default_output_dir_is_next_to_script(tmp_path: Path) -> None:
    """
    Without ``--output-dir``, outputs land next to the script, not in the cwd.

    Args:
        tmp_path:
            Pytest-provided temporary directory.

    Returns:
        None.
    """
    example_dir = tmp_path / "example"
    caller_dir = tmp_path / "caller"
    example_dir.mkdir()
    caller_dir.mkdir()
    script_copy = example_dir / "analysis.py"
    shutil.copy2(SCRIPT_PATH, script_copy)

    completed = _run(script_copy, caller_dir, [])

    assert completed.returncode == 0, completed.stderr
    assert (example_dir / "outputs" / "summary.json").exists()
    assert (example_dir / "outputs" / "synthetic_data.csv").exists()
    assert not (caller_dir / "outputs").exists()


def test_output_dir_is_created_when_missing(tmp_path: Path) -> None:
    """
    A nested, not-yet-existing ``--output-dir`` is created with its parents.

    Args:
        tmp_path:
            Pytest-provided temporary directory.

    Returns:
        None.
    """
    nested = tmp_path / "a" / "b" / "c"
    assert not nested.exists()

    completed = subprocess.run(
        [
            sys.executable,
            str(SCRIPT_PATH),
            "--seed",
            "7",
            "--n",
            "60",
            "--output-dir",
            str(nested),
        ],
        cwd=tmp_path,
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    summary = json.loads((nested / "summary.json").read_text(encoding="utf-8"))
    assert summary["n"] == 60
