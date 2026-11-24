"""Behavioral regression tests for runtime effects of the mypy type repairs."""

import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict

from pubrun.report.reproducibility import compare_with_current_environment


def _find_check(result: Dict[str, Any], name: str) -> Dict[str, Any]:
    """Return the single preflight check with the given name."""
    matches = [c for c in result["checks"] if c.get("name") == name]
    assert len(matches) == 1, f"Expected 1 check named {name!r}, got {matches!r}"
    return matches[0]


def test_report_bug_does_not_load_package_twice() -> None:
    """Calling _run_bug_report must not load pubrun.__init__ as a second module."""
    repo_src = Path(__file__).resolve().parents[1] / "src"
    child_code = (
        "import contextlib, io, sys, webbrowser\n"
        "webbrowser.open = lambda url: True\n"
        "import pubrun.__main__ as main_mod\n"
        "with contextlib.redirect_stdout(io.StringIO()):\n"
        "    main_mod._run_bug_report()\n"
        "print('pubrun.__init__' in sys.modules)\n"
    )
    env = os.environ.copy()
    env["PYTHONPATH"] = str(repo_src)
    env["PUBRUN_IMPORT_MODE"] = "noauto"

    proc = subprocess.run(
        [sys.executable, "-c", child_code],
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, f"Child failed (rc={proc.returncode}): {proc.stderr}"
    lines = [line.strip() for line in proc.stdout.splitlines() if line.strip()]
    assert lines, f"Expected output from child process, got empty stdout (stderr={proc.stderr!r})"
    assert lines[-1] == "False"


def test_working_directory_path_is_stripped(tmp_path: Path) -> None:
    """Recorded working directory paths must be stripped before comparison and reporting."""
    manifest: Dict[str, Any] = {
        "invocation": {
            "working_directory": {"path": f"  {tmp_path}  "},
            "argv": ["x"],
        }
    }
    result = compare_with_current_environment(manifest, cwd=str(tmp_path))
    chk = _find_check(result, "working_directory")
    assert chk["details"]["recorded_working_directory"] == str(tmp_path)


def test_blank_working_directory_is_not_checked(tmp_path: Path) -> None:
    """Whitespace-only working directory paths must be treated as absent."""
    manifest: Dict[str, Any] = {
        "invocation": {
            "working_directory": {"path": "   "},
            "argv": ["x"],
        }
    }
    result = compare_with_current_environment(manifest, cwd=str(tmp_path))
    chk = _find_check(result, "working_directory")
    assert chk["message"] == "No working directory path was recorded in the manifest."


def test_entrypoint_script_path_is_stripped(tmp_path: Path) -> None:
    """Recorded entrypoint script paths must be stripped before resolving locally."""
    script = tmp_path / "train.py"
    script.write_text("print('ok')\n", encoding="utf-8")
    manifest: Dict[str, Any] = {
        "invocation": {
            "entrypoint_type": "script",
            "script": {"path": f"  {script}  "},
            "argv": ["x"],
        }
    }
    result = compare_with_current_environment(manifest, cwd=str(tmp_path))
    chk = _find_check(result, "entrypoint_script")
    assert chk["details"]["resolved_path"] == str(script)
    assert "exists locally" in chk["message"]
