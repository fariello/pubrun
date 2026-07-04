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
        if sys0 in ("pubrun", "pubrun.exe", "pbr", "pbr.exe", "__main__.py", "-m") or "pubrun.__main__" in sys.modules:
            return

        try:
            start()
        except Exception as start_err:
            logging.getLogger("pubrun").warning(
                f"pubrun auto-start failed (tracking disabled): {start_err}"
            )


# -- Explicit Tracking API (Phases 1-4) --------------------------------------

import hashlib
import time
import subprocess as _subprocess
from pathlib import Path
import builtins

def report(name: str, data: Any) -> None:
    """Save a custom structured report to the run directory.
    
    If data is a dict or list, it is serialized as JSON (to '{name}.json').
    Otherwise, it is written as a plain string (to '{name}.txt').
    
    Emits an annotation event so the report is discoverable via `pubrun report`.
    """
    import json
    run = get_current_run()
    if not run or not run.is_active:
        _handle_inactive(f"pubrun.report('{name}')")
        return

    try:
        # Determine format and file name
        if isinstance(data, (dict, list)):
            filename = f"{name}.json"
            content = json.dumps(data, indent=2)
            summary = data if isinstance(data, dict) else {"items": len(data)}
        else:
            filename = f"{name}.txt"
            content = str(data)
            summary = {"preview": content[:100]}

        # Write file safely
        dest = run.run_dir / filename
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(content, encoding="utf-8")

        # Emit annotation to make it visible in `pubrun report`
        annotate(f"report: {name}", filename=filename, summary=summary)
    except Exception as e:
        logging.getLogger("pubrun").warning(f"pubrun: failed to write report '{name}': {e}")


def artifact(filename: str, content: Any) -> None:
    """Write a file (e.g., text, csv, or binary bytes) to the run directory.
    
    Emits an annotation event so the file is recorded in the run's event timeline.
    """
    run = get_current_run()
    if not run or not run.is_active:
        _handle_inactive(f"pubrun.artifact('{filename}')")
        return

    try:
        dest = run.run_dir / filename
        dest.parent.mkdir(parents=True, exist_ok=True)

        if isinstance(content, bytes):
            dest.write_bytes(content)
        else:
            dest.write_text(str(content), encoding="utf-8")

        # Emit annotation to make it visible in `pubrun report`
        annotate(f"artifact: {filename}", filename=filename)
    except Exception as e:
        logging.getLogger("pubrun").warning(f"pubrun: failed to write artifact '{filename}': {e}")


def print(*args: Any, **kwargs: Any) -> None:
    """Drop-in print replacement that logs to stdout.log in the active run directory.
    
    Respects all standard print arguments (sep, end, file, flush).
    """
    # 1. Capture the printed string
    sep = kwargs.get("sep", " ")
    end = kwargs.get("end", "\n")
    msg = sep.join(map(str, args)) + end
    
    builtins.print(*args, **kwargs)
    
    run = get_current_run()
    if run and run.is_active:
        try:
            log_path = run.run_dir / "stdout.log"
            timestamped = run.config.get("console", {}).get("capture_mode", "off") in {"standard", "deep"}
            
            if timestamped:
                from datetime import datetime, timezone
                lines = msg.split('\n')
                out_lines = []
                for i, line in enumerate(lines):
                    if i < len(lines) - 1 or line:
                        ts = f"[{datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3]}Z] "
                        out_lines.append(ts + line)
                    else:
                        out_lines.append("")
                log_msg = '\n'.join(out_lines)
            else:
                log_msg = msg
                
            with builtins.open(log_path, "a", encoding="utf-8") as f:
                f.write(log_msg)
        except Exception as e:
            logging.getLogger("pubrun").warning(f"pubrun.print: failed to write to stdout.log: {e}")


