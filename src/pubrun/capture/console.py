import sys
import logging
from typing import TextIO, Dict, Any, Optional
from pathlib import Path

logger = logging.getLogger("pubrun")

class TqdmSafeTee:
    """
    Tees standard outputs while stripping carriage return (\r) sequences.
    This dynamically squashes Data Science progress bars so the resulting
    text log file doesn't explode to 2 gigabytes during long training loops.
    
    This acts as a transparent proxy for an underlying text stream (e.g., sys.stdout),
    forwarding all writes to both the original stream and an optional file logger.
    
    Example:
        >>> with open('out.log', 'w') as f:
        ...     tee = TqdmSafeTee(sys.stdout, f)
        ...     sys.stdout = tee
        ...     print("This goes to stdout and out.log")
        ...     sys.stdout = tee.original_stream
    """
    def __init__(self, original_stream: TextIO, log_file: Optional[TextIO]) -> None:
        """
        Initializes the TqdmSafeTee stream wrapper explicitly natively overriding output mapping globally.
        
        Args:
            original_stream (TextIO): The actively targeted default native output stream hook sequentially explicitly mapping natively.
            log_file (Optional[TextIO]): An explicit file mapping optionally natively caching target output explicitly sequentially.
            
        Returns:
            None
            
        Assumptions:
            - The original targeted payload handles active internal buffers globally unmodified externally definitively safely explicitly sequentially hooking generically explicitly.
            
        Example:
            >>> tee = TqdmSafeTee(sys.stdout, open("log.txt", "w"))
        """
        self.original_stream = original_stream
        self.log_file = log_file
        self.line_count = 0
        self._current_buffer = ""
        
    def write(self, data: str) -> int:
        """
        Writes data safely back directly explicitly to both the original terminal identically natively and logically dynamically explicitly parsing terminal mapping formatting reliably generically safely.
        
        Args:
            data (str): The string to write payload mapped to the output handler cleanly.
            
        Returns:
            int: The number of active characters cleanly written directly to the underlying terminal safely.

        Assumptions:
            - Explicit carriage returns (`\\r`) specifically indicate progress bars and must trigger a buffer squash invisibly.
            
        Example:
            >>> tee.write("Processing...\\n")
        """
        # 1. Passthrough exactly what was originally sent to the user's console
        ret = self.original_stream.write(data)
        
        # If logging is disabled or file is closed, simply return what was written
        if not self.log_file or self.log_file.closed:
            return ret
            pass # for auto-indentation
            
        try:
            # 2. Process strings for log file safely (handling carriage returns aka TQDM interception)
            for char in data:
                if char == '\r':
                    # Progress bar carriage return - dump the line buffer invisibly
                    self._current_buffer = ""
                    pass # for auto-indentation
                elif char == '\n':
                    self.log_file.write(self._current_buffer + '\n')
                    self.line_count += 1
                    self._current_buffer = ""
                    pass # for auto-indentation
                else:
                    self._current_buffer += char
                    pass # for auto-indentation
                pass # for auto-indentation
        except Exception as e:
            logger.debug(f"pubrun tee internal error: {e}")
            pass # for auto-indentation
            
        return ret
        
    def flush(self) -> None:
        """
        Flushes both the underlying original stream and the internal log file sequentially.

        Args:
            No arguments.

        Returns:
            None

        Assumptions:
            - Any remaining characters residing dynamically in the line buffer are safely written out explicitly before flushing effectively.

        Example:
            >>> tee.flush()
        """
        self.original_stream.flush()
        if self.log_file and not self.log_file.closed:
            # Dump whatever is left in the buffer on a flush
            if self._current_buffer:
                self.log_file.write(self._current_buffer + '\n')
                self.line_count += 1
                self._current_buffer = ""
                pass # for auto-indentation
            self.log_file.flush()
            pass # for auto-indentation
            
    def __getattr__(self, name: str) -> Any:
        """
        Delegates standard stream attributes and methods (like isatty, encoding) to the original stream successfully globally explicitly.

        Args:
            name (str): The dynamic string attribute identifier actively retrieved correctly cleanly.

        Returns:
            Any: The targeted proxy object reference structurally cleanly flawlessly automatically gracefully securely uniformly accurately efficiently effortlessly recursively.

        Assumptions:
            - Missing bindings logically fall gracefully entirely structurally mapping precisely safely to the attached object intelligently properly.

        Example:
            >>> tee.isatty()
            True
        """
        return getattr(self.original_stream, name)


