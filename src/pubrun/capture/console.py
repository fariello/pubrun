import sys
import logging
import threading
from typing import TextIO, Dict, Any, Optional
from pathlib import Path

logger = logging.getLogger("pubrun")

# Per-thread console-recording pause gate (ref-counted). When depth > 0 on the
# calling thread, TqdmSafeTee.write still passes data through to the real stream
# but does NOT record it to the log file. Thread-local so a pause on one thread
# does not blind another thread's capture. Covers both the stdout and stderr
# tees (they consult this shared module-level gate). (IPD 20260705.)
_tee_local = threading.local()


def _tee_depth() -> int:
    return getattr(_tee_local, "depth", 0)


def _tee_paused() -> bool:
    """True if console RECORDING is suspended on the calling thread."""
    return _tee_depth() > 0


def pause_console() -> None:
    """Suspend console recording on the CALLING thread (ref-counted)."""
    _tee_local.depth = _tee_depth() + 1


def resume_console() -> None:
    """Undo one pause_console() on the calling thread (never below 0)."""
    _tee_local.depth = max(0, _tee_depth() - 1)


def _is_jupyter_kernel() -> bool:
    """Detect if running inside a Jupyter/IPython notebook kernel."""
    try:
        if "IPython" not in sys.modules:
            return False
        from IPython import get_ipython
        ip = get_ipython()
        if ip is None:
            return False
        # ZMQInteractiveShell = Jupyter kernel; TerminalInteractiveShell = IPython CLI
        return ip.__class__.__name__ == "ZMQInteractiveShell"
    except Exception:
        return False


def resolve_console_mode(config: Dict[str, Any], force_base: Optional[str] = None) -> str:
    """Resolve the effective console capture mode considering context.

    Applies Jupyter and non-TTY overrides on top of the base capture_mode.

    Args:
        config: Resolved pubrun configuration.
        force_base: If given (e.g. ``"standard"`` from the ``full`` import mode),
            use it as the base instead of reading ``[console].capture_mode`` — the
            import mode forces the console tee on regardless of config. The
            Jupyter and non-TTY safety guards below STILL apply on top of it.

    Returns:
        The effective capture mode string ("off", "basic", "standard", "deep").
    """
    base_mode = force_base if force_base else config.get("console", {}).get("capture_mode", "off")

    if base_mode == "off":
        return "off"

    # Jupyter override
    if _is_jupyter_kernel():
        jupyter_mode = config.get("console", {}).get("jupyter_mode", "off")
        return jupyter_mode

    # Non-TTY override
    try:
        if not sys.stdout.isatty():
            non_tty_mode = config.get("console", {}).get("non_tty_mode", "inherit")
            if non_tty_mode != "inherit":
                return non_tty_mode
    except Exception:
        pass  # isatty() can fail on broken streams; ignore

    return base_mode

