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
from typing import Any, Callable, Dict, Optional

from pubrun.tracker import Run, get_current_run


# -- Thread lock for ref_count safety ----------------------------------------
_run_lock = threading.Lock()


def _append_manual_subprocess_record(current_run: Any, record: dict) -> None:
    """Append a manual (pubrun.subprocess.*) subprocess record with a size cap.

    The SubprocessSpy has its own cap (max_tracked_commands); the manual
    wrappers previously had none, so a script calling pubrun.subprocess.run() in
    a tight loop grew the list without bound (OOM risk). Reuse the same
    configured cap here. (IPD 20260705 EC-09.)
    """
    if not hasattr(current_run, "manual_subprocess_records"):
        current_run.manual_subprocess_records = []
    records = current_run.manual_subprocess_records
    try:
        cap = int(
            current_run.config.get("capture", {})
            .get("subprocesses", {})
            .get("max_tracked_commands", 5000)
        )
    except Exception:
        cap = 5000
    if cap > 0 and len(records) >= cap:
        return  # cap reached; stop recording to bound memory
    records.append(record)


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
        The active ``Run`` instance. Useful attributes:

        - ``run.run_dir`` (Path): the directory where artifacts are written.
        - ``run.run_id`` (str): 8-char hex identifier for this run.
        - ``run.config`` (dict): the resolved configuration.
        - ``run.is_active`` (bool): whether the run is still collecting data.
        - ``run.started_at_utc`` (float): POSIX start timestamp.

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
    # BUG-04: Hold the lock across Run() construction to prevent two
    # concurrent threads from both seeing active=None and creating two Runs.
    with _run_lock:
        # Double-check: another thread may have created one while we waited.
        active = get_current_run()
        if active:
            active.ref_count = getattr(active, "ref_count", 0) + 1
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


class paused:
    """Context manager that suspends pubrun *recording* for a block.

    ::

        with pubrun.paused():
            call_something_noisy()   # runs and prints, but is NOT recorded

    Semantics (see IPD 20260705-scoped-pause-resume):

    - **Mute, not unpatch.** Output still goes to the real terminal and
      subprocesses still run; only the *recording* is suspended — the console
      tee stops writing to ``stdout.log``/``stderr.log`` and the subprocess spy
      stops recording spawned processes.
    - **Thread-local.** Only the calling thread's recording is suspended; other
      threads keep being captured. Passthrough to the terminal is process-global
      (there is one ``sys.stdout``), so output still appears for all threads.
    - **Ref-counted / nestable.** Nested ``paused()`` blocks (and any internal
      ``disable_spy`` spans) compose; recording resumes only when the outermost
      block exits. Resume is guaranteed even if the block raises.
    - **NOT paused:** ``annotate()``/``phase()`` events (your explicit markers
      still fire) and background resource sampling (RAM/CPU are process-wide and
      still counted).

    Safe to use in any import mode and with no active run (it is a no-op on the
    engines that are not installed). Never raises out of enter/exit.
    """

    def __enter__(self) -> "paused":
        try:
            from pubrun.capture.subprocesses import pause_spy
            pause_spy()
        except Exception:
            pass
        try:
            from pubrun.capture.console import pause_console
            pause_console()
        except Exception:
            pass
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        # Resume in reverse order; never let resume failures escape (golden rule).
        try:
            from pubrun.capture.console import resume_console
            resume_console()
        except Exception:
            pass
        try:
            from pubrun.capture.subprocesses import resume_spy
            resume_spy()
        except Exception:
            pass
        return None


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
        self._profiler = None

    def __enter__(self) -> "phase":
        if self.run_tracker and getattr(self.run_tracker, "event_stream", None):
            self.run_tracker.event_stream.emit("phase_start", name=self.name)
        else:
            _handle_inactive(f"pubrun.phase('{self.name}')")
        # Phase-scoped profiling (opt-in via [capture.profiling].enabled)
        self._started_yappi = False
        if self.run_tracker and self.run_tracker.is_active:
            prof_cfg = self.run_tracker.config.get("capture", {}).get("profiling", {})
            if prof_cfg.get("enabled", False):
                backend = prof_cfg.get("backend", "cprofile")
                try:
                    if backend == "cprofile":
                        import cProfile
                        self._profiler = cProfile.Profile()
                        self._profiler.enable()
                        # Track on Run for orphan cleanup (BUG2-04)
                        if not hasattr(self.run_tracker, "_active_profilers"):
                            self.run_tracker._active_profilers = []
                        self.run_tracker._active_profilers.append(self._profiler)
                    elif backend == "yappi":
                        import yappi  # type: ignore[import-not-found]
                        # BUG2-03: guard against concurrent/nested phases
                        if not getattr(phase, "_yappi_active", False):
                            yappi.start()
                            phase._yappi_active = True
                            self._started_yappi = True
                            self._profiler = "yappi"
                        else:
                            logging.getLogger("pubrun").warning(
                                "pubrun: yappi already active (nested/concurrent phase); "
                                f"skipping profiling for phase '{self.name}'"
                            )
                except Exception as prof_err:
                    logging.getLogger("pubrun").warning(
                        f"pubrun: profiling backend '{backend}' unavailable: {prof_err}"
                    )
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        # Stop profiler and dump stats
        if self._profiler and self.run_tracker and self.run_tracker.is_active:
            try:
                if self._profiler == "yappi" and self._started_yappi:
                    import yappi  # type: ignore[import-not-found]
                    yappi.stop()
                    phase._yappi_active = False
                    prof_path = self.run_tracker.run_dir / f"profile-{self.name}.prof"
                    stats = yappi.get_func_stats()
                    stats.save(str(prof_path), type="pstat")
                    yappi.clear_stats()
                elif self._profiler != "yappi":
                    # cProfile.Profile instance
                    self._profiler.disable()
                    prof_path = self.run_tracker.run_dir / f"profile-{self.name}.prof"
                    self._profiler.dump_stats(str(prof_path))
                    # Remove from active list
                    if hasattr(self.run_tracker, "_active_profilers"):
                        try:
                            self.run_tracker._active_profilers.remove(self._profiler)
                        except ValueError:
                            pass
                # Emit event so profile is discoverable
                if getattr(self.run_tracker, "event_stream", None):
                    self.run_tracker.event_stream.emit(
                        "profile_saved", name=self.name,
                        payload={"path": f"profile-{self.name}.prof"}
                    )
            except Exception as prof_err:
                logging.getLogger("pubrun").debug(f"pubrun: profiling save failed: {prof_err}")
            self._profiler = None

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
    # 1. Capture the printed string. Builtin print() accepts sep=None/end=None
    # as "use the default", so normalize before joining to avoid an
    # AttributeError on None.join(...). (IPD 20260705 EC-21.)
    sep = kwargs.get("sep")
    if sep is None:
        sep = " "
    end = kwargs.get("end")
    if end is None:
        end = "\n"
    try:
        msg = sep.join(map(str, args)) + end
    except Exception:
        # Never let provenance-side string building change the host's print
        # semantics; fall back to a best-effort representation.
        msg = " ".join(str(a) for a in args) + "\n"

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


