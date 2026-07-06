"""Tests for the `full` import mode (IPD 20260705-full-capture-mode).

`full` = auto-start + all hooks + console tee FORCED on, regardless of config,
while still respecting the Jupyter/non-TTY safety guards. Import mode is an
absolute imperative: it overrides env/config; only `pubrun run --mode` overrides
the in-code import.

Step 1 (characterization gate) pins the pre-change console-mode behavior so the
`resolve_console_mode(force_base=...)` seam change cannot regress the other five
modes. Those tests must be green BEFORE and AFTER Step 2.
"""
import json
import os
import subprocess
import sys

import pytest


PYTHON = sys.executable


# ---------------------------------------------------------------------------
# Step 1: characterization gate (pin CURRENT behavior; must stay green after)
# ---------------------------------------------------------------------------

class TestConsoleModeCharacterization:
    """Pin the current resolve_console_mode behavior before the force_base change."""

    def _resolve(self, monkeypatch, config, jupyter=False, tty=True):
        from unittest.mock import MagicMock
        from pubrun.capture import console as _console
        monkeypatch.setattr(_console, "_is_jupyter_kernel", lambda: jupyter)
        monkeypatch.setattr("sys.stdout", MagicMock(isatty=lambda: tty))
        return _console.resolve_console_mode(config)

    def test_default_off_is_off(self, monkeypatch):
        assert self._resolve(monkeypatch, {"console": {"capture_mode": "off"}}) == "off"

    def test_empty_config_is_off(self, monkeypatch):
        # No console section at all -> default "off".
        assert self._resolve(monkeypatch, {}) == "off"

    def test_explicit_standard_is_standard(self, monkeypatch):
        cfg = {"console": {"capture_mode": "standard", "jupyter_mode": "off",
                           "non_tty_mode": "inherit"}}
        assert self._resolve(monkeypatch, cfg) == "standard"

    def test_standard_in_jupyter_downgrades(self, monkeypatch):
        cfg = {"console": {"capture_mode": "standard", "jupyter_mode": "off",
                           "non_tty_mode": "inherit"}}
        assert self._resolve(monkeypatch, cfg, jupyter=True) == "off"

    def test_standard_non_tty_inherit_stays_standard(self, monkeypatch):
        cfg = {"console": {"capture_mode": "standard", "jupyter_mode": "off",
                           "non_tty_mode": "inherit"}}
        assert self._resolve(monkeypatch, cfg, tty=False) == "standard"

    def test_standard_non_tty_off_downgrades(self, monkeypatch):
        cfg = {"console": {"capture_mode": "standard", "jupyter_mode": "off",
                           "non_tty_mode": "off"}}
        assert self._resolve(monkeypatch, cfg, tty=False) == "off"


class TestExistingModesConsoleOff:
    """Regression: none of the five existing modes wrap console with no user
    config (subprocess-isolated because import mode is process-global)."""

    @pytest.mark.parametrize("mode", ["auto", "noauto", "nopatch", "noconsole", "minimal"])
    def test_mode_default_console_off(self, mode, tmp_path):
        # Start the mode, then inspect the manifest's recorded console_capture_mode.
        module = "pubrun" if mode == "auto" else f"pubrun.{mode}"
        script = f"""
import glob, json
import {module} as pubrun
r = pubrun.get_current_run()
if r is None:
    pubrun.start()          # noauto/minimal need an explicit start
    r = pubrun.get_current_run()
rd = str(r.run_dir)
pubrun.stop()
m = json.load(open(rd + "/manifest.json"))
# console.capture_mode here is the EFFECTIVE mode the interceptor ran with.
cc = m.get("console", {{}}).get("capture_mode")
print("CONSOLE_MODE=" + str(cc))
"""
        result = subprocess.run(
            [PYTHON, "-c", script], capture_output=True, text=True, timeout=30,
            cwd=str(tmp_path),
            env={**os.environ, "PUBRUN_IMPORT_MODE": "", "PUBRUN_AUTO_START": ""},
        )
        assert result.returncode == 0, f"stderr: {result.stderr}"
        # No existing mode wraps the console with default config.
        assert "CONSOLE_MODE=off" in result.stdout, f"stdout: {result.stdout}"
