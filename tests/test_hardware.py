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
    monkeypatch.setattr(hw_mod, "_get_windows_cpu_model_native", lambda: None)
    monkeypatch.setattr(hw_mod, "_get_windows_memory_bytes_native", lambda: None)
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


def test_windows_native_hardware_capture_without_wmic(monkeypatch):
    import ctypes
    from types import SimpleNamespace

    def no_wmic(cmd, **kwargs):
        raise FileNotFoundError("wmic removed in Windows 11 24H2")

    # Fake GlobalMemoryStatusEx
    observed_dw_length = []

    class FakeKernel32:
        def GlobalMemoryStatusEx(self, status_ptr):
            observed_dw_length.append(status_ptr._obj.dwLength)
            status_ptr._obj.ullTotalPhys = 32 * 1024 ** 3
            return 1

    # Fake winreg providing CPU ProcessorNameString and display adapter class keys
    class FakeKey:
        def __init__(self, path):
            self.path = path

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

    class_path = r"SYSTEM\CurrentControlSet\Control\Class\{4d36e968-e325-11ce-bfc1-08002be10318}"
    subkeys = ["0000", "0001", "Properties"]
    reg_values = {
        (r"HARDWARE\DESCRIPTION\System\CentralProcessor\0", "ProcessorNameString"): (
            "AMD Ryzen 9 7950X   ",
            1,
        ),
        (class_path + r"\0000", "DriverDesc"): ("AMD Radeon RX 7900 XTX", 1),
        (class_path + r"\0000", "DriverVersion"): ("31.0.24002.92", 1),
        (class_path + r"\0000", "HardwareInformation.qwMemorySize"): (24 * 1024 ** 3, 11),
        (class_path + r"\0001", "DriverDesc"): ("Intel UHD Graphics 770", 1),
        (class_path + r"\0001", "HardwareInformation.MemorySize"): (
            (128 * 1024 ** 2).to_bytes(4, "little"),
            3,
        ),
    }

    fake_winreg = SimpleNamespace(
        HKEY_LOCAL_MACHINE=object(),
        OpenKey=lambda root, sub: FakeKey(
            sub if root is fake_winreg.HKEY_LOCAL_MACHINE else f"{root.path}\\{sub}"
        ),
        EnumKey=lambda key, idx: (
            subkeys[idx] if idx < len(subkeys) else (_ for _ in ()).throw(OSError("no more"))
        ),
        QueryValueEx=lambda key, name: (
            reg_values[(key.path, name)]
            if (key.path, name) in reg_values
            else (_ for _ in ()).throw(OSError("not found"))
        ),
    )

    monkeypatch.setattr(hw_mod.sys, "platform", "win32")
    monkeypatch.setattr(hw_mod.subprocess, "check_output", no_wmic)
    monkeypatch.setattr(ctypes, "windll", SimpleNamespace(kernel32=FakeKernel32()), raising=False)
    monkeypatch.setitem(sys.modules, "winreg", fake_winreg)

    assert _get_cpu_model(1.0) == "AMD Ryzen 9 7950X"
    assert _get_total_memory_bytes(1.0) == 32 * 1024 ** 3
    assert observed_dw_length and observed_dw_length[0] > 0

    gpus = _get_gpus({}, 1.0)
    assert gpus == [
        {
            "vendor": "Generic",
            "model": "AMD Radeon RX 7900 XTX",
            "memory_total_bytes": 24 * 1024 ** 3,
            "driver_version": "31.0.24002.92",
        },
        {
            "vendor": "Generic",
            "model": "Intel UHD Graphics 770",
            "memory_total_bytes": 128 * 1024 ** 2,
            "driver_version": None,
        },
    ]


