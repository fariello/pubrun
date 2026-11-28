"""Regression tests for config discovery and capture mode/depth enforcement.

Covers BUG-40 (boot import-mode discovery parity), BUG-63 (non-mutating
override resolution and empty XDG_CONFIG_HOME), and BUG-39 (environment
allowlist mode and per-collector ``depth = "off"``).
"""
import copy
import os
import subprocess
import sys
import warnings
from pathlib import Path

import pytest

from pubrun import _bootstrap
from pubrun._bootstrap import PubrunImportModeConflictError, PubrunImportModeConflictWarning
from pubrun._config_boot import resolve_import_mode
from pubrun.capture.environment import get_environment
from pubrun.capture.git import get_git
from pubrun.capture.host import get_host
from pubrun.capture.process import get_process_info
from pubrun.capture.python_runtime import get_python_runtime
from pubrun.config import (
    get_global_config_dir,
    resolve_config,
    resolve_config_with_provenance,
)


@pytest.fixture
def isolated_home(tmp_path, monkeypatch):
    """Point HOME at a fresh directory and clear XDG/APPDATA and import-mode env vars."""
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("USERPROFILE", str(home))
    monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
    monkeypatch.delenv("APPDATA", raising=False)
    monkeypatch.delenv("PUBRUN_IMPORT_MODE", raising=False)
    monkeypatch.delenv("PUBRUN_AUTO_START", raising=False)
    monkeypatch.delenv("PUBRUN_PROFILE", raising=False)
    monkeypatch.delenv("PUBRUN_META_REF", raising=False)
    return home


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _non_windows(monkeypatch):
    monkeypatch.setattr("sys.platform", "linux")


# ---------------------------------------------------------------------------
# BUG-63: get_global_config_dir and non-mutating override resolution
# ---------------------------------------------------------------------------


class TestGlobalConfigDir:
    @pytest.mark.parametrize("value", ["", "   ", "\t"])
    def test_empty_xdg_falls_back_to_home_config(self, isolated_home, monkeypatch, value):
        _non_windows(monkeypatch)
        monkeypatch.setenv("XDG_CONFIG_HOME", value)
        result = get_global_config_dir()
        assert result == Path(os.path.expanduser("~/.config")) / "pubrun"
        assert result.is_absolute()
        assert str(result).startswith(str(isolated_home))

    def test_nonempty_xdg_is_honored(self, isolated_home, tmp_path, monkeypatch):
        _non_windows(monkeypatch)
        xdg = tmp_path / "xdg"
        monkeypatch.setenv("XDG_CONFIG_HOME", str(xdg))
        assert get_global_config_dir() == xdg / "pubrun"

    @pytest.mark.parametrize("value", ["", "  "])
    def test_empty_appdata_on_windows_falls_back(self, isolated_home, monkeypatch, value):
        monkeypatch.setattr("sys.platform", "win32")
        monkeypatch.setenv("APPDATA", value)
        result = get_global_config_dir()
        assert result == Path(os.path.expanduser("~/.config")) / "pubrun"
        assert result.is_absolute()


class TestOverridesNotMutated:
    def _overrides(self):
        return {
            "core": {"output_dir": "./nested_out"},
            "profile": "deep",
            "console": {"capture_mode": "off"},
        }

    def test_resolve_config_does_not_mutate_caller(self, isolated_home):
        overrides = self._overrides()
        snapshot = copy.deepcopy(overrides)
        core_ref = overrides["core"]
        cfg = resolve_config(overrides)
        assert overrides == snapshot
        assert core_ref == {"output_dir": "./nested_out"}
        assert cfg["core"]["profile"] == "deep"
        assert cfg["core"]["output_dir"] == "./nested_out"
        assert cfg["console"]["capture_mode"] == "off"

    def test_resolve_config_with_provenance_does_not_mutate_caller(self, isolated_home):
        overrides = self._overrides()
        snapshot = copy.deepcopy(overrides)
        cfg, prov = resolve_config_with_provenance(overrides)
        assert overrides == snapshot
        assert cfg["core"]["profile"] == "deep"
        assert prov["core.profile"]["layer"] == "api"

    def test_repeated_resolution_is_stable(self, isolated_home):
        overrides = self._overrides()
        first = resolve_config(overrides)
        second = resolve_config(overrides)
        assert first == second


