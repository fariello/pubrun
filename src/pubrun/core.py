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
import time
from typing import Any, Callable, Dict, Optional

from pubrun.tracker import Run, get_current_run


# -- Thread locks for ref_count and Run construction safety ------------------
_run_lock = threading.RLock()
_start_lock = threading.Lock()


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

# Cache for the [events].on_inactive_annotate policy used by _handle_inactive.
# Each memo is replaced by assigning one new tuple, so a concurrent reader sees
# either the old pair or the new pair, never a mix.
_INACTIVE_POLICY_CACHE: Optional[tuple] = None  # (signature, policy)
_USER_CONFIG_PATH_MEMO: Optional[tuple] = None  # (key, user config path)
_LOCAL_CONFIG_PATHS_MEMO: Optional[tuple] = None  # (cwd, deep path, root path)

# Every environment input of get_global_config_dir(), including the variables
# os.path.expanduser reads on Windows.
_USER_CONFIG_ENV_VARS = (
    "APPDATA", "XDG_CONFIG_HOME", "HOME", "USERPROFILE", "HOMEDRIVE", "HOMEPATH",
)


def _stat_identity(path: str) -> Optional[tuple]:
    """Return (st_ino, st_size, st_mtime_ns) for path, or None if it cannot be stat'ed."""
    try:
        st = os.stat(path)
    except OSError:
        return None
    return (st.st_ino, st.st_size, st.st_mtime_ns)


def _inactive_policy() -> str:
    """Return the [events].on_inactive_annotate policy, resolving the config only on change.

    The full configuration is resolved again only when the configuration
    signature changes: the resolver or loader functions, the user config path
    or its stat identity, the working directory, or the stat identity of either
    local config file. PUBRUN_PROFILE and PUBRUN_META_REF only set [core] keys,
    so they are not part of the signature.
    """
    global _INACTIVE_POLICY_CACHE, _USER_CONFIG_PATH_MEMO, _LOCAL_CONFIG_PATHS_MEMO
    from pathlib import Path
    from pubrun import config as _config

    environ = os.environ
    get_dir = _config.get_global_config_dir
    user_key = (sys.platform, get_dir) + tuple(environ.get(n) for n in _USER_CONFIG_ENV_VARS)
    user_memo = _USER_CONFIG_PATH_MEMO
    if user_memo is None or user_memo[0] != user_key:
        user_memo = (user_key, str(get_dir() / "config.toml"))
        _USER_CONFIG_PATH_MEMO = user_memo
    user_path = user_memo[1]

    cwd = Path.cwd()
    local_memo = _LOCAL_CONFIG_PATHS_MEMO
    if local_memo is None or local_memo[0] != cwd:
        cwd_str = str(cwd)
        local_memo = (
            cwd,
            os.path.join(cwd_str, ".config", "pubrun", "config.toml"),
            os.path.join(cwd_str, ".pubrun.toml"),
        )
        _LOCAL_CONFIG_PATHS_MEMO = local_memo

    resolver = _config.resolve_config
    signature = (
        resolver,
        _config.load_user_config,
        _config.load_local_config,
        user_path,
        _stat_identity(user_path),
        cwd,
        _stat_identity(local_memo[1]),
        _stat_identity(local_memo[2]),
    )
    cached = _INACTIVE_POLICY_CACHE
    if cached is not None and cached[0] == signature:
        return cached[1]

    policy = resolver().get("events", {}).get("on_inactive_annotate", "ignore")
    _INACTIVE_POLICY_CACHE = (signature, policy)
    return policy