def test_windows_cpu_fallback_order_and_enum_display_devices(monkeypatch):
    import ctypes
    from types import SimpleNamespace

    # 1. When winreg and wmic both fail, platform.processor() is used as final fallback.
    monkeypatch.setattr(hw_mod.sys, "platform", "win32")
    monkeypatch.setattr(hw_mod, "_get_windows_cpu_model_native", lambda: None)
    monkeypatch.setattr(
        hw_mod.subprocess,
        "check_output",
        lambda cmd, **kw: (_ for _ in ()).throw(FileNotFoundError("wmic")),
    )
    monkeypatch.setattr(hw_mod.platform, "processor", lambda: "Intel64 Family 6 Model 151")
    assert _get_cpu_model(1.0) == "Intel64 Family 6 Model 151"

    # 2. EnumDisplayDevicesW fallback skips mirroring driver and deduplicates same adapter.
    devices = [
        ("Microsoft Basic Display Driver", 0x00000008, "PCI\\MIRROR"),  # MIRRORING_DRIVER
        ("Intel Iris Xe Graphics", 0x00000001, "PCI\\VEN_8086&DEV_9A49"),
        ("Intel Iris Xe Graphics", 0x00000000, "PCI\\VEN_8086&DEV_9A49"),  # second monitor
        ("AMD Radeon Pro W6800", 0x00000001, "PCI\\VEN_1002&DEV_73A3"),
    ]

    class FakeUser32:
        def EnumDisplayDevicesW(self, dev_name, dev_num, dd_ptr, flags):
            if dev_num >= len(devices):
                return 0
            desc, state, dev_id = devices[dev_num]
            dd_ptr._obj.DeviceString = desc
            dd_ptr._obj.StateFlags = state
            dd_ptr._obj.DeviceID = dev_id
            return 1

    # Make winreg fail so EnumDisplayDevicesW path executes
    bad_winreg = SimpleNamespace(
        HKEY_LOCAL_MACHINE=object(),
        OpenKey=lambda *a, **k: (_ for _ in ()).throw(OSError("access denied")),
    )
    monkeypatch.setitem(sys.modules, "winreg", bad_winreg)
    monkeypatch.setattr(ctypes, "windll", SimpleNamespace(user32=FakeUser32()), raising=False)

    gpus = hw_mod._get_windows_gpus_native()
    assert gpus == [
        {
            "vendor": "Generic",
            "model": "Intel Iris Xe Graphics",
            "memory_total_bytes": None,
            "driver_version": None,
        },
        {
            "vendor": "Generic",
            "model": "AMD Radeon Pro W6800",
            "memory_total_bytes": None,
            "driver_version": None,
        },
    ]


def test_linux_arm64_cpu_fallbacks(monkeypatch):
    import io

    monkeypatch.setattr(hw_mod.sys, "platform", "linux")
    real_open = open
    real_exists = os.path.exists

    # Case 1: /proc/cpuinfo with Hardware key (no model name)
    files = {"/proc/cpuinfo": "processor\t: 0\nHardware\t: BCM2835\n"}
    monkeypatch.setattr(
        os.path, "exists", lambda p: True if p in files else (False if p.startswith("/proc/") else real_exists(p))
    )
    monkeypatch.setattr(
        "builtins.open",
        lambda p, *a, **k: io.StringIO(files[p]) if p in files else real_open(p, *a, **k),
    )
    assert _get_cpu_model(1.0) == "BCM2835"

    # Case 2: /proc/cpuinfo with Model key only
    files.clear()
    files["/proc/cpuinfo"] = "processor\t: 0\nModel\t\t: Raspberry Pi 5 Model B Rev 1.0\n"
    assert _get_cpu_model(1.0) == "Raspberry Pi 5 Model B Rev 1.0"

    # Case 3: /proc/device-tree/model with trailing NUL bytes
    files.clear()
    files["/proc/cpuinfo"] = "processor\t: 0\nCPU implementer\t: 0x41\n"
    files["/proc/device-tree/model"] = "NVIDIA Jetson AGX Orin\x00\n"
    assert _get_cpu_model(1.0) == "NVIDIA Jetson AGX Orin"

    # Case 4: lscpu fallback with LC_ALL=C and ignoring "-"
    files.clear()
    files["/proc/cpuinfo"] = "processor\t: 0\nCPU implementer\t: 0x41\n"
    seen_env = {}

    def fake_lscpu(cmd, **kwargs):
        assert cmd == ["lscpu"]
        seen_env.update(kwargs.get("env") or {})
        return "Architecture: aarch64\nModel name:   Neoverse-N1\n"

    monkeypatch.setattr(hw_mod.subprocess, "check_output", fake_lscpu)
    assert _get_cpu_model(1.0) == "Neoverse-N1"
    assert seen_env.get("LC_ALL") == "C"

    monkeypatch.setattr(
        hw_mod.subprocess, "check_output", lambda cmd, **kw: "Model name: -\n"
    )
    assert _get_cpu_model(1.0) is None


