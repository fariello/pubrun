import subprocess
import logging
import shlex
from datetime import datetime, timezone
from typing import Any, List, Dict, Optional

logger = logging.getLogger("runtrace")

_original_popen_init = subprocess.Popen.__init__
_original_popen_wait = subprocess.Popen.wait

class SubprocessSpy:
    """
    Globally patches subprocess.Popen to actively record executed shell scripts
    while completely transparent to the user code.
    """
    _installed = False
    _records: List[Dict[str, Any]] = []

    @classmethod
    def install(cls) -> None:
        if not cls._installed:
            cls._records = []
            subprocess.Popen.__init__ = cls._patched_popen_init
            subprocess.Popen.wait = cls._patched_popen_wait
            cls._installed = True

    @classmethod
    def uninstall(cls) -> None:
        if cls._installed:
            subprocess.Popen.__init__ = _original_popen_init
            subprocess.Popen.wait = _original_popen_wait
            cls._installed = False

    @classmethod
    def get_records(cls) -> List[Dict[str, Any]]:
        return cls._records
        
    @classmethod
    def finalize_all(cls) -> None:
        """Mark un-waited sub-processes upon exiting tracing."""
        now_str = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
        for rec in cls._records:
            if rec.get("exit_code") is None and "ended_at_utc" not in rec:
                rec["ended_at_utc"] = now_str
                # They didn't explicitly wait. Technically abandoned or detached execution.
                if rec.get("capture_state", {}).get("status") == "partial":
                    rec["capture_state"]["status"] = "complete"

    @staticmethod
    def _patched_popen_init(self: Any, args: Any, *sys_args: Any, **kwargs: Any) -> None:
        start_time = datetime.now(timezone.utc)
        
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
                "started_at_utc": start_time.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z",
                "cwd": cwd_str,
                "capture_state": {"status": "failed", "detail": str(e)}
            })
            raise
            
        # Hook our tracker into this specific Popen instance
        self._runtrace_idx = len(SubprocessSpy._records)
        SubprocessSpy._records.append({
            "argv": argv_list,
            "started_at_utc": start_time.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z",
            "cwd": cwd_str,
            "exit_code": None,
            "capture_state": {"status": "partial"} # Partial because it hasn't exited yet
        })

    @staticmethod
    def _patched_popen_wait(self: Any, *args: Any, **kwargs: Any) -> int:
        exit_code = _original_popen_wait(self, *args, **kwargs)
        try:
            idx = getattr(self, "_runtrace_idx", None)
            if idx is not None and idx < len(SubprocessSpy._records):
                rec = SubprocessSpy._records[idx]
                if rec.get("exit_code") is None: 
                    rec["exit_code"] = exit_code
                    rec["ended_at_utc"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
                    rec["capture_state"]["status"] = "complete" if exit_code == 0 else "failed"
        except Exception as e:
            logger.debug(f"runtrace failed to finalize subprocess record wait hook: {e}")
        return exit_code
