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
        # Start the mode, then inspect the FINAL manifest (read AFTER pubrun.stop(),
        # which finalizes synchronously). The console section is never an ambiguous
        # empty {} now: it is written with capture_mode + capture_state at startup and
        # overwritten with the final result + status "complete" on stop() (IPD
        # 20260721-1425-01). So capture_mode is deterministically present here.
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
console = m.get("console", {{}})
cc = console.get("capture_mode")
status = console.get("capture_state", {{}}).get("status")
print("CONSOLE_MODE=" + str(cc))
print("CONSOLE_STATUS=" + str(status))
"""
        result = subprocess.run(
            [PYTHON, "-c", script], capture_output=True, text=True, timeout=30,
            cwd=str(tmp_path),
            env={**os.environ, "PUBRUN_IMPORT_MODE": "", "PUBRUN_AUTO_START": ""},
        )
        assert result.returncode == 0, f"stderr: {result.stderr}"
        # No existing mode wraps the console with default config; and after stop() the
        # section is finalized. Both are deterministic now (no CI-load tolerance needed).
        assert "CONSOLE_MODE=off" in result.stdout, f"stdout: {result.stdout}"
        assert "CONSOLE_STATUS=complete" in result.stdout, f"stdout: {result.stdout}"

    def test_startup_console_section_is_pending_then_complete(self, tmp_path):
        """Regression (IPD 20260721-1425-01): the STARTUP manifest's console section
        must be self-describing (capture_mode + capture_state.status == "pending"),
        never an empty {}; the FINAL manifest must show status "complete". Guards
        against a revert to the empty-console startup manifest that caused an
        intermittent CONSOLE_MODE=None read."""
        script = """
import json
import pubrun.nopatch as pubrun
r = pubrun.get_current_run()
if r is None:
    pubrun.start()
    r = pubrun.get_current_run()
rd = str(r.run_dir)
# Read the STARTUP manifest (before stop() finalizes).
m0 = json.load(open(rd + "/manifest.json"))
c0 = m0.get("console", {})
print("STARTUP_MODE=" + str(c0.get("capture_mode")))
print("STARTUP_STATUS=" + str(c0.get("capture_state", {}).get("status")))
pubrun.stop()
m1 = json.load(open(rd + "/manifest.json"))
c1 = m1.get("console", {})
print("FINAL_MODE=" + str(c1.get("capture_mode")))
print("FINAL_STATUS=" + str(c1.get("capture_state", {}).get("status")))
"""
        result = subprocess.run(
            [PYTHON, "-c", script], capture_output=True, text=True, timeout=30,
            cwd=str(tmp_path),
            env={**os.environ, "PUBRUN_IMPORT_MODE": "", "PUBRUN_AUTO_START": ""},
        )
        assert result.returncode == 0, f"stderr: {result.stderr}"
        # Startup: self-describing, not empty.
        assert "STARTUP_MODE=off" in result.stdout, f"stdout: {result.stdout}"
        assert "STARTUP_STATUS=pending" in result.stdout, f"stdout: {result.stdout}"
        # Final: finalized.
        assert "FINAL_MODE=off" in result.stdout, f"stdout: {result.stdout}"
        assert "FINAL_STATUS=complete" in result.stdout, f"stdout: {result.stdout}"


# ---------------------------------------------------------------------------
# The `full` mode itself (Steps 2-4)
# ---------------------------------------------------------------------------

class TestFullModeBehavior:
    """`full` = auto + force console on (respecting Jupyter/non-TTY guards)."""

    def test_mode_defined_with_force_console(self):
        from pubrun._modes import MODES, VALID_MODES, get_mode_behavior
        assert "full" in VALID_MODES
        b = get_mode_behavior("full")
        assert b["auto_start"] is True
        assert b["patch_subprocesses"] is True
        assert b["patch_console"] is True
        assert b["signal_hooks"] is True
        assert b["force_console"] is True

    def test_force_base_forces_standard_over_config_off(self, monkeypatch):
        """force_base overrides an explicit capture_mode='off' (import wins)."""
        from unittest.mock import MagicMock
        from pubrun.capture import console as _console
        monkeypatch.setattr(_console, "_is_jupyter_kernel", lambda: False)
        monkeypatch.setattr("sys.stdout", MagicMock(isatty=lambda: True))
        cfg = {"console": {"capture_mode": "off", "jupyter_mode": "off",
                           "non_tty_mode": "inherit"}}
        assert _console.resolve_console_mode(cfg, force_base="standard") == "standard"

    def test_force_base_still_respects_jupyter_guard(self, monkeypatch):
        from unittest.mock import MagicMock
        from pubrun.capture import console as _console
        monkeypatch.setattr(_console, "_is_jupyter_kernel", lambda: True)
        monkeypatch.setattr("sys.stdout", MagicMock(isatty=lambda: True))
        cfg = {"console": {"capture_mode": "off", "jupyter_mode": "off",
                           "non_tty_mode": "inherit"}}
        assert _console.resolve_console_mode(cfg, force_base="standard") == "off"

    def test_force_base_non_tty_off_downgrades(self, monkeypatch):
        from unittest.mock import MagicMock
        from pubrun.capture import console as _console
        monkeypatch.setattr(_console, "_is_jupyter_kernel", lambda: False)
        monkeypatch.setattr("sys.stdout", MagicMock(isatty=lambda: False))
        cfg = {"console": {"capture_mode": "off", "jupyter_mode": "off",
                           "non_tty_mode": "off"}}
        assert _console.resolve_console_mode(cfg, force_base="standard") == "off"

    def test_full_alias_exposes_full_api(self):
        names = json.dumps([
            "start", "stop", "annotate", "phase", "diff", "audit_run",
            "tracked_run", "get_current_run", "report", "artifact",
            "print", "open", "subprocess", "popen",
        ])
        script = f"""
