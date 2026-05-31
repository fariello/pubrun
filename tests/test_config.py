"""Tests for configuration resolution, file loading, and merge precedence."""
import pytest
from pathlib import Path

from pubrun.config import _deep_merge, load_default_config, resolve_config, load_local_config


class TestDeepMerge:

    def test_basic_merge(self):
        a = {"core": {"profile": "default", "auto_start": False}, "events": {"enabled": False}}
        b = {"core": {"auto_start": True}, "console": {"capture_mode": "off"}}
        result = _deep_merge(a, b)
        assert result["core"]["profile"] == "default"
        assert result["core"]["auto_start"] is True
        assert result["events"]["enabled"] is False
        assert result["console"]["capture_mode"] == "off"

    def test_does_not_mutate_originals(self):
        a = {"core": {"profile": "default", "nested": {"x": 1}}}
        b = {"core": {"nested": {"y": 2}}}
        result = _deep_merge(a, b)
        # Original a should be untouched
        assert "y" not in a["core"]["nested"]
        # Result should have both
        assert result["core"]["nested"]["x"] == 1
        assert result["core"]["nested"]["y"] == 2

    def test_non_dict_overwrite(self):
        a = {"core": {"profile": "default"}}
        b = {"core": {"profile": "deep"}}
        result = _deep_merge(a, b)
        assert result["core"]["profile"] == "deep"

    def test_list_overwrite_not_append(self):
        a = {"items": [1, 2, 3]}
        b = {"items": [4, 5]}
        result = _deep_merge(a, b)
        assert result["items"] == [4, 5]

    def test_empty_dicts(self):
        assert _deep_merge({}, {}) == {}
        assert _deep_merge({"a": 1}, {}) == {"a": 1}
        assert _deep_merge({}, {"b": 2}) == {"b": 2}

    def test_deeply_nested(self):
        a = {"a": {"b": {"c": {"d": 1}}}}
        b = {"a": {"b": {"c": {"e": 2}}}}
        result = _deep_merge(a, b)
        assert result["a"]["b"]["c"]["d"] == 1
        assert result["a"]["b"]["c"]["e"] == 2


class TestLoadDefaultConfig:

    def test_returns_dict(self):
        conf = load_default_config()
        assert isinstance(conf, dict)

    def test_has_core_section(self):
        conf = load_default_config()
        assert "core" in conf
        assert conf["core"]["profile"] == "default"

    def test_has_capture_section(self):
        conf = load_default_config()
        assert "capture" in conf

    def test_has_redaction_section(self):
        conf = load_default_config()
        assert "redaction" in conf

    def test_has_events_section(self):
        conf = load_default_config()
        assert "events" in conf

    def test_has_console_section(self):
        conf = load_default_config()
        assert "console" in conf


class TestLoadLocalConfig:

    def test_no_local_config_returns_none(self, tmp_path):
        result = load_local_config(start_dir=tmp_path)
        assert result is None

    def test_pubrun_toml_discovered(self, tmp_path):
        config_file = tmp_path / ".pubrun.toml"
        config_file.write_text('[core]\nprofile = "deep"\n', encoding="utf-8")
        result = load_local_config(start_dir=tmp_path)
        assert result is not None
        assert result["core"]["profile"] == "deep"

    def test_deep_config_discovered(self, tmp_path):
        config_dir = tmp_path / ".config" / "pubrun"
        config_dir.mkdir(parents=True)
        config_file = config_dir / "config.toml"
        config_file.write_text('[events]\nenabled = true\n', encoding="utf-8")
        result = load_local_config(start_dir=tmp_path)
        assert result is not None
        assert result["events"]["enabled"] is True

    def test_pubrun_toml_overrides_deep_config(self, tmp_path):
        """When both exist, .pubrun.toml takes precedence (applied last)."""
        deep_dir = tmp_path / ".config" / "pubrun"
        deep_dir.mkdir(parents=True)
        (deep_dir / "config.toml").write_text('[core]\nprofile = "deep"\n', encoding="utf-8")
        (tmp_path / ".pubrun.toml").write_text('[core]\nprofile = "minimal"\n', encoding="utf-8")
        result = load_local_config(start_dir=tmp_path)
        assert result["core"]["profile"] == "minimal"

    def test_non_overlapping_keys_merge_from_both_files(self, tmp_path):
        """Non-overlapping sections from both files are merged together."""
        deep_dir = tmp_path / ".config" / "pubrun"
        deep_dir.mkdir(parents=True)
        # Deep config has [capture.resources]
        (deep_dir / "config.toml").write_text(
            '[capture.resources]\ndepth = "deep"\n',
            encoding="utf-8"
        )
        # .pubrun.toml has [events]
        (tmp_path / ".pubrun.toml").write_text(
            '[events]\nenabled = false\n',
            encoding="utf-8"
        )
        result = load_local_config(start_dir=tmp_path)
        # Both sections should be present
        assert result["capture"]["resources"]["depth"] == "deep"
        assert result["events"]["enabled"] is False


