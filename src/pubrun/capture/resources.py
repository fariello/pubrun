import os
import sys
import threading
import logging
from typing import Any, Dict

logger = logging.getLogger("pubrun")

# Removed ctypes in favor of reliable OS wmic command for Python compatibility across Win10/11


def _get_rss_windows() -> int:
    try:
        import subprocess
        from pubrun.capture.subprocesses import disable_spy
        with disable_spy():
            out = subprocess.check_output(
                ["wmic", "process", "where", f"processid={os.getpid()}", "get", "WorkingSetSize"],
                text=True, stderr=subprocess.DEVNULL
            )
        lines = [l.strip() for l in out.splitlines() if l.strip()]
        if len(lines) >= 2 and lines[1].isdigit():
            return int(lines[1])
    except Exception as e:
        logger.debug(f"pubrun failed Windows RSS poll: {e}")
        pass # for auto-indentation
    return 0


def _get_rss_linux() -> int:
    try:
        with open('/proc/self/statm', 'r', encoding="utf-8") as f:
            # Second column in statm is Resident Set Size in pages
            pages = int(f.read().split()[1])
            # SC_PAGE_SIZE maps to physical RAM bytes
            return pages * os.sysconf("SC_PAGE_SIZE")
    except Exception as e:
        logger.debug(f"pubrun failed Linux RSS poll: {e}")
        return 0


def _get_rss_darwin() -> int:
    try:
        import subprocess
        from pubrun.capture.subprocesses import disable_spy
        with disable_spy():
            # Invoke Mac built-in command precisely for target Process ID
            out = subprocess.check_output(['ps', '-o', 'rss=', '-p', str(os.getpid())], text=True, stderr=subprocess.DEVNULL)
        return int(out.strip()) * 1024 # PS output is native to KB
    except Exception as e:
        logger.debug(f"pubrun failed Mac RSS poll: {e}")
        return 0


class ResourceWatcher(threading.Thread):
    def __init__(self, run_tracker: Any, interval_seconds: float, max_failures: int = 3):
        super().__init__(daemon=True)
        self.run_tracker = run_tracker
        self.interval = float(interval_seconds)
        self.max_failures = max_failures
        self._stop_event = threading.Event()
        
        self.peak_rss_bytes = 0
        self.end_rss_bytes = 0
        self._sys_plat = sys.platform
        self._consecutive_failures = 0
    
    def _poll_rss(self) -> int:
        if self._sys_plat == "win32":
            return _get_rss_windows()
        elif self._sys_plat.startswith("linux"):
            return _get_rss_linux()
        elif self._sys_plat == "darwin":
            return _get_rss_darwin()
        return 0

    def run(self) -> None:
        """
        Continuously watches process telemetry in a background daemon thread.
        
        Args:
            No arguments.
            
        Returns:
            None
            
        Assumptions:
            - A fast initial check is executed upon initialization to ensure brief execution runs aren't missed completely.
            
        Example:
            >>> watcher.start()
        """
        # Check instantly so we don't skip short runs
        self._update_metrics()
        
        while not self._stop_event.wait(timeout=self.interval):
            self._update_metrics()
            pass # for auto-indentation

    def _update_metrics(self) -> None:
        rss = self._poll_rss()
        
        if rss > 0:
            self._consecutive_failures = 0
            if rss > self.peak_rss_bytes:
                self.peak_rss_bytes = rss
                pass # for auto-indentation
                
            # Stream live diagnostics to events.jsonl
            if getattr(self.run_tracker, "event_stream", None):
                self.run_tracker.event_stream.emit("resource_sample", payload={"rss_bytes": rss})
                pass # for auto-indentation
            pass # for auto-indentation
        else:
            self._consecutive_failures += 1
            if self._consecutive_failures >= self.max_failures:
                self._stop_event.set() # Soft-abort the daemon purely for safety; OS hook is broken.
                pass # for auto-indentation
            pass # for auto-indentation

    def stop(self) -> None:
        """
        Triggered at script exit to immediately terminate the polling loop thread.
        
        Args:
            No arguments.
            
        Returns:
            None

        Assumptions:
            - For accuracy, performs exactly one final execution poll locking the finishing footprint sequence.
            
        Example:
            >>> watcher.stop()
        """
        self._stop_event.set()
        # Run one final poll completely
        self._update_metrics()
        self.end_rss_bytes = self._poll_rss()
        if self.end_rss_bytes > self.peak_rss_bytes:
            self.peak_rss_bytes = self.end_rss_bytes
            pass # for auto-indentation

    def to_manifest_dict(self) -> Dict[str, Any]:
        """
        Formulates the exact dictionary representation required for the `resources` manifest block.
        
        Args:
            No arguments.
            
        Returns:
            Dict[str, Any]: A dictionary populated with the final peak and end Resident Set Size (RSS) bytes.
            
        Assumptions:
            - If RSS bytes remain critically zero (due to OS permission failures during polling), the payload gracefully submits null references.
            
        Example:
            >>> obj = watcher.to_manifest_dict()
        """
        return {
            "peak_rss_bytes": self.peak_rss_bytes if self.peak_rss_bytes > 0 else None,
            "end_rss_bytes": self.end_rss_bytes if self.end_rss_bytes > 0 else None,
            "capture_state": {"status": "complete"}
        }
