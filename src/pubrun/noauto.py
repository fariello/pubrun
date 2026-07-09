"""
pubrun.noauto — Load API without auto-starting a run.

Usage::

    import pubrun.noauto as pubrun

    # API is available but no run is active yet.
    pubrun.start()  # You control when tracking begins.

The same hooks as the default ``auto`` mode apply once ``start()`` is called:
the subprocess spy and signal handlers install and are on by default, while the
console tee is *permitted* but stays off unless ``[console].capture_mode`` is
set (it defaults to ``"off"``). To auto-start while suppressing hooks, use
``pubrun.nopatch``; to auto-start while skipping only the console tee, use
``pubrun.noconsole``.
"""
from pubrun._bootstrap import select_mode

# Select mode before importing core — prevents auto-start
_behavior = select_mode("noauto", "pubrun.noauto", "explicit")

# Import the full public API (no boot sequence — no auto-start)
from pubrun.core import (  # noqa: F401, E402
    start,
    stop,
    annotate,
    phase,
    paused,
    diff,
    audit_run,
    tracked_run,
    get_current_run,
    report,
    artifact,
    print,
    open,
    subprocess,
    popen,
    _run_lock,
)
from pubrun.core import _execute_boot_sequence as _boot  # noqa: E402
from pubrun import __version__  # noqa: F401, E402

# Execute boot but with noauto mode already selected — will NOT auto-start
_boot(selected_by="pubrun.noauto")
del _boot, _behavior

# Populate the parent pubrun namespace so `from pubrun import X` works
# after `import pubrun.noauto`. This is needed because __init__.py deferred.
import pubrun as _pkg  # noqa: E402
_pkg.start = start
_pkg.stop = stop
_pkg.annotate = annotate
_pkg.phase = phase
_pkg.paused = paused
_pkg.diff = diff
_pkg.audit_run = audit_run
_pkg.tracked_run = tracked_run
_pkg.get_current_run = get_current_run
# `pubrun.report` is a CallableModule (see pubrun/report/__init__.py): BOTH callable as
# the report() API AND a subpackage exposing pubrun.report.output/checks/diagnostics.
# Import the subpackage so `pubrun.report` resolves to that CallableModule (callable
# and submodule-bearing). Do NOT do `_pkg.report = report` — assigning the plain
# function shadows the subpackage and breaks `import pubrun.report.<submodule>`.
import pubrun.report  # noqa: E402,F401
_pkg.artifact = artifact
_pkg.print = print
_pkg.open = open
_pkg.subprocess = subprocess
_pkg.popen = popen
_pkg._run_lock = _run_lock
del _pkg