class ProvenanceFileProxy:
    """Wraps a standard file stream to compute hash on the fly for reads,
    and record file size/hashes on close."""
    def __init__(self, file_obj: Any, path: Path, mode: str, run_instance: Any) -> None:
        self._file_obj = file_obj
        self._path = path
        self._mode = mode
        self._run = run_instance
        self._hash = hashlib.sha256()
        self._bytes_read = 0
        self._closed = False
        # PERF-08: detect binary mode at construction to skip isinstance per I/O call.
        self._is_binary = "b" in mode

    def _to_bytes(self, data: Any) -> bytes:
        """Convert data to bytes for hashing. Skips encode for binary mode."""
        if self._is_binary:
            return data
        return data.encode("utf-8", errors="ignore")

    def read(self, size: int = -1) -> Any:
        data = self._file_obj.read(size)
        if data:
            chunk = self._to_bytes(data)
            self._hash.update(chunk)
            self._bytes_read += len(chunk)
        return data

    def readline(self, limit: int = -1) -> Any:
        data = self._file_obj.readline(limit)
        if data:
            chunk = self._to_bytes(data)
            self._hash.update(chunk)
            self._bytes_read += len(chunk)
        return data

    def readlines(self, hint: int = -1) -> Any:
        lines = self._file_obj.readlines(hint)
        for line in lines:
            chunk = self._to_bytes(line)
            self._hash.update(chunk)
            self._bytes_read += len(chunk)
        return lines

    def __next__(self) -> Any:
        try:
            line = self._file_obj.__next__()
            chunk = self._to_bytes(line)
            self._hash.update(chunk)
            self._bytes_read += len(chunk)
            return line
        except StopIteration:
            raise

    def __iter__(self) -> Any:
        return self

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        try:
            self._file_obj.close()
        finally:
            self._register_provenance()

    def _register_provenance(self) -> None:
        try:
            size = 0
            if self._path.exists():
                size = os.path.getsize(self._path)

            if "r" in self._mode and "w" not in self._mode and "a" not in self._mode:
                # Read-only: use the incrementally computed hash (avoids re-reading
                # the entire file just to get a hash we already have). PERF-07.
                sha = self._hash.hexdigest()
            elif self._path.exists():
                # Write/append mode: we didn't see all data go through our proxy
                # (e.g. the file may have been written by the underlying object),
                # so compute the hash from the final file on disk.
                h = hashlib.sha256()
                with builtins.open(self._path, "rb") as f:
                    for chunk in iter(lambda: f.read(65536), b""):
                        h.update(chunk)
                sha = h.hexdigest()
            else:
                sha = None

            if "r" in self._mode and "w" not in self._mode and "a" not in self._mode:
                record = {
                    "path": str(self._path.resolve()),
                    "size_bytes": size,
                    "sha256": sha or self._hash.hexdigest(),
                    "accessed_at_utc": time.time()
                }
                if not hasattr(self._run, "data_files"):
                    self._run.data_files = {"inputs": [], "outputs": []}
                self._run.data_files["inputs"].append(record)
                
                if getattr(self._run, "event_stream", None):
                    self._run.event_stream.emit("input_dataset", name=str(self._path.name), payload={"path": record["path"], "sha256": record["sha256"]})
            else:
                record = {
                    "path": str(self._path.resolve()),
                    "size_bytes": size,
                    "sha256": sha or self._hash.hexdigest(),
                    "modified_at_utc": time.time()
                }
                if not hasattr(self._run, "data_files"):
                    self._run.data_files = {"inputs": [], "outputs": []}
                self._run.data_files["outputs"].append(record)
                
                if getattr(self._run, "event_stream", None):
                    self._run.event_stream.emit("output_artifact", name=str(self._path.name), payload={"path": record["path"], "sha256": record["sha256"]})
        except Exception as e:
            logging.getLogger("pubrun").warning(f"pubrun: failed to register provenance for '{self._path}': {e}")

    def __enter__(self) -> "ProvenanceFileProxy":
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.close()

    def __getattr__(self, name: str) -> Any:
        return getattr(self._file_obj, name)


def open(file: Any, mode: str = "r", **kwargs: Any) -> Any:
    """Wrapper around Python's built-in open() that intercepts file reads and writes
    to catalog dataset provenance.
    """
    f_obj = builtins.open(file, mode, **kwargs)
    
    current_run = get_current_run()
    if current_run and current_run.is_active:
        try:
            f_path = Path(file)
            return ProvenanceFileProxy(f_obj, f_path, mode, current_run)
        except Exception as e:
            logging.getLogger("pubrun").warning(f"pubrun: failed to wrap file for provenance: {e}")
            
    return f_obj