def _handle_inactive(context: str) -> None:
    """Check the on_inactive_annotate policy and raise/warn/ignore accordingly.

    Called when annotate() or phase() is used with no active run.

    Args:
        context: Human-readable label for the error/warning message
            (e.g. "pubrun.annotate()" or "pubrun.phase('training')").
    """
    action = _inactive_policy()
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
    event_stream = getattr(current_run, "event_stream", None) if current_run else None
    if event_stream:
        payload = kwargs.copy()
        event_stream.emit("annotation", name=message, payload=payload)
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
    is_ghost_or_inactive = False
    with _run_lock:
        active = get_current_run()
        if active:
            active.ref_count = getattr(active, "ref_count", 0) + 1
            is_ghost_or_inactive = (
                getattr(active, "_outcome", None) == "ghost"
                or not getattr(active, "is_active", False)
            )
    if active:
        if not is_ghost_or_inactive and hasattr(active, "_merge_and_migrate"):
            active._merge_and_migrate(kwargs)
        return active
    # BUG-04: Serialize Run() construction with _start_lock so two concurrent
    # threads never create two Runs, while keeping _run_lock free for rollback
    # and background hardware thread coordination inside Run.__init__().
    with _start_lock:
        with _run_lock:
            active = get_current_run()
            if active:
                active.ref_count = getattr(active, "ref_count", 0) + 1
                is_ghost_or_inactive = (
                    getattr(active, "_outcome", None) == "ghost"
                    or not getattr(active, "is_active", False)
                )
        if active:
            if not is_ghost_or_inactive and hasattr(active, "_merge_and_migrate"):
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
            Defaults to the ``[diff].ignore_standard`` config list (or a
            legacy ``[diff].ignore`` list when ``ignore_standard`` is absent).

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
        diff_conf = resolve_config().get("diff", {})
        if "ignore_standard" in diff_conf:
            ignores = diff_conf.get("ignore_standard") or []
        else:
            ignores = diff_conf.get("ignore", [])

    return compare_manifests(manifest_a, manifest_b, ignores)


def _classify_exit_outcome(exc: Optional[BaseException]) -> str:
    """Map an exception leaving a tracked scope to a run outcome.

    ``None`` and ``SystemExit`` with code ``None`` or ``0`` are ``"completed"``;
    ``KeyboardInterrupt`` is ``"interrupted"``; anything else is ``"failed"``.
    ``SystemExit(True)`` exits with status 1, so it is ``"failed"``.
    """
    if exc is None:
        return "completed"
    if isinstance(exc, KeyboardInterrupt):
        return "interrupted"
    if isinstance(exc, SystemExit):
        code = exc.code
        if code is None or (isinstance(code, int) and code == 0):
            return "completed"
        return "failed"
    return "failed"


def _stop_for_exit(run_tracker: Any, exc: Optional[BaseException]) -> None:
    """Stop ``run_tracker`` with the outcome implied by ``exc``.

    A ``SystemExit`` leaving the scope also records its exit code on the
    run's signal capture so the manifest reports the code the process used.
    """
    if isinstance(exc, SystemExit):
        sig_cap = getattr(run_tracker, "signal_capture", None)
        if sig_cap is not None and getattr(sig_cap, "_active", False):
            try:
                from pubrun.capture.signals import _exit_details
                code, detail = _exit_details(exc, getattr(sig_cap, "_config", None))
                sig_cap._set_exit(code, detail, "SystemExit")
            except Exception:
                pass
    run_tracker.stop(outcome=_classify_exit_outcome(exc))