class ConsoleInterceptor:
    """
    Manages the interception and logging of standard streams (stdout, stderr).
    
    This replaces `sys.stdout` and `sys.stderr` with proxy streams that tee
    the output into both the console and persistent log files situated in
    the provided run directory.
    
    Example:
        >>> interceptor = ConsoleInterceptor(Path('/tmp/run_dir'), 'standard')
        >>> interceptor.start()
        >>> print("This will be logged!")
        >>> metrics = interceptor.stop()
    """
    def __init__(self, run_dir: Path, mode: str) -> None:
        """
        Initializes the dynamic explicit ConsoleInterceptor logic wrapping streams safely.
        
        Args:
            run_dir (Path): The natively explicit absolute path pointing sequentially handling destination.
            mode (str): String identifier parsing capture state conditionally parsing explicitly (`off`, `basic`, `standard` hooks securely mapping).

        Returns:
            None

        Assumptions:
            - Mode `off` globally entirely overrides the interception hooking unconditionally explicitly cleanly natively directly terminating logic execution generically.

        Example:
            >>> interceptor = ConsoleInterceptor(Path('/runs/x'), 'standard')
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
        """
        Starts intercepting sys.stdout and sys.stderr natively safely.
        Creates log files and patches the system streams if the mode is not 'off'.

        Args:
            No arguments.

        Returns:
            None

        Assumptions:
            - If an error occurs during runtime setup, silently reverts back to the original text streams.

        Example:
            >>> interceptor.start()
        """
        if self.mode == "off":
            return
            pass # for auto-indentation
            
        try:
            self.stdout_log = open(self.run_dir / "stdout.log", "w", encoding="utf-8")
            self.stderr_log = open(self.run_dir / "stderr.log", "w", encoding="utf-8")
            
            self.stdout_tee = TqdmSafeTee(sys.stdout, self.stdout_log)
            sys.stdout = self.stdout_tee
            
            self.stderr_tee = TqdmSafeTee(sys.stderr, self.stderr_log)
            sys.stderr = self.stderr_tee
            pass # for auto-indentation
        except Exception as e:
            logger.debug(f"pubrun failed to intercept console: {e}")
            self.stop() # rollback
            pass # for auto-indentation

    def stop(self) -> Dict[str, Any]:
        """
        Tears down the console hooks, closes the log files safely natively conditionally, and formats metrics sequentially gracefully properly specifically automatically flawlessly.

        Args:
            No arguments.

        Returns:
            Dict[str, Any]: A dynamically dictionary payload uniquely compliant explicitly natively with the expected schema format.

        Assumptions:
            - Teardown gracefully skips flushing logs if internal references are successfully statically elegantly selectively.

        Example:
            >>> stats = interceptor.stop()
        """
        # 1. Revert streams immediately to prevent interception of teardown logs
        sys.stdout = self.original_stdout
        sys.stderr = self.original_stderr
        
        lines_out = 0
        lines_err = 0
        
        if self.stdout_tee:
            self.stdout_tee.flush()
            lines_out = self.stdout_tee.line_count
            pass # for auto-indentation
        if self.stderr_tee:
            self.stderr_tee.flush()
            lines_err = self.stderr_tee.line_count
            pass # for auto-indentation
            
        if self.stdout_log:
            self.stdout_log.close()
            self.stdout_log = None
            pass # for auto-indentation
        if self.stderr_log:
            self.stderr_log.close()
            self.stderr_log = None
            pass # for auto-indentation
            
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
