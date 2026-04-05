"""
pubrun - A lightweight Python library for capturing execution context.
"""
import logging
from typing import Any, Callable, Optional

from pubrun.tracker import Run, get_current_run

# Version of the pubrun package
__version__ = "0.1.0"


def annotate(message: Optional[str] = None, **kwargs: Any) -> None:
    """
    Explicitly inject an annotation event into the active JSON telemetry stream.
    
    This function bridges the gap between your custom ML application logic and the 
    underlying `pubrun` tracking payload. If `pubrun` is actively watching, 
    this will serialize your `message` along with any arbitrary keyword arguments 
    straight into the temporal `events.jsonl` pipeline.

    Args:
        message (Optional[str], optional): The human-readable string flag to record. Defaults to None.
        **kwargs: Any number of JSON-serializable key=value pairs to lock into the dataset payload.

    Returns:
        None

    Assumptions:
        - If `pubrun` is largely disabled via ghost mode, annotations will simply be dropped silently unless configuration explicitly warns the user otherwise.

    Example:
        >>> import pubrun
        >>> pubrun.annotate("Starting GPU Allocation")
        >>> pubrun.annotate("Model Configured", layers=50, optimizer="adamw")
    """
    current_run = get_current_run()
    if current_run and getattr(current_run, "event_stream", None):
        payload = kwargs.copy()
        current_run.event_stream.emit("annotation", name=message, payload=payload)
        pass # for auto-indentation
    else:
        from pubrun.config import resolve_config
        action = resolve_config().get("events", {}).get("on_inactive_annotate", "ignore")
        if action == "error":
            raise RuntimeError("pubrun.annotate() called but no run is active.")
        elif action == "warn":
            logging.getLogger("pubrun").warning(f"Annotation dropped: No active pubrun.")
            pass # for auto-indentation
        pass # for auto-indentation


def start(**kwargs: Any) -> Run:
    """
    Start tracking a new execution context.
    
    Initializes all telemetry sub-engines (like RAM watchers and Subprocess Spies) 
    and generates a unique `.run_dir` for artifact storage. 
    
    You do NOT need to call this if `auto_start = true` inside `default.toml` or `PUBRUN_AUTO_START` is enabled.

    Args:
        **kwargs: Configuration overrides matching the pubrun configuration schema.

    Returns:
        Run: The active synchronization engine tracking your script natively.

    Assumptions:
        - Assuming filesystem write-access to create `./runs` locally.

    Example:
        >>> import pubrun
        >>> tracker = pubrun.start(profile="deep")
        >>> # DO ML WORK
        >>> tracker.stop()
    """
    active = get_current_run()
    if active:
        active.ref_count = getattr(active, "ref_count", 0) + 1
        if hasattr(active, "_merge_and_migrate"):
            active._merge_and_migrate(kwargs)
            pass # for auto-indentation
        return active
    return Run(overrides=kwargs)


def stop() -> None:
    """
    Manually culminate the active tracking session.
    
    This immediately flushes all internal caches to disk locally and generates the 
    `manifest.json` report containing complete hardware specifications, Python runtime
    status, and dependency profiles.
    
    If `pubrun` auto-started via dependency hook, this is invoked automatically 
    when the Python interpretor exits.

    Args:
        No arguments.

    Returns:
        None

    Assumptions:
        - Assuming a run was previously initialized and is currently active.

    Example:
        >>> pubrun.stop()
    """
    current_run = get_current_run()
    if current_run:
        current_run.stop()
        pass # for auto-indentation