def audit_run(func: Optional[Callable] = None, **kwargs: Any) -> Callable:
    """Decorator that wraps a function in a pubrun tracking session.

    Starts a run before the function executes and stops it afterward.
    If the function raises, the outcome is set to ``"failed"`` (or
    ``"interrupted"`` for ``KeyboardInterrupt``, ``"completed"`` for
    ``SystemExit`` with code 0 or ``None``) and the exception is re-raised.

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
        except BaseException as exc:
            _stop_for_exit(run_tracker, exc)
            raise
        _stop_for_exit(run_tracker, None)
        return result

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
            if exc_type is not None and exc_val is None:
                try:
                    exc_val = exc_type()
                except Exception:
                    exc_val = Exception()
            _stop_for_exit(self.run_tracker, exc_val if exc_type is not None else None)


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
    _yappi_active: bool = False

    def __init__(self, name: str) -> None:
        self.name = name
        self.run_tracker: Optional[Run] = None
        self._profiler: Any = None
        self._started_yappi = False
        self._start_mono: Optional[float] = None

    def __enter__(self) -> "phase":
        # Bind at entry, not construction, so a phase object created before
        # start() (or reused across runs) logs to the run active when it runs.
        self.run_tracker = get_current_run()
        event_stream = getattr(self.run_tracker, "event_stream", None) if self.run_tracker else None
        if event_stream:
            event_stream.emit("phase_start", name=self.name)
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
                    else:
                        raise ValueError("unknown backend")
                except Exception as prof_err:
                    logging.getLogger("pubrun").warning(
                        f"pubrun: profiling backend '{backend}' unavailable: {prof_err}"
                    )
        self._start_mono = time.perf_counter()
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        end_mono = time.perf_counter()
        prof_name = f"profile-{_safe_phase_filename(self.name)}.prof"
        if self._profiler == "yappi" and self._started_yappi:
            # Always stop yappi and release the class-wide latch, even when the
            # run stopped inside the phase, so later phases can profile again.
            yappi_mod: Any = None
            try:
                import yappi as _yappi_imported  # type: ignore[import-not-found]
                yappi_mod = _yappi_imported
                yappi_mod.stop()
            except Exception as prof_err:
                logging.getLogger("pubrun").debug(f"pubrun: yappi stop failed: {prof_err}")
            finally:
                phase._yappi_active = False
                self._started_yappi = False
            try:
                if yappi_mod is not None and self.run_tracker and self.run_tracker.is_active:
                    prof_path = self.run_tracker.run_dir / prof_name
                    stats = yappi_mod.get_func_stats()
                    stats.save(str(prof_path), type="pstat")
                    self._emit_profile_saved(prof_name)
            except Exception as prof_err:
                logging.getLogger("pubrun").debug(f"pubrun: profiling save failed: {prof_err}")
            finally:
                try:
                    if yappi_mod is not None:
                        yappi_mod.clear_stats()
                except Exception:
                    pass
            self._profiler = None
        elif self._profiler and self._profiler != "yappi":
            try:
                # cProfile.Profile instance
                self._profiler.disable()
                if self.run_tracker and self.run_tracker.is_active:
                    prof_path = self.run_tracker.run_dir / prof_name
                    self._profiler.dump_stats(str(prof_path))
                    self._emit_profile_saved(prof_name)
            except Exception as prof_err:
                logging.getLogger("pubrun").debug(f"pubrun: profiling save failed: {prof_err}")
            finally:
                if self.run_tracker is not None and hasattr(self.run_tracker, "_active_profilers"):
                    try:
                        self.run_tracker._active_profilers.remove(self._profiler)
                    except ValueError:
                        pass
            self._profiler = None

        end_stream = getattr(self.run_tracker, "event_stream", None) if self.run_tracker else None
        if end_stream:
            end_payload: Dict[str, Any] = {}
            if self._start_mono is not None:
                end_payload["elapsed_seconds"] = max(0.0, end_mono - self._start_mono)
                end_payload["duration_clock"] = "monotonic"
            if exc_type is not None:
                end_payload["error"] = (
                    exc_val.__class__.__name__ if exc_val is not None else exc_type.__name__
                )
            end_stream.emit(
                "phase_end",
                name=self.name,
                payload=end_payload if end_payload else None,
            )

    def _emit_profile_saved(self, prof_name: str) -> None:
        """Emit a ``profile_saved`` event so the saved profile is discoverable."""
        event_stream = getattr(self.run_tracker, "event_stream", None)
        if event_stream:
            event_stream.emit(
                "profile_saved", name=self.name, payload={"path": prof_name}
            )


def _safe_phase_filename(name: Any) -> str:
    """Reduce a phase name to a single safe filename component.

    Every character outside ``[A-Za-z0-9_-]`` becomes ``_``, which removes path
    separators, drive colons, and dots (so ``..`` cannot survive). A name with
    no usable characters falls back to ``"phase"``.
    """
    import re
    safe = re.sub(r"[^A-Za-z0-9_-]", "_", str(name))
    if not safe.strip("_"):
        return "phase"
    return safe


# -- Boot sequence ------------------------------------------------------------

_PUBRUN_CLI_SCRIPTS = ("pubrun", "pubrun.exe", "pbr", "pbr.exe")


def _is_pubrun_module_name(name: Any) -> bool:
    return isinstance(name, str) and (name == "pubrun" or name.startswith("pubrun."))


def _is_pubrun_cli_invocation() -> bool:
    """Return True when this process is pubrun's own command-line interface.

    Covers the console scripts, an already-imported ``pubrun.__main__``, a
    ``__main__`` module whose spec names pubrun, and ``python -m pubrun``
    while runpy is still importing the package (``sys.argv[0]`` is ``"-m"``
    and ``pubrun.__main__`` has not loaded yet). ``python -m <user_pkg>`` is
    not a pubrun invocation, so user packages still auto-start.
    """
    try:
        sys0 = os.path.basename(sys.argv[0]) if sys.argv else ""
    except Exception:
        sys0 = ""
    if sys0 in _PUBRUN_CLI_SCRIPTS:
        return True
    if "pubrun.__main__" in sys.modules:
        return True
    main_mod = sys.modules.get("__main__")
    spec = getattr(main_mod, "__spec__", None)
    if spec is not None and getattr(spec, "name", None) in ("pubrun", "pubrun.__main__"):
        return True
    if sys0 == "-m":
        try:
            frame: Any = sys._getframe(1)
        except Exception:
            frame = None
        while frame is not None:
            # Match on the module name: runpy may be frozen ("<frozen runpy>").
            if frame.f_globals.get("__name__") == "runpy":
                if _is_pubrun_module_name(frame.f_locals.get("mod_name")):
                    return True
            frame = frame.f_back
    return False


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
        if _is_pubrun_cli_invocation():
            return

        try:
            start()
        except Exception as start_err:
            logging.getLogger("pubrun").warning(
                f"pubrun auto-start failed (tracking disabled): {start_err}"
            )


# -- Explicit Tracking API (Phases 1-4) --------------------------------------

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


def _should_log_pubrun_print(run: Any, target: Any) -> bool:
    """Return True when a ``pubrun.print`` call should be appended to ``stdout.log``.

    Skips output sent to a stream other than stdout, output made inside
    ``pubrun.paused()``, and output that the run's own console tee on
    ``sys.stdout`` already records (logging it here too would duplicate it).
    """
    if target is not None and target is not sys.stdout:
        return False
    try:
        from pubrun.capture.console import _tee_paused
        if _tee_paused():
            return False
    except Exception:
        pass
    interceptor = getattr(run, "console_interceptor", None)
    tee = getattr(interceptor, "stdout_tee", None)
    if tee is not None and sys.stdout is tee and getattr(tee, "log_file", None) is not None:
        return False
    return True


def print(*args: Any, **kwargs: Any) -> None:
    """Drop-in print replacement that logs to stdout.log in the active run directory.

    Respects all standard print arguments (sep, end, file, flush). Output sent
    to another stream with ``file=``, output inside ``pubrun.paused()``, and
    output already recorded by active console capture is not logged again.
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
    if run and run.is_active and _should_log_pubrun_print(run, kwargs.get("file")):
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
_VALID_FILE_ROLES = ("input", "output", "input_output")


