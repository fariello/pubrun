"""
pubrun.auto — Explicit auto-start mode (same as default ``import pubrun``).

Usage::

    import pubrun.auto as pubrun

This is equivalent to a plain ``import pubrun`` with default config.
Useful when you want to be explicit about the mode in source code.

Note: "auto" permits the console tee, but stdout/stderr are NOT wrapped by
default — ``[console].capture_mode`` defaults to ``"off"``. Subprocess and
signal capture are on by default (their ``enabled`` keys default true), and the
background resource watcher runs in every mode while a run is active.
"""
from pubrun._bootstrap import select_mode

# Select mode before importing core
_behavior = select_mode("auto", "pubrun.auto", "explicit")

# Import the full public API
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
    _execute_boot_sequence,
)

# Also make __version__ available
from pubrun import __version__  # noqa: F401, E402

# Execute boot (auto-start since this is "auto" mode)
_execute_boot_sequence(selected_by="pubrun.auto")
del _execute_boot_sequence, _behavior

# Populate the parent pubrun namespace
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
_pkg.report = report
_pkg.artifact = artifact
_pkg.print = print
_pkg.open = open
_pkg.subprocess = subprocess
_pkg.popen = popen
_pkg._run_lock = _run_lock
del _pkg