class TqdmSafeTee:
    """Transparent stream proxy that tees writes to a log file.

    Strips carriage-return (``\r``) redraws so progress bars don't
    inflate the log file.
    """
    def __init__(self, original_stream: TextIO, log_file: Optional[TextIO], timestamped: bool = False) -> None:
        """Initialize the tee with the original stream and an optional log file."""
        self.original_stream = original_stream
        self.log_file = log_file
        self.timestamped = timestamped
        self.line_count = 0
        self._current_buffer = ""
        self._log_write_failed = False
        self._in_error_log = False

    def _handle_log_error(self, exc: BaseException) -> None:
        """Detach a failing log handle once and emit at most one bounded debug message."""
        was_failed = self._log_write_failed
        self._log_write_failed = True
        self.log_file = None
        if not was_failed and not self._in_error_log:
            self._in_error_log = True
            try:
                from pubrun.capture.redaction import format_safe_error_detail
                logger.debug(
                    "pubrun tee log write failed: %s",
                    format_safe_error_detail(exc),
                )
            except Exception:
                pass
            finally:
                self._in_error_log = False

    def write(self, data: str) -> int:
        """Write data to the original stream and the log file.

        Carriage returns (``\r``) trigger a buffer squash to prevent
        progress bar redraws from bloating the log file.
        """
        if self._in_error_log:
            return len(data)

        # 1. Passthrough exactly what was originally sent to the user's console
        try:
            ret = self.original_stream.write(data)
        except BrokenPipeError:
            # Downstream reader closed (e.g., piped to head). Don't crash —
            # let the signal handler record SIGPIPE and let the process exit cleanly.
            ret = len(data)
        except (OSError, ValueError):
            # The original stream may be closed or in a bad state (e.g. host code
            # closed sys.stdout, or "I/O operation on closed file"). The tee must
            # never surface an error the plain stream would not have here; report
            # the bytes as consumed and keep logging. (IPD 20260705 EC-16.)
            ret = len(data)

        # If logging is disabled or file is closed, simply return what was written
        log_file = self.log_file
        if not log_file or getattr(log_file, "closed", False):
            return ret

        # Paused on this thread? Output already passed through above; skip
        # RECORDING it (thread-local, ref-counted). (IPD 20260705 pause/resume.)
        # Inlined `getattr` (no helper-call indirection) to keep this hot-path
        # check cheap; the module-level pause_console/resume_console maintain
        # `_tee_local.depth`. When no pause has ever occurred on this thread the
        # attribute is absent, so the default-0 getattr is the common fast path.
        if getattr(_tee_local, "depth", 0):
            return ret

        try:
            # 2. Process strings for log file safely (handling carriage returns aka TQDM interception)
            # Split on \r first to squash progress bar redraws, then process \n for line breaks.
            # PERF-05: compute timestamp once per write() call, not per line.
            if self.timestamped:
                from datetime import datetime, timezone
                ts = f"[{datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3]}Z] "
            else:
                ts = ""
            segments = data.split('\r')
            for i, segment in enumerate(segments):
                if i > 0:
                    # A \r was encountered — discard the current buffer (progress bar redraw)
                    self._current_buffer = ""
                lines = segment.split('\n')
                # All but the last piece end with \n
                for j, line in enumerate(lines):
                    if j < len(lines) - 1:
                        full_line = self._current_buffer + line
                        if ts:
                            log_file.write(ts + full_line + '\n')
                        else:
                            log_file.write(full_line + '\n')
                        self.line_count += 1
                        self._current_buffer = ""
                    else:
                        self._current_buffer += line
        except Exception as e:
            self._handle_log_error(e)

        return ret

    def flush(self) -> None:
        """Flush both the original stream and the log file."""
        if self._in_error_log:
            return
        try:
            self.original_stream.flush()
        except (BrokenPipeError, OSError, ValueError):
            pass  # Downstream reader closed or original stream closed/broken
        log_file = self.log_file
        if log_file and not getattr(log_file, "closed", False):
            try:
                # Dump whatever is left in the buffer on a flush
                if self._current_buffer:
                    if self.timestamped:
                        from datetime import datetime, timezone
                        ts = f"[{datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3]}Z] "
                        log_file.write(ts + self._current_buffer + '\n')
                    else:
                        log_file.write(self._current_buffer + '\n')
                    self.line_count += 1
                    self._current_buffer = ""
                log_file.flush()
            except Exception as e:
                self._handle_log_error(e)

    def __getattr__(self, name: str) -> Any:
        """Delegate attribute access to the original stream (e.g. isatty, encoding)."""
        return getattr(self.original_stream, name)