# ---------------------------------------------------------------------------
# BUG-40: boot import-mode discovery parity
# ---------------------------------------------------------------------------


class TestBootDiscovery:
    @pytest.mark.parametrize(
        "value,expected",
        [
            ("1", "auto"), ("true", "auto"), ("yes", "auto"), ("on", "auto"),
            ("YES", "auto"), ("On", "auto"), (" TRUE ", "auto"),
            ("0", "noauto"), ("false", "noauto"), ("no", "noauto"), ("off", "noauto"),
            ("NO", "noauto"), ("Off", "noauto"),
        ],
    )
    def test_auto_start_env_values(self, isolated_home, monkeypatch, value, expected):
        monkeypatch.setenv("PUBRUN_AUTO_START", value)
        assert resolve_import_mode() == (expected, "env:PUBRUN_AUTO_START")

    def test_unrecognized_auto_start_env_ignored(self, isolated_home, monkeypatch):
        monkeypatch.setenv("PUBRUN_AUTO_START", "maybe")
        assert resolve_import_mode() == ("auto", "default")

    @pytest.mark.parametrize(
        "toml_value,expected",
        [
            ('"on"', "auto"), ('"yes"', "auto"), ('"1"', "auto"), ("true", "auto"),
            ('"off"', "noauto"), ('"no"', "noauto"), ('"0"', "noauto"), ("false", "noauto"),
        ],
    )
    def test_core_auto_start_file_values(self, isolated_home, tmp_path, toml_value, expected):
        _write(tmp_path / ".pubrun.toml", f"[core]\nauto_start = {toml_value}\n")
        assert resolve_import_mode() == (expected, "config:[core].auto_start")

    def test_user_global_config_is_read(self, isolated_home, monkeypatch):
        _non_windows(monkeypatch)
        _write(isolated_home / ".config" / "pubrun" / "config.toml", '[imports]\nmode = "nopatch"\n')
        assert resolve_import_mode() == ("nopatch", "config:[imports].mode")

    def test_user_global_auto_start_is_read(self, isolated_home, monkeypatch):
        _non_windows(monkeypatch)
        _write(isolated_home / ".config" / "pubrun" / "config.toml", "[core]\nauto_start = false\n")
        assert resolve_import_mode() == ("noauto", "config:[core].auto_start")

    def test_xdg_config_home_is_honored(self, isolated_home, tmp_path, monkeypatch):
        _non_windows(monkeypatch)
        xdg = tmp_path / "xdg"
        monkeypatch.setenv("XDG_CONFIG_HOME", str(xdg))
        _write(xdg / "pubrun" / "config.toml", '[imports]\nmode = "minimal"\n')
        # A file under ~/.config must be ignored when XDG_CONFIG_HOME is set.
        _write(isolated_home / ".config" / "pubrun" / "config.toml", '[imports]\nmode = "nopatch"\n')
        assert resolve_import_mode() == ("minimal", "config:[imports].mode")

    def test_empty_xdg_config_home_falls_back_to_home(self, isolated_home, monkeypatch):
        _non_windows(monkeypatch)
        monkeypatch.setenv("XDG_CONFIG_HOME", "  ")
        _write(isolated_home / ".config" / "pubrun" / "config.toml", '[imports]\nmode = "noauto"\n')
        assert resolve_import_mode() == ("noauto", "config:[imports].mode")

    def test_appdata_on_windows_is_honored(self, isolated_home, tmp_path, monkeypatch):
        monkeypatch.setattr("sys.platform", "win32")
        appdata = tmp_path / "appdata"
        monkeypatch.setenv("APPDATA", str(appdata))
        _write(appdata / "pubrun" / "config.toml", '[imports]\nmode = "noconsole"\n')
        assert resolve_import_mode() == ("noconsole", "config:[imports].mode")

    def test_project_deep_config_is_read(self, isolated_home, tmp_path):
        _write(tmp_path / ".config" / "pubrun" / "config.toml", '[imports]\nmode = "nopatch"\n')
        assert resolve_import_mode() == ("nopatch", "config:[imports].mode")

    def test_precedence_pubrun_toml_over_deep_over_user(self, isolated_home, tmp_path, monkeypatch):
        _non_windows(monkeypatch)
        _write(isolated_home / ".config" / "pubrun" / "config.toml", '[imports]\nmode = "minimal"\n')
        _write(tmp_path / ".config" / "pubrun" / "config.toml", '[imports]\nmode = "nopatch"\n')
        _write(tmp_path / ".pubrun.toml", '[imports]\nmode = "noconsole"\n')
        assert resolve_import_mode() == ("noconsole", "config:[imports].mode")

        (tmp_path / ".pubrun.toml").unlink()
        assert resolve_import_mode() == ("nopatch", "config:[imports].mode")

        (tmp_path / ".config" / "pubrun" / "config.toml").unlink()
        assert resolve_import_mode() == ("minimal", "config:[imports].mode")

    def test_higher_file_auto_start_beats_lower_file_mode(self, isolated_home, tmp_path, monkeypatch):
        _non_windows(monkeypatch)
        _write(isolated_home / ".config" / "pubrun" / "config.toml", '[imports]\nmode = "minimal"\n')
        _write(tmp_path / ".pubrun.toml", "[core]\nauto_start = false\n")
        assert resolve_import_mode() == ("noauto", "config:[core].auto_start")

    def test_file_without_mode_keys_falls_through(self, isolated_home, tmp_path, monkeypatch):
        _non_windows(monkeypatch)
        _write(tmp_path / ".pubrun.toml", '[console]\ncapture_mode = "off"\n')
        _write(isolated_home / ".config" / "pubrun" / "config.toml", '[imports]\nmode = "nopatch"\n')
        assert resolve_import_mode() == ("nopatch", "config:[imports].mode")

    def test_invalid_mode_in_higher_file_falls_through(self, isolated_home, tmp_path):
        _write(tmp_path / ".pubrun.toml", '[imports]\nmode = "bogus"\n')
        _write(tmp_path / ".config" / "pubrun" / "config.toml", '[imports]\nmode = "minimal"\n')
        assert resolve_import_mode() == ("minimal", "config:[imports].mode")

    def test_malformed_higher_file_is_skipped(self, isolated_home, tmp_path):
        _write(tmp_path / ".pubrun.toml", "[imports\nmode = = \n")
        _write(tmp_path / ".config" / "pubrun" / "config.toml", '[imports]\nmode = "noauto"\n')
        assert resolve_import_mode() == ("noauto", "config:[imports].mode")

    def test_env_beats_all_files(self, isolated_home, tmp_path, monkeypatch):
        _write(tmp_path / ".pubrun.toml", '[imports]\nmode = "minimal"\n')
        monkeypatch.setenv("PUBRUN_AUTO_START", "on")
        assert resolve_import_mode() == ("auto", "env:PUBRUN_AUTO_START")

    def test_no_files_is_default(self, isolated_home):
        assert resolve_import_mode() == ("auto", "default")