def _file_io_level(run_instance: Any) -> str:
    """Resolve the effective [capture.file_io].level from the run's config (default 'stat')."""
    try:
        cfg = getattr(run_instance, "config", {}) or {}
        level = cfg.get("capture", {}).get("file_io", {}).get("level", "stat")
        return level if level in _FILE_IO_LEVELS else "stat"
    except Exception:
        return "stat"


def _validate_file_registration_args(
    path: Any,
    role: Any,
    level: Any,
    digest: Any,
    digest_algorithm: Any,
    verify_digest: Any,
    metadata: Any,
    *,
    label: Any = None,
) -> None:
    """Validate programmer-error arguments early without importing file_io."""
    import json

    raw_path = os.fspath(path)
    if isinstance(raw_path, bytes):
        path_str = os.fsdecode(raw_path)
    elif isinstance(raw_path, str):
        path_str = raw_path
    else:
        raise TypeError("path must be a string or os.PathLike")
    if not path_str or not path_str.strip():
        raise ValueError("path must be a non-empty string or os.PathLike")

    if not isinstance(role, str) or role not in _VALID_FILE_ROLES:
        raise ValueError(
            f"invalid role {role!r}; expected one of {', '.join(_VALID_FILE_ROLES)}"
        )

    if label is not None and not isinstance(label, str):
        raise TypeError("label must be a string or None")

    if level is not None:
        if not isinstance(level, str) or level not in _FILE_IO_LEVELS:
            raise ValueError(
                f"invalid level {level!r}; expected one of {', '.join(_FILE_IO_LEVELS)}"
            )

    digest_val: Optional[str] = None
    if digest is not None:
        if not isinstance(digest, str) or not digest.strip():
            raise ValueError("digest must be a non-empty string when provided")
        digest_val = digest.strip()

    if not isinstance(digest_algorithm, str) or not digest_algorithm.strip():
        raise ValueError("digest_algorithm must be a non-empty string")

    if bool(verify_digest) and digest_val is None:
        raise ValueError("verify_digest=True requires a non-empty digest")

    if metadata is not None:
        if not isinstance(metadata, dict):
            raise ValueError("metadata must be a dict or None")
        json.dumps(metadata, allow_nan=False)


