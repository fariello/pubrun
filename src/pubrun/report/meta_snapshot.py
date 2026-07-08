import sys
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
    import time
    from pubrun.report import output as _out
    _out.info(f"Analyzing global environment context (depth: {depth})...", stream=sys.stdout)
    # Resolve config with explicit overrides for global mode
    cfg = resolve_config({
        "core": {"profile": depth},
        "capture": {"packages": {"mode": "full-environment"}}
    })

    # 1. Capture each section, timed, itemizing what was gathered and its outcome.
    #    A section whose capture_state.status != "complete" is surfaced as [WARN ].
    def _gather(label, fn, summary_fn):
        t = time.perf_counter()
        try:
            data = fn(cfg)
        except Exception as e:
            _out.warn(f"{label}: capture failed ({type(e).__name__}: {e})", stream=sys.stdout)
            return {"capture_state": {"status": "failed", "detail": str(e)}}
        dt = time.perf_counter() - t
        state = (data.get("capture_state") or {}).get("status") if isinstance(data, dict) else None
        summary = summary_fn(data)
        line = f"{label}: {summary} ({dt*1000:.0f} ms)"
        if state and state != "complete":
            _out.warn(f"{line} — capture_state={state}", stream=sys.stdout)
        else:
            _out.ok(line, stream=sys.stdout)
        return data

    t0 = time.perf_counter()
    hardware = _gather("hardware", get_hardware,
                       lambda d: (d.get("cpu", {}) or {}).get("model", "unknown"))
    python_env = _gather("python", get_python_runtime,
                         lambda d: f"v{(d.get('version','') or 'unknown').split()[0]} ({d.get('environment_kind','?')})")
    packages = _gather("packages", get_packages,
                       lambda d: f"{len(d.get('records', []))} recorded dependencies")
    git_track = _gather("git", get_git,
                        lambda d: d.get("commit") or "no tracked repository")
    sys_env = _gather("environment", get_environment,
                      lambda d: f"{len(d.get('variables', []))} variables")
    host_env = _gather("host", get_host,
                       lambda d: f"{d.get('hostname','?')} / {d.get('os_name','?')}")
    total = time.perf_counter() - t0

    now_ts = time.time()
    meta_json = {
        "manifest_type": "pubrun-meta-snapshot",
        "timing": {"started_at_utc": now_ts},
        "hardware": hardware,
        "python": python_env,
        "packages": packages,
        "git": git_track,
        "environment": sys_env,
        "host": host_env
    }

    # Drop to file (the JSON remains the source of truth; the console is a readable digest).
    out_target = Path(output_path) if output_path else Path.cwd() / "runs" / "meta.json"
    out_target.parent.mkdir(parents=True, exist_ok=True)
    with open(out_target, "w", encoding="utf-8") as f:
        json.dump(meta_json, f, indent=2)

    _out.ok(f"Meta snapshot saved to: {out_target}", stream=sys.stdout)
    print(f"\nGathered 6 environment sections in {total:.2f}s.")
