"""
pubrun.minimal — API-only mode with no auto-start and no global patches.

Usage::

    import pubrun.minimal as pubrun

    # Nothing happens until you explicitly start.
    pubrun.start()  # Starts tracking with minimal-mode defaults.

No auto-start, no subprocess interception, no console replacement,
no signal handlers installed at import time. When ``start()`` is called
later, the minimal-mode defaults (no global patches/hooks) apply unless explicitly
overridden.
"""
from pubrun._bootstrap import select_mode

# Select mode before importing core — no auto-start, no hooks
_behavior = select_mode("minimal", "pubrun.minimal", "explicit")

# Import the full public API (no boot sequence side effects)
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
)
from pubrun.core import _execute_boot_sequence as _boot  # noqa: E402
from pubrun import __version__  # noqa: F401, E402

# Execute boot — mode is minimal, so no auto-start and no hooks
_boot(selected_by="pubrun.minimal")
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
_pkg._run_lock = _run_lock
del _pkg
