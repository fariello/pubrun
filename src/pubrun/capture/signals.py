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
from typing import Any, Callable, Dict, List, Optional, Tuple


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


def _finalize_active_run() -> None:
    """Best-effort finalization of the active run before process death.

    Called when a lethal signal (SIGTERM, SIGHUP) is about to kill the
    process via SIG_DFL re-delivery.  Imports tracker lazily to avoid
    circular imports.
    """
    try:
        from pubrun.tracker import get_current_run
        run = get_current_run()
        if run and hasattr(run, "writer") and run.writer:
            run.writer.write_artifacts()
    except Exception:
        pass  # Best-effort: never crash during signal handling


class SignalExitCapture:
    """Non-intrusive signal and exit-code recorder.

    Installs thin shim handlers that:
      - Record the signal number + timestamp in an internal list.
      - Forward to the previously-installed handler (user's or default).

    Also wraps ``sys.excepthook`` to capture SystemExit codes.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        self._lock = threading.Lock()
        self._config: Optional[Dict[str, Any]] = config
        self._signals_received: List[Dict[str, Any]] = []
        self._exit_code: Optional[int] = None
        self._exit_exception: Optional[str] = None
        self._installed = False
        self._active = False
        self._signals_unavailable = False
        self._install_error: Optional[str] = None
        self._previous_handlers: Dict[int, Any] = {}
        self._installed_handlers: Dict[int, Callable] = {}
        self._previous_excepthook: Optional[Callable] = None
        self._installed_excepthook: Optional[Callable] = None

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

    def get_records(self) -> Dict[str, Any]:
        """Return the captured signal/exit data for manifest inclusion."""
        with self._lock:
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
        """Explicitly record the process exit code (called at finalization)."""
        with self._lock:
            if self._exit_code is None:
                self._exit_code = code

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
            sig_name = _signal_name(sig)
            with self._lock:
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

            # Record exit information
            if exc_type is SystemExit and isinstance(exc_value, SystemExit):
                code = exc_value.code
                if isinstance(code, int):
                    _self.record_exit_code(code)
                    exit_exc_str = f"SystemExit({code!r})"
                elif code is None:
                    _self.record_exit_code(0)
                    exit_exc_str = f"SystemExit({code!r})"
                else:
                    # SystemExit can be passed a string message; exit code is 1
                    _self.record_exit_code(1)
                    exit_exc_str = format_safe_error_detail(exc_value, _self._config)
                with _self._lock:
                    _self._exit_exception = exit_exc_str
            else:
                # Unhandled exception -- process will exit with code 1
                _self.record_exit_code(1)
                exit_exc_str = format_safe_error_detail(exc_value, _self._config)
                with _self._lock:
                    _self._exit_exception = exit_exc_str

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


# --------------------------------------------------------------------------
# Utility
# --------------------------------------------------------------------------

def _signal_name(signum: int) -> str:
    """Resolve a signal number to its symbolic name (e.g. 2 -> 'SIGINT')."""
    try:
        return signal.Signals(signum).name
    except (ValueError, AttributeError):
        return f"SIG{signum}"
