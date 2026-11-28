import contextlib
import json
import logging
import math
import os
import platform
import re
import subprocess
import sys
import time
from typing import Any, Dict, List, Optional

logger = logging.getLogger("pubrun")

_SYS_MODULES = sys.modules


def _disable_spy_if_loaded() -> Any:
    """Return ``disable_spy()`` when ``pubrun.capture.subprocesses`` is loaded, else a no-op context."""
    modules = getattr(sys, "modules", _SYS_MODULES)
    spy_mod = modules.get("pubrun.capture.subprocesses") if modules is not None else None
    disable = getattr(spy_mod, "disable_spy", None)
    if callable(disable):
        return disable()
    return contextlib.nullcontext()

# Default per-command timeout (seconds) for hardware-inspection subprocesses if
# no config value is available. Overridable via [capture.hardware].timeout.
_DEFAULT_HW_TIMEOUT = 10.0

_VRAM_RE = re.compile(r"^\s*(\d+(?:\.\d+)?)\s*([A-Za-z]+)\s*$")
_VRAM_BINARY_MULTIPLIERS: Dict[str, int] = {
    "b": 1,
    "byte": 1,
    "bytes": 1,
    "kb": 1024,
    "kib": 1024,
    "mb": 1024 ** 2,
    "mib": 1024 ** 2,
    "gb": 1024 ** 3,
    "gib": 1024 ** 3,
    "tb": 1024 ** 4,
    "tib": 1024 ** 4,
}


def _parse_vram_bytes(text: str) -> Optional[int]:
    """Parse a binary (1024-based) VRAM size string such as '4 GB' or '1.5 GB'."""
    if not isinstance(text, str):
        return None
    match = _VRAM_RE.match(text)
    if match is None:
        return None
    num_str, unit_str = match.group(1), match.group(2).lower()
    mult = _VRAM_BINARY_MULTIPLIERS.get(unit_str)
    if mult is None:
        return None
    try:
        val = float(num_str)
    except ValueError:
        return None
    if not math.isfinite(val) or val < 0:
        return None
    return int(round(val * mult))


def _get_windows_memory_bytes_native() -> Optional[int]:
    """Query total physical RAM on Windows via ctypes GlobalMemoryStatusEx."""
    if sys.platform != "win32":
        return None
    try:
        import ctypes
        import ctypes.wintypes

        class _MEMORYSTATUSEX(ctypes.Structure):
            _fields_ = [
                ("dwLength", ctypes.wintypes.DWORD),
                ("dwMemoryLoad", ctypes.wintypes.DWORD),
                ("ullTotalPhys", ctypes.c_uint64),
                ("ullAvailPhys", ctypes.c_uint64),
                ("ullTotalPageFile", ctypes.c_uint64),
                ("ullAvailPageFile", ctypes.c_uint64),
                ("ullTotalVirtual", ctypes.c_uint64),
                ("ullAvailVirtual", ctypes.c_uint64),
                ("ullAvailExtendedVirtual", ctypes.c_uint64),
            ]

        windll_obj = getattr(ctypes, "windll", None)
        kernel32 = getattr(windll_obj, "kernel32", None)
        if kernel32 is None:
            return None
        win_dll_cls = getattr(ctypes, "WinDLL", None)
        if win_dll_cls is not None and isinstance(kernel32, win_dll_cls):
            kernel32 = win_dll_cls("kernel32", use_last_error=True)
            kernel32.GlobalMemoryStatusEx.argtypes = [ctypes.POINTER(_MEMORYSTATUSEX)]
            kernel32.GlobalMemoryStatusEx.restype = ctypes.wintypes.BOOL
        status = _MEMORYSTATUSEX()
        status.dwLength = ctypes.sizeof(status)
        if kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
            total = int(status.ullTotalPhys)
            if total > 0:
                return total
    except Exception as e:
        logger.debug("pubrun Windows GlobalMemoryStatusEx failed: %s", e)
    return None


def _get_windows_cpu_model_native() -> Optional[str]:
    """Query CPU model on Windows from the registry without spawning wmic."""
    if sys.platform != "win32":
        return None
    try:
        import winreg

        with winreg.OpenKey(
            winreg.HKEY_LOCAL_MACHINE,
            r"HARDWARE\DESCRIPTION\System\CentralProcessor\0",
        ) as key:
            val, _ = winreg.QueryValueEx(key, "ProcessorNameString")
            if isinstance(val, str):
                cleaned = val.strip()
                if cleaned:
                    return cleaned
    except Exception as e:
        logger.debug("pubrun Windows winreg CPU lookup failed: %s", e)
    return None


