"""Fallback tests for process, host, and python_runtime capture engines."""
import getpass
import os
import platform
import socket
import sys

import pytest

from pubrun.capture.host import get_host
from pubrun.capture.process import get_process_info
from pubrun.capture.python_runtime import environment_kind


class TestProcessFallbacks:
    def test_getuser_failure_reports_unknown(self, monkeypatch):
        def _fail():
            raise OSError("no passwd entry")

        monkeypatch.setattr(getpass, "getuser", _fail)
        res = get_process_info({})
        assert res["user"]["username"] == {"representation": "plain", "value": "unknown"}
        assert res["capture_state"]["status"] == "complete"

    def test_missing_getuid_getgid_reports_none(self, monkeypatch):
        monkeypatch.delattr(os, "getuid", raising=False)
        monkeypatch.delattr(os, "getgid", raising=False)
        res = get_process_info({})
        assert res["user"]["uid"] is None
        assert res["user"]["gid"] is None
        assert res["capture_state"]["status"] == "complete"


class TestHostFallbacks:
    def test_empty_node_falls_back_to_socket_hostname(self, monkeypatch):
        monkeypatch.setattr(platform, "node", lambda: "")
        monkeypatch.setattr(socket, "gethostname", lambda: "fallback-host")
        res = get_host({})
        assert res["hostname"] == "fallback-host"
        assert res["capture_state"]["status"] == "complete"

    def test_platform_system_failure_returns_failed_state(self, monkeypatch):
        def _boom():
            raise RuntimeError("uname broke")

        monkeypatch.setattr(platform, "system", _boom)
        res = get_host({})
        assert res == {"capture_state": {"status": "failed", "detail": "uname broke"}}


@pytest.fixture
def plain_env(tmp_path, monkeypatch):
    """Isolate sys and os.environ to a plain non-venv, non-conda, non-pyenv environment."""
    prefix = str(tmp_path)
    monkeypatch.setattr(sys, "prefix", prefix)
    monkeypatch.setattr(sys, "base_prefix", prefix, raising=False)
    monkeypatch.setattr(
        sys, "executable", os.path.join(os.sep, "opt", "py", "bin", "python")
    )
    monkeypatch.delattr(sys, "real_prefix", raising=False)
    monkeypatch.delattr(sys, "frozen", raising=False)
    monkeypatch.delenv("CONDA_PREFIX", raising=False)
    monkeypatch.delenv("PYENV_VERSION", raising=False)
    return tmp_path


class TestPythonRuntimeEnvironmentKind:
    def test_plain_environment_is_system(self, plain_env):
        res = environment_kind()
        assert res["environment_kind"] == "system"
        assert res["pyenv"] is False

    def test_conda_meta_directory_is_conda(self, plain_env):
        (plain_env / "conda-meta").mkdir()
        res = environment_kind()
        assert res["environment_kind"] == "conda"

    def test_real_prefix_is_virtualenv(self, plain_env, monkeypatch):
        monkeypatch.setattr(sys, "real_prefix", "/usr", raising=False)
        res = environment_kind()
        assert res["environment_kind"] == "virtualenv"

    def test_frozen_wins_over_conda(self, plain_env, monkeypatch):
        (plain_env / "conda-meta").mkdir()
        monkeypatch.setattr(sys, "frozen", True, raising=False)
        res = environment_kind()
        assert res["environment_kind"] == "frozen"

    def test_pyenv_version_env_var(self, plain_env, monkeypatch):
        monkeypatch.setenv("PYENV_VERSION", "3.12.3")
        res = environment_kind()
        assert res["pyenv"] is True
        assert res["environment_kind"] == "system"

    def test_isdir_oserror_falls_back_to_system(self, plain_env, monkeypatch):
        def _fail(_path):
            raise OSError("stat failed")

        monkeypatch.setattr(os.path, "isdir", _fail)
        res = environment_kind()
        assert res["environment_kind"] == "system"
