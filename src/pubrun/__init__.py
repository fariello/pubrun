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

# -- Public API (re-exported from core) --------------------------------------
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

# -- Boot Sequence ------------------------------------------------------------
# Execute auto-start logic for root `import pubrun` (the default path).
# Mode submodules (pubrun.noauto, etc.) will skip this in Phase 4.
from pubrun.core import _execute_boot_sequence as _boot  # noqa: E402
_boot()
del _boot
