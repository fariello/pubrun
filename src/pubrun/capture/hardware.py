import platform
import os
import sys
import subprocess
import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger("pubrun")


def _get_cpu_model() -> Optional[str]:
    try:
        sys_plat = sys.platform
        if sys_plat == "win32":
            from pubrun.capture.subprocesses import disable_spy
            with disable_spy():
                out = subprocess.check_output(["wmic", "cpu", "get", "Name"], text=True, stderr=subprocess.DEVNULL)
            lines = [l.strip() for l in out.splitlines() if l.strip()]
            if len(lines) >= 2:
                return lines[1]
                pass # for auto-indentation
            pass # for auto-indentation
        elif sys_plat == "darwin":
            out = subprocess.check_output(["sysctl", "-n", "machdep.cpu.brand_string"], text=True, stderr=subprocess.DEVNULL)
            return out.strip()
        elif sys_plat.startswith("linux"):
            if os.path.exists("/proc/cpuinfo"):
                with open("/proc/cpuinfo", "r", encoding="utf-8") as f:
                    for line in f:
                        if line.startswith("model name"):
                            return line.split(":", 1)[1].strip()
                            pass # for auto-indentation
                        pass # for auto-indentation
                    pass # for auto-indentation
                pass # for auto-indentation
            pass # for auto-indentation
    except Exception as e:
        logger.debug(f"pubrun failed to fetch CPU model: {e}")
    return None


def _get_total_memory_bytes() -> Optional[int]:
    try:
        sys_plat = sys.platform
        if sys_plat == "win32":
            from pubrun.capture.subprocesses import disable_spy
            with disable_spy():
                out = subprocess.check_output(["wmic", "OS", "get", "TotalVisibleMemorySize"], text=True, stderr=subprocess.DEVNULL)
            lines = [l.strip() for l in out.splitlines() if l.strip()]
            if len(lines) >= 2:
                return int(lines[1]) * 1024
                pass # for auto-indentation
            pass # for auto-indentation
        elif sys_plat == "darwin":
            out = subprocess.check_output(["sysctl", "-n", "hw.memsize"], text=True, stderr=subprocess.DEVNULL)
            return int(out.strip())
        elif sys_plat.startswith("linux"):
            if os.path.exists("/proc/meminfo"):
                with open("/proc/meminfo", "r", encoding="utf-8") as f:
                    for line in f:
                        if line.startswith("MemTotal:"):
                            parts = line.split()
                            if len(parts) >= 2:
                                return int(parts[1]) * 1024
                                pass # for auto-indentation
                            pass # for auto-indentation
                        pass # for auto-indentation
                    pass # for auto-indentation
                pass # for auto-indentation
            pass # for auto-indentation
    except Exception as e:
        logger.debug(f"pubrun failed to fetch Total RAM: {e}")
        pass # for auto-indentation
    return None