def register_file(
    path: Any,
    role: str = "input",
    *,
    label: Optional[str] = None,
    digest: Optional[str] = None,
    digest_algorithm: str = "sha256",
    level: Optional[str] = None,
    verify_digest: bool = False,
    defer: bool = False,
    metadata: Optional[Dict[str, Any]] = None,
) -> Optional[Dict[str, Any]]:
    """Register an external input, output, or mixed-role file path with the active run.

    Designed for workflows using external I/O libraries (such as pandas, PyArrow,
    NumPy, or C extensions) without replacing their readers or writers. Does not
    patch ``builtins.open``.

    Args:
        path: Local file path (``str`` or ``os.PathLike``). Remote URIs are
            recorded honestly as out-of-scope without network access.
        role: File role (``"input"``, ``"output"``, or ``"input_output"``).
        label: Optional logical label (for example ``"training_data"``).
        digest: Optional caller-supplied digest value. Recorded as asserted
            evidence unless ``verify_digest=True`` is requested.
        digest_algorithm: Digest algorithm name (default ``"sha256"``).
        level: Optional per-call override for ``[capture.file_io].level``.
        verify_digest: If True, verify ``digest`` against on-disk bytes.
        defer: If True on an output or mixed role, defer inspection until
            a post-creation registration call or run finalization.
        metadata: Optional JSON-serializable dict of extra file metadata.

    Returns:
        The recorded provenance dict, or ``None`` when no run is active or
        the effective detail level is ``"none"``.
    """
    _validate_file_registration_args(
        path,
        role,
        level,
        digest,
        digest_algorithm,
        verify_digest,
        metadata,
        label=label,
    )
    run = get_current_run()
    if not run or not run.is_active:
        _handle_inactive("pubrun.register_file()")
        return None
    from pubrun.capture.file_io import register_file_provenance

    return register_file_provenance(
        run,
        path,
        role=role,
        label=label,
        digest=digest,
        digest_algorithm=digest_algorithm,
        level=level,
        verify_digest=verify_digest,
        defer=defer,
        metadata=metadata,
        registration_source="register_file",
    )