def _parse_windows_reg_vram(raw: Any) -> Optional[int]:
    """Decode Windows HardwareInformation.qwMemorySize or MemorySize registry values."""
    if isinstance(raw, bool):
        return None
    if isinstance(raw, int):
        if raw < 0:
            return raw & 0xFFFFFFFF
        return raw if raw > 0 else None
    if isinstance(raw, (bytes, bytearray)) and raw:
        val = int.from_bytes(raw, "little", signed=False)
        return val if val > 0 else None
    return None


def _get_windows_gpus_native() -> List[Dict[str, Any]]:
    """Query Windows display adapters via winreg, falling back to EnumDisplayDevicesW."""
    if sys.platform != "win32":
        return []

    gpus: List[Dict[str, Any]] = []
    # 1. Registry display-adapter class key (provides model, driver version, and 64-bit VRAM).
    try:
        import winreg

        class_path = r"SYSTEM\CurrentControlSet\Control\Class\{4d36e968-e325-11ce-bfc1-08002be10318}"
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, class_path) as class_key:
            for idx in range(256):
                try:
                    subkey_name = winreg.EnumKey(class_key, idx)
                except OSError:
                    break
                if not subkey_name.isdigit():
                    continue
                try:
                    with winreg.OpenKey(class_key, subkey_name) as dev_key:
                        try:
                            desc_val, _ = winreg.QueryValueEx(dev_key, "DriverDesc")
                        except OSError:
                            continue
                        if not isinstance(desc_val, str) or not desc_val.strip():
                            continue
                        model = desc_val.strip()

                        driver_version: Optional[str] = None
                        try:
                            ver_val, _ = winreg.QueryValueEx(dev_key, "DriverVersion")
                            if isinstance(ver_val, str) and ver_val.strip():
                                driver_version = ver_val.strip()
                        except OSError:
                            pass

                        mem_bytes: Optional[int] = None
                        for reg_val_name in (
                            "HardwareInformation.qwMemorySize",
                            "HardwareInformation.MemorySize",
                        ):
                            try:
                                raw_mem, _ = winreg.QueryValueEx(dev_key, reg_val_name)
                                parsed_mem = _parse_windows_reg_vram(raw_mem)
                                if parsed_mem is not None:
                                    mem_bytes = parsed_mem
                                    break
                            except OSError:
                                continue

                        gpus.append({
                            "vendor": "Generic",
                            "model": model,
                            "memory_total_bytes": mem_bytes,
                            "driver_version": driver_version,
                        })
                except OSError:
                    continue
    except Exception as e:
        logger.debug("pubrun Windows winreg GPU lookup failed: %s", e)

    if gpus:
        return gpus

    # 2. Fallback: user32.EnumDisplayDevicesW (skipping mirroring drivers).
    try:
        import ctypes
        import ctypes.wintypes

        DISPLAY_DEVICE_MIRRORING_DRIVER = 0x00000008

        class _DISPLAY_DEVICEW(ctypes.Structure):
            _fields_ = [
                ("cb", ctypes.wintypes.DWORD),
                ("DeviceName", ctypes.c_wchar * 32),
                ("DeviceString", ctypes.c_wchar * 128),
                ("StateFlags", ctypes.wintypes.DWORD),
                ("DeviceID", ctypes.c_wchar * 128),
                ("DeviceKey", ctypes.c_wchar * 128),
            ]

        windll_obj = getattr(ctypes, "windll", None)
        user32 = getattr(windll_obj, "user32", None)
        if user32 is None:
            return []
        win_dll_cls = getattr(ctypes, "WinDLL", None)
        if win_dll_cls is not None and isinstance(user32, win_dll_cls):
            user32 = win_dll_cls("user32", use_last_error=True)
            user32.EnumDisplayDevicesW.argtypes = [
                ctypes.c_wchar_p,
                ctypes.wintypes.DWORD,
                ctypes.POINTER(_DISPLAY_DEVICEW),
                ctypes.wintypes.DWORD,
            ]
            user32.EnumDisplayDevicesW.restype = ctypes.wintypes.BOOL

        seen: set = set()
        for dev_idx in range(256):
            dd = _DISPLAY_DEVICEW()
            dd.cb = ctypes.sizeof(dd)
            if not user32.EnumDisplayDevicesW(None, dev_idx, ctypes.byref(dd), 0):
                break
            if dd.StateFlags & DISPLAY_DEVICE_MIRRORING_DRIVER:
                continue
            model = (dd.DeviceString or "").strip()
            if not model:
                continue
            dedup_key = ((dd.DeviceID or "").strip(), model)
            if dedup_key in seen:
                continue
            seen.add(dedup_key)
            gpus.append({
                "vendor": "Generic",
                "model": model,
                "memory_total_bytes": None,
                "driver_version": None,
            })
    except Exception as e:
        logger.debug("pubrun Windows EnumDisplayDevicesW GPU lookup failed: %s", e)

    return gpus


