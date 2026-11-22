import json
import logging
import os
import platform
import sys
import threading
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from pubrun.config import resolve_config
from pubrun.writer import ArtifactWriter

# Import our capture engines
from pubrun.capture.invocation import get_invocation
from pubrun.capture.subprocesses import SubprocessSpy
from pubrun.capture.console import ConsoleInterceptor
from pubrun.capture.hardware import get_hardware
from pubrun.events import EventStream
from pubrun.capture.resources import ResourceWatcher
from pubrun.capture.process import get_process_info
from pubrun.capture.python_runtime import get_python_runtime
from pubrun.capture.packages import get_packages
from pubrun.capture.environment import get_environment
from pubrun.capture.git import get_git
from pubrun.capture.host import get_host
from pubrun.capture.signals import SignalExitCapture


# Maximum number of structured capture-error records retained per Run manifest.
MAX_CAPTURE_ERRORS = 50

# Define a singleton instance to manage global tracking state
_active_run: Optional["Run"] = None


def get_current_run() -> Optional["Run"]:
    """Return the globally active Run instance, or None."""
    return _active_run


class Run:
    """Core tracking object. Gathers capture data and produces manifest output."""
    def __init__(self, overrides: Optional[Dict[str, Any]] = None) -> None:
        """Initialize and register the active run.

        Args:
            overrides: Configuration overrides merged on top of resolved config.

        If the run directory cannot be created (e.g. read-only filesystem),
        enters Ghost Mode: all capture is suppressed and the host script
        continues unaffected.
        """
        global _active_run

        # Timing anchors and interval state.
        # UTC epoch floats (time.time()) establish absolute chronology, while
        # private monotonic counter readings (time.perf_counter()) measure
        # nonnegative intervals immune to wall-clock jumps. Monotonic anchors
        # remain in memory only and are never serialized to manifest.json.
        self.started_at_utc: float = time.time()
        self._start_mono: float = time.perf_counter()
        self.workload_started_at_utc: Optional[float] = None
        self._workload_start_mono: Optional[float] = None
        self.ended_at_utc: Optional[float] = None
        self._workload_end_mono: Optional[float] = None
        self.finalized_at_utc: Optional[float] = None
        self._finalize_end_mono: Optional[float] = None
        self._hardware_wait_seconds: Optional[float] = None
        self._background_hardware_seconds: Optional[float] = None
        self.writer_overhead_seconds: Optional[float] = None
        self._manifest_timing_frozen: bool = False
        self._frozen_timing_dict: Optional[Dict[str, Any]] = None

        try:
            self.config = resolve_config(overrides)
        except Exception as config_err:
            from pubrun.capture.redaction import format_safe_error_detail
            detail = format_safe_error_detail(config_err, None)
            logging.getLogger("pubrun").warning(
                "pubrun: config resolution failed, using defaults: %s", detail
            )
            from pubrun.config import load_default_config
            self.config = load_default_config()

        # Non-disruptive config notices (recorded in the manifest, never raised into the
        # host). Currently: the deprecated, inert `core.profile` setting.
        self.config_notices = []
        try:
            from pubrun.config import profile_deprecation_notice
            _profile_notice = profile_deprecation_notice(self.config)
            if _profile_notice:
                self.config_notices.append(_profile_notice)
        except Exception:
            # A notice must never break a run; degrade silently.
            pass

        self.ref_count = 1
        self.run_id = uuid.uuid4().hex[:8]
        self.pid = os.getpid()
        raw_script = Path(sys.argv[0]).stem if sys.argv and sys.argv[0] else "interactive"
        import re
        self.script_name = re.sub(r"[^a-zA-Z0-9_\-\.]", "_", raw_script)

        self.is_active = True
        self._outcome = "running"
        self._finalized = False
        self._hardware_write_closed = False

        # Error isolation, ownership, and fallback section state initialized before
        # any filesystem or hook operation so ghost/partial runs stay well-formed.
        self._errors_lock = threading.Lock()
        self._capture_errors: list = []
        self._capture_errors_truncated: int = 0
        self._warned_errors: set = set()
        self._failed_sections: set = set()
        self._spy_owner_token = object()
        self._spying_subprocesses = False
        self._subprocesses_was_enabled = False
        self.writer: Optional[ArtifactWriter] = None

        self.invocation_data: Dict[str, Any] = {}
        self.git_data: Dict[str, Any] = {}
        self.process_data: Dict[str, Any] = {}
        self.python_data: Dict[str, Any] = {}
        self.packages_data: Dict[str, Any] = {}
        self.environment_data: Dict[str, Any] = {}
        self.hardware_data: Dict[str, Any] = {}
        self.host_data: Dict[str, Any] = {}
        self.filesystem_data: Dict[str, Any] = {}
        self.console_data: Dict[str, Any] = {}
        self.resources_data: Optional[Dict[str, Any]] = None
        self.signals_data: Optional[Dict[str, Any]] = None
        self.data_files: Dict[str, Any] = {"inputs": [], "outputs": [], "mixed": []}
        self._data_files_lock = threading.Lock()
        self._file_io_budget: Optional[Any] = None
        self._pending_file_registrations: list = []
        self.manual_subprocess_records: list = []
        self._active_profilers: list = []
        self.console_interceptor = None
        self.event_stream = None
        self.resource_watcher = None
        self.signal_capture = None
        self._hardware_thread: Optional[threading.Thread] = None
        self._hardware_future_done: Optional[threading.Event] = None

        # Establish the unique run directory name
        base_dir_str = self.config.get("core", {}).get("output_dir", "")
        base_dir = Path(base_dir_str) if base_dir_str else Path.cwd() / "runs"

        # Format timezone for human-readable directory names
        dt = datetime.fromtimestamp(self.started_at_utc, tz=timezone.utc)
        timestamp_str = dt.strftime("%Y%m%dT%H%M%SZ")
        dir_name = f"pubrun-{self.script_name}-{timestamp_str}-{self.pid}-{self.run_id}"
        self.run_dir = base_dir / dir_name

        # Ensure directory is created safely with restrictive permissions.
        # Set umask to prevent world-readable window between mkdir and chmod (P2-S1).
        try:
            old_umask = None
            if sys.platform != "win32":
                old_umask = os.umask(0o077)  # Ensure dirs created as 0o700
            try:
                self.run_dir.mkdir(parents=True, exist_ok=True)
            finally:
                if old_umask is not None:
                    os.umask(old_umask)
        except Exception as e:
            # GHOST MODE: run directory cannot be created (e.g. read-only storage).
            # No hooks have been installed yet; enter ghost mode cleanly.
            from pubrun.capture.redaction import format_safe_error_detail
            self._enter_ghost_mode(format_safe_error_detail(e, self.config))
            return

        # ---- Phase 3: Bootstrap Capture Engines ----
        # Every engine inside _bootstrap_engines() runs in its own isolated guard
        # so an individual engine failure degrades only that section rather than
        # entering ghost mode.
        self._bootstrap_engines()
        # ---------------------------------------------

        # Wire up crash-safety and verify startup output is writable before
        # registering atexit or publishing the active run.
        self.writer = ArtifactWriter(self)
        startup_ok: Any = False
        startup_err: Optional[str] = None
        try:
            startup_ok = self.writer.write_startup_manifest()
        except Exception as write_exc:
            from pubrun.capture.redaction import format_safe_error_detail
            startup_err = format_safe_error_detail(write_exc, self.config)
            startup_ok = False

        if startup_ok is False or (
            startup_ok is None and getattr(self.writer, "last_error", None) is not None
        ):
            # Output directory is unusable (e.g. read-only storage after mkdir).
            # Latch _finalized under _run_lock FIRST so background threads cannot
            # race with rollback, roll back all hooks/threads/handles this run
            # owns, and enter ghost mode without registering atexit.
            reason = (
                startup_err
                or getattr(self.writer, "last_error", None)
                or "unable to write startup manifest"
            )
            from pubrun import _run_lock
            with _run_lock:
                self._finalized = True
                self._hardware_write_closed = True
                self.is_active = False
            self._rollback_owned_hooks(stage="rollback")
            self._enter_ghost_mode(reason)
            return

        self.writer.register_atexit()

        # Anchor t1: synchronous startup complete; observed tracked workload begins.
        self._workload_start_mono = time.perf_counter()
        self.workload_started_at_utc = time.time()

        # Update global reference
        _active_run = self

    # ------------------------------------------------------------------
    # Error recording, ghost mode, and transactional rollback helpers
    # ------------------------------------------------------------------

    def _check_section_failed(self, section: str, data: Any) -> None:
        """Record ``section`` as failed if its returned dict carries a failed capture_state."""
        if isinstance(data, dict):
            cs = data.get("capture_state")
            if isinstance(cs, dict) and cs.get("status") == "failed":
                with self._errors_lock:
                    self._failed_sections.add(section)

    def _store_capture_error_detail(
        self,
        section: str,
        stage: str,
        detail: str,
        exc_type: Optional[str] = None,
        *,
        warn: bool = True,
    ) -> bool:
        """Store a bounded capture-error record under ``_errors_lock``.

        Returns True when the caller should emit a one-time warning outside locks.
        """
        if exc_type is None and ":" in detail:
            prefix = detail.split(":", 1)[0].strip()
            if prefix:
                exc_type = prefix
        with self._errors_lock:
            if (
                not self._finalized
                or not getattr(self, "_hardware_write_closed", True)
                or stage in ("finalization", "rollback", "writer")
            ):
                if len(self._capture_errors) < MAX_CAPTURE_ERRORS:
                    self._capture_errors.append({
                        "kind": "capture-error",
                        "type": exc_type,
                        "message": detail,
                        "traceback": None,
                        "section": section,
                        "stage": stage,
                    })
                else:
                    self._capture_errors_truncated += 1
                self._failed_sections.add(section)
            warn_key = (section, stage)
            should_warn = False
            if warn and warn_key not in self._warned_errors:
                self._warned_errors.add(warn_key)
                should_warn = True
        return should_warn

    def _emit_capture_warning(self, section: str, stage: str, detail: str) -> None:
        """Emit one bounded warning outside all internal locks."""
        try:
            logging.getLogger("pubrun").warning(
                "pubrun: %s capture failed (%s): %s", section, stage, detail
            )
        except Exception:
            pass

    def _record_capture_error_detail(
        self,
        section: str,
        stage: str,
        detail: str,
        exc_type: Optional[str] = None,
        *,
        warn: bool = True,
    ) -> str:
        """Record an already-formatted safe error detail and emit at most one warning."""
        should_warn = self._store_capture_error_detail(
            section, stage, detail, exc_type=exc_type, warn=warn
        )
        if should_warn:
            self._emit_capture_warning(section, stage, detail)
        return detail

    def _record_capture_error(
        self,
        section: str,
        stage: str,
        exc: BaseException,
        *,
        warn: bool = True,
    ) -> str:
        """Format, record, and warn once for a capture/cleanup exception."""
        from pubrun.capture.redaction import format_safe_error_detail
        detail = format_safe_error_detail(exc, getattr(self, "config", None))
        should_warn = self._store_capture_error_detail(
            section, stage, detail, exc_type=type(exc).__name__, warn=warn
        )
        if should_warn:
            self._emit_capture_warning(section, stage, detail)
        return detail

    def _enter_ghost_mode(self, reason: str) -> None:
        """Transition this run into Ghost Mode when output is genuinely unusable."""
        global _active_run
        self.is_active = False
        self._outcome = "ghost"
        self._finalized = True
        self.writer = None
        self._spying_subprocesses = False
        self._subprocesses_was_enabled = False
        self.console_interceptor = None
        self.event_stream = None
        self.resource_watcher = None
        self.signal_capture = None

        safe_reason = " ".join(str(reason or "output directory unavailable").splitlines()).strip()
        if len(safe_reason) > 240:
            safe_reason = safe_reason[:237] + "..."
        try:
            print(
                f"pubrun WARNING: Unable to write run artifacts ({safe_reason}). "
                "Running in Ghost Mode (tracking suppressed).",
                file=sys.stderr,
            )
        except Exception:
            pass
        _active_run = self

    # ------------------------------------------------------------------
    # Lock file (enables external status queries)
    # ------------------------------------------------------------------

    LOCK_FILENAME = ".pubrun.lock"

    def _write_lock_file(self) -> None:
        """Write a lock file to the run directory so external tools can detect
        this run is active.  Contains PID, start time, hostname, and git commit
        for status queries.  Best-effort -- never crashes the host script."""
        try:
            git_commit = None
            if isinstance(self.git_data, dict):
                git_commit = self.git_data.get("commit")
            # Get compact import provenance
            _import_mode = None
            _import_selected_by = None
            try:
                from pubrun._bootstrap import get_selected_mode, _selected_by as _sel_by
                _import_mode = get_selected_mode()
                _import_selected_by = _sel_by
            except Exception:
                pass

            # Redact argv before writing to lock file (P2-S2)
            _lock_argv = sys.argv[1:] if len(sys.argv) > 1 else []
            _sys_argv = list(sys.argv) if sys.argv else []
            try:
                from pubrun.capture.redaction import redact_argv
                _lock_argv = redact_argv(_lock_argv, self.config)
                _sys_argv = redact_argv(_sys_argv, self.config)
            except Exception:
                pass  # Best-effort redaction

            lock_data = {
                "pid": self.pid,
                "started_at_utc": self.started_at_utc,
                "script": self.script_name,
                "run_id": self.run_id,
                "hostname": platform.node(),
                "git_commit": git_commit,
                "cwd": str(Path.cwd()),
                "argv": _lock_argv,
                "sys_argv": _sys_argv,
                "import_mode": _import_mode,
                "import_selected_by": _import_selected_by,
            }
            lock_path = self.run_dir / self.LOCK_FILENAME
            with open(lock_path, "w", encoding="utf-8") as f:
                json.dump(lock_data, f, indent=2)
        except Exception:
            pass  # Best-effort: pubrun must never crash the host script.

    def _remove_lock_file(self) -> None:
        """Remove the lock file after finalization.  Best-effort."""
        try:
            lock_path = self.run_dir / self.LOCK_FILENAME
            if lock_path.exists():
                lock_path.unlink()
        except Exception:
            pass

    def _bootstrap_engines(self) -> None:
        """Initialize all capture engines with per-engine failure isolation.

        Each capture engine runs inside its own isolated guard so an escaping
        exception marks only that section ``"failed"`` and records a bounded
        redacted ``capture-error`` without promoting healthy tracking into
        ghost mode.
        """
        import threading as _threading

        # 1. Invocation canonical path extraction
        try:
            self.invocation_data = get_invocation(self.config)
            self._check_section_failed("invocation", self.invocation_data)
        except Exception as exc:
            detail = self._record_capture_error("invocation", "bootstrap", exc)
            try:
                from pubrun.capture.redaction import redact_argv
                safe_argv = redact_argv(list(sys.argv), self.config)
            except Exception:
                safe_argv = []
            self.invocation_data = {
                "argv": safe_argv,
                "capture_state": {"status": "failed", "detail": detail},
            }

        # 2. Get Git provenance before subprocess tracking to prevent logging ourselves
        try:
            self.git_data = get_git(self.config)
            self._check_section_failed("git", self.git_data)
        except Exception as exc:
            detail = self._record_capture_error("git", "bootstrap", exc)
            self.git_data = {"capture_state": {"status": "failed", "detail": detail}}

        # Write lock file early so external tools can detect this run is active.
        self._write_lock_file()

        # 3. Process, Python runtime, Packages, and Environment snapshotting
        try:
            self.process_data = get_process_info(self.config)
            self._check_section_failed("process", self.process_data)
        except Exception as exc:
            detail = self._record_capture_error("process", "bootstrap", exc)
            self.process_data = {"capture_state": {"status": "failed", "detail": detail}}

        try:
            self.python_data = get_python_runtime(self.config)
            self._check_section_failed("python", self.python_data)
        except Exception as exc:
            detail = self._record_capture_error("python", "bootstrap", exc)
            self.python_data = {"capture_state": {"status": "failed", "detail": detail}}

        try:
            self.packages_data = get_packages(self.config)
            self._check_section_failed("packages", self.packages_data)
        except Exception as exc:
            detail = self._record_capture_error("packages", "bootstrap", exc)
            self.packages_data = {"capture_state": {"status": "failed", "detail": detail}}

        try:
            self.environment_data = get_environment(self.config)
            self._check_section_failed("environment", self.environment_data)
        except Exception as exc:
            detail = self._record_capture_error("environment", "bootstrap", exc)
            self.environment_data = {"capture_state": {"status": "failed", "detail": detail}}

        # 4. Hardware, Host, and Filesystem tracking -- deferred to a background thread (PERF-02).
        # Each of get_hardware(), get_host(), and get_filesystem() runs in its own
        # independent try/except block so a failure in one never skips or overwrites
        # the others.
        self.hardware_data = {"capture_state": {"status": "pending"}}
        self.host_data = {"capture_state": {"status": "pending"}}
        self.filesystem_data = {"capture_state": {"status": "pending"}}
        self._hardware_future_done = _threading.Event()

        def _collect_hardware():
            from pubrun import _run_lock
            from pubrun.capture.redaction import format_safe_error_detail

            hw_start = time.perf_counter()
            try:
                # 4a. Hardware
                try:
                    hw_res = get_hardware(self.config)
                    with _run_lock:
                        if not self._hardware_write_closed:
                            self.hardware_data = hw_res
                            self._check_section_failed("hardware", hw_res)
                except Exception as exc:
                    detail = format_safe_error_detail(exc, self.config)
                    should_warn = False
                    with _run_lock:
                        if not self._hardware_write_closed:
                            self.hardware_data = {
                                "capture_state": {"status": "failed", "detail": detail}
                            }
                            should_warn = self._store_capture_error_detail(
                                "hardware", "bootstrap", detail, exc_type=type(exc).__name__
                            )
                    if should_warn:
                        self._emit_capture_warning("hardware", "bootstrap", detail)

                # 4b. Host
                try:
                    host_res = get_host(self.config)
                    with _run_lock:
                        if not self._hardware_write_closed:
                            self.host_data = host_res
                            self._check_section_failed("host", host_res)
                except Exception as exc:
                    detail = format_safe_error_detail(exc, self.config)
                    should_warn = False
                    with _run_lock:
                        if not self._hardware_write_closed:
                            self.host_data = {
                                "capture_state": {"status": "failed", "detail": detail}
                            }
                            should_warn = self._store_capture_error_detail(
                                "host", "bootstrap", detail, exc_type=type(exc).__name__
                            )
                    if should_warn:
                        self._emit_capture_warning("host", "bootstrap", detail)

                # 4c. Filesystem classification (NON-BLOCKING by design)
                try:
                    from pubrun.capture.filesystem import get_filesystem
                    import tempfile as _tf
                    paths = {
                        "output_dir": str(getattr(self, "output_base_dir", "") or ""),
                        "run_dir": str(getattr(self, "run_dir", "") or ""),
                        "tmpdir": _tf.gettempdir(),
                    }
                    fs_res = get_filesystem(self.config, {k: v for k, v in paths.items() if v})
                    with _run_lock:
                        if not self._hardware_write_closed:
                            self.filesystem_data = fs_res
                            self._check_section_failed("filesystem", fs_res)
                except Exception as exc:
                    detail = format_safe_error_detail(exc, self.config)
                    should_warn = False
                    with _run_lock:
                        if not self._hardware_write_closed:
                            self.filesystem_data = {
                                "capture_state": {"status": "failed", "detail": detail}
                            }
                            should_warn = self._store_capture_error_detail(
                                "filesystem", "bootstrap", detail, exc_type=type(exc).__name__
                            )
                    if should_warn:
                        self._emit_capture_warning("filesystem", "bootstrap", detail)
            finally:
                self._background_hardware_seconds = max(0.0, time.perf_counter() - hw_start)
                self._hardware_future_done.set()

            # BUG-06 / RACE FIX: Re-write startup manifest only if the run is still
            # active and not finalized, guarded under _run_lock to prevent clobbering
            # a finalized manifest.
            try:
                with _run_lock:
                    if (
                        getattr(self, "writer", None)
                        and self.is_active
                        and not self._finalized
                    ):
                        self.writer.write_startup_manifest()
            except Exception:
                pass  # Best-effort

        self._hardware_thread = _threading.Thread(
            target=_collect_hardware, daemon=True, name="pubrun-hw"
        )
        try:
            self._hardware_thread.start()
        except Exception as exc:
            detail = self._record_capture_error("hardware", "bootstrap", exc)
            self._record_capture_error("host", "bootstrap", exc, warn=False)
            self._record_capture_error("filesystem", "bootstrap", exc, warn=False)
            self.hardware_data = {"capture_state": {"status": "failed", "detail": detail}}
            self.host_data = {"capture_state": {"status": "failed", "detail": detail}}
            self.filesystem_data = {"capture_state": {"status": "failed", "detail": detail}}
            self._hardware_thread = None
            self._hardware_future_done.set()

        # Determine if global hooks and patches are permitted by the import mode.
        _patch_subprocesses = True
        _patch_console = True
        _signal_hooks = True
        _force_console = False
        try:
            from pubrun._bootstrap import get_selected_behavior
            _behavior = get_selected_behavior()
            if _behavior is not None:
                _patch_subprocesses = _behavior.get("patch_subprocesses", True)
                _patch_console = _behavior.get("patch_console", True)
                _signal_hooks = _behavior.get("signal_hooks", True)
                _force_console = _behavior.get("force_console", False)
        except Exception:
            pass

        # 5. Subprocess interception (monkeypatch)
        if _patch_subprocesses and self.config.get("capture", {}).get("subprocesses", {}).get("enabled", False):
            try:
                max_tracked = self.config.get("capture", {}).get("subprocesses", {}).get("max_tracked_commands", 5000)
                installed = SubprocessSpy.install(
                    max_tracked, config=self.config, owner=self._spy_owner_token
                )
                self._spying_subprocesses = bool(installed)
                if self._spying_subprocesses:
                    self._subprocesses_was_enabled = True
            except Exception as exc:
                self._spying_subprocesses = False
                self._record_capture_error("subprocesses", "bootstrap", exc)

        # 6. Console tee (monkeypatch -- wraps sys.stdout/stderr)
        console_mode = "off"
        try:
            if _patch_console:
                from pubrun.capture.console import resolve_console_mode
                resolved_mode = resolve_console_mode(
                    self.config, force_base="standard" if _force_console else None
                )
                if resolved_mode in ("off", "basic", "standard", "deep"):
                    console_mode = resolved_mode
            interceptor = ConsoleInterceptor(self.run_dir, console_mode, config=self.config)
            started = interceptor.start()
            if not started:
                failed_detail = (
                    getattr(interceptor, "_failed_detail", None)
                    or "console interceptor failed to start"
                )
                try:
                    self.console_data = interceptor.stop()
                except Exception:
                    self.console_data = {
                        "capture_mode": console_mode,
                        "capture_state": {"status": "failed", "detail": failed_detail},
                    }
                self._record_capture_error_detail("console", "bootstrap", failed_detail)
                self.console_interceptor = None
            else:
                self.console_interceptor = interceptor
                self.console_data = {
                    "capture_mode": interceptor.mode,
                    "capture_state": {"status": "pending"},
                }
        except Exception as exc:
            detail = self._record_capture_error("console", "bootstrap", exc)
            self.console_data = {
                "capture_mode": console_mode,
                "capture_state": {"status": "failed", "detail": detail},
            }
            self.console_interceptor = None

        # 7. Event Stream (not a global hook -- safe in all modes)
        if self.config.get("events", {}).get("enabled", False):
            try:
                stream = EventStream(self.run_dir, config=self.config)
                if getattr(stream, "_file", None) is None:
                    err_detail = (
                        getattr(stream, "_last_error", None)
                        or "event stream failed to open"
                    )
                    self._record_capture_error_detail("events", "bootstrap", err_detail)
                    self.event_stream = None
                else:
                    self.event_stream = stream
            except Exception as exc:
                self.event_stream = None
                self._record_capture_error("events", "bootstrap", exc)

        # 8. Background Telemetry (not a global hook -- background thread only)
        res_cfg = self.config.get("capture", {}).get("resources", {})
        if res_cfg.get("depth", "off") != "off":
            watcher = None
            try:
                interval = res_cfg.get("sample_interval_seconds", 15)
                max_fails = res_cfg.get("max_consecutive_failures", 3)
                scope = res_cfg.get("scope", "process")
                system_metrics = res_cfg.get("system_metrics", True)
                from pubrun.capture.resources import set_poll_timeout
                set_poll_timeout(res_cfg.get("poll_timeout", 3))
                watcher = ResourceWatcher(
                    self, interval, max_fails, scope=scope, system_metrics=system_metrics
                )
                watcher.start()
                self.resource_watcher = watcher
            except Exception as exc:
                if watcher is not None:
                    try:
                        watcher.stop()
                    except Exception:
                        pass
                self.resource_watcher = None
                detail = self._record_capture_error("resources", "bootstrap", exc)
                self.resources_data = {"capture_state": {"status": "failed", "detail": detail}}

        # 9. Signal and exit-code capture (standard registration hook)
        if _signal_hooks and self.config.get("capture", {}).get("signals", {}).get("enabled", True):
            try:
                sig_cap = SignalExitCapture(config=self.config)
                sig_cap.install()
                self.signal_capture = sig_cap
            except Exception as exc:
                self.signal_capture = None
                detail = self._record_capture_error("signals", "bootstrap", exc)
                self.signals_data = {"capture_state": {"status": "failed", "detail": detail}}

    def _merge_and_migrate(self, overrides: Dict[str, Any]) -> None:
        """Merge new overrides into a running config. Migrates the run directory
        if the output_dir changes."""
        if (
            self._outcome == "ghost"
            or not self.is_active
            or self._finalized
            or not overrides
        ):
            return

        try:
            merged = resolve_config(overrides)
        except Exception as exc:
            from pubrun.capture.redaction import format_safe_error_detail
            detail = format_safe_error_detail(exc, getattr(self, "config", None))
            logging.getLogger("pubrun").warning(
                "pubrun: failed to resolve config overrides during merge: %s", detail
            )
            return

        new_base_str = merged.get("core", {}).get("output_dir", "")

        if new_base_str:
            new_base = Path(new_base_str)
            new_dir = new_base / self.run_dir.name

            if new_dir != self.run_dir:
                # Wait for the background hardware thread to finish first: it re-writes the
                # startup manifest into run_dir, and on Windows a directory cannot be moved
                # while any file inside it is open -- a concurrent write would make shutil.move
                # fail and silently abort the migration. (Windows CI: dir-migration bug.)
                hw = getattr(self, "_hardware_thread", None)
                if hw is not None and hw.is_alive():
                    hw.join(timeout=5)
                done = getattr(self, "_hardware_future_done", None)
                if done is not None:
                    done.wait(timeout=5)

                # Close open files before moving the directory (required on Windows)
                if getattr(self, "event_stream", None):
                    self.event_stream.close()

                if getattr(self, "console_interceptor", None):
                    if getattr(self.console_interceptor, "stdout_log", None):
                        try:
                            self.console_interceptor.stdout_log.flush()
                            self.console_interceptor.stdout_log.close()
                        except Exception:
                            pass
                        self.console_interceptor.stdout_log = None
                    if getattr(self.console_interceptor, "stderr_log", None):
                        try:
                            self.console_interceptor.stderr_log.flush()
                            self.console_interceptor.stderr_log.close()
                        except Exception:
                            pass
                        self.console_interceptor.stderr_log = None

                try:
                    import shutil
                    new_dir.parent.mkdir(parents=True, exist_ok=True)
                    shutil.move(str(self.run_dir), str(new_dir))
                    old_dir_str = str(self.run_dir)
                    self.run_dir = new_dir
                except Exception as e:
                    from pubrun.capture.redaction import format_safe_error_detail
                    logging.getLogger("pubrun").warning(
                        "Failed migrating runtime paths: %s",
                        format_safe_error_detail(e, merged),
                    )
                    # Reopen files in original directory if move failed
                    new_dir = self.run_dir
                    old_dir_str = str(self.run_dir)

                # Reopen or migrate the files to the active run_dir
                if getattr(self, "event_stream", None):
                    self.event_stream.migrate_directory(new_dir)
                    # BUG-10: Only emit if the stream successfully reopened.
                    if new_dir != Path(old_dir_str):
                        if getattr(self.event_stream, "_file", None):
                            self.event_stream.emit("warning", payload={"message": f"Storage directory changed mid-execution from {old_dir_str} to {new_dir}"})
                        else:
                            logging.getLogger("pubrun").warning(
                                "pubrun: storage migrated to %s but event stream failed to reopen",
                                new_dir,
                            )

                if getattr(self, "console_interceptor", None):
                    if self.console_interceptor.mode != "off":
                        try:
                            self.console_interceptor.stdout_log = open(new_dir / "stdout.log", "a", encoding="utf-8")
                            if self.console_interceptor.stdout_tee:
                                self.console_interceptor.stdout_tee.log_file = self.console_interceptor.stdout_log

                            self.console_interceptor.stderr_log = open(new_dir / "stderr.log", "a", encoding="utf-8")
                            if self.console_interceptor.stderr_tee:
                                self.console_interceptor.stderr_tee.log_file = self.console_interceptor.stderr_log
                        except Exception as reopen_err:
                            logging.getLogger("pubrun").debug(
                                "Failed to reopen console logs after migration: %s", reopen_err
                            )

        was_spying = self._spying_subprocesses
        will_spy = merged.get("capture", {}).get("subprocesses", {}).get("enabled", False)
        if will_spy and not was_spying:
            _patch_subprocesses = True
            try:
                from pubrun._bootstrap import get_selected_behavior
                _behavior = get_selected_behavior()
                if _behavior is not None:
                    _patch_subprocesses = _behavior.get("patch_subprocesses", True)
            except Exception:
                pass
            if _patch_subprocesses:
                try:
                    max_tracked = merged.get("capture", {}).get("subprocesses", {}).get("max_tracked_commands", 5000)
                    installed = SubprocessSpy.install(
                        max_tracked, config=merged, owner=self._spy_owner_token
                    )
                    self._spying_subprocesses = bool(installed)
                    if self._spying_subprocesses:
                        self._subprocesses_was_enabled = True
                except Exception as exc:
                    self._spying_subprocesses = False
                    self._record_capture_error("subprocesses", "runtime", exc)

        self.config = merged

    def _rollback_owned_hooks(self, *, stage: str = "rollback") -> None:
        """Tear down every hook, worker, handle, and lock file owned by this run.

        Every cleanup step executes in its own independent try/except block so a
        first or second failure never skips later teardown steps.
        """
        is_finalization = stage == "finalization"
        is_rollback = stage == "rollback"

        # 1. SubprocessSpy (separated so finalize_all / get_records failures never skip uninstall)
        if self._spying_subprocesses:
            if is_finalization:
                try:
                    SubprocessSpy.finalize_all()
                except Exception as exc:
                    self._record_capture_error("subprocesses", stage, exc)
                try:
                    self._saved_subprocess_records = list(SubprocessSpy.get_records())
                except Exception as exc:
                    self._record_capture_error("subprocesses", stage, exc)
                    if not hasattr(self, "_saved_subprocess_records"):
                        self._saved_subprocess_records = []
            try:
                SubprocessSpy.uninstall(owner=self._spy_owner_token)
            except Exception as exc:
                self._record_capture_error("subprocesses", stage, exc)
            finally:
                self._spying_subprocesses = False

        # 2. ConsoleInterceptor
        if self.console_interceptor is not None:
            interceptor = self.console_interceptor
            try:
                res = interceptor.stop()
                if is_finalization:
                    self.console_data = res
                    self._check_section_failed("console", res)
            except Exception as exc:
                detail = self._record_capture_error("console", stage, exc)
                if is_finalization:
                    mode = getattr(interceptor, "mode", "off")
                    if mode not in ("off", "basic", "standard", "deep"):
                        mode = "off"
                    self.console_data = {
                        "capture_mode": mode,
                        "capture_state": {"status": "failed", "detail": detail},
                    }
            finally:
                self.console_interceptor = None

        # 3. ResourceWatcher (stop and manifest snapshot isolated separately)
        if self.resource_watcher is not None:
            watcher = self.resource_watcher
            try:
                watcher.stop()
            except Exception as exc:
                detail = self._record_capture_error("resources", stage, exc)
                if is_finalization and self.resources_data is None:
                    self.resources_data = {"capture_state": {"status": "failed", "detail": detail}}
            if is_finalization:
                try:
                    res_dict = watcher.to_manifest_dict()
                    self.resources_data = res_dict
                    self._check_section_failed("resources", res_dict)
                except Exception as exc:
                    detail = self._record_capture_error("resources", stage, exc)
                    self.resources_data = {"capture_state": {"status": "failed", "detail": detail}}
            if is_rollback:
                self.resource_watcher = None

        # 4. Pending deferred external file registrations (finalization only)
        if is_finalization and getattr(self, "_pending_file_registrations", None):
            try:
                from pubrun.capture.file_io import finalize_pending_registrations
                finalize_pending_registrations(self)
            except Exception as exc:
                self._record_capture_error("data_files", stage, exc)

        # 5. EventStream
        if self.event_stream is not None:
            stream = self.event_stream
            try:
                stream.close()
            except Exception as exc:
                self._record_capture_error("events", stage, exc)
            if is_rollback:
                self.event_stream = None

        # 6. Orphaned profilers (BUG2-04)
        profilers = getattr(self, "_active_profilers", None)
        if profilers:
            for profiler in list(profilers):
                try:
                    profiler.disable()
                except Exception as exc:
                    self._record_capture_error("profiling", stage, exc)
            try:
                profilers.clear()
            except Exception:
                pass

        # 7. SignalExitCapture (snapshot and uninstall isolated separately)
        if self.signal_capture is not None:
            sig_cap = self.signal_capture
            if is_finalization:
                try:
                    sig_dict = sig_cap.get_records()
                    self.signals_data = sig_dict
                    self._check_section_failed("signals", sig_dict)
                except Exception as exc:
                    detail = self._record_capture_error("signals", stage, exc)
                    self.signals_data = {"capture_state": {"status": "failed", "detail": detail}}
            try:
                sig_cap.uninstall()
            except Exception as exc:
                self._record_capture_error("signals", stage, exc)
            if is_rollback:
                self.signal_capture = None

        # 8. Lock file removal
        try:
            self._remove_lock_file()
        except Exception as exc:
            self._record_capture_error("lock_file", stage, exc)

        # 9. Ghost rollback extras: unregister atexit and bound-join background hardware thread
        if is_rollback:
            writer = getattr(self, "writer", None)
            if writer is not None and hasattr(writer, "unregister_atexit"):
                try:
                    writer.unregister_atexit()
                except Exception as exc:
                    self._record_capture_error("writer", stage, exc)
            hw_thread = getattr(self, "_hardware_thread", None)
            if hw_thread is not None and hw_thread.is_alive():
                try:
                    hw_thread.join(timeout=0.5)
                except Exception as exc:
                    self._record_capture_error("hardware", stage, exc)

    def _finalize_state(self) -> None:
        """Shut down all capture engines and record the final outcome.

        Idempotent -- safe to call multiple times (guarded by ``_finalized``).
        Every pre-teardown and teardown step runs independently so an error in
        one step never blocks subsequent cleanup or manifest writing.
        """
        # Set the finalized latch and capture workload-end anchor t2 under _run_lock
        # before waiting on deferred hardware collection so teardown latency never
        # inflates workload_seconds and the async hardware thread cannot overwrite
        # a finalized manifest (IPD 20260721-1425-01).
        from pubrun import _run_lock
        with _run_lock:
            if self._finalized:
                return
            self._finalized = True
            if self.is_active:
                self._workload_end_mono = time.perf_counter()
                self.ended_at_utc = time.time()
                self.is_active = False

        # Pre-teardown step 1: Wait for deferred hardware collection (capped at 2s),
        # then close the background hardware write window under _run_lock so a slow
        # worker outlasting the wait can never mutate finalized state afterward.
        hw_done = getattr(self, "_hardware_future_done", None)
        if hw_done is not None:
            hw_wait_start = time.perf_counter()
            try:
                hw_done.wait(timeout=2.0)
            except Exception as exc:
                self._record_capture_error("hardware", "finalization", exc)
            finally:
                self._hardware_wait_seconds = max(0.0, time.perf_counter() - hw_wait_start)
                with _run_lock:
                    self._hardware_write_closed = True
        else:
            with _run_lock:
                self._hardware_write_closed = True

        if self._outcome in ("unknown", "running"):
            # If sys.exc_info() denotes an active crash at exit time, we log failed.
            if sys.exc_info()[0] is not None:
                exc_type = sys.exc_info()[0]
                if exc_type is KeyboardInterrupt:
                    self._outcome = "interrupted"
                else:
                    self._outcome = "failed"
            else:
                self._outcome = "completed"

        # Pre-teardown step 2: Upgrade nominally completed runs if interrupted by signal.
        if self._outcome == "completed" and self.signal_capture:
            try:
                records = self.signal_capture.get_records()
                interruption_signals = {"SIGINT", "SIGTERM", "SIGHUP"}
                for sig in records.get("signals_received", []):
                    if sig.get("signal_name") in interruption_signals:
                        self._outcome = "interrupted"
                        break
            except Exception as exc:
                self._record_capture_error("signals", "finalization", exc)

        # Pre-teardown step 3: Record process exit code.
        if self.signal_capture:
            try:
                exc_info = sys.exc_info()
                if exc_info[1] is not None and isinstance(exc_info[1], SystemExit):
                    code = exc_info[1].code
                    if isinstance(code, int):
                        self.signal_capture.record_exit_code(code)
                    elif code is None:
                        self.signal_capture.record_exit_code(0)
                    else:
                        self.signal_capture.record_exit_code(1)
                elif self._outcome == "completed":
                    self.signal_capture.record_exit_code(0)
                elif self._outcome == "failed":
                    # Unhandled exception -- exit code will be 1
                    self.signal_capture.record_exit_code(1)
            except Exception as exc:
                self._record_capture_error("signals", "finalization", exc)

        # Execute every teardown step independently.
        self._rollback_owned_hooks(stage="finalization")

        # Stamp initial pre-manifest finalization end anchor t3 so direct callers
        # of _finalize_state() have complete finalization timing before freezing.
        self._mark_finalization_end()

    def _mark_finalization_end(self) -> None:
        """Record or refresh pre-manifest finalization anchor t3 until timing is frozen."""
        if (
            self._workload_end_mono is not None
            and not getattr(self, "_manifest_timing_frozen", False)
        ):
            self._finalize_end_mono = time.perf_counter()
            self.finalized_at_utc = time.time()

    def _build_timing_dict(self) -> Dict[str, Any]:
        """Compute the manifest timing section from monotonic deltas and UTC anchors."""
        start_mono = getattr(self, "_start_mono", None)
        workload_start_mono = getattr(self, "_workload_start_mono", None)
        workload_end_mono = getattr(self, "_workload_end_mono", None)
        finalize_end_mono = getattr(self, "_finalize_end_mono", None)

        startup_overhead: Optional[float] = None
        if start_mono is not None and workload_start_mono is not None:
            startup_overhead = max(0.0, workload_start_mono - start_mono)

        workload_seconds: Optional[float] = None
        if workload_start_mono is not None and workload_end_mono is not None:
            workload_seconds = max(0.0, workload_end_mono - workload_start_mono)

        finalization_overhead: Optional[float] = None
        if workload_end_mono is not None and finalize_end_mono is not None:
            finalization_overhead = max(0.0, finalize_end_mono - workload_end_mono)

        session_seconds: Optional[float] = None
        if start_mono is not None and finalize_end_mono is not None:
            session_seconds = max(0.0, finalize_end_mono - start_mono)

        is_ghost = (
            getattr(self, "_outcome", None) == "ghost"
            or (getattr(self, "_finalized", False) and workload_start_mono is None)
        )

        if is_ghost:
            capture_state: Dict[str, Any] = {
                "status": "partial",
                "detail": "ghost mode: startup did not complete",
            }
            duration_clock: Optional[str] = None
            elapsed_basis: Optional[str] = None
            elapsed_seconds: Optional[float] = None
        elif (
            getattr(self, "_finalized", False)
            and start_mono is not None
            and workload_start_mono is not None
            and workload_end_mono is not None
            and finalize_end_mono is not None
        ):
            capture_state = {"status": "complete"}
            duration_clock = "monotonic"
            elapsed_basis = "workload"
            elapsed_seconds = workload_seconds
        else:
            capture_state = {"status": "partial"}
            duration_clock = "monotonic"
            elapsed_basis = "workload"
            elapsed_seconds = None

        return {
            "started_at_utc": self.started_at_utc,
            "workload_started_at_utc": getattr(self, "workload_started_at_utc", None),
            "ended_at_utc": self.ended_at_utc,
            "finalized_at_utc": getattr(self, "finalized_at_utc", None),
            "elapsed_seconds": elapsed_seconds,
            "workload_seconds": workload_seconds,
            "startup_overhead_seconds": startup_overhead,
            "finalization_overhead_seconds": finalization_overhead,
            "session_seconds": session_seconds,
            "hardware_wait_seconds": getattr(self, "_hardware_wait_seconds", None),
            "background_hardware_seconds": getattr(self, "_background_hardware_seconds", None),
            "duration_clock": duration_clock,
            "elapsed_basis": elapsed_basis,
            "interval_scope": "tracked_interval",
            "capture_state": capture_state,
        }

    def stop(self, outcome: str = "completed") -> None:
        """Stop tracking, finalize engines, and write artifacts.

        Args:
            outcome: Result label (``"completed"`` or ``"failed"``).
                A ``"failed"`` or ``"ghost"`` outcome is sticky and cannot be overwritten.

        Decrements the reference count. Artifacts are written only when the
        count reaches zero.
        """
        if not getattr(self, "_finalized", False) and self._outcome not in ("failed", "ghost"):
            self._outcome = outcome

        from pubrun import _run_lock
        with _run_lock:
            self.ref_count = getattr(self, "ref_count", 1) - 1
            if self.ref_count > 0:
                return  # Still referenced by an outer wrapper.

        global _active_run
        writer = getattr(self, "writer", None)
        try:
            self._finalize_state()
            if writer is not None:
                writer.write_artifacts()
        finally:
            if writer is not None and hasattr(writer, "unregister_atexit"):
                try:
                    writer.unregister_atexit()
                except Exception:
                    pass
            with _run_lock:
                if _active_run is self:
                    _active_run = None

    def _get_import_metadata(self) -> Dict[str, Any]:
        """Return import-mode provenance metadata for the manifest."""
        try:
            from pubrun._bootstrap import get_import_metadata
            return get_import_metadata()
        except Exception:
            return {"selected_mode": None, "capture_state": {"status": "unavailable"}}

    def to_manifest_dict(self) -> Dict[str, Any]:
        """Build and return the complete ``manifest.json`` dictionary."""
        if getattr(self, "_finalized", False):
            if self._frozen_timing_dict is None:
                self._frozen_timing_dict = self._build_timing_dict()
                self._manifest_timing_frozen = True
            timing_dict = dict(self._frozen_timing_dict)
            if isinstance(timing_dict.get("capture_state"), dict):
                timing_dict["capture_state"] = dict(timing_dict["capture_state"])
        else:
            timing_dict = self._build_timing_dict()

        # Use saved records (captured before uninstall) if available; fall back to live.
        spy_records = getattr(self, "_saved_subprocess_records", None)
        if spy_records is None:
            if self._spying_subprocesses:
                try:
                    spy_records = list(SubprocessSpy.get_records())
                except Exception as exc:
                    self._record_capture_error("subprocesses", "runtime", exc)
                    spy_records = []
            else:
                spy_records = []
        manual_records = list(getattr(self, "manual_subprocess_records", []))
        subprocess_records = spy_records + manual_records

        try:
            from pubrun import __version__, __commit__
        except ImportError:
            __version__ = "1.0.0"
            __commit__ = None

        data_files_lock = getattr(self, "_data_files_lock", None)
        if data_files_lock is not None:
            with data_files_lock:
                raw_data_files = getattr(self, "data_files", None) or {}
                data_files_snapshot: Dict[str, Any] = {
                    "inputs": list(raw_data_files.get("inputs", [])),
                    "outputs": list(raw_data_files.get("outputs", [])),
                    "mixed": list(raw_data_files.get("mixed", [])),
                }
        else:
            raw_data_files = getattr(self, "data_files", None) or {}
            data_files_snapshot = {
                "inputs": list(raw_data_files.get("inputs", [])),
                "outputs": list(raw_data_files.get("outputs", [])),
                "mixed": list(raw_data_files.get("mixed", [])),
            }
        file_io_budget = getattr(self, "_file_io_budget", None)
        if file_io_budget is not None:
            try:
                data_files_snapshot["hashing_summary"] = file_io_budget.to_summary_dict()
            except Exception:
                pass

        # Evaluate dynamic providers safely (preferring snapshotted data when present
        # so failed sections never falsely report "suppressed").
        resources_data = getattr(self, "resources_data", None)
        if resources_data is not None:
            resources_section = resources_data
        elif self.resource_watcher is not None:
            try:
                resources_section = self.resource_watcher.to_manifest_dict()
            except Exception as exc:
                detail = self._record_capture_error("resources", "runtime", exc)
                resources_section = {"capture_state": {"status": "failed", "detail": detail}}
        else:
            resources_section = {"capture_state": {"status": "suppressed"}}

        signals_data = getattr(self, "signals_data", None)
        if signals_data is not None:
            signals_section = signals_data
        elif self.signal_capture is not None:
            try:
                signals_section = self.signal_capture.get_records()
            except Exception as exc:
                detail = self._record_capture_error("signals", "runtime", exc)
                signals_section = {"capture_state": {"status": "failed", "detail": detail}}
        else:
            signals_section = {"capture_state": {"status": "suppressed"}}

        filesystem_section = getattr(self, "filesystem_data", {"capture_state": {"status": "suppressed"}})

        # Snapshot error state atomically under _errors_lock to prevent concurrent
        # iteration races with the background hardware thread.
        errors_lock = getattr(self, "_errors_lock", None)
        if errors_lock is not None:
            with errors_lock:
                errors_copy = [dict(rec) for rec in getattr(self, "_capture_errors", [])]
                truncated = getattr(self, "_capture_errors_truncated", 0)
                failed_sections = set(getattr(self, "_failed_sections", set()))
        else:
            errors_copy = [dict(rec) for rec in getattr(self, "_capture_errors", [])]
            truncated = getattr(self, "_capture_errors_truncated", 0)
            failed_sections = set(getattr(self, "_failed_sections", set()))

        errors_section: Dict[str, Any] = {
            "records": errors_copy,
            "capture_state": (
                {
                    "status": "partial",
                    "detail": f"{truncated} additional capture error(s) omitted",
                }
                if truncated > 0
                else {"status": "complete"}
            ),
        }

        # Aggregate failed sections from both recorded exceptions and any section
        # dict returning capture_state.status == "failed" on its own.
        all_failed = set(failed_sections)
        section_entries = (
            ("invocation", self.invocation_data),
            ("console", self.console_data),
            ("process", self.process_data),
            ("python", self.python_data),
            ("packages", self.packages_data),
            ("environment", self.environment_data),
            ("git", self.git_data),
            ("hardware", self.hardware_data),
            ("host", self.host_data),
            ("filesystem", filesystem_section),
            ("resources", resources_section),
            ("signals", signals_section),
        )
        for sec_name, sec_val in section_entries:
            if isinstance(sec_val, dict):
                cs = sec_val.get("capture_state")
                if isinstance(cs, dict) and cs.get("status") == "failed":
                    all_failed.add(sec_name)

        if all_failed:
            capture_state: Dict[str, Any] = {
                "status": "partial",
                "detail": f"capture degraded in: {', '.join(sorted(all_failed))}",
            }
        else:
            capture_state = {"status": "complete"}

        return {
            "schema_version": "1.0",
            "manifest_type": "pubrun-manifest",
            "meta_ref": self.config.get("core", {}).get("meta_ref", None),
            "run": {
                "run_id": self.run_id,
                "library_version": __version__,
                "library_commit": __commit__,
                "capture_state": {"status": "complete"}
            },
            "timing": timing_dict,

            # Integrated Phase 3 sections
            "invocation": self.invocation_data,
            "console": self.console_data,
            "subprocesses": subprocess_records,

            "process": self.process_data,
            "python": self.python_data,
            "packages": self.packages_data,
            "environment": self.environment_data,
            "git": self.git_data,
            "errors": errors_section,

            "config": {
                "resolved_config_path": "config.resolved.json",
                "sources_path": None,
                "source_files": [],
                "notices": list(getattr(self, "config_notices", [])),
                "capture_state": {"status": "complete"}
            },

            "hardware": self.hardware_data,
            "host": self.host_data,
            "filesystem": filesystem_section,
            "resources": resources_section,

            "capture": {
                "output_base_dir": str(self.run_dir.parent),
                "run_dir": str(self.run_dir),
                "event_stream_enabled": self.config.get("events", {}).get("enabled", False),
                "console_capture_mode": self.config.get("console", {}).get("capture_mode", "off"),
                # Definitive enable flags so `pubrun inspect` can distinguish "feature was
                # OFF" from "feature was on but produced no records" (empty subprocesses /
                # data_files lists are otherwise ambiguous). Additive; do not remove.
                "subprocesses_enabled": bool(
                    getattr(self, "_subprocesses_was_enabled", False)
                    or getattr(self, "_spying_subprocesses", False)
                ),
                "file_provenance_available": True,  # a run was active and pubrun.open is importable
                "capture_state": capture_state,
            },
            "signals": signals_section,

            "pubrun_imports": self._get_import_metadata(),
            "data_files": data_files_snapshot,

            "status": {
                "outcome": self._outcome,
                "capture_state": {"status": "complete"}
            }
        }
