import json
import os
import platform
import sys
from pathlib import Path

import pubrun.capture.hardware as hw_mod
from pubrun import start
from pubrun.capture.hardware import (
    _get_cpu_model,
    _get_gpus,
    _get_total_memory_bytes,
    get_hardware,
)


def test_hardware_poller_does_not_crash():
    # If this runs on a CI machine, we don't know what it will output,
    # but we can assert it returns strongly typed dicts and doesn't crash.
    config = {
        "capture": {
            "hardware": {"depth": "basic", "capture_gpu_clock_speed": False}
        }
    }

    hw = get_hardware(config)

    assert "cpu" in hw
    assert "gpus" in hw
    assert "capture_state" in hw
    assert hw["capture_state"]["status"] in {"complete", "partial", "timeout"}

    # Check CPU and GPU shapes
    assert hw["cpu"]["architecture"] == platform.machine()
    assert hw["cpu"]["logical_cores"] is None or isinstance(hw["cpu"]["logical_cores"], int)
    assert isinstance(hw["gpus"], list)


def test_tracker_hardware_integration(tmp_path, monkeypatch):
    monkeypatch.setattr("pathlib.Path.cwd", lambda: tmp_path)

    tracker = start()
    tracker.stop()

    # Verify manifest
    manifest_path = tracker.run_dir / "manifest.json"
    assert manifest_path.exists()

    with open(manifest_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    hw = data.get("hardware")
    assert hw is not None
    assert "cpu" in hw
    assert "gpus" in hw
    assert hw["capture_state"]["status"] == "complete"


def test_get_gpus_nvidia_with_clock_speed(monkeypatch):
    captured = {}

    def fake_check_output(cmd, **kwargs):
        captured["cmd"] = list(cmd)
        return "A100, 81920, 535.1, 1410\nT4, [N/A], 535.1, [N/A]\n"

    monkeypatch.setattr(hw_mod.sys, "platform", "linux")
    monkeypatch.setattr(hw_mod.subprocess, "check_output", fake_check_output)

    gpus = _get_gpus({"capture_gpu_clock_speed": True}, 1.0)

    assert captured["cmd"][1].endswith(",clocks.max.sm")
    assert len(gpus) == 2
    assert gpus[0] == {
        "vendor": "NVIDIA",
        "model": "A100",
        "memory_total_bytes": 81920 * 1024 * 1024,
        "driver_version": "535.1",
        "clock_speed_mhz": 1410,
    }
    assert gpus[1] == {
        "vendor": "NVIDIA",
        "model": "T4",
        "memory_total_bytes": None,
        "driver_version": "535.1",
    }
    assert gpus[1]["memory_total_bytes"] is None
    assert "clock_speed_mhz" not in gpus[1]


def test_get_gpus_nvidia_default_query_ignores_blank_lines(monkeypatch):
    captured = {}

    def fake_check_output(cmd, **kwargs):
        captured["cmd"] = list(cmd)
        return "\nRTX 4090, 24576, 550.0\n   \n"

    monkeypatch.setattr(hw_mod.sys, "platform", "linux")
    monkeypatch.setattr(hw_mod.subprocess, "check_output", fake_check_output)

    gpus = _get_gpus({}, 1.0)

    assert captured["cmd"][1] == "--query-gpu=name,memory.total,driver_version"
    assert gpus == [
        {
            "vendor": "NVIDIA",
            "model": "RTX 4090",
            "memory_total_bytes": 24576 * 1024 * 1024,
            "driver_version": "550.0",
        }
    ]
    assert "clock_speed_mhz" not in gpus[0]


def test_windows_wmic_cpu_model_and_total_memory(monkeypatch):
    def fake_check_output(cmd, **kwargs):
        if cmd[:2] == ["wmic", "cpu"]:
            return "Name\nIntel Xeon\n"
        if cmd[:2] == ["wmic", "OS"]:
            return "TotalVisibleMemorySize\n16384\n"
        raise AssertionError("Unexpected command: %r" % (cmd,))

    monkeypatch.setattr(hw_mod.sys, "platform", "win32")
    monkeypatch.setattr(hw_mod.subprocess, "check_output", fake_check_output)

    assert _get_cpu_model(1.0) == "Intel Xeon"
    assert _get_total_memory_bytes(1.0) == 16384 * 1024


def test_get_hardware_depth_off_suppressed_without_subprocesses(monkeypatch):
    def fail_check_output(cmd, **kwargs):
        raise AssertionError("check_output must not run when depth is off")

    monkeypatch.setattr(hw_mod.sys, "platform", "linux")
    monkeypatch.setattr(hw_mod.subprocess, "check_output", fail_check_output)

    result = get_hardware({"capture": {"hardware": {"depth": "off"}}})
    assert result == {
        "capture_state": {"status": "suppressed", "detail": "Hardware depth set to off."}
    }


def test_get_hardware_unexpected_error_returns_failed_state(monkeypatch):
    def fail_machine():
        raise RuntimeError("boom")

    def fail_check_output(cmd, **kwargs):
        raise AssertionError("check_output should not be reached after platform.machine fails")

    monkeypatch.setattr(hw_mod.sys, "platform", "linux")
    monkeypatch.setattr(hw_mod.subprocess, "check_output", fail_check_output)
    monkeypatch.setattr(hw_mod.platform, "machine", fail_machine)

    assert get_hardware({}) == {
        "capture_state": {"status": "failed", "detail": "boom"}
    }
