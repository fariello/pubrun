"""Tests for Phase 1: Import mode resolution and centralized config boot."""
import os
import json
import subprocess
import sys
import pytest

from pubrun._modes import MODES, VALID_MODES, get_mode_behavior, resolve_mode_name
from pubrun._config_boot import resolve_import_mode


PYTHON = sys.executable


class TestModeDefinitions:
    """Unit tests for _modes.py."""

    def test_four_modes_defined(self):
        assert len(MODES) == 4
        assert VALID_MODES == {"auto", "noauto", "nopatch", "quiet"}

    def test_auto_mode_behavior(self):
        b = get_mode_behavior("auto")
        assert b == {"auto_start": True, "global_hooks": True}

    def test_noauto_mode_behavior(self):
        b = get_mode_behavior("noauto")
        assert b == {"auto_start": False, "global_hooks": True}

    def test_nopatch_mode_behavior(self):
        b = get_mode_behavior("nopatch")
        assert b == {"auto_start": True, "global_hooks": False}

    def test_quiet_mode_behavior(self):
        b = get_mode_behavior("quiet")
        assert b == {"auto_start": False, "global_hooks": False}

    def test_unknown_mode_falls_back_to_auto(self):
        b = get_mode_behavior("invalid")
        assert b == {"auto_start": True, "global_hooks": True}

    def test_get_mode_behavior_returns_copy(self):
        b1 = get_mode_behavior("auto")
        b1["auto_start"] = False
        b2 = get_mode_behavior("auto")
        assert b2["auto_start"] is True

    def test_resolve_mode_name(self):
        assert resolve_mode_name(True, True) == "auto"
        assert resolve_mode_name(False, True) == "noauto"
        assert resolve_mode_name(True, False) == "nopatch"
        assert resolve_mode_name(False, False) == "quiet"


class TestConfigBootResolver:
    """Unit tests for _config_boot.py resolve_import_mode()."""

    def test_default_is_auto(self, monkeypatch):
        monkeypatch.delenv("PUBRUN_IMPORT_MODE", raising=False)
        monkeypatch.delenv("PUBRUN_AUTO_START", raising=False)
        mode, source = resolve_import_mode()
        assert mode == "auto"
        assert source == "default"

    def test_pubrun_import_mode_env_quiet(self, monkeypatch):
        monkeypatch.setenv("PUBRUN_IMPORT_MODE", "quiet")
        monkeypatch.delenv("PUBRUN_AUTO_START", raising=False)
        mode, source = resolve_import_mode()
        assert mode == "quiet"
        assert source == "env:PUBRUN_IMPORT_MODE"

    def test_pubrun_import_mode_env_nopatch(self, monkeypatch):
        monkeypatch.setenv("PUBRUN_IMPORT_MODE", "nopatch")
        mode, source = resolve_import_mode()
        assert mode == "nopatch"
        assert source == "env:PUBRUN_IMPORT_MODE"

    def test_pubrun_import_mode_case_insensitive(self, monkeypatch):
        monkeypatch.setenv("PUBRUN_IMPORT_MODE", "NOAUTO")
        mode, source = resolve_import_mode()
        assert mode == "noauto"

    def test_pubrun_import_mode_invalid_falls_through(self, monkeypatch):
        monkeypatch.setenv("PUBRUN_IMPORT_MODE", "bogus")
        monkeypatch.delenv("PUBRUN_AUTO_START", raising=False)
        mode, source = resolve_import_mode()
        # Invalid PUBRUN_IMPORT_MODE is ignored; falls to default
        assert mode == "auto"
        assert source == "default"

    def test_legacy_auto_start_false(self, monkeypatch):
        monkeypatch.delenv("PUBRUN_IMPORT_MODE", raising=False)
        monkeypatch.setenv("PUBRUN_AUTO_START", "false")
        mode, source = resolve_import_mode()
        assert mode == "noauto"
        assert source == "env:PUBRUN_AUTO_START"

    def test_legacy_auto_start_true(self, monkeypatch):
        monkeypatch.delenv("PUBRUN_IMPORT_MODE", raising=False)
        monkeypatch.setenv("PUBRUN_AUTO_START", "true")
        mode, source = resolve_import_mode()
        assert mode == "auto"
        assert source == "env:PUBRUN_AUTO_START"

    def test_import_mode_takes_precedence_over_auto_start(self, monkeypatch):
        monkeypatch.setenv("PUBRUN_IMPORT_MODE", "quiet")
        monkeypatch.setenv("PUBRUN_AUTO_START", "true")
        mode, source = resolve_import_mode()
        assert mode == "quiet"
        assert source == "env:PUBRUN_IMPORT_MODE"

    def test_config_file_imports_mode(self, tmp_path, monkeypatch):
        """[imports].mode in .pubrun.toml is respected."""
        toml_file = tmp_path / ".pubrun.toml"
        toml_file.write_text('[imports]\nmode = "nopatch"\n', encoding="utf-8")
        monkeypatch.chdir(tmp_path)
        monkeypatch.delenv("PUBRUN_IMPORT_MODE", raising=False)
        monkeypatch.delenv("PUBRUN_AUTO_START", raising=False)
        mode, source = resolve_import_mode()
        assert mode == "nopatch"
        assert source == "config:[imports].mode"

    def test_config_file_core_auto_start_false(self, tmp_path, monkeypatch):
        """[core].auto_start = false in .pubrun.toml maps to noauto."""
        toml_file = tmp_path / ".pubrun.toml"
        toml_file.write_text('[core]\nauto_start = false\n', encoding="utf-8")
        monkeypatch.chdir(tmp_path)
        monkeypatch.delenv("PUBRUN_IMPORT_MODE", raising=False)
        monkeypatch.delenv("PUBRUN_AUTO_START", raising=False)
        mode, source = resolve_import_mode()
        assert mode == "noauto"
        assert source == "config:[core].auto_start"

    def test_env_overrides_config_file(self, tmp_path, monkeypatch):
        """Environment variable takes precedence over config file."""
        toml_file = tmp_path / ".pubrun.toml"
        toml_file.write_text('[imports]\nmode = "quiet"\n', encoding="utf-8")
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("PUBRUN_IMPORT_MODE", "auto")
        mode, source = resolve_import_mode()
        assert mode == "auto"
        assert source == "env:PUBRUN_IMPORT_MODE"


