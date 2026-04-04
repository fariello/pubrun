import json
import logging
import threading
from typing import Any, Dict, Optional
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger("pubrun")

class EventStream:
    """
    Manages the events.jsonl output. Safely flushes every event to disk rapidly
    so context isn't lost if the host script crashes or is OOM-killed.
    """
    def __init__(self, run_dir: Path):
        self.stream_path = run_dir / "events.jsonl"
        self._lock = threading.Lock()
        
        try:
            # We keep the handle open in append mode for rapid high-frequency writes
            # typical in machine learning epochs.
            self._file = open(self.stream_path, "a", encoding="utf-8")
        except Exception as e:
            logger.debug(f"pubrun failed to open event stream: {e}")
            self._file = None

    def emit(self, event_type: str, name: Optional[str] = None, payload: Optional[Dict[str, Any]] = None) -> None:
        """Immediately formats and flushes a JSONL record out."""
        if not self._file:
            return
            
        record = {
            "timestamp_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z",
            "type": event_type,
        }
        if name is not None:
            record["name"] = name
        if payload is not None:
            record["payload"] = payload
            
        try:
            with self._lock:
                self._file.write(json.dumps(record) + "\n")
                self._file.flush()
        except Exception as e:
            logger.debug(f"pubrun event write failed: {e}")

    def close(self) -> None:
        if self._file:
            try:
                with self._lock:
                    self._file.flush()
                    self._file.close()
            except Exception:
                pass
            self._file = None
