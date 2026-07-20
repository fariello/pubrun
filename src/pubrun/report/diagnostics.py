from __future__ import annotations
import json
from typing import Optional, Dict, Any
import os
import sys
from pathlib import Path
from datetime import datetime, timezone
from pubrun.report.utils import hydrate_manifest

# The section names `pubrun show <run> <section>` accepts as a bare trailing token.
# Single source of truth: the CLI shift heuristic, the argparse help, and the render
# branches below all reference this so the set cannot drift (it did before: it was
# duplicated as a literal in three places).
SHOW_SECTIONS = ("logs", "env", "packages")

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
    from pubrun.report import output as _out
    _out.error(message)


def read_resource_series(events_path) -> Dict[str, Any]:
    """Read per-sample resource series from an events.jsonl.

    Returns a dict with time-ordered lists: ``timestamps``, ``rss`` (main), ``cpu`` (main),
    ``tree_rss``, ``tree_cpu`` (present only when captured). Shared by the ``res``/``report``
    summary, the ASCII charts, and the TUI. Never raises; returns empty lists on any error.
    """
    out = {"timestamps": [], "rss": [], "cpu": [], "tree_rss": [], "tree_cpu": []}
    try:
        with open(events_path, "r", encoding="utf-8") as ef:
            for line in ef:
                try:
                    e = json.loads(line)
                    if e.get("type") != "resource_sample":
                        continue
                    p = e.get("payload", {})
                    ts = e.get("timestamp_utc")
                    rss = p.get("rss_bytes")
                    cpu = p.get("cpu_percent")
                    if ts is None or rss is None or cpu is None:
                        continue
                    out["timestamps"].append(ts)
                    out["rss"].append(rss)
                    out["cpu"].append(cpu)
                    if p.get("tree_rss_bytes") is not None:
                        out["tree_rss"].append(p["tree_rss_bytes"])
                    if p.get("tree_cpu_percent") is not None:
                        out["tree_cpu"].append(p["tree_cpu_percent"])
                except Exception:
                    continue
    except Exception:
        pass
    return out


def _series_stats(values):
    """(peak, avg, min) for a numeric series, or None if empty."""
    if not values:
        return None
    return (max(values), sum(values) / len(values), min(values))


def _sparkline(values, width: int = 40) -> str:
    """A tiny unicode sparkline for a numeric series (no color, no deps). Empty -> ''."""
    if not values:
        return ""
    bars = "▁▂▃▄▅▆▇█"
    lo = min(values)
    hi = max(values)
    span = (hi - lo) or 1.0
    # Downsample to width by simple bucketed max (keeps spikes visible).
    n = len(values)
    if n > width:
        step = n / width
        sampled = [max(values[int(i * step):int((i + 1) * step)] or [values[min(int(i * step), n - 1)]])
                   for i in range(width)]
    else:
        sampled = values
    return "".join(bars[min(len(bars) - 1, int((v - lo) / span * (len(bars) - 1)))] for v in sampled)


def format_resource_digest(series, width: int = 40) -> str:
    """Plain-text resource digest (summary lines + sparklines) for a run's per-sample series.

    ``series`` is the dict returned by :func:`read_resource_series`. Returns a multi-line
    string with peak/avg/min + a sparkline for each captured metric (main RSS/CPU and, when
    present, tree RSS/CPU). Used by the TUI resource view; pure, no textual/ANSI dependency,
    so it is unit-testable. Returns a clear message when there are no samples.
    """
    if not series or not series.get("timestamps"):
        return "No resource samples recorded for this run."

    def _mb(n):
        return f"{n / (1024**2):.1f} MB" if n < 1024**3 else f"{n / (1024**3):.2f} GB"

    lines = []

    def _row(title, values, fmt, unit=""):
        st = _series_stats(values)
        if not st:
            return
        pk, avg, mn = st
        lines.append(f"{title:<12} peak {fmt(pk)}{unit} / avg {fmt(avg)}{unit} / min {fmt(mn)}{unit}")
        spark = _sparkline(values, width)
        if spark:
            lines.append(f"             {spark}")

    _row("RSS (main)", series.get("rss", []), _mb)
    _row("CPU (main)", series.get("cpu", []), lambda v: f"{v:.1f}", "%")
    _row("RSS (tree)", series.get("tree_rss", []), _mb)
    _row("CPU (tree)", series.get("tree_cpu", []), lambda v: f"{v:.1f}", "%")
    return "\n".join(lines) if lines else "No resource samples recorded for this run."

def _supports_unicode(stream) -> bool:
    try:
        "┌".encode(getattr(stream, "encoding", "utf-8") or "utf-8")
        return True
    except UnicodeEncodeError:
        return False