class _PubrunSubprocessNamespace:
    """Explicit subprocess execution tracking wrappers."""
    @staticmethod
    def run(*args: Any, **kwargs: Any) -> _subprocess.CompletedProcess:
        cmd = args[0] if args else kwargs.get("args")
        if isinstance(cmd, list):
            cmd_args = [str(c) for c in cmd]
        else:
            cmd_args = [str(cmd)]
            
        started_at = time.time()
        
        from pubrun.capture.subprocesses import disable_spy
        with disable_spy():
            res = _subprocess.run(*args, **kwargs)
                
        ended_at = time.time()
        
        current_run = get_current_run()
        if current_run and current_run.is_active:
            record = {
                "argv": cmd_args,
                "exit_code": res.returncode,
                "started_at_utc": started_at,
                "ended_at_utc": ended_at,
                "pid": None
            }
            if not hasattr(current_run, "manual_subprocess_records"):
                current_run.manual_subprocess_records = []
            current_run.manual_subprocess_records.append(record)
            
        return res

    class Popen(_subprocess.Popen):
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            self._pubrun_cmd = args[0] if args else kwargs.get("args")
            self._pubrun_started_at = time.time()
            from pubrun.capture.subprocesses import disable_spy
            with disable_spy():
                super().__init__(*args, **kwargs)

        def _log_pubrun_record(self) -> None:
            if getattr(self, "_pubrun_logged", False):
                return
            self._pubrun_logged = True
            ended_at = time.time()
            current_run = get_current_run()
            if current_run and current_run.is_active:
                if isinstance(self._pubrun_cmd, list):
                    cmd_args = [str(c) for c in self._pubrun_cmd]
                else:
                    cmd_args = [str(self._pubrun_cmd)]
                record = {
                    "argv": cmd_args,
                    "exit_code": self.returncode,
                    "started_at_utc": self._pubrun_started_at,
                    "ended_at_utc": ended_at,
                    "pid": self.pid
                }
                if not hasattr(current_run, "manual_subprocess_records"):
                    current_run.manual_subprocess_records = []
                current_run.manual_subprocess_records.append(record)

        def wait(self, timeout: Optional[float] = None) -> int:
            res = super().wait(timeout)
            self._log_pubrun_record()
            return res

        def communicate(self, input: Any = None, timeout: Optional[float] = None) -> Any:
            res = super().communicate(input, timeout)
            self._log_pubrun_record()
            return res

        def poll(self) -> Optional[int]:
            res = super().poll()
            if res is not None:
                self._log_pubrun_record()
            return res


subprocess = _PubrunSubprocessNamespace()


def popen(cmd: str, mode: str = "r", bufsize: int = -1) -> Any:
    """Wrapper around os.popen that tracks execution provenance."""
    started_at = time.time()
    from pubrun.capture.subprocesses import disable_spy
    with disable_spy():
        pipe = os.popen(cmd, mode, bufsize)
    
    class _PopenPipeProxy:
        def __init__(self, pipe_obj: Any) -> None:
            self._pipe_obj = pipe_obj
            self._closed = False

        def close(self) -> Optional[int]:
            if self._closed:
                return None
            self._closed = True
            exit_status = self._pipe_obj.close()
            rc = 0
            if exit_status is not None:
                if sys.platform == "win32":
                    rc = exit_status
                else:
                    rc = os.WEXITSTATUS(exit_status) if os.WIFEXITED(exit_status) else exit_status
                    
            ended_at = time.time()
            current_run = get_current_run()
            if current_run and current_run.is_active:
                record = {
                    "argv": [cmd],
                    "exit_code": rc,
                    "started_at_utc": started_at,
                    "ended_at_utc": ended_at,
                    "pid": None
                }
                if not hasattr(current_run, "manual_subprocess_records"):
                    current_run.manual_subprocess_records = []
                current_run.manual_subprocess_records.append(record)
            return exit_status

        def __getattr__(self, name: str) -> Any:
            return getattr(self._pipe_obj, name)

        def __enter__(self) -> "_PopenPipeProxy":
            return self

        def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
            self.close()

    return _PopenPipeProxy(pipe)
