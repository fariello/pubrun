import collections
import logging
import os
import shlex
import subprocess
import sys
import threading
import time
import weakref
from contextlib import contextmanager
from typing import Any, Deque, Dict, List, Optional, Tuple

from pubrun.capture.signals import finalization_lock

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
_original_popen_poll = subprocess.Popen.poll
_original_popen_del = subprocess.Popen.__del__
_original_os_system = os.system

_UNWAITED_DETAIL = "child process not waited on before finalization"
_EXTERNAL_REAP_DETAIL = (
    "child exit status was collected outside pubrun and is unavailable"
)


def _decode_wait_status(status: Any) -> Any:
    """Convert an ``os.system`` return value to a process exit code for recording.

    On POSIX ``os.system`` returns a wait status (exit 1 -> 256); on Windows it
    already returns the exit code. A signal-terminated child decodes to
    ``-signum`` (matching ``subprocess``). Undecodable values are returned as-is.
    """
    if os.name != "posix" or not isinstance(status, int) or isinstance(status, bool):
        return status
    converter = getattr(os, "waitstatus_to_exitcode", None)
    if converter is not None:
        try:
            return converter(status)
        except ValueError:
            return status
    # Python 3.8 fallback.
    if sys.platform == "win32":
        return status
    try:
        if os.WIFEXITED(status):
            return os.WEXITSTATUS(status)
        if os.WIFSIGNALED(status):
            return -os.WTERMSIG(status)
    except (ValueError, OverflowError):
        pass
    return status