# File-I/O provenance detail levels (see [capture.file_io].level). Progressive; each
# includes the ones before it. Ordered by cost (see docs/design evaluation): fstat on the
# open fd is ~free even on NFS, but realpath walks every path component (costly on NFS), so
# realpath sits ABOVE stat.
_FILE_IO_LEVELS = ("none", "name", "stat", "realpath", "hash")


def _file_io_level(run_instance: Any) -> str:
    """Resolve the effective [capture.file_io].level from the run's config (default 'stat')."""
    try:
        cfg = getattr(run_instance, "config", {}) or {}
        level = cfg.get("capture", {}).get("file_io", {}).get("level", "stat")
        return level if level in _FILE_IO_LEVELS else "stat"
    except Exception:
        return "stat"


class ProvenanceFileProxy:
    """Wraps a file stream opened via ``pubrun.open()`` to record file provenance at the
    configured detail level (name/stat/realpath/hash). Records at close().

    This is opt-in and per-file: it wraps ONLY files the user routes through
    ``pubrun.open()``. pubrun never patches the builtin ``open``.
    """
    def __init__(self, file_obj: Any, path: Path, mode: str, run_instance: Any,
                 level: str = "stat") -> None:
        self._file_obj = file_obj
        self._path = path
        self._mode = mode
        self._run = run_instance
        self._level = level if level in _FILE_IO_LEVELS else "stat"
        self._closed = False

    def _is_read_mode(self) -> bool:
        return "r" in self._mode and "w" not in self._mode and "a" not in self._mode

    def close(self) -> None:
        """Close the underlying file, then register provenance at the configured level.

        Recording after close() means write/append buffers are flushed to disk, and read
        hashes reflect the actual on-disk bytes (correct even for buffered/``readinto``
        reads that never pass through this proxy's methods).
        """
        if self._closed:
            return
        self._closed = True
        try:
            self._file_obj.close()
        finally:
            if self._level != "none":
                self._register_provenance()

    def _compute_hash_on_disk(self) -> Optional[str]:
        """sha256 of the file's on-disk bytes. This is the honest 'hash of the file' —
        independent of text/binary mode and of which read path the caller used."""
        try:
            if not self._path.exists():
                return None
            cap = 0
            try:
                cap = int(self._run.config.get("capture", {}).get("file_io", {}).get("max_hash_bytes", 0))
            except Exception:
                cap = 0
            size = os.path.getsize(self._path)
            if cap and size > cap:
                return None  # too large to hash under the configured cap
            h = hashlib.sha256()
            with builtins.open(self._path, "rb") as f:
                for chunk in iter(lambda: f.read(65536), b""):
                    h.update(chunk)
            return h.hexdigest()
        except Exception:
            return None

    def _register_provenance(self) -> None:
        try:
            level = self._level
            # L1 name: the path as given.
            record: Dict[str, Any] = {"path": str(self._path)}

            # L2 stat: fstat on the fd we hold (cheap even on NFS), + absolute path.
            if level in ("stat", "realpath", "hash"):
                record["path"] = os.path.abspath(str(self._path))
                try:
                    st = os.stat(self._path)  # file just closed; attrs cache-hot
                    record["size_bytes"] = st.st_size
                    record["mtime"] = st.st_mtime
                    record["ctime"] = st.st_ctime
                except OSError:
                    pass

            # L3 realpath: resolve symlinks (costlier on NFS — see docs).
            if level in ("realpath", "hash"):
                try:
                    record["realpath"] = os.path.realpath(str(self._path))
                except OSError:
                    pass

            # L4 hash: sha256 of on-disk bytes.
            record["sha256"] = self._compute_hash_on_disk() if level == "hash" else None

            if not hasattr(self._run, "data_files"):
                self._run.data_files = {"inputs": [], "outputs": []}

            if self._is_read_mode():
                record["accessed_at_utc"] = time.time()
                self._run.data_files["inputs"].append(record)
                event = "input_dataset"
            else:
                record["modified_at_utc"] = time.time()
                self._run.data_files["outputs"].append(record)
                event = "output_artifact"

            if getattr(self._run, "event_stream", None):
                self._run.event_stream.emit(
                    event, name=str(self._path.name),
                    payload={"path": record["path"], "sha256": record.get("sha256")})
        except Exception as e:
            logging.getLogger("pubrun").warning(f"pubrun: failed to register provenance for '{self._path}': {e}")

    def __enter__(self) -> "ProvenanceFileProxy":
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.close()

    def __iter__(self) -> Any:
        return iter(self._file_obj)

    def __getattr__(self, name: str) -> Any:
        # Everything not overridden (read/write/readinto/seek/fileno/...) goes straight to
        # the real file object, so behavior is identical to the builtin.
        return getattr(self._file_obj, name)


