import os
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from runtrace.config import resolve_config
from runtrace.writer import ArtifactWriter

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
        dir_name = f"runtrace-{self.script_name}-{timestamp_str}-{self.pid}-{self.run_id}"
        self.run_dir = base_dir / dir_name

        # Ensure directory is created before registering hooks
        self.run_dir.mkdir(parents=True, exist_ok=True)
        
        # State tracking (to detect crashes)
        self._outcome = "unknown"
        
        # Wire up crash-safety
        self.writer = ArtifactWriter(self)
        self.writer.register_atexit()

        # Update global reference
        global _active_run
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

    def stop(self, outcome: str = "completed") -> None:
        """Manually halt tracking, overriding the atexit hooks."""
        self._outcome = outcome
        self._finalize_state()
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

        return {
            "schema_version": "1.0",
            "manifest_type": "runtrace-manifest",
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
            "invocation": {
                "argv": sys.argv,
                "capture_state": {"status": "complete"}
            },
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