def _clean_gpu_str(val: Any) -> Optional[str]:
    if not isinstance(val, str):
        return None
    cleaned = val.strip()
    if not cleaned or cleaned.upper() in {"N/A", "[N/A]", "NONE", "UNKNOWN"}:
        return None
    return cleaned


def _parse_amd_smi_json(raw_json: str) -> List[Dict[str, Any]]:
    """Parse `amd-smi static --json` output into schema-valid GPU records."""
    parsed = json.loads(raw_json)
    if isinstance(parsed, dict):
        items = parsed.get("gpu_data")
        if not isinstance(items, list):
            items = [parsed] if ("asic" in parsed or "vram" in parsed) else []
    elif isinstance(parsed, list):
        items = parsed
    else:
        return []

    gpus: List[Dict[str, Any]] = []
    for entry in items:
        if not isinstance(entry, dict):
            continue
        raw_asic = entry.get("asic")
        asic: Dict[str, Any] = raw_asic if isinstance(raw_asic, dict) else {}
        raw_board = entry.get("board")
        board: Dict[str, Any] = raw_board if isinstance(raw_board, dict) else {}
        raw_vram = entry.get("vram")
        vram: Dict[str, Any] = raw_vram if isinstance(raw_vram, dict) else {}
        driver = entry.get("driver")

        model = (
            _clean_gpu_str(asic.get("market_name"))
            or _clean_gpu_str(board.get("product_name"))
            or _clean_gpu_str(asic.get("name"))
            or _clean_gpu_str(entry.get("market_name"))
            or _clean_gpu_str(entry.get("model"))
        )

        mem_bytes: Optional[int] = None
        vram_size = vram.get("size") if vram else entry.get("vram_size")
        if isinstance(vram_size, dict):
            val = vram_size.get("value")
            unit = vram_size.get("unit")
            if val is not None and isinstance(unit, str):
                mem_bytes = _parse_vram_bytes(f"{val} {unit}")
            elif isinstance(val, int) and not isinstance(val, bool) and val >= 0:
                mem_bytes = val
        elif isinstance(vram_size, str):
            mem_bytes = _parse_vram_bytes(vram_size)
        elif isinstance(vram_size, int) and not isinstance(vram_size, bool) and vram_size >= 0:
            mem_bytes = vram_size * 1024 * 1024

        driver_version: Optional[str] = None
        if isinstance(driver, dict):
            driver_version = _clean_gpu_str(driver.get("version"))
        else:
            driver_version = _clean_gpu_str(driver) or _clean_gpu_str(
                entry.get("driver_version")
            )

        if model is None and mem_bytes is None:
            continue
        gpus.append({
            "vendor": "AMD",
            "model": model,
            "memory_total_bytes": mem_bytes,
            "driver_version": driver_version,
        })
    return gpus


