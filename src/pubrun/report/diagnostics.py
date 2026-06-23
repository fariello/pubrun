from __future__ import annotations
import json
from typing import Optional
import os
import sys
from pathlib import Path
from datetime import datetime, timezone
from pubrun.report.utils import hydrate_manifest

def bytes_to_gb(bytes_val: int) -> float:
    if not bytes_val: return 0.0
    return round(bytes_val / (1024 ** 3), 1)

class Colors:
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    MAGENTA = '\033[95m'
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

def print_report(manifest_path: str, depth: str = "standard", section: Optional[str] = None) -> None:
    """Print a human-readable diagnostic summary of a recorded run.

    Args:
        manifest_path: Path to the manifest.json file.
        depth: Verbosity level (``"basic"``, ``"standard"``, or ``"deep"``).
        section: Optional section to extract (``"logs"``, ``"env"``, or ``"packages"``).
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

    if section == "logs":
        run_dir = Path(manifest_path).parent
        stdout_path = run_dir / "stdout.log"
        stderr_path = run_dir / "stderr.log"
        if stdout_path.exists():
            try:
                with open(stdout_path, "r", encoding="utf-8", errors="replace") as sf:
                    print(sf.read(), end="")
            except Exception as e:
                _print_error(f"Failed to read stdout log: {e}")
                sys.exit(1)
        if stderr_path.exists():
            try:
                with open(stderr_path, "r", encoding="utf-8", errors="replace") as se:
                    print(se.read(), end="")
            except Exception as e:
                _print_error(f"Failed to read stderr log: {e}")
                sys.exit(1)
        return

    if section == "env":
        envs = manifest.get("environment", {}).get("variables", [])
        use_color = _has_color()
        blue = Colors.BLUE if use_color else ""
        green = Colors.GREEN if use_color else ""
        yellow = Colors.YELLOW if use_color else ""
        rst = Colors.RESET if use_color else ""
        
        print(f"{blue}[ Environment Variables ]{rst}")
        if not envs:
            print("  (None captured)")
        for var in envs:
            name = var.get("name")
            val_obj = var.get("value", {})
            if isinstance(val_obj, dict) and "representation" in val_obj:
                if val_obj["representation"] == "plain":
                    print(f"  {green}{name}{rst}={val_obj.get('value', '')}")
                else:
                    print(f"  {green}{name}{rst}={yellow}<{val_obj['representation'].upper()}>{rst}")
            else:
                print(f"  {green}{name}{rst}={val_obj}")
        return

    if section == "packages":
        pkgs = manifest.get("packages", {}).get("records", [])
        use_color = _has_color()
        blue = Colors.BLUE if use_color else ""
        green = Colors.GREEN if use_color else ""
        rst = Colors.RESET if use_color else ""
        
        print(f"{blue}[ Packages ]{rst}")
        if not pkgs:
            print("  (None captured)")
        for i, p in enumerate(pkgs):
            name = p.get('name')
            ver = p.get('version', 'unknown')
            pkg_str = f"{name}=={ver}"
            display_len = len(pkg_str)
            if use_color:
                pkg_str = f"{green}{name}{rst}=={ver}"
            print(pkg_str.ljust(30 + (len(pkg_str) - display_len)), end="")
            if (i + 1) % 3 == 0:
                print()
        if len(pkgs) % 3 != 0:
            print()
        return
    
    use_color = _has_color()
    bold = Colors.BOLD if use_color else ""
    rst = Colors.RESET if use_color else ""
    cyan = Colors.CYAN if use_color else ""
    blue = Colors.BLUE if use_color else ""
    green = Colors.GREEN if use_color else ""
    red = Colors.RED if use_color else ""
    yellow = Colors.YELLOW if use_color else ""
    
    if use_color:
        if _supports_unicode(sys.stdout):
            print(f"\n{cyan}{bold}┌─────────────────────────────────────────────────┐{rst}")
            print(f"{cyan}{bold}│               PUBRUN DIAGNOSTICS                │{rst}")
            print(f"{cyan}{bold}└─────────────────────────────────────────────────┘{rst}")
        else:
            print(f"\n{cyan}{bold}+-------------------------------------------------+{rst}")
            print(f"{cyan}{bold}|               PUBRUN DIAGNOSTICS                |{rst}")
            print(f"{cyan}{bold}+-------------------------------------------------+{rst}")
    else:
        print(f"\n=================================================")
        print(f"               PUBRUN DIAGNOSTICS                ")
        print(f"=================================================")
        
    print(f"{cyan}Source{rst}      : {manifest_path}")
    
    meta_ref = manifest.get("meta_ref")
    if meta_ref:
        print(f"{cyan}Parent{rst}      : {meta_ref}")
        
    for w in warnings:
        print(f"\n{yellow}[WARNING]{rst} {w}")
    
    print(f"\n{blue}{bold}--- Basic Information ---{rst}")
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

    print(f"{cyan}Run ID{rst}      : {run.get('run_id')}")
    print(f"{cyan}Script{rst}      : {script_name}")
    print(f"{cyan}Status{rst}      : {out_color}{outcome}{rst}")
    if exit_code is not None and exit_code != 0:
        print(f"{cyan}Exit Code{rst}   : {red}{exit_code}{rst}")
    if exit_exception:
        print(f"{cyan}Exception{rst}   : {red}{exit_exception}{rst}")
    if signals_received:
        sig_names = [s.get("signal_name", f"SIG{s.get('signal')}") for s in signals_received]
        print(f"{cyan}Signals{rst}     : {yellow}{', '.join(sig_names)}{rst}")

    start_ts = timing.get('started_at_utc')
    start_str = datetime.fromtimestamp(start_ts, tz=timezone.utc).isoformat() if start_ts else "unknown"
    print(f"{cyan}Started{rst}     : {start_str}")
    if timing.get("elapsed_seconds"):
        print(f"{cyan}Elapsed{rst}     : {timing.get('elapsed_seconds')}s")
        
    # Read Events if available
    events_path = Path(manifest_path).parent / "events.jsonl"
    if events_path.exists():
        print(f"\n{blue}{bold}--- Event Timeline ---{rst}")
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
                    print(f"  [{cyan}{ts_str}{rst}] {green}{e.get('type')}{rst}: {e.get('name', '')} {e.get('payload', '')}")
                    
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
    
    print(f"\n{blue}{bold}--- Standard Information ---{rst}")
    print(f"{cyan}Arguments{rst}   : {' '.join(inv.get('argv', []))}")
    
    # Safely extract python version
    py_ver = python.get("version", "")
    if py_ver:
        v_tag = py_ver.split()[0]
    else:
        v_tag = "unknown"
    print(f"{cyan}Python{rst}      : {python.get('executable')} (v{v_tag})")
    
    hostname = host.get("hostname", "unknown")
    print(f"{cyan}Host{rst}        : {hostname} - {host.get('os_name')} {host.get('os_version')} ({cpu_model}, {ram_gb} GB RAM)")
    
    commit = git.get("commit")
    if commit:
        remote = git.get("remote_url", {}).get("value", "unknown origin")
        print(f"{cyan}Git Commit{rst}  : {commit[:8]} ({remote})")
    else:
        print(f"{cyan}Git Commit{rst}  : Not found or un-tracked")
        
    print(f"{cyan}Packages{rst}    : {len(pkgs)} recorded")
    print(f"{cyan}Env Vars{rst}    : {len(envs)} captured")
    
    if depth == "standard":
        print()
        return
        
    # --- DEEP ---
    print(f"\n{blue}{bold}--- Deep Information ---{rst}")
    
    # Read Config
    cfg_path = Path(manifest_path).parent / "config.resolved.json"
    if cfg_path.exists():
        try:
            with open(cfg_path, "r", encoding="utf-8") as cf:
                cfg = json.load(cf)
            print(f"\n{blue}[ Overridden Configurations ]{rst}")
            print(f"  {cyan}Profile{rst}: {cfg.get('core', {}).get('profile')}")
            print(f"  {cyan}Inputs Mode{rst}: {cfg.get('capture', {}).get('inputs', {}).get('enabled')}")
            print(f"  {cyan}Packages Mode{rst}: {cfg.get('capture', {}).get('packages', {}).get('mode')}")
        except Exception:
            pass

    print(f"\n{blue}[ Environment Variables ]{rst}")
    if not envs:
        print("  (None captured)")
    for var in envs:
        name = var.get("name")
        val_obj = var.get("value", {})
        if isinstance(val_obj, dict) and "representation" in val_obj:
            if val_obj["representation"] == "plain":
                print(f"  {green}{name}{rst}={val_obj.get('value', '')}")
            else:
                print(f"  {green}{name}{rst}={yellow}<{val_obj['representation'].upper()}>{rst}")
        else:
            print(f"  {green}{name}{rst}={val_obj}")
            
    print(f"\n{blue}[ Packages ]{rst}")
    if not pkgs:
        print("  (None captured)")
    
    for i, p in enumerate(pkgs):
        name = p.get('name')
        ver = p.get('version', 'unknown')
        pkg_str = f"{name}=={ver}"
        display_len = len(pkg_str)
        if use_color:
            pkg_str = f"{green}{name}{rst}=={ver}"
        print(pkg_str.ljust(30 + (len(pkg_str) - display_len)), end="")
        if (i + 1) % 3 == 0:
            print()
    if len(pkgs) % 3 != 0:
        print()
        
    subprocs = manifest.get("subprocesses", [])
    print(f"\n{blue}[ Subprocesses ]{rst} ({len(subprocs)} executed)")
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
            print(f"  [{green if rc == 0 else red}{rc}{rst}] {cmd_str} ({elapsed}s)")
        else:
            print(f"  [{green if rc == 0 else red}{rc}{rst}] {cmd_str}")
        
    print()


def format_elapsed_range(total_seconds: float) -> tuple[str, str]:
    sec_int = int(round(total_seconds))
    days = sec_int // 86400
    hours = (sec_int % 86400) // 3600
    minutes = (sec_int % 3600) // 60
    secs = sec_int % 60
    
    if days > 0:
        return "0d 00:00:00", f"{days}d {hours:02d}:{minutes:02d}:{secs:02d}"
    elif hours > 0:
        return "00:00:00", f"{hours:02d}:{minutes:02d}:{secs:02d}"
    else:
        return "00:00", f"{minutes:02d}:{secs:02d}"


def parse_duration(val: str) -> float:
    val = val.strip().lower()
    if not val:
        raise ValueError("duration string is empty")
    if val.endswith("d"):
        return float(val[:-1]) * 86400
    elif val.endswith("h"):
        return float(val[:-1]) * 3600
    elif val.endswith("m"):
        return float(val[:-1]) * 60
    elif val.endswith("s"):
        return float(val[:-1])
    else:
        return float(val)


def draw_ascii_chart(
    data: list[float], 
    timestamps: list[float], 
    title: str, 
    unit: str, 
    height: int = 8, 
    width: int = 50, 
    color: str = "", 
    use_color: bool = True,
    average: bool = False,
) -> None:
    """Helper to render a standardized ASCII utilization area graph."""
    min_val = 0.0
    max_val = max(0.1, max(data))
    if unit == "%":
        max_val = max(100.0, max_val)
        
    n = len(data)
    y_vals = []
    if n <= width:
        # No downsampling needed, just interpolate/map to closest indices
        for x in range(width):
            idx = int(round(x * (n - 1) / (width - 1))) if width > 1 else 0
            idx = max(0, min(n - 1, idx))
            y_vals.append(data[idx])
    else:
        # Downsampling needed: group by bin
        t_start = timestamps[0]
        t_end = timestamps[-1]
        total_time = t_end - t_start
        
        # Initialize bins
        bins = [[] for _ in range(width)]
        for i in range(n):
            t = timestamps[i]
            if total_time > 0:
                pct = (t - t_start) / total_time
                bin_idx = int(pct * width)
                bin_idx = max(0, min(width - 1, bin_idx))
            else:
                bin_idx = 0
            bins[bin_idx].append(data[i])
            
        for x in range(width):
            bin_data = bins[x]
            if not bin_data:
                # Fallback to nearest neighbor index
                idx = int(round(x * (n - 1) / (width - 1))) if width > 1 else 0
                idx = max(0, min(n - 1, idx))
                val = data[idx]
            else:
                if average:
                    val = sum(bin_data) / len(bin_data)
                else:
                    val = max(bin_data)
            y_vals.append(val)
        
    grid = [[" " for _ in range(width)] for _ in range(height)]
    
    char = "█" if _supports_unicode(sys.stdout) else "#"
    
    for x in range(width):
        y = y_vals[x]
        pct = (y - min_val) / (max_val - min_val)
        fill_height = int(round(pct * (height - 1)))
        fill_height = max(0, min(height - 1, fill_height))
        for r in range(height - 1, height - 1 - fill_height - 1, -1):
            if 0 <= r < height:
                grid[r][x] = char
                
    bold = Colors.BOLD if use_color else ""
    rst = Colors.RESET if use_color else ""
    
    corner = "└" if _supports_unicode(sys.stdout) else "+"
    pipe = "│" if _supports_unicode(sys.stdout) else "|"
    hline = "─" if _supports_unicode(sys.stdout) else "-"
    
    print(f"\n{bold}{title}{rst}")
    
    for r in range(height):
        val = max_val - r * (max_val - min_val) / (height - 1)
        label_str = f"{val:6.1f} {unit}".rjust(10)
        row_str = "".join(grid[r])
        if use_color and color:
            row_str = f"{color}{row_str}{rst}"
        print(f"  {label_str} {pipe} {row_str}")
        
    # Put ticks at the start, 25%, middle, 75%, and end marks
    ticks_str = list(hline * width)
    if width > 1:
        tick_char = "┴" if _supports_unicode(sys.stdout) else "+"
        ticks_str[0] = tick_char
        ticks_str[-1] = tick_char
        ticks_str[(width - 1) // 2] = tick_char
        if width >= 8:
            ticks_str[(width - 1) // 4] = tick_char
            ticks_str[(3 * (width - 1)) // 4] = tick_char
    axis_line = "".join(ticks_str)
    print(f"  {' ' * 10} {corner}{axis_line}")
    
    elapsed_total = round(timestamps[-1] - timestamps[0], 1)
    # Format elapsed total cleanly without trailing .0 if integer
    elapsed_val = int(elapsed_total) if elapsed_total % 1 == 0 else elapsed_total
    
    start_lbl = "Start: 0s"
    end_lbl = f"End: {elapsed_val}s"
    
    # Format max value string
    if data:
        max_data_val = max(data)
        if unit == "%":
            max_str = f"Max: {max_data_val:.1f}%"
        else:
            if unit in ("GB", "MB"):
                max_str = f"Max: {max_data_val:.2f} {unit}"
            else:
                max_str = f"Max: {max_data_val:.1f} {unit}"
    else:
        max_str = ""
            
    total_lbl_len = len(start_lbl) + len(end_lbl) + len(max_str)
    if width - total_lbl_len >= 4:
        rem_spaces = width - len(start_lbl) - len(end_lbl) - len(max_str)
        spaces_left = rem_spaces // 2
        spaces_right = rem_spaces - spaces_left
        axis_labels = f"{start_lbl}{' ' * spaces_left}{max_str}{' ' * spaces_right}{end_lbl}"
    else:
        spaces = width - len(start_lbl) - len(end_lbl)
        if spaces > 0:
            axis_labels = f"{start_lbl}{' ' * spaces}{end_lbl}"
        else:
            axis_labels = f"{start_lbl} ... {end_lbl}"
    print(f"  {' ' * 13}{axis_labels}")


def print_resources_report(manifest_path: str, average: bool = False, last: Optional[str] = None, metric: str = "all", width: Optional[int] = None) -> None:
    """Print a diagnostic resources report with ASCII utilization graphs over time."""
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
    cyan = Colors.CYAN if use_color else ""
    blue = Colors.BLUE if use_color else ""
    yellow = Colors.YELLOW if use_color else ""
    red = Colors.RED if use_color else ""
    
    run = manifest.get("run", {})
    timing = manifest.get("timing", {})
    status = manifest.get("status", {})
    inv = manifest.get("invocation", {})
    resources = manifest.get("resources", {})
    
    script_name = inv.get("script", {}).get("basename", "<interactive or module>")
    outcome = status.get('outcome', 'unknown')
    
    out_color = ""
    if use_color:
        if outcome == "completed":
            out_color = Colors.GREEN
        elif outcome in ("failed", "crashed"):
            out_color = Colors.RED
        elif outcome == "interrupted":
            out_color = Colors.YELLOW

    if use_color:
        if _supports_unicode(sys.stdout):
            print(f"\n{cyan}{bold}┌─────────────────────────────────────────────────┐{rst}")
            print(f"{cyan}{bold}│               RESOURCE MONITORING               │{rst}")
            print(f"{cyan}{bold}└─────────────────────────────────────────────────┘{rst}")
        else:
            print(f"\n{cyan}{bold}+-------------------------------------------------+{rst}")
            print(f"{cyan}{bold}|               RESOURCE MONITORING               |{rst}")
            print(f"{cyan}{bold}+-------------------------------------------------+{rst}")
    else:
        print(f"\n=================================================")
        print(f"               RESOURCE MONITORING               ")
        print(f"=================================================")

    print(f"{cyan}Run ID{rst}      : {run.get('run_id')}")
    print(f"{cyan}Script{rst}      : {script_name}")
    print(f"{cyan}Status{rst}      : {out_color}{outcome}{rst}")
    
    peak_rss = resources.get("peak_rss_bytes")
    peak_cpu = resources.get("peak_cpu_percent")
    end_rss = resources.get("end_rss_bytes")
    
    if metric in ("mem", "all") and peak_rss:
        if peak_rss >= 1024**3:
            rss_str = f"{peak_rss / (1024**3):.2f} GB"
        else:
            rss_str = f"{peak_rss / (1024**2):.2f} MB"
        print(f"{cyan}Peak RSS{rst}    : {rss_str}")
        
    if metric in ("mem", "all") and end_rss:
        if end_rss >= 1024**3:
            end_rss_str = f"{end_rss / (1024**3):.2f} GB"
        else:
            end_rss_str = f"{end_rss / (1024**2):.2f} MB"
        print(f"{cyan}End RSS{rst}     : {end_rss_str}")
        
    if metric in ("cpu", "all") and peak_cpu is not None:
        print(f"{cyan}Peak CPU{rst}    : {peak_cpu}%")
        
    events_path = Path(manifest_path).parent / "events.jsonl"
    if not events_path.exists():
        print(f"\n{yellow}No events.jsonl file found. Cannot generate utilization graphs.{rst}\n")
        return
        
    timestamps = []
    rss_values = []
    cpu_values = []
    
    try:
        with open(events_path, "r", encoding="utf-8") as ef:
            for line in ef:
                try:
                    e = json.loads(line)
                    if e.get("type") == "resource_sample":
                        payload = e.get("payload", {})
                        ts = e.get("timestamp_utc")
                        rss = payload.get("rss_bytes")
                        cpu = payload.get("cpu_percent")
                        if ts is not None and rss is not None and cpu is not None:
                            timestamps.append(ts)
                            rss_values.append(rss)
                            cpu_values.append(cpu)
                except Exception:
                    pass
    except Exception:
        print(f"\n{red}Events file corrupt or unreadable.{rst}\n")
        return
        
    last_seconds = None
    if last is not None:
        try:
            last_seconds = parse_duration(last)
        except ValueError as e:
            _print_error(f"Invalid duration for --last: {e}")
            sys.exit(1)

    if last_seconds is not None and timestamps:
        cutoff_time = timestamps[-1] - last_seconds
        filtered_timestamps = []
        filtered_rss = []
        filtered_cpu = []
        for ts, rss, cpu in zip(timestamps, rss_values, cpu_values):
            if ts >= cutoff_time:
                filtered_timestamps.append(ts)
                filtered_rss.append(rss)
                filtered_cpu.append(cpu)
        timestamps = filtered_timestamps
        rss_values = filtered_rss
        cpu_values = filtered_cpu
        
    if not rss_values:
        print(f"\n{yellow}No resource samples found in events.jsonl.{rst}\n")
        return
        
    if len(rss_values) < 2:
        print(f"\nOnly one resource sample recorded:")
        if metric in ("mem", "all"):
            if rss_values[0] >= 1024**3:
                single_rss = f"{rss_values[0] / (1024**3):.2f} GB"
            else:
                single_rss = f"{rss_values[0] / (1024**2):.2f} MB"
            print(f"  Memory: {single_rss}")
        if metric in ("cpu", "all"):
            print(f"  CPU   : {cpu_values[0]}%")
        print()
        return

    # Get terminal width for dynamic sizing
    if width is not None:
        chart_width = max(20, width)
    else:
        try:
            columns = os.get_terminal_size().columns
        except OSError:
            columns = 80
        chart_width = max(20, columns - 20)

    # Plot CPU (Yellow theme)
    if metric in ("cpu", "all"):
        draw_ascii_chart(
            cpu_values, 
            timestamps, 
            "CPU Utilization History", 
            "%", 
            height=8, 
            width=chart_width, 
            color=Colors.YELLOW if use_color else "", 
            use_color=use_color,
            average=average
        )
    
    # Plot Memory (Green theme)
    if metric in ("mem", "all"):
        # Determine memory scale
        max_mem_val = max(rss_values)
        if max_mem_val >= 1024**3:
            mem_scale = 1024**3
            mem_unit = "GB"
        elif max_mem_val >= 1024**2:
            mem_scale = 1024**2
            mem_unit = "MB"
        else:
            mem_scale = 1024
            mem_unit = "KB"
            
        scaled_rss = [r / mem_scale for r in rss_values]
        
        draw_ascii_chart(
            scaled_rss, 
            timestamps, 
            "Memory (RSS) History", 
            mem_unit, 
            height=8, 
            width=chart_width, 
            color=Colors.GREEN if use_color else "", 
            use_color=use_color,
            average=average
        )
    print()
