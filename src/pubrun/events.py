import json
import logging
import threading
import time
from typing import Any, Dict, List, Optional
from pathlib import Path

logger = logging.getLogger("pubrun")

class EventStream:
    """Manages the ``events.jsonl`` output with buffered writes for throughput.

    Critical events (annotations, phases) are flushed immediately to preserve
    context on crash. Non-critical events (resource_sample, etc.) are buffered
    and flushed every ``_flush_interval`` events or on close/explicit flush.
    """
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

        # PERF-06: Buffer non-critical events to reduce flush() syscalls.
        # Critical events still get immediate flush for crash safety.
        self._flush_interval = config.get("events", {}).get("flush_interval_events", 100)
        self._buffer: List[str] = []

        try:
            # We keep the handle open in append mode for rapid high-frequency writes
            # typical in machine learning epochs.
            self._file = open(self.stream_path, "a", encoding="utf-8")
        except Exception as e:
            logger.debug(f"pubrun failed to open event stream: {e}")
            self._file = None

    def emit(self, event_type: str, name: Optional[str] = None, payload: Optional[Dict[str, Any]] = None) -> None:
        """Write one JSON-Lines record to disk.

        Critical events (phase_start, phase_end, annotation) are flushed
        immediately. Non-critical events are buffered and flushed every
        ``flush_interval_events`` writes.

        Args:
            event_type: Category string (e.g. ``"annotation"``, ``"phase_start"``).
            name: Optional semantic label.
            payload: Optional key-value data attached to the event.
        """
        if not self._file:
            return

        # Critical lifecycle events bypass the throttle threshold so they are
        # never silently dropped.
        is_critical = event_type in {"phase_start", "phase_end", "annotation"}

        record = {
            "timestamp_utc": time.time(),
            "type": event_type,
        }
        if name is not None:
            record["name"] = name
        if payload is not None:
            record["payload"] = payload

        # Serialize outside the lock for reduced contention (PERF-06).
        try:
            line = json.dumps(record) + "\n"
        except (TypeError, ValueError, OverflowError) as ser_err:
            # BUG-05: Non-serializable payload — log at warning so user knows.
            logger.warning(
                f"pubrun: event '{event_type}' dropped (payload not JSON-serializable): {ser_err}"
            )
            return

        try:
            with self._lock:
                if is_critical:
                    if self._critical_event_count >= self._max_critical_events:
                        return
                    self._critical_event_count += 1
                    # Flush any buffered events first, then write + flush immediately.
                    if self._buffer:
                        self._file.writelines(self._buffer)
                        self._buffer.clear()
                    self._file.write(line)
                    self._file.flush()
                else:
                    if self._event_count >= self._max_events:
                        return
                    self._event_count += 1
                    self._buffer.append(line)
                    if len(self._buffer) >= self._flush_interval:
                        self._file.writelines(self._buffer)
                        self._buffer.clear()
                        self._file.flush()
        except Exception as e:
            logger.debug(f"pubrun event write failed: {e}")

    def close(self) -> None:
        """Flush and close the event stream file. Safe to call multiple times."""
        with self._lock:
            if self._file:
                try:
                    # Flush remaining buffer before closing.
                    if self._buffer:
                        self._file.writelines(self._buffer)
                        self._buffer.clear()
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
                    if self._buffer:
                        self._file.writelines(self._buffer)
                        self._buffer.clear()
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