def _parse_rocm_smi_json(raw_json: str) -> List[Dict[str, Any]]:
    """Parse `rocm-smi --showproductname --showmeminfo vram --showdriverversion --json`."""
    parsed = json.loads(raw_json)
    if not isinstance(parsed, dict):
        return []

    sys_section = parsed.get("system")
    sys_driver: Optional[str] = None
    if isinstance(sys_section, dict):
        sys_driver = (
            _clean_gpu_str(sys_section.get("Driver version"))
            or _clean_gpu_str(sys_section.get("Driver Version"))
        )

    gpus: List[Dict[str, Any]] = []
    for key, entry in parsed.items():
        if key == "system" or not isinstance(entry, dict):
            continue
        model = (
            _clean_gpu_str(entry.get("Card Series"))
            or _clean_gpu_str(entry.get("Card series"))
            or _clean_gpu_str(entry.get("Market Name"))
            or _clean_gpu_str(entry.get("Product Name"))
            or _clean_gpu_str(entry.get("Card Model"))
            or _clean_gpu_str(entry.get("Card model"))
        )

        mem_bytes: Optional[int] = None
        raw_vram_b = entry.get("VRAM Total Memory (B)")
        if raw_vram_b is not None:
            try:
                v_int = int(str(raw_vram_b).strip())
                if v_int >= 0:
                    mem_bytes = v_int
            except (TypeError, ValueError):
                mem_bytes = _parse_vram_bytes(str(raw_vram_b))
        else:
            for k_mem, v_mem in entry.items():
                if isinstance(k_mem, str) and "vram total memory" in k_mem.lower():
                    mem_bytes = _parse_vram_bytes(str(v_mem))
                    if mem_bytes is not None:
                        break

        driver_version = (
            _clean_gpu_str(entry.get("Driver version"))
            or _clean_gpu_str(entry.get("Driver Version"))
            or sys_driver
        )

        if model is None and mem_bytes is None:
            continue
        gpus.append({
            "vendor": "AMD",
            "model": model,
            "memory_total_bytes": mem_bytes,
            "driver_version": driver_version,
        })
    return gpus


def _parse_positive_timeout(value: Any, default: float) -> float:
    """Return a finite positive timeout in seconds, or ``default`` when invalid."""
    if isinstance(value, bool) or value is None:
        return default
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return default
    if not math.isfinite(parsed) or parsed <= 0:
        return default
    return parsed


def _parse_nonnegative_timeout(value: Any, default: float) -> float:
    """Return a finite nonnegative timeout in seconds, or ``default`` when invalid."""
    if isinstance(value, bool) or value is None:
        return default
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return default
    if not math.isfinite(parsed) or parsed < 0:
        return default
    return parsed


class _CaptureBudget:
    """Monotonic wall-clock budget shared across hardware subprocess probes."""

    def __init__(self, total_timeout: float, per_cmd_timeout: float) -> None:
        self.total_timeout = total_timeout
        self.per_cmd_timeout = per_cmd_timeout
        self.deadline = time.monotonic() + total_timeout
        self.timed_out = False
        self.exhausted = False

    def next_timeout(self) -> Optional[float]:
        """Return timeout for the next subprocess probe, or None if budget expired."""
        remaining = self.deadline - time.monotonic()
        if remaining <= 0:
            self.exhausted = True
            return None
        return min(self.per_cmd_timeout, remaining)

    def mark_timeout(self) -> None:
        """Record that a subprocess probe raised ``subprocess.TimeoutExpired``."""
        self.timed_out = True
        if self.deadline - time.monotonic() <= 0:
            self.exhausted = True


