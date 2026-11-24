"""Environment / provenance checks shared by ``pubrun self-check`` and ``pubrun inspect``.

Pure, printing-free functions that produce *findings* — small dicts of the form
``{"severity": ..., "code": ..., "message": ..., "suggestion": ...}`` — from either the
LIVE environment (``live_findings``) or a COMPLETED run's manifest
(``manifest_findings``). The two commands overlap but neither is a subset of the other:
``self-check`` inspects the current machine (has no manifest); ``inspect`` inspects a
finished run (has no live re-check unless it happens to be the same host). Both share this
module's filesystem/RAM/load classification and formatting helpers.

IMPORTANT: this module is imported ONLY by ``pubrun.__main__`` (the CLI), NEVER by
``pubrun/__init__`` or the run path, so it cannot affect a user's ``import pubrun`` script.
There is a test pinning that ``import pubrun`` does not import ``pubrun.report.checks``.

Nothing here mutates the environment or any run. Report-only.
"""
import os
import sys
import shutil
from typing import Dict, Any, List, Optional

from pubrun.report.reproducibility import (
    assess_manifest_reproducibility,
    assess_run,
    should_fail_strict,
)

# Severity levels (textual, authoritative — color is optional reinforcement only).
INFO = "info"
WARN = "warn"

# Python versions pubrun supports (mirror pyproject requires-python = ">=3.8").
_MIN_PY = (3, 8)


def _finding(severity: str, code: str, message: str, suggestion: Optional[str] = None) -> Dict[str, Any]:
    return {"severity": severity, "code": code, "message": message, "suggestion": suggestion}


# --------------------------------------------------------------------------- live checks

def _live_paths() -> Dict[str, str]:
    """The paths self-check cares about: pubrun install dir, output dir, tmpdir, cwd."""
    import tempfile
    paths: Dict[str, str] = {"tmpdir": tempfile.gettempdir(), "cwd": os.getcwd(),
                             "python_prefix": sys.base_prefix}
    try:
        import pubrun
        pkg_file = getattr(pubrun, "__file__", None)
        if pkg_file:
            paths["pubrun_install"] = str(os.path.dirname(os.path.realpath(pkg_file)))
    except Exception:
        pass
    try:
        from pubrun.config import resolve_config
        base = resolve_config().get("core", {}).get("output_dir", "")
        paths["output_dir"] = base or os.path.join(os.getcwd(), "runs")
    except Exception:
        paths["output_dir"] = os.path.join(os.getcwd(), "runs")
    return paths