def register_input(
    path: Any,
    *,
    label: Optional[str] = None,
    digest: Optional[str] = None,
    digest_algorithm: str = "sha256",
    level: Optional[str] = None,
    verify_digest: bool = False,
    metadata: Optional[Dict[str, Any]] = None,
) -> Optional[Dict[str, Any]]:
    """Register an external input dataset path with the active run.

    Convenience wrapper around ``register_file(path, role="input", ...)``.
    """
    _validate_file_registration_args(
        path,
        "input",
        level,
        digest,
        digest_algorithm,
        verify_digest,
        metadata,
        label=label,
    )
    run = get_current_run()
    if not run or not run.is_active:
        _handle_inactive("pubrun.register_input()")
        return None
    from pubrun.capture.file_io import register_file_provenance

    return register_file_provenance(
        run,
        path,
        role="input",
        label=label,
        digest=digest,
        digest_algorithm=digest_algorithm,
        level=level,
        verify_digest=verify_digest,
        defer=False,
        metadata=metadata,
        registration_source="register_input",
    )


def register_output(
    path: Any,
    *,
    label: Optional[str] = None,
    digest: Optional[str] = None,
    digest_algorithm: str = "sha256",
    level: Optional[str] = None,
    verify_digest: bool = False,
    defer: bool = False,
    metadata: Optional[Dict[str, Any]] = None,
) -> Optional[Dict[str, Any]]:
    """Register an external output file path with the active run.

    Supports both pre-creation registration (automatic when missing or explicit
    via ``defer=True``) and post-creation registration. Convenience wrapper
    around ``register_file(path, role="output", ...)``.
    """
    _validate_file_registration_args(
        path,
        "output",
        level,
        digest,
        digest_algorithm,
        verify_digest,
        metadata,
        label=label,
    )
    run = get_current_run()
    if not run or not run.is_active:
        _handle_inactive("pubrun.register_output()")
        return None
    from pubrun.capture.file_io import register_file_provenance

    return register_file_provenance(
        run,
        path,
        role="output",
        label=label,
        digest=digest,
        digest_algorithm=digest_algorithm,
        level=level,
        verify_digest=verify_digest,
        defer=defer,
        metadata=metadata,
        registration_source="register_output",
    )


def open(file: Any, mode: str = "r", **kwargs: Any) -> Any:
    """Drop-in wrapper around the built-in ``open()`` that records file provenance for
    a run at the configured ``[capture.file_io].level`` (default ``stat``: path + size +
    mtime/ctime, no content hashing). Set the level to ``hash`` for content hashes, or
    ``none`` to behave exactly like the builtin. pubrun never patches the global ``open``;
    this only affects files you open via ``pubrun.open()``.
    """
    f_obj = builtins.open(file, mode, **kwargs)

    if isinstance(file, int):
        return f_obj

    current_run = get_current_run()
    if current_run and current_run.is_active:
        try:
            level = _file_io_level(current_run)
            if level != "none":
                path_val = os.fspath(file)
                if isinstance(path_val, bytes):
                    path_val = os.fsdecode(path_val)
                from pubrun.capture.file_io import ProvenanceFileProxy
                return ProvenanceFileProxy(
                    f_obj, Path(path_val), mode, current_run, level=level
                )
        except Exception as e:
            logging.getLogger("pubrun").warning(f"pubrun: failed to wrap file for provenance: {e}")

    return f_obj


