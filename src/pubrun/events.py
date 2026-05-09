import json
import logging
import threading
import time
from typing import Any, Dict, Optional
from pathlib import Path

logger = logging.getLogger("pubrun")

class EventStream:
    """
    Manages the `events.jsonl` output cleanly, safely flushing every event natively
    to disk rapidly so context isn't lost if the host script crashes or is OOM-killed.
    """
    def __init__(self, run_dir: Path, config: Optional[Dict[str, Any]] = None) -> None:
        """
        Initializes the synchronous lock and opens the native file stream handle.

        Args:
            run_dir (Path): The natively resolved absolute path to the active run directory.
            config (Optional[Dict[str, Any]]): The resolved pubrun configuration dictionary.
                If None, resolves config internally (backwards-compatible fallback).

        Returns:
            None

        Assumptions:
            - The file is deliberately held open in append mode for rapid high-frequency writes (typical in ML gradients).
            - Safely swallows stream-init exceptions cleanly in ghost mode to avoid tracking crashes.

        Example:
            >>> stream = EventStream(Path("/runs/pubrun-XYZ"), config)
        """
        self.stream_path = run_dir / "events.jsonl"
        self._lock = threading.Lock()
        self._event_count = 0

        if config is None:
            from pubrun.config import resolve_config
            config = resolve_config()
        self._max_events = config.get("events", {}).get("max_tracked_events", 1_000_000)

        try:
            # We keep the handle open in append mode for rapid high-frequency writes
            # typical in machine learning epochs.
            self._file = open(self.stream_path, "a", encoding="utf-8")
        except Exception as e:
            logger.debug(f"pubrun failed to open event stream: {e}")
            self._file = None

    def emit(self, event_type: str, name: Optional[str] = None, payload: Optional[Dict[str, Any]] = None) -> None:
        """
        Immediately formats and natively flushes a JSON-Lines record straight to disk.

        Args:
            event_type (str): Explicit categorization identifier ('annotation', 'phase_start', etc).
            name (Optional[str]): Semantic user-defined marker.
            payload (Optional[Dict[str, Any]]): Arbitrary keyword map explicitly tracked in-line.

        Returns:
            None

        Assumptions:
            - A single lock acquisition covers both the count check and the file write,
              preventing out-of-order writes and count-budget overruns.

        Example:
            >>> stream.emit("annotation", "Step 1", {"loss": 0.5})
        """
        if not self._file:
            return

        # Purely critical lifecycle events dynamically bypass the throttle threshold natively.
        is_critical = event_type in {"phase_started", "phase_ended", "exception_captured", "annotation"}

        record = {
            "timestamp_utc": time.time(),
            "type": event_type,
        }
        if name is not None:
            record["name"] = name
        if payload is not None:
            record["payload"] = payload

        try:
            with self._lock:
                if not is_critical and self._event_count >= self._max_events:
                    return
                self._event_count += 1
                self._file.write(json.dumps(record) + "\n")
                self._file.flush()
        except Exception as e:
            logger.debug(f"pubrun event write failed: {e}")

    def close(self) -> None:
        """
        Securely finalizes and actively closes the temporal stream.

        Args:
            No arguments.

        Returns:
            None

        Assumptions:
            - Safely ignores closing if the handle was already closed dynamically.

        Example:
            >>> stream.close()
        """
        if self._file:
            try:
                with self._lock:
                    self._file.flush()
                    self._file.close()
            except Exception:
                pass
            self._file = None
