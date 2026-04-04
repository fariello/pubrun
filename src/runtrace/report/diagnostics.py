import json
import os
import sys
from pathlib import Path
from runtrace.report.utils import hydrate_manifest

def bytes_to_gb(bytes_val: int) -> float:
    if not bytes_val: return 0.0
    return round(bytes_val / (1024 ** 3), 1)

def print_report(manifest_path: str, depth: str = "standard") -> None:
    try:
        with open(manifest_path, "r", encoding="utf-8") as f:
            manifest = json.load(f)
    except FileNotFoundError:
        print(f"Error: Could not find manifest file at '{manifest_path}'.", file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError:
        print(f"Error: The manifest file at '{manifest_path}' is corrupt or contains invalid JSON.", file=sys.stderr)
        sys.exit(1)
        
    # Hydrate!
    manifest, warnings = hydrate_manifest(manifest_path, manifest)
    
    print(f"\n=================================================")
    print(f"            RUNTRACE DIAGNOSTICS                 ")
    print(f"=================================================")
    print(f"Source : {manifest_path}")
    
    meta_ref = manifest.get("meta_ref")
    if meta_ref:
        print(f"Parent : {meta_ref}")
        
    for w in warnings:
        print(f"\n[WARNING] {w}")
    
    print("\n--- Basic Information ---")
    run = manifest.get("run", {})
    timing = manifest.get("timing", {})
    status = manifest.get("status", {})
    python = manifest.get("python", {})
    inv = manifest.get("invocation", {})
    
    script_name = inv.get("script", {}).get("basename", "<interactive or module>")
    
    print(f"Run ID      : {run.get('run_id')}")
    print(f"Script      : {script_name}")
    print(f"Status      : {status.get('outcome')}")
    print(f"Started     : {timing.get('started_at_utc')}")
    if timing.get("elapsed_seconds"):
        print(f"Elapsed     : {timing.get('elapsed_seconds')}s")
        
    # Read Events if available
    events_path = Path(manifest_path).parent / "events.jsonl"
    if events_path.exists():
        print("\n--- Event Timeline ---")
        try:
            with open(events_path, "r", encoding="utf-8") as ef:
                for line in ef:
                    e = json.loads(line)
                    print(f"  [{e.get('timestamp')}] {e.get('type')}: {e.get('name', '')} {e.get('payload', '')}")
        except Exception:
            print("  (Events file corrupt or unreadable)")
        
    if depth == "basic":
        print()
        return
        
    # --- STANDARD ---
    host = manifest.get("host", {})
    hw = manifest.get("hardware", {})
    git = manifest.get("git", {})
    pkgs = manifest.get("packages", {}).get("records", [])
    envs = manifest.get("environment", {}).get("variables", [])
    
    cpu_model = hw.get("cpu", {}).get("model", "unknown")
    ram_gb = bytes_to_gb(hw.get("memory_total_bytes", 0))
    
    print("\n--- Standard Information ---")
    print(f"Arguments   : {' '.join(inv.get('argv', []))}")
    
    # Safely extract python version
    py_ver = python.get("version", "")
    if py_ver:
        v_tag = py_ver.split()[0]
    else:
        v_tag = "unknown"
    print(f"Python      : {python.get('executable')} (v{v_tag})")
    
    print(f"Host        : {host.get('os_name')} {host.get('os_version')} ({cpu_model}, {ram_gb} GB RAM)")
    
    commit = git.get("commit")
    if commit:
        remote = git.get("remote_url", {}).get("value", "unknown origin")
        print(f"Git Commit  : {commit[:8]} ({remote})")
    else:
        print("Git Commit  : Not found or un-tracked")
        
    print(f"Packages    : {len(pkgs)} recorded")
    print(f"Env Vars    : {len(envs)} explicitly captured")
    
    if depth == "standard":
        print()
        return
        
    # --- DEEP ---
    print("\n--- Deep Information ---")
    
    # Read Config
    cfg_path = Path(manifest_path).parent / "config.resolved.json"
    if cfg_path.exists():
        try:
            with open(cfg_path, "r", encoding="utf-8") as cf:
                cfg = json.load(cf)
            print("\n[ Overridden Configurations ]")
            print(f"  Profile: {cfg.get('core', {}).get('profile')}")
            print(f"  Inputs Mode: {cfg.get('capture', {}).get('inputs', {}).get('enabled')}")
            print(f"  Packages Mode: {cfg.get('capture', {}).get('packages', {}).get('mode')}")
        except Exception:
            pass

    print("\n[ Environment Variables ]")
    if not envs:
        print("  (None captured)")
    for var in envs:
        name = var.get("name")
        val_obj = var.get("value", {})
        if isinstance(val_obj, dict) and "representation" in val_obj:
            if val_obj["representation"] == "plain":
                print(f"  {name}={val_obj.get('value', '')}")
            else:
                print(f"  {name}=<{val_obj['representation'].upper()}>")
        else:
            print(f"  {name}={val_obj}")
            
    print("\n[ Packages ]")
    if not pkgs:
        print("  (None captured)")
    
    for i, p in enumerate(pkgs):
        name = p.get('name')
        ver = p.get('version', 'unknown')
        print(f"{name}=={ver}".ljust(30), end="")
        if (i + 1) % 3 == 0:
            print()
    if len(pkgs) % 3 != 0:
        print()
        
    subprocs = manifest.get("subprocesses", [])
    print(f"\n[ Subprocesses ] ({len(subprocs)} executed)")
    for sp in subprocs:
        cmd = sp.get("command", [])
        if isinstance(cmd, list):
            cmd_str = " ".join(str(c) for c in cmd)
        else:
            cmd_str = str(cmd)
        rc = sp.get("return_code")
        elapsed = sp.get("timing", {}).get("elapsed_seconds")
        print(f"  [{rc}] {cmd_str} ({elapsed}s)")
        
    print()
