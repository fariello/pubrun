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


def _install_health_findings() -> List[Dict[str, Any]]:
    findings: List[Dict[str, Any]] = []

    # Python version support.
    if sys.version_info < _MIN_PY:
        findings.append(_finding(
            WARN, "python_version",
            f"Python {sys.version_info.major}.{sys.version_info.minor} is below pubrun's "
            f"minimum supported {_MIN_PY[0]}.{_MIN_PY[1]}.",
            "Upgrade Python to a supported version."))

    # Config file validity (if a .pubrun.toml is present in cwd or via resolve).
    try:
        from pubrun.config import resolve_config
        resolve_config()  # raises / logs on malformed config
    except Exception as e:
        findings.append(_finding(
            WARN, "config_invalid",
            f"pubrun configuration could not be resolved cleanly: {type(e).__name__}: {e}",
            "Check your `.pubrun.toml` for syntax/schema errors."))

    # Output dir writability.
    try:
        base = _live_paths().get("output_dir", "")
        parent = base if os.path.isdir(base) else os.path.dirname(base) or "."
        # Walk up to the nearest existing ancestor to test writability without creating dirs.
        probe = parent
        while probe and not os.path.exists(probe):
            probe = os.path.dirname(probe)
        if probe and not os.access(probe, os.W_OK):
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
    by_prefix = {}
    for f in findings:
        by_prefix.setdefault(f.get("code", ""), f)
    checks = []
    for name, label, codes in _CHECK_CATALOG:
        matched = None
        for f in findings:
            code = f.get("code", "")
            if any(code == c or code.startswith(c) for c in codes):
                matched = f
                break
        if matched is None:
            checks.append({"name": name, "label": label, "status": "ok", "detail": ""})
        else:
            checks.append({
                "name": name, "label": label,
                "status": matched.get("severity", "info"),
                "detail": matched.get("message", ""),
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
        # (scheduler name, submit-tool on PATH, "inside an allocation" env marker)
        schedulers = [
            ("Slurm", "sbatch", "SLURM_JOB_ID"),
            ("PBS/Torque", "qsub", "PBS_JOBID"),
            ("LSF", "bsub", "LSB_JOBID"),
            ("SGE/Grid Engine", "qsub", "JOB_ID"),
        ]
        seen = set()
        for name, tool, alloc_env in schedulers:
            if not shutil.which(tool) or tool in seen:
                continue
            seen.add(tool)
            on_compute = bool(os.environ.get(alloc_env))
            if not on_compute:
                findings.append(_finding(
                    INFO, "hpc_login_node",
                    f"you appear to be on an HPC {name} login node "
                    f"(`{tool}` present, not inside an allocation).",
                    "Benchmark on a compute node for representative numbers: run "
                    "`pubrun bench`, which offers to submit to the scheduler."))
                break  # one nudge is enough
    except Exception:
        pass
    return findings


# ------------------------------------------------------------------- manifest completeness

def _capture_state_status(section: Any) -> Optional[str]:
    if isinstance(section, dict):
        cs = section.get("capture_state")
        if isinstance(cs, dict):
            return cs.get("status")
    return None


def manifest_findings(manifest: Dict[str, Any],
                      current_hostname: Optional[str] = None) -> List[Dict[str, Any]]:
    """Capture-completeness + recorded-signal findings for a completed run's manifest.

    Reports what the run captured AND what it could not tell you (and how to enable more),
    honestly distinguishing "feature OFF" from "on but no records" where the manifest is
    ambiguous. Never raises.
    """
    findings: List[Dict[str, Any]] = []
    try:
        # --- Different-system banner data (host identity) ---
        run_host = None
        host = manifest.get("host", {})
        if isinstance(host, dict):
            hn = host.get("hostname")
            run_host = hn.get("value") if isinstance(hn, dict) else hn
        if current_hostname and run_host and current_hostname != run_host:
            findings.append(_finding(
                WARN, "different_host",
                f"this run executed on '{run_host}', but you are inspecting from "
                f"'{current_hostname}'. Any live environment checks reflect THIS machine, "
                f"not where the run ran (common on HPC: run on a compute node, inspect on "
                f"the head node).", None))

        # --- Recorded network-filesystem signal ---
        fs_data = manifest.get("filesystem", {})
        if isinstance(fs_data, dict):
            for f in _network_fs_findings(fs_data):
                # reframe as "this run ran on network FS" rather than a live suggestion
                f["message"] = "this run's " + f["message"]
                findings.append(f)

        # --- Capture-completeness: DETECTABLE from the manifest ---
        res = manifest.get("resources", {})
        res_status = _capture_state_status(res)
        if res_status == "suppressed":
            findings.append(_finding(
                WARN, "resources_off",
                "resource monitoring was OFF (no RSS/CPU/RAM/load recorded).",
                "Set `[capture.resources].depth` to `standard` to record resource usage "
                "(low overhead; see docs/performance.md)."))
        elif isinstance(res, dict) and res.get("scope") not in ("tree", None):
            findings.append(_finding(
                WARN, "resources_process_scope",
                "process-tree resources were NOT captured (only the main process).",
                "Set `[capture.resources].scope = \"tree\"` to sum RSS/CPU across child "
                "processes (multiprocessing/Dask/Ray). Slight extra sampling cost."))

        console = manifest.get("console", {})
        if isinstance(console, dict) and console.get("capture_mode") == "off":
            findings.append(_finding(
                INFO, "console_off",
                "console output was not captured (capture_mode = off).",
                "Set `[console].capture_mode = \"standard\"` to record stdout/stderr."))

        for section_name, label, key in (
            ("hardware", "hardware", None),
            ("packages", "package inventory", None),
            ("git", "git/source-code state", None),
        ):
            if _capture_state_status(manifest.get(section_name, {})) == "suppressed":
                findings.append(_finding(
                    INFO, f"{section_name}_off",
                    f"{label} was not captured.",
                    f"Enable `[capture.{section_name}]` if you want it recorded."))

        # Import mode: reveal whether patching was even permitted.
        imports = manifest.get("pubrun_imports", {})
        behavior = imports.get("selected_behavior", {}) if isinstance(imports, dict) else {}
        if isinstance(behavior, dict):
            if behavior.get("patch_subprocesses") is False:
                findings.append(_finding(
                    INFO, "mode_no_subprocess_patch",
                    f"the import mode ('{imports.get('selected_mode')}') did not permit "
                    "subprocess tracking.",
                    "Use the default `import pubrun` (auto) mode to allow subprocess capture."))

        # --- Capture-completeness: AMBIGUOUS unless the flags are present ---
        cap = manifest.get("capture", {})
        subs = manifest.get("subprocesses", [])
        sub_flag = cap.get("subprocesses_enabled") if isinstance(cap, dict) else None
        if sub_flag is False:
            findings.append(_finding(
                WARN, "subprocess_tracking_off",
                "subprocess tracking was OFF — no child processes were recorded.",
                "Enable `[capture.subprocesses].enabled = true` to record subprocess calls."))
        elif sub_flag is None and not subs:
            # Older manifest without the flag: cannot tell off from unused. Be honest.
            findings.append(_finding(
                INFO, "subprocess_unknown",
                "no subprocesses were recorded — either subprocess tracking was disabled "
                "or none were spawned (this run's manifest predates the enabled-flag, so it "
                "cannot be determined).",
                "pubrun records subprocesses only when `[capture.subprocesses]` is enabled."))

        data_files = manifest.get("data_files", {})
        inputs = data_files.get("inputs", []) if isinstance(data_files, dict) else []
        outputs = data_files.get("outputs", []) if isinstance(data_files, dict) else []
        if not inputs and not outputs:
            findings.append(_finding(
                INFO, "no_file_provenance",
                "no file-I/O provenance was recorded — pubrun does NOT patch open() "
                "globally, so file reads/writes are only recorded if the script calls "
                "`pubrun.open()` (or `pubrun.subprocess`).",
                "Use `pubrun.open(...)` in place of `open(...)` to record input/output "
                "files (path + hash)."))

    except Exception:
        # Completeness assessment must never crash inspect.
        pass
    return findings


def summarize(findings: List[Dict[str, Any]]) -> str:
    """One-line terse summary for the default (non-verbose) output."""
    warns = [f for f in findings if f["severity"] == WARN]
    if not warns:
        return "No configuration or capture-completeness concerns found."
    codes = ", ".join(sorted({f["code"] for f in warns})[:4])
    more = "" if len(warns) <= 4 else f" (+{len(warns)-4} more)"
    return f"{len(warns)} concern(s): {codes}{more}."
