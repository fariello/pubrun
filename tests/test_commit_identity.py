"""Behavioral tests for deferred, ownership-verified commit identity resolution,
build-time metadata stamping (`hatch_build.py`), retired post-commit hook
cleanup (`scripts/update_commit_file.py`), and single-read boot TOML loading.
"""
from __future__ import annotations

import builtins
import importlib
import importlib.util
import json
import os
import shutil
import stat
import subprocess
import sys
import time
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Dict, List, Optional

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_PUBRUN = REPO_ROOT / "src" / "pubrun"

SHA_40_A = "a" * 40
SHA_40_B = "b" * 40
SHA_64_C = "c" * 64


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _clean_git_env(extra: Optional[Dict[str, str]] = None) -> Dict[str, str]:
    env = {
        k: v
        for k, v in os.environ.items()
        if k
        not in (
            "GIT_DIR",
            "GIT_WORK_TREE",
            "GIT_COMMON_DIR",
            "GIT_INDEX_FILE",
            "PUBRUN_IMPORT_MODE",
            "PUBRUN_AUTO_START",
        )
    }
    if extra:
        env.update(extra)
    return env


def _init_git_repo(repo_dir: Path, filename: str = "hello.txt", content: str = "hi\n") -> str:
    """Create a real minimal Git repository and return its 40-hex HEAD SHA."""
    repo_dir.mkdir(parents=True, exist_ok=True)
    env = _clean_git_env()
    subprocess.run(["git", "init"], cwd=str(repo_dir), env=env, check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"],
        cwd=str(repo_dir),
        env=env,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test User"],
        cwd=str(repo_dir),
        env=env,
        check=True,
        capture_output=True,
    )
    (repo_dir / filename).write_text(content, encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=str(repo_dir), env=env, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "initial"],
        cwd=str(repo_dir),
        env=env,
        check=True,
        capture_output=True,
    )
    proc = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=str(repo_dir),
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )
    return proc.stdout.strip()


def _copy_pubrun_package(dest_pkg_dir: Path) -> None:
    """Copy src/pubrun cleanly into dest_pkg_dir without bytecode or commit files."""
    if dest_pkg_dir.exists():
        shutil.rmtree(dest_pkg_dir)
    shutil.copytree(
        SRC_PUBRUN,
        dest_pkg_dir,
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "COMMIT", "_build_meta.json"),
    )


def _create_simulated_wheel(
    site_packages: Path,
    version: str = "1.3.1",
    build_meta: Optional[str] = None,
    commit_file: Optional[str] = None,
) -> Path:
    """Create a simulated installed wheel with matching .dist-info/METADATA."""
    pkg_dir = site_packages / "pubrun"
    _copy_pubrun_package(pkg_dir)
    dist_info = site_packages / f"pubrun-{version}.dist-info"
    dist_info.mkdir(parents=True, exist_ok=True)
    (dist_info / "METADATA").write_text(
        f"Metadata-Version: 2.1\nName: pubrun\nVersion: {version}\n",
        encoding="utf-8",
    )
    if build_meta is not None:
        (pkg_dir / "_build_meta.json").write_text(build_meta, encoding="utf-8")
    if commit_file is not None:
        (pkg_dir / "COMMIT").write_text(commit_file, encoding="utf-8")
    return pkg_dir