import json
import pubrun.full as pubrun
names = {names}
missing = [n for n in names if not hasattr(pubrun, n)]
print(json.dumps({{"missing": missing}}))
try:
    if pubrun.get_current_run():
        pubrun.stop()
except Exception:
    pass
"""
        result = subprocess.run(
            [PYTHON, "-c", script], capture_output=True, text=True, timeout=20,
            env={**os.environ, "PUBRUN_IMPORT_MODE": "", "PUBRUN_AUTO_START": ""},
        )
        assert result.returncode == 0, f"stderr: {result.stderr}"
        data = json.loads(result.stdout.strip().splitlines()[-1])
        assert data["missing"] == [], f"full alias missing: {data['missing']}"

    def test_full_wraps_console_end_to_end(self, tmp_path):
        """import pubrun.full → console tee active, output recorded to stdout.log,
        overriding the default capture_mode='off'."""
        script = """
import glob, json
import pubrun.full as pubrun
print("SENTINEL_FULL_LINE")
r = pubrun.get_current_run()
rd = str(r.run_dir)
pubrun.stop()
m = json.load(open(rd + "/manifest.json"))
logs = glob.glob(rd + "/stdout.log")
captured = bool(logs) and "SENTINEL_FULL_LINE" in open(logs[0]).read()
# Read AFTER stop(): the console section is finalized and never ambiguously empty
# (IPD 20260721-1425-01), so the effective mode is deterministic here.
print("EFFECTIVE=" + str(m.get("console", {}).get("capture_mode")))
print("CAPTURED=" + str(captured))
"""
        result = subprocess.run(
            [PYTHON, "-c", script], capture_output=True, text=True, timeout=30,
            cwd=str(tmp_path),
            env={**os.environ, "PUBRUN_IMPORT_MODE": "", "PUBRUN_AUTO_START": ""},
        )
        assert result.returncode == 0, f"stderr: {result.stderr}"
        # The load-bearing invariant: `full` mode actually teed console output to stdout.log.
        assert "CAPTURED=True" in result.stdout, f"stdout: {result.stdout}"
        # The recorded effective mode is standard (deterministic post-fix; the earlier
        # EFFECTIVE=None tolerance is no longer needed now the section is never empty).
        assert "EFFECTIVE=standard" in result.stdout, f"stdout: {result.stdout}"

    def test_env_selects_full(self):
        script = """
from pubrun._bootstrap import get_selected_mode
import pubrun
print("SELECTED=" + str(get_selected_mode()))
if pubrun.get_current_run():
    pubrun.stop()
"""
        result = subprocess.run(
            [PYTHON, "-c", script], capture_output=True, text=True, timeout=20,
            env={**os.environ, "PUBRUN_IMPORT_MODE": "full", "PUBRUN_AUTO_START": ""},
        )
        assert result.returncode == 0, f"stderr: {result.stderr}"
        assert "SELECTED=full" in result.stdout, f"stdout: {result.stdout}"

    def test_run_mode_full_wraps_child_console(self, tmp_path):
        workload = tmp_path / "w.py"
        workload.write_text(
            "import glob, json, pubrun\n"
            "print('SENTINEL_RUNMODE')\n"
            "r = pubrun.get_current_run(); rd = str(r.run_dir); pubrun.stop()\n"
            "m = json.load(open(rd + '/manifest.json'))\n"
            "print('EFFECTIVE=' + str(m['console']['capture_mode']))\n",
            encoding="utf-8",
        )
        result = subprocess.run(
            [PYTHON, "-m", "pubrun", "run", "--mode", "full", "--", PYTHON, str(workload)],
            capture_output=True, text=True, timeout=40, cwd=str(tmp_path),
            env={**os.environ, "PUBRUN_IMPORT_MODE": "", "PUBRUN_AUTO_START": ""},
        )
        assert result.returncode == 0, f"stderr: {result.stderr}"
        assert "EFFECTIVE=standard" in result.stdout, f"stdout: {result.stdout}"
