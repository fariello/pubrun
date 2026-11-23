"""Child Python processes spawned by tests must import ``pubrun`` from this checkout's ``src``."""
import os
import pathlib
import subprocess
import sys

_REPO_SRC = pathlib.Path(__file__).resolve().parents[1] / "src"
_EXPECTED_INIT = os.path.realpath(_REPO_SRC / "pubrun" / "__init__.py")
_PROBE = "import os, pubrun; print(os.path.realpath(pubrun.__file__))"


def test_inherited_env_child_imports_pubrun_from_this_checkout(tmp_path):
    result = subprocess.run(
        [sys.executable, "-c", _PROBE],
        capture_output=True,
        text=True,
        timeout=60,
        cwd=str(tmp_path),
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == _EXPECTED_INIT


def test_child_prefers_this_checkout_over_a_later_pythonpath_entry(tmp_path):
    decoy_root = tmp_path / "decoy"
    decoy_pkg = decoy_root / "pubrun"
    decoy_pkg.mkdir(parents=True)
    (decoy_pkg / "__init__.py").write_text("DECOY = True\n", encoding="utf-8")

    env = dict(os.environ)
    inherited = env.get("PYTHONPATH")
    env["PYTHONPATH"] = (
        f"{inherited}{os.pathsep}{decoy_root}" if inherited else str(decoy_root)
    )
    result = subprocess.run(
        [sys.executable, "-c", _PROBE],
        capture_output=True,
        text=True,
        timeout=60,
        cwd=str(tmp_path),
        env=env,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == _EXPECTED_INIT


def test_pythonpath_starts_with_this_checkout_src():
    first = os.environ["PYTHONPATH"].split(os.pathsep)[0]
    assert os.path.realpath(first) == os.path.realpath(_REPO_SRC)
