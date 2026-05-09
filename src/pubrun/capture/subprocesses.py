import os
import subprocess
import logging
import shlex
import threading
import time
from contextlib import contextmanager
from typing import Any, List, Dict, Optional

_spy_local = threading.local()

@contextmanager
def disable_spy():
    """Context manager to bypass SubprocessSpy for internal pubrun commands."""
    old = getattr(_spy_local, "bypass", False)
    _spy_local.bypass = True
    try:
        yield
    finally:
        _spy_local.bypass = old


logger = logging.getLogger("pubrun")

_original_popen_init = subprocess.Popen.__init__
_original_popen_wait = subprocess.Popen.wait
_original_os_system = os.system

class SubprocessSpy:
    """Patches subprocess.Popen and os.system to record spawned processes transparently."""
    _installed = False
    _records: List[Dict[str, Any]] = []
    _max_records = 5000
    _truncated = False
    _lock = threading.Lock()
    _config: Optional[Dict[str, Any]] = None

    @classmethod
    def install(cls, max_records: int = 5000, config: Optional[Dict[str, Any]] = None) -> None:
        """Install monkey-patches on subprocess.Popen and os.system.

        Args:
            max_records: Stop recording after this many entries (memory safety).
            config: Resolved config, used for argv redaction.
        """
        if not cls._installed:
            cls._max_records = max_records
            cls._records = []
            cls._truncated = False
            cls._config = config
            subprocess.Popen.__init__ = cls._patched_popen_init
            subprocess.Popen.wait = cls._patched_popen_wait
            os.system = cls._patched_os_system
            cls._installed = True

    @classmethod
    def uninstall(cls) -> None:
        """Revert monkey-patches to their original implementations."""
        if cls._installed:
            subprocess.Popen.__init__ = _original_popen_init
            subprocess.Popen.wait = _original_popen_wait
            os.system = _original_os_system
            cls._installed = False

    @classmethod
    def get_records(cls) -> List[Dict[str, Any]]:
        return cls._records
        
    @classmethod
    def finalize_all(cls) -> None:
        """Mark any un-waited subprocess records as complete."""
        now_ts = time.time()
        with cls._lock:
            for rec in cls._records:
                if rec.get("exit_code") is None and "ended_at_utc" not in rec:
                    rec["ended_at_utc"] = now_ts
                    if rec.get("capture_state", {}).get("status") == "partial":
                        rec["capture_state"]["status"] = "complete"

    @staticmethod
    def _safe_shlex_split(args: Any) -> list:
        """Parse a command string into a list, falling back to [args] on failure."""
        if isinstance(args, str):
            try:
                return shlex.split(args)
            except ValueError:
                # Unterminated quotes or other parse errors — store raw string
                return [args]
        elif isinstance(args, (list, tuple)):
            return [str(a) for a in args]
        else:
            return [str(args)]

    @staticmethod
    def _patched_popen_init(self: Any, args: Any, *sys_args: Any, **kwargs: Any) -> None:
        if getattr(_spy_local, "bypass", False):
            return _original_popen_init(self, args, *sys_args, **kwargs)
            
        if len(SubprocessSpy._records) >= SubprocessSpy._max_records:
            SubprocessSpy._truncated = True
            return _original_popen_init(self, args, *sys_args, **kwargs)
            
        start_time = time.time()
        argv_list = SubprocessSpy._safe_shlex_split(args)

        # Redact sensitive values in argv before storing
        from pubrun.capture.redaction import redact_argv
        argv_list = redact_argv(argv_list, SubprocessSpy._config)

        kwargs_cwd = kwargs.get("cwd", None)
        cwd_str = str(kwargs_cwd) if kwargs_cwd else None
            
        try:
            _original_popen_init(self, args, *sys_args, **kwargs)
        except Exception as e:
            with SubprocessSpy._lock:
                SubprocessSpy._records.append({
                    "argv": argv_list,
                    "started_at_utc": start_time,
                    "cwd": cwd_str,
                    "capture_state": {"status": "failed", "detail": str(e)}
                })
            raise
            
        # Atomically assign index and append under the same lock
        with SubprocessSpy._lock:
            self._pubrun_idx = len(SubprocessSpy._records)
            SubprocessSpy._records.append({
                "argv": argv_list,
                "started_at_utc": start_time,
                "cwd": cwd_str,
                "exit_code": None,
                "capture_state": {"status": "partial"}
            })

    @staticmethod
    def _patched_popen_wait(self: Any, *args: Any, **kwargs: Any) -> int:
        exit_code = _original_popen_wait(self, *args, **kwargs)
        try:
            idx = getattr(self, "_pubrun_idx", None)
            with SubprocessSpy._lock:
                if idx is not None and idx < len(SubprocessSpy._records):
                    rec = SubprocessSpy._records[idx]
                    if rec.get("exit_code") is None:
                        rec["exit_code"] = exit_code
                        rec["ended_at_utc"] = time.time()
                        rec["capture_state"]["status"] = "complete" if exit_code == 0 else "failed"
        except Exception as e:
            logger.debug(f"pubrun failed to finalize subprocess record wait hook: {e}")
        return exit_code

    @staticmethod
    def _patched_os_system(command: str) -> int:
        if getattr(_spy_local, "bypass", False):
            return _original_os_system(command)
            
        if len(SubprocessSpy._records) >= SubprocessSpy._max_records:
            SubprocessSpy._truncated = True
            return _original_os_system(command)
            
        start_time = time.time()
        argv_list = SubprocessSpy._safe_shlex_split(command)

        # Redact sensitive values in argv before storing
        from pubrun.capture.redaction import redact_argv
        argv_list = redact_argv(argv_list, SubprocessSpy._config)

        with SubprocessSpy._lock:
            idx = len(SubprocessSpy._records)
            SubprocessSpy._records.append({
                "argv": argv_list,
                "started_at_utc": start_time,
                "cwd": None,
                "exit_code": None,
                "capture_state": {"status": "partial"}
            })
        
        try:
            exit_code = _original_os_system(command)
        except Exception as e:
            with SubprocessSpy._lock:
                SubprocessSpy._records[idx]["capture_state"] = {"status": "failed", "detail": str(e)}
            raise
            
        with SubprocessSpy._lock:
            SubprocessSpy._records[idx]["exit_code"] = exit_code
            SubprocessSpy._records[idx]["ended_at_utc"] = time.time()
            SubprocessSpy._records[idx]["capture_state"]["status"] = "complete" if exit_code == 0 else "failed"
        
        return exit_code
