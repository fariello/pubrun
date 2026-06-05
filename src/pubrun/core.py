"""
pubrun.core - Public API implementation and boot sequence.

This module contains the actual implementation of start(), stop(), annotate(),
phase(), tracked_run(), audit_run(), diff(), and the auto-start boot logic.

It is imported by pubrun/__init__.py for the default (root import) path,
and will be imported by mode submodules (pubrun.noauto, pubrun.nopatch, etc.)
in later phases.

All public symbols are re-exported at the package root so users always
access them via ``pubrun.start()``, ``pubrun.stop()``, etc.
"""
import functools
import logging
import os
import sys
import threading
from typing import Any, Callable, Optional

from pubrun.tracker import Run, get_current_run


# -- Thread lock for ref_count safety ----------------------------------------
_run_lock = threading.Lock()


# -- Internal helpers ---------------------------------------------------------

def _handle_inactive(context: str) -> None:
    """Check the on_inactive_annotate policy and raise/warn/ignore accordingly.

    Called when annotate() or phase() is used with no active run.

    Args:
        context: Human-readable label for the error/warning message
            (e.g. "pubrun.annotate()" or "pubrun.phase('training')").
    """
    from pubrun.config import resolve_config
    action = resolve_config().get("events", {}).get("on_inactive_annotate", "ignore")
    if action == "error":
        raise RuntimeError(f"{context} called but no run is active.")
    elif action == "warn":
        logging.getLogger("pubrun").warning(f"{context} dropped: No active run.")


# -- Public API ---------------------------------------------------------------

def annotate(message: Optional[str] = None, **kwargs: Any) -> None:
    """Inject an annotation event into the active event stream.

    If a run is active, the message and keyword arguments are written to
    ``events.jsonl``.  If no run is active, behavior depends on the
    ``[events].on_inactive_annotate`` config key ("ignore", "warn", or "error").

    Args:
        message: Optional human-readable label for the annotation.
        **kwargs: Arbitrary JSON-serializable key-value pairs.

    Example:
        >>> pubrun.annotate("Starting GPU Allocation")
        >>> pubrun.annotate("Model Configured", layers=50, optimizer="adamw")
    """
    current_run = get_current_run()
    if current_run and getattr(current_run, "event_stream", None):
        payload = kwargs.copy()
        current_run.event_stream.emit("annotation", name=message, payload=payload)
    else:
        _handle_inactive("pubrun.annotate()")


def start(**kwargs: Any) -> Run:
    """Start tracking a new execution context.

    Creates a unique run directory and initializes all configured capture
    engines.  Not needed when ``auto_start = true`` (the default).

    If a run is already active, increments its reference count and merges
    the new overrides into the existing configuration.

    .. note:: Threading model

       ``start()`` and ``stop()`` should be called from the **main thread**.
       ``annotate()``, ``phase()``, and ``get_current_run()`` are safe to
       call from any thread.  Signal capture requires main-thread installation.

    Args:
        **kwargs: Configuration overrides (same keys as ``.pubrun.toml``).

    Returns:
        The active ``Run`` instance.

    Example:
        >>> tracker = pubrun.start(profile="deep")
        >>> tracker.stop()
    """
    with _run_lock:
        active = get_current_run()
        if active:
            active.ref_count = getattr(active, "ref_count", 0) + 1
    if active:
        if hasattr(active, "_merge_and_migrate"):
            active._merge_and_migrate(kwargs)
        return active
    return Run(overrides=kwargs)


def stop() -> None:
    """Stop the active tracking session and write artifacts to disk.

    Flushes all capture engines, writes ``manifest.json`` and
    ``config.resolved.json``.  Called automatically at interpreter exit
    if auto-start is enabled.  Safe to call when no run is active.
    """
    current_run = get_current_run()
    if current_run:
        current_run.stop()


def diff(run_dir_a: str, run_dir_b: str, ignores: Optional[list] = None) -> dict:
    """Compare two run manifests and return a structured diff.

    Args:
        run_dir_a: Path to the baseline run directory.
        run_dir_b: Path to the comparison run directory.
        ignores: Manifest keys to exclude from comparison.
            Defaults to the ``[diff].ignore`` config list.

    Returns:
        Dict with ``added``, ``removed``, ``modified``, and ``same`` keys.

    Example:
        >>> delta = pubrun.diff("runs/A", "runs/B")
        >>> print(delta["added"])
    """
    import json
    from pathlib import Path
    from pubrun.config import resolve_config
    from pubrun.report.utils import hydrate_manifest
    from pubrun.analysis.diff import compare_manifests

    def _load(d: str) -> dict:
        p = Path(d) / "manifest.json"
        if not p.exists():
            raise FileNotFoundError(f"Missing: {p}")
        with open(p, "r", encoding="utf-8") as f:
            obj = json.load(f)
        obj, _ = hydrate_manifest(str(p), obj)
        return obj

    manifest_a = _load(run_dir_a)
    manifest_b = _load(run_dir_b)

    if ignores is None:
        ignores = resolve_config().get("diff", {}).get("ignore", [])

    return compare_manifests(manifest_a, manifest_b, ignores)


