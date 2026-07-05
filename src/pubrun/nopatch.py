"""
pubrun.nopatch — Auto-start tracking without process-global hooks.

Usage::

    import pubrun.nopatch as pubrun

Tracking starts automatically, but no subprocess interception, console
stream replacement, or signal handlers are installed. Still captures
static metadata: process info, Python runtime, packages, environment,
Git state, host, hardware, and resource monitoring (background thread).
"""
from pubrun._bootstrap import select_mode

# Select mode before importing core — prevents global hook installation
_behavior = select_mode("nopatch", "pubrun.nopatch", "explicit")

# Import the full public API
from pubrun.core import (  # noqa: F401, E402
    start,
    stop,
    annotate,
    phase,
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

# Execute boot — auto-starts but mode behavior suppresses global hooks
_boot(selected_by="pubrun.nopatch")
del _boot, _behavior

# Populate the parent pubrun namespace
import pubrun as _pkg  # noqa: E402
_pkg.start = start
_pkg.stop = stop
_pkg.annotate = annotate
_pkg.phase = phase
_pkg.diff = diff
_pkg.audit_run = audit_run
_pkg.tracked_run = tracked_run
_pkg.get_current_run = get_current_run
_pkg.report = report
_pkg.artifact = artifact
_pkg.print = print
_pkg.open = open
_pkg.subprocess = subprocess
_pkg.popen = popen
_pkg._run_lock = _run_lock
del _pkg
