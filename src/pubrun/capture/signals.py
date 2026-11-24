"""
Signal and exit-code capture for pubrun.

Design principles:
    1. **Chain, don't replace** -- Every installed handler saves the previous
       handler and invokes it after recording.  If the importing script had
       its own SIGINT handler, pubrun calls it unchanged.
    2. **Record, don't suppress** -- Signals are logged with timestamp and
       signal number/name; the original behavior (raise KeyboardInterrupt,
       terminate, etc.) proceeds normally.
    3. **Exit code capture** -- A thin wrapper around sys.excepthook captures
       SystemExit codes; atexit captures clean exits (code 0).  The process
       still exits with the same code the user's script intended.
    4. **Platform-safe** -- Only registers handlers for signals that exist on
       the current OS (e.g. SIGHUP is unavailable on Windows).
"""
import os
import signal
import sys
import time
import threading
from contextlib import contextmanager
from typing import Any, Callable, Dict, Iterator, List, Optional, Set, Tuple


# Signals we attempt to intercept (subset of catchable, meaningful signals).
# We intentionally omit SIGKILL/SIGSTOP (uncatchable) and obscure signals.
_TARGET_SIGNALS: List[str] = [
    "SIGINT",    # Ctrl+C -> KeyboardInterrupt
    "SIGTERM",   # Polite kill
    "SIGHUP",    # Terminal hangup (Unix only)
    "SIGPIPE",   # Broken pipe (Unix only) — downstream reader closed
    "SIGUSR1",   # User-defined (Unix only)
    "SIGUSR2",   # User-defined (Unix only)
    "SIGBREAK",  # Ctrl+Break on Windows
]

# Signals that will kill the process when delivered with SIG_DFL disposition.
# For these, we must finalize the run before re-delivering.
_LETHAL_SIGNALS: set = set()
for _sig_name in ("SIGTERM", "SIGHUP"):
    _sig = getattr(signal, _sig_name, None)
    if _sig is not None:
        _LETHAL_SIGNALS.add(_sig)


# Re-entrancy latch for _finalize_active_run(). Signal handlers run on the main
# thread between bytecodes, so a second lethal signal can arrive while the first
# one is still writing artifacts; the nested call must return immediately.
_finalizing_active_run = False
# Lock object ids that already timed out during the current signal finalization;
# subsequent acquires for the same lock only try a non-blocking acquire.
_timed_out_locks: Set[int] = set()


def in_signal_finalization() -> bool:
    """Return True while ``_finalize_active_run`` is finalizing a lethal signal."""
    return _finalizing_active_run


@contextmanager
def finalization_lock(lock: Any, timeout: float) -> Iterator[bool]:
    """Acquire ``lock`` normally, or with a bound during lethal-signal finalization.

    Outside signal finalization (``_finalizing_active_run`` is False), this
    acquires ``lock`` with a normal blocking ``with lock:`` and always yields
    ``True``. During signal finalization, it waits at most ``timeout`` seconds
    (or uses ``acquire(blocking=False)`` if ``lock`` already timed out in this
    finalization). Yields ``True`` when the lock is held and ``False`` when it
    gave up so the caller can proceed lock-free.
    """
    if not _finalizing_active_run:
        with lock:
            yield True
        return

    lock_id = id(lock)
    if lock_id in _timed_out_locks:
        acquired = lock.acquire(blocking=False)
    else:
        acquired = lock.acquire(timeout=timeout)
        if not acquired:
            _timed_out_locks.add(lock_id)
    try:
        yield acquired
    finally:
        if acquired:
            lock.release()