class SubprocessSpy:
    """Patches subprocess.Popen and os.system to record spawned processes transparently."""
    _installed = False
    _records: List[Dict[str, Any]] = []
    _start_monos: Dict[int, Tuple[Dict[str, Any], float]] = {}
    _popen_refs: Dict[int, Tuple[Dict[str, Any], Any]] = {}
    _pending_exits: Deque[Tuple[Dict[str, Any], Any, float, float]] = collections.deque()
    _pending_running: Deque[Any] = collections.deque()
    _max_records = 5000
    _truncated = False
    _lock = threading.Lock()
    _config: Optional[Dict[str, Any]] = None
    _owner: Optional[object] = None
    _active_state: Optional[Dict[str, Any]] = None
    _installed_popen_init: Optional[Any] = None
    _installed_popen_wait: Optional[Any] = None
    _installed_popen_poll: Optional[Any] = None
    _installed_popen_del: Optional[Any] = None
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
            prev_popen_poll = subprocess.Popen.poll
            prev_popen_del = subprocess.Popen.__del__
            prev_os_system = os.system

            # Bind wall and monotonic clocks at install time so __del__ works
            # even if module globals are cleared during interpreter shutdown.
            _now_wall = time.time
            _now_mono = time.perf_counter

            pending_exits: Deque[
                Tuple[Dict[str, Any], Any, float, float]
            ] = collections.deque()
            pending_running: Deque[Any] = collections.deque()

            state: Dict[str, Any] = {
                "active": True,
                "config": config,
                "prev_popen_init": prev_popen_init,
                "prev_popen_wait": prev_popen_wait,
                "prev_popen_poll": prev_popen_poll,
                "prev_popen_del": prev_popen_del,
                "prev_os_system": prev_os_system,
                "pending_exits": pending_exits,
                "pending_running": pending_running,
            }

            def _complete_record(
                rec: Dict[str, Any],
                exit_code: Any,
                end_ts: float,
                end_mono: float,
            ) -> None:
                """Record a child's observed exit or unavailable status once under _lock."""
                if exit_code is None or not state["active"]:
                    return
                if rec.get("exit_code") is not None:
                    return
                try:
                    with finalization_lock(cls._lock, 0.25):
                        if not state["active"] or rec.get("exit_code") is not None:
                            return
                        cls._popen_refs.pop(id(rec), None)
                        entry = cls._start_monos.pop(id(rec), None)
                        if entry is not None and entry[0] is rec:
                            rec["elapsed_seconds"] = max(0.0, end_mono - entry[1])
                            rec["duration_clock"] = "monotonic"
                        if exit_code == sys.maxsize and not isinstance(exit_code, bool):
                            rec["ended_at_utc"] = None
                            rec["capture_state"] = {
                                "status": "partial",
                                "detail": _EXTERNAL_REAP_DETAIL,
                            }
                        else:
                            rec["exit_code"] = exit_code
                            rec["ended_at_utc"] = end_ts
                            rec["capture_state"] = {
                                "status": "complete" if exit_code == 0 else "failed"
                            }
                except Exception as e:
                    logger.debug(
                        f"pubrun failed to finalize subprocess record: {e}"
                    )

            def _drain() -> None:
                """Drain lock-free Popen.__del__ queues outside SubprocessSpy._lock."""
                if not state["active"]:
                    return
                while True:
                    try:
                        rec, exit_code, end_ts, end_mono = pending_exits.popleft()
                    except IndexError:
                        break
                    _complete_record(rec, exit_code, end_ts, end_mono)

                still_running: List[Any] = []
                while True:
                    try:
                        proc = pending_running.popleft()
                    except IndexError:
                        break
                    rc = getattr(proc, "returncode", None)
                    if rc is not None:
                        proc_rec: Optional[Dict[str, Any]] = getattr(proc, "_pubrun_rec", None)
                        if proc_rec is not None:
                            _complete_record(proc_rec, rc, time.time(), time.perf_counter())
                    else:
                        still_running.append(proc)
                if still_running and state["active"]:
                    pending_running.extend(still_running)

            def _safe_drain() -> None:
                try:
                    _drain()
                except Exception as e:
                    logger.debug(
                        f"pubrun failed to drain subprocess exit queues: {e}"
                    )

            state["drain"] = _drain
            state["complete_record"] = _complete_record

            def _patched_popen_init(
                self: Any, args: Any, *sys_args: Any, **kwargs: Any
            ) -> None:
                if not state["active"] or _spy_bypassed():
                    try:
                        return prev_popen_init(self, args, *sys_args, **kwargs)
                    finally:
                        if state["active"]:
                            _safe_drain()

                with cls._lock:
                    if not state["active"]:
                        should_record = False
                    elif len(cls._records) >= cls._max_records:
                        cls._truncated = True
                        should_record = False
                    else:
                        should_record = True

                if not should_record:
                    try:
                        return prev_popen_init(self, args, *sys_args, **kwargs)
                    finally:
                        if state["active"]:
                            _safe_drain()

                start_time = time.time()
                start_mono = time.perf_counter()
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
                    end_ts = time.time()
                    end_mono = time.perf_counter()
                    detail = format_safe_error_detail(e, state["config"])
                    with cls._lock:
                        if state["active"]:
                            cls._records.append({
                                "argv": argv_list,
                                "started_at_utc": start_time,
                                "ended_at_utc": end_ts,
                                "elapsed_seconds": max(0.0, end_mono - start_mono),
                                "duration_clock": "monotonic",
                                "cwd": cwd_str,
                                "capture_state": {"status": "failed", "detail": detail},
                            })
                    raise
                finally:
                    _safe_drain()

                rec: Dict[str, Any] = {
                    "argv": argv_list,
                    "started_at_utc": start_time,
                    "cwd": cwd_str,
                    "exit_code": None,
                    "capture_state": {"status": "partial"},
                }
                try:
                    popen_ref: Optional[Any] = weakref.ref(self)
                except TypeError:
                    popen_ref = None
                with cls._lock:
                    if state["active"]:
                        self._pubrun_state = state
                        self._pubrun_rec = rec
                        self._pubrun_idx = len(cls._records)
                        cls._records.append(rec)
                        cls._start_monos[id(rec)] = (rec, start_mono)
                        if popen_ref is not None:
                            cls._popen_refs[id(rec)] = (rec, popen_ref)

            def _complete_popen_record(self: Any, exit_code: Any) -> None:
                """Record a reaped child's exit once (idempotent across wait/poll)."""
                if exit_code is None or not state["active"]:
                    return
                if getattr(self, "_pubrun_state", None) is not state:
                    return
                rec = getattr(self, "_pubrun_rec", None)
                if rec is None or rec.get("exit_code") is not None:
                    # Already recorded: repeated poll() calls stay cheap.
                    return
                _complete_record(rec, exit_code, time.time(), time.perf_counter())

            def _patched_popen_wait(self: Any, *args: Any, **kwargs: Any) -> int:
                exit_code = prev_popen_wait(self, *args, **kwargs)
                _complete_popen_record(self, exit_code)
                return exit_code

            def _patched_popen_poll(self: Any, *args: Any, **kwargs: Any) -> Any:
                exit_code = prev_popen_poll(self, *args, **kwargs)
                _complete_popen_record(self, exit_code)
                return exit_code

            def _patched_popen_del(self: Any, *args: Any, **kwargs: Any) -> None:
                try:
                    prev_popen_del(self, *args, **kwargs)
                finally:
                    try:
                        if (
                            getattr(self, "_pubrun_state", None) is state
                            and state["active"]
                        ):
                            rc = getattr(self, "returncode", None)
                            if rc is None:
                                pending_running.append(self)
                            else:
                                rec = getattr(self, "_pubrun_rec", None)
                                if rec is not None and rec.get("exit_code") is None:
                                    pending_exits.append(
                                        (rec, rc, _now_wall(), _now_mono())
                                    )
                    except Exception:
                        pass

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
                start_mono = time.perf_counter()
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
                        cls._start_monos[id(rec)] = (rec, start_mono)

                try:
                    exit_code = prev_os_system(command)
                except Exception as e:
                    end_ts = time.time()
                    end_mono = time.perf_counter()
                    detail = format_safe_error_detail(e, state["config"])
                    with cls._lock:
                        if state["active"]:
                            rec["ended_at_utc"] = end_ts
                            entry = cls._start_monos.pop(id(rec), None)
                            if entry is not None and entry[0] is rec:
                                rec["elapsed_seconds"] = max(0.0, end_mono - entry[1])
                                rec["duration_clock"] = "monotonic"
                            elif "elapsed_seconds" not in rec:
                                rec["elapsed_seconds"] = max(0.0, end_mono - start_mono)
                                rec["duration_clock"] = "monotonic"
                            rec["capture_state"] = {
                                "status": "failed",
                                "detail": detail,
                            }
                    raise

                end_ts = time.time()
                end_mono = time.perf_counter()
                # The host receives the raw wait status unchanged; only the
                # recorded value is decoded to a real exit code.
                recorded_code = _decode_wait_status(exit_code)
                with cls._lock:
                    if state["active"]:
                        rec["exit_code"] = recorded_code
                        rec["ended_at_utc"] = end_ts
                        entry = cls._start_monos.pop(id(rec), None)
                        if entry is not None and entry[0] is rec:
                            rec["elapsed_seconds"] = max(0.0, end_mono - entry[1])
                            rec["duration_clock"] = "monotonic"
                        elif "elapsed_seconds" not in rec:
                            rec["elapsed_seconds"] = max(0.0, end_mono - start_mono)
                            rec["duration_clock"] = "monotonic"
                        rec["capture_state"]["status"] = (
                            "complete" if recorded_code == 0 else "failed"
                        )

                return exit_code

            cls._max_records = max_records
            cls._records = []
            cls._start_monos = {}
            cls._popen_refs = {}
            cls._pending_exits = pending_exits
            cls._pending_running = pending_running
            cls._truncated = False
            cls._config = config

            patched: List[tuple] = []
            targets = [
                (subprocess.Popen, "__init__", _patched_popen_init, prev_popen_init),
                (subprocess.Popen, "wait", _patched_popen_wait, prev_popen_wait),
                (subprocess.Popen, "poll", _patched_popen_poll, prev_popen_poll),
                (subprocess.Popen, "__del__", _patched_popen_del, prev_popen_del),
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
                cls._installed_popen_poll = None
                cls._installed_popen_del = None
                cls._installed_os_system = None
                cls._popen_refs = {}
                cls._pending_exits = collections.deque()
                cls._pending_running = collections.deque()
                raise

            cls._active_state = state
            cls._installed_popen_init = _patched_popen_init
            cls._installed_popen_wait = _patched_popen_wait
            cls._installed_popen_poll = _patched_popen_poll
            cls._installed_popen_del = _patched_popen_del
            cls._installed_os_system = _patched_os_system
            cls._owner = owner
            cls._installed = True
            return True

    @classmethod
    def uninstall(cls, owner: Optional[object] = None) -> None:
        """Deactivate recording and restore still-owned targets independently."""
        with finalization_lock(cls._lock, 0.25):
            if not cls._installed:
                return
            if owner is not None and cls._owner is not None and owner is not cls._owner:
                return

            state = cls._active_state
            if state is not None:
                state["active"] = False
                state["pending_exits"].clear()
                state["pending_running"].clear()
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
                        subprocess.Popen,
                        "poll",
                        cls._installed_popen_poll,
                        state["prev_popen_poll"],
                    ),
                    (
                        subprocess.Popen,
                        "__del__",
                        cls._installed_popen_del,
                        state["prev_popen_del"],
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
            cls._installed_popen_poll = None
            cls._installed_popen_del = None
            cls._installed_os_system = None
            # BUG-09: Clear records on uninstall to prevent cross-run leakage.
            cls._records = []
            cls._start_monos = {}
            cls._popen_refs = {}
            cls._pending_exits = collections.deque()
            cls._pending_running = collections.deque()
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
        """Harvest observable exit codes and mark unobserved unwaited records partial."""
        with finalization_lock(cls._lock, 0.25):
            state = cls._active_state

        if state is not None and state.get("active"):
            # Phase 1: Drain exits and reaped objects queued by Popen.__del__.
            try:
                state["drain"]()
            except Exception as e:
                logger.debug(
                    f"pubrun failed to drain subprocess queues at finalization: {e}"
                )

            # Phase 2: Collect live Popen objects for open records under _lock.
            live_procs: List[Tuple[Dict[str, Any], Any]] = []
            seen_rec_ids = set()
            with finalization_lock(cls._lock, 0.25):
                for rec in list(cls._records):
                    if rec.get("exit_code") is None and "ended_at_utc" not in rec:
                        rec_id = id(rec)
                        ref_entry = cls._popen_refs.get(rec_id)
                        if ref_entry is not None and ref_entry[0] is rec:
                            proc = ref_entry[1]()
                            if proc is not None:
                                live_procs.append((rec, proc))
                                seen_rec_ids.add(rec_id)
                pending_running = state["pending_running"]
                while True:
                    try:
                        proc = pending_running.popleft()
                    except IndexError:
                        break
                    proc_rec: Optional[Dict[str, Any]] = getattr(proc, "_pubrun_rec", None)
                    if (
                        proc_rec is not None
                        and proc_rec.get("exit_code") is None
                        and "ended_at_utc" not in proc_rec
                        and id(proc_rec) not in seen_rec_ids
                    ):
                        live_procs.append((proc_rec, proc))
                        seen_rec_ids.add(id(proc_rec))

            # Phase 3: Poll each live Popen once outside _lock.
            prev_poll = state["prev_popen_poll"]
            complete_record = state["complete_record"]
            for rec, proc in live_procs:
                try:
                    rc = prev_poll(proc)
                except Exception as e:
                    logger.debug(
                        f"pubrun failed to poll subprocess at finalization: {e}"
                    )
                    continue
                if isinstance(rc, int) and not isinstance(rc, bool):
                    complete_record(rec, rc, time.time(), time.perf_counter())

            # Drain any exits queued while Phase 2/3 ran.
            try:
                state["drain"]()
            except Exception as e:
                logger.debug(
                    f"pubrun failed to drain subprocess queues after polling: {e}"
                )

        # Phase 4: Mark remaining unobserved records partial and drop all Popen refs.
        now_mono = time.perf_counter()
        with finalization_lock(cls._lock, 0.25):
            for rec in list(cls._records):
                if rec.get("exit_code") is None and "ended_at_utc" not in rec:
                    rec["ended_at_utc"] = None
                    entry = cls._start_monos.pop(id(rec), None)
                    if entry is not None and entry[0] is rec:
                        rec["elapsed_seconds"] = max(0.0, now_mono - entry[1])
                        rec["duration_clock"] = "monotonic"
                    rec["capture_state"] = {
                        "status": "partial",
                        "detail": _UNWAITED_DETAIL,
                    }
            cls._popen_refs.clear()
            cls._pending_running.clear()
            if state is not None:
                state["pending_running"].clear()

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
