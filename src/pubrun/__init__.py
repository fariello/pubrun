"""
pubrun - A lightweight Python library for capturing execution context.
"""
import logging
from typing import Any, Callable, Optional

from pubrun.tracker import Run, get_current_run

# Version of the pubrun package
__version__ = "0.1.0"


def annotate(message: Optional[str] = None, **kwargs: Any) -> None:
    """Explicitly inject an annotation event into the active JSON telemetry stream.
    
    This function bridges the gap between your custom ML application logic and the 
    underlying `pubrun` tracking payload. If `pubrun` is actively watching, 
    this will serialize your `message` along with any arbitrary keyword arguments 
    straight into the temporal `events.jsonl` pipeline.

    Examples:
        >>> import pubrun
        >>> pubrun.annotate("Starting GPU Allocation")
        >>> pubrun.annotate("Model Configured", layers=50, optimizer="adamw")

    Args:
        message (Optional[str], optional): The human-readable string flag to record. Defaults to None.
        **kwargs: Any number of JSON-serializable key=value pairs to lock into the dataset payload.
    """
    current_run = get_current_run()
    if current_run and getattr(current_run, "event_stream", None):
        payload = kwargs.copy()
        current_run.event_stream.emit("annotation", name=message, payload=payload)
    else:
        from pubrun.config import resolve_config
        action = resolve_config().get("events", {}).get("on_inactive_annotate", "ignore")
        if action == "error":
            raise RuntimeError("pubrun.annotate() called but no run is active.")
        elif action == "warn":
            logging.getLogger("pubrun").warning(f"Annotation dropped: No active pubrun.")


def start(**kwargs: Any) -> Run:
    """Start tracking a new execution context.
    
    Initializes all telemetry sub-engines (like RAM watchers and Subprocess Spies) 
    and generates a unique `.run_dir` for artifact storage. 
    
    You do NOT need to call this if `auto_start = true` inside `default.toml` or `PUBRUN_AUTO_START` is enabled.

    Examples:
        >>> import pubrun
        >>> tracker = pubrun.start(profile="deep")
        >>> # DO ML WORK
        >>> tracker.stop()

    Returns:
        Run: The active synchronization engine tracking your script.
    """
    return Run(overrides=kwargs)


def stop() -> None:
    """Manually culminate the active tracking session.
    
    This immediately flushes all internal caches to disk locally and generates the 
    `manifest.json` report containing complete hardware specifications, Python runtime
    status, and dependency profiles.
    
    If `pubrun` auto-started via dependency hook, this is invoked automatically 
    when the Python interpretor exits.

    Examples:
        >>> pubrun.stop()
    """
    current_run = get_current_run()
    if current_run:
        current_run.stop()


def audit_run(func: Optional[Callable] = None, **kwargs: Any) -> Callable:
    """Wrap an entire Python function execution within an isolated pubrun boundary.

    This decorator initiates `pubrun` specifically as the function begins, 
    intercepts any generic Exceptions (flagging the trace result as 'failed'), 
    and then cleanly halts telemetry the exact moment the function ceases.

    Examples:
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
            return func(*args, **func_kwargs)
        except Exception:
            run_tracker._outcome = "failed"
            raise
        finally:
            run_tracker.stop()
            
    return wrapped


class tracked_run:
    """Context manager to surgically inject `pubrun` over a specific code footprint.

    Allows isolated and distinct profiling for an explicitly delimited sequence of Python syntax.

    Examples:
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
                self.run_tracker._outcome = "failed"
            self.run_tracker.stop()


class phase:
    """Wrap execution steps into temporally labeled segments within the JSON tracker.
    
    If you are attempting to optimize distinct elements of an ML pipeline (e.g. Data Loading 
    vs Gradient Descent), bounding each zone in a `phase()` natively writes boundary 
    timestamps directly to `events.jsonl`.

    Examples:
        >>> with pubrun.phase("data_ingestion"):
        >>>     df = pd.read_csv("huge.csv")
    """
    def __init__(self, name: str) -> None:
        self.name = name
        self.run_tracker = get_current_run()

    def __enter__(self) -> "phase":
        if self.run_tracker and getattr(self.run_tracker, "event_stream", None):
            self.run_tracker.event_stream.emit("phase_start", name=self.name)
        else:
            from pubrun.config import resolve_config
            action = resolve_config().get("events", {}).get("on_inactive_annotate", "ignore")
            if action == "error":
                raise RuntimeError(f"pubrun.phase('{self.name}') called but no run is active.")
            elif action == "warn":
                logging.getLogger("pubrun").warning(f"Phase '{self.name}' dropped: No active pubrun.")
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        if self.run_tracker and getattr(self.run_tracker, "event_stream", None):
            if exc_type is not None:
                err_payload = {"error": exc_val.__class__.__name__}
                self.run_tracker.event_stream.emit("phase_end", name=self.name, payload=err_payload)
            else:
                self.run_tracker.event_stream.emit("phase_end", name=self.name)
