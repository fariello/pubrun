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
    "SIGUSR1",   # User-defined (Unix only)
    "SIGUSR2",   # User-defined (Unix only)
    "SIGBREAK",  # Ctrl+Break on Windows
]


class SignalExitCapture:
    """Non-intrusive signal and exit-code recorder.

    Installs thin shim handlers that:
      - Record the signal number + timestamp in an internal list.
      - Forward to the previously-installed handler (user's or default).

    Also wraps ``sys.excepthook`` to capture SystemExit codes.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._signals_received: List[Dict[str, Any]] = []
        self._exit_code: Optional[int] = None
        self._exit_exception: Optional[str] = None
        self._installed = False
        self._previous_handlers: Dict[int, Any] = {}
        self._previous_excepthook: Optional[Callable] = None

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def install(self) -> None:
        """Install signal shims and excepthook wrapper.  Safe to call multiple times."""
        if self._installed:
            return
        self._installed = True
        self._install_signal_handlers()
        self._install_excepthook()

    def uninstall(self) -> None:
        """Restore all original handlers.  Called during finalization."""
        if not self._installed:
            return
        self._installed = False
        self._restore_signal_handlers()
        self._restore_excepthook()

    def get_records(self) -> Dict[str, Any]:
        """Return the captured signal/exit data for manifest inclusion."""
        with self._lock:
            return {
                "signals_received": list(self._signals_received),
                "exit_code": self._exit_code,
                "exit_exception": self._exit_exception,
                "capture_state": {"status": "complete"},
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
                signal.signal(signum, self._make_handler(signum, previous))
                # Only record the previous handler if signal.signal() succeeded.
                self._previous_handlers[signum] = previous
                skipped_all = False
            except (OSError, ValueError):
                # Cannot set handler (e.g. not main thread, or signal not
                # settable).  Skip but track for warning below.
                pass

        # If ALL signals were skipped (typically because we're not on the main
        # thread), emit a single warning so users know why signal data is missing.
        if skipped_all and not self._previous_handlers:
            logging.getLogger("pubrun").warning(
                "pubrun: signal capture unavailable (not running on the main thread). "
                "Signal and exit-code data will not be recorded for this run."
            )

    def _restore_signal_handlers(self) -> None:
        """Put back the original handlers we displaced."""
        for signum, handler in self._previous_handlers.items():
            try:
                signal.signal(signum, handler)
            except (OSError, ValueError):
                pass
        self._previous_handlers.clear()

    def _make_handler(self, signum: int, previous_handler: Any) -> Callable:
        """Create a shim handler that records the signal, then chains."""

        def _handler(sig: int, frame: Any) -> Any:
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
                # Re-raise with default behavior: temporarily reset to SIG_DFL,
                # re-send the signal to ourselves.
                signal.signal(sig, signal.SIG_DFL)
                os.kill(os.getpid(), sig)
                # If we survive (e.g., SIGINT raised KeyboardInterrupt which was
                # caught by user code), re-install our shim so subsequent signals
                # are still recorded.
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
        self._previous_excepthook = sys.excepthook
        _self = self  # closure reference

        def _excepthook(exc_type: type, exc_value: BaseException, exc_tb: Any) -> None:
            # Record exit information
            if exc_type is SystemExit and isinstance(exc_value, SystemExit):
                code = exc_value.code
                if isinstance(code, int):
                    _self.record_exit_code(code)
                elif code is None:
                    _self.record_exit_code(0)
                else:
                    # SystemExit can be passed a string message; exit code is 1
                    _self.record_exit_code(1)
                with _self._lock:
                    _self._exit_exception = f"SystemExit({code!r})"
            else:
                # Unhandled exception -- process will exit with code 1
                _self.record_exit_code(1)
                with _self._lock:
                    _self._exit_exception = f"{exc_type.__name__}: {exc_value}"

            # Chain to previous excepthook (which prints the traceback, etc.)
            if _self._previous_excepthook is not None:
                _self._previous_excepthook(exc_type, exc_value, exc_tb)

        sys.excepthook = _excepthook

    def _restore_excepthook(self) -> None:
        """Restore the original sys.excepthook."""
        if self._previous_excepthook is not None:
            sys.excepthook = self._previous_excepthook
            self._previous_excepthook = None


# --------------------------------------------------------------------------
# Utility
# --------------------------------------------------------------------------

def _signal_name(signum: int) -> str:
    """Resolve a signal number to its symbolic name (e.g. 2 -> 'SIGINT')."""
    try:
        return signal.Signals(signum).name
    except (ValueError, AttributeError):
        return f"SIG{signum}"