# Signal-context lock rule: during signal finalization, never block without a
# bound; on timeout, do the work lock-free and still write the manifest.
#
# Lock inventory (every lock audited for lethal-signal finalization):
# - src/pubrun/core.py::_run_lock (RLock): bounded 2.0 s via finalization_lock in Run._finalize_state; lock-free fallback prevents cross-thread deadlock with pubrun-hw.
# - src/pubrun/writer.py::ArtifactWriter._write_lock (RLock): bounded 2.0 s via finalization_lock in ArtifactWriter.write_artifacts; lock-free fallback still writes manifest.json.
# - src/pubrun/tracker.py::Run._errors_lock (Lock): bounded 0.25 s via finalization_lock in Run._check_section_failed, Run._store_capture_error_detail, and Run.to_manifest_dict; lock-free fallback.
# - src/pubrun/tracker.py::Run._data_files_lock (Lock): bounded 0.25 s via finalization_lock in Run.to_manifest_dict, file_io.finalize_pending_registrations, and file_io.get_or_create_budget_tracker; lock-free fallback.
# - src/pubrun/capture/file_io.py::FileIoBudgetTracker._lock (Lock): bounded 0.25 s via finalization_lock in all FileIoBudgetTracker methods; lock-free fallback.
# - src/pubrun/events.py::EventStream._lock (Lock): bounded 0.25 s via finalization_lock in EventStream.emit (drops event on timeout) and EventStream.close (returns without closing; OS closes fd at exit).
# - src/pubrun/capture/subprocesses.py::SubprocessSpy._lock (Lock, class): bounded 0.25 s via finalization_lock in SubprocessSpy.finalize_all (and its _complete_record helper) and SubprocessSpy.uninstall; lock-free fallback.
# - src/pubrun/capture/resources.py::ResourceWatcher._lock (Lock): bounded 0.25 s via finalization_lock in ResourceWatcher.stop (with 0.5 s thread join cap) and ResourceWatcher.to_manifest_dict; lock-free fallback.
# - src/pubrun/__init__.py::_commit_lock (Lock): unchanged; startup manifest write caches the commit before the active run is published, so _get_commit returns without taking the lock.
# - src/pubrun/capture/signals.py::SignalExitCapture._lock (RLock): unchanged; get_records already uses acquire(blocking=False) with lock-free fallback (commit 94e504a).
# - src/pubrun/capture/console.py::TqdmSafeTee._lock (RLock): unchanged; not taken by ConsoleInterceptor.stop.
# - src/pubrun/capture/packages.py::_CACHE_LOCK and _DistributionIndex._files_lock (Lock): unchanged; main thread holds them only at startup (before handlers are installed) or inside _finalize_state after _finalized is latched.
# - src/pubrun/writer.py::_durability_warn_lock and src/pubrun/capture/file_io.py::_warn_lock (Lock): unchanged; only acquired when a configuration value is invalid.
# - src/pubrun/_bootstrap.py::_lock, src/pubrun/core.py::_start_lock, and src/pubrun/core.py::_pubrun_log_lock (Lock): unchanged; not reached during finalization (_bootstrap.get_import_metadata takes no lock).
def _finalize_active_run() -> None:
    """Best-effort finalization of the active run before process death.

    Called when a lethal signal (SIGTERM, SIGHUP) is about to kill the
    process via SIG_DFL re-delivery.  Imports tracker lazily to avoid
    circular imports.  A nested call made while a finalization is already in
    progress returns without writing.
    """
    global _finalizing_active_run
    if _finalizing_active_run:
        return
    _finalizing_active_run = True
    try:
        from pubrun.tracker import get_current_run
        run = get_current_run()
        if run and hasattr(run, "writer") and run.writer:
            run.writer.write_artifacts()
    except Exception:
        pass  # Best-effort: never crash during signal handling
    finally:
        _timed_out_locks.clear()
        _finalizing_active_run = False


