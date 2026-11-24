"""Smoke tests for the numbered example scripts under examples/."""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[1]
_SRC = _REPO / "src"
_EXAMPLES = sorted((_REPO / "examples").glob("[0-9]*.py"), key=lambda p: p.name)


@pytest.mark.parametrize(
    "example_script",
    _EXAMPLES or [None],
    ids=lambda p: p.name if p is not None else "missing",
)
def test_example_runs_and_creates_manifest(example_script: Path | None, tmp_path: Path) -> None:
    """Each numbered example runs cleanly in an isolated directory and writes a manifest."""
    assert _EXAMPLES and example_script is not None, "no examples/[0-9]*.py scripts found"

    env = os.environ.copy()
    existing_pythonpath = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = (
        f"{_SRC}{os.pathsep}{existing_pythonpath}" if existing_pythonpath else str(_SRC)
    )
    config_dir = tmp_path / "xdg_config"
    appdata_dir = tmp_path / "appdata"
    config_dir.mkdir(exist_ok=True)
    appdata_dir.mkdir(exist_ok=True)
    env["XDG_CONFIG_HOME"] = str(config_dir)
    env["APPDATA"] = str(appdata_dir)

    result = subprocess.run(
        [sys.executable, str(example_script)],
        cwd=tmp_path,
        env=env,
        timeout=120,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, (
        f"{example_script.name} exited {result.returncode}\n"
        f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    )
    assert "[PASS]" in result.stdout, (
        f"{example_script.name} did not report [PASS]\nstdout:\n{result.stdout}"
    )
    manifests = list(tmp_path.glob("runs/*/manifest.json"))
    assert manifests, f"{example_script.name} created no runs/*/manifest.json in {tmp_path}"
