import sys
import logging
from typing import TextIO, Dict, Any, Optional
from pathlib import Path

logger = logging.getLogger("runtrace")

class TqdmSafeTee:
    """
    Tees standard outputs while stripping carriage return (\r) sequences.
    This dynamically squashes Data Science progress bars so the resulting
    text log file doesn't explode to 2 gigabytes during long training loops.
    """
    def __init__(self, original_stream: TextIO, log_file: Optional[TextIO]):
        self.original_stream = original_stream
        self.log_file = log_file
        self.line_count = 0
        self._current_buffer = ""
        
    def write(self, data: str) -> int:
        # 1. Passthrough exactly what was originally sent to the user's console
        ret = self.original_stream.write(data)
        
        if not self.log_file or self.log_file.closed:
            return ret
            
        try:
            # 2. Process for log file safely (TQDM interception)
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
            logger.debug(f"runtrace tee internal error: {e}")
            
        return ret
        
    def flush(self) -> None:
        self.original_stream.flush()
        if self.log_file and not self.log_file.closed:
            if self._current_buffer:
                self.log_file.write(self._current_buffer + '\n')
                self.line_count += 1
                self._current_buffer = ""
            self.log_file.flush()
            
    def __getattr__(self, name: str) -> Any:
        return getattr(self.original_stream, name)


class ConsoleInterceptor:
    def __init__(self, run_dir: Path, mode: str):
        self.run_dir = run_dir
        self.mode = mode
        self.stdout_log = None
        self.stderr_log = None
        self.stdout_tee = None
        self.stderr_tee = None
        
        self.original_stdout = sys.stdout
        self.original_stderr = sys.stderr

    def start(self) -> None:
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
            logger.debug(f"runtrace failed to intercept console: {e}")
            self.stop() # rollback

    def stop(self) -> Dict[str, Any]:
        """Tears down hooks and returns the 'console' metrics spec dict."""
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