def __getattr__(name: str) -> Any:
    """PEP 562 lazy attribute lookup to avoid importing file_io on cold import."""
    if name == "ProvenanceFileProxy":
        from pubrun.capture.file_io import ProvenanceFileProxy
        return ProvenanceFileProxy
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def _manual_argv(cmd: Any, current_run: Any) -> list:
    """Split ``cmd`` like the SubprocessSpy does and redact secret arguments."""
    from pubrun.capture.subprocesses import SubprocessSpy
    argv = SubprocessSpy._safe_shlex_split(cmd)
    try:
        from pubrun.capture.redaction import redact_argv
        return redact_argv(argv, getattr(current_run, "config", None))
    except Exception:
        # Never store unredacted arguments when redaction itself fails.
        return ["[REDACTED]" for _ in argv]


def _manual_error_detail(exc: BaseException, current_run: Any) -> str:
    """Return a single-line, redacted description of a subprocess failure.

    ``CalledProcessError`` and ``TimeoutExpired`` embed the raw command in
    their message, so a copy carrying the redacted argv is formatted instead.
    """
    import copy as _copy
    from pubrun.capture.redaction import format_safe_error_detail
    config = getattr(current_run, "config", None)
    target: BaseException = exc
    if isinstance(exc, _subprocess.SubprocessError) and getattr(exc, "cmd", None) is not None:
        try:
            target = _copy.copy(exc)
            target.cmd = _manual_argv(exc.cmd, current_run)  # type: ignore[attr-defined]
        except Exception:
            return type(exc).__name__
    return format_safe_error_detail(target, config)


