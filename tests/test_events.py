"""Tests for EventStream: creation, throttling, close idempotency, and event format."""
import json
import logging
from pathlib import Path

from pubrun import start, annotate, phase
from pubrun.events import EventStream


class TestEventStreamCreation:

    def test_creates_jsonl_file(self):
        t = start(events={"enabled": True}, capture={"resources": {"depth": "off"}})
        annotate("Training started", epoch=1)
        with phase("Data Prep"):
            annotate(records_processed=50, msg="halfway")
        try:
            with phase("Failing Phase"):
                raise ValueError("Something broke")
        except ValueError:
            pass
        t.stop()

        events_path = t.run_dir / "events.jsonl"
        assert events_path.exists()

        lines = events_path.read_text("utf-8").strip().splitlines()
        assert len(lines) == 6

        ev0 = json.loads(lines[0])
        assert ev0["type"] == "annotation"
        assert ev0["name"] == "Training started"
        assert ev0["payload"]["epoch"] == 1

        ev1 = json.loads(lines[1])
        assert ev1["type"] == "phase_start"
        assert ev1["name"] == "Data Prep"

        ev5 = json.loads(lines[5])
        assert ev5["type"] == "phase_end"
        assert ev5["name"] == "Failing Phase"
        assert ev5["payload"]["error"] == "ValueError"


class TestEventStreamInactive:

    def test_annotate_without_events_is_silent(self, caplog):
        caplog.set_level(logging.WARNING, logger="pubrun")
        annotate("Should be silently ignored because default is ignore")
        assert "Annotation dropped" not in caplog.text


class TestEventStreamThrottling:

    def test_max_events_respected(self, tmp_path):
        config = {"events": {"enabled": True, "max_tracked_events": 5}}
        stream = EventStream(tmp_path, config=config)

        # Emit 10 regular events
        for i in range(10):
            stream.emit("metric", name=f"step_{i}", payload={"value": i})
        stream.close()

        lines = (tmp_path / "events.jsonl").read_text("utf-8").strip().splitlines()
        assert len(lines) == 5

    def test_critical_events_bypass_throttle(self, tmp_path):
        config = {"events": {"enabled": True, "max_tracked_events": 3}}
        stream = EventStream(tmp_path, config=config)

        # Fill up with regular events
        for i in range(5):
            stream.emit("metric", name=f"step_{i}")

        # Critical events should still be accepted after budget is exhausted
        stream.emit("annotation", name="important")
        stream.emit("phase_start", name="critical_phase")
        stream.emit("phase_end", name="critical_phase")
        stream.close()

        lines = (tmp_path / "events.jsonl").read_text("utf-8").strip().splitlines()
        # 3 regular + 3 critical = 6
        assert len(lines) == 6

    def test_phase_events_bypass_throttle(self, tmp_path):
        """Regression: phase_start/phase_end must bypass throttle (was broken when
        bypass set used old names phase_started/phase_ended)."""
        config = {"events": {"enabled": True, "max_tracked_events": 0}}
        stream = EventStream(tmp_path, config=config)

        # Budget is 0 — only critical events should be written
        stream.emit("metric", name="blocked")
        stream.emit("phase_start", name="training")
        stream.emit("phase_end", name="training")
        stream.close()

        lines = (tmp_path / "events.jsonl").read_text("utf-8").strip().splitlines()
        assert len(lines) == 2
        assert json.loads(lines[0])["type"] == "phase_start"
        assert json.loads(lines[1])["type"] == "phase_end"

    def test_zero_max_events(self, tmp_path):
        config = {"events": {"enabled": True, "max_tracked_events": 0}}
        stream = EventStream(tmp_path, config=config)
        stream.emit("metric", name="should_not_appear")
        # Critical events still bypass
        stream.emit("annotation", name="but_this_should")
        stream.close()

        lines = (tmp_path / "events.jsonl").read_text("utf-8").strip().splitlines()
        assert len(lines) == 1
        assert json.loads(lines[0])["name"] == "but_this_should"


class TestEventStreamClose:

    def test_close_idempotent(self, tmp_path):
        config = {"events": {"enabled": True, "max_tracked_events": 100}}
        stream = EventStream(tmp_path, config=config)
        stream.emit("metric", name="test")
        stream.close()
        stream.close()  # Should not crash

    def test_emit_after_close_is_silent(self, tmp_path):
        config = {"events": {"enabled": True, "max_tracked_events": 100}}
        stream = EventStream(tmp_path, config=config)
        stream.close()
        stream.emit("metric", name="orphan")  # Should not crash


class TestEventStreamFormat:

    def test_event_has_timestamp(self, tmp_path):
        config = {"events": {"enabled": True, "max_tracked_events": 100}}
        stream = EventStream(tmp_path, config=config)
        stream.emit("annotation", name="checkpoint")
        stream.close()

        lines = (tmp_path / "events.jsonl").read_text("utf-8").strip().splitlines()
        record = json.loads(lines[0])
        assert "timestamp_utc" in record
        assert isinstance(record["timestamp_utc"], float)

    def test_event_payload_optional(self, tmp_path):
        config = {"events": {"enabled": True, "max_tracked_events": 100}}
        stream = EventStream(tmp_path, config=config)
        stream.emit("annotation", name="no_payload")
        stream.close()

        lines = (tmp_path / "events.jsonl").read_text("utf-8").strip().splitlines()
        record = json.loads(lines[0])
        assert "payload" not in record


class TestEventStreamConstructorFailure:
    """Tests for EventStream when file creation fails."""

    def test_open_failure_sets_file_to_none(self, tmp_path, monkeypatch):
        """If open() fails during construction, _file is None."""
        import builtins
        original_open = builtins.open

        def failing_open(path, *args, **kwargs):
            if "events.jsonl" in str(path):
                raise PermissionError("read-only filesystem")
            return original_open(path, *args, **kwargs)

        monkeypatch.setattr(builtins, "open", failing_open)

        config = {"events": {"enabled": True, "max_tracked_events": 100}}
        stream = EventStream(tmp_path, config=config)
        assert stream._file is None

    def test_emit_after_open_failure_is_silent(self, tmp_path, monkeypatch):
        """emit() does not raise when _file is None (failed open)."""
        import builtins
        original_open = builtins.open

        def failing_open(path, *args, **kwargs):
            if "events.jsonl" in str(path):
                raise PermissionError("read-only filesystem")
            return original_open(path, *args, **kwargs)

        monkeypatch.setattr(builtins, "open", failing_open)

        config = {"events": {"enabled": True, "max_tracked_events": 100}}
        stream = EventStream(tmp_path, config=config)
        # Should not raise
        stream.emit("annotation", name="lost_event", payload={"key": "value"})
        stream.close()  # Also should not raise
