"""Behavioral unit and side-effect safety tests for read-only offline preflight."""

import copy
import hashlib
import json
import os
import platform
import socket
import subprocess
import sys
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional
from unittest import mock

import pytest

from pubrun.capture import packages as pkg_mod
from pubrun.capture import python_runtime
from pubrun.report import checks
from pubrun.report.reproducibility import (
    CATEGORY_ORDER,
    COMPARISON_OUTCOMES,
    DEFAULT_MAX_HASH_BYTES,
    EVIDENCE_STATUSES,
    IMPACT_LEVELS,
    NON_GUARANTEE_DISCLAIMER,
    assess_run,
    compare_with_current_environment,
    format_reproducibility_detail,
    format_reproducibility_summary,
    should_fail_strict,
)
from pubrun.report.utils import HydrationReport


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _md5_bytes(data: bytes) -> str:
    return hashlib.md5(data).hexdigest()


def _init_git_repo(repo_dir: Path, files: Dict[str, str]) -> str:
    """Create a real local Git repository with one clean commit and return HEAD."""
    repo_dir.mkdir(parents=True, exist_ok=True)
    clean_env = {
        k: v
        for k, v in os.environ.items()
        if k not in ("GIT_DIR", "GIT_WORK_TREE", "GIT_COMMON_DIR", "GIT_INDEX_FILE")
    }
    clean_env.update(
        {
            "GIT_AUTHOR_NAME": "Test User",
            "GIT_AUTHOR_EMAIL": "test@example.com",
            "GIT_COMMITTER_NAME": "Test User",
            "GIT_COMMITTER_EMAIL": "test@example.com",
        }
    )

    def _git(*args: str) -> str:
        res = subprocess.run(
            ["git", "-C", str(repo_dir)] + list(args),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True,
            env=clean_env,
        )
        return res.stdout.strip()

    _git("init")
    for rel_path, content in files.items():
        target = repo_dir / rel_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
    _git("add", ".")
    _git("commit", "-m", "initial")
    return _git("rev-parse", "HEAD")


