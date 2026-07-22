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

4. Import modes::

    import pubrun.auto as pubrun     # Explicit default: auto-start.
    import pubrun.full as pubrun     # Auto-start; force console capture on (capture everything).
    import pubrun.noauto as pubrun   # No auto-start; start() manually.
    import pubrun.nopatch as pubrun  # Auto-start, no global hooks.
    import pubrun.noconsole as pubrun # Auto-start, no console wrapping.
    import pubrun.minimal as pubrun  # No auto-start, no hooks.
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
    __version__ = "1.0.0"  # fallback for editable installs / dev

# Commit hash resolution. A file cannot contain its own commit's hash, so prefer the LIVE
# HEAD when running from a git checkout (always exact, never one commit behind), and fall
# back to the packaged COMMIT file for installed wheels (stamped by the post-commit hook and
# the build). Both paths are best-effort and stdlib-only, preserving the zero-runtime-dep
# invariant; any failure yields None rather than raising at import time.
def _resolve_commit():
    # 1) Live git HEAD from the checkout containing this file (dev / source use).
    try:
        import os as _os
        import subprocess as _sp
        _repo = _os.path.dirname(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
        _proc = _sp.run(
            ["git", "-C", _repo, "rev-parse", "HEAD"],
            capture_output=True, text=True, timeout=5,
        )
        if _proc.returncode == 0:
            _head = _proc.stdout.strip()
            if _head:
                return _head
    except Exception:
        pass
    # 2) Packaged COMMIT file (installed wheel / no git available).
    try:
        import importlib.resources as _pkg_resources
        if sys.version_info >= (3, 9):
            return _pkg_resources.files("pubrun").joinpath("COMMIT").read_text(encoding="utf-8").strip()
        return _pkg_resources.read_text("pubrun", "COMMIT").strip()
    except Exception:
        return None


__commit__ = _resolve_commit()

# Publication name (matches the author's existing academic publication record so
# citations aggregate correctly). The full legal name appears in LICENSE/NOTICE.
__author__ = "Gabriele Fariello"
__license__ = "Apache-2.0"
__copyright__ = "Copyright 2007-2026 Gabriele Fariello"
__credit__ = __author__  # backward-compatible alias

__all__ = [
    "start",
    "stop",
    "annotate",
    "phase",
    "paused",
    "diff",
    "audit_run",
    "tracked_run",
    "get_current_run",
    "report",
    "artifact",
    "print",
    "open",
    "subprocess",
    "popen",
    "__version__",
    "__commit__",
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
    _execute_boot_sequence()
    del _execute_boot_sequence
else:
    # Mode submodule import in progress — defer everything to the submodule.
    # The submodule will import pubrun.core and populate pubrun.* attributes.
    # If the submodule import fails, we need a safety net so pubrun isn't
    # left permanently broken (P2-B5).
    import atexit as _atexit

    def _ensure_core_loaded():
        """Safety net: if mode submodule failed, load core as fallback."""
        import pubrun as _pkg
        if not hasattr(_pkg, "start"):
            try:
                from pubrun.core import (
                    start, stop, annotate, phase, paused, diff,
                    audit_run, tracked_run, get_current_run,
                    report, artifact, print, open, subprocess, popen,
                    _run_lock,
                )
                _pkg.start = start
                _pkg.stop = stop
                _pkg.annotate = annotate
                _pkg.phase = phase
                _pkg.paused = paused
                _pkg.diff = diff
                _pkg.audit_run = audit_run
                _pkg.tracked_run = tracked_run
                _pkg.get_current_run = get_current_run
                # `pubrun.report` is a CallableModule (pubrun/report/__init__.py): BOTH callable
                # as the report() API AND a subpackage exposing pubrun.report.output/checks/
                # diagnostics. Import the subpackage so the attribute is that CallableModule; do
                # NOT do `_pkg.report = report` (the plain function shadows the subpackage and
                # breaks `import pubrun.report.<submodule>`).
                import pubrun.report  # noqa: F401
                _pkg.artifact = artifact
                _pkg.print = print
                _pkg.open = open
                _pkg.subprocess = subprocess
                _pkg.popen = popen
                _pkg._run_lock = _run_lock
            except Exception:
                pass

    _atexit.register(_ensure_core_loaded)
    del _atexit

del _is_mode_import