def test_linux_amd_rocm_gpu_fallbacks_validate_against_schema(monkeypatch):
    import pytest

    jsonschema = pytest.importorskip("jsonschema")
    schema_path = Path(__file__).resolve().parents[1] / "schemas" / "manifest.schema.json"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    gpu_schema = dict(schema["$defs"]["gpu_record"])
    gpu_schema["$defs"] = schema["$defs"]

    monkeypatch.setattr(hw_mod.sys, "platform", "linux")

    # 1. amd-smi static --json succeeds
    amd_smi_payload = json.dumps(
        {
            "gpu_data": [
                {
                    "gpu": 0,
                    "asic": {"market_name": "AMD Instinct MI250X"},
                    "vram": {"size": {"value": 65536, "unit": "MB"}},
                    "driver": {"version": "6.3.6"},
                }
            ]
        }
    )

    def fake_amd_smi(cmd, **kwargs):
        if cmd[0] == "nvidia-smi":
            raise FileNotFoundError("nvidia-smi")
        if cmd[:3] == ["amd-smi", "static", "--json"]:
            return amd_smi_payload
        raise AssertionError(f"Unexpected cmd: {cmd}")

    monkeypatch.setattr(hw_mod.subprocess, "check_output", fake_amd_smi)
    gpus = _get_gpus({}, 1.0)
    assert gpus == [
        {
            "vendor": "AMD",
            "model": "AMD Instinct MI250X",
            "memory_total_bytes": 65536 * 1024 ** 2,
            "driver_version": "6.3.6",
        }
    ]
    for rec in gpus:
        jsonschema.validate(rec, gpu_schema)

    # 2. amd-smi absent -> falls back to rocm-smi --json
    rocm_smi_payload = json.dumps(
        {
            "card0": {
                "Card Series": "AMD Instinct MI300X",
                "VRAM Total Memory (B)": "206158430208",
            },
            "system": {"Driver version": "6.7.0"},
        }
    )

    def fake_rocm_smi(cmd, **kwargs):
        if cmd[0] in ("nvidia-smi", "amd-smi"):
            raise FileNotFoundError(cmd[0])
        if cmd[0] == "rocm-smi":
            return rocm_smi_payload
        raise AssertionError(f"Unexpected cmd: {cmd}")

    monkeypatch.setattr(hw_mod.subprocess, "check_output", fake_rocm_smi)
    gpus_rocm = _get_gpus({}, 1.0)
    assert gpus_rocm == [
        {
            "vendor": "AMD",
            "model": "AMD Instinct MI300X",
            "memory_total_bytes": 206158430208,
            "driver_version": "6.7.0",
        }
    ]
    for rec in gpus_rocm:
        jsonschema.validate(rec, gpu_schema)


def test_parse_vram_bytes_binary_units_and_invalid():
    assert hw_mod._parse_vram_bytes("4 GB") == 4 * 1024 ** 3
    assert hw_mod._parse_vram_bytes("1.5 GB") == int(round(1.5 * 1024 ** 3))
    assert hw_mod._parse_vram_bytes("4096 MB") == 4096 * 1024 ** 2
    assert hw_mod._parse_vram_bytes("512 MiB") == 512 * 1024 ** 2
    assert hw_mod._parse_vram_bytes("256 KB") == 256 * 1024
    assert hw_mod._parse_vram_bytes("1 TB") == 1024 ** 4
    assert hw_mod._parse_vram_bytes("1024 B") == 1024
    assert hw_mod._parse_vram_bytes("unknown") is None
    assert hw_mod._parse_vram_bytes("") is None
    assert hw_mod._parse_vram_bytes("12345") is None
    assert hw_mod._parse_vram_bytes("-4 GB") is None
