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

        # Critical events should still be accepted
        stream.emit("annotation", name="important")
        stream.emit("phase_started", name="critical_phase")
        stream.close()

        lines = (tmp_path / "events.jsonl").read_text("utf-8").strip().splitlines()
        # 3 regular + 2 critical = 5
        assert len(lines) == 5

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