def _create_fake_git(bin_dir: Path, python_body: str) -> Path:
    """Place a cross-platform fake `git` executable inside bin_dir."""
    bin_dir.mkdir(parents=True, exist_ok=True)
    driver = bin_dir / "_fake_git.py"
    driver.write_text(python_body, encoding="utf-8")

    if os.name == "nt":
        shim = bin_dir / "git.cmd"
        shim.write_text(f'@echo off\r\n"{sys.executable}" "{driver}" %*\r\n', encoding="utf-8")
    else:
        shim = bin_dir / "git"
        shim.write_text(f'#!/bin/sh\nexec "{sys.executable}" "{driver}" "$@"\n', encoding="utf-8")
        shim.chmod(shim.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    return shim


def _run_python_isolated(
    code: str,
    pythonpath: Path,
    cwd: Path,
    extra_env: Optional[Dict[str, str]] = None,
    prepend_path: Optional[Path] = None,
    override_path: Optional[str] = None,
    timeout: float = 15.0,
) -> subprocess.CompletedProcess:
    """Execute Python in a fresh subprocess loading pubrun strictly from pythonpath."""
    env = _clean_git_env(extra_env)
    env["PYTHONPATH"] = str(pythonpath)
    if override_path is not None:
        env["PATH"] = override_path
    elif prepend_path is not None:
        env["PATH"] = f"{prepend_path}{os.pathsep}{env.get('PATH', '')}"

    # Prepend pythonpath cleanly and strip any editable repo/src entry that could shadow it.
    prelude = (
        "import os, sys\n"
        f"_target = os.path.realpath({str(pythonpath)!r})\n"
        f"_repo_src = os.path.realpath({str(REPO_ROOT / 'src')!r})\n"
        "if _target != _repo_src:\n"
        "    sys.path = [p for p in sys.path if os.path.realpath(p) != _repo_src]\n"
        "if not sys.path or os.path.realpath(sys.path[0]) != _target:\n"
        "    sys.path.insert(0, _target)\n"
    )
    return subprocess.run(
        [sys.executable, "-c", prelude + code],
        cwd=str(cwd),
        env=env,
        capture_output=True,
        text=True,
        timeout=timeout,
    )


def _load_module_from_path(name: str, file_path: Path):
    spec = importlib.util.spec_from_file_location(name, str(file_path))
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ---------------------------------------------------------------------------
# 1. Zero-Git import tests
# ---------------------------------------------------------------------------


class TestZeroGitImport:
    """Importing pubrun.minimal, pubrun.noauto, or non-auto pubrun never spawns git."""

    @pytest.mark.parametrize("import_stmt", ["import pubrun.minimal", "import pubrun.noauto"])
    def test_source_checkout_import_spawns_zero_git(self, tmp_path: Path, import_stmt: str) -> None:
        log_file = tmp_path / "git_calls.log"
        bin_dir = tmp_path / "bin"
        _create_fake_git(
            bin_dir,
            (
                "import json, sys\n"
                f"with open({str(log_file)!r}, 'a', encoding='utf-8') as f:\n"
                "    f.write(json.dumps(sys.argv[1:]) + '\\n')\n"
                "sys.exit(99)\n"
            ),
        )
        code = (
            "import json, sys\n"
            f"{import_stmt}\n"
            "import pubrun\n"
            "print(json.dumps({\n"
            "    'file': pubrun.__file__,\n"
            "    'has_commit_in_dir': '__commit__' in dir(pubrun),\n"
            "    'has_commit_in_all': '__commit__' in pubrun.__all__,\n"
            "}))\n"
        )
        res = _run_python_isolated(
            code,
            pythonpath=REPO_ROOT / "src",
            cwd=tmp_path,
            prepend_path=bin_dir,
        )
        assert res.returncode == 0, f"stderr: {res.stderr}"
        data = json.loads(res.stdout.strip())
        assert data["has_commit_in_dir"] is True
        assert data["has_commit_in_all"] is True
        assert not log_file.exists(), f"Unexpected git calls: {log_file.read_text()}"

    @pytest.mark.parametrize("import_stmt", ["import pubrun.minimal", "import pubrun.noauto"])
    def test_installed_wheel_import_spawns_zero_git(self, tmp_path: Path, import_stmt: str) -> None:
        site_packages = tmp_path / "site-packages"
        _create_simulated_wheel(
            site_packages,
            version="1.3.1",
            build_meta=json.dumps({"commit": SHA_40_A, "version": "1.3.1"}) + "\n",
        )
        log_file = tmp_path / "git_calls.log"
        bin_dir = tmp_path / "bin"
        _create_fake_git(
            bin_dir,
            (
                "import json, sys\n"
                f"with open({str(log_file)!r}, 'a', encoding='utf-8') as f:\n"
                "    f.write(json.dumps(sys.argv[1:]) + '\\n')\n"
                "sys.exit(99)\n"
            ),
        )
        code = (
            "import json, os\n"
            f"{import_stmt}\n"
            "import pubrun\n"
            "print(json.dumps({'file': os.path.realpath(pubrun.__file__)}))\n"
        )
        res = _run_python_isolated(
            code,
            pythonpath=site_packages,
            cwd=tmp_path,
            prepend_path=bin_dir,
        )
        assert res.returncode == 0, f"stderr: {res.stderr}"
        data = json.loads(res.stdout.strip())
        assert os.path.realpath(str(site_packages)) in data["file"]
        assert not log_file.exists(), f"Unexpected git calls: {log_file.read_text()}"

    @pytest.mark.parametrize("mode", ["minimal", "noauto"])
    def test_root_import_with_non_autostart_mode_spawns_zero_git(
        self, tmp_path: Path, mode: str
    ) -> None:
        log_file = tmp_path / "git_calls.log"
        bin_dir = tmp_path / "bin"
        _create_fake_git(
            bin_dir,
            (
                "import json, sys\n"
                f"with open({str(log_file)!r}, 'a', encoding='utf-8') as f:\n"
                "    f.write(json.dumps(sys.argv[1:]) + '\\n')\n"
                "sys.exit(99)\n"
            ),
        )
        res = _run_python_isolated(
            "import pubrun\nprint(pubrun.get_current_run() is None)\n",
            pythonpath=REPO_ROOT / "src",
            cwd=tmp_path,
            extra_env={"PUBRUN_IMPORT_MODE": mode},
            prepend_path=bin_dir,
        )
        assert res.returncode == 0, f"stderr: {res.stderr}"
        assert res.stdout.strip() == "True"
        assert not log_file.exists()


# ---------------------------------------------------------------------------
# 2. Installed wheel, nested repository isolation, and packaged metadata cases
# ---------------------------------------------------------------------------


class TestInstalledWheelCommitIdentity:
    """Installed packages read version-checked build metadata and never invoke git."""

    def test_nested_repo_wheel_reports_packaged_commit_without_git(self, tmp_path: Path) -> None:
        outer_repo = tmp_path / "user_project"
        outer_sha = _init_git_repo(outer_repo)
        assert outer_sha != SHA_40_A

        site_packages = outer_repo / ".venv" / "site-packages"
        _create_simulated_wheel(
            site_packages,
            version="2.5.0",
            build_meta=json.dumps({"commit": SHA_40_A, "version": "2.5.0"}) + "\n",
        )
        log_file = tmp_path / "git_calls.log"
        bin_dir = tmp_path / "bin"
        _create_fake_git(
            bin_dir,
            (
                "import json, sys\n"
                f"with open({str(log_file)!r}, 'a', encoding='utf-8') as f:\n"
                "    f.write(json.dumps(sys.argv[1:]) + '\\n')\n"
                "sys.exit(99)\n"
            ),
        )
        code = (
            "import json, os\n"
            "import pubrun.minimal as _m\n"
            "import pubrun\n"
            "from pubrun import __commit__ as imported_commit\n"
            "unknown_raised = False\n"
            "try:\n"
            "    getattr(pubrun, 'definitely_not_a_real_symbol')\n"
            "except AttributeError:\n"
            "    unknown_raised = True\n"
            "print(json.dumps({\n"
            "    'version': pubrun.__version__,\n"
            "    'commit': pubrun.__commit__,\n"
            "    'imported_commit': imported_commit,\n"
            "    'in_dir': '__commit__' in dir(pubrun),\n"
            "    'in_all': '__commit__' in pubrun.__all__,\n"
            "    'unknown_raised': unknown_raised,\n"
            "    'file': os.path.realpath(pubrun.__file__),\n"
            "}))\n"
        )
        res = _run_python_isolated(
            code,
            pythonpath=site_packages,
            cwd=outer_repo,
            prepend_path=bin_dir,
        )
        assert res.returncode == 0, f"stderr: {res.stderr}"
        data = json.loads(res.stdout.strip())
        assert data["version"] == "2.5.0"
        assert data["commit"] == SHA_40_A
        assert data["imported_commit"] == SHA_40_A
        assert data["commit"] != outer_sha
        assert data["in_dir"] is True
        assert data["in_all"] is True
        assert data["unknown_raised"] is True
        assert not log_file.exists(), f"Unexpected git calls: {log_file.read_text()}"

    @pytest.mark.parametrize(
        "build_meta,commit_file,expected",
        [
            (None, None, None),
            ("{not valid json", SHA_40_B + "\n", None),
            (json.dumps(["not", "a", "dict"]), SHA_40_B + "\n", None),
            (json.dumps({"commit": SHA_40_A}), SHA_40_B + "\n", None),
            (json.dumps({"commit": SHA_40_A, "version": ""}), SHA_40_B + "\n", None),
            (json.dumps({"commit": "not-a-hex-sha", "version": "1.3.1"}), SHA_40_B + "\n", None),
            (json.dumps({"commit": SHA_40_A, "version": "0.9.9"}), SHA_40_B + "\n", None),
            (None, SHA_40_B + "\n", SHA_40_B),
            (None, SHA_64_C + "\n", SHA_64_C),
            (None, "short-invalid-sha\n", None),
            (None, "   \n", None),
            (json.dumps({"commit": SHA_64_C, "version": "1.3.1"}), None, SHA_64_C),
        ],
    )
    def test_packaged_metadata_validation_and_legacy_fallback(
        self,
        tmp_path: Path,
        build_meta: Optional[str],
        commit_file: Optional[str],
        expected: Optional[str],
    ) -> None:
        site_packages = tmp_path / "site-packages"
        _create_simulated_wheel(
            site_packages,
            version="1.3.1",
            build_meta=build_meta,
            commit_file=commit_file,
        )
        log_file = tmp_path / "git_calls.log"
        bin_dir = tmp_path / "bin"
        _create_fake_git(
            bin_dir,
            (
                "import sys\n"
                f"open({str(log_file)!r}, 'a', encoding='utf-8').write('called\\n')\n"
                "sys.exit(99)\n"
            ),
        )
        code = (
            "import json\n"
            "import pubrun.minimal\n"
            "import pubrun\n"
            "print(json.dumps({'commit': pubrun.__commit__, 'version': pubrun.__version__}))\n"
        )
        res = _run_python_isolated(
            code,
            pythonpath=site_packages,
            cwd=tmp_path,
            prepend_path=bin_dir,
        )
        assert res.returncode == 0, f"stderr: {res.stderr}"
        data = json.loads(res.stdout.strip())
        assert data["version"] == "1.3.1"
        assert data["commit"] == expected
        assert not log_file.exists()


# ---------------------------------------------------------------------------
# 3. Verified source checkout cases
# ---------------------------------------------------------------------------


def _create_verified_checkout(repo_dir: Path, project_name: str = "pubrun") -> str:
    """Create a real temporary verified pubrun Git checkout and return its HEAD SHA."""
    repo_dir.mkdir(parents=True, exist_ok=True)
    (repo_dir / "pyproject.toml").write_text(
        f'[project]\nname = "{project_name}"\nversion = "1.3.1"\n',
        encoding="utf-8",
    )
    _copy_pubrun_package(repo_dir / "src" / "pubrun")
    return _init_git_repo(repo_dir, filename="README.md", content="# temp checkout\n")


class TestSourceCheckoutCommitIdentity:
    """Verified source checkouts resolve live HEAD lazily with strict ownership checks."""

    def test_live_head_cached_and_resettable(self, tmp_path: Path) -> None:
        repo_dir = tmp_path / "pubrun_checkout"
        expected_sha = _create_verified_checkout(repo_dir)
        real_git = shutil.which("git")
        assert real_git is not None

        log_file = tmp_path / "git_calls.log"
        bin_dir = tmp_path / "bin"
        _create_fake_git(
            bin_dir,
            (
                "import json, subprocess, sys\n"
                f"with open({str(log_file)!r}, 'a', encoding='utf-8') as f:\n"
                "    f.write(json.dumps(sys.argv[1:]) + '\\n')\n"
                f"res = subprocess.run([{real_git!r}] + sys.argv[1:])\n"
                "sys.exit(res.returncode)\n"
            ),
        )
        code = (
            "import json\n"
            "import pubrun.minimal\n"
            "import pubrun\n"
            "c1 = pubrun.__commit__\n"
            "c2 = pubrun.__commit__\n"
            "from pubrun import __commit__ as c3\n"
            "pubrun._reset_commit_cache()\n"
            "c4 = pubrun.__commit__\n"
            "print(json.dumps({'c1': c1, 'c2': c2, 'c3': c3, 'c4': c4}))\n"
        )
        res = _run_python_isolated(
            code,
            pythonpath=repo_dir / "src",
            cwd=tmp_path,
            prepend_path=bin_dir,
        )
        assert res.returncode == 0, f"stderr: {res.stderr}"
        data = json.loads(res.stdout.strip())
        assert data == {
            "c1": expected_sha,
            "c2": expected_sha,
            "c3": expected_sha,
            "c4": expected_sha,
        }
        calls = log_file.read_text(encoding="utf-8").strip().splitlines()
        # Once for c1 (c2 and c3 hit cache), and once after _reset_commit_cache() for c4.
        assert len(calls) == 2

    def test_inherited_git_dir_override_is_ignored(self, tmp_path: Path) -> None:
        repo_dir = tmp_path / "pubrun_checkout"
        expected_sha = _create_verified_checkout(repo_dir)

        other_repo = tmp_path / "other_repo"
        other_sha = _init_git_repo(other_repo)
        assert other_sha != expected_sha

        code = (
            "import json\n"
            "import pubrun.minimal\n"
            "import pubrun\n"
            "print(json.dumps({'commit': pubrun.__commit__}))\n"
        )
        res = _run_python_isolated(
            code,
            pythonpath=repo_dir / "src",
            cwd=other_repo,
            extra_env={
                "GIT_DIR": str(other_repo / ".git"),
                "GIT_WORK_TREE": str(other_repo),
            },
        )
        assert res.returncode == 0, f"stderr: {res.stderr}"
        data = json.loads(res.stdout.strip())
        assert data["commit"] == expected_sha

    def test_lazy_commit_resolution_does_not_leak_into_subprocess_spy(
        self, tmp_path: Path
    ) -> None:
        repo_dir = tmp_path / "pubrun_checkout"
        expected_sha = _create_verified_checkout(repo_dir)

        code = (
            "import json\n"
            "import pubrun.noauto\n"
            "import pubrun\n"
            "from pubrun.capture.subprocesses import SubprocessSpy\n"
            "SubprocessSpy.install()\n"
            "try:\n"
            "    pubrun._reset_commit_cache()\n"
            "    commit = pubrun.__commit__\n"
            "    records = list(SubprocessSpy.get_records())\n"
            "finally:\n"
            "    SubprocessSpy.uninstall()\n"
            "print(json.dumps({'commit': commit, 'records': records}))\n"
        )
        res = _run_python_isolated(
            code,
            pythonpath=repo_dir / "src",
            cwd=tmp_path,
        )
        assert res.returncode == 0, f"stderr: {res.stderr}"
        data = json.loads(res.stdout.strip())
        assert data["commit"] == expected_sha
        assert data["records"] == []

    def test_missing_git_returns_none_even_with_stale_commit_file(self, tmp_path: Path) -> None:
        repo_dir = tmp_path / "pubrun_checkout"
        _create_verified_checkout(repo_dir)
        (repo_dir / "src" / "pubrun" / "COMMIT").write_text(SHA_40_B + "\n", encoding="utf-8")

        empty_bin = tmp_path / "empty_bin"
        empty_bin.mkdir()
        code = (
            "import json\n"
            "import pubrun.minimal\n"
            "import pubrun\n"
            "print(json.dumps({'commit': pubrun.__commit__}))\n"
        )
        res = _run_python_isolated(
            code,
            pythonpath=repo_dir / "src",
            cwd=tmp_path,
            override_path=str(empty_bin),
        )
        assert res.returncode == 0, f"stderr: {res.stderr}"
        assert json.loads(res.stdout.strip())["commit"] is None

    def test_git_timeout_returns_none_promptly_without_stale_fallback(
        self, tmp_path: Path
    ) -> None:
        repo_dir = tmp_path / "pubrun_checkout"
        _create_verified_checkout(repo_dir)
        (repo_dir / "src" / "pubrun" / "COMMIT").write_text(SHA_40_B + "\n", encoding="utf-8")

        bin_dir = tmp_path / "bin"
        _create_fake_git(bin_dir, "import time\ntime.sleep(5)\n")
        code = (
            "import json\n"
            "import pubrun.minimal\n"
            "import pubrun\n"
            "print(json.dumps({'commit': pubrun.__commit__}))\n"
        )
        start = time.monotonic()
        res = _run_python_isolated(
            code,
            pythonpath=repo_dir / "src",
            cwd=tmp_path,
            prepend_path=bin_dir,
            timeout=10.0,
        )
        elapsed = time.monotonic() - start
        assert res.returncode == 0, f"stderr: {res.stderr}"
        assert json.loads(res.stdout.strip())["commit"] is None
        # Bounded by the 1.0s checkout timeout rather than the 5s sleep.
        assert elapsed < 4.5

    def test_git_error_returns_none_without_stale_fallback(self, tmp_path: Path) -> None:
        repo_dir = tmp_path / "pubrun_checkout"
        _create_verified_checkout(repo_dir)
        (repo_dir / "src" / "pubrun" / "COMMIT").write_text(SHA_40_B + "\n", encoding="utf-8")

        bin_dir = tmp_path / "bin"
        _create_fake_git(bin_dir, "import sys\nsys.stderr.write('fatal: bad repo\\n')\nsys.exit(128)\n")
        code = (
            "import json\n"
            "import pubrun.minimal\n"
            "import pubrun\n"
            "print(json.dumps({'commit': pubrun.__commit__}))\n"
        )
        res = _run_python_isolated(
            code,
            pythonpath=repo_dir / "src",
            cwd=tmp_path,
            prepend_path=bin_dir,
        )
        assert res.returncode == 0, f"stderr: {res.stderr}"
        assert json.loads(res.stdout.strip())["commit"] is None

    def test_toplevel_mismatch_returns_none_without_stale_fallback(self, tmp_path: Path) -> None:
        repo_dir = tmp_path / "pubrun_checkout"
        _create_verified_checkout(repo_dir)
        (repo_dir / "src" / "pubrun" / "COMMIT").write_text(SHA_40_B + "\n", encoding="utf-8")

        wrong_toplevel = tmp_path / "enclosing_repo"
        wrong_toplevel.mkdir()
        bin_dir = tmp_path / "bin"
        _create_fake_git(
            bin_dir,
            f"print({str(wrong_toplevel)!r})\nprint({SHA_40_A!r})\n",
        )
        code = (
            "import json\n"
            "import pubrun.minimal\n"
            "import pubrun\n"
            "print(json.dumps({'commit': pubrun.__commit__}))\n"
        )
        res = _run_python_isolated(
            code,
            pythonpath=repo_dir / "src",
            cwd=tmp_path,
            prepend_path=bin_dir,
        )
        assert res.returncode == 0, f"stderr: {res.stderr}"
        assert json.loads(res.stdout.strip())["commit"] is None

    def test_non_pubrun_pyproject_is_not_treated_as_verified_checkout(
        self, tmp_path: Path
    ) -> None:
        repo_dir = tmp_path / "other_project"
        _create_verified_checkout(repo_dir, project_name="other-project")

        log_file = tmp_path / "git_calls.log"
        bin_dir = tmp_path / "bin"
        _create_fake_git(
            bin_dir,
            (
                "import sys\n"
                f"open({str(log_file)!r}, 'a', encoding='utf-8').write('called\\n')\n"
                "sys.exit(99)\n"
            ),
        )
        code = (
            "import json\n"
            "import pubrun.minimal\n"
            "import pubrun\n"
            "print(json.dumps({'commit': pubrun.__commit__}))\n"
        )
        res = _run_python_isolated(
            code,
            pythonpath=repo_dir / "src",
            cwd=tmp_path,
            prepend_path=bin_dir,
        )
        assert res.returncode == 0, f"stderr: {res.stderr}"
        assert json.loads(res.stdout.strip())["commit"] is None
        assert not log_file.exists()

    def test_fallback_pyproject_parser_is_section_scoped(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        import pubrun

        # Simulate neither tomllib nor tomli being importable.
        real_import = builtins.__import__

        def _block_toml(name: str, *args: Any, **kwargs: Any) -> Any:
            if name in ("tomllib", "tomli"):
                raise ImportError(f"blocked {name}")
            return real_import(name, *args, **kwargs)

        monkeypatch.setattr(builtins, "__import__", _block_toml)

        valid_toml = tmp_path / "valid.toml"
        valid_toml.write_text(
            "[build-system]\nrequires = ['hatchling']\n\n"
            "[project]\nname = 'pubrun' # inline comment\nversion = '1.3.1'\n",
            encoding="utf-8",
        )
        wrong_section_toml = tmp_path / "wrong_section.toml"
        wrong_section_toml.write_text(
            '[project]\nversion = "1.3.1"\n\n[tool.demo]\nname = "pubrun"\n',
            encoding="utf-8",
        )

        assert pubrun._pyproject_declares_pubrun(valid_toml) is True
        assert pubrun._pyproject_declares_pubrun(wrong_section_toml) is False


# ---------------------------------------------------------------------------
# 4. hatch_build.py and scripts/update_commit_file.py tests
# ---------------------------------------------------------------------------


class TestHatchBuildHook:
    """CustomBuildHook stamps build-scoped metadata cleanly without requiring hatchling."""

    def _make_hook(self, root: Path, target_name: str, pkg_version: str = "2.4.6"):
        hatch_build = _load_module_from_path("pubrun_hatch_build_under_test", REPO_ROOT / "hatch_build.py")
        metadata = SimpleNamespace(version=pkg_version)
        return hatch_build.CustomBuildHook(
            root=str(root),
            config={},
            build_config=None,
            metadata=metadata,
            directory=str(root / "dist"),
            target_name=target_name,
        )

    @pytest.mark.parametrize(
        "target_name,expected_meta_dest,expected_commit_dest",
        [
            ("wheel", "pubrun/_build_meta.json", "pubrun/COMMIT"),
            ("sdist", "src/pubrun/_build_meta.json", "src/pubrun/COMMIT"),
        ],
    )
    def test_verified_checkout_stamps_metadata_version_and_cleans_up(
        self,
        tmp_path: Path,
        target_name: str,
        expected_meta_dest: str,
        expected_commit_dest: str,
    ) -> None:
        repo_dir = tmp_path / "checkout"
        head_sha = _create_verified_checkout(repo_dir)
        hook = self._make_hook(repo_dir, target_name=target_name, pkg_version="2.4.6")

        build_data: Dict[str, Any] = {}
        hook.initialize("standard", build_data)

        force_include = build_data.get("force_include", {})
        assert len(force_include) == 2
        dest_to_src = {dest: Path(src) for src, dest in force_include.items()}
        assert expected_meta_dest in dest_to_src
        assert expected_commit_dest in dest_to_src

        meta_src = dest_to_src[expected_meta_dest]
        commit_src = dest_to_src[expected_commit_dest]
        assert meta_src.is_file()
        assert commit_src.is_file()

        meta_payload = json.loads(meta_src.read_text(encoding="utf-8"))
        # Must record self.metadata.version, NOT build version ("standard").
        assert meta_payload == {"commit": head_sha, "version": "2.4.6"}
        assert commit_src.read_text(encoding="utf-8").strip() == head_sha

        # Source tree stays clean (no src/pubrun/COMMIT or _build_meta.json created).
        assert not (repo_dir / "src" / "pubrun" / "COMMIT").exists()
        assert not (repo_dir / "src" / "pubrun" / "_build_meta.json").exists()

        temp_parent = meta_src.parent
        hook.finalize("standard", build_data, str(repo_dir / "dist" / "artifact"))
        assert not meta_src.exists()
        assert not commit_src.exists()
        assert not temp_parent.exists()

    def test_editable_build_is_noop(self, tmp_path: Path) -> None:
        repo_dir = tmp_path / "checkout"
        _create_verified_checkout(repo_dir)
        hook = self._make_hook(repo_dir, target_name="wheel", pkg_version="2.4.6")

        build_data: Dict[str, Any] = {}
        hook.initialize("editable", build_data)
        assert build_data.get("force_include", {}) == {}
        hook.finalize("editable", build_data, str(repo_dir / "dist" / "editable.whl"))

    def test_inherited_git_dir_is_ignored_during_build(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        repo_dir = tmp_path / "checkout"
        head_sha = _create_verified_checkout(repo_dir)
        other_repo = tmp_path / "other"
        other_sha = _init_git_repo(other_repo)
        assert other_sha != head_sha

        monkeypatch.setenv("GIT_DIR", str(other_repo / ".git"))
        monkeypatch.setenv("GIT_WORK_TREE", str(other_repo))

        hook = self._make_hook(repo_dir, target_name="wheel", pkg_version="1.3.1")
        build_data: Dict[str, Any] = {}
        hook.initialize("standard", build_data)
        try:
            dest_to_src = {dest: Path(src) for src, dest in build_data["force_include"].items()}
            payload = json.loads(dest_to_src["pubrun/_build_meta.json"].read_text(encoding="utf-8"))
            assert payload["commit"] == head_sha
        finally:
            hook.finalize("standard", build_data, "dist/pubrun.whl")

    def test_checkout_git_failure_or_mismatch_attaches_nothing(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        repo_dir = tmp_path / "checkout"
        _create_verified_checkout(repo_dir)
        # Plant a stale on-disk COMMIT to ensure it is NOT picked up on Git failure.
        (repo_dir / "src" / "pubrun" / "COMMIT").write_text(SHA_40_B + "\n", encoding="utf-8")

        # Case 1: git exits non-zero
        fail_bin = tmp_path / "fail_bin"
        _create_fake_git(fail_bin, "import sys\nsys.exit(1)\n")
        monkeypatch.setenv("PATH", f"{fail_bin}{os.pathsep}{os.environ.get('PATH', '')}")

        hook = self._make_hook(repo_dir, target_name="wheel", pkg_version="1.3.1")
        build_data: Dict[str, Any] = {}
        hook.initialize("standard", build_data)
        assert build_data.get("force_include", {}) == {}
        hook.finalize("standard", build_data, "dist/pubrun.whl")

        # Case 2: git returns a different toplevel
        wrong_root = tmp_path / "elsewhere"
        wrong_root.mkdir()
        mismatch_bin = tmp_path / "mismatch_bin"
        _create_fake_git(mismatch_bin, f"print({str(wrong_root)!r})\nprint({SHA_40_A!r})\n")
        monkeypatch.setenv("PATH", f"{mismatch_bin}{os.pathsep}{os.environ.get('PATH', '')}")

        build_data2: Dict[str, Any] = {}
        hook.initialize("standard", build_data2)
        assert build_data2.get("force_include", {}) == {}
        hook.finalize("standard", build_data2, "dist/pubrun.whl")

    def test_sdist_to_wheel_preserves_matching_version_and_rejects_mismatch_or_commit_only(
        self, tmp_path: Path
    ) -> None:
        # 1) Unpacked sdist with matching _build_meta.json
        sdist_match = tmp_path / "sdist_match"
        (sdist_match / "src" / "pubrun").mkdir(parents=True)
        (sdist_match / "src" / "pubrun" / "_build_meta.json").write_text(
            json.dumps({"commit": SHA_40_A, "version": "1.3.1"}) + "\n",
            encoding="utf-8",
        )
        hook = self._make_hook(sdist_match, target_name="wheel", pkg_version="1.3.1")
        build_data: Dict[str, Any] = {}
        hook.initialize("standard", build_data)
        try:
            dest_to_src = {dest: Path(src) for src, dest in build_data["force_include"].items()}
            assert json.loads(
                dest_to_src["pubrun/_build_meta.json"].read_text(encoding="utf-8")
            ) == {"commit": SHA_40_A, "version": "1.3.1"}
            assert dest_to_src["pubrun/COMMIT"].read_text(encoding="utf-8").strip() == SHA_40_A
        finally:
            hook.finalize("standard", build_data, "dist/pubrun.whl")

        # 2) Unpacked sdist with version mismatch (even when COMMIT exists)
        sdist_mismatch = tmp_path / "sdist_mismatch"
        (sdist_mismatch / "src" / "pubrun").mkdir(parents=True)
        (sdist_mismatch / "src" / "pubrun" / "_build_meta.json").write_text(
            json.dumps({"commit": SHA_40_A, "version": "1.3.0"}) + "\n",
            encoding="utf-8",
        )
        (sdist_mismatch / "src" / "pubrun" / "COMMIT").write_text(SHA_40_A + "\n", encoding="utf-8")
        hook_mismatch = self._make_hook(sdist_mismatch, target_name="wheel", pkg_version="1.3.1")
        build_data_mismatch: Dict[str, Any] = {}
        hook_mismatch.initialize("standard", build_data_mismatch)
        assert build_data_mismatch.get("force_include", {}) == {}

        # 3) Unpacked sdist with unversioned COMMIT only (no _build_meta.json)
        sdist_commit_only = tmp_path / "sdist_commit_only"
        (sdist_commit_only / "src" / "pubrun").mkdir(parents=True)
        (sdist_commit_only / "src" / "pubrun" / "COMMIT").write_text(
            SHA_40_A + "\n", encoding="utf-8"
        )
        hook_commit_only = self._make_hook(
            sdist_commit_only, target_name="wheel", pkg_version="1.3.1"
        )
        build_data_commit_only: Dict[str, Any] = {}
        hook_commit_only.initialize("standard", build_data_commit_only)
        assert build_data_commit_only.get("force_include", {}) == {}


class TestUpdateCommitFileScript:
    """scripts/update_commit_file.py is a quiet stale-file cleanup no-op."""

    def test_removes_stale_commit_file_and_never_creates_it(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
    ) -> None:
        mod = _load_module_from_path(
            "pubrun_update_commit_file_under_test", REPO_ROOT / "scripts" / "update_commit_file.py"
        )
        stale_commit = tmp_path / "COMMIT"
        stale_commit.write_text(SHA_40_A + "\n", encoding="utf-8")
        monkeypatch.setattr(mod, "_COMMIT_FILE", stale_commit)

        assert mod.main() == 0
        assert not stale_commit.exists()
        captured = capsys.readouterr()
        assert captured.out == ""
        assert captured.err == ""

        # Second invocation when file is already absent also succeeds quietly.
        assert mod.main() == 0
        assert not stale_commit.exists()


# ---------------------------------------------------------------------------
# 5. Boot TOML single-read and non-dict safety tests
# ---------------------------------------------------------------------------


class TestConfigBootSingleRead:
    """src/pubrun/_config_boot.py parses .pubrun.toml at most once and handles bad sections."""

    def test_resolve_import_mode_opens_pubrun_toml_once_on_core_fallthrough(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from pubrun._config_boot import resolve_import_mode

        toml_file = tmp_path / ".pubrun.toml"
        toml_file.write_text("[core]\nauto_start = false\n", encoding="utf-8")
        monkeypatch.chdir(tmp_path)
        monkeypatch.delenv("PUBRUN_IMPORT_MODE", raising=False)
        monkeypatch.delenv("PUBRUN_AUTO_START", raising=False)

        open_count = 0
        real_open = builtins.open

        def _counting_open(file: Any, *args: Any, **kwargs: Any) -> Any:
            nonlocal open_count
            if os.path.basename(str(file)) == ".pubrun.toml":
                open_count += 1
            return real_open(file, *args, **kwargs)

        monkeypatch.setattr(builtins, "open", _counting_open)

        mode, source = resolve_import_mode()
        assert mode == "noauto"
        assert source == "config:[core].auto_start"
        assert open_count == 1

    @pytest.mark.parametrize(
        "toml_content",
        [
            'imports = "bad"\n',
            'imports = "bad"\ncore = 123\n',
            "imports = [1, 2, 3]\n",
        ],
    )
    def test_resolve_import_mode_handles_non_dict_sections_safely(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, toml_content: str
    ) -> None:
        from pubrun._config_boot import resolve_import_mode

        (tmp_path / ".pubrun.toml").write_text(toml_content, encoding="utf-8")
        monkeypatch.chdir(tmp_path)
        monkeypatch.delenv("PUBRUN_IMPORT_MODE", raising=False)
        monkeypatch.delenv("PUBRUN_AUTO_START", raising=False)

        mode, source = resolve_import_mode()
        assert mode == "auto"
        assert source == "default"

    def test_read_local_toml_key_preserved_for_bootstrap_conflict_policy(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from pubrun._config_boot import _read_local_toml_key

        (tmp_path / ".pubrun.toml").write_text('[imports]\non_conflict = "error"\n', encoding="utf-8")
        monkeypatch.chdir(tmp_path)

        assert _read_local_toml_key("imports", "on_conflict") == "error"
        assert _read_local_toml_key("imports", "missing") is None
