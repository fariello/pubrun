"""
pubrun.auto — Explicit auto-start mode (same as default ``import pubrun``).

Usage::

    import pubrun.auto as pubrun

This is equivalent to a plain ``import pubrun`` with default config.
Useful when you want to be explicit about the mode in source code.
"""
from pubrun._bootstrap import select_mode
from pubrun._modes import get_mode_behavior

# Select mode before importing core
_behavior = select_mode("auto", "pubrun.auto", "explicit")

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
_pkg.diff = diff
_pkg.audit_run = audit_run
_pkg.tracked_run = tracked_run
_pkg.get_current_run = get_current_run
_pkg._run_lock = _run_lock
del _pkg