def _network_fs_findings(fs_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    findings: List[Dict[str, Any]] = []
    _human = {
        "pubrun_install": ("pubrun is installed on a network filesystem",
                           "Consider a node-local venv (e.g. on local scratch / $TMPDIR) or "
                           "`pip install --target` to local disk; import/startup over NFS/Lustre "
                           "can be markedly slower."),
        "output_dir": ("the run output directory is on a network filesystem",
                       "Consider setting `[core].output_dir` to node-local storage and copying "
                       "results back afterward; pubrun writes to this dir throughout a run."),
        "tmpdir": ("$TMPDIR is on a network filesystem",
                   "Point $TMPDIR at node-local storage for faster temp I/O."),
    }
    for label, entry in fs_data.items():
        if label == "capture_state" or not isinstance(entry, dict):
            continue
        if entry.get("is_network"):
            title, sugg = _human.get(label, (f"{label} is on a network filesystem", None))
            mp = entry.get("mount_point", entry.get("path", "?"))
            ft = entry.get("fstype", "?")
            findings.append(_finding(WARN, f"netfs_{label}",
                                     f"{title} ({mp}, {ft}).", sugg))
    return findings


def _live_fs_health_findings(fs_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """WARN on wedged (hung/pending) or slow live probes — a SYSTEM-WIDE hazard, worded
    honestly (affects any script, not just pubrun; magnitude only stated when measured)."""
    findings: List[Dict[str, Any]] = []
    _label = {"tmpdir": "$TMPDIR", "output_dir": "the run output directory",
              "pubrun_install": "the pubrun install", "python_prefix": "the Python install"}
    for label, entry in fs_data.items():
        if label == "capture_state" or not isinstance(entry, dict):
            continue
        live = entry.get("live")
        if not isinstance(live, dict):
            continue
        where = _label.get(label, label)
        mp = entry.get("mount_point", entry.get("path", "?"))
        ft = entry.get("fstype", "?")
        status = live.get("status")
        if status == "pending" or live.get("hung"):
            findings.append(_finding(
                WARN, f"fs_hung_{label}",
                f"a capacity probe of {where} ({mp}, {ft}) did not return within the check "
                f"(still pending after {live.get('waited_s', '?')}s).",
                "This mount appears wedged/very slow. Any script doing I/O here — not just "
                "pubrun — is likely to stall; use node-local storage or a healthy mount."))
        elif status == "complete" and live.get("slow"):
            findings.append(_finding(
                WARN, f"fs_slow_{label}",
                f"a capacity probe of {where} ({mp}, {ft}) took {live.get('elapsed_s')}s to "
                f"return.",
                "I/O on this mount is likely slow for any script, not just pubrun; prefer "
                "node-local storage for temp/output."))
    return findings


def _config_file_findings() -> List[Dict[str, Any]]:
    """WARN for each config file ``resolve_config()`` would load that fails to parse."""
    findings: List[Dict[str, Any]] = []
    try:
        from pathlib import Path
        from pubrun.config import get_global_config_dir, tomllib
        candidates = [
            get_global_config_dir() / "config.toml",
            Path.cwd() / ".config" / "pubrun" / "config.toml",
            Path.cwd() / ".pubrun.toml",
        ]
    except Exception:
        return findings
    for path in candidates:
        try:
            if not path.is_file():
                continue
        except OSError:
            continue
        try:
            tomllib.loads(path.read_text(encoding="utf-8"))
        except (tomllib.TOMLDecodeError, OSError, UnicodeDecodeError) as e:
            findings.append(_finding(
                WARN, "config_invalid",
                f"pubrun config file {path} could not be parsed and is being ignored: "
                f"{type(e).__name__}: {e}",
                f"Fix the TOML syntax in `{path}` (or remove the file)."))
    return findings


def _install_health_findings() -> List[Dict[str, Any]]:
    findings: List[Dict[str, Any]] = []

    # Python version support.
    if sys.version_info < _MIN_PY:
        findings.append(_finding(
            WARN, "python_version",
            f"Python {sys.version_info.major}.{sys.version_info.minor} is below pubrun's "
            f"minimum supported {_MIN_PY[0]}.{_MIN_PY[1]}.",
            "Upgrade Python to a supported version."))

    # Config file validity. resolve_config() deliberately tolerates malformed TOML (it logs
    # and skips the file so a user's script never breaks), so parse each config file it
    # would load explicitly here; otherwise a broken file passes self-check silently.
    findings.extend(_config_file_findings())
    try:
        from pubrun.config import resolve_config
        resolve_config()
    except Exception as e:
        findings.append(_finding(
            WARN, "config_invalid",
            f"pubrun configuration could not be resolved cleanly: {type(e).__name__}: {e}",
            "Check your `.pubrun.toml` for syntax/schema errors."))

    # Output dir writability.
    try:
        base = _live_paths().get("output_dir", "")
        if base:
            base = os.path.abspath(base)
            parent = base if os.path.isdir(base) else os.path.dirname(base)
        else:
            parent = os.getcwd()
        # Walk up to the nearest existing ancestor to test writability without creating dirs.
        # dirname() is a fixed point at a filesystem root (including a nonexistent Windows
        # drive), so stop there rather than looping forever.
        probe = parent
        while probe and not os.path.exists(probe):
            next_probe = os.path.dirname(probe)
            if next_probe == probe:
                probe = ""
                break
            probe = next_probe
        if not probe or not os.access(probe, os.W_OK):
            findings.append(_finding(
                WARN, "output_not_writable",
                f"the run output location ({base}) is not writable.",
                "Point `[core].output_dir` somewhere writable, or fix permissions."))
    except Exception:
        pass

    # git availability (git capture degrades gracefully, but flag it as info).
    if shutil.which("git") is None:
        findings.append(_finding(
            INFO, "git_missing",
            "`git` was not found on PATH; source-code state capture will be limited.",
            "Install git if you want commit/branch/dirty-state provenance."))

    return findings


def live_findings() -> List[Dict[str, Any]]:
    """Findings about the CURRENT machine (for ``pubrun self-check``). Never raises."""
    findings: List[Dict[str, Any]] = []
    try:
        from pubrun.capture.filesystem import get_filesystem, probe_paths_live
        fs_data = get_filesystem({}, _live_paths())
        findings.extend(_network_fs_findings(fs_data))
        # Live probe (diagnostic context — self-check is invoked deliberately, never the
        # import path). Surfaces wedged/slow mounts as a system-wide hazard.
        try:
            probe_paths_live(fs_data)
            findings.extend(_live_fs_health_findings(fs_data))
        except Exception:
            pass
    except Exception:
        pass

    # Low free memory (best-effort, Linux).
    try:
        from pubrun.capture.system_metrics import get_system_memory, get_load_average
        mem = get_system_memory()
        if mem and mem.get("total_bytes") and mem.get("available_bytes") is not None:
            frac = mem["available_bytes"] / mem["total_bytes"]
            if frac < 0.10:
                findings.append(_finding(
                    WARN, "low_memory",
                    f"only {frac*100:.0f}% of system RAM is available "
                    f"({mem['available_bytes'] // (1024*1024)} MiB free).",
                    "Free memory or request more before a large run; low RAM causes swapping."))
        load = get_load_average()
        cores = os.cpu_count() or 1
        if load and load.get("1min") is not None and load["1min"] > cores * 2:
            findings.append(_finding(
                WARN, "high_load",
                f"system load is high ({load['1min']:.1f} on {cores} cores); "
                "benchmarks/timings may be noisy.",
                "Wait for the node to quiesce or use a less busy node."))
    except Exception:
        pass

    findings.extend(_install_health_findings())
    findings.extend(_hpc_login_node_findings())
    return findings


# The logical checks self-check performs, in display order. Each maps to the finding
# code(s) it can raise; a check with no matching finding is reported as OK. This makes the
# "what was checked, and how did each do" view possible without duplicating every probe.
_CHECK_CATALOG = [
    ("python_version", "Python version supported", ("python_version",)),
    ("config_valid", "pubrun configuration is valid", ("config_invalid",)),
    ("output_writable", "run output directory is writable", ("output_not_writable",)),
    ("git_available", "git available for source-code provenance", ("git_missing",)),
    ("filesystems", "run-relevant filesystems are healthy (not network/hung/slow)",
     ("netfs_", "fs_hung_", "fs_slow_")),
    ("memory", "sufficient free system memory", ("low_memory",)),
    ("load", "system load is not excessive", ("high_load",)),
    ("hpc_context", "HPC allocation context", ("hpc_login_node",)),
]


def live_checks():
    """Run the live self-check and return ``(checks, findings)``.

    ``findings`` is the existing problem list (unchanged; ``self-check --strict`` still keys
    on WARN severity). ``checks`` is a list of per-check records
    ``{"name", "label", "status": "ok"|"warn"|"info", "detail"}`` covering every logical
    check performed — including the ones that PASSED — so the itemized output can show what
    was checked and how each did (not only the problems). Never raises.
    """
    findings = live_findings()
    checks = []
    for name, label, codes in _CHECK_CATALOG:
        matched = [
            f for f in findings
            if any(f.get("code", "") == c or f.get("code", "").startswith(c) for c in codes)
        ]
        if not matched:
            checks.append({"name": name, "label": label, "status": "ok", "detail": ""})
            continue
        # One record per finding, so a check with several problems (e.g. two network
        # mounts) shows and counts each one, and --show-suggestions can match each detail.
        for f in matched:
            checks.append({
                "name": name, "label": label,
                "status": f.get("severity", "info"),
                "detail": f.get("message", ""),
            })
    return checks, findings


def _hpc_login_node_findings() -> List[Dict[str, Any]]:
    """INFO nudge when we appear to be on an HPC login node (a scheduler's submit tools are
    present but we are NOT inside an allocation). Benchmarking here gives unrepresentative
    numbers; suggest `pubrun bench` (which offers to submit to a compute node).

    INFO, not WARN, by design: this is advice, not a problem, and `self-check --strict` exits
    non-zero on any WARN — a WARN here would break --strict on every login node.
    """
    import shutil
    findings: List[Dict[str, Any]] = []
    try:
        # Inside ANY scheduler allocation means a compute node, whichever submit tools are
        # also on PATH. Checked first because PBS and SGE both ship `qsub`.
        alloc_envs = ("SLURM_JOB_ID", "PBS_JOBID", "LSB_JOBID", "JOB_ID", "PE_HOSTFILE")
        if any(os.environ.get(v) for v in alloc_envs):
            return findings
        detected = None
        if shutil.which("sbatch"):
            detected = ("Slurm", "sbatch")
        elif shutil.which("bsub"):
            detected = ("LSF", "bsub")
        elif shutil.which("qsub"):
            pbs = any(os.environ.get(v) for v in ("PBS_ENVIRONMENT", "PBS_O_HOST"))
            sge = any(os.environ.get(v) for v in ("SGE_ROOT", "SGE_O_HOST"))
            if pbs:
                name = "PBS/Torque"
            elif sge:
                name = "SGE/Grid Engine"
            else:
                name = "PBS/Torque or SGE"
            detected = (name, "qsub")
        if detected is not None:
            name, tool = detected
            findings.append(_finding(
                INFO, "hpc_login_node",
                f"you appear to be on an HPC {name} login node "
                f"(`{tool}` present, not inside an allocation).",
                "Benchmark on a compute node for representative numbers: run "
                "`pubrun bench`, which offers to submit to the scheduler."))
    except Exception:
        pass
    return findings


# ------------------------------------------------------------------- manifest completeness

def manifest_findings(manifest: Dict[str, Any],
                      current_hostname: Optional[str] = None) -> List[Dict[str, Any]]:
    """Capture-completeness + recorded-signal findings for a completed run's manifest.

    Delegates directly to the shared reproducibility assessment engine so CLI,
    TUI, and machine-readable outputs use one canonical findings model. Never raises.
    """
    try:
        assessment = assess_manifest_reproducibility(
            manifest,
            current_hostname=current_hostname,
        )
        return [
            dict(f) for f in assessment.get("findings", []) if isinstance(f, dict)
        ]
    except Exception:
        # Completeness assessment must never crash inspect.
        return []


def summarize(findings: List[Dict[str, Any]]) -> str:
    """One-line terse summary for the default (non-verbose) output."""
    warns = [f for f in findings if f["severity"] == WARN]
    if not warns:
        return "No configuration or capture-completeness concerns found."
    codes = ", ".join(sorted({f["code"] for f in warns})[:4])
    more = "" if len(warns) <= 4 else f" (+{len(warns)-4} more)"
    return f"{len(warns)} concern(s): {codes}{more}."
