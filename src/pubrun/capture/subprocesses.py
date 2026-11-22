import os
import subprocess
import logging
import shlex
import threading
import time
from contextlib import contextmanager
from typing import Any, List, Dict, Optional

_spy_local = threading.local()


def _spy_depth() -> int:
    """Current per-thread bypass depth (0 = recording, >0 = bypassed)."""
    return getattr(_spy_local, "depth", 0)


def _spy_bypassed() -> bool:
    """True if subprocess recording is suspended on the calling thread."""
    return _spy_depth() > 0


def pause_spy() -> None:
    """Suspend subprocess recording on the CALLING thread (ref-counted).

    Composes with nesting and with disable_spy(): each pause increments a
    per-thread depth counter; recording resumes only when it returns to 0.
    """
    _spy_local.depth = _spy_depth() + 1


def resume_spy() -> None:
    """Undo one pause_spy() on the calling thread (never goes below 0)."""
    _spy_local.depth = max(0, _spy_depth() - 1)


@contextmanager
def disable_spy():
    """Context manager to bypass SubprocessSpy for internal pubrun commands.

    Re-expressed on the same per-thread ref-counted depth as the public
    pause/resume, so internal bypass spans and user ``pubrun.paused()`` blocks
    compose additively (neither resets the other).
    """
    pause_spy()
    try:
        yield
    finally:
        resume_spy()


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
    _owner: Optional[object] = None
    _active_state: Optional[Dict[str, Any]] = None
    _installed_popen_init: Optional[Any] = None
    _installed_popen_wait: Optional[Any] = None
    _installed_os_system: Optional[Any] = None

    @classmethod
    def install(
        cls,
        max_records: int = 5000,
        config: Optional[Dict[str, Any]] = None,
        owner: Optional[object] = None,
    ) -> bool:
        """Install monkey-patches on subprocess.Popen and os.system transactionally.

        Captures the live pre-existing targets at install time, chains to them, and
        rolls back any already-patched target if a later patch raises.

        Args:
            max_records: Stop recording after this many entries (memory safety).
            config: Resolved config, used for argv and error-detail redaction.
            owner: Optional ownership token that guards subsequent uninstall calls.

        Returns:
            True if this call installed the spy; False if already installed.
        """
        with cls._lock:
            if cls._installed:
                return False

            prev_popen_init = subprocess.Popen.__init__
            prev_popen_wait = subprocess.Popen.wait
            prev_os_system = os.system

            state: Dict[str, Any] = {
                "active": True,
                "config": config,
                "prev_popen_init": prev_popen_init,
                "prev_popen_wait": prev_popen_wait,
                "prev_os_system": prev_os_system,
            }

            def _patched_popen_init(
                self: Any, args: Any, *sys_args: Any, **kwargs: Any
            ) -> None:
                if not state["active"] or _spy_bypassed():
                    return prev_popen_init(self, args, *sys_args, **kwargs)

                with cls._lock:
                    if not state["active"]:
                        should_record = False
                    elif len(cls._records) >= cls._max_records:
                        cls._truncated = True
                        should_record = False
                    else:
                        should_record = True

                if not should_record:
                    return prev_popen_init(self, args, *sys_args, **kwargs)

                start_time = time.time()
                argv_list = cls._safe_shlex_split(args)

                from pubrun.capture.redaction import (
                    format_safe_error_detail,
                    redact_argv,
                )
                try:
                    argv_list = redact_argv(argv_list, state["config"])
                except Exception:
                    argv_list = []

                kwargs_cwd = kwargs.get("cwd", None)
                cwd_str = str(kwargs_cwd) if kwargs_cwd else None

                try:
                    prev_popen_init(self, args, *sys_args, **kwargs)
                except Exception as e:
                    detail = format_safe_error_detail(e, state["config"])
                    with cls._lock:
                        if state["active"]:
                            cls._records.append({
                                "argv": argv_list,
                                "started_at_utc": start_time,
                                "cwd": cwd_str,
                                "capture_state": {"status": "failed", "detail": detail},
                            })
                    raise

                rec: Dict[str, Any] = {
                    "argv": argv_list,
                    "started_at_utc": start_time,
                    "cwd": cwd_str,
                    "exit_code": None,
                    "capture_state": {"status": "partial"},
                }
                with cls._lock:
                    if state["active"]:
                        self._pubrun_state = state
                        self._pubrun_rec = rec
                        self._pubrun_idx = len(cls._records)
                        cls._records.append(rec)

            def _patched_popen_wait(self: Any, *args: Any, **kwargs: Any) -> int:
                exit_code = prev_popen_wait(self, *args, **kwargs)
                if not state["active"]:
                    return exit_code
                try:
                    with cls._lock:
                        if (
                            state["active"]
                            and getattr(self, "_pubrun_state", None) is state
                        ):
                            rec = getattr(self, "_pubrun_rec", None)
                            if rec is not None and rec.get("exit_code") is None:
                                rec["exit_code"] = exit_code
                                rec["ended_at_utc"] = time.time()
                                rec["capture_state"]["status"] = (
                                    "complete" if exit_code == 0 else "failed"
                                )
                except Exception as e:
                    logger.debug(
                        f"pubrun failed to finalize subprocess record wait hook: {e}"
                    )
                return exit_code

            def _patched_os_system(command: str) -> int:
                if not state["active"] or _spy_bypassed():
                    return prev_os_system(command)

                with cls._lock:
                    if not state["active"]:
                        should_record = False
                    elif len(cls._records) >= cls._max_records:
                        cls._truncated = True
                        should_record = False
                    else:
                        should_record = True

                if not should_record:
                    return prev_os_system(command)

                start_time = time.time()
                argv_list = cls._safe_shlex_split(command)

                from pubrun.capture.redaction import (
                    format_safe_error_detail,
                    redact_argv,
                )
                try:
                    argv_list = redact_argv(argv_list, state["config"])
                except Exception:
                    argv_list = []

                rec: Dict[str, Any] = {
                    "argv": argv_list,
                    "started_at_utc": start_time,
                    "cwd": None,
                    "exit_code": None,
                    "capture_state": {"status": "partial"},
                }
                with cls._lock:
                    if state["active"]:
                        cls._records.append(rec)

                try:
                    exit_code = prev_os_system(command)
                except Exception as e:
                    detail = format_safe_error_detail(e, state["config"])
                    with cls._lock:
                        if state["active"]:
                            rec["capture_state"] = {
                                "status": "failed",
                                "detail": detail,
                            }
                    raise

                with cls._lock:
                    if state["active"]:
                        rec["exit_code"] = exit_code
                        rec["ended_at_utc"] = time.time()
                        rec["capture_state"]["status"] = (
                            "complete" if exit_code == 0 else "failed"
                        )

                return exit_code

            cls._max_records = max_records
            cls._records = []
            cls._truncated = False
            cls._config = config

            patched: List[tuple] = []
            targets = [
                (subprocess.Popen, "__init__", _patched_popen_init, prev_popen_init),
                (subprocess.Popen, "wait", _patched_popen_wait, prev_popen_wait),
                (os, "system", _patched_os_system, prev_os_system),
            ]
            try:
                for target_obj, attr_name, wrapper, previous in targets:
                    setattr(target_obj, attr_name, wrapper)
                    patched.append((target_obj, attr_name, wrapper, previous))
            except Exception:
                state["active"] = False
                for target_obj, attr_name, wrapper, previous in reversed(patched):
                    try:
                        if getattr(target_obj, attr_name, None) is wrapper:
                            setattr(target_obj, attr_name, previous)
                    except Exception:
                        pass
                cls._installed = False
                cls._owner = None
                cls._active_state = None
                cls._installed_popen_init = None
                cls._installed_popen_wait = None
                cls._installed_os_system = None
                raise

            cls._active_state = state
            cls._installed_popen_init = _patched_popen_init
            cls._installed_popen_wait = _patched_popen_wait
            cls._installed_os_system = _patched_os_system
            cls._owner = owner
            cls._installed = True
            return True

    @classmethod
    def uninstall(cls, owner: Optional[object] = None) -> None:
        """Deactivate recording and restore still-owned targets independently."""
        with cls._lock:
            if not cls._installed:
                return
            if owner is not None and cls._owner is not None and owner is not cls._owner:
                return

            state = cls._active_state
            if state is not None:
                state["active"] = False
                restores = [
                    (
                        subprocess.Popen,
                        "__init__",
                        cls._installed_popen_init,
                        state["prev_popen_init"],
                    ),
                    (
                        subprocess.Popen,
                        "wait",
                        cls._installed_popen_wait,
                        state["prev_popen_wait"],
                    ),
                    (
                        os,
                        "system",
                        cls._installed_os_system,
                        state["prev_os_system"],
                    ),
                ]
                for target_obj, attr_name, installed_wrapper, previous in restores:
                    try:
                        if (
                            installed_wrapper is not None
                            and getattr(target_obj, attr_name, None)
                            is installed_wrapper
                        ):
                            setattr(target_obj, attr_name, previous)
                    except Exception:
                        pass

            cls._installed = False
            cls._owner = None
            cls._active_state = None
            cls._installed_popen_init = None
            cls._installed_popen_wait = None
            cls._installed_os_system = None
            # BUG-09: Clear records on uninstall to prevent cross-run leakage.
            cls._records = []
            cls._truncated = False

    @classmethod
    def get_records(cls) -> List[Dict[str, Any]]:
        return cls._records

    @staticmethod
    def pause() -> None:
        """Pausable contract: suspend subprocess recording on the calling thread."""
        pause_spy()

    @staticmethod
    def resume() -> None:
        """Pausable contract: resume subprocess recording on the calling thread."""
        resume_spy()

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
