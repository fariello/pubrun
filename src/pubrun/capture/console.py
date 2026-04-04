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
    def __init__(self, original_stream: TextIO, log_file: Optional[TextIO]):
        """
        Initializes the TqdmSafeTee stream wrapper.
        
        Args:
            original_stream: The original output stream to pass data to (e.g., sys.stdout).
            log_file: An optional file-like object to tee the text to. If None,
                      data is just passed to the original stream.
        """
        self.original_stream = original_stream
        self.log_file = log_file
        self.line_count = 0
        self._current_buffer = ""
        
    def write(self, data: str) -> int:
        """
        Writes data to the original stream and to the log file (safely squashing progress bars).
        
        Args:
            data: The string to write.
            
        Returns:
            The number of characters written to the original stream.
        """
        # 1. Passthrough exactly what was originally sent to the user's console
        ret = self.original_stream.write(data)
        
        # If logging is disabled or file is closed, simply return what was written
        if not self.log_file or self.log_file.closed:
            return ret
            
        try:
            # 2. Process strings for log file safely (handling carriage returns aka TQDM interception)
            for char in data:
                if char == '\r':
                    # Progress bar carriage return - dump the line buffer invisibly
                    self._current_buffer = ""
                elif char == '\n':
                    self.log_file.write(self._current_buffer + '\n')
                    self.line_count += 1
                    self._current_buffer = ""
                else:
                    self._current_buffer += char
        except Exception as e:
            logger.debug(f"pubrun tee internal error: {e}")
            
        return ret
        
    def flush(self) -> None:
        """
        Flushes both the underlying original stream and the internal log file.
        Any remaining characters in the line buffer are written out before flushing.
        """
        self.original_stream.flush()
        if self.log_file and not self.log_file.closed:
            # Dump whatever is left in the buffer on a flush
            if self._current_buffer:
                self.log_file.write(self._current_buffer + '\n')
                self.line_count += 1
                self._current_buffer = ""
            self.log_file.flush()
            
    def __getattr__(self, name: str) -> Any:
        """
        Delegates standard stream attributes and methods (like isatty, encoding)
        to the original stream wrapper to ensure full compatibility.
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
    def __init__(self, run_dir: Path, mode: str):
        """
        Initializes the ConsoleInterceptor.
        
        Args:
            run_dir: The directory path where `stdout.log` and `stderr.log` will be created.
            mode: The capture mode (e.g., 'off', 'basic', 'standard', 'deep'). If 'off',
                  interception is disabled.
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
        Starts intercepting sys.stdout and sys.stderr. 
        Creates log files and patches the system streams if the mode is not 'off'.
        If an error occurs during setup, silently reverts back to original streams.
        """
        if self.mode == "off":
            return
            
        try:
            self.stdout_log = open(self.run_dir / "stdout.log", "w", encoding="utf-8")
            self.stderr_log = open(self.run_dir / "stderr.log", "w", encoding="utf-8")
            
            self.stdout_tee = TqdmSafeTee(sys.stdout, self.stdout_log)
            sys.stdout = self.stdout_tee
            
            self.stderr_tee = TqdmSafeTee(sys.stderr, self.stderr_log)
            sys.stderr = self.stderr_tee
        except Exception as e:
            logger.debug(f"pubrun failed to intercept console: {e}")
            self.stop() # rollback

    def stop(self) -> Dict[str, Any]:
        """
        Tears down the console hooks, closes the log files, and formats the 
        recorded metrics for inclusion in the run manifest.
        
        Returns:
            A dictionary conforming to the manifest schema for the 'console' section,
            reporting captured files, modes, and line count statistics.
        """
        # 1. Revert streams immediately to prevent interception of teardown logs
        sys.stdout = self.original_stdout
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
