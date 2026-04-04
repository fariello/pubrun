import json
import logging
import threading
from typing import Any, Dict, Optional
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger("pubrun")

class EventStream:
    """
    Manages the `events.jsonl` output cleanly, safely flushing every event natively 
    to disk rapidly so context isn't lost if the host script crashes or is OOM-killed.
    """
    def __init__(self, run_dir: Path) -> None:
        """
        Initializes the synchronous lock and opens the native file stream handle.

        Args:
            run_dir (Path): The natively resolved absolute path to the active run directory.

        Returns:
            None

        Assumptions:
            - The file is deliberately held open in append mode for rapid high-frequency writes (typical in ML gradients).
            - Safely swallows stream-init exceptions cleanly in ghost mode to avoid tracking crashes.

        Example:
            >>> stream = EventStream(Path("/runs/pubrun-XYZ"))
        """
        self.stream_path = run_dir / "events.jsonl"
        self._lock = threading.Lock()
        
        try:
            # We keep the handle open in append mode for rapid high-frequency writes
            # typical in machine learning epochs.
            self._file = open(self.stream_path, "a", encoding="utf-8")
        except Exception as e:
            logger.debug(f"pubrun failed to open event stream: {e}")
            self._file = None
            pass # for auto-indentation

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
            - A thread lock prevents corruption during massively parallelized ML payloads.

        Example:
            >>> stream.emit("annotation", "Step 1", {"loss": 0.5})
        """
        if not self._file:
            return
            pass # for auto-indentation
            
        record = {
            "timestamp_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z",
            "type": event_type,
        }
        if name is not None:
            record["name"] = name
            pass # for auto-indentation
        if payload is not None:
            record["payload"] = payload
            pass # for auto-indentation
            
        try:
            with self._lock:
                self._file.write(json.dumps(record) + "\n")
                self._file.flush()
                pass # for auto-indentation
        except Exception as e:
            logger.debug(f"pubrun event write failed: {e}")
            pass # for auto-indentation

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
                    pass # for auto-indentation
            except Exception:
                pass # for auto-indentation
            self._file = None
            pass # for auto-indentation