def open(file: Any, mode: str = "r", **kwargs: Any) -> Any:
    """Drop-in wrapper around the built-in ``open()`` that records file provenance for
    a run at the configured ``[capture.file_io].level`` (default ``stat``: path + size +
    mtime/ctime, no content hashing). Set the level to ``hash`` for content hashes, or
    ``none`` to behave exactly like the builtin. pubrun never patches the global ``open``;
    this only affects files you open via ``pubrun.open()``.
    """
    f_obj = builtins.open(file, mode, **kwargs)

    current_run = get_current_run()
    if current_run and current_run.is_active:
        try:
            level = _file_io_level(current_run)
            if level != "none":
                return ProvenanceFileProxy(f_obj, Path(file), mode, current_run, level=level)
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
        try:
            with disable_spy():
                res = _subprocess.run(*args, **kwargs)
        except Exception as exc:
            # Record the failed invocation for provenance (parity with the
            # SubprocessSpy, which logs failures), then re-raise unchanged so
            # host semantics are untouched. (IPD 20260705 EC-25.)
            current_run = get_current_run()
            if current_run and current_run.is_active:
                _append_manual_subprocess_record(current_run, {
                    "argv": cmd_args,
                    "exit_code": None,
                    "started_at_utc": started_at,
                    "ended_at_utc": time.time(),
                    "pid": None,
                    "error": f"{type(exc).__name__}: {exc}",
                })
            raise

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
            _append_manual_subprocess_record(current_run, record)

        return res

    class Popen(_subprocess.Popen):
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            self._pubrun_cmd = args[0] if args else kwargs.get("args")
            self._pubrun_started_at = time.time()
            self._pubrun_log_lock = threading.Lock()
            self._pubrun_logged = False
            from pubrun.capture.subprocesses import disable_spy
            with disable_spy():
                super().__init__(*args, **kwargs)

        def _log_pubrun_record(self) -> None:
            # Atomically claim the single log slot so concurrent wait()/poll()
            # from two threads cannot double-append. (IPD 20260705 EC-24.)
            lock = getattr(self, "_pubrun_log_lock", None)
            if lock is not None:
                with lock:
                    if self._pubrun_logged:
                        return
                    self._pubrun_logged = True
            else:
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
                _append_manual_subprocess_record(current_run, record)

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
                _append_manual_subprocess_record(current_run, record)
            return exit_status

        def __getattr__(self, name: str) -> Any:
            return getattr(self._pipe_obj, name)

        def __enter__(self) -> "_PopenPipeProxy":
            return self

        def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
            self.close()

    return _PopenPipeProxy(pipe)
