import sys
import logging
from typing import TextIO, Dict, Any, Optional
from pathlib import Path

logger = logging.getLogger("pubrun")


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

    def write(self, data: str) -> int:
        """Write data to the original stream and the log file.

        Carriage returns (``\r``) trigger a buffer squash to prevent
        progress bar redraws from bloating the log file.
        """
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
        if not self.log_file or self.log_file.closed:
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
                            self.log_file.write(ts + full_line + '\n')
                        else:
                            self.log_file.write(full_line + '\n')
                        self.line_count += 1
                        self._current_buffer = ""
                    else:
                        self._current_buffer += line
        except Exception as e:
            logger.debug(f"pubrun tee internal error: {e}")

        return ret

    def flush(self) -> None:
        """Flush both the original stream and the log file."""
        try:
            self.original_stream.flush()
        except BrokenPipeError:
            pass  # Downstream reader closed; SIGPIPE will be recorded
        if self.log_file and not self.log_file.closed:
            # Dump whatever is left in the buffer on a flush
            if self._current_buffer:
                if self.timestamped:
                    from datetime import datetime, timezone
                    ts = f"[{datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3]}Z] "
                    self.log_file.write(ts + self._current_buffer + '\n')
                else:
                    self.log_file.write(self._current_buffer + '\n')
                self.line_count += 1
                self._current_buffer = ""
            self.log_file.flush()

    def __getattr__(self, name: str) -> Any:
        """Delegate attribute access to the original stream (e.g. isatty, encoding)."""
        return getattr(self.original_stream, name)



class ConsoleInterceptor:
    """Manages tee-style interception of stdout/stderr into log files."""
    def __init__(self, run_dir: Path, mode: str) -> None:
        """Initialize the interceptor.

        Args:
            run_dir: Directory where log files will be written.
            mode: Capture mode (``"off"``, ``"basic"``, ``"standard"``, ``"deep"``).
        """
        self.run_dir = run_dir
        self.mode = mode
        self.stdout_log = None
        self.stderr_log = None
        self.stdout_tee = None
        self.stderr_tee = None

        # Save original streams for safe teardown later
        self.original_stdout = sys.stdout
        self.original_stderr = sys.stderr

    def start(self) -> None:
        """Replace sys.stdout and sys.stderr with tee proxies.

        Silently reverts to original streams if setup fails.
        """
        if self.mode == "off":
            return

        try:
            self.stdout_log = open(self.run_dir / "stdout.log", "w", encoding="utf-8")
            self.stderr_log = open(self.run_dir / "stderr.log", "w", encoding="utf-8")

            timestamped = self.mode in {"standard", "deep"}

            self.stdout_tee = TqdmSafeTee(sys.stdout, self.stdout_log, timestamped)
            sys.stdout = self.stdout_tee

            self.stderr_tee = TqdmSafeTee(sys.stderr, self.stderr_log, timestamped)
            sys.stderr = self.stderr_tee

            import faulthandler
            try:
                faulthandler.enable(file=self.stderr_log)
            except Exception:
                pass
        except Exception as e:
            logger.debug(f"pubrun failed to intercept console: {e}")
            self.stop() # rollback


    def stop(self) -> Dict[str, Any]:
        """Restore original streams, close log files, and return capture metrics."""
        # 1. Revert streams only if they still point to our tees.
        # If a third-party library wrapped over our tee after start(), leave
        # the streams alone to avoid breaking that library's wrapper.
        if sys.stdout is self.stdout_tee:
            sys.stdout = self.original_stdout
        if sys.stderr is self.stderr_tee:
            sys.stderr = self.original_stderr

        lines_out = 0
        lines_err = 0

        if self.stdout_tee:
            self.stdout_tee.flush()
            lines_out = self.stdout_tee.line_count
        if self.stderr_tee:
            self.stderr_tee.flush()
            lines_err = self.stderr_tee.line_count

        if self.stdout_log:
            self.stdout_log.close()
            self.stdout_log = None
        if self.stderr_log:
            import faulthandler
            try:
                faulthandler.disable()
            except Exception:
                pass
            self.stderr_log.close()
            self.stderr_log = None

        return {
            "capture_mode": self.mode,
            "stdout": {
                "captured": self.mode != "off",
                "path": "stdout.log" if self.mode != "off" else None,
                "lines_captured": lines_out if self.mode != "off" else None
            },
            "stderr": {
                "captured": self.mode != "off",
                "path": "stderr.log" if self.mode != "off" else None,
                "lines_captured": lines_err if self.mode != "off" else None
            },
            # Dummy for combined, our phase 3 simply implements split
            "combined": {"captured": False, "path": None, "lines_captured": None},
            "capture_state": {"status": "complete"}
        }
