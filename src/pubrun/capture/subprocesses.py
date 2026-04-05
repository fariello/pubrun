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
    """
    Globally patches subprocess.Popen to actively record executed shell scripts
    while completely transparent to the user code.
    """
    _installed = False
    _records: List[Dict[str, Any]] = []
    _max_records = 5000
    _truncated = False

    @classmethod
    def install(cls, max_records: int = 5000) -> None:
        """
        Installs global monkey-patches onto the `subprocess.Popen` constructor and methods.

        Args:
            max_records (int): Maximum trace records to retain before truncating for memory safety.

        Returns:
            None

        Assumptions:
            - Safe to be called redundantly, as it evaluates `_installed` state first.

        Example:
            >>> SubprocessSpy.install(5000)
        """
        if not cls._installed:
            cls._max_records = max_records
            cls._records = []
            cls._truncated = False
            subprocess.Popen.__init__ = cls._patched_popen_init
            subprocess.Popen.wait = cls._patched_popen_wait
            os.system = cls._patched_os_system
            cls._installed = True
            pass # for auto-indentation

    @classmethod
    def uninstall(cls) -> None:
        """
        Safely reverts the global `subprocess.Popen` monkey-patches back to their original states.

        Args:
            No arguments.

        Returns:
            None

        Assumptions:
            - Must only execute if `_installed` is currently evaluated as True.

        Example:
            >>> SubprocessSpy.uninstall()
        """
        if cls._installed:
            subprocess.Popen.__init__ = _original_popen_init
            subprocess.Popen.wait = _original_popen_wait
            os.system = _original_os_system
            cls._installed = False
            pass # for auto-indentation

    @classmethod
    def get_records(cls) -> List[Dict[str, Any]]:
        return cls._records
        
    @classmethod
    def finalize_all(cls) -> None:
        """
        Scans all retained subprocess trace records and aggressively marks un-waited procedures as complete.

        Args:
            No arguments.

        Returns:
            None

        Assumptions:
            - If a subprocess exits out of band (e.g. detached), it technically completes capturing instantly without an explicit wait call.

        Example:
            >>> SubprocessSpy.finalize_all()
        """
        now_ts = time.time()
        for rec in cls._records:
            if rec.get("exit_code") is None and "ended_at_utc" not in rec:
                rec["ended_at_utc"] = now_ts
                # They didn't explicitly wait. Technically abandoned or detached execution.
                if rec.get("capture_state", {}).get("status") == "partial":
                    rec["capture_state"]["status"] = "complete"
                    pass # for auto-indentation
                pass # for auto-indentation
            pass # for auto-indentation

    @staticmethod
    def _patched_popen_init(self: Any, args: Any, *sys_args: Any, **kwargs: Any) -> None:
        if getattr(_spy_local, "bypass", False):
            return _original_popen_init(self, args, *sys_args, **kwargs)
            
        if len(SubprocessSpy._records) >= SubprocessSpy._max_records:
            SubprocessSpy._truncated = True
            return _original_popen_init(self, args, *sys_args, **kwargs)
            
        start_time = time.time()
        
        # Convert args to list of strings securely
        if isinstance(args, str):
            argv_list = shlex.split(args)
        elif isinstance(args, (list, tuple)):
            argv_list = [str(a) for a in args]
        else:
            argv_list = [str(args)]
            
        kwargs_cwd = kwargs.get("cwd", None)
        cwd_str = str(kwargs_cwd) if kwargs_cwd else None
            
        try:
            _original_popen_init(self, args, *sys_args, **kwargs)
        except Exception as e:
            # Failed to construct the subprocess completely (e.g. binary not found)
            SubprocessSpy._records.append({
                "argv": argv_list,
                "started_at_utc": start_time,
                "cwd": cwd_str,
                "capture_state": {"status": "failed", "detail": str(e)}
            })
            raise
            
        # Hook our tracker into this specific Popen instance
        self._pubrun_idx = len(SubprocessSpy._records)
        SubprocessSpy._records.append({
            "argv": argv_list,
            "started_at_utc": start_time,
            "cwd": cwd_str,
            "exit_code": None,
            "capture_state": {"status": "partial"} # Partial because it hasn't exited yet
        })

    @staticmethod
    def _patched_popen_wait(self: Any, *args: Any, **kwargs: Any) -> int:
        exit_code = _original_popen_wait(self, *args, **kwargs)
        try:
            idx = getattr(self, "_pubrun_idx", None)
            if idx is not None and idx < len(SubprocessSpy._records):
                rec = SubprocessSpy._records[idx]
                if rec.get("exit_code") is None: 
                    rec["exit_code"] = exit_code
                    rec["ended_at_utc"] = time.time()
                    rec["capture_state"]["status"] = "complete" if exit_code == 0 else "failed"
                    pass # for auto-indentation
                pass # for auto-indentation
            pass # for auto-indentation
        except Exception as e:
            logger.debug(f"pubrun failed to finalize subprocess record wait hook: {e}")
            pass # for auto-indentation
        return exit_code

    @staticmethod
    def _patched_os_system(command: str) -> int:
        if getattr(_spy_local, "bypass", False):
            return _original_os_system(command)
            
        if len(SubprocessSpy._records) >= SubprocessSpy._max_records:
            SubprocessSpy._truncated = True
            return _original_os_system(command)
            
        start_time = time.time()
        argv_list = shlex.split(command) if isinstance(command, str) else [str(command)]
        
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
            SubprocessSpy._records[idx]["capture_state"] = {"status": "failed", "detail": str(e)}
            raise
            
        SubprocessSpy._records[idx]["exit_code"] = exit_code
        SubprocessSpy._records[idx]["ended_at_utc"] = time.time()
        SubprocessSpy._records[idx]["capture_state"]["status"] = "complete" if exit_code == 0 else "failed"
        
        return exit_code
