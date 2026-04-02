"""
runtrace - A lightweight Python library for capturing execution context.
"""
from typing import Any, Callable, Optional

# Version of the runtrace package
__version__ = "0.1.0"


def annotate(label: str, data: Any = None) -> None:
    """
    Log a custom annotation to the active trace.
    If no trace is active, behavior depends on the `on_inactive_annotate` config.
    """
    # Stub: to be implemented by capture engine
    pass


def start(**kwargs: Any) -> Any:
    """
    Start a trace. Accepts configuration overrides as kwargs.
    Returns the active Run tracker instance.
    """
    # Stub
    pass


def audit_run(func: Optional[Callable] = None, **kwargs: Any) -> Callable:
    """
    Decorator to wrap a function execution in a tracked run.
    """
    if func is None:
        def wrapper(f: Callable) -> Callable:
            return audit_run(f, **kwargs)
        return wrapper

    def wrapped(*args: Any, **func_kwargs: Any) -> Any:
        # Stub logic
        return func(*args, **func_kwargs)
    return wrapped


class tracked_run:
    """
    Context manager to wrap a block of code in a tracked run.
    """
    def __init__(self, **kwargs: Any) -> None:
        self.kwargs = kwargs

    def __enter__(self) -> "tracked_run":
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        pass


class phase:
    """
    Context manager to mark a temporal phase within an active trace.
    """
    def __init__(self, name: str) -> None:
        self.name = name

    def __enter__(self) -> "phase":
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        pass
