import json
import logging
import os
import threading
import time
from typing import Any, Dict, List, Optional, TextIO
from pathlib import Path

from pubrun.capture.signals import finalization_lock
from pubrun.config import _section
from pubrun.writer import _sanitize_json_value

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
        self._pid = os.getpid()
        self._lock = threading.Lock()
        self._event_count = 0

        if config is None:
            from pubrun.config import resolve_config
            config = resolve_config()
        self._config: Optional[Dict[str, Any]] = config
        self._write_failed: bool = False
        self._last_error: Optional[str] = None
        events_cfg = _section(config, "events")
        raw_max_events = events_cfg.get("max_tracked_events", 1_000_000)
        if (
            isinstance(raw_max_events, int)
            and not isinstance(raw_max_events, bool)
            and raw_max_events >= 0
        ):
            self._max_events = raw_max_events
        else:
            logger.warning(
                "pubrun: invalid events.max_tracked_events %r; falling back to 1000000",
                raw_max_events,
            )
            self._max_events = 1_000_000
        # Secondary cap for critical events (annotations, phases) to prevent
        # unbounded disk writes from scripts calling annotate() in tight loops.
        # Minimum of 10,000 ensures critical events always have headroom even
        # when max_tracked_events is set very low.
        self._max_critical_events = max(10_000, self._max_events * 10)
        self._critical_event_count = 0

        # PERF-06: Buffer non-critical events to reduce flush() syscalls.
        # Critical events still get immediate flush for crash safety.
        raw_flush_interval = events_cfg.get("flush_interval_events", 100)
        if (
            isinstance(raw_flush_interval, int)
            and not isinstance(raw_flush_interval, bool)
            and raw_flush_interval >= 1
        ):
            self._flush_interval = raw_flush_interval
        else:
            logger.warning(
                "pubrun: invalid events.flush_interval_events %r; falling back to 100",
                raw_flush_interval,
            )
            self._flush_interval = 100
        self._buffer: List[str] = []
        self._file: Optional[TextIO] = None

        try:
            # We keep the handle open in append mode for rapid high-frequency writes
            # typical in machine learning epochs.
            self._file = open(self.stream_path, "a", encoding="utf-8")
        except Exception as e:
            from pubrun.capture.redaction import format_safe_error_detail
            detail = format_safe_error_detail(e, self._config)
            self._last_error = detail
            logger.debug("pubrun failed to open event stream: %s", detail)
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
        if self._file is None or os.getpid() != self._pid:
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
            line = json.dumps(_sanitize_json_value(record), allow_nan=False) + "\n"
        except (TypeError, ValueError, OverflowError) as ser_err:
            # BUG-05: Non-serializable payload -- log at warning so user knows.
            logger.warning(
                f"pubrun: event '{event_type}' dropped (payload not JSON-serializable): {ser_err}"
            )
            return

        should_warn = False
        warn_detail = ""
        with finalization_lock(self._lock, 0.25) as acquired:
            if not acquired or self._file is None:
                return
            try:
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
                f, self._file = self._file, None
                self._buffer.clear()
                try:
                    if f is not None:
                        f.close()
                except Exception:
                    pass
                from pubrun.capture.redaction import format_safe_error_detail
                detail = format_safe_error_detail(e, self._config)
                self._last_error = detail
                should_warn = not self._write_failed
                self._write_failed = True
                warn_detail = detail

        if should_warn:
            logger.warning("pubrun: event stream write failed: %s", warn_detail)

    def close(self) -> None:
        """Flush and close the event stream file. Safe to call multiple times."""
        if os.getpid() != self._pid:
            self._file = None
            self._buffer = []
            return
        with finalization_lock(self._lock, 0.25) as acquired:
            if not acquired:
                return
            f, self._file = self._file, None
            buf = self._buffer
            self._buffer = []
            if f is not None:
                _flush_and_close(f, buf)

    def migrate_directory(self, new_dir: Path) -> None:
        """Close the current stream file, update the path to the new directory,
        and reopen the file in append mode. Safe to call concurrently."""
        with self._lock:
            f, self._file = self._file, None
            buf = self._buffer
            self._buffer = []
            if f is not None:
                _flush_and_close(f, buf)
            self.stream_path = new_dir / "events.jsonl"
            try:
                self._file = open(self.stream_path, "a", encoding="utf-8")
                self._write_failed = False
                self._last_error = None
            except Exception as e:
                from pubrun.capture.redaction import format_safe_error_detail
                detail = format_safe_error_detail(e, self._config)
                self._last_error = detail
                logger.debug("pubrun failed to open migrated event stream: %s", detail)
                self._file = None


def _flush_and_close(f: Any, buf: List[str]) -> None:
    """Write any buffered lines and flush ``f``, then always close it.

    The close runs in ``finally`` so the descriptor is released even when the
    flush raises ``OSError`` or a ``BaseException`` such as ``KeyboardInterrupt``.
    """
    try:
        try:
            if buf:
                f.writelines(buf)
            f.flush()
        except Exception:
            pass
    finally:
        try:
            f.close()
        except Exception:
            pass
