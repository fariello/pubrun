"""Regression tests for the `pubrun.report` callable-subpackage collision, and a
generalized guard against a whole CLASS of bugs: an import-mode module shadowing a
pubrun *subpackage* by binding a same-named attribute on the top-level package.

The specific bug: every mode module (auto/noauto/full/nopatch/noconsole/minimal) and
the deferred `__init__` used to do `pubrun.report = report`, overwriting the
`pubrun.report` CallableModule subpackage with the plain report() function. After that,
`import pubrun.report.diagnostics` (and .output/.checks) raised ImportError, because the
`pubrun.report` attribute was a function, not the subpackage. `pubrun.report` is designed
to be BOTH: callable as the report() API *and* a subpackage exposing submodules.

Each test runs in a fresh subprocess so import-mode selection (which is process-global
and first-wins) is isolated per mode.
"""
import subprocess
import sys

import pytest

# The public capture-related submodules that must remain importable regardless of mode.
_REPORT_SUBMODULES = ["output", "checks", "diagnostics", "methods", "utils"]

_MODES = ["auto", "noauto", "full", "nopatch", "noconsole", "minimal"]


def _run(code: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True, text=True, timeout=60,
    )


@pytest.mark.parametrize("mode", _MODES)
def test_report_is_callable_and_subpackage_under_every_mode(mode):
    """After `import pubrun.<mode>`, `pubrun.report` must be callable AND every
    report submodule must still import."""
    submods = ", ".join(f"'{s}'" for s in _REPORT_SUBMODULES)
    code = f"""
import importlib, sys
import pubrun.{mode} as pubrun
import pubrun as base

# 1. Callable report() API still works.
assert callable(base.report), "pubrun.report is not callable under mode {mode}"

# 2. The subpackage and its submodules still import (the shadowing regression).
for name in [{submods}]:
    importlib.import_module("pubrun.report." + name)

# 3. A live run does not corrupt subpackage access afterwards.
if hasattr(pubrun, "start"):
    try:
        import os, tempfile
        os.chdir(tempfile.mkdtemp())
        t = pubrun.start()
        pubrun.stop()
    except Exception:
        pass  # some modes don't auto-provide start(); the import checks are the point
importlib.import_module("pubrun.report.diagnostics")
print("OK")
"""
    r = _run(code)
    assert r.returncode == 0, f"mode {mode} failed:\nSTDOUT:{r.stdout}\nSTDERR:{r.stderr}"
    assert "OK" in r.stdout


@pytest.mark.parametrize("mode", _MODES)
def test_no_mode_module_shadows_a_pubrun_subpackage(mode):
    """Generalized guard: after selecting a mode, no top-level `pubrun` attribute that
    shares a name with a real subpackage may be a non-module that hides it.

    Catches the whole bug class (not just `report`): if a future mode module does
    `pubrun.<name> = <func>` where `pubrun.<name>` is also a subpackage, the subpackage
    becomes unimportable. We assert every actual subpackage remains importable as a module.
    """
    code = f"""
import importlib, pkgutil, types
import pubrun.{mode} as _mode
import pubrun

# Discover real subpackages/submodules shipped under pubrun/.
subpkgs = [m.name for m in pkgutil.iter_modules(pubrun.__path__)]
broken = []
for name in subpkgs:
    try:
        mod = importlib.import_module("pubrun." + name)
        if not isinstance(mod, types.ModuleType):
            broken.append((name, "not-a-module"))
    except Exception as e:
        broken.append((name, repr(e)))
assert not broken, "shadowed/broken subpackages under mode {mode}: " + repr(broken)
print("OK")
"""
    r = _run(code)
    assert r.returncode == 0, f"mode {mode} failed:\nSTDOUT:{r.stdout}\nSTDERR:{r.stderr}"
    assert "OK" in r.stdout


def test_report_call_and_submodule_coexist_same_process():
    """In one process: call pubrun.report() AND import a report submodule, in both
    orders, to prove they coexist (the exact interaction the regression broke)."""
    code = """
import os, tempfile
os.chdir(tempfile.mkdtemp())
import pubrun.noauto as pubrun
# submodule first, then call
import pubrun.report.output  # noqa
import pubrun as base
t = pubrun.start()
base.report("metric", {"acc": 0.9})
pubrun.stop()
# submodule import AGAIN after a full run cycle
import importlib
importlib.import_module("pubrun.report.diagnostics")
importlib.import_module("pubrun.report.checks")
print("OK")
"""
    r = _run(code)
    assert r.returncode == 0, f"failed:\nSTDOUT:{r.stdout}\nSTDERR:{r.stderr}"
    assert "OK" in r.stdout
