"""
pubrun.noconsole — Auto-start tracking but skip wrapping console streams.

Usage::

    import pubrun.noconsole as pubrun

    # Telemetry tracking starts automatically, but stdout/stderr are not wrapped.
"""
from pubrun._bootstrap import select_mode

# Select mode before importing core
_behavior = select_mode("noconsole", "pubrun.noconsole", "explicit")

# Import the full public API (must match the top-level `import pubrun` surface,
# so `import pubrun.noconsole as pubrun` exposes the same names).
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

# Execute boot — since auto_start is True for noconsole, it will auto-start tracking
_boot(selected_by="pubrun.noconsole")
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
