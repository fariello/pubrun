#!/usr/bin/env python3
"""Local, non-publishing startup and finalization breakdown benchmark for pubrun.

Measures import-only, auto-start, startup capture, workload, finalization,
subprocess spawn, serialization, and synchronization costs in fresh child
processes using Python standard library modules only (Python 3.8 through 3.14).

Usage:
    python benchmarks/startup_breakdown.py
    python benchmarks/startup_breakdown.py --passes 3 --iterations 15 --warmup 1
    python benchmarks/startup_breakdown.py --workdir /path/to/shared/tmp --out out.json
    python benchmarks/startup_breakdown.py --durability-policies fsync,finalize,atomic,strict
"""
from __future__ import annotations

import argparse
import copy
import getpass
import json
import math
import os
import platform
import shutil
import statistics
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

_HERE = Path(__file__).resolve().parent
_REPO_ROOT = _HERE.parent
_SRC_ROOT = _REPO_ROOT / "src"

if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))
if str(_SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(_SRC_ROOT))

import share_safety as _share_safety  # noqa: E402

SCHEMA_VERSION = "pubrun-startup-breakdown/1"
VALID_DURABILITY_POLICIES = ("default", "fsync", "finalize", "atomic", "strict")
_REDACTED = "<redacted>"
_PROBE_MARKER = "__PUBRUN_BREAKDOWN_JSON__:"
_CHILD_TIMEOUT_S = 120.0

_REDACT_KEYS = {
    "hostname",
    "username",
    "executable",
    "prefix",
    "base_prefix",
    "virtual_env",
    "python_executable",
    "path",
    "mount_point",
    "run_dir",
    "output_base_dir",
    "results_dir",
    "pubrun_install",
    "tmpdir",
    "workdir",
}
_REDACT_LIST_KEYS = {"sys_path", "source_files"}

# Standard manifest["timing"] keys that carry wall timestamps rather than
# additive phase/overhead breakdown metrics.
_TIMING_WALL_KEYS = {"started_at_utc", "ended_at_utc", "capture_state"}


# ---------------------------------------------------------------------------
# Statistics helpers (Python 3.8+ safe, small-n safe)
# ---------------------------------------------------------------------------

def _percentile(sorted_vals: Sequence[float], p: float) -> float:
    """Return linear-interpolated percentile (0.0 <= p <= 1.0) on non-empty sorted data."""
    n = len(sorted_vals)
    if n == 1:
        return float(sorted_vals[0])
    pos = p * (n - 1)
    lo = int(math.floor(pos))
    hi = min(n - 1, int(math.ceil(pos)))
    if lo == hi:
        return float(sorted_vals[lo])
    frac = pos - lo
    return float(sorted_vals[lo] + (sorted_vals[hi] - sorted_vals[lo]) * frac)


def compute_stats(samples_ms: Sequence[float], failures: int = 0) -> Dict[str, Any]:
    """Compute n, failures, median, mean, p95, stdev, and IQR in milliseconds."""
    s = sorted(float(x) for x in samples_ms)
    n = len(s)
    if n == 0:
        return {
            "n": 0,
            "failures": int(failures),
            "median_ms": None,
            "mean_ms": None,
            "p95_ms": None,
            "stdev_ms": None,
            "iqr_ms": None,
        }
    if n == 1:
        v = round(s[0], 3)
        return {
            "n": 1,
            "failures": int(failures),
            "median_ms": v,
            "mean_ms": v,
            "p95_ms": v,
            "stdev_ms": 0.0,
            "iqr_ms": 0.0,
        }
    q1 = _percentile(s, 0.25)
    q3 = _percentile(s, 0.75)
    return {
        "n": n,
        "failures": int(failures),
        "median_ms": round(statistics.median(s), 3),
        "mean_ms": round(statistics.fmean(s), 3),
        "p95_ms": round(_percentile(s, 0.95), 3),
        "stdev_ms": round(statistics.stdev(s), 3),
        "iqr_ms": round(q3 - q1, 3),
    }


# ---------------------------------------------------------------------------
# Environment metadata and strict redaction
# ---------------------------------------------------------------------------