def _get_cpu_model(
    timeout: float = _DEFAULT_HW_TIMEOUT,
    *,
    budget: Optional[_CaptureBudget] = None,
) -> Optional[str]:
    try:
        sys_plat = sys.platform
        if sys_plat == "win32":
            native_model = _get_windows_cpu_model_native()
            if native_model:
                return native_model
            cmd_timeout = budget.next_timeout() if budget is not None else timeout
            if cmd_timeout is not None:
                try:
                    with _disable_spy_if_loaded():
                        out = subprocess.check_output(
                            ["wmic", "cpu", "get", "Name"],
                            text=True,
                            stderr=subprocess.DEVNULL,
                            timeout=cmd_timeout,
                        )
                    lines = [line.strip() for line in out.splitlines() if line.strip()]
                    if len(lines) >= 2:
                        return lines[1]
                except subprocess.TimeoutExpired as e:
                    if budget is not None:
                        budget.mark_timeout()
                    logger.debug("pubrun timed out fetching CPU model: %s", e)
                    return None
                except Exception as e:
                    logger.debug("pubrun legacy wmic CPU fallback failed: %s", e)
            else:
                return None
            proc = platform.processor().strip()
            return proc or None
        elif sys_plat == "darwin":
            cmd_timeout = budget.next_timeout() if budget is not None else timeout
            if cmd_timeout is None:
                return None
            with _disable_spy_if_loaded():
                out = subprocess.check_output(
                    ["sysctl", "-n", "machdep.cpu.brand_string"],
                    text=True,
                    stderr=subprocess.DEVNULL,
                    timeout=cmd_timeout,
                )
            return out.strip() or None
        elif sys_plat.startswith("linux"):
            cpuinfo_hardware: Optional[str] = None
            cpuinfo_model: Optional[str] = None
            if os.path.exists("/proc/cpuinfo"):
                with open("/proc/cpuinfo", "r", encoding="utf-8", errors="replace") as f:
                    for line in f:
                        if ":" not in line:
                            continue
                        key, val = line.split(":", 1)
                        key_s = key.strip()
                        val_s = val.strip()
                        if not val_s:
                            continue
                        if key_s == "model name":
                            return val_s
                        if key_s == "Hardware" and cpuinfo_hardware is None:
                            cpuinfo_hardware = val_s
                        elif key_s == "Model" and cpuinfo_model is None:
                            cpuinfo_model = val_s
            if cpuinfo_hardware:
                return cpuinfo_hardware
            if cpuinfo_model:
                return cpuinfo_model
            if os.path.exists("/proc/device-tree/model"):
                try:
                    with open(
                        "/proc/device-tree/model", "r", encoding="utf-8", errors="replace"
                    ) as f:
                        dt_model = f.read().replace("\x00", "").strip()
                    if dt_model:
                        return dt_model
                except Exception as e:
                    logger.debug("pubrun failed reading /proc/device-tree/model: %s", e)
            cmd_timeout = budget.next_timeout() if budget is not None else timeout
            if cmd_timeout is None:
                return None
            with _disable_spy_if_loaded():
                out = subprocess.check_output(
                    ["lscpu"],
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    env={**os.environ, "LC_ALL": "C"},
                    stderr=subprocess.DEVNULL,
                    timeout=cmd_timeout,
                )
            for line in out.splitlines():
                if line.startswith("Model name:"):
                    val_s = line.split(":", 1)[1].strip()
                    if val_s and val_s != "-":
                        return val_s
    except subprocess.TimeoutExpired as e:
        if budget is not None:
            budget.mark_timeout()
        logger.debug("pubrun timed out fetching CPU model: %s", e)
    except Exception as e:
        logger.debug("pubrun failed to fetch CPU model: %s", e)
    return None


def _get_total_memory_bytes(
    timeout: float = _DEFAULT_HW_TIMEOUT,
    *,
    budget: Optional[_CaptureBudget] = None,
) -> Optional[int]:
    try:
        sys_plat = sys.platform
        if sys_plat == "win32":
            native_mem = _get_windows_memory_bytes_native()
            if native_mem is not None:
                return native_mem
            cmd_timeout = budget.next_timeout() if budget is not None else timeout
            if cmd_timeout is None:
                return None
            with _disable_spy_if_loaded():
                out = subprocess.check_output(
                    ["wmic", "OS", "get", "TotalVisibleMemorySize"],
                    text=True,
                    stderr=subprocess.DEVNULL,
                    timeout=cmd_timeout,
                )
            lines = [line.strip() for line in out.splitlines() if line.strip()]
            if len(lines) >= 2:
                return int(lines[1]) * 1024
        elif sys_plat == "darwin":
            cmd_timeout = budget.next_timeout() if budget is not None else timeout
            if cmd_timeout is None:
                return None
            with _disable_spy_if_loaded():
                out = subprocess.check_output(
                    ["sysctl", "-n", "hw.memsize"],
                    text=True,
                    stderr=subprocess.DEVNULL,
                    timeout=cmd_timeout,
                )
            return int(out.strip())
        elif sys_plat.startswith("linux"):
            if os.path.exists("/proc/meminfo"):
                with open("/proc/meminfo", "r", encoding="utf-8") as f:
                    for line in f:
                        if line.startswith("MemTotal:"):
                            parts = line.split()
                            if len(parts) >= 2:
                                return int(parts[1]) * 1024
    except subprocess.TimeoutExpired as e:
        if budget is not None:
            budget.mark_timeout()
        logger.debug("pubrun timed out fetching Total RAM: %s", e)
    except Exception as e:
        logger.debug("pubrun failed to fetch Total RAM: %s", e)
    return None