class _PubrunSubprocessNamespace:
    """Explicit subprocess execution tracking wrappers."""
    @staticmethod
    def run(*args: Any, **kwargs: Any) -> _subprocess.CompletedProcess:
        cmd = args[0] if args else kwargs.get("args")

        started_at = time.time()
        start_mono = time.perf_counter()

        from pubrun.capture.subprocesses import disable_spy
        try:
            with disable_spy():
                res = _subprocess.run(*args, **kwargs)
        except Exception as exc:
            # Record the failed invocation for provenance (parity with the
            # SubprocessSpy, which logs failures), then re-raise unchanged so
            # host semantics are untouched. (IPD 20260705 EC-25.)
            ended_at = time.time()
            elapsed = max(0.0, time.perf_counter() - start_mono)
            current_run = get_current_run()
            if current_run and current_run.is_active:
                err_detail = _manual_error_detail(exc, current_run)
                _append_manual_subprocess_record(current_run, {
                    "argv": _manual_argv(cmd, current_run),
                    "exit_code": getattr(exc, "returncode", None),
                    "started_at_utc": started_at,
                    "ended_at_utc": ended_at,
                    "elapsed_seconds": elapsed,
                    "duration_clock": "monotonic",
                    "pid": None,
                    "error": err_detail,
                    "capture_state": {"status": "failed", "detail": err_detail},
                })
            raise

        ended_at = time.time()
        elapsed = max(0.0, time.perf_counter() - start_mono)

        current_run = get_current_run()
        if current_run and current_run.is_active:
            record = {
                "argv": _manual_argv(cmd, current_run),
                "exit_code": res.returncode,
                "started_at_utc": started_at,
                "ended_at_utc": ended_at,
                "elapsed_seconds": elapsed,
                "duration_clock": "monotonic",
                "pid": None,
                "capture_state": {
                    "status": "complete" if res.returncode == 0 else "failed"
                },
            }
            _append_manual_subprocess_record(current_run, record)

        return res

    class Popen(_subprocess.Popen):
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            self._pubrun_cmd = args[0] if args else kwargs.get("args")
            self._pubrun_started_at = time.time()
            self._pubrun_start_mono = time.perf_counter()
            self._pubrun_log_lock = threading.Lock()
            self._pubrun_logged = False
            from pubrun.capture.subprocesses import disable_spy
            try:
                with disable_spy():
                    super().__init__(*args, **kwargs)
            except Exception as exc:
                ended_at = time.time()
                elapsed = max(0.0, time.perf_counter() - self._pubrun_start_mono)
                current_run = get_current_run()
                if current_run and current_run.is_active:
                    err_detail = _manual_error_detail(exc, current_run)
                    _append_manual_subprocess_record(current_run, {
                        "argv": _manual_argv(self._pubrun_cmd, current_run),
                        "exit_code": getattr(exc, "returncode", None),
                        "started_at_utc": self._pubrun_started_at,
                        "ended_at_utc": ended_at,
                        "elapsed_seconds": elapsed,
                        "duration_clock": "monotonic",
                        "pid": None,
                        "error": err_detail,
                        "capture_state": {"status": "failed", "detail": err_detail},
                    })
                raise

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
            end_mono = time.perf_counter()
            start_mono = getattr(self, "_pubrun_start_mono", None)
            current_run = get_current_run()
            if current_run and current_run.is_active:
                record: Dict[str, Any] = {
                    "argv": _manual_argv(self._pubrun_cmd, current_run),
                    "exit_code": self.returncode,
                    "started_at_utc": self._pubrun_started_at,
                    "ended_at_utc": ended_at,
                    "pid": self.pid,
                    "capture_state": {
                        "status": "complete" if self.returncode == 0 else "failed"
                    },
                }
                if start_mono is not None:
                    record["elapsed_seconds"] = max(0.0, end_mono - start_mono)
                    record["duration_clock"] = "monotonic"
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
    start_mono = time.perf_counter()
    from pubrun.capture.subprocesses import disable_spy
    try:
        with disable_spy():
            pipe = os.popen(cmd, mode, bufsize)
    except Exception as exc:
        ended_at = time.time()
        elapsed = max(0.0, time.perf_counter() - start_mono)
        current_run = get_current_run()
        if current_run and current_run.is_active:
            err_detail = _manual_error_detail(exc, current_run)
            _append_manual_subprocess_record(current_run, {
                "argv": _manual_argv(cmd, current_run),
                "exit_code": getattr(exc, "returncode", None),
                "started_at_utc": started_at,
                "ended_at_utc": ended_at,
                "elapsed_seconds": elapsed,
                "duration_clock": "monotonic",
                "pid": None,
                "error": err_detail,
                "capture_state": {"status": "failed", "detail": err_detail},
            })
        raise

    class _PopenPipeProxy:
        def __init__(self, pipe_obj: Any) -> None:
            self._pipe_obj = pipe_obj
            self._closed = False

        def close(self) -> Optional[int]:
            if self._closed:
                return None
            self._closed = True
            exit_status = self._pipe_obj.close()
            ended_at = time.time()
            end_mono = time.perf_counter()
            rc = 0
            if exit_status is not None:
                if sys.platform == "win32":
                    rc = exit_status
                else:
                    rc = os.WEXITSTATUS(exit_status) if os.WIFEXITED(exit_status) else exit_status

            current_run = get_current_run()
            if current_run and current_run.is_active:
                record = {
                    "argv": _manual_argv(cmd, current_run),
                    "exit_code": rc,
                    "started_at_utc": started_at,
                    "ended_at_utc": ended_at,
                    "elapsed_seconds": max(0.0, end_mono - start_mono),
                    "duration_clock": "monotonic",
                    "pid": None,
                    "capture_state": {
                        "status": "complete" if rc == 0 else "failed"
                    },
                }
                _append_manual_subprocess_record(current_run, record)
            return exit_status

        def __getattr__(self, name: str) -> Any:
            return getattr(self._pipe_obj, name)

        # Dunder lookups bypass __getattr__, so iteration must be explicit.
        def __iter__(self) -> "_PopenPipeProxy":
            return self

        def __next__(self) -> Any:
            # os.popen's _wrap_close defines __iter__ but not __next__.
            it = self.__dict__.get("_line_iter")
            if it is None:
                it = iter(self._pipe_obj)
                self._line_iter = it
            return next(it)

        def __enter__(self) -> "_PopenPipeProxy":
            return self

        def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
            self.close()

    return _PopenPipeProxy(pipe)