class ConsoleInterceptor:
    """Manages tee-style interception of stdout/stderr into log files."""
    def __init__(
        self,
        run_dir: Path,
        mode: str,
        config: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Initialize the interceptor.

        Args:
            run_dir: Directory where log files will be written.
            mode: Capture mode (``"off"``, ``"basic"``, ``"standard"``, ``"deep"``).
            config: Optional resolved pubrun config for error-detail redaction.
        """
        self.run_dir = run_dir
        self.mode = mode
        self._config: Optional[Dict[str, Any]] = config
        self.stdout_log = None
        self.stderr_log = None
        self.stdout_tee = None
        self.stderr_tee = None

        # Save original streams for safe teardown later
        self.original_stdout = sys.stdout
        self.original_stderr = sys.stderr

        self._started = False
        self._failed_detail: Optional[str] = None
        self._faulthandler_owned = False
        self._faulthandler_was_enabled = False
        self._cached_result: Optional[Dict[str, Any]] = None

    def _cleanup_resources(self) -> tuple:
        """Run every teardown step independently and return (lines_out, lines_err, out_failed, err_failed)."""
        lines_out = 0
        lines_err = 0
        out_failed = False
        err_failed = False

        # 1. Revert stdout only if it still points to our tee.
        try:
            if self.stdout_tee is not None and sys.stdout is self.stdout_tee:
                sys.stdout = self.original_stdout
        except Exception:
            pass

        # 2. Revert stderr only if it still points to our tee.
        try:
            if self.stderr_tee is not None and sys.stderr is self.stderr_tee:
                sys.stderr = self.original_stderr
        except Exception:
            pass

        # 3. Flush stdout_tee, record metrics, and detach log_file.
        if self.stdout_tee is not None:
            try:
                self.stdout_tee.flush()
            except Exception:
                out_failed = True
            finally:
                try:
                    lines_out = self.stdout_tee.line_count
                except Exception:
                    pass
                try:
                    out_failed = out_failed or bool(
                        getattr(self.stdout_tee, "_log_write_failed", False)
                    )
                except Exception:
                    pass
                try:
                    self.stdout_tee.log_file = None
                except Exception:
                    pass

        # 4. Flush stderr_tee, record metrics, and detach log_file.
        if self.stderr_tee is not None:
            try:
                self.stderr_tee.flush()
            except Exception:
                err_failed = True
            finally:
                try:
                    lines_err = self.stderr_tee.line_count
                except Exception:
                    pass
                try:
                    err_failed = err_failed or bool(
                        getattr(self.stderr_tee, "_log_write_failed", False)
                    )
                except Exception:
                    pass
                try:
                    self.stderr_tee.log_file = None
                except Exception:
                    pass

        # 5. Disable faulthandler BEFORE closing stderr_log, only when we enabled it.
        if self._faulthandler_owned:
            try:
                import faulthandler
                faulthandler.disable()
            except Exception:
                pass
            finally:
                self._faulthandler_owned = False

        # 6. Close stdout_log independently.
        if self.stdout_log is not None:
            try:
                self.stdout_log.close()
            except Exception:
                pass
            finally:
                self.stdout_log = None

        # 7. Close stderr_log independently.
        if self.stderr_log is not None:
            try:
                self.stderr_log.close()
            except Exception:
                pass
            finally:
                self.stderr_log = None

        return lines_out, lines_err, out_failed, err_failed

    def start(self) -> bool:
        """Replace sys.stdout and sys.stderr with tee proxies transactionally.

        Returns True on success (including mode=="off"). On any setup error,
        rolls back opened handles, streams, and owned faulthandler state, records
        a bounded redacted failure detail, and returns False.
        """
        if self.mode == "off":
            return True

        self._cached_result = None
        self._failed_detail = None
        self._faulthandler_owned = False
        self._faulthandler_was_enabled = False
        self.original_stdout = sys.stdout
        self.original_stderr = sys.stderr

        try:
            self.stdout_log = open(self.run_dir / "stdout.log", "w", encoding="utf-8")
            self.stderr_log = open(self.run_dir / "stderr.log", "w", encoding="utf-8")

            timestamped = self.mode in {"standard", "deep"}

            self.stdout_tee = TqdmSafeTee(self.original_stdout, self.stdout_log, timestamped)
            sys.stdout = self.stdout_tee

            self.stderr_tee = TqdmSafeTee(self.original_stderr, self.stderr_log, timestamped)
            sys.stderr = self.stderr_tee

            import faulthandler
            try:
                self._faulthandler_was_enabled = bool(faulthandler.is_enabled())
            except Exception:
                self._faulthandler_was_enabled = False
            if not self._faulthandler_was_enabled:
                try:
                    faulthandler.enable(file=self.stderr_log)
                    self._faulthandler_owned = True
                except Exception:
                    self._faulthandler_owned = False

            self._started = True
            return True
        except Exception as e:
            from pubrun.capture.redaction import format_safe_error_detail
            self._failed_detail = format_safe_error_detail(e, self._config)
            logger.debug("pubrun failed to intercept console: %s", self._failed_detail)
            self._cleanup_resources()
            self._started = False
            return False

    def stop(self) -> Dict[str, Any]:
        """Restore original streams, close log files, and return capture metrics.

        Idempotent: repeated calls return a copy of the cached final result.
        """
        import copy

        if self._cached_result is not None:
            return copy.deepcopy(self._cached_result)

        lines_out, lines_err, out_failed, err_failed = self._cleanup_resources()
        self._started = False

        if self._failed_detail is not None:
            result: Dict[str, Any] = {
                "capture_mode": self.mode,
                "stdout": {
                    "captured": False,
                    "path": None,
                    "lines_captured": None,
                },
                "stderr": {
                    "captured": False,
                    "path": None,
                    "lines_captured": None,
                },
                "combined": {"captured": False, "path": None, "lines_captured": None},
                "capture_state": {"status": "failed", "detail": self._failed_detail},
            }
        elif self.mode == "off":
            result = {
                "capture_mode": self.mode,
                "stdout": {
                    "captured": False,
                    "path": None,
                    "lines_captured": None,
                },
                "stderr": {
                    "captured": False,
                    "path": None,
                    "lines_captured": None,
                },
                "combined": {"captured": False, "path": None, "lines_captured": None},
                "capture_state": {"status": "complete"},
            }
        else:
            if out_failed or err_failed:
                capture_state: Dict[str, Any] = {
                    "status": "partial",
                    "detail": "console log write failed during execution",
                }
            else:
                capture_state = {"status": "complete"}
            result = {
                "capture_mode": self.mode,
                "stdout": {
                    "captured": True,
                    "path": "stdout.log",
                    "lines_captured": lines_out,
                },
                "stderr": {
                    "captured": True,
                    "path": "stderr.log",
                    "lines_captured": lines_err,
                },
                # Dummy for combined, our phase 3 simply implements split
                "combined": {"captured": False, "path": None, "lines_captured": None},
                "capture_state": capture_state,
            }

        self._cached_result = result
        return copy.deepcopy(result)
