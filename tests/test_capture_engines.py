"""Tests for capture engines: environment, host, process, python_runtime, packages, git."""
import os
import sys
import pytest
from unittest.mock import patch, MagicMock

from pubrun.capture.environment import get_environment
from pubrun.capture.host import get_host
from pubrun.capture.process import get_process_info
from pubrun.capture.python_runtime import get_python_runtime
from pubrun.capture.packages import get_packages
from pubrun.capture.git import get_git


# ---------------------------------------------------------------------------
# Environment
# ---------------------------------------------------------------------------
class TestEnvironment:

    def test_returns_correct_structure(self):
        config = {"capture": {"environment": {"mode": "filtered"}}}
        result = get_environment(config)
        assert "mode" in result
        assert "variables" in result
        assert "capture_state" in result
        assert result["capture_state"]["status"] == "complete"

    def test_variables_are_sorted_by_name(self):
        config = {"capture": {"environment": {"mode": "full"}}}
        result = get_environment(config)
        names = [v["name"] for v in result["variables"]]
        assert names == sorted(names)

    def test_each_variable_has_schema_keys(self):
        config = {"capture": {"environment": {"mode": "filtered"}}}
        result = get_environment(config)
        for var in result["variables"]:
            assert "name" in var
            assert "value" in var
            assert "source" in var
            assert isinstance(var["value"], dict)
            assert "representation" in var["value"]

    def test_suppressed_when_off(self):
        config = {"capture": {"environment": {"mode": "off"}}}
        result = get_environment(config)
        assert result["capture_state"]["status"] == "suppressed"
        assert "variables" not in result

    def test_redacts_secrets(self):
        config = {"capture": {"environment": {"mode": "filtered"}}}
        with patch.dict(os.environ, {"TEST_API_TOKEN": "sk-live-xxx"}, clear=False):
            result = get_environment(config)
        by_name = {v["name"]: v for v in result["variables"]}
        if "TEST_API_TOKEN" in by_name:
            assert by_name["TEST_API_TOKEN"]["value"]["representation"] == "redacted"

    def test_redaction_disabled_via_config(self):
        config = {
            "capture": {"environment": {"mode": "filtered"}},
            "redaction": {"env_enabled": False}
        }
        with patch.dict(os.environ, {"TEST_API_TOKEN": "visible"}, clear=False):
            result = get_environment(config)
        by_name = {v["name"]: v for v in result["variables"]}
        if "TEST_API_TOKEN" in by_name:
            assert by_name["TEST_API_TOKEN"]["value"]["representation"] == "plain"
            assert by_name["TEST_API_TOKEN"]["value"]["value"] == "visible"


# ---------------------------------------------------------------------------
# Host
# ---------------------------------------------------------------------------
class TestHost:

    def test_returns_correct_structure(self):
        result = get_host({})
        assert "os_name" in result
        assert "os_version" in result
        assert "hostname" in result
        assert result["capture_state"]["status"] == "complete"

    def test_os_name_is_string(self):
        result = get_host({})
        assert isinstance(result["os_name"], str)
        assert len(result["os_name"]) > 0

    def test_suppressed_when_disabled(self):
        config = {"capture": {"host": {"enabled": False}}}
        result = get_host(config)
        assert result["capture_state"]["status"] == "suppressed"
        assert "os_name" not in result


# ---------------------------------------------------------------------------
# Process
# ---------------------------------------------------------------------------
class TestProcess:

    def test_returns_correct_structure(self):
        result = get_process_info({})
        assert "pid" in result
        assert "ppid" in result
        assert "user" in result
        assert result["capture_state"]["status"] == "complete"

    def test_pid_is_current(self):
        result = get_process_info({})
        assert result["pid"] == os.getpid()

    def test_user_has_schema_keys(self):
        result = get_process_info({})
        user = result["user"]
        assert "username" in user
        assert "uid" in user
        assert "gid" in user
        assert user["username"]["representation"] == "plain"

    def test_uid_gid_are_integers_on_unix(self):
        result = get_process_info({})
        if hasattr(os, "getuid"):
            assert isinstance(result["user"]["uid"], int)
            assert isinstance(result["user"]["gid"], int)


# ---------------------------------------------------------------------------
# Python Runtime
# ---------------------------------------------------------------------------
class TestPythonRuntime:

    def test_returns_correct_structure(self):
        result = get_python_runtime({})
        assert "executable" in result
        assert "version" in result
        assert "implementation" in result
        assert "prefix" in result
        assert "sys_path" in result
        assert result["capture_state"]["status"] == "complete"

    def test_executable_matches_current(self):
        result = get_python_runtime({})
        assert result["executable"] == sys.executable

    def test_version_is_current(self):
        result = get_python_runtime({})
        assert result["version"] == sys.version

    def test_implementation_is_cpython(self):
        result = get_python_runtime({})
        assert result["implementation"] == "cpython"

    def test_sys_path_is_list(self):
        result = get_python_runtime({})
        assert isinstance(result["sys_path"], list)


# ---------------------------------------------------------------------------
# Packages
# ---------------------------------------------------------------------------
class TestPackages:

    def test_returns_correct_structure(self):
        config = {"capture": {"packages": {"mode": "imported-only"}}}
        result = get_packages(config)
        assert "mode" in result
        assert "records" in result
        assert result["capture_state"]["status"] == "complete"

    def test_records_sorted_by_name(self):
        config = {"capture": {"packages": {"mode": "imported-only"}}}
        result = get_packages(config)
        names = [r["name"].lower() for r in result["records"]]
        assert names == sorted(names)

    def test_each_record_has_schema_keys(self):
        config = {"capture": {"packages": {"mode": "imported-only"}}}
        result = get_packages(config)
        for rec in result["records"]:
            assert "name" in rec
            assert "version" in rec

    def test_suppressed_when_off(self):
        config = {"capture": {"packages": {"mode": "off"}}}
        result = get_packages(config)
        assert result["capture_state"]["status"] == "suppressed"
        assert "records" not in result

    def test_full_environment_returns_more(self):
        config_imported = {"capture": {"packages": {"mode": "imported-only"}}}
        config_full = {"capture": {"packages": {"mode": "full-environment"}}}
        imported = get_packages(config_imported)
        full = get_packages(config_full)
        # Full env should capture at least as many as imported-only
        assert len(full["records"]) >= len(imported["records"])

    def test_detects_pubrun_itself(self):
        config = {"capture": {"packages": {"mode": "imported-only"}}}
        result = get_packages(config)
        names = [r["name"].lower() for r in result["records"]]
        assert "pubrun" in names


# ---------------------------------------------------------------------------
# Git
# ---------------------------------------------------------------------------
class TestGit:

    def test_returns_correct_structure(self):
        result = get_git({})
        assert "capture_state" in result

    def test_has_commit_when_in_repo(self):
        """We're running from the pubrun repo, so git should find a commit."""
        result = get_git({})
        if result["capture_state"]["status"] == "complete":
            assert "commit" in result
            assert isinstance(result["commit"], str)
            assert len(result["commit"]) == 40  # Full SHA-1

    def test_has_branch(self):
        result = get_git({})
        if result["capture_state"]["status"] == "complete":
            assert "branch" in result

    def test_has_is_dirty(self):
        result = get_git({})
        if result["capture_state"]["status"] == "complete":
            assert "is_dirty" in result
            assert isinstance(result["is_dirty"], bool)

    def test_no_crash_outside_git_repo(self, tmp_path, monkeypatch):
        """Simulate running outside a git repo."""
        monkeypatch.chdir(tmp_path)
        result = get_git({})
        # Should not crash; returns suppressed or empty
        assert "capture_state" in result
