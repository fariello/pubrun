"""
runtrace - A lightweight Python library for capturing execution context.
"""
import logging
from typing import Any, Callable, Optional

from runtrace.tracker import Run, get_current_run

# Version of the runtrace package
__version__ = "0.1.0"


def annotate(message: Optional[str] = None, **kwargs: Any) -> None:
    """
    Explicitly document user payloads in the active events.jsonl stream.
    If no trace is active, behavior depends on the `on_inactive_annotate` config.
    """
    current_run = get_current_run()
    if current_run and getattr(current_run, "event_stream", None):
        payload = kwargs.copy()
        current_run.event_stream.emit("annotation", name=message, payload=payload)
    else:
        from runtrace.config import resolve_config
        action = resolve_config().get("events", {}).get("on_inactive_annotate", "ignore")
        if action == "error":
            raise RuntimeError("runtrace.annotate() called but no run is active.")
        elif action == "warn":
            logging.getLogger("runtrace").warning(f"Annotation dropped: No active runtrace.")


def start(**kwargs: Any) -> Run:
    """
    Start a trace. Accepts configuration overrides as kwargs.
    Returns the active Run tracker instance.
    """
    return Run(overrides=kwargs)


def stop() -> None:
    """
    Manually halt the active trace, flushing the manifest.json immediately.
    """
    current_run = get_current_run()
    if current_run:
        current_run.stop()


def audit_run(func: Optional[Callable] = None, **kwargs: Any) -> Callable:
    """
    Decorator to wrap a function execution in a tracked run.
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
    """
    Context manager to wrap a block of code in a tracked run.
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
    """
    Context manager to mark a temporal phase within an active trace.
    """
    def __init__(self, name: str) -> None:
        self.name = name
        self.run_tracker = get_current_run()

    def __enter__(self) -> "phase":
        if self.run_tracker and getattr(self.run_tracker, "event_stream", None):
            self.run_tracker.event_stream.emit("phase_start", name=self.name)
        else:
            from runtrace.config import resolve_config
            action = resolve_config().get("events", {}).get("on_inactive_annotate", "ignore")
            if action == "error":
                raise RuntimeError(f"runtrace.phase('{self.name}') called but no run is active.")
            elif action == "warn":
                logging.getLogger("runtrace").warning(f"Phase '{self.name}' dropped: No active runtrace.")
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        if self.run_tracker and getattr(self.run_tracker, "event_stream", None):
            if exc_type is not None:
                err_payload = {"error": exc_val.__class__.__name__}
                self.run_tracker.event_stream.emit("phase_end", name=self.name, payload=err_payload)
            else:
                self.run_tracker.event_stream.emit("phase_end", name=self.name)
