import json
import math
import os
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional, Set
from pubrun.config import resolve_config
from pubrun.capture.python_runtime import get_python_runtime
from pubrun.capture.packages import get_packages
from pubrun.capture.environment import get_environment
from pubrun.capture.git import get_git
from pubrun.capture.hardware import get_hardware
from pubrun.capture.host import get_host


def _sanitize_json_value(value: Any, _seen: Optional[Set[int]] = None) -> Any:
    """Recursively replace non-finite floats (NaN/Inf/-Inf) with ``None``."""
    if isinstance(value, float):
        return None if not math.isfinite(value) else value
    if isinstance(value, dict):
        obj_id = id(value)
        seen = set() if _seen is None else _seen
        if obj_id in seen:
            raise ValueError("Circular reference detected")
        seen.add(obj_id)
        try:
            return {
                ("null" if isinstance(k, float) and not math.isfinite(k) else k): _sanitize_json_value(v, seen)
                for k, v in value.items()
            }
        finally:
            seen.discard(obj_id)
    if isinstance(value, list):
        obj_id = id(value)
        seen = set() if _seen is None else _seen
        if obj_id in seen:
            raise ValueError("Circular reference detected")
        seen.add(obj_id)
        try:
            return [_sanitize_json_value(item, seen) for item in value]
        finally:
            seen.discard(obj_id)
    if isinstance(value, tuple):
        obj_id = id(value)
        seen = set() if _seen is None else _seen
        if obj_id in seen:
            raise ValueError("Circular reference detected")
        seen.add(obj_id)
        try:
            return tuple(_sanitize_json_value(item, seen) for item in value)
        finally:
            seen.discard(obj_id)
    return value

_DEPTH_CAPTURE_OVERRIDES = {
    "basic": {
        "hardware": {"depth": "basic", "capture_gpu_clock_speed": False},
        "git": {"enabled": True, "depth": "basic", "check_dirty": False},
        "environment": {"mode": "off", "depth": "off"},
        "packages": {"mode": "off", "depth": "off"},
        "host": {"enabled": True, "depth": "basic"},
        "python": {"depth": "basic"},
    },
    "standard": {
        "hardware": {"depth": "standard", "capture_gpu_clock_speed": False},
        "git": {"enabled": True, "depth": "standard", "check_dirty": True},
        "environment": {"mode": "filtered", "depth": "standard"},
        "packages": {"mode": "top-level-installed", "depth": "standard"},
        "host": {"enabled": True, "depth": "standard"},
        "python": {"depth": "standard"},
    },
    "deep": {
        "hardware": {"depth": "deep", "capture_gpu_clock_speed": True},
        "git": {"enabled": True, "depth": "deep", "check_dirty": True},
        # "filtered", never "full": the snapshot is shared with child runs, so secrets
        # must stay redacted even at the deepest level.
        "environment": {"mode": "filtered", "depth": "deep"},
        "packages": {"mode": "full-environment", "depth": "deep"},
        "host": {"enabled": True, "depth": "deep"},
        "python": {"depth": "deep"},
    },
}


def generate_meta_snapshot(output_path: str, depth: str) -> None:
    """Generate a standalone environment snapshot for HPC parent-child hydration.

    Args:
        output_path: Target JSON file path.
        depth: Profiling depth (``"basic"``, ``"standard"``, ``"deep"``).

    Raises:
        ValueError: If ``depth`` is not one of the supported values.
    """
    import copy
    import time
    from pubrun.report import output as _out
    if depth not in _DEPTH_CAPTURE_OVERRIDES:
        raise ValueError(
            f"invalid meta snapshot depth {depth!r}; expected one of "
            f"{', '.join(_DEPTH_CAPTURE_OVERRIDES)}"
        )
    _out.info(f"Analyzing global environment context (depth: {depth})...", stream=sys.stdout)
    cfg = resolve_config({"capture": copy.deepcopy(_DEPTH_CAPTURE_OVERRIDES[depth])})

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
        if state == "suppressed":
            # Deliberately off at this depth: informational, not a problem.
            _out.info(f"{line} — capture_state={state}", stream=sys.stdout)
        elif state and state != "complete":
            _out.warn(f"{line} — capture_state={state}", stream=sys.stdout)
        else:
            _out.ok(line, stream=sys.stdout)
        return data

    t0 = time.perf_counter()
    hardware = _gather("hardware", get_hardware,
                       lambda d: (d.get("cpu", {}) or {}).get("model") or "unknown")
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

    # Drop to file atomically (the JSON remains the source of truth; the console is a readable digest).
    out_target = Path(output_path) if output_path else Path.cwd() / "runs" / "meta.json"
    out_target.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = out_target.parent / f".{out_target.name}.{os.getpid()}.{uuid.uuid4().hex[:8]}.tmp"
    sanitized = _sanitize_json_value(meta_json)
    try:
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(sanitized, f, indent=2, allow_nan=False)
            f.flush()
            os.fsync(f.fileno())
        for _attempt in range(10 if os.name == "nt" else 1):
            try:
                os.replace(str(tmp_path), str(out_target))
                break
            except PermissionError:
                if os.name != "nt" or _attempt == 9:
                    raise
                time.sleep(0.005 * (_attempt + 1))
    finally:
        try:
            tmp_path.unlink(missing_ok=True)
        except OSError:
            pass

    _out.ok(f"Meta snapshot saved to: {out_target}", stream=sys.stdout)
    print(f"\nGathered 6 environment sections in {total:.2f}s.")
    resolved_target = out_target.resolve()
    parent_toml = json.dumps(str(resolved_target.parent))
    print("\nNext steps:")
    print("  1. Set PUBRUN_META_REF before importing pubrun in child jobs:")
    print(f'     export PUBRUN_META_REF="{resolved_target}"')
    print("  2. If meta.json lives outside a run directory, add this to .pubrun.toml:")
    print("     [report]")
    print(f"     meta_ref_allowed_dirs = [{parent_toml}]")