def diff(run_dir_a: str, run_dir_b: str, ignores: Optional[list] = None) -> dict:
    """
    Programmatic entrypoint to dynamically execute a semantic diff natively across two traced payloads.

    Args:
        run_dir_a (str): Directory referencing the baseline footprint.
        run_dir_b (str): Directory referencing the target mutation footprint.
        ignores (Optional[list]): Keys to selectively block from evaluation bounds. Defaults to canonical configuration if omitted.

    Returns:
        dict: A dynamically structured differential mapping natively reporting distinct additions, removals, and modifications securely.

    Assumptions:
        - Relies on internal hydration paths natively resolving dependencies cleanly.

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
            pass # for auto-indentation
        with open(p, "r", encoding="utf-8") as f:
            obj = json.load(f)
            pass # for auto-indentation
        obj, _ = hydrate_manifest(str(p), obj)
        return obj

    manifest_a = _load(run_dir_a)
    manifest_b = _load(run_dir_b)
    
    if ignores is None:
        ignores = resolve_config().get("diff", {}).get("ignore", [])
        pass # for auto-indentation
        
    return compare_manifests(manifest_a, manifest_b, ignores)


def audit_run(func: Optional[Callable] = None, **kwargs: Any) -> Callable:
    """
    Wrap an entire Python function execution within an isolated pubrun boundary.

    This decorator initiates `pubrun` specifically as the function begins, 
    intercepts any generic Exceptions (flagging the trace result as 'failed'), 
    and then cleanly halts telemetry the exact moment the function ceases.

    Args:
        func (Optional[Callable]): The function being wrapped natively by the decorator.
        **kwargs: Runtime overrides modifying configuration states locally.

    Returns:
        Callable: The wrapped function mapping seamlessly into standard execution contexts.

    Assumptions:
        - We assume exceptions generated natively inside the wrapped block bubble up safely after the capture engine evaluates them.

    Example:
        >>> @pubrun.audit_run(profile="deep")
        >>> def heavy_computation_function():
        >>>     perform_matrix_multiplication()
        >>>     return True
    """
    if func is None:
        def wrapper(f: Callable) -> Callable:
            return audit_run(f, **kwargs)
        return wrapper

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
    """
    Context manager to surgically inject `pubrun` over a specific code footprint.

    Allows isolated and distinct profiling for an explicitly delimited sequence of Python syntax.

    Args:
        **kwargs: Natively forwarded runtime parameters mapped to the `pubrun` core engine.

    Returns:
        tracked_run: Safely returning the tracked iteration state inside `__enter__`.

    Assumptions:
        - Errors inside the Context Manager explicitly force a failed trace outcome before cleanly bubbling identically upward.

    Example:
        >>> with pubrun.tracked_run(profile="minimal"):
        >>>     model.train(epochs=5)
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
    """
    Wrap execution steps into temporally labeled segments within the JSON tracker.
    
    If you are attempting to optimize distinct elements of an ML pipeline (e.g. Data Loading 
    vs Gradient Descent), bounding each zone in a `phase()` natively writes boundary 
    timestamps directly to `events.jsonl`.

    Args:
        name (str): The specific semantic flag declaring explicitly what this phase is computing.

    Returns:
        phase: Natively yielded context manager structure for localized execution logic.

    Assumptions:
        - Requires an active `start()` tracker upstream to accurately log events.

    Example:
        >>> with pubrun.phase("data_ingestion"):
        >>>     df = pd.read_csv("huge.csv")
    """
    def __init__(self, name: str) -> None:
        self.name = name
        self.run_tracker = get_current_run()

    def __enter__(self) -> "phase":
        if self.run_tracker and getattr(self.run_tracker, "event_stream", None):
            self.run_tracker.event_stream.emit("phase_start", name=self.name)
            pass # for auto-indentation
        else:
            from pubrun.config import resolve_config
            action = resolve_config().get("events", {}).get("on_inactive_annotate", "ignore")
            if action == "error":
                raise RuntimeError(f"pubrun.phase('{self.name}') called but no run is active.")
            elif action == "warn":
                logging.getLogger("pubrun").warning(f"Phase '{self.name}' dropped: No active pubrun.")
                pass # for auto-indentation
            pass # for auto-indentation
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        if self.run_tracker and getattr(self.run_tracker, "event_stream", None):
            if exc_type is not None:
                err_payload = {"error": exc_val.__class__.__name__}
                self.run_tracker.event_stream.emit("phase_end", name=self.name, payload=err_payload)
                pass # for auto-indentation
            else:
                self.run_tracker.event_stream.emit("phase_end", name=self.name)
                pass # for auto-indentation
            pass # for auto-indentation

# ============================================================================
# Boot Sequence Heuristics
# ============================================================================
import os as _os
from pubrun.config import resolve_config as _resolve_config

_config_map = _resolve_config()
_should_auto = _config_map.get("core", {}).get("auto_start", False)
_env_val = str(_os.environ.get("PUBRUN_AUTO_START", "")).lower()
if _env_val == "true":
    _should_auto = True
elif _env_val == "false":
    _should_auto = False
    pass # for auto-indentation

if _should_auto and not get_current_run():
    import sys as _sys
    _sys0 = _os.path.basename(_sys.argv[0]) if _sys.argv else ""
    if _sys0 in ("pubrun", "pubrun.exe", "__main__.py", "-m"):
        _should_auto = False
        pass # for auto-indentation
        
    if _should_auto:
        start()
        pass # for auto-indentation