# ---------------------------------------------------------------------------
# ql671s: [imports].on_conflict is read from every boot config file
# ---------------------------------------------------------------------------


_REPO_SRC = str(Path(__file__).resolve().parents[1] / "src")


def _conflict_toml(policy: str) -> str:
    return f'[imports]\non_conflict = "{policy}"\n'


def _trigger_conflict():
    _bootstrap.select_mode("auto", "pubrun", "default")
    _bootstrap.select_mode("minimal", "pubrun.minimal", "explicit")


def _assert_conflict_raises():
    _bootstrap.reset_state()
    with pytest.raises(PubrunImportModeConflictError):
        _trigger_conflict()


def _assert_conflict_silent():
    _bootstrap.reset_state()
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        _trigger_conflict()
    assert not [w for w in caught if issubclass(w.category, PubrunImportModeConflictWarning)]


class TestBootConflictPolicyDiscovery:
    @pytest.fixture(autouse=True)
    def _clear_conflict_env(self, monkeypatch):
        monkeypatch.delenv("PUBRUN_IMPORT_CONFLICT", raising=False)

    def test_project_deep_config_is_read(self, isolated_home, tmp_path):
        _write(tmp_path / ".config" / "pubrun" / "config.toml", _conflict_toml("error"))
        _assert_conflict_raises()

    def test_user_global_config_is_read(self, isolated_home, monkeypatch):
        _non_windows(monkeypatch)
        _write(isolated_home / ".config" / "pubrun" / "config.toml", _conflict_toml("error"))
        _assert_conflict_raises()

    def test_xdg_config_home_is_honored(self, isolated_home, tmp_path, monkeypatch):
        _non_windows(monkeypatch)
        xdg = tmp_path / "xdg"
        monkeypatch.setenv("XDG_CONFIG_HOME", str(xdg))
        _write(xdg / "pubrun" / "config.toml", _conflict_toml("error"))
        _assert_conflict_raises()

    def test_appdata_on_windows_is_honored(self, isolated_home, tmp_path, monkeypatch):
        monkeypatch.setattr("sys.platform", "win32")
        appdata = tmp_path / "appdata"
        monkeypatch.setenv("APPDATA", str(appdata))
        _write(appdata / "pubrun" / "config.toml", _conflict_toml("error"))
        _assert_conflict_raises()

    def test_precedence_pubrun_toml_over_deep(self, isolated_home, tmp_path):
        _write(tmp_path / ".pubrun.toml", _conflict_toml("ignore"))
        _write(tmp_path / ".config" / "pubrun" / "config.toml", _conflict_toml("error"))
        _assert_conflict_silent()

        (tmp_path / ".pubrun.toml").unlink()
        _assert_conflict_raises()

    def test_invalid_value_in_higher_file_falls_through(self, isolated_home, tmp_path):
        _write(tmp_path / ".pubrun.toml", _conflict_toml("bogus"))
        _write(tmp_path / ".config" / "pubrun" / "config.toml", _conflict_toml("error"))
        _assert_conflict_raises()

    def test_malformed_higher_file_is_skipped(self, isolated_home, tmp_path):
        _write(tmp_path / ".pubrun.toml", "[imports\non_conflict = = \n")
        _write(tmp_path / ".config" / "pubrun" / "config.toml", _conflict_toml("error"))
        _assert_conflict_raises()

    def test_env_beats_all_files(self, isolated_home, tmp_path, monkeypatch):
        monkeypatch.setenv("PUBRUN_IMPORT_CONFLICT", "ignore")
        _write(tmp_path / ".config" / "pubrun" / "config.toml", _conflict_toml("error"))
        _assert_conflict_silent()

    def test_no_files_warns_once(self, isolated_home):
        _bootstrap.reset_state()
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            _trigger_conflict()
        conflicts = [w for w in caught if issubclass(w.category, PubrunImportModeConflictWarning)]
        assert len(conflicts) == 1

    def test_child_process_import_conflict_raises(self, isolated_home, tmp_path):
        _write(tmp_path / ".config" / "pubrun" / "config.toml", _conflict_toml("error"))
        env = dict(os.environ)
        for name in ("PUBRUN_IMPORT_CONFLICT", "PUBRUN_IMPORT_MODE", "XDG_CONFIG_HOME", "APPDATA"):
            env.pop(name, None)
        env["PUBRUN_AUTO_START"] = "false"
        env["HOME"] = str(isolated_home)
        env["USERPROFILE"] = str(isolated_home)
        env["XDG_CONFIG_HOME"] = str(isolated_home / ".config")
        existing = env.get("PYTHONPATH", "")
        env["PYTHONPATH"] = f"{_REPO_SRC}{os.pathsep}{existing}" if existing else _REPO_SRC
        res = subprocess.run(
            [sys.executable, "-c", "import pubrun, pubrun.minimal"],
            cwd=str(tmp_path),
            env=env,
            capture_output=True,
            text=True,
            timeout=60,
        )
        assert res.returncode != 0
        assert "PubrunImportModeConflictError" in res.stderr


