import json
from pathlib import Path
from datetime import datetime, timezone
from pubrun.config import resolve_config
from pubrun.capture.python_runtime import get_python_runtime
from pubrun.capture.packages import get_packages
from pubrun.capture.environment import get_environment
from pubrun.capture.git import get_git
from pubrun.capture.hardware import get_hardware
from pubrun.capture.host import get_host

def generate_meta_snapshot(output_path: str, depth: str) -> None:
    """Generate a standalone environment snapshot for HPC parent-child hydration.

    Args:
        output_path: Target JSON file path.
        depth: Profiling depth (``"basic"``, ``"standard"``, ``"deep"``).
    """
    print(f"[*] Analyzing Global Environment Context (Depth: {depth})...")
    # Resolve config with explicit overrides for global mode
    cfg = resolve_config({
        "core": {"profile": depth},
        "capture": {"packages": {"mode": "full-environment"}}
    })
    
    # 1. Capture Heavies
    hardware = get_hardware(cfg)
    python_env = get_python_runtime(cfg)
    packages = get_packages(cfg)
    git_track = get_git(cfg)
    sys_env = get_environment(cfg)
    host_env = get_host(cfg)
    
    # Construct Parent Map
    import time
    now_ts = time.time()
    
    meta_json = {
        "manifest_type": "pubrun-meta-snapshot",
        "timing": {
            "started_at_utc": now_ts
        },
        "hardware": hardware,
        "python": python_env,
        "packages": packages,
        "git": git_track,
        "environment": sys_env,
        "host": host_env
    }
    
    # Drop to file
    out_target = Path(output_path) if output_path else Path.cwd() / "runs" / "meta.json"
    out_target.parent.mkdir(parents=True, exist_ok=True)
    
    with open(out_target, "w", encoding="utf-8") as f:
        json.dump(meta_json, f, indent=2)
        
    print(f"[OK] Meta snapshot saved to: {out_target}")
    
    # Print a brief summary to console
    print("\n--- Snapshot Brief ---")
    pkgs = packages.get("records", [])
    print(f"Packages       : {len(pkgs)} recorded dependencies (Pip/Conda)")
    print(f"Git Context    : {git_track.get('commit', 'No tracked repository found.')}")
    
    py_ver = python_env.get("version", "")
    if py_ver:
        v_tag = py_ver.split()[0]
    else:
        v_tag = "unknown"
    print(f"Python Runtime : v{v_tag}")
    print(f"Hardware       : {hardware.get('cpu', {}).get('model', 'unknown')}")
