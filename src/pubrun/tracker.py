import os
import sys
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


# Define a singleton instance to manage global tracking state
_active_run: Optional["Run"] = None


def get_current_run() -> Optional["Run"]:
    """Returns the globally active Run, if any."""
    return _active_run


class Run:
    """
    The core tracking object. Responsible for gathering mandatory base sections 
    and generating the output structures cleanly.
    """
    def __init__(self, overrides: Optional[Dict[str, Any]] = None) -> None:
        global _active_run
        
        self.config = resolve_config(overrides)
        self.run_id = uuid.uuid4().hex[:8]
        self.pid = os.getpid()
        self.script_name = Path(sys.argv[0]).stem if sys.argv and sys.argv[0] else "interactive"
        
        # Timing state (explicit UTC timezone requirement)
        self.started_at_utc = datetime.now(timezone.utc)
        self.ended_at_utc: Optional[datetime] = None
        self.is_active = True
        
        # Establish the unique run directory name
        base_dir_str = self.config.get("core", {}).get("output_dir", "")
        base_dir = Path(base_dir_str) if base_dir_str else Path.cwd() / "runs"
        timestamp_str = self.started_at_utc.strftime("%Y%m%dT%H%M%SZ")
        dir_name = f"pubrun-{self.script_name}-{timestamp_str}-{self.pid}-{self.run_id}"
        self.run_dir = base_dir / dir_name

        # Ensure directory is created safely
        try:
            self.run_dir.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            # GHOST MODE: 
            # If filesystem is read-only (e.g. strict Slurm nodes), we silently abort
            # internal serialization tracking completely so the user's ML script doesn't crash.
            # However, we must alert the user via standard error so that Slurm logs show context.
            print(f"pubrun WARNING: Unable to create {self.run_dir}. System running in Ghost Mode (tracking suppressed) due to: {e}", file=sys.stderr)
            self.is_active = False
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
            self.console_interceptor = None
            _active_run = self
            return
        
        # State tracking (to detect crashes)
        self._outcome = "unknown"
        
        # ---- Phase 3: Bootstrap Capture Engines ----
        # 1. Invocation canonical path extraction
        self.invocation_data = get_invocation(self.config)
        
        # 2. Get Git provenance before subprocess tracking to prevent logging ourselves
        self.git_data = get_git(self.config)
        
        # 3. Process, Env, and Runtime Snapshotting
        self.process_data = get_process_info(self.config)
        self.python_data = get_python_runtime(self.config)
        self.packages_data = get_packages(self.config)
        self.environment_data = get_environment(self.config)
        
        # 4. Hardware tracking (Must run before SubprocessSpy to avoid logging psutil tools etc)
        self.hardware_data = get_hardware(self.config)
        
        # 4. Console & Subprocess interception setup
        if self.config.get("capture", {}).get("subprocesses", {}).get("enabled", False):
            max_tracked = self.config.get("capture", {}).get("subprocesses", {}).get("max_tracked_commands", 5000)
            SubprocessSpy.install(max_tracked)
            self._spying_subprocesses = True
        else:
            self._spying_subprocesses = False
            
        # 3. Console tee hook
        console_mode = self.config.get("capture", {}).get("console", {}).get("capture_mode", "off")
        self.console_interceptor = ConsoleInterceptor(self.run_dir, console_mode)
        self.console_interceptor.start()
        
        self.console_data: Dict[str, Any] = {}
        
        # 5. Event Stream
        self.event_stream = None
        if self.config.get("events", {}).get("enabled", False):
            self.event_stream = EventStream(self.run_dir)
            
        # 6. Background Telemetry (RAM watcher)
        self.resource_watcher = None
        res_cfg = self.config.get("capture", {}).get("resources", {})
        if res_cfg.get("depth", "off") != "off":
            interval = res_cfg.get("sample_interval_seconds", 15)
            max_fails = res_cfg.get("max_consecutive_failures", 3)
            self.resource_watcher = ResourceWatcher(self, interval, max_fails)
            self.resource_watcher.start()
        # ---------------------------------------------
        
        # Wire up crash-safety
        self.writer = ArtifactWriter(self)
        self.writer.register_atexit()

        # Update global reference
        _active_run = self

    def _finalize_state(self) -> None:
        """Called automatically strictly before serialization."""
        if self.is_active:
            self.ended_at_utc = datetime.now(timezone.utc)
            self.is_active = False

        if self._outcome == "unknown":
            # If sys.exc_info() denotes an active crash at exit time, we log failed.
            if sys.exc_info()[0] is not None:
                self._outcome = "failed"
            else:
                self._outcome = "completed"
                
        # Gracefully shutdown engines
        if self._spying_subprocesses:
            SubprocessSpy.finalize_all()
            SubprocessSpy.uninstall()
        self.console_data = self.console_interceptor.stop()
        if self.resource_watcher:
            self.resource_watcher.stop()
        if self.event_stream:
            self.event_stream.close()

    def stop(self, outcome: str = "completed") -> None:
        """Manually halt tracking, overriding the atexit hooks."""
        self._outcome = outcome
        self._finalize_state()
        if getattr(self, "writer", None):
            self.writer.write_artifacts()
            
        global _active_run
        if _active_run is self:
            _active_run = None

    def to_manifest_dict(self) -> Dict[str, Any]:
        """Constructs the canonical manifest.json dict."""
        elapsed = None
        if self.ended_at_utc:
            elapsed = (self.ended_at_utc - self.started_at_utc).total_seconds()
            
        def _str_fmt(dt: datetime) -> str:
            """Formats datetime specifically to match exact JSON Schema regex pattern: Z"""
            return dt.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
            
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
                "started_at_utc": _str_fmt(self.started_at_utc),
                "ended_at_utc": _str_fmt(self.ended_at_utc) if self.ended_at_utc else None,
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
            "resources": self.resource_watcher.to_manifest_dict() if self.resource_watcher else {"capture_state": {"status": "suppressed"}},
            
            "capture": {
                "output_base_dir": str(self.run_dir.parent),
                "run_dir": str(self.run_dir),
                "event_stream_enabled": self.config.get("events", {}).get("enabled", False),
                "console_capture_mode": self.config.get("capture", {}).get("console", {}).get("capture_mode", "off"),
                "capture_state": {"status": "complete"}
            },
            "status": {
                "outcome": self._outcome,
                "capture_state": {"status": "complete"}
            }
        }
