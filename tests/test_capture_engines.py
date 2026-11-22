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

    def test_default_mode_is_imported_only(self):
        result = get_packages({})
        assert result["mode"] == "imported-only"
        assert "records" in result

    def test_top_level_installed_is_subset_of_full_environment(self):
        top = get_packages({"capture": {"packages": {"mode": "top-level-installed"}}})
        full = get_packages({"capture": {"packages": {"mode": "full-environment"}}})
        assert top["mode"] == "top-level-installed"
        top_names = {r["name"].lower() for r in top["records"]}
        full_names = {r["name"].lower() for r in full["records"]}
        assert top_names.issubset(full_names)


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

    def test_has_dirty(self):
        result = get_git({})
        if result["capture_state"]["status"] == "complete":
            assert "dirty" in result
            assert isinstance(result["dirty"], bool)

    def test_git_capture_redaction_token(self):
        """Test that git capture redacts token in remote url."""
        def mock_run(args, **kwargs):
            cmd = args
            if "--show-toplevel" in cmd:
                return MagicMock(returncode=0, stdout="/some/path")
            elif "--abbrev-ref" in cmd:
                return MagicMock(returncode=0, stdout="main")
            elif "HEAD" in cmd:
                return MagicMock(returncode=0, stdout="a"*40)
            elif "status" in cmd:
                return MagicMock(returncode=0, stdout="")
            elif "remote" in cmd and "get-url" in cmd:
                return MagicMock(returncode=0, stdout="https://mytoken@github.com/user/repo.git\n")
            return MagicMock(returncode=1)

        with patch("subprocess.run", side_effect=mock_run):
            result = get_git({})
            assert result["capture_state"]["status"] == "complete"
            assert result["commit"] == "a"*40
            assert result["branch"] == "main"
            assert result["dirty"] is False
            assert result["remote_url"] == {
                "representation": "plain",
                "value": "https://[REDACTED]@github.com/user/repo.git"
            }

    def test_git_capture_redaction_password(self):
        """Test that git capture redacts password in remote url."""
        def mock_run(args, **kwargs):
            cmd = args
            if "--show-toplevel" in cmd:
                return MagicMock(returncode=0, stdout="/some/path")
            elif "--abbrev-ref" in cmd:
                return MagicMock(returncode=0, stdout="main")
            elif "HEAD" in cmd:
                return MagicMock(returncode=0, stdout="a"*40)
            elif "status" in cmd:
                return MagicMock(returncode=0, stdout="")
            elif "remote" in cmd and "get-url" in cmd:
                return MagicMock(returncode=0, stdout="https://user:password@github.com/user/repo.git\n")
            return MagicMock(returncode=1)

        with patch("subprocess.run", side_effect=mock_run):
            result = get_git({})
            assert result["capture_state"]["status"] == "complete"
            assert result["remote_url"] == {
                "representation": "plain",
                "value": "https://user:[REDACTED]@github.com/user/repo.git"
            }

    def test_no_crash_outside_git_repo(self, tmp_path, monkeypatch):
        """Simulate running outside a git repo and verify single git subprocess spawn."""
        import subprocess
        monkeypatch.chdir(tmp_path)
        calls = []
        real_run = subprocess.run

        def spy_run(args, *a, **kw):
            calls.append(list(args))
            return real_run(args, *a, **kw)

        monkeypatch.setattr(subprocess, "run", spy_run)
        result = get_git({})
        assert result["capture_state"]["status"] == "unavailable"
        assert len(calls) == 1

    def test_combined_rev_parse_reduces_spawns_on_real_repo(self, tmp_path, monkeypatch):
        """Normal git repository uses combined rev-parse (3 spawns total, 2 without dirty check)."""
        import subprocess
        repo = tmp_path / "repo"
        repo.mkdir()
        subprocess.run(["git", "init"], cwd=repo, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo, check=True)
        subprocess.run(["git", "config", "user.name", "Test User"], cwd=repo, check=True)
        (repo / "hello.txt").write_text("hi\n", encoding="utf-8")
        subprocess.run(["git", "add", "hello.txt"], cwd=repo, check=True)
        subprocess.run(["git", "commit", "-m", "init"], cwd=repo, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        monkeypatch.chdir(repo)

        calls = []
        real_run = subprocess.run

        def spy_run(args, *a, **kw):
            calls.append(list(args))
            return real_run(args, *a, **kw)

        monkeypatch.setattr(subprocess, "run", spy_run)
        result = get_git({"capture": {"git": {"enabled": True, "check_dirty": True}}})
        assert result["capture_state"]["status"] == "complete"
        assert len(result["commit"]) == 40
        assert result["dirty"] is False
        assert len(calls) == 3
        assert calls[0] == ["git", "rev-parse", "--show-toplevel", "HEAD", "--abbrev-ref", "HEAD"]

        calls.clear()
        result_no_dirty = get_git({"capture": {"git": {"enabled": True, "check_dirty": False}}})
        assert result_no_dirty["capture_state"]["status"] == "complete"
        assert result_no_dirty["dirty"] is None
        assert len(calls) == 2

    def test_unborn_head_empty_repo_handled_cleanly(self, tmp_path, monkeypatch):
        """Empty git repo with unborn HEAD returns repo_root, null commit/branch, complete state."""
        import subprocess
        repo = tmp_path / "empty_repo"
        repo.mkdir()
        subprocess.run(["git", "init"], cwd=repo, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        monkeypatch.chdir(repo)

        result = get_git({"capture": {"git": {"enabled": True}}})
        assert result["capture_state"]["status"] == "complete"
        assert result["repo_root"] is not None
        assert result["commit"] is None
        assert result["branch"] is None

    def test_git_total_timeout_zero_skips_spawns_and_reports_timeout(self, monkeypatch):
        """total_timeout=0 exhausts budget before launching any git subprocess."""
        import subprocess
        calls = []

        def spy_run(args, *a, **kw):
            calls.append(args)
            return MagicMock(returncode=0, stdout="", stderr="")

        monkeypatch.setattr(subprocess, "run", spy_run)
        result = get_git({"capture": {"git": {"enabled": True, "timeout": 5, "total_timeout": 0}}})
        assert result["capture_state"]["status"] == "timeout"
        assert calls == []

    def test_git_post_root_timeout_reports_partial_and_skips_remaining(self, monkeypatch):
        """When status --porcelain times out and exhausts total_timeout, report partial and skip remote."""
        import subprocess
        import pubrun.capture.git as git_mod

        now = [100.0]
        calls = []

        def fake_monotonic():
            return now[0]

        def fake_run(args, **kwargs):
            calls.append(list(args))
            if "rev-parse" in args:
                now[0] += 0.2
                return MagicMock(
                    returncode=0,
                    stdout="/repo/root\n" + ("a" * 40) + "\nmain\n",
                    stderr="",
                )
            if "status" in args:
                now[0] += 1.0
                raise subprocess.TimeoutExpired(cmd=args, timeout=kwargs.get("timeout", 1.0))
            return MagicMock(returncode=0, stdout="https://example.com/repo.git\n", stderr="")

        monkeypatch.setattr(git_mod.time, "monotonic", fake_monotonic)
        monkeypatch.setattr(git_mod.subprocess, "run", fake_run)

        result = get_git(
            {"capture": {"git": {"enabled": True, "timeout": 5, "total_timeout": 1.0}}}
        )
        assert result["capture_state"]["status"] == "partial"
        assert result["repo_root"] == "/repo/root"
        assert result["commit"] == "a" * 40
        assert result["branch"] == "main"
        assert result["dirty"] is None
        # remote get-url origin was skipped because budget was exhausted after status timeout
        assert len(calls) == 2

    def test_git_invalid_timeout_values_fall_back_safely(self, monkeypatch):
        """Non-finite, negative, or boolean timeout configs fall back safely without crashing."""
        import pubrun.capture.git as git_mod

        seen_timeouts = []

        def fake_run(args, **kwargs):
            seen_timeouts.append(kwargs.get("timeout"))
            return MagicMock(
                returncode=0,
                stdout="/repo\n" + ("b" * 40) + "\nmain\n",
                stderr="",
            )

        monkeypatch.setattr(git_mod.subprocess, "run", fake_run)
        result = get_git(
            {
                "capture": {
                    "git": {
                        "enabled": True,
                        "timeout": float("nan"),
                        "total_timeout": float("inf"),
                        "check_dirty": False,
                    }
                }
            }
        )
        assert result["capture_state"]["status"] == "complete"
        assert seen_timeouts
        assert all(0 < t <= 5.0 for t in seen_timeouts)
