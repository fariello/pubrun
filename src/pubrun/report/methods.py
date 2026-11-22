import math
from typing import Dict, Any, List, Optional
from pubrun.report.templates import MARKDOWN_TEMPLATE, LATEX_TEMPLATE, HIGHLIGHT_PACKAGES


def _as_dict(val: Any) -> Dict[str, Any]:
    return val if isinstance(val, dict) else {}


def _section_status(manifest: Any, name: str) -> Optional[str]:
    if not isinstance(manifest, dict):
        return None
    sec = manifest.get(name)
    if not isinstance(sec, dict):
        return None
    cs = sec.get("capture_state")
    if not isinstance(cs, dict):
        return None
    status = cs.get("status")
    return status if isinstance(status, str) else None


def _failed_sections(manifest: Any) -> List[str]:
    if not isinstance(manifest, dict):
        return []
    failed = [
        sec_name
        for sec_name, sec_val in manifest.items()
        if isinstance(sec_val, dict) and _section_status(manifest, sec_name) == "failed"
    ]
    return sorted(failed)


def bytes_to_gb(bytes_val: Any) -> float:
    if isinstance(bytes_val, bool) or not isinstance(bytes_val, (int, float)):
        return 0.0
    if not math.isfinite(bytes_val) or not bytes_val:
        return 0.0
    return round(float(bytes_val) / (1024 ** 3), 1)


def extract_highlighted_packages(manifest: Dict[str, Any]) -> List[str]:
    """Return formatted strings for notable packages found in the manifest."""
    found: List[str] = []
    if not isinstance(manifest, dict):
        return found
    records = _as_dict(manifest.get("packages")).get("records")
    if not isinstance(records, list):
        return found
    for record in records:
        if not isinstance(record, dict):
            continue
        raw_name = record.get("name")
        if not isinstance(raw_name, str) or not raw_name:
            continue
        name = raw_name.lower()
        if name in HIGHLIGHT_PACKAGES:
            raw_version = record.get("version")
            version = str(raw_version) if raw_version not in (None, "") else "unknown"
            found.append(f"{name} (v{version})")
    return found


def generate_report(manifest: Dict[str, Any], format_type: str = "markdown") -> str:
    """Generate a publication-ready 'Computational Methods' paragraph.

    Args:
        manifest: Hydrated manifest dictionary.
        format_type: Output format (``"markdown"`` or ``"latex"``).
    """
    m = _as_dict(manifest)

    # Hardware
    # OS name — use the host capture data, not the Windows-only OS env var
    host = _as_dict(m.get("host"))
    raw_os = host.get("os_name")
    os_name = raw_os if isinstance(raw_os, str) and raw_os else "an unknown OS"
    if format_type == "latex":
        os_name = os_name.replace("_", "\\_")
    hw = _as_dict(m.get("hardware"))
    raw_cpu = _as_dict(hw.get("cpu")).get("model")
    cpu_model = raw_cpu if isinstance(raw_cpu, str) and raw_cpu else "unknown CPU"
    ram_gb = bytes_to_gb(hw.get("memory_total_bytes", 0))

    # Python
    py = _as_dict(m.get("python"))
    raw_py_ver = py.get("version")
    py_parts = raw_py_ver.split() if isinstance(raw_py_ver, str) else []
    python_version = py_parts[0] if py_parts else "unknown"
    raw_py_impl = py.get("implementation")
    python_impl = raw_py_impl if isinstance(raw_py_impl, str) and raw_py_impl else "unknown"

    # Git
    git = _as_dict(m.get("git"))
    if "commit" not in git:
        git_commit = "unknown"
    else:
        raw_commit = git.get("commit")
        git_commit = raw_commit if isinstance(raw_commit, str) and raw_commit else "unavailable"

    remote_obj = git.get("remote_url")
    if isinstance(remote_obj, dict):
        raw_remote = remote_obj.get("value")
        remote = raw_remote if isinstance(raw_remote, str) and raw_remote else None
    elif isinstance(remote_obj, str) and remote_obj:
        remote = remote_obj
    else:
        remote = None
    git_repo_text = f" (origin: {remote})" if remote else ""
    if format_type == "latex":
        git_repo_text = git_repo_text.replace("_", "\\_")

    # Packages
    packages_status = _section_status(m, "packages")
    if packages_status == "failed":
        packages_text = "Package provenance was unavailable because package capture failed."
    elif packages_status == "suppressed":
        packages_text = "Package capture was disabled by configuration."
    else:
        packages = extract_highlighted_packages(m)
        if packages:
            packages_text = f"Key dependencies tracked include {', '.join(packages)}."
        else:
            packages_text = "Standard library dependencies were utilized."

    # pubrun version/commit — the tool that produced this record. Recorded in the
    # manifest as run.library_version / run.library_commit. Naming the exact
    # version (and commit) is important for reproducibility of the provenance.
    run_meta = _as_dict(m.get("run"))
    raw_pubrun_version = run_meta.get("library_version")
    pubrun_version = (
        str(raw_pubrun_version) if raw_pubrun_version not in (None, "") else None
    )
    raw_pubrun_commit = run_meta.get("library_commit")
    pubrun_commit = raw_pubrun_commit if isinstance(raw_pubrun_commit, str) else ""
    if pubrun_version and pubrun_commit:
        pubrun_version_text = f"pubrun v{pubrun_version} (commit {pubrun_commit[:8]})"
    elif pubrun_version:
        pubrun_version_text = f"pubrun v{pubrun_version}"
    else:
        pubrun_version_text = "pubrun (version unknown)"

    template = LATEX_TEMPLATE if format_type == "latex" else MARKDOWN_TEMPLATE

    rendered = template.format(
        os_name=os_name,
        cpu_model=cpu_model,
        ram_gb=ram_gb,
        python_version=python_version,
        python_impl=python_impl.capitalize(),
        packages_text=packages_text,
        git_commit=git_commit[:8] if len(git_commit) >= 8 else git_commit,
        git_repo_text=git_repo_text,
        pubrun_version_text=pubrun_version_text
    ).strip()

    failed = _failed_sections(m)
    if failed:
        if format_type == "latex":
            escaped = ", ".join(sec.replace("_", "\\_") for sec in failed)
            rendered = f"{rendered}\n\n% Note: partial provenance; capture failed for: {escaped}."
        else:
            rendered = f"{rendered}\n\n*Note: partial provenance; capture failed for: {', '.join(failed)}.*"

    return rendered


