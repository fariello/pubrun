import json
import os
import platform
import sys
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
        
        self.config = resolve_config(overrides)
        self.ref_count = 1
        self.run_id = uuid.uuid4().hex[:8]
        self.pid = os.getpid()
        self.script_name = Path(sys.argv[0]).stem if sys.argv and sys.argv[0] else "interactive"
        
        # Timing state -- stored as POSIX epoch floats (time.time()), not ISO 8601
        # strings. This is a deliberate design choice:
        #   - Sub-second / microsecond precision via IEEE 754.
        #   - Timezone-agnostic: no locale-dependent formatting or parsing.
        #   - Trivial arithmetic: elapsed = ended_at - started_at.
        #   - Natively produced by time.time(), os.stat().st_mtime, etc.
        #   - Compact and deterministic (no string formatting jitter).
        self.started_at_utc = time.time()
        self.ended_at_utc: Optional[float] = None
        self.is_active = True
        
        # Establish the unique run directory name
        base_dir_str = self.config.get("core", {}).get("output_dir", "")
        base_dir = Path(base_dir_str) if base_dir_str else Path.cwd() / "runs"
        
        # Format timezone for human-readable directory names
        dt = datetime.fromtimestamp(self.started_at_utc, tz=timezone.utc)
        timestamp_str = dt.strftime("%Y%m%dT%H%M%SZ")
        dir_name = f"pubrun-{self.script_name}-{timestamp_str}-{self.pid}-{self.run_id}"
        self.run_dir = base_dir / dir_name

        # Ensure directory is created safely with restrictive permissions
        try:
            self.run_dir.mkdir(parents=True, exist_ok=True)
            # Restrict to owner-only on POSIX to prevent other users on shared
            # systems from reading captured environment data.
            if sys.platform != "win32":
                os.chmod(self.run_dir, 0o700)
        except Exception as e:
            # GHOST MODE: 
            # If filesystem is read-only (e.g. strict Slurm nodes), we silently abort
            # internal serialization tracking completely so the user's ML script doesn't crash.
            # However, we must alert the user via standard error so that Slurm logs show context.
            print(f"pubrun WARNING: Unable to create {self.run_dir}. System running in Ghost Mode (tracking suppressed) due to: {e}", file=sys.stderr)
            self.is_active = False
            self._outcome = "ghost"
            self._finalized = True
            self._spying_subprocesses = False
            self.event_stream = None
            self.resource_watcher = None
            self.writer = None
            self.hardware_data = {}
            self.invocation_data = {}
            self.console_data = {}
            self.git_data = {}
            self.process_data = {}
            self.python_data = {}
            self.packages_data = {}
            self.environment_data = {}
            self.host_data = {}
            self.console_interceptor = None
            self.signal_capture = None
            _active_run = self
            return
        
        # State tracking (to detect crashes)
        self._outcome = "unknown"
        self._finalized = False

        # Initialize all capture data to safe defaults so that a partial
        # init failure never leaves the object in an undefined state.
        self.invocation_data: Dict[str, Any] = {}
        self.git_data: Dict[str, Any] = {}
        self.process_data: Dict[str, Any] = {}
        self.python_data: Dict[str, Any] = {}
        self.packages_data: Dict[str, Any] = {}
        self.environment_data: Dict[str, Any] = {}
        self.hardware_data: Dict[str, Any] = {}
        self.host_data: Dict[str, Any] = {}
        self.console_data: Dict[str, Any] = {}
        self._spying_subprocesses = False
        self.console_interceptor = None
        self.event_stream = None
        self.resource_watcher = None
        self.signal_capture = None

        # ---- Phase 3: Bootstrap Capture Engines ----
        # Wrapped in a broad try/except so that a crash in any single engine
        # promotes the run to ghost mode rather than crashing the host script.
        try:
            self._bootstrap_engines()
        except Exception as engine_err:
            import logging as _logging
            _logging.getLogger("pubrun").warning(
                f"pubrun: capture engine init failed, entering ghost mode: {engine_err}"
            )
            self.is_active = False
            self._outcome = "ghost"
            self._finalized = True
            _active_run = self
            return
        # ---------------------------------------------

        # Wire up crash-safety
        self.writer = ArtifactWriter(self)
        self.writer.register_atexit()

        # Update global reference
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
            lock_data = {
                "pid": self.pid,
                "started_at_utc": self.started_at_utc,
                "script": self.script_name,
                "run_id": self.run_id,
                "hostname": platform.node(),
                "git_commit": git_commit,
                "cwd": str(Path.cwd()),
                "argv": sys.argv[1:] if len(sys.argv) > 1 else [],
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
        """Initialize all capture engines.

        Called from ``__init__``.  If this method raises, the run promotes
        itself to ghost mode (handled by the caller).
        """
        # 1. Invocation canonical path extraction
        self.invocation_data = get_invocation(self.config)

        # 2. Get Git provenance before subprocess tracking to prevent logging ourselves
        self.git_data = get_git(self.config)

        # Write lock file early so external tools can detect this run is active.
        self._write_lock_file()

        # 3. Process, Env, and Runtime Snapshotting
        self.process_data = get_process_info(self.config)
        self.python_data = get_python_runtime(self.config)
        self.packages_data = get_packages(self.config)
        self.environment_data = get_environment(self.config)

        # 4. Hardware tracking (Must run before SubprocessSpy to avoid logging psutil tools etc)
        self.hardware_data = get_hardware(self.config)
        self.host_data = get_host(self.config)

        # 5. Console & Subprocess interception setup
        if self.config.get("capture", {}).get("subprocesses", {}).get("enabled", False):
            max_tracked = self.config.get("capture", {}).get("subprocesses", {}).get("max_tracked_commands", 5000)
            SubprocessSpy.install(max_tracked, config=self.config)
            self._spying_subprocesses = True

        # 6. Console tee hook
        console_mode = self.config.get("console", {}).get("capture_mode", "off")
        self.console_interceptor = ConsoleInterceptor(self.run_dir, console_mode)
        self.console_interceptor.start()

        # 7. Event Stream
        if self.config.get("events", {}).get("enabled", False):
            self.event_stream = EventStream(self.run_dir, config=self.config)

        # 8. Background Telemetry (RAM watcher)
        res_cfg = self.config.get("capture", {}).get("resources", {})
        if res_cfg.get("depth", "off") != "off":
            interval = res_cfg.get("sample_interval_seconds", 15)
            max_fails = res_cfg.get("max_consecutive_failures", 3)
            self.resource_watcher = ResourceWatcher(self, interval, max_fails)
            self.resource_watcher.start()

        # 9. Signal and exit-code capture (non-intrusive, chains to user handlers)
        if self.config.get("capture", {}).get("signals", {}).get("enabled", True):
            self.signal_capture = SignalExitCapture()
            self.signal_capture.install()

    def _merge_and_migrate(self, overrides: Dict[str, Any]) -> None:
        """Merge new overrides into a running config. Migrates the run directory
        if the output_dir changes."""
        if not overrides:
            return
            
        merged = resolve_config(overrides)
        new_base_str = merged.get("core", {}).get("output_dir", "")
        
        if new_base_str:
            new_base = Path(new_base_str)
            new_dir = new_base / self.run_dir.name
            
            if new_dir != self.run_dir:
                try:
                    import shutil
                    new_dir.parent.mkdir(parents=True, exist_ok=True)
                    shutil.move(str(self.run_dir), str(new_dir))
                    old_dir_str = str(self.run_dir)
                    self.run_dir = new_dir
                    
                    if getattr(self, "event_stream", None):
                        self.event_stream.directory = new_dir
                        self.event_stream.emit("warning", payload={"message": f"Storage directory changed mid-execution from {old_dir_str} to {new_dir}"})
                        
                    if getattr(self, "console_interceptor", None) and hasattr(self.console_interceptor, "file_path"):
                        self.console_interceptor.file_path = new_dir / "console.log"
                        if hasattr(self.console_interceptor, "file") and self.console_interceptor.file and not self.console_interceptor.file.closed:
                            self.console_interceptor.file.flush()
                            self.console_interceptor.file.close()
                            self.console_interceptor.file = open(self.console_interceptor.file_path, "a", encoding="utf-8")
                        
                except Exception as e:
                    import logging
                    logging.getLogger("pubrun").warning(f"Failed migrating runtime paths: {e}")
                
        was_spying = self._spying_subprocesses
        will_spy = merged.get("capture", {}).get("subprocesses", {}).get("enabled", False)
        if will_spy and not was_spying:
            max_tracked = merged.get("capture", {}).get("subprocesses", {}).get("max_tracked_commands", 5000)
            SubprocessSpy.install(max_tracked)
            self._spying_subprocesses = True
            
        self.config = merged

    def _finalize_state(self) -> None:
        """Shut down all capture engines and record the final outcome.

        Idempotent — safe to call multiple times (guarded by ``_finalized``).
        If ``sys.exc_info()`` indicates an active exception, outcome is set
        to ``"failed"``.
        """
        if self._finalized:
            return
        self._finalized = True

        if self.is_active:
            self.ended_at_utc = time.time()
            self.is_active = False

        if self._outcome == "unknown":
            # If sys.exc_info() denotes an active crash at exit time, we log failed.
            if sys.exc_info()[0] is not None:
                exc_type = sys.exc_info()[0]
                if exc_type is KeyboardInterrupt:
                    self._outcome = "interrupted"
                else:
                    self._outcome = "failed"
            else:
                self._outcome = "completed"

        # If the outcome is nominally "completed" but we received termination
        # signals (SIGINT, SIGTERM, SIGHUP), upgrade to "interrupted".
        # This handles the common case where user code catches KeyboardInterrupt
        # and exits cleanly -- the signal was still received.
        if self._outcome == "completed" and self.signal_capture:
            records = self.signal_capture.get_records()
            interruption_signals = {"SIGINT", "SIGTERM", "SIGHUP"}
            for sig in records.get("signals_received", []):
                if sig.get("signal_name") in interruption_signals:
                    self._outcome = "interrupted"
                    break

        # Capture the exit code.  At atexit time we can inspect whether a
        # SystemExit was the cause.  For a clean exit, code is 0.
        if self.signal_capture:
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

        # Gracefully shutdown engines
        if self._spying_subprocesses:
            SubprocessSpy.finalize_all()
            SubprocessSpy.uninstall()
        if self.console_interceptor:
            self.console_data = self.console_interceptor.stop()
        if self.resource_watcher:
            self.resource_watcher.stop()
        if self.event_stream:
            self.event_stream.close()
        # Restore original signal handlers so pubrun leaves no footprint
        if self.signal_capture:
            self.signal_capture.uninstall()

        # Remove the lock file -- this run is no longer active.
        self._remove_lock_file()

    def stop(self, outcome: str = "completed") -> None:
        """Stop tracking, finalize engines, and write artifacts.

        Args:
            outcome: Result label (``"completed"`` or ``"failed"``).
                A ``"failed"`` outcome is sticky and cannot be overwritten.

        Decrements the reference count. Artifacts are written only when the
        count reaches zero.
        """
        if self._outcome != "failed":
            self._outcome = outcome

        from pubrun import _run_lock
        with _run_lock:
            self.ref_count = getattr(self, "ref_count", 1) - 1
            if self.ref_count > 0:
                return  # Still referenced by an outer wrapper.
            
        self._finalize_state()
        if getattr(self, "writer", None):
            self.writer.write_artifacts()
            
        global _active_run
        if _active_run is self:
            _active_run = None

    def to_manifest_dict(self) -> Dict[str, Any]:
        """Build and return the complete ``manifest.json`` dictionary."""
        elapsed = None
        if self.ended_at_utc:
            elapsed = self.ended_at_utc - self.started_at_utc
            
            pass # removed local string formatter hook
        subprocess_records = SubprocessSpy.get_records() if self._spying_subprocesses else []

        return {
            "schema_version": "1.0",
            "manifest_type": "pubrun-manifest",
            "meta_ref": self.config.get("core", {}).get("meta_ref", None),
            "run": {
                "run_id": self.run_id,
                "capture_state": {"status": "complete"}
            },
            "timing": {
                "started_at_utc": self.started_at_utc,
                "ended_at_utc": self.ended_at_utc,
                "elapsed_seconds": elapsed,
                "capture_state": {"status": "complete"}
            },
            
            # Integrated Phase 3 sections
            "invocation": self.invocation_data,
            "console": self.console_data,
            "subprocesses": subprocess_records,
            
            "process": self.process_data,
            "python": self.python_data,
            "packages": self.packages_data,
            "environment": self.environment_data,
            "git": self.git_data,
            "errors": {"records": [], "capture_state": {"status": "complete"}},
            
            "config": {
                "resolved_config_path": "config.resolved.json",
                "sources_path": None,
                "source_files": [],
                "capture_state": {"status": "complete"}
            },
            
            "hardware": self.hardware_data,
            "host": self.host_data,
            "resources": self.resource_watcher.to_manifest_dict() if self.resource_watcher else {"capture_state": {"status": "suppressed"}},
            
            "capture": {
                "output_base_dir": str(self.run_dir.parent),
                "run_dir": str(self.run_dir),
                "event_stream_enabled": self.config.get("events", {}).get("enabled", False),
                "console_capture_mode": self.config.get("console", {}).get("capture_mode", "off"),
                "capture_state": {"status": "complete"}
            },
            "signals": self.signal_capture.get_records() if self.signal_capture else {"capture_state": {"status": "suppressed"}},

            "status": {
                "outcome": self._outcome,
                "capture_state": {"status": "complete"}
            }
        }