class TestBootSequenceIntegration:
    """Subprocess tests verifying the boot sequence uses the centralized resolver."""

    def test_default_auto_starts(self, tmp_path):
        """Default behavior: import pubrun auto-starts."""
        script = f"""
import os, sys, json
os.chdir({str(tmp_path)!r})
os.environ.pop('PUBRUN_IMPORT_MODE', None)
os.environ['PUBRUN_AUTO_START'] = 'true'
for mod in list(sys.modules.keys()):
    if 'pubrun' in mod:
        del sys.modules[mod]
import pubrun
run = pubrun.get_current_run()
print(json.dumps({{"active": run is not None}}))
if run:
    pubrun.stop()
"""
        result = subprocess.run(
            [PYTHON, "-c", script],
            capture_output=True, text=True, timeout=15,
            env={**os.environ, "PUBRUN_AUTO_START": "true"}
        )
        assert result.returncode == 0, f"stderr: {result.stderr}"
        data = json.loads(result.stdout.strip())
        assert data["active"] is True

    def test_import_mode_quiet_prevents_start(self, tmp_path):
        """PUBRUN_IMPORT_MODE=quiet prevents auto-start."""
        script = f"""
import os, sys, json
os.chdir({str(tmp_path)!r})
import pubrun
run = pubrun.get_current_run()
print(json.dumps({{"active": run is not None}}))
"""
        result = subprocess.run(
            [PYTHON, "-c", script],
            capture_output=True, text=True, timeout=15,
            env={**os.environ, "PUBRUN_IMPORT_MODE": "quiet"}
        )
        assert result.returncode == 0, f"stderr: {result.stderr}"
        data = json.loads(result.stdout.strip())
        assert data["active"] is False

    def test_legacy_auto_start_false_still_works(self, tmp_path):
        """PUBRUN_AUTO_START=false still prevents auto-start."""
        script = f"""
import os, sys, json
os.chdir({str(tmp_path)!r})
import pubrun
run = pubrun.get_current_run()
print(json.dumps({{"active": run is not None}}))
"""
        result = subprocess.run(
            [PYTHON, "-c", script],
            capture_output=True, text=True, timeout=15,
            env={**os.environ, "PUBRUN_AUTO_START": "false", "PUBRUN_IMPORT_MODE": ""}
        )
        assert result.returncode == 0, f"stderr: {result.stderr}"
        data = json.loads(result.stdout.strip())
        assert data["active"] is False