# Methods-relevant fields compared across a run set (label -> extractor). Order
# is the display order for the variance note; extractors return a display string.
def _os_of(m: Dict[str, Any]) -> str:
    val = _as_dict(_as_dict(m).get("host")).get("os_name")
    return val if isinstance(val, str) and val else "unknown OS"


def _cpu_of(m: Dict[str, Any]) -> str:
    val = _as_dict(_as_dict(_as_dict(m).get("hardware")).get("cpu")).get("model")
    return val if isinstance(val, str) and val else "unknown CPU"


def _ram_of(m: Dict[str, Any]) -> str:
    return f"{bytes_to_gb(_as_dict(_as_dict(m).get('hardware')).get('memory_total_bytes', 0))} GB"


def _py_of(m: Dict[str, Any]) -> str:
    raw = _as_dict(_as_dict(m).get("python")).get("version")
    parts = raw.split() if isinstance(raw, str) else []
    return parts[0] if parts else "unknown"


def _commit_of(m: Dict[str, Any]) -> str:
    c = _as_dict(_as_dict(m).get("git")).get("commit")
    if not isinstance(c, str) or not c:
        return "unavailable"
    return c[:8] if len(c) >= 8 else c


def _pubrun_of(m: Dict[str, Any]) -> str:
    v = _as_dict(_as_dict(m).get("run")).get("library_version")
    return f"v{v}" if v not in (None, "") else "version unknown"


def _packages_of(m: Dict[str, Any]) -> str:
    status = _section_status(m, "packages")
    if status == "failed":
        return "(package capture failed)"
    if status == "suppressed":
        return "(package capture disabled)"
    pkgs = extract_highlighted_packages(m)
    return ", ".join(sorted(pkgs)) if pkgs else "(standard library only)"


_VARIANCE_FIELDS = [
    ("Operating system", _os_of),
    ("CPU", _cpu_of),
    ("RAM", _ram_of),
    ("Python", _py_of),
    ("Git commit", _commit_of),
    ("pubrun", _pubrun_of),
    ("Key packages", _packages_of),
]


def generate_report_multi(manifests: List[Dict[str, Any]], format_type: str = "markdown") -> str:
    """Generate a methods paragraph aggregated over a SET of runs (option C).

    - Empty list: raises ValueError (the caller must have runs).
    - Exactly one run: byte-identical to ``generate_report`` (single-run parity).
    - Many runs: a representative paragraph (from the FIRST manifest — callers pass
      most-recent-first) that states "across N runs", plus a variance note listing
      only the methods-relevant fields that DIFFER across the set (sorted distinct
      values). Environment-homogeneous sets read like the single-run output with
      just the run count added. Output is deterministic for a fixed set.

    Divergence (including differing git commits) is disclosed, never a hard error.
    """
    if not manifests:
        raise ValueError("generate_report_multi requires at least one manifest")
    if len(manifests) == 1:
        return generate_report(manifests[0], format_type)

    n = len(manifests)
    base = generate_report(manifests[0], format_type)

    # Insert the run count into the representative paragraph's opening sentence.
    # (Kept simple and deterministic; the base text is the most-recent run.)
    count_note = (
        f"These figures describe a representative run; provenance was aggregated "
        f"across {n} runs."
    )

    # Compute per-field distinct values across the set (sorted for determinism).
    varying = []
    for label, fn in _VARIANCE_FIELDS:
        try:
            values = sorted({fn(m) for m in manifests})
        except Exception:
            continue
        if len(values) > 1:
            varying.append((label, values))

    per_run_failed = [_failed_sections(m) for m in manifests]
    rest_has_failures = any(per_run_failed[1:])
    all_failed_sections = sorted({sec for secs in per_run_failed for sec in secs})
    affected_runs = sum(1 for secs in per_run_failed if secs)

    if format_type == "latex":
        parts = [base, "", f"% {count_note}"]
        if varying:
            parts.append("% Environment varied across the aggregated runs:")
            for label, values in varying:
                joined = "; ".join(v.replace("_", "\\_") for v in values)
                parts.append(f"%   {label}: {joined}")
        if rest_has_failures and all_failed_sections:
            escaped = ", ".join(sec.replace("_", "\\_") for sec in all_failed_sections)
            parts.append(
                f"% Note: partial provenance across {affected_runs} of {n} runs; "
                f"capture failed for: {escaped}."
            )
        return "\n".join(parts).strip()

    # markdown
    parts = [base, "", f"*{count_note}*"]
    if varying:
        parts.append("")
        parts.append("**Environment variation across the aggregated runs:**")
        for label, values in varying:
            parts.append(f"- {label}: {', '.join(values)}")
    if rest_has_failures and all_failed_sections:
        parts.append("")
        parts.append(
            f"*Note: partial provenance across {affected_runs} of {n} runs; "
            f"capture failed for: {', '.join(all_failed_sections)}.*"
        )
    return "\n".join(parts).strip()