class TestResolveConfig:

    def test_defaults_present(self, monkeypatch):
        monkeypatch.setattr("pubrun.config.load_user_config", lambda: None)
        monkeypatch.setattr("pubrun.config.load_local_config", lambda start_dir=None: None)
        resolved = resolve_config()
        assert "core" in resolved
        assert "capture" in resolved

    def test_api_overrides_take_highest_precedence(self, monkeypatch):
        monkeypatch.setattr("pubrun.config.load_user_config", lambda: None)
        monkeypatch.setattr("pubrun.config.load_local_config", lambda start_dir=None: None)
        resolved = resolve_config({"core": {"profile": "deep"}})
        assert resolved["core"]["profile"] == "deep"

    def test_local_overrides_user(self, monkeypatch):
        monkeypatch.setattr("pubrun.config.load_user_config", lambda: {"core": {"profile": "user-pref"}})
        monkeypatch.setattr("pubrun.config.load_local_config", lambda start_dir=None: {"core": {"profile": "local-pref"}})
        resolved = resolve_config()
        assert resolved["core"]["profile"] == "local-pref"

    def test_user_overrides_defaults(self, monkeypatch):
        monkeypatch.setattr("pubrun.config.load_user_config", lambda: {"core": {"profile": "user-pref"}})
        monkeypatch.setattr("pubrun.config.load_local_config", lambda start_dir=None: None)
        resolved = resolve_config()
        assert resolved["core"]["profile"] == "user-pref"

    def test_preserves_unrelated_defaults(self, monkeypatch):
        monkeypatch.setattr("pubrun.config.load_user_config", lambda: None)
        monkeypatch.setattr("pubrun.config.load_local_config", lambda start_dir=None: None)
        resolved = resolve_config({"core": {"profile": "deep"}})
        # Console defaults should be preserved
        assert "capture_mode" in resolved.get("console", {})


class TestMetaRefEnvVar:

    def test_pubrun_meta_ref_sets_core_meta_ref(self, monkeypatch):
        monkeypatch.setenv("PUBRUN_META_REF", "parent_meta.json")
        monkeypatch.setattr("pubrun.config.load_user_config", lambda: None)
        monkeypatch.setattr("pubrun.config.load_local_config", lambda start_dir=None: None)
        resolved = resolve_config()
        assert resolved["core"]["meta_ref"] == "parent_meta.json"

    def test_pubrun_meta_ref_absent_means_none(self, monkeypatch):
        monkeypatch.delenv("PUBRUN_META_REF", raising=False)
        monkeypatch.setattr("pubrun.config.load_user_config", lambda: None)
        monkeypatch.setattr("pubrun.config.load_local_config", lambda start_dir=None: None)
        resolved = resolve_config()
        assert resolved["core"].get("meta_ref") is None

    def test_api_override_trumps_env_var(self, monkeypatch):
        monkeypatch.setenv("PUBRUN_META_REF", "env_meta.json")
        monkeypatch.setattr("pubrun.config.load_user_config", lambda: None)
        monkeypatch.setattr("pubrun.config.load_local_config", lambda start_dir=None: None)
        resolved = resolve_config({"core": {"meta_ref": "api_meta.json"}})
        assert resolved["core"]["meta_ref"] == "api_meta.json"

    def test_env_var_trumps_config_file(self, monkeypatch):
        monkeypatch.setenv("PUBRUN_META_REF", "env_meta.json")
        monkeypatch.setattr("pubrun.config.load_user_config", lambda: None)
        monkeypatch.setattr("pubrun.config.load_local_config", lambda start_dir=None: {"core": {"meta_ref": "local_meta.json"}})
        resolved = resolve_config()
        assert resolved["core"]["meta_ref"] == "env_meta.json"


class TestProfileEnvVar:

    def test_pubrun_profile_sets_core_profile(self, monkeypatch):
        monkeypatch.setenv("PUBRUN_PROFILE", "deep")
        monkeypatch.setattr("pubrun.config.load_user_config", lambda: None)
        monkeypatch.setattr("pubrun.config.load_local_config", lambda start_dir=None: None)
        resolved = resolve_config()
        assert resolved["core"]["profile"] == "deep"

    def test_pubrun_profile_absent_uses_default(self, monkeypatch):
        monkeypatch.delenv("PUBRUN_PROFILE", raising=False)
        monkeypatch.setattr("pubrun.config.load_user_config", lambda: None)
        monkeypatch.setattr("pubrun.config.load_local_config", lambda start_dir=None: None)
        resolved = resolve_config()
        assert resolved["core"]["profile"] == "default"

    def test_api_override_trumps_profile_env_var(self, monkeypatch):
        monkeypatch.setenv("PUBRUN_PROFILE", "minimal")
        monkeypatch.setattr("pubrun.config.load_user_config", lambda: None)
        monkeypatch.setattr("pubrun.config.load_local_config", lambda start_dir=None: None)
        resolved = resolve_config({"core": {"profile": "deep"}})
        assert resolved["core"]["profile"] == "deep"

    def test_profile_env_var_trumps_config_file(self, monkeypatch):
        monkeypatch.setenv("PUBRUN_PROFILE", "minimal")
        monkeypatch.setattr("pubrun.config.load_user_config", lambda: None)
        monkeypatch.setattr("pubrun.config.load_local_config", lambda start_dir=None: {"core": {"profile": "deep"}})
        resolved = resolve_config()
        assert resolved["core"]["profile"] == "minimal"
