import json
import os
import sys
from pathlib import Path
from datetime import datetime, timezone
from pubrun.report.utils import hydrate_manifest

def bytes_to_gb(bytes_val: int) -> float:
    if not bytes_val: return 0.0
    return round(bytes_val / (1024 ** 3), 1)

class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BOLD = '\033[1m'
    DIM = '\033[2m'
    RESET = '\033[0m'

def _has_color() -> bool:
    return not os.environ.get("NO_COLOR", "")

def _print_error(message: str) -> None:
    if os.environ.get("NO_COLOR", ""):
        print(f"[ERRO] {message}", file=sys.stderr)
    else:
        print(f"\033[31m[ERRO]\033[0m {message}", file=sys.stderr)

def _supports_unicode(stream) -> bool:
    try:
        "┌".encode(getattr(stream, "encoding", "utf-8") or "utf-8")
        return True
    except UnicodeEncodeError:
        return False

def print_report(manifest_path: str, depth: str = "standard") -> None:
    """Print a human-readable diagnostic summary of a recorded run.

    Args:
        manifest_path: Path to the manifest.json file.
        depth: Verbosity level (``"basic"``, ``"standard"``, or ``"deep"``).
    """
    try:
        with open(manifest_path, "r", encoding="utf-8") as f:
            manifest = json.load(f)
    except FileNotFoundError:
        _print_error(f"Could not find manifest file at '{manifest_path}'.")
        sys.exit(1)
    except json.JSONDecodeError:
        _print_error(f"The manifest file at '{manifest_path}' is corrupt or contains invalid JSON.")
        sys.exit(1)
        
    # Hydrate!
    manifest, warnings = hydrate_manifest(manifest_path, manifest)
    
    use_color = _has_color()
    bold = Colors.BOLD if use_color else ""
    rst = Colors.RESET if use_color else ""
    
    if use_color:
        if _supports_unicode(sys.stdout):
            print(f"\n{bold}┌─────────────────────────────────────────────────┐{rst}")
            print(f"{bold}│               PUBRUN DIAGNOSTICS                │{rst}")
            print(f"{bold}└─────────────────────────────────────────────────┘{rst}")
        else:
            print(f"\n{bold}+-------------------------------------------------+{rst}")
            print(f"{bold}|               PUBRUN DIAGNOSTICS                |{rst}")
            print(f"{bold}+-------------------------------------------------+{rst}")
    else:
        print(f"\n=================================================")
        print(f"               PUBRUN DIAGNOSTICS                ")
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
    
    signals_data = manifest.get("signals", {})
    exit_code = signals_data.get("exit_code")
    exit_exception = signals_data.get("exit_exception")
    signals_received = signals_data.get("signals_received", [])

    # Colorize outcome
    outcome = status.get('outcome', 'unknown')
    out_color = ""
    if use_color:
        if outcome == "completed":
            out_color = Colors.GREEN
        elif outcome in ("failed", "crashed"):
            out_color = Colors.RED
        elif outcome == "interrupted":
            out_color = Colors.YELLOW

    print(f"Run ID      : {run.get('run_id')}")
    print(f"Script      : {script_name}")
    print(f"Status      : {out_color}{outcome}{rst}")
    if exit_code is not None and exit_code != 0:
        print(f"Exit Code   : {Colors.RED if use_color else ''}{exit_code}{rst}")
    if exit_exception:
        print(f"Exception   : {Colors.RED if use_color else ''}{exit_exception}{rst}")
    if signals_received:
        sig_names = [s.get("signal_name", f"SIG{s.get('signal')}") for s in signals_received]
        print(f"Signals     : {Colors.YELLOW if use_color else ''}{', '.join(sig_names)}{rst}")

    start_ts = timing.get('started_at_utc')
    start_str = datetime.fromtimestamp(start_ts, tz=timezone.utc).isoformat() if start_ts else "unknown"
    print(f"Started     : {start_str}")
    if timing.get("elapsed_seconds"):
        print(f"Elapsed     : {timing.get('elapsed_seconds')}s")
        
    # Read Events if available
    events_path = Path(manifest_path).parent / "events.jsonl"
    if events_path.exists():
        print("\n--- Event Timeline ---")
        try:
            from collections import deque
            with open(events_path, "r", encoding="utf-8") as ef:
                first_events = []
                last_events = deque(maxlen=20)
                total_events = 0
                for line in ef:
                    total_events += 1
                    if total_events <= 20:
                        first_events.append(line)
                    else:
                        last_events.append(line)
                        
                def _print_ev(raw_line: str) -> None:
                    e = json.loads(raw_line)
                    ts = e.get('timestamp_utc', 0.0)
                    ts_str = datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()
                    print(f"  [{ts_str}] {e.get('type')}: {e.get('name', '')} {e.get('payload', '')}")
                    
                for line in first_events:
                    _print_ev(line)
                    
                if total_events > 40:
                    print(f"  ... [ {total_events - 40} events logically truncated ] ...")
                    
                if total_events > 20:
                    # Render the remaining tail
                    for line in last_events:
                        _print_ev(line)
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
    
    hostname = host.get("hostname", "unknown")
    print(f"Host        : {hostname} - {host.get('os_name')} {host.get('os_version')} ({cpu_model}, {ram_gb} GB RAM)")
    
    commit = git.get("commit")
    if commit:
        remote = git.get("remote_url", {}).get("value", "unknown origin")
        print(f"Git Commit  : {commit[:8]} ({remote})")
    else:
        print("Git Commit  : Not found or un-tracked")
        
    print(f"Packages    : {len(pkgs)} recorded")
    print(f"Env Vars    : {len(envs)} captured")
    
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
        cmd = sp.get("argv", [])
        if isinstance(cmd, list):
            cmd_str = " ".join(str(c) for c in cmd)
        else:
            cmd_str = str(cmd)
        rc = sp.get("exit_code")
        started = sp.get("started_at_utc")
        ended = sp.get("ended_at_utc")
        if started and ended:
            elapsed = round(ended - started, 3)
            print(f"  [{rc}] {cmd_str} ({elapsed}s)")
        else:
            print(f"  [{rc}] {cmd_str}")
        
    print()
