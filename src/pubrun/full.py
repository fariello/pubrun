"""
pubrun.full — Capture everything, including console output, on import.

Usage::

    import pubrun.full as pubrun

Equivalent to the default ``import pubrun`` (auto-start, subprocess spy, signal
handlers, resource monitoring) PLUS it FORCES the console tee on — stdout/stderr
are wrapped and copied to the run directory even though the default
``[console].capture_mode`` is ``"off"``. It is the one-import "capture
everything" preset and the mirror image of ``pubrun.noconsole``.

The import mode is an absolute imperative: ``full`` forces console capture on
regardless of any ``capture_mode`` in a config file or environment variable
(only ``pubrun run --mode ...`` at launch can override the in-code import). The
Jupyter and non-TTY safety guards still apply — in a Jupyter kernel the tee
auto-disables (double-wrapping the notebook's stdout is broken), and a
``non_tty_mode`` override is still honored.
"""
from pubrun._bootstrap import select_mode

# Select mode before importing core
_behavior = select_mode("full", "pubrun.full", "explicit")

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
    _execute_boot_sequence,
)

# Also make __version__ available
from pubrun import __version__  # noqa: F401, E402

# Execute boot (auto-start since "full" has auto_start=True)
_execute_boot_sequence(selected_by="pubrun.full")
del _execute_boot_sequence, _behavior

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