def _matching_manifest(
    repo_dir: Path,
    *,
    commit: str,
    script_rel: str = "train.py",
    script_bytes: bytes = b"print('hello')\n",
    input_rel: str = "data/input.csv",
    input_bytes: bytes = b"x,y\n1,2\n",
    packages_records: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """Build a complete manifest that matches the current local environment."""
    script_path = repo_dir / script_rel
    input_path = repo_dir / input_rel
    env_kind_val = python_runtime.environment_kind()["environment_kind"]
    cur_ver = f"{sys.version_info[0]}.{sys.version_info[1]}.{sys.version_info[2]}"
    cur_host = socket.gethostname()

    return {
        "schema_version": "1.0",
        "manifest_type": "pubrun-manifest",
        "run": {"run_id": "run-match-001", "capture_state": {"status": "complete"}},
        "timing": {
            "started_at_utc": 1780250100.0,
            "ended_at_utc": 1780250160.0,
            "elapsed_seconds": 60.0,
            "capture_state": {"status": "complete"},
        },
        "status": {
            "outcome": "completed",
            "exit_code": 0,
            "capture_state": {"status": "complete"},
        },
        "invocation": {
            "argv": [script_rel, "--epochs", "5"],
            "rerun_command": f"cd {repo_dir} && python {script_rel} --epochs 5",
            "entrypoint_type": "script",
            "script": {
                "path": script_rel,
                "real_path": str(script_path),
                "sha256": _sha256_bytes(script_bytes),
                "size": len(script_bytes),
            },
            "working_directory": {
                "path": str(repo_dir),
                "real_path": str(repo_dir.resolve()),
            },
            "inputs": [],
            "capture_state": {"status": "complete"},
        },
        "git": {
            "repo_root": str(repo_dir),
            "commit": commit,
            "branch": "main",
            "dirty": False,
            "capture_state": {"status": "complete"},
        },
        "python": {
            "version": cur_ver,
            "implementation": sys.implementation.name,
            "environment_kind": env_kind_val,
            "capture_state": {"status": "complete"},
        },
        "host": {
            "os_name": platform.system(),
            "os_version": platform.release(),
            "hostname": cur_host,
            "capture_state": {"status": "complete"},
        },
        "hardware": {
            "cpu": {"architecture": platform.machine(), "model": "TestCPU"},
            "memory_total_bytes": 16_000_000_000,
            "capture_state": {"status": "complete"},
        },
        "packages": {
            "mode": "full-environment",
            "records": (
                packages_records
                if packages_records is not None
                else [{"name": "pytest", "version": pytest.__version__, "editable": False}]
            ),
            "capture_state": {"status": "complete"},
        },
        "environment": {
            "mode": "filtered",
            "variables": [],
            "capture_state": {"status": "complete"},
        },
        "data_files": {
            "inputs": [
                {
                    "path": input_rel,
                    "realpath": str(input_path),
                    "size_bytes": len(input_bytes),
                    "sha256": _sha256_bytes(input_bytes),
                    "evidence_source": "observed",
                    "hash_status": "completed",
                }
            ],
            "outputs": [],
            "mixed": [],
        },
        "resources": {"scope": "tree", "capture_state": {"status": "complete"}},
        "console": {"capture_mode": "standard", "capture_state": {"status": "complete"}},
        "subprocesses": [],
        "capture": {"subprocesses_enabled": True, "capture_state": {"status": "complete"}},
        "pubrun_imports": {
            "selected_mode": "auto",
            "selected_behavior": {"patch_subprocesses": True},
        },
        "determinism": {
            "registered_seeds": [{"name": "random", "value": 7}],
            "capture_state": {"status": "complete"},
        },
        "config": {"notices": [], "capture_state": {"status": "complete"}},
        "errors": {"records": [], "capture_state": {"status": "complete"}},
        "meta_ref": None,
    }


def _check_by_name(result: Dict[str, Any], name: str) -> Dict[str, Any]:
    matches = [c for c in result["checks"] if c["name"] == name]
    assert matches, f"Expected check {name!r}; got {[c['name'] for c in result['checks']]}"
    return matches[0]


class _FakeDist:
    """Minimal synthetic distribution object for package helper tests."""

    def __init__(
        self,
        name: Any,
        version: Optional[str],
        *,
        direct_url: Optional[str] = None,
        location: Optional[str] = "/site-packages",
        raise_on_metadata: bool = False,
    ) -> None:
        self._name = name
        self._version = version
        self._direct_url = direct_url
        self._location = location
        self._raise_on_metadata = raise_on_metadata

    @property
    def metadata(self) -> Any:
        if self._raise_on_metadata:
            raise RuntimeError("corrupt METADATA")
        return {"Name": self._name}

    @property
    def version(self) -> Optional[str]:
        return self._version

    def read_text(self, filename: str) -> Optional[str]:
        if filename == "direct_url.json":
            return self._direct_url
        return None

    def locate_file(self, path: Any) -> Optional[str]:
        return self._location


class TestPackageLookupHelpers:
    """Tests for shared PEP 503 normalization and distribution version lookup."""

    def test_package_normalize_pep503_variants(self):
        assert pkg_mod.normalize_package_name("Scikit_Learn") == "scikit-learn"
        assert pkg_mod.normalize_package_name("scikit-learn") == "scikit-learn"
        assert pkg_mod.normalize_package_name("zope.interface") == "zope-interface"
        assert pkg_mod.normalize_package_name("My__Pkg..Name--1") == "my-pkg-name-1"

    def test_package_lookup_precedence_editable_null_and_no_import(self, monkeypatch):
        fake_dists = [
            # First-wins sys.path precedence: version 2.0.0 must win over shadowed 1.0.0.
            _FakeDist(
                "Scikit_Learn",
                "2.0.0",
                direct_url=json.dumps(
                    {"url": "file:///secret/user/repo", "dir_info": {"editable": True}}
                ),
                location="/venv/site-packages",
            ),
            _FakeDist(
                "scikit-learn",
                "1.0.0",
                direct_url=json.dumps(
                    {"url": "file:///other", "dir_info": {"editable": False}}
                ),
                location="/system/site-packages",
            ),
            # Non-editable dir_info must report editable=False.
            _FakeDist(
                "NonEditable_Dir",
                "0.5.0",
                direct_url=json.dumps(
                    {"url": "file:///local/pkg", "dir_info": {"editable": False}}
                ),
            ),
            # Malformed direct_url JSON falls back to substring check.
            _FakeDist("Malformed_Json", "0.1.0", direct_url="{bad json dir_info"),
            # Missing / non-string Name and corrupt metadata must be skipped safely.
            _FakeDist(None, "9.9.9"),
            _FakeDist("", "9.9.9"),
            _FakeDist("Corrupt_Dist", "1.0.0", raise_on_metadata=True),
        ]

        monkeypatch.setattr(pkg_mod.importlib.metadata, "distributions", lambda: list(fake_dists))
        pkg_mod.invalidate_package_cache()

        target_mod = "_never_imported_preflight_pkg_xyz"
        assert target_mod not in sys.modules

        real_import = __import__
        imported_names: List[str] = []

        def _spy_import(name: str, *args: Any, **kwargs: Any) -> Any:
            imported_names.append(name)
            return real_import(name, *args, **kwargs)

        with mock.patch("builtins.__import__", side_effect=_spy_import):
            versions = pkg_mod.get_installed_distribution_versions(use_cache=False)

        assert target_mod not in sys.modules
        assert "scikit_learn" not in imported_names
        assert set(versions.keys()) == {"scikit-learn", "noneditable-dir", "malformed-json"}

        sk = versions["scikit-learn"]
        assert sk["name"] == "Scikit_Learn"
        assert sk["version"] == "2.0.0"
        assert sk["editable"] is True
        assert sk["location"] == "/venv/site-packages"
        assert "file:///secret" not in json.dumps(versions)

        assert versions["noneditable-dir"]["editable"] is False
        assert versions["malformed-json"]["editable"] is True


class TestPreflightComparisonDimensions:
    """Behavioral tests across every preflight comparison dimension."""

    def test_matching_environment_all_checks_match(self, tmp_path: Path):
        script_bytes = b"print('ok')\n"
        input_bytes = b"a,b\n1,2\n"
        commit = _init_git_repo(
            tmp_path,
            {"train.py": script_bytes.decode(), "data/input.csv": input_bytes.decode()},
        )
        manifest = _matching_manifest(
            tmp_path,
            commit=commit,
            script_bytes=script_bytes,
            input_bytes=input_bytes,
        )

        result = compare_with_current_environment(manifest, cwd=tmp_path)
        assert result["requested"] is True
        assert result["status"] == "match"
        assert result["findings"] == []
        assert result["counts"]["mismatch"] == 0
        assert result["counts"]["unknown"] == 0
        assert result["counts"]["not_checked"] == 0
        assert result["counts"]["portability_diff"] == 0
        assert result["counts"]["match"] >= 8
        for chk in result["checks"]:
            assert chk["comparison"] in COMPARISON_OUTCOMES
            assert chk["evidence_status"] in EVIDENCE_STATUSES
            assert chk["impact"] in IMPACT_LEVELS
            assert chk["category"] in CATEGORY_ORDER

    def test_python_and_platform_material_vs_portability_and_redacted_hostname(
        self, tmp_path: Path, monkeypatch
    ):
        monkeypatch.setattr(
            python_runtime,
            "environment_kind",
            lambda: {
                "environment_kind": "conda",
                "in_venv": True,
                "sys_path_len": 10,
                "pyenv": False,
            },
        )
        cur_major, cur_minor, cur_patch = sys.version_info[:3]

        # 1. Major.minor mismatch + implementation mismatch + OS/arch/env_kind portability diff + redacted hostname dict.
        manifest_mismatch = {
            "python": {
                "version": f"{cur_major}.{cur_minor + 1}.0 (main, Jan 1 2026) [GCC]",
                "implementation": "pypy",
                "environment_kind": "venv",
                "capture_state": {"status": "complete"},
            },
            "host": {
                "os_name": "OtherOS",
                "os_version": "9.9.9",
                "hostname": {"representation": "redacted", "value": "[REDACTED]"},
                "capture_state": {"status": "complete"},
            },
            "hardware": {
                "cpu": {"architecture": "riscv64"},
                "capture_state": {"status": "complete"},
            },
        }
        res = compare_with_current_environment(manifest_mismatch, cwd=tmp_path)

        py_ver = _check_by_name(res, "python_version")
        assert py_ver["comparison"] == "mismatch"
        assert py_ver["impact"] == "material"
        assert py_ver["severity"] == "warn"
        assert py_ver["evidence_status"] == "observed"
        assert f"{cur_major}.{cur_minor + 1}.0" in py_ver["message"]

        py_impl = _check_by_name(res, "python_implementation")
        assert py_impl["comparison"] == "mismatch"
        assert py_impl["impact"] == "material"
        assert py_impl["severity"] == "warn"

        py_env = _check_by_name(res, "python_environment_kind")
        assert py_env["comparison"] == "portability_diff"
        assert py_env["impact"] == "portability"
        assert py_env["severity"] == "info"
        assert py_env["details"]["current_environment_kind"] == "conda"

        os_chk = _check_by_name(res, "host_os")
        assert os_chk["comparison"] == "portability_diff"
        assert os_chk["impact"] == "portability"
        assert os_chk["severity"] == "info"

        arch_chk = _check_by_name(res, "cpu_architecture")
        assert arch_chk["comparison"] == "portability_diff"
        assert arch_chk["impact"] == "portability"
        assert arch_chk["severity"] == "info"

        host_chk = _check_by_name(res, "host_hostname")
        assert host_chk["comparison"] == "unknown"
        assert host_chk["evidence_status"] == "unavailable"
        assert "[REDACTED]" not in str(host_chk["details"])

        # 2. Patch diff + OS minor release diff + plain-dict different hostname -> portability_diff.
        manifest_patch = {
            "python": {
                "version": f"{cur_major}.{cur_minor}.{cur_patch + 1}rc1",
                "implementation": sys.implementation.name,
                "environment_kind": "conda",
                "capture_state": {"status": "complete"},
            },
            "host": {
                "os_name": platform.system(),
                "os_version": platform.release() + "-different",
                "hostname": {"representation": "plain", "value": "different-compute-node"},
                "capture_state": {"status": "complete"},
            },
            "hardware": {
                "cpu": {"architecture": platform.machine()},
                "capture_state": {"status": "complete"},
            },
        }
        res_patch = compare_with_current_environment(manifest_patch, cwd=tmp_path)
        py_patch = _check_by_name(res_patch, "python_version")
        assert py_patch["comparison"] == "portability_diff"
        assert py_patch["impact"] == "portability"
        assert py_patch["severity"] == "info"

        os_ver_chk = _check_by_name(res_patch, "host_os_version")
        assert os_ver_chk["comparison"] == "portability_diff"
        assert os_ver_chk["impact"] == "incidental"
        assert os_ver_chk["severity"] == "info"

        host_plain = _check_by_name(res_patch, "host_hostname")
        assert host_plain["comparison"] == "portability_diff"
        assert host_plain["impact"] == "incidental"
        assert host_plain["severity"] == "info"
        assert host_plain["details"]["recorded_hostname"] == "different-compute-node"

        # 3. Missing / suppressed / unparseable runtime sections -> unknown (never verified match).
        res_missing = compare_with_current_environment(
            {
                "python": {"version": "not-a-version", "capture_state": {"status": "complete"}},
                "host": {"capture_state": {"status": "suppressed"}},
                "hardware": {"capture_state": {"status": "failed"}},
            },
            cwd=tmp_path,
        )
        assert _check_by_name(res_missing, "python_version")["comparison"] == "unknown"
        assert _check_by_name(res_missing, "host_os")["comparison"] == "unknown"
        assert _check_by_name(res_missing, "cpu_architecture")["comparison"] == "unknown"

    def test_package_comparison_match_mismatch_missing_unknown_and_caveats(
        self, tmp_path: Path, monkeypatch
    ):
        installed = {
            "scikit-learn": {
                "name": "scikit-learn",
                "version": "1.5.0",
                "editable": True,
                "location": "/venv",
            },
            "numpy": {
                "name": "numpy",
                "version": "2.0.1",
                "editable": False,
                "location": "/venv",
            },
            "scipy": {
                "name": "scipy",
                "version": "1.13.0",
                "editable": False,
                "location": "/venv",
            },
        }
        monkeypatch.setattr(
            pkg_mod, "get_installed_distribution_versions", lambda use_cache=True: installed
        )

        manifest = {
            "packages": {
                "mode": "imported-only",
                "records": [
                    "not-a-dict",
                    {"name": None, "version": "1.0"},
                    {"name": "Scikit_Learn", "version": "1.5.0", "editable": False},
                    {"name": "numpy", "version": "1.26.4", "editable": False},
                    {"name": "missing-pkg", "version": "0.1.0", "editable": False},
                    {"name": "scipy", "version": "unknown", "editable": False},
                ],
                "capture_state": {"status": "complete"},
            }
        }

        res = compare_with_current_environment(manifest, cwd=tmp_path)

        matched = _check_by_name(res, "packages_matched")
        assert matched["comparison"] == "match"
        assert matched["details"]["matched_count"] == 1
        assert "editable" in matched["message"].lower()
        assert "imported-only" in matched["message"].lower()

        np_chk = _check_by_name(res, "package:numpy")
        assert np_chk["comparison"] == "mismatch"
        assert np_chk["impact"] == "material"
        assert np_chk["severity"] == "warn"
        assert np_chk["details"]["recorded_version"] == "1.26.4"
        assert np_chk["details"]["installed_version"] == "2.0.1"

        miss_chk = _check_by_name(res, "package:missing-pkg")
        assert miss_chk["comparison"] == "mismatch"
        assert miss_chk["impact"] == "material"
        assert miss_chk["severity"] == "warn"

        unk_chk = _check_by_name(res, "package:scipy")
        assert unk_chk["comparison"] == "unknown"
        assert unk_chk["evidence_status"] == "unavailable"

        # Suppressed and empty packages never produce a verified match.
        res_supp = compare_with_current_environment(
            {"packages": {"capture_state": {"status": "suppressed"}}}, cwd=tmp_path
        )
        assert _check_by_name(res_supp, "packages")["comparison"] == "not_checked"

        res_empty = compare_with_current_environment(
            {"packages": {"mode": "imported-only", "records": [], "capture_state": {"status": "complete"}}},
            cwd=tmp_path,
        )
        assert _check_by_name(res_empty, "packages")["comparison"] == "not_checked"

    def test_git_commit_dirty_timeout_unavailable_and_git_dir_isolation(
        self, tmp_path: Path, monkeypatch
    ):
        repo_a = tmp_path / "repo_a"
        repo_b = tmp_path / "repo_b"
        commit_a = _init_git_repo(repo_a, {"train.py": "print(1)\n"})
        commit_b = _init_git_repo(repo_b, {"train.py": "print(2)\n"})
        assert commit_a != commit_b

        # Poison GIT_DIR / GIT_WORK_TREE with repo_b while probing repo_a.
        monkeypatch.setenv("GIT_DIR", str(repo_b / ".git"))
        monkeypatch.setenv("GIT_WORK_TREE", str(repo_b))

        clean_manifest = {
            "git": {
                "repo_root": str(repo_a),
                "commit": commit_a,
                "dirty": False,
                "capture_state": {"status": "complete"},
            }
        }
        res_clean = compare_with_current_environment(clean_manifest, cwd=repo_a)
        git_chk = _check_by_name(res_clean, "git_source")
        assert git_chk["comparison"] == "match"
        assert git_chk["details"]["current_commit"] == commit_a

        # Commit mismatch when probing repo_b against repo_a's recorded commit.
        res_diff = compare_with_current_environment(clean_manifest, cwd=repo_b)
        diff_chk = _check_by_name(res_diff, "git_source")
        assert diff_chk["comparison"] == "mismatch"
        assert diff_chk["impact"] == "material"
        assert diff_chk["severity"] == "warn"
        assert diff_chk["details"]["recorded_commit"] == commit_a
        assert diff_chk["details"]["current_commit"] == commit_b

        # Matching HEAD when recorded git.dirty is True -> unknown + material warn.
        recorded_dirty = {
            "git": {
                "repo_root": str(repo_a),
                "commit": commit_a,
                "dirty": True,
                "capture_state": {"status": "complete"},
            }
        }
        res_rec_dirty = compare_with_current_environment(recorded_dirty, cwd=repo_a)
        rd_chk = _check_by_name(res_rec_dirty, "git_source")
        assert rd_chk["comparison"] == "unknown"
        assert rd_chk["impact"] == "material"
        assert rd_chk["severity"] == "warn"
        assert "does not prove identical source" in rd_chk["message"]

        # Matching HEAD when current working tree is dirty -> mismatch + material warn.
        (repo_a / "train.py").write_text("print('modified')\n", encoding="utf-8")
        res_cur_dirty = compare_with_current_environment(clean_manifest, cwd=repo_a)
        cd_chk = _check_by_name(res_cur_dirty, "git_source")
        assert cd_chk["comparison"] == "mismatch"
        assert cd_chk["impact"] == "material"
        assert cd_chk["severity"] == "warn"

        # Non-Git directory -> unknown + unavailable + info.
        non_git = tmp_path / "plain_dir"
        non_git.mkdir()
        res_nongit = compare_with_current_environment(clean_manifest, cwd=non_git)
        ng_chk = _check_by_name(res_nongit, "git_source")
        assert ng_chk["comparison"] == "unknown"
        assert ng_chk["evidence_status"] == "unavailable"
        assert ng_chk["severity"] == "info"

        # cwd=None in a non-Git directory falls back to recorded git.repo_root.
        monkeypatch.chdir(non_git)
        repo_c = tmp_path / "repo_c"
        commit_c = _init_git_repo(repo_c, {"train.py": "print(3)\n"})
        fallback_manifest = {
            "git": {
                "repo_root": str(repo_c),
                "commit": commit_c,
                "dirty": False,
                "capture_state": {"status": "complete"},
            }
        }
        res_fb = compare_with_current_environment(fallback_manifest)
        fb_chk = _check_by_name(res_fb, "git_source")
        assert fb_chk["comparison"] == "match"
        assert fb_chk["details"]["probed_dir"] == str(repo_c)

        # Git timeout -> unknown + unavailable + material warn.
        def _timeout_run(*args: Any, **kwargs: Any) -> Any:
            raise subprocess.TimeoutExpired(cmd=args[0], timeout=0.05)

        monkeypatch.setattr(subprocess, "run", _timeout_run)
        res_to = compare_with_current_environment(
            clean_manifest, cwd=repo_a, git_timeout=0.05
        )
        to_chk = _check_by_name(res_to, "git_source")
        assert to_chk["comparison"] == "unknown"
        assert to_chk["evidence_status"] == "unavailable"
        assert to_chk["impact"] == "material"
        assert to_chk["severity"] == "warn"
        assert "timed out" in to_chk["message"].lower()

    def test_script_hash_size_missing_over_cap_and_non_script(self, tmp_path: Path):
        script = tmp_path / "run.py"
        content = b"x = 1\n"
        script.write_bytes(content)

        # Matching SHA-256.
        base_inv = {
            "invocation": {
                "entrypoint_type": "script",
                "script": {
                    "path": "run.py",
                    "real_path": str(script),
                    "sha256": _sha256_bytes(content),
                    "size": len(content),
                },
            }
        }
        assert _check_by_name(compare_with_current_environment(base_inv, cwd=tmp_path), "entrypoint_script")["comparison"] == "match"

        # Over-cap -> not_checked.
        res_cap = compare_with_current_environment(base_inv, cwd=tmp_path, max_hash_bytes=2)
        cap_chk = _check_by_name(res_cap, "entrypoint_script")
        assert cap_chk["comparison"] == "not_checked"
        assert cap_chk["evidence_status"] == "not_checked"

        # check_hashes=False with same size -> unknown (not_checked).
        res_nohash = compare_with_current_environment(base_inv, cwd=tmp_path, check_hashes=False)
        nh_chk = _check_by_name(res_nohash, "entrypoint_script")
        assert nh_chk["comparison"] == "unknown"
        assert nh_chk["evidence_status"] == "not_checked"

        # Modified script -> hash mismatch (and size mismatch when check_hashes=False).
        script.write_bytes(b"x = 999999\n")
        res_hm = compare_with_current_environment(base_inv, cwd=tmp_path)
        assert _check_by_name(res_hm, "entrypoint_script")["comparison"] == "mismatch"
        res_sm = compare_with_current_environment(base_inv, cwd=tmp_path, check_hashes=False)
        assert _check_by_name(res_sm, "entrypoint_script")["comparison"] == "mismatch"

        # Missing script -> mismatch + unavailable.
        script.unlink()
        res_miss = compare_with_current_environment(base_inv, cwd=tmp_path)
        miss_chk = _check_by_name(res_miss, "entrypoint_script")
        assert miss_chk["comparison"] == "mismatch"
        assert miss_chk["evidence_status"] == "unavailable"

        # Non-script entrypoint -> not_checked.
        res_mod = compare_with_current_environment(
            {"invocation": {"entrypoint_type": "module", "script": {}}}, cwd=tmp_path
        )
        assert _check_by_name(res_mod, "entrypoint_script")["comparison"] == "not_checked"

    def test_inputs_hash_mismatch_missing_dir_fifo_stat_only_cap_and_asserted(
        self, tmp_path: Path
    ):
        f_match = tmp_path / "match.csv"
        f_match_bytes = b"col\n1\n"
        f_match.write_bytes(f_match_bytes)

        f_changed = tmp_path / "changed.csv"
        f_changed.write_bytes(b"new-bytes\n")

        f_stat = tmp_path / "stat_only.csv"
        f_stat.write_bytes(b"12345")

        f_large = tmp_path / "large.bin"
        f_large.write_bytes(b"0" * 64)

        f_asserted = tmp_path / "asserted.csv"
        f_asserted_bytes = b"asserted-data\n"
        f_asserted.write_bytes(f_asserted_bytes)

        f_asserted_bad = tmp_path / "asserted_bad.csv"
        f_asserted_bad.write_bytes(b"different-bytes\n")

        f_mixed = tmp_path / "mixed.csv"
        f_mixed_bytes = b"mixed-data\n"
        f_mixed.write_bytes(f_mixed_bytes)

        f_dir_replaced = tmp_path / "was_dir.txt"
        f_dir_replaced.write_bytes(b"not a dir anymore\n")

        f_md5 = tmp_path / "argv_md5.csv"
        f_md5_bytes = b"md5-data\n"
        f_md5.write_bytes(f_md5_bytes)

        f_dir = tmp_path / "dataset_dir"
        f_dir.mkdir()

        f_nonreg_dir = tmp_path / "unexpected_dir"
        f_nonreg_dir.mkdir()

        fifo_entries: List[Dict[str, Any]] = []
        if hasattr(os, "mkfifo"):
            fifo_path = tmp_path / "named_pipe"
            os.mkfifo(fifo_path)
            fifo_entries.append(
                {
                    "path": "named_pipe",
                    "realpath": str(fifo_path),
                    "sha256": "0" * 64,
                }
            )

        manifest = {
            "data_files": {
                "inputs": [
                    {
                        "path": "match.csv",
                        "realpath": str(f_match),
                        "size_bytes": len(f_match_bytes),
                        "sha256": _sha256_bytes(f_match_bytes),
                        "evidence_source": "observed",
                    },
                    {
                        "path": "changed.csv",
                        "realpath": str(f_changed),
                        "size_bytes": 5,
                        "sha256": _sha256_bytes(b"old!!"),
                        "evidence_source": "observed",
                    },
                    {
                        "path": "missing.csv",
                        "realpath": str(tmp_path / "missing.csv"),
                        "size_bytes": 10,
                        "sha256": "a" * 64,
                    },
                    {
                        "path": "stat_only.csv",
                        "realpath": str(f_stat),
                        "size_bytes": 5,
                    },
                    {
                        "path": "large.bin",
                        "realpath": str(f_large),
                        "size_bytes": 64,
                        "sha256": _sha256_bytes(b"0" * 64),
                    },
                    {
                        "path": "asserted.csv",
                        "realpath": str(f_asserted),
                        "size_bytes": len(f_asserted_bytes),
                        "digest": {"algorithm": "sha256", "value": _sha256_bytes(f_asserted_bytes)},
                        "caller_digest": {
                            "algorithm": "sha256",
                            "value": _sha256_bytes(f_asserted_bytes),
                            "verified": None,
                        },
                        "evidence_source": "asserted",
                    },
                    {
                        "path": "asserted_bad.csv",
                        "realpath": str(f_asserted_bad),
                        "size_bytes": len(f_asserted_bytes),
                        "caller_digest": {
                            "algorithm": "sha256",
                            "value": _sha256_bytes(f_asserted_bytes),
                            "verified": None,
                        },
                        "evidence_source": "asserted",
                    },
                    {
                        "path": "unexpected_dir",
                        "realpath": str(f_nonreg_dir),
                        "sha256": "b" * 64,
                    },
                ]
                + fifo_entries,
                "mixed": [
                    {
                        "path": "mixed.csv",
                        "realpath": str(f_mixed),
                        "size_bytes": len(f_mixed_bytes),
                        "sha256": _sha256_bytes(f_mixed_bytes),
                        "evidence_source": "observed",
                    }
                ],
            },
            "invocation": {
                "inputs": [
                    # Duplicate of match.csv without digest: richer data_files entry must win.
                    {
                        "path": "match.csv",
                        "real_path": str(f_match),
                        "is_dir": False,
                        "size": len(f_match_bytes),
                    },
                    {
                        "path": "argv_md5.csv",
                        "real_path": str(f_md5),
                        "is_dir": False,
                        "size": len(f_md5_bytes),
                        "md5": _md5_bytes(f_md5_bytes),
                    },
                    {
                        "path": "dataset_dir",
                        "real_path": str(f_dir),
                        "is_dir": True,
                    },
                    {
                        "path": "was_dir.txt",
                        "real_path": str(f_dir_replaced),
                        "is_dir": True,
                    },
                ]
            },
        }

        res = compare_with_current_environment(manifest, cwd=tmp_path, max_hash_bytes=32)

        assert _check_by_name(res, "input:match.csv")["comparison"] == "match"
        assert _check_by_name(res, "input:mixed.csv")["comparison"] == "match"
        assert _check_by_name(res, "input:argv_md5.csv")["comparison"] == "match"

        chg = _check_by_name(res, "input:changed.csv")
        assert chg["comparison"] == "mismatch"
        assert chg["impact"] == "material"
        assert chg["severity"] == "warn"

        miss = _check_by_name(res, "input:missing.csv")
        assert miss["comparison"] == "mismatch"
        assert miss["evidence_status"] == "unavailable"

        stat_chk = _check_by_name(res, "input:stat_only.csv")
        assert stat_chk["comparison"] == "unknown"
        assert stat_chk["evidence_status"] == "not_checked"

        large_chk = _check_by_name(res, "input:large.bin")
        assert large_chk["comparison"] == "not_checked"
        assert large_chk["evidence_status"] == "not_checked"
        assert "max_hash_bytes" in large_chk["message"]

        asserted_chk = _check_by_name(res, "input:asserted.csv")
        assert asserted_chk["comparison"] == "match"
        assert asserted_chk["evidence_status"] == "asserted"
        assert "asserted" in asserted_chk["message"].lower()

        asserted_bad_chk = _check_by_name(res, "input:asserted_bad.csv")
        assert asserted_bad_chk["comparison"] == "mismatch"
        assert asserted_bad_chk["evidence_status"] == "asserted"
        assert asserted_bad_chk["severity"] == "warn"
        assert "asserted" in asserted_bad_chk["message"].lower()

        dir_chk = _check_by_name(res, "input:dataset_dir")
        assert dir_chk["comparison"] == "unknown"
        assert dir_chk["evidence_status"] == "not_checked"

        dir_rep_chk = _check_by_name(res, "input:was_dir.txt")
        assert dir_rep_chk["comparison"] == "mismatch"
        assert dir_rep_chk["evidence_status"] == "unavailable"

        nonreg_chk = _check_by_name(res, "input:unexpected_dir")
        assert nonreg_chk["comparison"] == "not_checked"

        if hasattr(os, "mkfifo"):
            fifo_chk = _check_by_name(res, "input:named_pipe")
            assert fifo_chk["comparison"] == "not_checked"

        # check_hashes=False skips hashing on match.csv -> not_checked (not match).
        res_nohash = compare_with_current_environment(
            {"data_files": {"inputs": [manifest["data_files"]["inputs"][0]]}},
            cwd=tmp_path,
            check_hashes=False,
        )
        nh = _check_by_name(res_nohash, "input:match.csv")
        assert nh["comparison"] == "not_checked"
        assert nh["evidence_status"] == "not_checked"

        # Zero recorded inputs -> not_checked.
        res_empty = compare_with_current_environment({}, cwd=tmp_path)
        assert _check_by_name(res_empty, "inputs")["comparison"] == "not_checked"

    def test_working_directory_redacted_command_and_malformed_manifest(self, tmp_path: Path):
        manifest = {
            "invocation": {
                "argv": ["train.py", "--token", "[REDACTED]"],
                "rerun_command": "cd /no/such/dir && python train.py --token [REDACTED]",
                "working_directory": {"path": str(tmp_path / "does-not-exist")},
            }
        }
        res = compare_with_current_environment(manifest, cwd=tmp_path)
        wd_chk = _check_by_name(res, "working_directory")
        assert wd_chk["comparison"] == "portability_diff"
        assert wd_chk["impact"] == "portability"
        assert wd_chk["severity"] == "info"

        cmd_chk = _check_by_name(res, "rerun_command")
        assert cmd_chk["comparison"] == "mismatch"
        assert cmd_chk["impact"] == "material"
        assert cmd_chk["severity"] == "warn"
        assert "verbatim" in cmd_chk["message"].lower()

        # Malformed manifests never raise.
        for bad in (None, [], "bad", {"python": 123, "packages": "bad", "git": [], "data_files": 5}):
            out = compare_with_current_environment(bad, cwd=tmp_path)
            assert out["requested"] is True
            assert out["status"] in COMPARISON_OUTCOMES


class TestAssessRunAndStrictPolicy:
    """Tests for assess_run(preflight=...), checks.py facade, and should_fail_strict."""

    def test_assess_run_preflight_false_matches_manifest_findings_and_preserves_stale_parent(
        self, tmp_path: Path
    ):
        script_bytes = b"print(1)\n"
        input_bytes = b"a\n1\n"
        commit = _init_git_repo(
            tmp_path,
            {"train.py": script_bytes.decode(), "data/input.csv": input_bytes.decode()},
        )
        manifest = _matching_manifest(
            tmp_path, commit=commit, script_bytes=script_bytes, input_bytes=input_bytes
        )
        manifest["git"]["dirty"] = True

        via_assess = checks.assess_run(manifest, current_hostname="other-host", preflight=False)
        via_manifest_findings = checks.manifest_findings(manifest, current_hostname="other-host")

        assert via_assess["mode"] == "manifest"
        assert via_assess["preflight"]["requested"] is False
        assert via_assess["findings"] == via_manifest_findings

        # Verify stale_parent_seconds passes through to parent_metadata evaluation.
        report = HydrationReport(
            meta_ref="meta.json",
            status="hydrated",
            inherited_sections=["hardware"],
            direct_sections=["python"],
            age_seconds=500.0,
        )
        stale_assess = checks.assess_run(
            manifest,
            hydration_report=report,
            stale_parent_seconds=100.0,
            preflight=False,
        )
        assert any(f["code"] == "parent_metadata_stale" for f in stale_assess["findings"])

        fresh_assess = checks.assess_run(
            manifest,
            hydration_report=report,
            stale_parent_seconds=1000.0,
            preflight=False,
        )
        assert not any(f["code"] == "parent_metadata_stale" for f in fresh_assess["findings"])

    def test_assess_run_preflight_true_merges_without_duplicating_redacted_or_host_findings(
        self, tmp_path: Path
    ):
        script_bytes = b"print(1)\n"
        input_bytes = b"a\n1\n"
        commit = _init_git_repo(
            tmp_path,
            {"train.py": script_bytes.decode(), "data/input.csv": input_bytes.decode()},
        )
        manifest = _matching_manifest(
            tmp_path, commit=commit, script_bytes=script_bytes, input_bytes=input_bytes
        )
        manifest["invocation"]["argv"] = ["train.py", "--api-key", "[REDACTED]"]
        manifest["invocation"]["rerun_command"] = f"cd {tmp_path} && python train.py --api-key [REDACTED]"
        manifest["host"]["hostname"] = "compute-node-99"

        assessment = checks.assess_run(
            manifest,
            current_hostname="head-node-01",
            preflight=True,
            cwd=tmp_path,
        )

        assert assessment["mode"] == "preflight"
        assert assessment["preflight"]["requested"] is True
        assert assessment["disclaimer"] == NON_GUARANTEE_DISCLAIMER

        codes = [f["code"] for f in assessment["findings"]]
        # No duplicate redacted-command warn finding.
        assert codes.count("rerun_command_redacted") == 1
        assert "preflight_rerun_command_redacted" not in codes
        # No contradictory/duplicate hostname finding when different_host is present.
        assert codes.count("different_host") == 1
        assert "preflight_hostname_diff" not in codes

        cats = {c["name"]: c for c in assessment["categories"]}
        assert cats["invocation"]["status"] == "mismatch"

        summary_txt = format_reproducibility_summary(assessment)
        assert "Preflight [MISMATCH]:" in summary_txt
        detail_txt = format_reproducibility_detail(assessment, use_color=False)
        assert "Preflight checks:" in detail_txt
        assert "\033[" not in detail_txt

    def test_should_fail_strict_modes_and_invalid_fail_on(self, tmp_path: Path):
        script_bytes = b"print(1)\n"
        input_bytes = b"a\n1\n"
        commit = _init_git_repo(
            tmp_path,
            {"train.py": script_bytes.decode(), "data/input.csv": input_bytes.decode()},
        )
        manifest = _matching_manifest(
            tmp_path, commit=commit, script_bytes=script_bytes, input_bytes=input_bytes
        )

        # Clean matching environment passes all three strict modes.
        clean = checks.assess_run(manifest, preflight=True, cwd=tmp_path)
        assert checks.should_fail_strict(clean, fail_on="warn") is False
        assert checks.should_fail_strict(clean, fail_on="mismatch") is False
        assert checks.should_fail_strict(clean, fail_on="unknown") is False

        # Portability-only different_host WARN trips fail_on="warn", NOT fail_on="mismatch".
        diff_host_manifest = copy.deepcopy(manifest)
        diff_host_manifest["host"]["hostname"] = "compute-node-07"
        diff_host = checks.assess_run(
            diff_host_manifest,
            current_hostname="login-node-01",
            preflight=True,
            cwd=tmp_path,
        )
        assert checks.should_fail_strict(diff_host, fail_on="warn") is True
        assert checks.should_fail_strict(diff_host, fail_on="mismatch") is False
        assert checks.should_fail_strict(diff_host, fail_on="unknown") is False

        # Material mismatch (changed input) trips warn, mismatch, and unknown.
        (tmp_path / "data/input.csv").write_bytes(b"corrupted\n")
        mismatched = checks.assess_run(manifest, preflight=True, cwd=tmp_path)
        assert checks.should_fail_strict(mismatched, fail_on="warn") is True
        assert checks.should_fail_strict(mismatched, fail_on="mismatch") is True
        assert checks.should_fail_strict(mismatched, fail_on="unknown") is True

        # Unverified (stat-only) input trips only fail_on="unknown".
        stat_only_manifest = copy.deepcopy(manifest)
        (tmp_path / "data/input.csv").write_bytes(input_bytes)
        del stat_only_manifest["data_files"]["inputs"][0]["sha256"]
        stat_assess = checks.assess_run(stat_only_manifest, preflight=True, cwd=tmp_path)
        assert checks.should_fail_strict(stat_assess, fail_on="warn") is False
        assert checks.should_fail_strict(stat_assess, fail_on="mismatch") is False
        assert checks.should_fail_strict(stat_assess, fail_on="unknown") is True

        # Manifest-only mode (preflight=False) with uncertain category trips fail_on="unknown".
        manifest_only = checks.assess_run(stat_only_manifest, preflight=False)
        assert checks.should_fail_strict(manifest_only, fail_on="warn") is False
        assert checks.should_fail_strict(manifest_only, fail_on="mismatch") is False
        assert checks.should_fail_strict(manifest_only, fail_on="unknown") is True

        # Invalid fail_on raises ValueError.
        for bad_mode in ("error", "info", "", None):
            with pytest.raises(ValueError):
                checks.should_fail_strict(clean, fail_on=bad_mode)  # type: ignore[arg-type]


class TestPreflightSafetyInvariants:
    """Explicit offline, read-only, and no-replay safety invariant tests."""

    def test_preflight_offline_readonly_no_replay_invariants(
        self, tmp_path: Path, monkeypatch
    ):
        sentinel = tmp_path / "SENTINEL_EXECUTED.txt"
        script_text = (
            "from pathlib import Path\n"
            f"Path({str(sentinel)!r}).write_text('EXECUTED', encoding='utf-8')\n"
        )
        script_bytes = script_text.encode("utf-8")
        input_bytes = b"id,val\n1,42\n"
        commit = _init_git_repo(
            tmp_path,
            {"train.py": script_text, "data/input.csv": input_bytes.decode()},
        )
        manifest = _matching_manifest(
            tmp_path,
            commit=commit,
            script_bytes=script_bytes,
            input_bytes=input_bytes,
        )
        manifest["invocation"]["rerun_command"] = (
            f"cd {tmp_path} && python train.py && touch {sentinel}"
        )

        def _snapshot_tree(root: Path) -> Dict[str, tuple]:
            snap: Dict[str, tuple] = {}
            for p in sorted(root.rglob("*")):
                if ".git" in p.parts:
                    continue
                st = p.stat()
                snap[str(p.relative_to(root))] = (st.st_size, st.st_mtime_ns, p.is_file())
            return snap

        tree_before = _snapshot_tree(tmp_path)
        env_before = dict(os.environ)

        # Forbid all network calls.
        def _forbid_network(*args: Any, **kwargs: Any) -> Any:
            raise AssertionError(f"Network access is forbidden during preflight: {args}")

        monkeypatch.setattr(socket, "create_connection", _forbid_network)
        monkeypatch.setattr(urllib.request, "urlopen", _forbid_network)

        # Restrict subprocess execution strictly to read-only git rev-parse / status.
        real_popen = subprocess.Popen
        observed_cmds: List[List[str]] = []

        def _guarded_popen(args: Any, *pargs: Any, **kwargs: Any) -> Any:
            cmd = list(args) if isinstance(args, (list, tuple)) else [str(args)]
            observed_cmds.append(cmd)
            assert cmd and cmd[0] == "git", f"Unexpected non-git subprocess: {cmd}"
            git_subcmds = [tok for tok in cmd[1:] if not tok.startswith("-") and tok != str(tmp_path)]
            assert git_subcmds, f"Empty git subcommand: {cmd}"
            assert git_subcmds[0] in ("rev-parse", "status"), (
                f"Disallowed non-readonly git subcommand: {cmd}"
            )
            return real_popen(args, *pargs, **kwargs)

        monkeypatch.setattr(subprocess, "Popen", _guarded_popen)

        assessment = assess_run(manifest, preflight=True, cwd=tmp_path)

        assert assessment["mode"] == "preflight"
        assert assessment["preflight"]["status"] == "match"
        assert not sentinel.exists()
        assert _snapshot_tree(tmp_path) == tree_before
        assert dict(os.environ) == env_before
        assert len(observed_cmds) == 2
        assert DEFAULT_MAX_HASH_BYTES == 104_857_600
