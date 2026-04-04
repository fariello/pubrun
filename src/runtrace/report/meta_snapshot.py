import json
from pathlib import Path
from datetime import datetime, timezone
from runtrace.config import resolve_config
from runtrace.capture.python_runtime import get_python_runtime
from runtrace.capture.packages import get_packages
from runtrace.capture.environment import get_environment
from runtrace.capture.git import get_git
from runtrace.capture.hardware import get_hardware

def generate_meta_snapshot(output_path: str, depth: str) -> None:
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
    
    # Construct Parent Map
    def _str_fmt(dt: datetime) -> str:
        return dt.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
        
    now = datetime.now(timezone.utc)
    
    meta_json = {
        "manifest_type": "runtrace-meta-snapshot",
        "timing": {
            "started_at_utc": _str_fmt(now)
        },
        "hardware": hardware,
        "python": python_env,
        "packages": packages,
        "git": git_track,
        "environment": sys_env
    }
    
    # Drop to file
    out_target = Path(output_path) if output_path else Path.cwd() / "runs" / "meta.json"
    out_target.parent.mkdir(parents=True, exist_ok=True)
    
    with open(out_target, "w", encoding="utf-8") as f:
        json.dump(meta_json, f, indent=2)
        
    print(f"[OK] Global meta snapshot generated perfectly: {out_target}")
    
    # Print a tiny brief to console natively
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
