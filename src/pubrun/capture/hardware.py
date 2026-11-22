import logging
import math
import os
import platform
import subprocess
import sys
import time
from typing import Any, Dict, List, Optional

logger = logging.getLogger("pubrun")

# Default per-command timeout (seconds) for hardware-inspection subprocesses if
# no config value is available. Overridable via [capture.hardware].timeout.
_DEFAULT_HW_TIMEOUT = 10.0


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
            cmd_timeout = budget.next_timeout() if budget is not None else timeout
            if cmd_timeout is None:
                return None
            from pubrun.capture.subprocesses import disable_spy
            with disable_spy():
                out = subprocess.check_output(
                    ["wmic", "cpu", "get", "Name"],
                    text=True,
                    stderr=subprocess.DEVNULL,
                    timeout=cmd_timeout,
                )
            lines = [line.strip() for line in out.splitlines() if line.strip()]
            if len(lines) >= 2:
                return lines[1]
        elif sys_plat == "darwin":
            cmd_timeout = budget.next_timeout() if budget is not None else timeout
            if cmd_timeout is None:
                return None
            from pubrun.capture.subprocesses import disable_spy
            with disable_spy():
                out = subprocess.check_output(
                    ["sysctl", "-n", "machdep.cpu.brand_string"],
                    text=True,
                    stderr=subprocess.DEVNULL,
                    timeout=cmd_timeout,
                )
            return out.strip()
        elif sys_plat.startswith("linux"):
            if os.path.exists("/proc/cpuinfo"):
                with open("/proc/cpuinfo", "r", encoding="utf-8") as f:
                    for line in f:
                        if line.startswith("model name"):
                            return line.split(":", 1)[1].strip()
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
            cmd_timeout = budget.next_timeout() if budget is not None else timeout
            if cmd_timeout is None:
                return None
            from pubrun.capture.subprocesses import disable_spy
            with disable_spy():
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
            from pubrun.capture.subprocesses import disable_spy
            with disable_spy():
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

            from pubrun.capture.subprocesses import disable_spy
            with disable_spy():
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

    # Attempt 2: Generic OS fallback on Windows/macOS when nvidia-smi found none.
    if not gpus and sys.platform in ("win32", "darwin"):
        fallback_timeout = budget.next_timeout() if budget is not None else timeout
        if fallback_timeout is not None:
            try:
                sys_plat = sys.platform
                if sys_plat == "win32":
                    from pubrun.capture.subprocesses import disable_spy
                    with disable_spy():
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
                            if parts[1].isdigit():
                                mem = int(parts[1])
                                if mem < 0:
                                    mem = mem & 0xFFFFFFFF
                            gpus.append({
                                "vendor": "Generic",
                                "model": parts[3],
                                "memory_total_bytes": mem,
                                "driver_version": parts[2],
                            })
                elif sys_plat == "darwin":
                    from pubrun.capture.subprocesses import disable_spy
                    with disable_spy():
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
                            gpu_rec["model"] = stripped.split(":", 1)[1].strip()
                        elif stripped.startswith("VRAM (Total):"):
                            gpu_rec["memory_total_bytes"] = None
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

    GPU detection uses nvidia-smi (NVIDIA), wmic (Windows), or
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