def _get_gpus(
    config_hw: Dict[str, Any],
    timeout: float = _DEFAULT_HW_TIMEOUT,
    *,
    budget: Optional[_CaptureBudget] = None,
) -> List[Dict[str, Any]]:
    gpus: List[Dict[str, Any]] = []

    # Attempt 1: NVIDIA SMI for CUDA GPU metadata.
    nvidia_timeout = budget.next_timeout() if budget is not None else timeout
    if nvidia_timeout is not None:
        try:
            cmd = [
                "nvidia-smi",
                "--query-gpu=name,memory.total,driver_version",
                "--format=csv,noheader,nounits",
            ]
            if config_hw.get("capture_gpu_clock_speed", False):
                cmd[1] += ",clocks.max.sm"

            with _disable_spy_if_loaded():
                out = subprocess.check_output(
                    cmd, text=True, stderr=subprocess.DEVNULL, timeout=nvidia_timeout
                )

            for line in out.splitlines():
                if not line.strip():
                    continue
                parts = [p.strip() for p in line.split(",")]
                gpu_record: Dict[str, Any] = {
                    "vendor": "NVIDIA",
                    "model": parts[0] if len(parts) > 0 else None,
                    "memory_total_bytes": (
                        int(parts[1]) * 1024 * 1024
                        if len(parts) > 1 and parts[1].isdigit()
                        else None
                    ),
                    "driver_version": parts[2] if len(parts) > 2 else None,
                }
                if len(parts) > 3 and parts[3].isdigit():
                    gpu_record["clock_speed_mhz"] = int(parts[3])

                gpus.append(gpu_record)
        except subprocess.TimeoutExpired as e:
            if budget is not None:
                budget.mark_timeout()
            logger.debug("pubrun nvidia-smi timed out: %s", e)
        except Exception as e:
            logger.debug("pubrun nvidia-smi failed or not found: %s", e)

    # Attempt 2a: Linux AMD ROCm fallbacks (amd-smi then rocm-smi).
    if not gpus and sys.platform.startswith("linux"):
        amd_timeout = budget.next_timeout() if budget is not None else timeout
        if amd_timeout is not None:
            try:
                with _disable_spy_if_loaded():
                    out = subprocess.check_output(
                        ["amd-smi", "static", "--json"],
                        text=True,
                        encoding="utf-8",
                        errors="replace",
                        stderr=subprocess.DEVNULL,
                        timeout=amd_timeout,
                    )
                gpus.extend(_parse_amd_smi_json(out))
            except subprocess.TimeoutExpired as e:
                if budget is not None:
                    budget.mark_timeout()
                logger.debug("pubrun amd-smi timed out: %s", e)
            except Exception as e:
                logger.debug("pubrun amd-smi failed or not found: %s", e)

        if not gpus:
            rocm_timeout = budget.next_timeout() if budget is not None else timeout
            if rocm_timeout is not None:
                try:
                    with _disable_spy_if_loaded():
                        out = subprocess.check_output(
                            [
                                "rocm-smi",
                                "--showproductname",
                                "--showmeminfo",
                                "vram",
                                "--showdriverversion",
                                "--json",
                            ],
                            text=True,
                            encoding="utf-8",
                            errors="replace",
                            stderr=subprocess.DEVNULL,
                            timeout=rocm_timeout,
                        )
                    gpus.extend(_parse_rocm_smi_json(out))
                except subprocess.TimeoutExpired as e:
                    if budget is not None:
                        budget.mark_timeout()
                    logger.debug("pubrun rocm-smi timed out: %s", e)
                except Exception as e:
                    logger.debug("pubrun rocm-smi failed or not found: %s", e)

    # Attempt 2b: Native Windows probes (winreg / EnumDisplayDevicesW) before legacy wmic.
    if not gpus and sys.platform == "win32":
        gpus.extend(_get_windows_gpus_native())

    # Attempt 3: Generic OS subprocess fallback on Windows (legacy wmic) / macOS (system_profiler).
    if not gpus and sys.platform in ("win32", "darwin"):
        fallback_timeout = budget.next_timeout() if budget is not None else timeout
        if fallback_timeout is not None:
            try:
                sys_plat = sys.platform
                if sys_plat == "win32":
                    with _disable_spy_if_loaded():
                        out = subprocess.check_output(
                            [
                                "wmic",
                                "path",
                                "win32_VideoController",
                                "get",
                                "Name,AdapterRAM,DriverVersion",
                                "/format:csv",
                            ],
                            text=True,
                            stderr=subprocess.DEVNULL,
                            timeout=fallback_timeout,
                        )
                    lines = [line.strip() for line in out.splitlines() if line.strip()]
                    for line in lines[1:]:
                        parts = line.split(",")
                        if len(parts) >= 4:
                            mem = None
                            try:
                                mem = int(parts[1].strip())
                            except ValueError:
                                mem = None
                            if mem is not None and mem < 0:
                                # AdapterRAM is a signed 32-bit WMI value that
                                # overflows negative for 2-4 GiB adapters.
                                mem = mem & 0xFFFFFFFF
                            gpus.append({
                                "vendor": "Generic",
                                "model": parts[3],
                                "memory_total_bytes": mem,
                                "driver_version": parts[2],
                            })
                elif sys_plat == "darwin":
                    with _disable_spy_if_loaded():
                        out = subprocess.check_output(
                            ["system_profiler", "SPDisplaysDataType"],
                            text=True,
                            stderr=subprocess.DEVNULL,
                            timeout=fallback_timeout,
                        )
                    gpu_rec: Dict[str, Any] = {"vendor": "Apple / Generic"}
                    for line in out.splitlines():
                        stripped = line.strip()
                        if stripped.startswith("Chipset Model:"):
                            # Each "Chipset Model:" starts a new GPU; keep the previous one.
                            if "model" in gpu_rec:
                                gpus.append(gpu_rec)
                                gpu_rec = {"vendor": "Apple / Generic"}
                            gpu_rec["model"] = stripped.split(":", 1)[1].strip()
                        elif stripped.startswith("VRAM (Total):"):
                            gpu_rec["memory_total_bytes"] = _parse_vram_bytes(
                                stripped.split(":", 1)[1].strip()
                            )
                    if "model" in gpu_rec:
                        gpus.append(gpu_rec)
            except subprocess.TimeoutExpired as e:
                if budget is not None:
                    budget.mark_timeout()
                logger.debug("pubrun generic GPU fallback timed out: %s", e)
            except Exception as e:
                logger.debug("pubrun generic GPU fallback failed: %s", e)

    return gpus