def _git_head_sha(repo_root: Path) -> Optional[str]:
    try:
        proc = subprocess.run(
            ["git", "-C", str(repo_root), "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if proc.returncode == 0:
            sha = proc.stdout.strip()
            if sha:
                return sha
    except Exception:
        pass
    return None


def _has_ancestor_git(path: Path) -> bool:
    cur = path.resolve()
    for candidate in (cur,) + tuple(cur.parents):
        if (candidate / ".git").exists():
            return True
    return False


def _ensure_pubrun_minimal() -> None:
    """Import pubrun.minimal before any pubrun.* helper so the parent never auto-starts."""
    if "pubrun" not in sys.modules:
        import pubrun.minimal  # noqa: F401


def _capture_filesystem_summary(workdir: Path) -> Dict[str, Any]:
    """Capture fstype and is_network for workdir, tmpdir, and pubrun install.

    Never emits raw path or mount_point fields.
    """
    raw_paths = {
        "workdir": str(workdir),
        "tmpdir": tempfile.gettempdir(),
        "pubrun_install": str(_SRC_ROOT / "pubrun"),
    }
    summary: Dict[str, Any] = {}
    try:
        _ensure_pubrun_minimal()
        from pubrun.capture.filesystem import get_filesystem
        fs_data = get_filesystem({}, raw_paths)
        for label in ("workdir", "tmpdir", "pubrun_install"):
            entry = fs_data.get(label)
            if isinstance(entry, dict) and "fstype" in entry:
                summary[label] = {
                    "fstype": str(entry.get("fstype", "unknown")),
                    "is_network": bool(entry.get("is_network", False)),
                }
            else:
                state = entry.get("capture_state", {}) if isinstance(entry, dict) else {}
                summary[label] = {
                    "fstype": "unknown",
                    "is_network": False,
                    "status": str(state.get("status", "unavailable")),
                }
    except Exception:
        for label in ("workdir", "tmpdir", "pubrun_install"):
            summary[label] = {
                "fstype": "unknown",
                "is_network": False,
                "status": "unavailable",
            }
    return summary


def _capture_cpu_summary() -> Dict[str, Any]:
    model: Optional[str] = None
    try:
        _ensure_pubrun_minimal()
        from pubrun.capture.hardware import _get_cpu_model
        model = _get_cpu_model(timeout=2.0)
    except Exception:
        model = None
    return {
        "model": model or "unknown",
        "logical_cores": os.cpu_count(),
        "architecture": platform.machine() or "unknown",
    }


def _capture_pubrun_version() -> Optional[str]:
    try:
        from importlib.metadata import version as pkg_version
        return pkg_version("pubrun")
    except Exception:
        pass
    pyproject = _REPO_ROOT / "pyproject.toml"
    if pyproject.is_file():
        try:
            for line in pyproject.read_text(encoding="utf-8").splitlines():
                stripped = line.strip()
                if stripped.startswith("version") and "=" in stripped:
                    val = stripped.split("=", 1)[1].strip().strip('"').strip("'")
                    if val:
                        return val
        except Exception:
            pass
    return None


def _collect_redaction_needles(extra_needles: Sequence[str] = ()) -> List[str]:
    raw: List[str] = []
    try:
        node = platform.node()
        if node:
            raw.append(node)
            short_node = node.split(".", 1)[0]
            if short_node and len(short_node) >= 3:
                raw.append(short_node)
    except Exception:
        pass
    try:
        user = getpass.getuser()
        if user:
            raw.append(user)
    except Exception:
        pass
    for env_key in ("USER", "USERNAME", "LOGNAME"):
        val = os.environ.get(env_key)
        if val:
            raw.append(val)
    try:
        home = os.path.expanduser("~")
        if home and home != "~":
            raw.append(home)
            raw.append(str(Path(home).resolve()))
    except Exception:
        pass
    raw.append(str(_REPO_ROOT))
    raw.append(str(_REPO_ROOT.resolve()))
    for item in extra_needles:
        if item:
            raw.append(str(item))
            try:
                raw.append(str(Path(item).resolve()))
            except Exception:
                pass
    expanded: List[str] = []
    for needle in raw:
        if not needle:
            continue
        expanded.append(needle)
        if "\\" in needle:
            expanded.append(needle.replace("\\", "/"))
            expanded.append(needle.replace("\\", "\\\\"))
    # Longest first so full paths containing username or hostname scrub whole.
    unique = {n for n in expanded if n}
    return sorted(unique, key=len, reverse=True)


def _redact_keys_recursive(obj: Any) -> Any:
    if isinstance(obj, dict):
        out: Dict[str, Any] = {}
        for k, v in obj.items():
            if k in _REDACT_LIST_KEYS and isinstance(v, list):
                out[k] = [_REDACTED for _ in v]
            elif k in _REDACT_KEYS and isinstance(v, str):
                out[k] = _REDACTED
            else:
                out[k] = _redact_keys_recursive(v)
        return out
    if isinstance(obj, list):
        return [_redact_keys_recursive(x) for x in obj]
    return obj


def _scrub_substrings(obj: Any, needles: Sequence[str]) -> Any:
    if isinstance(obj, dict):
        return {k: _scrub_substrings(v, needles) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_scrub_substrings(x, needles) for x in obj]
    if isinstance(obj, str):
        s = obj
        for needle in needles:
            if needle and needle in s:
                s = s.replace(needle, _REDACTED)
        return s
    return obj


def redact_breakdown(
    result: Dict[str, Any],
    extra_needles: Sequence[str] = (),
) -> Dict[str, Any]:
    """Return a deeply redacted copy of a breakdown result dict."""
    needles = _collect_redaction_needles(extra_needles)
    redacted = _redact_keys_recursive(copy.deepcopy(result))
    scrubbed = _scrub_substrings(redacted, needles)
    return scrubbed if isinstance(scrubbed, dict) else redacted


def scrub_text(text: str, extra_needles: Sequence[str] = ()) -> str:
    """Scrub identifying needles from rendered Markdown text."""
    s = text
    for needle in _collect_redaction_needles(extra_needles):
        if needle and needle in s:
            s = s.replace(needle, _REDACTED)
    return s


def validate_redacted_output(
    result: Dict[str, Any],
    markdown_text: str = "",
    extra_needles: Sequence[str] = (),
) -> Tuple[bool, List[str]]:
    """Run share_safety.check_share_safe plus strict needle checks on JSON and Markdown."""
    ok, reasons = _share_safety.check_share_safe(result)
    issues = list(reasons)
    blob = json.dumps(result)
    needles = _collect_redaction_needles(extra_needles)

    # Check path/host/user needles (skip very short usernames that could be common substrings
    # in keys like 'os', while always checking full paths and hostnames >= 3 chars).
    for needle in needles:
        is_path = ("/" in needle) or ("\\" in needle)
        if not is_path and len(needle) < 3:
            continue
        if needle in blob:
            issues.append("identifying substring remains in JSON payload")
            break
    if markdown_text:
        if _share_safety._HOME_PATH_RE.search(markdown_text):
            issues.append("an absolute home or user-profile path is present in Markdown output")
        for needle in needles:
            is_path = ("/" in needle) or ("\\" in needle)
            if not is_path and len(needle) < 3:
                continue
            if needle in markdown_text:
                issues.append("identifying substring remains in Markdown output")
                break
    return (len(issues) == 0, issues)


# ---------------------------------------------------------------------------
# Ephemeral workspace, isolated layouts, and deterministic temp Git repos
# ---------------------------------------------------------------------------

def _init_git_repo(repo_dir: Path, add_origin: bool = True) -> None:
    """Initialize a small deterministic temporary Git repository."""
    repo_dir.mkdir(parents=True, exist_ok=True)
    (repo_dir / "README.txt").write_text("pubrun benchmark sample repo\n", encoding="utf-8")
    (repo_dir / ".gitignore").write_text("work_*/\n", encoding="utf-8")
    git_env = dict(os.environ)
    for key in list(git_env):
        if key.startswith("GIT_"):
            git_env.pop(key, None)
    git_env["GIT_AUTHOR_NAME"] = "pubrun-bench"
    git_env["GIT_AUTHOR_EMAIL"] = "bench@example.invalid"
    git_env["GIT_COMMITTER_NAME"] = "pubrun-bench"
    git_env["GIT_COMMITTER_EMAIL"] = "bench@example.invalid"

    commands = [
        ["git", "-C", str(repo_dir), "init", "-q"],
        ["git", "-C", str(repo_dir), "add", "README.txt", ".gitignore"],
        [
            "git",
            "-C",
            str(repo_dir),
            "-c",
            "commit.gpgsign=false",
            "commit",
            "-q",
            "-m",
            "init",
        ],
    ]
    if add_origin:
        commands.append(
            [
                "git",
                "-C",
                str(repo_dir),
                "remote",
                "add",
                "origin",
                "https://example.invalid/pubrun-bench/sample.git",
            ]
        )
    for cmd in commands:
        proc = subprocess.run(
            cmd,
            env=git_env,
            capture_output=True,
            text=True,
            timeout=30,
        )
        if proc.returncode != 0:
            raise RuntimeError(f"git setup failed ({' '.join(cmd)}): {proc.stderr.strip()}")


def _copy_installed_pubrun(dest_site_packages: Path, synthetic_commit: str) -> Path:
    """Copy src/pubrun into an isolated site-packages directory with synthetic COMMIT."""
    dest_pkg = dest_site_packages / "pubrun"
    shutil.copytree(
        _SRC_ROOT / "pubrun",
        dest_pkg,
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.pyo"),
    )
    (dest_pkg / "COMMIT").write_text(synthetic_commit + "\n", encoding="utf-8")
    return dest_pkg


def _build_isolated_env(
    site_root: Optional[Path],
    empty_config_home: Path,
) -> Dict[str, str]:
    """Build a child process environment stripped of PUBRUN_* and user config."""
    env = dict(os.environ)
    for key in list(env):
        if key.startswith("PUBRUN_") or key.startswith("GIT_"):
            env.pop(key, None)
    env["XDG_CONFIG_HOME"] = str(empty_config_home)
    env["APPDATA"] = str(empty_config_home)
    env["PYTHONNOUSERSITE"] = "1"

    # Strip any PYTHONPATH entry that already exposes a pubrun package.
    cleaned_parts: List[str] = []
    if site_root is not None:
        cleaned_parts.append(str(site_root))
    existing_pp = env.get("PYTHONPATH", "")
    if existing_pp:
        for entry in existing_pp.split(os.pathsep):
            if not entry:
                continue
            try:
                p = Path(entry)
                if (p / "pubrun").exists():
                    continue
            except Exception:
                pass
            if entry not in cleaned_parts:
                cleaned_parts.append(entry)
    if cleaned_parts:
        env["PYTHONPATH"] = os.pathsep.join(cleaned_parts)
    else:
        env.pop("PYTHONPATH", None)
    return env


def _layout_prelude_code(expected_site_root: Path) -> str:
    """Pure-sys prelude ensuring expected_site_root wins over any editable install."""
    site_str = repr(str(expected_site_root.resolve()))
    return (
        "import sys\n"
        f"_exp_site = {site_str}\n"
        "sys.meta_path = [f for f in sys.meta_path if 'Editable' not in type(f).__name__]\n"
        "if not sys.path or sys.path[0] != _exp_site:\n"
        "    sys.path.insert(0, _exp_site)\n"
    )


def _layout_verify_code(expected_pkg_root: Path) -> str:
    """Post-import guard confirming pubrun.__file__ lives under expected_pkg_root."""
    pkg_str = repr(str(expected_pkg_root.resolve()))
    return (
        "import pubrun as _ver_pkg\n"
        "from pathlib import Path as _VerPath\n"
        f"_exp_pkg = _VerPath({pkg_str}).resolve()\n"
        "_actual = _VerPath(_ver_pkg.__file__).resolve()\n"
        "try:\n"
        "    _actual.relative_to(_exp_pkg)\n"
        "except ValueError:\n"
        "    raise SystemExit(f'layout mismatch: {_actual} not under {_exp_pkg}')\n"
    )


def _write_policy_config(cwd: Path, policy: str) -> None:
    """Write .pubrun.toml for explicit durability policies; write nothing for 'default'."""
    cfg_path = cwd / ".pubrun.toml"
    if policy == "default":
        cfg_path.unlink(missing_ok=True)
        return
    cfg_path.write_text(
        f'[core]\nartifact_durability = "{policy}"\n',
        encoding="utf-8",
    )


# ---------------------------------------------------------------------------
# Child probe runners (clean timing vs phased timing vs instrumented counters)
# ---------------------------------------------------------------------------

def _run_clean_wall_once(argv: List[str], env: Dict[str, str], cwd: Path) -> Optional[float]:
    """Run one uninstrumented child process and return elapsed milliseconds or None."""
    t0 = time.perf_counter()
    try:
        proc = subprocess.run(
            argv,
            env=env,
            cwd=str(cwd),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            timeout=_CHILD_TIMEOUT_S,
        )
    except Exception:
        return None
    elapsed_ms = (time.perf_counter() - t0) * 1000.0
    if proc.returncode != 0:
        return None
    return elapsed_ms


def _build_import_clean_argv(
    module_name: str,
    expected_site_root: Path,
    expected_pkg_root: Path,
) -> List[str]:
    code = (
        _layout_prelude_code(expected_site_root)
        + f"import {module_name}\n"
        + _layout_verify_code(expected_pkg_root)
    )
    return [sys.executable, "-c", code]


def _build_auto_clean_argv(
    workload_path: Path,
    expected_site_root: Path,
    expected_pkg_root: Path,
) -> List[str]:
    w_str = repr(str(workload_path))
    code = (
        _layout_prelude_code(expected_site_root)
        + f"sys.argv = [{w_str}]\n"
        + "import pubrun\n"
        + _layout_verify_code(expected_pkg_root)
        + f"with open({w_str}, 'r', encoding='utf-8') as _wf:\n"
        + "    _src = _wf.read()\n"
        + f"exec(compile(_src, {w_str}, 'exec'), {{'__name__': '__main__', '__file__': {w_str}}})\n"
    )
    return [sys.executable, "-c", code]


def _build_phased_argv(
    workload_path: Path,
    expected_site_root: Path,
    expected_pkg_root: Path,
) -> List[str]:
    """Uninstrumented child probe timing import, startup, workload, and finalization."""
    w_str = repr(str(workload_path))
    marker = repr(_PROBE_MARKER)
    code = (
        _layout_prelude_code(expected_site_root)
        + f"sys.argv = [{w_str}]\n"
        + "import time as _t\n"
        + "with open(" + w_str + ", 'r', encoding='utf-8') as _wf:\n"
        + "    _wcode = compile(_wf.read(), " + w_str + ", 'exec')\n"
        + "_t0 = _t.perf_counter()\n"
        + "import pubrun.noauto as _pubrun\n"
        + "_t1 = _t.perf_counter()\n"
        + "_run = _pubrun.start()\n"
        + "_t2 = _t.perf_counter()\n"
        + "exec(_wcode, {'__name__': '__main__', '__file__': " + w_str + "})\n"
        + "_t3 = _t.perf_counter()\n"
        + "_pubrun.stop()\n"
        + "_t4 = _t.perf_counter()\n"
        + _layout_verify_code(expected_pkg_root)
        + "import json as _json\n"
        + "_manifest_timing = {}\n"
        + "try:\n"
        + "    _mpath = _run.run_dir / 'manifest.json'\n"
        + "    if _mpath.is_file():\n"
        + "        _mdata = _json.loads(_mpath.read_text(encoding='utf-8'))\n"
        + "        _tm = _mdata.get('timing', {})\n"
        + "        if isinstance(_tm, dict):\n"
        + "            for _k, _v in _tm.items():\n"
        + "                if isinstance(_v, (int, float)) and not isinstance(_v, bool):\n"
        + "                    _manifest_timing[_k] = _v\n"
        + "except Exception:\n"
        + "    pass\n"
        + "_payload = {\n"
        + "    'import_ms': (_t1 - _t0) * 1000.0,\n"
        + "    'startup_ms': (_t2 - _t1) * 1000.0,\n"
        + "    'workload_ms': (_t3 - _t2) * 1000.0,\n"
        + "    'finalization_ms': (_t4 - _t3) * 1000.0,\n"
        + "    'in_process_ms': (_t4 - _t0) * 1000.0,\n"
        + "    'manifest_timing': _manifest_timing,\n"
        + "}\n"
        + f"sys.__stdout__.write({marker} + _json.dumps(_payload) + '\\n')\n"
        + "sys.__stdout__.flush()\n"
    )
    return [sys.executable, "-c", code]


def _run_phased_once(
    argv: List[str],
    env: Dict[str, str],
    cwd: Path,
) -> Optional[Dict[str, Any]]:
    t0 = time.perf_counter()
    try:
        proc = subprocess.run(
            argv,
            env=env,
            cwd=str(cwd),
            capture_output=True,
            text=True,
            timeout=_CHILD_TIMEOUT_S,
        )
    except Exception:
        return None
    total_ms = (time.perf_counter() - t0) * 1000.0
    if proc.returncode != 0:
        return None
    for line in reversed(proc.stdout.splitlines()):
        if line.startswith(_PROBE_MARKER):
            try:
                data = json.loads(line[len(_PROBE_MARKER):])
                data["total_ms"] = total_ms
                return data
            except Exception:
                return None
    return None


def _run_instrumented_counter_probe(
    kind: str,
    env: Dict[str, str],
    cwd: Path,
    expected_site_root: Path,
    expected_pkg_root: Path,
    module_name: Optional[str] = None,
    workload_path: Optional[Path] = None,
) -> Dict[str, Any]:
    """Run a dedicated instrumented probe (outside timed samples) to collect exact counts.

    Wraps subprocess.Popen.__init__, os.replace, os.fsync, and json.dump/json.dumps
    (attributing serialization time to pubrun.writer).
    """
    setup_code = f"""
import atexit as _atexit
import json as _json
import os as _os
import subprocess as _sp
import sys
import threading as _th
import time as _t

_exp_site = {str(expected_site_root.resolve())!r}
sys.meta_path = [f for f in sys.meta_path if 'Editable' not in type(f).__name__]
if not sys.path or sys.path[0] != _exp_site:
    sys.path.insert(0, _exp_site)

_lock = _th.Lock()
_state = {{
    "phase": "import",
    "git_spawns": 0,
    "total_subprocesses": 0,
    "manifest_writes": 0,
    "manifest_writes_startup": 0,
    "manifest_writes_finalization": 0,
    "config_writes": 0,
    "config_writes_startup": 0,
    "config_writes_finalization": 0,
    "fsync_total": 0,
    "fsync_startup": 0,
    "fsync_finalization": 0,
    "fsync_ms": 0.0,
    "writer_json_calls": 0,
    "writer_json_ms": 0.0,
    "emitted": False,
}}

def _is_git_cmd(args):
    if isinstance(args, (list, tuple)) and args:
        head = _os.path.basename(str(args[0])).lower()
        return head in ("git", "git.exe")
    if isinstance(args, str):
        parts = args.strip().split()
        if parts:
            head = _os.path.basename(parts[0]).lower()
            return head in ("git", "git.exe")
    return False

_orig_popen_init = _sp.Popen.__init__
def _wrapped_popen_init(self, args, *a, **kw):
    with _lock:
        _state["total_subprocesses"] += 1
        if _is_git_cmd(args):
            _state["git_spawns"] += 1
    return _orig_popen_init(self, args, *a, **kw)
_sp.Popen.__init__ = _wrapped_popen_init

_orig_replace = _os.replace
def _wrapped_replace(src, dst, *a, **kw):
    res = _orig_replace(src, dst, *a, **kw)
    try:
        name = _os.path.basename(_os.fspath(dst))
    except Exception:
        name = ""
    with _lock:
        phase = _state["phase"]
        if name == "manifest.json":
            _state["manifest_writes"] += 1
            if phase == "finalization":
                _state["manifest_writes_finalization"] += 1
            else:
                _state["manifest_writes_startup"] += 1
        elif name == "config.resolved.json":
            _state["config_writes"] += 1
            if phase == "finalization":
                _state["config_writes_finalization"] += 1
            else:
                _state["config_writes_startup"] += 1
    return res
_os.replace = _wrapped_replace

_orig_fsync = _os.fsync
def _wrapped_fsync(fd):
    t0 = _t.perf_counter()
    res = _orig_fsync(fd)
    dt_ms = (_t.perf_counter() - t0) * 1000.0
    with _lock:
        _state["fsync_total"] += 1
        _state["fsync_ms"] += dt_ms
        if _state["phase"] == "finalization":
            _state["fsync_finalization"] += 1
        else:
            _state["fsync_startup"] += 1
    return res
_os.fsync = _wrapped_fsync

def _called_from_writer():
    try:
        f = sys._getframe(2)
        for _ in range(5):
            if f is None:
                break
            mod = f.f_globals.get("__name__", "")
            if mod == "pubrun.writer":
                return True
            f = f.f_back
    except Exception:
        pass
    return False

_orig_dump = _json.dump
def _wrapped_dump(*a, **kw):
    if _called_from_writer():
        t0 = _t.perf_counter()
        try:
            return _orig_dump(*a, **kw)
        finally:
            dt_ms = (_t.perf_counter() - t0) * 1000.0
            with _lock:
                _state["writer_json_calls"] += 1
                _state["writer_json_ms"] += dt_ms
    return _orig_dump(*a, **kw)
_json.dump = _wrapped_dump

_orig_dumps = _json.dumps
def _wrapped_dumps(*a, **kw):
    if _called_from_writer():
        t0 = _t.perf_counter()
        try:
            return _orig_dumps(*a, **kw)
        finally:
            dt_ms = (_t.perf_counter() - t0) * 1000.0
            with _lock:
                _state["writer_json_calls"] += 1
                _state["writer_json_ms"] += dt_ms
    return _orig_dumps(*a, **kw)
_json.dumps = _wrapped_dumps

def _emit_counters():
    with _lock:
        if _state["emitted"]:
            return
        _state["emitted"] = True
        out = {{
            "git_spawns": _state["git_spawns"],
            "total_subprocesses": _state["total_subprocesses"],
            "manifest_writes": _state["manifest_writes"],
            "manifest_writes_startup": _state["manifest_writes_startup"],
            "manifest_writes_finalization": _state["manifest_writes_finalization"],
            "config_writes": _state["config_writes"],
            "config_writes_startup": _state["config_writes_startup"],
            "config_writes_finalization": _state["config_writes_finalization"],
            "fsync_total": _state["fsync_total"],
            "fsync_startup": _state["fsync_startup"],
            "fsync_finalization": _state["fsync_finalization"],
            "fsync_ms": round(_state["fsync_ms"], 3),
            "writer_json_calls": _state["writer_json_calls"],
            "writer_json_ms": round(_state["writer_json_ms"], 3),
        }}
    sys.__stdout__.write({_PROBE_MARKER!r} + _orig_dumps(out) + "\\n")
    sys.__stdout__.flush()

_atexit.register(_emit_counters)
"""

    if kind == "import":
        assert module_name is not None
        body = (
            f"import {module_name}\n"
            + _layout_verify_code(expected_pkg_root)
            + "_emit_counters()\n"
        )
    elif kind == "auto":
        assert workload_path is not None
        w_str = repr(str(workload_path))
        body = (
            f"sys.argv = [{w_str}]\n"
            + "_state['phase'] = 'startup'\n"
            + "import pubrun\n"
            + _layout_verify_code(expected_pkg_root)
            + "_state['phase'] = 'workload'\n"
            + f"with open({w_str}, 'r', encoding='utf-8') as _wf:\n"
            + "    _src = _wf.read()\n"
            + f"exec(compile(_src, {w_str}, 'exec'), {{'__name__': '__main__', '__file__': {w_str}}})\n"
            + "_state['phase'] = 'finalization'\n"
        )
    elif kind == "phased":
        assert workload_path is not None
        w_str = repr(str(workload_path))
        body = (
            f"sys.argv = [{w_str}]\n"
            + "_state['phase'] = 'import'\n"
            + "import pubrun.noauto as _pubrun\n"
            + _layout_verify_code(expected_pkg_root)
            + "_state['phase'] = 'startup'\n"
            + "_pubrun.start()\n"
            + "_state['phase'] = 'workload'\n"
            + f"with open({w_str}, 'r', encoding='utf-8') as _wf:\n"
            + "    _src = _wf.read()\n"
            + f"exec(compile(_src, {w_str}, 'exec'), {{'__name__': '__main__', '__file__': {w_str}}})\n"
            + "_state['phase'] = 'finalization'\n"
            + "_pubrun.stop()\n"
            + "_emit_counters()\n"
        )
    else:
        raise ValueError(f"Unknown probe kind: {kind}")

    proc = subprocess.run(
        [sys.executable, "-c", setup_code + body],
        env=env,
        cwd=str(cwd),
        capture_output=True,
        text=True,
        timeout=_CHILD_TIMEOUT_S,
    )
    if proc.returncode != 0:
        raise RuntimeError(
            f"instrumented counter probe ({kind}) failed with exit code {proc.returncode}: "
            f"{proc.stderr.strip()}"
        )
    for line in reversed(proc.stdout.splitlines()):
        if line.startswith(_PROBE_MARKER):
            return json.loads(line[len(_PROBE_MARKER):])
    raise RuntimeError(f"instrumented counter probe ({kind}) emitted no counter payload")


# ---------------------------------------------------------------------------
# Main benchmark execution engine
# ---------------------------------------------------------------------------

def _pass_label(pass_no: int) -> str:
    return "cold" if pass_no == 1 else "warm"


def _aggregate_manifest_timing(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Summarize numeric additive manifest['timing'] fields across a pass when present."""
    by_key: Dict[str, List[float]] = {}
    for row in rows:
        tm = row.get("manifest_timing")
        if not isinstance(tm, dict):
            continue
        for k, v in tm.items():
            if k in _TIMING_WALL_KEYS:
                continue
            if isinstance(v, (int, float)) and not isinstance(v, bool):
                by_key.setdefault(k, []).append(float(v))
    if not by_key:
        return {}
    out: Dict[str, Any] = {}
    for k, vals in sorted(by_key.items()):
        out[k] = {
            "n": len(vals),
            "median": round(statistics.median(vals), 6),
        }
    return out


def run_breakdown(
    iterations: int = 15,
    passes: int = 3,
    warmup: int = 1,
    workdir: Optional[str] = None,
    durability_policies: Sequence[str] = ("default",),
) -> Dict[str, Any]:
    """Run the full startup and finalization breakdown and return a redacted result dict."""
    if iterations < 1:
        raise ValueError("--iterations must be >= 1")
    if passes < 1:
        raise ValueError("--passes must be >= 1")
    if warmup < 0:
        raise ValueError("--warmup must be >= 0")

    policies: List[str] = []
    for p in durability_policies:
        token = p.strip()
        if not token or token not in VALID_DURABILITY_POLICIES:
            raise ValueError(
                f"invalid durability policy {p!r}; valid choices: "
                + ", ".join(VALID_DURABILITY_POLICIES)
            )
        if token not in policies:
            policies.append(token)
    if not policies:
        raise ValueError("--durability-policies must name at least one valid policy")

    parent_dir: Optional[Path] = None
    extra_needles: List[str] = []
    if workdir is not None:
        parent_dir = Path(workdir)
        if parent_dir.exists() and not parent_dir.is_dir():
            raise ValueError(f"--workdir is not a directory: {workdir}")
        parent_dir.mkdir(parents=True, exist_ok=True)
        if not os.access(str(parent_dir), os.W_OK):
            raise ValueError(f"--workdir is not writable: {workdir}")
        raw_wd = str(parent_dir)
        if "/" in raw_wd or "\\" in raw_wd:
            extra_needles.append(raw_wd)
        extra_needles.append(str(parent_dir.resolve()))

    wall_start = time.perf_counter()
    noop_path = _HERE / "workloads" / "noop.py"
    cpu_burn_path = _HERE / "workloads" / "cpu_burn.py"

    with tempfile.TemporaryDirectory(
        prefix="pubrun-startup-bench-",
        dir=str(parent_dir) if parent_dir is not None else None,
    ) as td:
        ephemeral = Path(td)
        extra_needles.append(str(ephemeral))
        extra_needles.append(str(ephemeral.resolve()))

        empty_cfg_home = ephemeral / "empty_config_home"
        empty_cfg_home.mkdir(parents=True, exist_ok=True)

        # Layout 1: source checkout (<repo>/src/pubrun)
        checkout_site = _SRC_ROOT
        checkout_pkg = _SRC_ROOT / "pubrun"

        # Layout 2: isolated installed package outside any Git tree
        installed_site = ephemeral / "installed" / "site-packages"
        installed_pkg = _copy_installed_pubrun(
            installed_site,
            "1111111111111111111111111111111111111111",
        )
        installed_ancestor_git = _has_ancestor_git(installed_site)

        # Layout 3: installed package nested inside a temporary user Git repo
        nested_repo = ephemeral / "nested_repo"
        _init_git_repo(nested_repo, add_origin=True)
        nested_site = nested_repo / ".venv" / "site-packages"
        nested_pkg = _copy_installed_pubrun(
            nested_site,
            "2222222222222222222222222222222222222222",
        )

        # Deterministic temp Git repository for auto-start and phased scenarios
        sample_repo = ephemeral / "sample_repo"
        _init_git_repo(sample_repo, add_origin=True)

        # Neutral non-Git cwd for baseline and import-only probes
        neutral_cwd = ephemeral / "neutral_cwd"
        neutral_cwd.mkdir(parents=True, exist_ok=True)

        # Capture run context before measuring
        env_meta: Dict[str, Any] = {
            "os": {
                "system": platform.system(),
                "release": platform.release(),
                "platform": sys.platform,
            },
            "python_version": platform.python_version(),
            "cpu": _capture_cpu_summary(),
            "git_commit": _git_head_sha(_REPO_ROOT),
            "pubrun_version": _capture_pubrun_version(),
            "filesystem": _capture_filesystem_summary(ephemeral),
            "installed_layout_ancestor_git": installed_ancestor_git,
        }

        # Build declarative scenario execution plan
        scenario_specs: List[Dict[str, Any]] = [
            {
                "name": "bare-python-noop",
                "category": "baseline",
                "layout": "none",
                "workload": "noop.py",
                "durability_policy": None,
                "kind": "baseline",
                "argv": [sys.executable, str(noop_path)],
                "env": _build_isolated_env(None, empty_cfg_home),
                "cwd": neutral_cwd,
            },
            {
                "name": "bare-python-cpu-burn",
                "category": "baseline",
                "layout": "none",
                "workload": "cpu_burn.py",
                "durability_policy": None,
                "kind": "baseline",
                "argv": [sys.executable, str(cpu_burn_path)],
                "env": _build_isolated_env(None, empty_cfg_home),
                "cwd": neutral_cwd,
            },
        ]

        layouts = [
            ("checkout", checkout_site, checkout_pkg, neutral_cwd),
            ("installed", installed_site, installed_pkg, neutral_cwd),
            ("installed-nested", nested_site, nested_pkg, nested_repo),
        ]
        for mode_short, mod_name in (("minimal", "pubrun.minimal"), ("noauto", "pubrun.noauto")):
            for layout_name, site_root, pkg_root, cwd_dir in layouts:
                scenario_specs.append(
                    {
                        "name": f"import-{mode_short}-{layout_name}",
                        "category": "import",
                        "layout": layout_name,
                        "workload": "none",
                        "durability_policy": None,
                        "kind": "import",
                        "module_name": mod_name,
                        "site_root": site_root,
                        "pkg_root": pkg_root,
                        "argv": _build_import_clean_argv(mod_name, site_root, pkg_root),
                        "env": _build_isolated_env(site_root, empty_cfg_home),
                        "cwd": cwd_dir,
                    }
                )

        for policy in policies:
            for wl_label, wl_path in (("noop", noop_path), ("cpu-burn", cpu_burn_path)):
                auto_name = f"auto-{wl_label}-{policy}"
                auto_cwd = sample_repo / f"work_{auto_name}"
                auto_cwd.mkdir(parents=True, exist_ok=True)
                _write_policy_config(auto_cwd, policy)
                scenario_specs.append(
                    {
                        "name": auto_name,
                        "category": "auto",
                        "layout": "checkout",
                        "workload": wl_path.name,
                        "durability_policy": policy,
                        "kind": "auto",
                        "workload_path": wl_path,
                        "site_root": checkout_site,
                        "pkg_root": checkout_pkg,
                        "argv": _build_auto_clean_argv(wl_path, checkout_site, checkout_pkg),
                        "env": _build_isolated_env(checkout_site, empty_cfg_home),
                        "cwd": auto_cwd,
                    }
                )

                phased_name = f"phased-{wl_label}-{policy}"
                phased_cwd = sample_repo / f"work_{phased_name}"
                phased_cwd.mkdir(parents=True, exist_ok=True)
                _write_policy_config(phased_cwd, policy)
                scenario_specs.append(
                    {
                        "name": phased_name,
                        "category": "phased",
                        "layout": "checkout",
                        "workload": wl_path.name,
                        "durability_policy": policy,
                        "kind": "phased",
                        "workload_path": wl_path,
                        "site_root": checkout_site,
                        "pkg_root": checkout_pkg,
                        "argv": _build_phased_argv(wl_path, checkout_site, checkout_pkg),
                        "env": _build_isolated_env(checkout_site, empty_cfg_home),
                        "cwd": phased_cwd,
                    }
                )

        scenarios_out: Dict[str, Dict[str, Any]] = {}
        for spec in scenario_specs:
            scenarios_out[spec["name"]] = {
                "category": spec["category"],
                "layout": spec["layout"],
                "workload": spec["workload"],
                "durability_policy": spec["durability_policy"],
                "passes": [],
                "counters": None,
            }

        # Run Pass 1 (cold) through Pass N (warm)
        for pass_no in range(1, passes + 1):
            p_label = _pass_label(pass_no)
            for spec in scenario_specs:
                name = spec["name"]
                kind = spec["kind"]
                if kind == "phased":
                    rows: List[Dict[str, Any]] = []
                    failures = 0
                    for i in range(iterations + warmup):
                        sample = _run_phased_once(spec["argv"], spec["env"], spec["cwd"])
                        if sample is None:
                            failures += 1
                            continue
                        if i >= warmup:
                            rows.append(sample)
                    if not rows:
                        raise RuntimeError(
                            f"scenario '{name}' finished pass {pass_no} with 0 successful samples "
                            f"(failures={failures})"
                        )
                    total_stats = compute_stats([r["total_ms"] for r in rows], failures=failures)
                    phase_stats = {
                        "import": compute_stats([r["import_ms"] for r in rows], failures=failures),
                        "startup": compute_stats([r["startup_ms"] for r in rows], failures=failures),
                        "workload": compute_stats([r["workload_ms"] for r in rows], failures=failures),
                        "finalization": compute_stats([r["finalization_ms"] for r in rows], failures=failures),
                        "in_process": compute_stats([r["in_process_ms"] for r in rows], failures=failures),
                    }
                    entry: Dict[str, Any] = {
                        "pass": pass_no,
                        "label": p_label,
                        **total_stats,
                        "phases": phase_stats,
                    }
                    mt = _aggregate_manifest_timing(rows)
                    if mt:
                        entry["manifest_timing"] = mt
                    scenarios_out[name]["passes"].append(entry)
                else:
                    samples_ms: List[float] = []
                    failures = 0
                    for i in range(iterations + warmup):
                        dt_ms = _run_clean_wall_once(spec["argv"], spec["env"], spec["cwd"])
                        if dt_ms is None:
                            failures += 1
                            continue
                        if i >= warmup:
                            samples_ms.append(dt_ms)
                    if not samples_ms:
                        raise RuntimeError(
                            f"scenario '{name}' finished pass {pass_no} with 0 successful samples "
                            f"(failures={failures})"
                        )
                    stats = compute_stats(samples_ms, failures=failures)
                    scenarios_out[name]["passes"].append(
                        {
                            "pass": pass_no,
                            "label": p_label,
                            **stats,
                        }
                    )

        # Dedicated instrumented counter/serialization probes (outside timed samples)
        for spec in scenario_specs:
            name = spec["name"]
            kind = spec["kind"]
            if kind == "baseline":
                scenarios_out[name]["counters"] = {
                    "git_spawns": 0,
                    "total_subprocesses": 0,
                    "manifest_writes": 0,
                    "manifest_writes_startup": 0,
                    "manifest_writes_finalization": 0,
                    "config_writes": 0,
                    "config_writes_startup": 0,
                    "config_writes_finalization": 0,
                    "fsync_total": 0,
                    "fsync_startup": 0,
                    "fsync_finalization": 0,
                    "fsync_ms": 0.0,
                    "writer_json_calls": 0,
                    "writer_json_ms": 0.0,
                }
                continue
            counters = _run_instrumented_counter_probe(
                kind=kind,
                env=spec["env"],
                cwd=spec["cwd"],
                expected_site_root=spec["site_root"],
                expected_pkg_root=spec["pkg_root"],
                module_name=spec.get("module_name"),
                workload_path=spec.get("workload_path"),
            )
            scenarios_out[name]["counters"] = counters

        # Build short vs long workload overhead summary per durability policy
        overhead_summary: Dict[str, Any] = {}
        for policy in policies:
            policy_summary: Dict[str, Any] = {}
            for bucket, wl_label, base_name in (
                ("short", "noop", "bare-python-noop"),
                ("long", "cpu-burn", "bare-python-cpu-burn"),
            ):
                auto_name = f"auto-{wl_label}-{policy}"
                phased_name = f"phased-{wl_label}-{policy}"
                base_passes = scenarios_out[base_name]["passes"]
                auto_passes = scenarios_out[auto_name]["passes"]
                phased_passes = scenarios_out[phased_name]["passes"]
                pass_rows: List[Dict[str, Any]] = []
                for idx in range(passes):
                    b_med = base_passes[idx]["median_ms"]
                    a_med = auto_passes[idx]["median_ms"]
                    abs_ms: Optional[float] = None
                    rel_pct: Optional[float] = None
                    if b_med is not None and a_med is not None:
                        abs_ms = round(a_med - b_med, 3)
                        if b_med > 0:
                            rel_pct = round(((a_med - b_med) / b_med) * 100.0, 2)
                    p_phases = phased_passes[idx]["phases"]
                    pass_rows.append(
                        {
                            "pass": idx + 1,
                            "label": _pass_label(idx + 1),
                            "baseline_median_ms": b_med,
                            "auto_median_ms": a_med,
                            "absolute_overhead_ms": abs_ms,
                            "relative_overhead_pct": rel_pct,
                            "fixed_import_ms": p_phases["import"]["median_ms"],
                            "fixed_startup_ms": p_phases["startup"]["median_ms"],
                            "fixed_workload_ms": p_phases["workload"]["median_ms"],
                            "fixed_finalization_ms": p_phases["finalization"]["median_ms"],
                        }
                    )
                policy_summary[bucket] = {
                    "workload": scenarios_out[auto_name]["workload"],
                    "baseline_scenario": base_name,
                    "auto_scenario": auto_name,
                    "phased_scenario": phased_name,
                    "passes": pass_rows,
                }
            overhead_summary[policy] = policy_summary

        raw_result: Dict[str, Any] = {
            "schema": SCHEMA_VERSION,
            "generated_utc": datetime.now(timezone.utc).isoformat(),
            "generated_local": datetime.now().astimezone().isoformat(),
            "config": {
                "iterations": iterations,
                "passes": passes,
                "warmup": warmup,
                "durability_policies": policies,
                "custom_workdir": workdir is not None,
            },
            "environment": env_meta,
            "scenarios": scenarios_out,
            "overhead_summary": overhead_summary,
            "total_wall_time_s": round(time.perf_counter() - wall_start, 3),
        }

        redacted = redact_breakdown(raw_result, extra_needles=extra_needles)
        md_check = scrub_text(format_markdown_report(redacted), extra_needles=extra_needles)
        ok, reasons = validate_redacted_output(
            redacted,
            markdown_text=md_check,
            extra_needles=extra_needles,
        )
        if not ok:
            raise RuntimeError(
                "share-safety check failed on redacted output: " + "; ".join(reasons)
            )
        return redacted


# ---------------------------------------------------------------------------
# Concise redacted Markdown summary formatting
# ---------------------------------------------------------------------------

def _fmt_num(val: Optional[float], digits: int = 2) -> str:
    if val is None:
        return "-"
    return f"{val:.{digits}f}"


def format_markdown_report(result: Dict[str, Any]) -> str:
    """Format a concise redacted Markdown summary of a breakdown result."""
    env = result.get("environment", {})
    cfg = result.get("config", {})
    os_info = env.get("os", {})
    cpu_info = env.get("cpu", {})
    fs_info = env.get("filesystem", {})
    scenarios = result.get("scenarios", {})
    overhead = result.get("overhead_summary", {})

    lines: List[str] = [
        "# pubrun Startup and Finalization Breakdown",
        "",
        "## Environment",
        "",
        f"- Schema: `{result.get('schema')}`",
        f"- Generated (UTC): `{result.get('generated_utc')}`",
        f"- Git revision: `{env.get('git_commit')}`",
        f"- pubrun version: `{env.get('pubrun_version')}`",
        f"- OS: `{os_info.get('system')} {os_info.get('release')}` (`{os_info.get('platform')}`)",
        f"- Python: `{env.get('python_version')}`",
        f"- CPU: `{cpu_info.get('model')}` ({cpu_info.get('logical_cores')} logical cores, `{cpu_info.get('architecture')}`)",
        (
            f"- Repetitions: `{cfg.get('passes')}` pass(es) x `{cfg.get('iterations')}` "
            f"iterations (+`{cfg.get('warmup')}` warmup per pass)"
        ),
        f"- Durability policies: `{', '.join(cfg.get('durability_policies', []))}`",
        f"- Installed layout ancestor `.git` present: `{env.get('installed_layout_ancestor_git')}`",
    ]
    for fs_label in ("workdir", "tmpdir", "pubrun_install"):
        fse = fs_info.get(fs_label, {})
        lines.append(
            f"- Filesystem ({fs_label}): `{fse.get('fstype', 'unknown')}` "
            f"(network=`{fse.get('is_network', False)}`)"
        )
    lines.append("")

    # Table 1: End-to-end wall times per pass (Pass 1 cold through Pass N warm)
    lines.extend(
        [
            "## Scenario Wall-Clock Timings (ms)",
            "",
            "| Scenario | Pass | n | Fail | Median (ms) | Mean (ms) | p95 (ms) | Stdev (ms) | IQR (ms) |",
            "|---|---|---:|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for name, data in scenarios.items():
        for p in data.get("passes", []):
            lines.append(
                f"| `{name}` | {p['pass']} ({p['label']}) | {p['n']} | {p['failures']} | "
                f"{_fmt_num(p['median_ms'])} | {_fmt_num(p['mean_ms'])} | "
                f"{_fmt_num(p['p95_ms'])} | {_fmt_num(p['stdev_ms'])} | {_fmt_num(p['iqr_ms'])} |"
            )
    lines.append("")

    # Table 2: Phase breakdown for phased scenarios
    phased_items = [(n, d) for n, d in scenarios.items() if d.get("category") == "phased"]
    if phased_items:
        lines.extend(
            [
                "## Phase Breakdown (median / IQR in ms)",
                "",
                "| Scenario | Pass | Import (ms) | Startup (ms) | Workload (ms) | Finalization (ms) | In-Process (ms) |",
                "|---|---|---:|---:|---:|---:|---:|",
            ]
        )
        for name, data in phased_items:
            for p in data.get("passes", []):
                ph = p.get("phases", {})
                def _mi(key: str) -> str:
                    st = ph.get(key, {})
                    return f"{_fmt_num(st.get('median_ms'))} / {_fmt_num(st.get('iqr_ms'))}"
                lines.append(
                    f"| `{name}` | {p['pass']} ({p['label']}) | {_mi('import')} | "
                    f"{_mi('startup')} | {_mi('workload')} | {_mi('finalization')} | "
                    f"{_mi('in_process')} |"
                )
        lines.append("")

    # Table 3: Instrumented counters and serialization time
    lines.extend(
        [
            "## Instrumented Subprocess, Write, Synchronization, and Serialization Counters",
            "",
            "| Scenario | git spawns | total procs | manifest writes (S/F) | config writes (S/F) | fsync total (S/F) | fsync (ms) | writer JSON calls | writer JSON (ms) |",
            "|---|---:|---:|---|---|---|---:|---:|---:|",
        ]
    )
    for name, data in scenarios.items():
        c = data.get("counters") or {}
        if data.get("category") == "baseline":
            continue
        lines.append(
            f"| `{name}` | {c.get('git_spawns', 0)} | {c.get('total_subprocesses', 0)} | "
            f"{c.get('manifest_writes', 0)} ({c.get('manifest_writes_startup', 0)}/{c.get('manifest_writes_finalization', 0)}) | "
            f"{c.get('config_writes', 0)} ({c.get('config_writes_startup', 0)}/{c.get('config_writes_finalization', 0)}) | "
            f"{c.get('fsync_total', 0)} ({c.get('fsync_startup', 0)}/{c.get('fsync_finalization', 0)}) | "
            f"{_fmt_num(c.get('fsync_ms'))} | {c.get('writer_json_calls', 0)} | "
            f"{_fmt_num(c.get('writer_json_ms'))} |"
        )
    lines.append("")

    # Table 4: Short vs long workload overhead summary
    lines.extend(
        [
            "## Short vs Long Workload Overhead Summary",
            "",
            "| Policy | Workload | Pass | Baseline (ms) | Auto (ms) | Abs Overhead (ms) | Rel Overhead (%) | Import (ms) | Startup (ms) | Finalize (ms) |",
            "|---|---|---|---:|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for policy, buckets in overhead.items():
        for bucket in ("short", "long"):
            bdata = buckets.get(bucket, {})
            wl = bdata.get("workload", bucket)
            for row in bdata.get("passes", []):
                lines.append(
                    f"| `{policy}` | `{wl}` ({bucket}) | {row['pass']} ({row['label']}) | "
                    f"{_fmt_num(row.get('baseline_median_ms'))} | "
                    f"{_fmt_num(row.get('auto_median_ms'))} | "
                    f"{_fmt_num(row.get('absolute_overhead_ms'))} | "
                    f"{_fmt_num(row.get('relative_overhead_pct'), 1)}% | "
                    f"{_fmt_num(row.get('fixed_import_ms'))} | "
                    f"{_fmt_num(row.get('fixed_startup_ms'))} | "
                    f"{_fmt_num(row.get('fixed_finalization_ms'))} |"
                )
    lines.append("")
    lines.append(f"Total benchmark wall time: `{result.get('total_wall_time_s')}` s")
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    ap = argparse.ArgumentParser(
        description=(
            "Local, non-publishing startup and finalization overhead breakdown "
            "benchmark for pubrun."
        )
    )
    ap.add_argument(
        "--iterations",
        type=int,
        default=15,
        help="Measured iterations per scenario per pass (integer >= 1, default: 15).",
    )
    ap.add_argument(
        "--passes",
        type=int,
        default=3,
        help="Number of measured passes from Pass 1 (cold) to Pass N (warm) (integer >= 1, default: 3).",
    )
    ap.add_argument(
        "--warmup",
        type=int,
        default=1,
        help="Discarded warmup iterations before each pass (integer >= 0, default: 1).",
    )
    ap.add_argument(
        "--workdir",
        type=str,
        default=None,
        help=(
            "Optional parent directory for ephemeral benchmark files (useful for "
            "testing local storage vs a shared filesystem mount). Only a dedicated "
            "ephemeral subdirectory inside --workdir is created and removed."
        ),
    )
    ap.add_argument(
        "--durability-policies",
        type=str,
        default="default",
        help=(
            "Comma-separated subset of default,fsync,finalize,atomic,strict "
            "(default: default)."
        ),
    )
    ap.add_argument(
        "--out",
        type=str,
        default=None,
        help="Optional path to write the redacted JSON breakdown report.",
    )
    return ap.parse_args(argv)


def _validate_cli_args(args: argparse.Namespace) -> List[str]:
    if args.iterations < 1:
        raise ValueError("--iterations must be an integer >= 1")
    if args.passes < 1:
        raise ValueError("--passes must be an integer >= 1")
    if args.warmup < 0:
        raise ValueError("--warmup must be an integer >= 0")

    raw_policies = [p.strip() for p in args.durability_policies.split(",")]
    if not raw_policies or any(not p for p in raw_policies):
        raise ValueError(
            "--durability-policies must be a non-empty comma-separated list of: "
            + ", ".join(VALID_DURABILITY_POLICIES)
        )
    invalid = [p for p in raw_policies if p not in VALID_DURABILITY_POLICIES]
    if invalid:
        raise ValueError(
            f"invalid durability policy value(s): {', '.join(invalid)}; "
            f"valid choices: {', '.join(VALID_DURABILITY_POLICIES)}"
        )
    policies: List[str] = []
    for p in raw_policies:
        if p not in policies:
            policies.append(p)
    return policies


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    try:
        policies = _validate_cli_args(args)
        result = run_breakdown(
            iterations=args.iterations,
            passes=args.passes,
            warmup=args.warmup,
            workdir=args.workdir,
            durability_policies=policies,
        )
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    extra_needles: List[str] = []
    if args.workdir:
        if "/" in args.workdir or "\\" in args.workdir:
            extra_needles.append(args.workdir)
        extra_needles.append(str(Path(args.workdir).resolve()))
    md_text = scrub_text(format_markdown_report(result), extra_needles=extra_needles)
    ok, reasons = validate_redacted_output(
        result,
        markdown_text=md_text,
        extra_needles=extra_needles,
    )
    if not ok:
        print(
            "error: share-safety check failed; refusing to emit output: "
            + "; ".join(reasons),
            file=sys.stderr,
        )
        return 1

    if args.out:
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")

    sys.stdout.write(md_text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
