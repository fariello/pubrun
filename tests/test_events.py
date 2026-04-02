import json
import logging
from pathlib import Path

from runtrace import start, annotate, phase
import runtrace

def test_event_stream_creates_jsonl(tmp_path, monkeypatch):
    monkeypatch.setattr("pathlib.Path.cwd", lambda: tmp_path)
    
    t = start(**{
        "events": {"enabled": True},
        "capture": {"resources": {"depth": "off"}}
    })
    
    # 1
    annotate("Training started", epoch=1)
    
    # 2, 3, 4
    with phase("Data Prep"):
        annotate(records_processed=50, msg="halfway")
        
    # 5, 6
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
    
    ev2 = json.loads(lines[2])
    assert ev2["type"] == "annotation"
    assert ev2["payload"]["records_processed"] == 50
    assert ev2["payload"]["msg"] == "halfway"
    
    ev3 = json.loads(lines[3])
    assert ev3["type"] == "phase_end"
    assert ev3["name"] == "Data Prep"
    
    ev4 = json.loads(lines[4])
    assert ev4["type"] == "phase_start"
    assert ev4["name"] == "Failing Phase"
    
    ev5 = json.loads(lines[5])
    assert ev5["type"] == "phase_end"
    assert ev5["name"] == "Failing Phase"
    assert ev5["payload"]["error"] == "ValueError"

def test_inactive_event_stream_warns(caplog):
    caplog.set_level(logging.WARNING, logger="runtrace")
    
    import runtrace.config
    
    # Should not crash
    annotate("Should be silently ignored because default is ignore")
    assert "Annotation dropped" not in caplog.text