def audit_run(func: Optional[Callable] = None, **kwargs: Any) -> Callable:
    """Decorator that wraps a function in a pubrun tracking session.

    Starts a run before the function executes and stops it afterward.
    If the function raises, the outcome is set to ``"failed"`` and the
    exception is re-raised.

    Args:
        func: The function to wrap (supplied automatically by Python).
        **kwargs: Configuration overrides forwarded to ``start()``.

    Example:
        >>> @pubrun.audit_run(profile="deep")
        ... def train():
        ...     model.fit()
    """
    if func is None:
        def wrapper(f: Callable) -> Callable:
            return audit_run(f, **kwargs)
        return wrapper

    @functools.wraps(func)
    def wrapped(*args: Any, **func_kwargs: Any) -> Any:
        run_tracker = start(**kwargs)
        try:
            result = func(*args, **func_kwargs)
            run_tracker.stop(outcome="completed")
            return result
        except Exception:
            run_tracker.stop(outcome="failed")
            raise

    return wrapped


class tracked_run:
    """Context manager that wraps a code block in a pubrun tracking session.

    Args:
        **kwargs: Configuration overrides forwarded to ``start()``.

    Example:
        >>> with pubrun.tracked_run(profile="minimal"):
        ...     model.train(epochs=5)
    """
    def __init__(self, **kwargs: Any) -> None:
        self.kwargs = kwargs
        self.run_tracker: Optional[Run] = None

    def __enter__(self) -> "tracked_run":
        self.run_tracker = start(**self.kwargs)
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        if self.run_tracker:
            if exc_type is not None:
                self.run_tracker.stop(outcome="failed")
            else:
                self.run_tracker.stop(outcome="completed")


class phase:
    """Context manager that emits ``phase_start``/``phase_end`` events.

    Useful for timing distinct pipeline stages (e.g. data loading vs training).
    Requires an active run to log events; behavior with no active run is
    controlled by ``[events].on_inactive_annotate``.

    Args:
        name: Label for this phase (written to ``events.jsonl``).

    Example:
        >>> with pubrun.phase("data_ingestion"):
        ...     df = pd.read_csv("huge.csv")
    """
    def __init__(self, name: str) -> None:
        self.name = name
        self.run_tracker = get_current_run()

    def __enter__(self) -> "phase":
        if self.run_tracker and getattr(self.run_tracker, "event_stream", None):
            self.run_tracker.event_stream.emit("phase_start", name=self.name)
        else:
            _handle_inactive(f"pubrun.phase('{self.name}')")
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        if self.run_tracker and getattr(self.run_tracker, "event_stream", None):
            if exc_type is not None:
                err_payload = {"error": exc_val.__class__.__name__}
                self.run_tracker.event_stream.emit("phase_end", name=self.name, payload=err_payload)
            else:
                self.run_tracker.event_stream.emit("phase_end", name=self.name)


# -- Boot sequence ------------------------------------------------------------

def _execute_boot_sequence(selected_by: str = "pubrun") -> None:
    """Resolve import mode, register selection, and auto-start if configured.

    Called by pubrun/__init__.py during root imports. Mode submodules
    (pubrun.noauto, etc.) call this after they've already selected their mode.

    Args:
        selected_by: Identifier for who triggered this boot (e.g., "pubrun",
            "pubrun.noauto").
    """
    from pubrun._config_boot import resolve_import_mode
    from pubrun._bootstrap import select_mode, mark_core_loaded, is_mode_selected, get_selected_behavior

    _should_auto = False
    try:
        if is_mode_selected():
            # Mode was already selected by a submodule (e.g., pubrun.noauto).
            # Don't re-resolve from config — just use the already-selected behavior.
            mode_behavior = get_selected_behavior()
        else:
            # Root import — resolve from config/env and select.
            import_mode, import_source = resolve_import_mode()
            mode_behavior = select_mode(import_mode, selected_by, import_source)

        _should_auto = mode_behavior["auto_start"] if mode_behavior else False
    except Exception as boot_err:
        logging.getLogger("pubrun").warning(
            f"pubrun boot sequence failed (tracking disabled): {boot_err}"
        )
        return
    finally:
        # Mark core as loaded regardless of success/failure
        mark_core_loaded()

    if _should_auto and not get_current_run():
        sys0 = os.path.basename(sys.argv[0]) if sys.argv else ""
        if sys0 in ("pubrun", "pubrun.exe", "__main__.py"):
            return

        try:
            start()
        except Exception as start_err:
            logging.getLogger("pubrun").warning(
                f"pubrun auto-start failed (tracking disabled): {start_err}"
            )