class SignalExitCapture:
    """Non-intrusive signal and exit-code recorder.

    Installs thin shim handlers that:
      - Record the signal number + timestamp in an internal list.
      - Forward to the previously-installed handler (user's or default).

    Also wraps ``sys.excepthook`` to capture unhandled exceptions and
    ``sys.exit`` to capture explicit exit codes (CPython never passes
    ``SystemExit`` to ``sys.excepthook``).
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        # Re-entrant: signal handlers run on the main thread and can interrupt
        # code that already holds this lock (for example get_records() inside
        # a manifest write), so a non-reentrant lock could deadlock forever.
        self._lock = threading.RLock()
        self._config: Optional[Dict[str, Any]] = config
        self._signals_received: List[Dict[str, Any]] = []
        self._exit_code: Optional[int] = None
        self._exit_exception: Optional[str] = None
        self._exit_exception_type: Optional[str] = None
        self._installed = False
        self._active = False
        self._signals_unavailable = False
        self._install_error: Optional[str] = None
        self._previous_handlers: Dict[int, Any] = {}
        self._installed_handlers: Dict[int, Callable] = {}
        self._previous_excepthook: Optional[Callable] = None
        self._installed_excepthook: Optional[Callable] = None
        self._previous_sys_exit: Optional[Callable] = None
        self._installed_sys_exit: Optional[Callable] = None

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def install(self) -> None:
        """Install signal shims and excepthook wrapper transactionally.

        Safe to call multiple times. On an unexpected setup error, rolls back
        any already-registered signal handlers or excepthook and re-raises.
        """
        if self._installed:
            return
        self._install_error = None
        self._signals_unavailable = False
        self._active = True
        try:
            self._install_signal_handlers()
            self._install_excepthook()
            self._install_sys_exit()
        except Exception as e:
            from pubrun.capture.redaction import format_safe_error_detail
            self._active = False
            self._installed = False
            self._install_error = format_safe_error_detail(e, self._config)
            try:
                self._restore_signal_handlers()
            except Exception:
                pass
            try:
                self._restore_excepthook()
            except Exception:
                pass
            try:
                self._restore_sys_exit()
            except Exception:
                pass
            raise
        self._installed = True

    def uninstall(self) -> None:
        """Deactivate wrappers and restore still-owned handlers independently."""
        if not self._installed:
            return
        self._active = False
        self._installed = False
        try:
            self._restore_signal_handlers()
        except Exception:
            pass
        try:
            self._restore_excepthook()
        except Exception:
            pass
        try:
            self._restore_sys_exit()
        except Exception:
            pass

    def get_records(self) -> Dict[str, Any]:
        """Return the captured signal/exit data for manifest inclusion.

        Never blocks on ``_lock``. A background manifest refresh calls this
        while holding ``pubrun.core._run_lock``; if the main thread holds
        ``_lock`` and a lethal signal makes it finalize (which takes
        ``_run_lock``), a blocking acquire here would deadlock both threads.
        When the lock is busy the snapshot is taken lock-free, which is safe
        because the signal shim and ``_set_exit`` already write lock-free.
        """
        acquired = self._lock.acquire(blocking=False)
        try:
            return self._snapshot_records()
        finally:
            if acquired:
                self._lock.release()

    def _snapshot_records(self) -> Dict[str, Any]:
        if self._install_error:
            capture_state: Dict[str, Any] = {
                "status": "failed",
                "detail": self._install_error,
            }
        elif self._signals_unavailable:
            capture_state = {
                "status": "partial",
                "detail": "signal handlers unavailable off main thread",
            }
        else:
            capture_state = {"status": "complete"}
        return {
            "signals_received": list(self._signals_received),
            "exit_code": self._exit_code,
            "exit_exception": self._exit_exception,
            "capture_state": capture_state,
        }

    def record_exit_code(self, code: Optional[int]) -> None:
        """Explicitly record the process exit code (called at finalization).

        Keeps the first recorded value, so a finalization-time default never
        overwrites a code captured from ``sys.exit`` or an unhandled exception.
        """
        with self._lock:
            if self._exit_code is None:
                self._exit_code = code

    def exit_exception_type(self) -> Optional[str]:
        """Return the class name of the exception that ended the process, if recorded."""
        return self._exit_exception_type

    def _set_exit(self, code: int, exc_str: Optional[str], exc_type_name: Optional[str]) -> None:
        """Record a definitive exit, overwriting any earlier value.

        Lock-free on purpose: this runs from the ``sys.exit`` wrapper, which a
        user signal handler may call while the main thread holds ``_lock``.
        Single attribute assignments are atomic under the GIL.
        """
        self._exit_code = code
        self._exit_exception = exc_str
        self._exit_exception_type = exc_type_name

    # ------------------------------------------------------------------
    # Signal handler installation
    # ------------------------------------------------------------------

    def _install_signal_handlers(self) -> None:
        """Register shim handlers for all target signals available on this platform."""
        import logging
        skipped_all = True
        for sig_name in _TARGET_SIGNALS:
            signum = getattr(signal, sig_name, None)
            if signum is None:
                continue  # Signal not available on this OS

            try:
                previous = signal.getsignal(signum)
                shim = self._make_handler(signum, previous)
                signal.signal(signum, shim)
                # Only record the previous handler and shim if signal.signal() succeeded.
                self._previous_handlers[signum] = previous
                self._installed_handlers[signum] = shim
                skipped_all = False
            except (OSError, ValueError):
                # Cannot set handler (e.g. not main thread, or signal not
                # settable).  Skip but track for warning below.
                pass

        # If ALL signals were skipped (typically because we're not on the main
        # thread), emit a single warning so users know why signal data is missing.
        if skipped_all and not self._previous_handlers:
            self._signals_unavailable = True
            logging.getLogger("pubrun").warning(
                "pubrun: signal capture unavailable (not running on the main thread). "
                "Signal and exit-code data will not be recorded for this run."
            )

    def _restore_signal_handlers(self) -> None:
        """Put back original handlers we displaced, only when still ours."""
        for signum, previous in list(self._previous_handlers.items()):
            try:
                installed_shim = self._installed_handlers.get(signum)
                if installed_shim is not None and signal.getsignal(signum) is installed_shim:
                    signal.signal(signum, previous)
            except Exception:
                pass
        self._previous_handlers.clear()
        self._installed_handlers.clear()

    def _make_handler(self, signum: int, previous_handler: Any) -> Callable:
        """Create a shim handler that records the signal, then chains."""

        def _handler(sig: int, frame: Any) -> Any:
            if not self._active:
                # Passive passthrough after uninstall: no recording, no
                # _finalize_active_run(), and never reinstall _handler on SIG_DFL.
                if previous_handler is signal.SIG_DFL:
                    signal.signal(sig, signal.SIG_DFL)
                    os.kill(os.getpid(), sig)
                elif previous_handler is signal.SIG_IGN:
                    pass
                elif callable(previous_handler):
                    previous_handler(sig, frame)
                return

            # Record the signal
            # Lock-free: list.append is atomic under the GIL, and taking
            # self._lock here could deadlock if the interrupted main-thread code
            # already holds it.
            sig_name = _signal_name(sig)
            self._signals_received.append({
                "signal": sig,
                "signal_name": sig_name,
                "timestamp_utc": time.time(),
            })

            # Chain to the previous handler.
            # The previous handler can be:
            #   - signal.SIG_DFL (0) -- default behavior
            #   - signal.SIG_IGN (1) -- ignore
            #   - A callable (user handler or Python's default KeyboardInterrupt raiser)
            if previous_handler is signal.SIG_DFL:
                # For lethal signals (SIGTERM, SIGHUP), finalize the run before
                # re-delivering, because SIG_DFL will kill the process without
                # running atexit handlers.
                if sig in _LETHAL_SIGNALS:
                    _finalize_active_run()

                # Re-raise with default behavior: temporarily reset to SIG_DFL,
                # re-send the signal to ourselves.
                signal.signal(sig, signal.SIG_DFL)
                os.kill(os.getpid(), sig)
                # If we survive (e.g., SIGINT raised KeyboardInterrupt which was
                # caught by user code), re-install our shim only while active.
                if self._active:
                    signal.signal(sig, _handler)
            elif previous_handler is signal.SIG_IGN:
                # The previous disposition was to ignore.  Respect that.
                pass
            elif callable(previous_handler):
                # A real callable (user's handler or Python's default).
                previous_handler(sig, frame)
            # If previous_handler is None (shouldn't happen), do nothing extra.

        return _handler

    # ------------------------------------------------------------------
    # sys.excepthook wrapper (captures SystemExit exit codes + unhandled exceptions)
    # ------------------------------------------------------------------

    def _install_excepthook(self) -> None:
        """Wrap sys.excepthook to capture SystemExit and unhandled exceptions."""
        prev_hook = sys.excepthook
        self._previous_excepthook = prev_hook
        _self = self  # closure reference
        self._installed_excepthook = None  # set after we build the wrapper

        def _excepthook(exc_type: type, exc_value: BaseException, exc_tb: Any) -> None:
            if not _self._active:
                if prev_hook is not None:
                    prev_hook(exc_type, exc_value, exc_tb)
                return

            from pubrun.capture.redaction import format_safe_error_detail

            # Record exit information. An unhandled exception is the definitive
            # end of the process, so it overwrites any earlier recorded value.
            if exc_type is SystemExit and isinstance(exc_value, SystemExit):
                code, exit_exc_str = _exit_details(exc_value, _self._config)
                _self._set_exit(code, exit_exc_str, "SystemExit")
            else:
                # Unhandled exception -- process will exit with code 1
                exit_exc_str = format_safe_error_detail(exc_value, _self._config)
                type_name = getattr(exc_type, "__name__", None) or type(exc_value).__name__
                _self._set_exit(1, exit_exc_str, type_name)

            # Chain to previous excepthook (which prints the traceback, etc.)
            if prev_hook is not None:
                prev_hook(exc_type, exc_value, exc_tb)

            # Flush stdout and stderr to ensure log files receive the traceback
            try:
                sys.stdout.flush()
                sys.stderr.flush()
            except Exception:
                pass

        sys.excepthook = _excepthook
        self._installed_excepthook = _excepthook

    def _restore_excepthook(self) -> None:
        """Restore the original sys.excepthook, but only if it is still ours.

        If a third party replaced sys.excepthook after we installed our wrapper,
        blindly restoring the previous hook would silently discard theirs. Only
        restore when the current hook is the wrapper we installed, matching the
        identity-guarded pattern used for the console stream restore.
        (IPD 20260705 EC-15.)
        """
        installed = getattr(self, "_installed_excepthook", None)
        if self._previous_excepthook is not None and sys.excepthook is installed:
            sys.excepthook = self._previous_excepthook
        self._previous_excepthook = None
        self._installed_excepthook = None

    # ------------------------------------------------------------------
    # sys.exit wrapper (captures explicit exit codes)
    # ------------------------------------------------------------------

    def _install_sys_exit(self) -> None:
        """Wrap ``sys.exit`` to record the requested exit code before delegating.

        CPython handles an uncaught ``SystemExit`` without calling
        ``sys.excepthook``, and ``sys.exc_info()`` is empty by the time atexit
        handlers run, so this wrapper is the only place the code is visible.
        Only calls on the main thread are recorded, because ``sys.exit()`` on a
        worker thread ends that thread, not the process.  A later call
        overwrites an earlier one.
        """
        prev_exit = sys.exit
        self._previous_sys_exit = prev_exit
        _self = self

        def _sys_exit(*args: Any) -> Any:
            if _self._active and threading.current_thread() is threading.main_thread():
                try:
                    status = args[0] if args else None
                    code, exit_exc_str = _exit_details(SystemExit(status), _self._config)
                    _self._set_exit(code, exit_exc_str, "SystemExit")
                except Exception:
                    pass  # Recording must never change how the process exits.
            return prev_exit(*args)

        sys.exit = _sys_exit
        self._installed_sys_exit = _sys_exit

    def _restore_sys_exit(self) -> None:
        """Restore the previous ``sys.exit``, but only if ours is still installed."""
        installed = getattr(self, "_installed_sys_exit", None)
        previous = getattr(self, "_previous_sys_exit", None)
        if previous is not None and installed is not None and sys.exit is installed:
            sys.exit = previous
        self._previous_sys_exit = None
        self._installed_sys_exit = None


# --------------------------------------------------------------------------
# Utility
# --------------------------------------------------------------------------

def _exit_details(exc: SystemExit, config: Optional[Dict[str, Any]]) -> Tuple[int, str]:
    """Map a ``SystemExit`` to the process exit code and a safe description.

    ``None`` exits 0, an integer (including ``bool``) exits with that value,
    and any other object is printed by CPython and exits 1; its text is
    redacted because it may carry arbitrary user data.
    """
    code = exc.code
    if code is None:
        return 0, "SystemExit(None)"
    if isinstance(code, int):
        return int(code), f"SystemExit({int(code)!r})"
    from pubrun.capture.redaction import format_safe_error_detail
    return 1, format_safe_error_detail(exc, config)


def _signal_name(signum: int) -> str:
    """Resolve a signal number to its symbolic name (e.g. 2 -> 'SIGINT')."""
    try:
        return signal.Signals(signum).name
    except (ValueError, AttributeError):
        return f"SIG{signum}"
