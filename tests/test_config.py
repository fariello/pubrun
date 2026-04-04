import pytest
from pubrun.config import _deep_merge, load_default_config, resolve_config

def test_deep_merge():
    a = {"core": {"profile": "default", "auto_start": False}, "events": {"enabled": False}}
    b = {"core": {"auto_start": True}, "console": {"capture_mode": "off"}}
    result = _deep_merge(a, b)
    assert result["core"]["profile"] == "default"
    assert result["core"]["auto_start"] is True
    assert result["events"]["enabled"] is False
    assert result["console"]["capture_mode"] == "off"

def test_load_default_config():
    conf = load_default_config()
    assert "core" in conf
    assert conf["core"]["profile"] == "default"

def test_resolve_config_with_overrides(monkeypatch):
    # Ensure local config and user config don't interfere
    monkeypatch.setattr("pubrun.config.load_user_config", lambda: None)
    monkeypatch.setattr("pubrun.config.load_local_config", lambda start_dir=None: None)
    
    overrides = {"core": {"profile": "deep"}}
    resolved = resolve_config(overrides)
    assert resolved["core"]["profile"] == "deep"
    assert resolved["console"]["capture_mode"] == "standard"  # preserved defaults
