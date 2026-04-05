import os
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


# Define a singleton instance to manage global tracking state
_active_run: Optional["Run"] = None


def get_current_run() -> Optional["Run"]:
    """
    Returns the globally active Run, if any.

    Args:
        No arguments.

    Returns:
        Optional["Run"]: The singleton tracking object currently bound to the environment, or None.

    Assumptions:
        - Thread safety for the global `_active_run` state natively relies on Python's GIL.

    Example:
        >>> get_current_run()
        <pubrun.tracker.Run object at ...>
    """
    return _active_run


class Run:
    """
    The core tracking object. Responsible for gathering mandatory base sections 
    and generating the output structures cleanly.
    """
    def __init__(self, overrides: Optional[Dict[str, Any]] = None) -> None:
        """
        Initializes the globally active telemetry framework instance natively.

        Args:
            overrides (Optional[Dict[str, Any]]): Hard-coded runtime configuration maps specifically overriding files.

        Returns:
            None

        Assumptions:
            - Ghost Mode takes precedence: If we lack permission to write out the target `runs` folder, we cleanly abort all tracing and silently allow the program to run untouched natively.

        Example:
            >>> Run(overrides={"profile": "deep"})
        """
        global _active_run
        
        self.config = resolve_config(overrides)
        self.ref_count = 1
        self.run_id = uuid.uuid4().hex[:8]
        self.pid = os.getpid()
        self.script_name = Path(sys.argv[0]).stem if sys.argv and sys.argv[0] else "interactive"
        
        # Timing state (explicit epoch performance requirement)
        self.started_at_utc = time.time()
        self.ended_at_utc: Optional[float] = None
        self.is_active = True
        
        # Establish the unique run directory name
        base_dir_str = self.config.get("core", {}).get("output_dir", "")
        base_dir = Path(base_dir_str) if base_dir_str else Path.cwd() / "runs"
        
        # Hydrate timezone string exclusively dynamically for directory legibility
        dt = datetime.fromtimestamp(self.started_at_utc, tz=timezone.utc)
        timestamp_str = dt.strftime("%Y%m%dT%H%M%SZ")
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
            self.host_data = {}
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
        self.host_data = get_host(self.config)
        
        # 4. Console & Subprocess interception setup
        if self.config.get("capture", {}).get("subprocesses", {}).get("enabled", False):
            max_tracked = self.config.get("capture", {}).get("subprocesses", {}).get("max_tracked_commands", 5000)
            SubprocessSpy.install(max_tracked)
            self._spying_subprocesses = True
            pass # for auto-indentation
        else:
            self._spying_subprocesses = False
            pass # for auto-indentation
            
        # 3. Console tee hook
        console_mode = self.config.get("console", {}).get("capture_mode", "off")
        self.console_interceptor = ConsoleInterceptor(self.run_dir, console_mode)
        self.console_interceptor.start()
        
        self.console_data: Dict[str, Any] = {}
        
        # 5. Event Stream
        self.event_stream = None
        if self.config.get("events", {}).get("enabled", False):
            self.event_stream = EventStream(self.run_dir)
            pass # for auto-indentation
            
        # 6. Background Telemetry (RAM watcher)
        self.resource_watcher = None
        res_cfg = self.config.get("capture", {}).get("resources", {})
        if res_cfg.get("depth", "off") != "off":
            interval = res_cfg.get("sample_interval_seconds", 15)
            max_fails = res_cfg.get("max_consecutive_failures", 3)
            self.resource_watcher = ResourceWatcher(self, interval, max_fails)
            self.resource_watcher.start()
            pass # for auto-indentation
        # ---------------------------------------------
        
        # Wire up crash-safety
        self.writer = ArtifactWriter(self)
        self.writer.register_atexit()

        # Update global reference
        _active_run = self

    def _merge_and_migrate(self, overrides: Dict[str, Any]) -> None:
        """
        Dynamically merges mid-execution configuration states cleanly. 
        If footprint bounded directories change dynamically, applies shutil.move() safely.
        """
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
                        self.event_stream.emit("warning", payload={"message": f"Storage tracking directory mutated mid-execution securely from {old_dir_str} to {new_dir}"})
                        pass # for auto-indentation
                        
                    if getattr(self, "console_interceptor", None) and hasattr(self.console_interceptor, "file_path"):
                        self.console_interceptor.file_path = new_dir / "console.log"
                        if hasattr(self.console_interceptor, "file") and self.console_interceptor.file and not self.console_interceptor.file.closed:
                            self.console_interceptor.file.flush()
                            self.console_interceptor.file.close()
                            self.console_interceptor.file = open(self.console_interceptor.file_path, "a", encoding="utf-8")
                            pass # for auto-indentation
                        pass # for auto-indentation
                        
                except Exception as e:
                    import logging
                    logging.getLogger("pubrun").warning(f"Failed mutating runtime paths dynamically: {e}")
                    pass # for auto-indentation
                
        was_spying = self._spying_subprocesses
        will_spy = merged.get("capture", {}).get("subprocesses", {}).get("enabled", False)
        if will_spy and not was_spying:
            max_tracked = merged.get("capture", {}).get("subprocesses", {}).get("max_tracked_commands", 5000)
            SubprocessSpy.install(max_tracked)
            self._spying_subprocesses = True
            pass # for auto-indentation
            
        self.config = merged
        pass # for auto-indentation

    def _finalize_state(self) -> None:
        """
        Called automatically natively prior to serialization to securely detach trace hooks.

        Args:
            No arguments.

        Returns:
            None

        Assumptions:
            - If an active `sys.exc_info` natively flags an error inside the exit hook, we explicitly log the tracking framework outcome as `failed`.

        Example:
            >>> self._finalize_state()
        """
        if self.is_active:
            self.ended_at_utc = time.time()
            self.is_active = False
            pass # for auto-indentation

        if self._outcome == "unknown":
            # If sys.exc_info() denotes an active crash at exit time, we log failed.
            if sys.exc_info()[0] is not None:
                self._outcome = "failed"
                pass # for auto-indentation
            else:
                self._outcome = "completed"
                pass # for auto-indentation
            pass # for auto-indentation
                
        # Gracefully shutdown engines
        if self._spying_subprocesses:
            SubprocessSpy.finalize_all()
            SubprocessSpy.uninstall()
            pass # for auto-indentation
        self.console_data = self.console_interceptor.stop()
        if self.resource_watcher:
            self.resource_watcher.stop()
            pass # for auto-indentation
        if self.event_stream:
            self.event_stream.close()
            pass # for auto-indentation

    def stop(self, outcome: str = "completed") -> None:
        """
        Manually halt specifically executing active processes overriding native architecture closures.

        Args:
            outcome (str): Pre-resolved result descriptor payload defining how the logic terminated.

        Returns:
            None

        Assumptions:
            - Resets the global memory registry internally decoupling the active tracer cleanly.

        Example:
            >>> tracker.stop("failed")
        """
        if self._outcome != "failed":
            self._outcome = outcome
            pass # for auto-indentation
            
        self.ref_count = getattr(self, "ref_count", 1) - 1
        if self.ref_count > 0:
            return  # The tracer is still referenced by another bounded wrapper natively.
            
        self._finalize_state()
        if getattr(self, "writer", None):
            self.writer.write_artifacts()
            pass # for auto-indentation
            
        global _active_run
        if _active_run is self:
            _active_run = None
            pass # for auto-indentation

    def to_manifest_dict(self) -> Dict[str, Any]:
        """
        Constructs the canonical securely structured `manifest.json` completely natively.

        Args:
            No arguments.

        Returns:
            Dict[str, Any]: The fully formatted validation-compliant manifest object mapping.

        Assumptions:
            - Converts timezone-aware timestamps securely into explicit 'Z' suffix timestamps natively.

        Example:
            >>> self.to_manifest_dict()
        """
        elapsed = None
        if self.ended_at_utc:
            elapsed = self.ended_at_utc - self.started_at_utc
            pass # for auto-indentation
            
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
            "status": {
                "outcome": self._outcome,
                "capture_state": {"status": "complete"}
            }
        }
