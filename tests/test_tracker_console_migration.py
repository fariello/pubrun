"""Subprocess test for console tee re-pointing after output-directory migration."""
import os
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

SRC_DIR = str(Path(__file__).resolve().parent.parent / "src")


def _child_env(tmp_path: Path) -> dict:
    env = dict(os.environ)
    env["PYTHONPATH"] = SRC_DIR + os.pathsep + env.get("PYTHONPATH", "")
    env["HOME"] = str(tmp_path)
    env["USERPROFILE"] = str(tmp_path)
    env["APPDATA"] = str(tmp_path / ".appdata")
    env["XDG_CONFIG_HOME"] = str(tmp_path / ".xdg")
    for key in (
        "PUBRUN_DISABLE",
        "PUBRUN_AUTO_START",
        "PUBRUN_IMPORT_MODE",
        "PUBRUN_PROFILE",
        "PUBRUN_META_REF",
    ):
        env.pop(key, None)
    return env


@pytest.mark.skipif(
    sys.platform == "win32",
    reason="Open file handles prevent shutil.move on Windows",
)
def test_console_lines_after_migration_land_in_migrated_logs(tmp_path: Path) -> None:
    """Console output written before and after output_dir migration reaches migrated logs."""
    (tmp_path / ".pubrun.toml").write_text(
        textwrap.dedent(
            """\
            [console]
            capture_mode = "basic"
            non_tty_mode = "basic"
            """
        ),
        encoding="utf-8",
    )
    script = tmp_path / "child_script.py"
    script.write_text(
        textwrap.dedent(
            """\
            import sys
            import pubrun

            print("before-out", flush=True)
            print("before-err", file=sys.stderr, flush=True)
            pubrun.start(output_dir="moved")
            print("after-out", flush=True)
            print("after-err", file=sys.stderr, flush=True)
            """
        ),
        encoding="utf-8",
    )

    res = subprocess.run(
        [sys.executable, str(script)],
        cwd=tmp_path,
        env=_child_env(tmp_path),
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert res.returncode == 0, res.stderr

    stdout_logs = sorted((tmp_path / "moved").glob("*/stdout.log"))
    assert len(stdout_logs) == 1, f"expected one migrated run with stdout.log, found {stdout_logs}"
    run_dir = stdout_logs[0].parent

    stdout_text = stdout_logs[0].read_text(encoding="utf-8")
    stderr_text = (run_dir / "stderr.log").read_text(encoding="utf-8")
    assert "before-out" in stdout_text, stdout_text
    assert "after-out" in stdout_text, stdout_text
    assert "before-err" in stderr_text, stderr_text
    assert "after-err" in stderr_text, stderr_text
