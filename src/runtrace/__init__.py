"""
runtrace - A lightweight Python library for capturing execution context.
"""
import logging
from typing import Any, Callable, Optional

from runtrace.tracker import Run, get_current_run

# Version of the runtrace package
__version__ = "0.1.0"


def annotate(label: str, data: Any = None) -> None:
    """
    Log a custom annotation to the active trace.
    If no trace is active, behavior depends on the `on_inactive_annotate` config.
    """
    current_run = get_current_run()
    if current_run:
        # Expected in Phase 3 (Event Stream)
        pass
    else:
        # We fail silently by default to prevent crashing host scripts
        logging.getLogger("runtrace").debug(f"Annotation '{label}' dropped: No active runtrace.")


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

    def __enter__(self) -> "phase":
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        # Phase 3 hooks
        pass
