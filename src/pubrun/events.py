import json
import logging
import threading
import time
from typing import Any, Dict, Optional
from pathlib import Path

logger = logging.getLogger("pubrun")

class EventStream:
    """Manages the ``events.jsonl`` output, flushing each event immediately
    to disk so context is preserved if the host script crashes."""
    def __init__(self, run_dir: Path, config: Optional[Dict[str, Any]] = None) -> None:
        """Open the event stream file for writing.

        Args:
            run_dir: Path to the active run directory.
            config: Resolved pubrun config. If None, resolves internally.
        """
        self.stream_path = run_dir / "events.jsonl"
        self._lock = threading.Lock()
        self._event_count = 0

        if config is None:
            from pubrun.config import resolve_config
            config = resolve_config()
        self._max_events = config.get("events", {}).get("max_tracked_events", 1_000_000)
        # Secondary cap for critical events (annotations, phases) to prevent
        # unbounded disk writes from scripts calling annotate() in tight loops.
        # Minimum of 10,000 ensures critical events always have headroom even
        # when max_tracked_events is set very low.
        self._max_critical_events = max(10_000, self._max_events * 10)
        self._critical_event_count = 0

        try:
            # We keep the handle open in append mode for rapid high-frequency writes
            # typical in machine learning epochs.
            self._file = open(self.stream_path, "a", encoding="utf-8")
        except Exception as e:
            logger.debug(f"pubrun failed to open event stream: {e}")
            self._file = None

    def emit(self, event_type: str, name: Optional[str] = None, payload: Optional[Dict[str, Any]] = None) -> None:
        """Write one JSON-Lines record to disk.

        Args:
            event_type: Category string (e.g. ``"annotation"``, ``"phase_start"``).
            name: Optional semantic label.
            payload: Optional key-value data attached to the event.
        """
        if not self._file:
            return

        # Critical lifecycle events bypass the throttle threshold so they are
        # never silently dropped.  The names here MUST match the event_type
        # strings passed to emit() elsewhere (phase_start / phase_end /
        # annotation).
        is_critical = event_type in {"phase_start", "phase_end", "annotation"}

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
                if is_critical:
                    if self._critical_event_count >= self._max_critical_events:
                        return
                    self._critical_event_count += 1
                else:
                    if self._event_count >= self._max_events:
                        return
                    self._event_count += 1
                self._file.write(json.dumps(record) + "\n")
                self._file.flush()
        except Exception as e:
            logger.debug(f"pubrun event write failed: {e}")

    def close(self) -> None:
        """Flush and close the event stream file. Safe to call multiple times."""
        with self._lock:
            if self._file:
                try:
                    self._file.flush()
                    self._file.close()
                except Exception:
                    pass
                self._file = None

    def migrate_directory(self, new_dir: Path) -> None:
        """Close the current stream file, update the path to the new directory,
        and reopen the file in append mode. Safe to call concurrently."""
        with self._lock:
            if self._file:
                try:
                    self._file.flush()
                    self._file.close()
                except Exception:
                    pass
                self._file = None
            self.stream_path = new_dir / "events.jsonl"
            try:
                self._file = open(self.stream_path, "a", encoding="utf-8")
            except Exception as e:
                logger.debug(f"pubrun failed to open migrated event stream: {e}")
                self._file = None