# ---------------------------------------------------------------------------
# BUG-39: environment allowlist mode and depth = "off"
# ---------------------------------------------------------------------------


def _env_config(**env_cfg):
    cfg = resolve_config()
    cfg["capture"]["environment"].update(env_cfg)
    return cfg


def _names(result):
    return [v["name"] for v in result["variables"]]


class TestEnvironmentCapture:
    def test_default_config_defines_empty_allowlist(self, isolated_home):
        assert resolve_config()["capture"]["environment"]["allowlist"] == []

    def test_depth_off_suppresses_without_reading_environ(self, isolated_home, monkeypatch):
        import types

        class _FakeOs(types.SimpleNamespace):
            @property
            def environ(self):
                raise AssertionError("os.environ must not be read")

        cfg = _env_config(depth="off")
        monkeypatch.setattr("pubrun.capture.environment.os", _FakeOs())
        assert get_environment(cfg) == {"capture_state": {"status": "suppressed"}}

    @pytest.mark.parametrize("allowlist", [[], None, "PATH", 42, {"PATH": 1}, [None, 5, ""]])
    def test_allowlist_fails_closed(self, isolated_home, monkeypatch, allowlist):
        monkeypatch.setenv("PUBRUN_TEST_VAR", "x")
        if allowlist is None:
            cfg = _env_config(mode="allowlist")
            cfg["capture"]["environment"].pop("allowlist", None)
        else:
            cfg = _env_config(mode="allowlist", allowlist=allowlist)
        result = get_environment(cfg)
        assert result["mode"] == "allowlist"
        assert result["variables"] == []
        assert result["capture_state"] == {"status": "complete"}

    def test_allowlist_exact_and_glob(self, isolated_home, monkeypatch):
        monkeypatch.setenv("PUBRUN_KEEP_EXACT", "a")
        monkeypatch.setenv("PRT_JOB_ID", "1")
        monkeypatch.setenv("PRT_NODE", "n1")
        monkeypatch.setenv("PUBRUN_DROP_ME", "b")
        cfg = _env_config(mode="allowlist", allowlist=["PUBRUN_KEEP_EXACT", "PRT_*"])
        result = get_environment(cfg)
        assert _names(result) == ["PRT_JOB_ID", "PRT_NODE", "PUBRUN_KEEP_EXACT"]
        values = {v["name"]: v["value"] for v in result["variables"]}
        assert values["PRT_JOB_ID"] == {"representation": "plain", "value": "1"}

    def test_allowlist_glob_is_case_sensitive(self, isolated_home, monkeypatch):
        monkeypatch.setattr("sys.platform", "linux")
        monkeypatch.setenv("PRT_UPPER", "1")
        cfg = _env_config(mode="allowlist", allowlist=["prt_*", "prt_upper"])
        assert get_environment(cfg)["variables"] == []

    def test_allowlist_glob_is_case_insensitive_on_windows(self, isolated_home, monkeypatch):
        from pubrun.capture import environment as env_mod

        monkeypatch.setattr("sys.platform", "win32")
        monkeypatch.setattr(
            env_mod.os,
            "environ",
            {"PRT_UPPER": "1", "Prt_Mixed": "2", "OTHER_VAR": "3"},
        )
        cfg = _env_config(mode="allowlist", allowlist=["prt_upper", "prt_m*"])
        assert _names(get_environment(cfg)) == ["PRT_UPPER", "Prt_Mixed"]

    def test_allowlist_tuple_and_set_accepted(self, isolated_home, monkeypatch):
        monkeypatch.setenv("PRT_ONE", "1")
        for seq in (("PRT_ONE",), {"PRT_ONE"}):
            cfg = _env_config(mode="allowlist", allowlist=seq)
            assert _names(get_environment(cfg)) == ["PRT_ONE"]

    def test_allowlist_matched_secrets_still_redacted(self, isolated_home, monkeypatch):
        monkeypatch.setenv("SLURM_API_TOKEN", "supersecretvalue")
        monkeypatch.setenv("SLURM_JOB_ID", "42")
        cfg = _env_config(mode="allowlist", allowlist=["SLURM_*"])
        result = get_environment(cfg)
        values = {v["name"]: v["value"] for v in result["variables"]}
        assert set(values) >= {"SLURM_API_TOKEN", "SLURM_JOB_ID"}
        assert values["SLURM_API_TOKEN"]["representation"] == "redacted"
        assert "supersecretvalue" not in repr(values["SLURM_API_TOKEN"])
        assert values["SLURM_JOB_ID"] == {"representation": "plain", "value": "42"}

    def test_filtered_mode_ignores_allowlist(self, isolated_home, monkeypatch):
        monkeypatch.setenv("PUBRUN_TEST_FILTERED", "v")
        cfg = _env_config(mode="filtered", allowlist=["NOTHING_MATCHES"])
        assert "PUBRUN_TEST_FILTERED" in _names(get_environment(cfg))


