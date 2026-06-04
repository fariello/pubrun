"""
pubrun - Zero-dependency Python execution provenance and telemetry capture.

Usage
-----
1. Auto-start (default)::

    import pubrun  # Tracking begins on import.

2. Explicit control::

    import pubrun

    tracker = pubrun.start(profile="deep")
    pubrun.annotate("loading_datasets", batches=400, mode="lazy")

    with pubrun.phase("gradient_descent"):
        train_model()

    tracker.stop()

3. Decorator::

    @pubrun.audit_run(profile="basic")
    def evaluate_node():
        ...

4. Import modes (no auto-start)::

    import pubrun.noauto as pubrun
    pubrun.start()  # You control when tracking begins.
"""
import sys

# -- Metadata ----------------------------------------------------------------
try:
    if sys.version_info >= (3, 8):
        from importlib.metadata import version as _pkg_version
    else:
        from importlib_metadata import version as _pkg_version
    __version__ = _pkg_version("pubrun")
except Exception:
    __version__ = "0.2.0"  # fallback for editable installs / dev

__author__ = "Gabriele Fariello"
__license__ = "BSD-3-Clause"
__copyright__ = "Copyright 2026 Gabriele Fariello"
__credit__ = __author__  # backward-compatible alias

__all__ = [
    "start",
    "stop",
    "annotate",
    "phase",
    "diff",
    "audit_run",
    "tracked_run",
    "get_current_run",
    "__version__",
]

# -- Target-aware routing -----------------------------------------------------
# When Python processes `import pubrun.noauto`, it loads pubrun/__init__.py
# first. We detect this and defer core loading to the mode submodule.
from pubrun._bootstrap import is_mode_submodule_import_in_progress as _is_mode_import  # noqa: E402

if not _is_mode_import():
    # Root import: load core and execute boot sequence (auto-start if configured)
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
    _execute_boot_sequence()
    del _execute_boot_sequence
else:
    # Mode submodule import in progress — defer everything to the submodule.
    # The submodule will import pubrun.core and populate pubrun.* attributes.
    pass

del _is_mode_import