def print_report(manifest_path: str, depth: str = "standard", section: Optional[str] = None,
                 utc: bool = False) -> None:
    """Print a human-readable diagnostic summary of a recorded run.

    Args:
        manifest_path: Path to the manifest.json file.
        depth: Verbosity level (``"basic"``, ``"standard"``, or ``"deep"``).
        section: Optional section to extract (``"logs"``, ``"env"``, or ``"packages"``).
        utc: Show timestamps in UTC instead of local time.
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
    dim = Colors.DIM if use_color else ""

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
        # Report-body warning (stays on stdout as part of the rendered report); label
        # normalized to the canonical [WARN ] prefix for consistency.
        print(f"\n{yellow}[WARN ]{rst} {w}")

    # Non-disruptive config notices recorded at run time (e.g. deprecated core.profile).
    for notice in manifest.get("config", {}).get("notices", []) or []:
        msg = notice.get("message", notice.get("code", "config notice"))
        print(f"\n{yellow}[WARN ]{rst} {msg}")

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

    from pubrun.status import _format_elapsed

    exit_str = ""
    if exit_code is not None:
        if exit_code == 0:
            code_color = Colors.BOLD + Colors.GREEN if use_color else ""
        else:
            code_color = Colors.BOLD + Colors.RED if use_color else ""
        exit_str = f" ({code_color}{exit_code}{rst})"

    print(f"{cyan}Run ID{rst}      : {run.get('run_id')}")
    print(f"{cyan}Script{rst}      : {script_name}")
    print(f"{cyan}Status{rst}      : {out_color}{outcome}{rst}{exit_str}")
    if exit_exception:
        print(f"{cyan}Exception{rst}   : {red}{exit_exception}{rst}")
    if signals_received:
        sig_names = [s.get("signal_name", f"SIG{s.get('signal')}") for s in signals_received]
        print(f"{cyan}Signals{rst}     : {yellow}{', '.join(sig_names)}{rst}")

    start_ts = timing.get('started_at_utc')
    if start_ts:
        _sdt = datetime.fromtimestamp(start_ts, tz=timezone.utc)
        if not utc:
            _sdt = _sdt.astimezone()
        start_str = _sdt.strftime("%Y-%m-%d %H:%M:%S")
    else:
        start_str = "unknown"
    print(f"{cyan}Started{rst}     : {start_str}")
    elapsed_val = timing.get("elapsed_seconds")
    if elapsed_val is not None:
        elapsed_str = _format_elapsed(elapsed_val)
        print(f"{cyan}Elapsed{rst}     : {elapsed_str}")

    # Read Events if available
    events_path = Path(manifest_path).parent / "events.jsonl"
    if events_path.exists():
        print(f"\n{blue}{bold}--- Event Timeline ---{rst}")
        try:
            from collections import deque
            with open(events_path, "r", encoding="utf-8") as ef:
                # Show ALL events when <= 20; otherwise the OLDEST 10 + NEWEST 10 with a
                # truncation marker between them.
                all_lines = ef.readlines()
                total_events = len(all_lines)
                if total_events > 20:
                    first_events = all_lines[:10]
                    last_events = all_lines[-10:]
                else:
                    first_events = all_lines
                    last_events = []

                def _print_ev(raw_line: str) -> None:
                    e = json.loads(raw_line)
                    ts = e.get('timestamp_utc', 0.0)
                    # Compact, human timestamp; honor UTC-vs-local like the rest of the report.
                    dt = datetime.fromtimestamp(ts, tz=timezone.utc)
                    if not utc:
                        dt = dt.astimezone()  # local time
                    ts_str = dt.strftime("%Y-%m-%d %H:%M:%S")
                    print(f"  [{cyan}{ts_str}{rst}] {green}{e.get('type')}{rst}: {e.get('name', '')} {e.get('payload', '')}")

                for line in first_events:
                    _print_ev(line)

                if total_events > 20:
                    print(f"  {dim}... [ {total_events - 20} events truncated ] ...{rst}")
                    for line in last_events:
                        _print_ev(line)
                del all_lines
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

    title_suffix = f" ({max_str})" if max_str else ""
    print(f"\n{bold}{title}{title_suffix}{rst}")

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
        tick_char = "┼" if _supports_unicode(sys.stdout) else "+"
        ticks_str[0] = tick_char
        ticks_str[-1] = tick_char
        ticks_str[(width - 1) // 2] = tick_char
        if width >= 8:
            ticks_str[(width - 1) // 4] = tick_char
            ticks_str[(3 * (width - 1)) // 4] = tick_char
    axis_line = "".join(ticks_str)
    print(f"  {' ' * 10} {corner}{axis_line}")

    from pubrun.status import _format_elapsed

    # Format dates
    t_start = timestamps[0]
    t_end = timestamps[-1]
    start_dt = datetime.fromtimestamp(t_start, tz=timezone.utc)
    end_dt = datetime.fromtimestamp(t_end, tz=timezone.utc)
    start_time_str = start_dt.strftime("%Y-%m-%d %H:%M:%S")
    end_time_str = end_dt.strftime("%Y-%m-%d %H:%M:%S")

    # Format elapsed durations
    duration = t_end - t_start
    elapsed_total_str = _format_elapsed(duration)
    start_elapsed_str = "0d 00:00:00" if "d " in elapsed_total_str else "00:00:00"

    # Build tick indices
    tick_indices = []
    if width > 0:
        tick_indices.append(0)
    if width > 1:
        if width >= 8:
            tick_indices.append((width - 1) // 4)
        tick_indices.append((width - 1) // 2)
        if width >= 8:
            tick_indices.append((3 * (width - 1)) // 4)
        tick_indices.append(width - 1)

    # Greedy placement of elapsed labels
    placed = {}  # maps idx -> (start_col, end_col, lbl_str)

    # Priority order: End tick, Start tick, Middle tick, then the rest
    priority_order = []
    if tick_indices:
        priority_order.append(tick_indices[-1])
        if tick_indices[0] not in priority_order:
            priority_order.append(tick_indices[0])
        mid_idx = tick_indices[len(tick_indices) // 2]
        if mid_idx not in priority_order:
            priority_order.append(mid_idx)
        for idx in tick_indices:
            if idx not in priority_order:
                priority_order.append(idx)

    for idx in priority_order:
        if idx == 0:
            lbl_str = start_elapsed_str
        else:
            lbl_str = _format_elapsed((idx / (width - 1)) * duration if width > 1 else 0.0)

        L = len(lbl_str)
        if idx == 0:
            start_col = 0
        elif idx == width - 1:
            start_col = width - L
        else:
            start_col = idx - 1 - (L // 2)

        start_col = max(0, min(width - L, start_col))

        # Check overlap with gap = 1
        overlap = False
        for p_start, p_end, _ in placed.values():
            if not (start_col + L + 1 <= p_start or p_end + 1 <= start_col):
                overlap = True
                break

        if not overlap:
            placed[idx] = (start_col, start_col + L, lbl_str)

    # Build elapsed row
    elapsed_row_list = [" "] * width
    for idx in placed:
        s_col, e_col, lbl_str = placed[idx]
        elapsed_row_list[s_col:e_col] = list(lbl_str)
    row2_vals = "".join(elapsed_row_list)

    # Row 1 (Timeline):
    spaces1 = width - len(start_time_str) - len(end_time_str)
    if spaces1 > 0:
        row1_vals = f"{start_time_str}{' ' * spaces1}{end_time_str}"
    else:
        row1_vals = f"{start_time_str} ... {end_time_str}"

    prefix1 = "  Timeline".ljust(13) + ": "
    prefix2 = "  Elapsed".ljust(13) + ": "
    print(f"{prefix1}{row1_vals}")
    print(f"{prefix2}{row2_vals}")


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

    def _fmt_bytes(n):
        try:
            n = float(n)
        except (TypeError, ValueError):
            return None
        if n >= 1024**3:
            return f"{n / (1024**3):.2f} GB"
        if n >= 1024**2:
            return f"{n / (1024**2):.2f} MB"
        return f"{n / 1024:.2f} KB"

    # Per-sample series (for avg/min/max). Read once here; reused for the charts below.
    _events_path = Path(manifest_path).parent / "events.jsonl"
    series = read_resource_series(_events_path) if _events_path.exists() else \
        {"timestamps": [], "rss": [], "cpu": [], "tree_rss": [], "tree_cpu": []}

    def _bytes_stat_line(values, peak_fallback):
        st = _series_stats(values)
        if st:
            pk, avg, mn = st
            return f"peak {_fmt_bytes(pk)} / avg {_fmt_bytes(avg)} / min {_fmt_bytes(mn)}"
        if peak_fallback:
            return f"peak {_fmt_bytes(peak_fallback)}"  # no per-sample data (short/old run)
        return None

    def _cpu_stat_line(values, peak_fallback):
        st = _series_stats(values)
        if st:
            pk, avg, mn = st
            return f"peak {pk:.1f}% / avg {avg:.1f}% / min {mn:.1f}%"
        if peak_fallback is not None:
            return f"peak {peak_fallback:.1f}%"
        return None

    # --- Main process: RSS + CPU (peak/avg/min from samples, peak fallback otherwise) ---
    if metric in ("mem", "all"):
        line = _bytes_stat_line(series["rss"], peak_rss)
        if line:
            print(f"{cyan}RSS (main){rst}   : {line}")
        if end_rss:
            print(f"{cyan}End RSS{rst}      : {_fmt_bytes(end_rss)}")

    if metric in ("cpu", "all"):
        line = _cpu_stat_line(series["cpu"], peak_cpu)
        if line:
            print(f"{cyan}CPU (main){rst}   : {line}")

    # Comprehensive resource view (only for `pubrun res`; cpu/mem stay single-metric).
    # Each field is rendered only when present, so older manifests just show less.
    if metric == "all":
        # Process-tree RSS + CPU (when scope=tree). Explicit "(tree)" labels so the reader
        # is never misled into thinking the main-process numbers are the whole tree.
        tree_line = _bytes_stat_line(series["tree_rss"], resources.get("peak_tree_rss_bytes"))
        if tree_line:
            print(f"{cyan}RSS (tree){rst}   : {tree_line}")
        tree_cpu_line = _cpu_stat_line(series["tree_cpu"], resources.get("peak_tree_cpu_percent"))
        if tree_cpu_line:
            print(f"{cyan}CPU (tree){rst}   : {tree_cpu_line} {yellow}(% of one core; may exceed 100%){rst}")

        # System memory (free/available) at start and worst point.
        sysmem = resources.get("system_memory")
        if isinstance(sysmem, dict):
            start = sysmem.get("start") or {}
            worst = sysmem.get("min_available") or {}
            avail = start.get("available_bytes")
            total = start.get("total_bytes")
            if avail is not None and total:
                print(f"{cyan}System RAM{rst}   : {_fmt_bytes(avail)} available of "
                      f"{_fmt_bytes(total)} at start")
            worst_avail = worst.get("available_bytes")
            if worst_avail is not None:
                print(f"{cyan}Min Avail RAM{rst}: {_fmt_bytes(worst_avail)} (lowest during run)")

        # Load average (start / max 1-min).
        load = resources.get("load_average")
        if isinstance(load, dict):
            start_l = (load.get("start") or {}).get("1min")
            max_l = load.get("max_1min")
            parts = []
            if start_l is not None:
                parts.append(f"{start_l:.2f} at start")
            if max_l is not None:
                parts.append(f"{max_l:.2f} peak (1-min)")
            if parts:
                print(f"{cyan}Load Average{rst} : {', '.join(parts)}")

        # Node iowait (labeled node-wide / indicative only).
        iowait = resources.get("system_iowait_pct")
        if isinstance(iowait, dict):
            mx = iowait.get("max")
            if mx is not None:
                print(f"{cyan}Node iowait{rst}  : {mx}% peak {yellow}(node-wide, indicative only){rst}")

        # Per-process I/O byte volume (this run), from /proc/self/io.
        io = resources.get("io_counters")
        if isinstance(io, dict):
            delta = io.get("delta") or {}
            rb = delta.get("read_bytes")
            wb = delta.get("write_bytes")
            rc = delta.get("rchar")
            wc = delta.get("wchar")
            if rb is not None or wb is not None:
                print(f"{cyan}Disk I/O{rst}     : read {_fmt_bytes(rb or 0)}, "
                      f"wrote {_fmt_bytes(wb or 0)} (storage layer)")
            if rc is not None or wc is not None:
                print(f"{cyan}Logical I/O{rst}  : read {_fmt_bytes(rc or 0)}, "
                      f"wrote {_fmt_bytes(wc or 0)} (incl. cache)")

    if not _events_path.exists():
        print(f"\n{yellow}No events.jsonl file found. Cannot generate utilization graphs.{rst}\n")
        return

    # Reuse the series already read for the summary above (single read of events.jsonl).
    timestamps = list(series["timestamps"])
    rss_values = list(series["rss"])
    cpu_values = list(series["cpu"])
    if not timestamps:
        print(f"\n{yellow}No resource samples found in events.jsonl.{rst}\n")
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

    # Scope label: the RSS/CPU samples are for the MAIN process unless the run
    # was recorded in "tree" scope. Make the chart title explicit so a reader
    # isn't misled into thinking a thin orchestrator's RSS is the whole tree.
    _scope = manifest.get("resources", {}).get("scope", "process")
    _scope_label = "process tree" if _scope == "tree" else "main process"

    # Plot CPU (Yellow theme). CPU% is always measured for the main process
    # (child CPU is excluded from the metric), regardless of RSS scope.
    if metric in ("cpu", "all"):
        draw_ascii_chart(
            cpu_values,
            timestamps,
            "CPU Utilization History (main process)",
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
            f"Memory (RSS) History ({_scope_label})",
            mem_unit,
            height=8,
            width=chart_width,
            color=Colors.GREEN if use_color else "",
            use_color=use_color,
            average=average
        )
    print()