# ---------------------------------------------------------------------------
# BUG-39: depth = "off" for git, host, process, and python collectors
# ---------------------------------------------------------------------------


def _section_off(section):
    cfg = resolve_config()
    cfg["capture"][section]["depth"] = "off"
    return cfg


class TestCollectorDepthOff:
    def test_git_depth_off_runs_no_subprocess(self, isolated_home, monkeypatch):
        calls = []

        def _fake_run(*args, **kwargs):
            calls.append(args)
            raise AssertionError("git must not be invoked")

        monkeypatch.setattr(subprocess, "run", _fake_run)
        result = get_git(_section_off("git"))
        assert result["capture_state"]["status"] == "suppressed"
        assert calls == []

    def test_host_depth_off(self, isolated_home, monkeypatch):
        import platform

        def _boom(*a, **k):
            raise AssertionError("host metadata must not be collected")

        monkeypatch.setattr(platform, "node", _boom)
        result = get_host(_section_off("host"))
        assert result["capture_state"]["status"] == "suppressed"
        assert set(result) == {"capture_state"}

    def test_process_depth_off(self, isolated_home, monkeypatch):
        import getpass

        def _boom(*a, **k):
            raise AssertionError("process metadata must not be collected")

        monkeypatch.setattr(getpass, "getuser", _boom)
        result = get_process_info(_section_off("process"))
        assert result == {"capture_state": {"status": "suppressed"}}

    def test_python_depth_off(self, isolated_home):
        result = get_python_runtime(_section_off("python"))
        assert result == {"capture_state": {"status": "suppressed"}}

    @pytest.mark.parametrize(
        "fn,section",
        [
            (get_host, "host"),
            (get_process_info, "process"),
            (get_python_runtime, "python"),
            (get_environment, "environment"),
        ],
    )
    def test_default_depth_still_collects(self, isolated_home, fn, section):
        result = fn(resolve_config())
        assert result["capture_state"]["status"] == "complete"
        assert len(result) > 1

    def test_suppressed_payloads_validate_against_schema(self, isolated_home, monkeypatch):
        jsonschema = pytest.importorskip("jsonschema")
        import json

        schema_path = Path(__file__).resolve().parents[1] / "schemas" / "manifest.schema.json"
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        defs = schema["$defs"]
        monkeypatch.setattr(subprocess, "run", lambda *a, **k: None)
        cases = [
            ("git_section", get_git(_section_off("git"))),
            ("host", get_host(_section_off("host"))),
            ("process", get_process_info(_section_off("process"))),
            ("python_runtime", get_python_runtime(_section_off("python"))),
            ("environment_section", get_environment(_section_off("environment"))),
        ]
        for def_name, payload in cases:
            sub = dict(defs[def_name])
            sub["$defs"] = defs
            jsonschema.validate(payload, sub)