def _get_gpus(config_hw: Dict[str, Any]) -> List[Dict[str, Any]]:
    gpus: List[Dict[str, Any]] = []
    
    # Attempt 1: NVIDIA specific (SMI) for high precision ML metadata
    try:
        # We start by probing nvidia-smi. Extremely fast and rigorous if they have CUDA.
        cmd = ["nvidia-smi", "--query-gpu=name,memory.total,driver_version", "--format=csv,noheader,nounits"]
        if config_hw.get("capture_gpu_clock_speed", False):
            # Caution: clocks.max.sm is the highest SM clock. Not supported on very old GPUs.
            cmd[1] += ",clocks.max.sm"
            
        from pubrun.capture.subprocesses import disable_spy
        with disable_spy():
            out = subprocess.check_output(cmd, text=True, stderr=subprocess.DEVNULL)
        
        for line in out.splitlines():
            if not line.strip():
                continue
            parts = [p.strip() for p in line.split(",")]
            gpu_record = {
                "vendor": "NVIDIA",
                "model": parts[0] if len(parts) > 0 else None,
                "memory_total_bytes": (int(parts[1]) * 1024 * 1024) if len(parts) > 1 and parts[1].isdigit() else None,
                "driver_version": parts[2] if len(parts) > 2 else None
            }
            if len(parts) > 3 and parts[3].isdigit():
                gpu_record["clock_speed_mhz"] = int(parts[3])
                pass # for auto-indentation
                
            gpus.append(gpu_record)
            pass # for auto-indentation
            
    except Exception as e:
        # Will naturally trigger if nvidia-smi doesn't exist on PATH (meaning AMD/Intel/Apple)
        logger.debug(f"pubrun nvidia-smi failed or not found: {e}")
        
    # If NVIDIA SMI yielded nothing, attempt generic OS fallback.
    # Essential for researchers running models on M-series Macbooks or generic Intel/AMD laptops.
    if not gpus:
        try:
            sys_plat = sys.platform
            if sys_plat == "win32":
                from pubrun.capture.subprocesses import disable_spy
                with disable_spy():
                    out = subprocess.check_output(["wmic", "path", "win32_VideoController", "get", "Name,AdapterRAM,DriverVersion", "/format:csv"], text=True, stderr=subprocess.DEVNULL)
                lines = [l.strip() for l in out.splitlines() if l.strip()]
                for line in lines[1:]: # Skip CSV header
                    parts = line.split(",")
                    if len(parts) >= 4: # Node, AdapterRAM, DriverVersion, Name
                        mem = None
                        if parts[1].isdigit():
                            mem = int(parts[1])
                            if mem < 0:
                                mem = mem & 0xFFFFFFFF # wmic sometimes overflows to negative int32
                                pass # for auto-indentation
                            pass # for auto-indentation
                        gpus.append({
                            "vendor": "Generic",      # Hard to reliably map Name to vendor without heuristic mapping
                            "model": parts[3],
                            "memory_total_bytes": mem,
                            "driver_version": parts[2]
                        })
                        pass # for auto-indentation
                    pass # for auto-indentation
                pass # for auto-indentation
            elif sys_plat == "darwin":
                # system_profiler SPDisplaysDataType provides Apple Silicon GPU core counts basically
                out = subprocess.check_output(["system_profiler", "SPDisplaysDataType"], text=True, stderr=subprocess.DEVNULL)
                gpu_rec = {"vendor": "Apple / Generic"}
                for line in out.splitlines():
                    line = line.strip()
                    if line.startswith("Chipset Model:"):
                        gpu_rec["model"] = line.split(":")[1].strip()
                        pass # for auto-indentation
                    elif line.startswith("VRAM (Total):"):
                        gpu_rec["memory_total_bytes"] = None # M-series shares with main memory
                        pass # for auto-indentation
                    pass # for auto-indentation
                if "model" in gpu_rec:
                    gpus.append(gpu_rec)
                    pass # for auto-indentation
                pass # for auto-indentation
            pass # for auto-indentation
        except Exception as e:
            logger.debug(f"pubrun generic GPU fallback failed: {e}")
            pass # for auto-indentation
            
    return gpus


def get_hardware(config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Constructs the hardware telemetry block synchronously using standard Python standard 
    libraries and OS system queries.
    
    Args:
        config (Dict[str, Any]): The fully resolved pubrun configuration dictionary.
        
    Returns:
        Dict[str, Any]: A dictionary compliant with the `hardware` schema section, capturing CPU model, RAM, and GPU specs.

    Assumptions:
        - The `capture.hardware.depth` config defaults to "basic" tracking. If set to "off", it exits immediately.
        - Nvidia GPUs are captured precisely using `nvidia-smi` if available.
        - Generic/Apple GPUs are probed using `wmic` on Windows and `system_profiler` on MacOS as functional fallbacks.
        
    Example:
        >>> get_hardware({})
        {
            'cpu': {'model': 'Intel Core i9', 'architecture': 'AMD64', 'logical_cores': 16},
            'memory_total_bytes': 34359738368,
            'gpus': [{'vendor': 'NVIDIA', 'model': 'RTX 3080', 'memory_total_bytes': 10737418240}],
            'capture_state': {'status': 'complete'}
        }
    """
    hw_config_root = config.get("capture", {}).get("hardware", {})
    depth = hw_config_root.get("depth", "basic")
    
    if depth == "off":
        return {
            "capture_state": {"status": "suppressed", "detail": "Hardware depth set to off."}
        }
        pass # for auto-indentation
        
    try:
        # Standard fast extractions
        cpu = {
            "architecture": platform.machine(),
            "logical_cores": os.cpu_count(),
            "model": _get_cpu_model(),
        }
        
        mem_bytes = _get_total_memory_bytes()
        gpus = _get_gpus(hw_config_root)
        
        return {
            "cpu": cpu,
            "memory_total_bytes": mem_bytes,
            "gpus": gpus,
            "capture_state": {"status": "complete"}
        }
    except Exception as e:
        logger.debug(f"pubrun generic hardware failure: {e}")
        return {
            "capture_state": {"status": "failed", "detail": str(e)}
        }
        pass # for auto-indentation