def get_hardware(config: Dict[str, Any]) -> Dict[str, Any]:
    """Capture hardware details: CPU model, RAM, and GPU specs within a shared budget.

    GPU detection uses nvidia-smi (NVIDIA), amd-smi/rocm-smi (Linux AMD ROCm),
    winreg/EnumDisplayDevicesW with legacy wmic fallback (Windows), or
    system_profiler (macOS). Enforces ``[capture.hardware].timeout``
    (per-command, default 10s) and ``[capture.hardware].total_timeout``
    (total monotonic budget, default equal to ``timeout``). Set
    ``depth = "off"`` to skip hardware inspection.

    Args:
        config: Resolved pubrun configuration.
    """
    hw_config_root = config.get("capture", {}).get("hardware", {})
    depth = hw_config_root.get("depth", "basic")

    if depth == "off":
        return {
            "capture_state": {"status": "suppressed", "detail": "Hardware depth set to off."}
        }

    per_cmd_timeout = _parse_positive_timeout(
        hw_config_root.get("timeout", _DEFAULT_HW_TIMEOUT), _DEFAULT_HW_TIMEOUT
    )
    total_timeout = _parse_nonnegative_timeout(
        hw_config_root.get("total_timeout"), per_cmd_timeout
    )
    budget = _CaptureBudget(total_timeout=total_timeout, per_cmd_timeout=per_cmd_timeout)

    try:
        cpu = {
            "architecture": platform.machine(),
            "logical_cores": os.cpu_count(),
            "model": _get_cpu_model(per_cmd_timeout, budget=budget),
        }

        mem_bytes = _get_total_memory_bytes(per_cmd_timeout, budget=budget)
        gpus = _get_gpus(hw_config_root, per_cmd_timeout, budget=budget)

        if budget.timed_out or budget.exhausted:
            if cpu["model"] is None and mem_bytes is None and not gpus:
                capture_state: Dict[str, Any] = {
                    "status": "timeout",
                    "detail": "hardware capture timed out",
                }
            else:
                capture_state = {
                    "status": "partial",
                    "detail": "hardware capture budget exhausted",
                }
        else:
            capture_state = {"status": "complete"}

        return {
            "cpu": cpu,
            "memory_total_bytes": mem_bytes,
            "gpus": gpus,
            "capture_state": capture_state,
        }
    except Exception as e:
        logger.debug("pubrun generic hardware failure: %s", e)
        return {
            "capture_state": {"status": "failed", "detail": str(e)}
        }
