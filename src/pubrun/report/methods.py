import math
from typing import Dict, Any, List, Optional
from pubrun._pep503 import normalize_package_name
from pubrun.report.templates import MARKDOWN_TEMPLATE, LATEX_TEMPLATE, HIGHLIGHT_PACKAGES
from pubrun.report.file_evidence import _classify_file_record

_NORMALIZED_HIGHLIGHTS = {normalize_package_name(n) for n in HIGHLIGHT_PACKAGES}


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


_LATEX_ESCAPE_TABLE = str.maketrans({
    "\\": r"\textbackslash{}",
    "&": r"\&",
    "%": r"\%",
    "$": r"\$",
    "#": r"\#",
    "_": r"\_",
    "{": r"\{",
    "}": r"\}",
    "~": r"\textasciitilde{}",
    "^": r"\textasciicircum{}",
})


def _escape_latex(text: str) -> str:
    """Escape all 10 LaTeX special characters in a single pass."""
    return text.translate(_LATEX_ESCAPE_TABLE)


def _format_gpus(hw: Dict[str, Any]) -> str:
    """Summarize captured ``hardware.gpus`` into a grouped human-readable string."""
    raw_gpus = hw.get("gpus")
    if not isinstance(raw_gpus, list):
        return ""
    counts: Dict[str, int] = {}
    for gpu in raw_gpus:
        if not isinstance(gpu, dict):
            continue
        raw_model = gpu.get("model")
        if not isinstance(raw_model, str) or not raw_model.strip():
            continue
        model = raw_model.strip()
        details: List[str] = []
        vram_gb = bytes_to_gb(gpu.get("memory_total_bytes"))
        if vram_gb > 0:
            details.append(f"{vram_gb} GB VRAM")
        raw_driver = gpu.get("driver_version")
        if isinstance(raw_driver, str) and raw_driver.strip():
            details.append(f"driver {raw_driver.strip()}")
        desc = f"{model} ({', '.join(details)})" if details else model
        counts[desc] = counts.get(desc, 0) + 1
    if not counts:
        return ""
    return ", ".join(f"{cnt}x {desc}" if cnt > 1 else desc for desc, cnt in counts.items())


def _extract_valid_packages(manifest: Dict[str, Any]) -> List[str]:
    """Return formatted strings for all valid recorded packages in manifest order."""
    found: List[str] = []
    seen: set = set()
    if not isinstance(manifest, dict):
        return found
    records = _as_dict(manifest.get("packages")).get("records")
    if not isinstance(records, list):
        return found
    for record in records:
        if not isinstance(record, dict):
            continue
        raw_name = record.get("name")
        if not isinstance(raw_name, str) or not raw_name.strip():
            continue
        norm_name = normalize_package_name(raw_name.strip())
        if norm_name not in seen:
            seen.add(norm_name)
            raw_version = record.get("version")
            version = str(raw_version) if raw_version not in (None, "") else "unknown"
            found.append(f"{norm_name} (v{version})")
    return found


def _summarize_manifest_data_files(manifest: Any) -> Dict[str, int]:
    """Summarize ``data_files`` evidence counts for a single manifest."""
    counts: Dict[str, int] = {
        "total": 0,
        "verified": 0,
        "asserted": 0,
        "identified_only": 0,
        "over_budget": 0,
        "pending": 0,
        "changed": 0,
        "failed_or_unavailable": 0,
    }
    if not isinstance(manifest, dict):
        return counts
    data_files = manifest.get("data_files")
    if not isinstance(data_files, dict):
        return counts
    for bucket_name in ("inputs", "outputs", "mixed"):
        bucket = data_files.get(bucket_name)
        if not isinstance(bucket, list):
            continue
        for rec in bucket:
            if not isinstance(rec, dict):
                continue
            cls = _classify_file_record(rec)
            counts["total"] += 1
            if cls == "verified":
                counts["verified"] += 1
            elif cls == "asserted":
                counts["asserted"] += 1
            elif cls == "identified_only":
                counts["identified_only"] += 1
            elif cls == "over_budget":
                counts["over_budget"] += 1
            elif cls == "pending":
                counts["pending"] += 1
            elif cls == "changed":
                counts["changed"] += 1
            elif cls in ("failed", "unavailable"):
                counts["failed_or_unavailable"] += 1
            else:
                counts["identified_only"] += 1
    return counts


def _format_file_provenance_note(
    counts: Dict[str, int],
    format_type: str,
    *,
    multi_run_count: Optional[int] = None,
    runs_with_files: Optional[int] = None,
) -> str:
    """Format an honest file-provenance evidence breakdown sentence, or ``""`` when empty."""
    total = counts.get("total", 0)
    if total <= 0:
        return ""

    parts: List[str] = []
    if counts.get("verified", 0) > 0:
        n = counts["verified"]
        parts.append(f"{n} with independently verified content digest{'s' if n != 1 else ''}")
    if counts.get("asserted", 0) > 0:
        n = counts["asserted"]
        parts.append(f"{n} with caller-asserted digest{'s' if n != 1 else ''} (unverified)")
    if counts.get("identified_only", 0) > 0:
        n = counts["identified_only"]
        parts.append(f"{n} recorded by path or stat metadata only")
    if counts.get("over_budget", 0) > 0:
        n = counts["over_budget"]
        parts.append(f"{n} skipped as over hashing budget")
    if counts.get("pending", 0) > 0:
        n = counts["pending"]
        parts.append(f"{n} pending output record{'s' if n != 1 else ''} (unhashed)")
    if counts.get("changed", 0) > 0:
        n = counts["changed"]
        parts.append(f"{n} changed during capture (unverified)")
    if counts.get("failed_or_unavailable", 0) > 0:
        n = counts["failed_or_unavailable"]
        parts.append(f"{n} with failed or unavailable hashing")

    breakdown = ", ".join(parts)
    record_word = "file record" if total == 1 else "file records"

    if multi_run_count is not None:
        recorded_runs = runs_with_files if runs_with_files is not None else multi_run_count
        sentence = (
            f"Note: data file provenance across {recorded_runs} of {multi_run_count} runs "
            f"tracked {total} {record_word} ({breakdown})."
        )
        if format_type == "latex":
            return f"% {_escape_latex(sentence)}"
        return f"*{sentence}*"

    sentence = f"Data file provenance tracked {total} {record_word} ({breakdown})."
    if format_type == "latex":
        return _escape_latex(sentence)
    return sentence


def bytes_to_gb(bytes_val: Any) -> float:
    if isinstance(bytes_val, bool) or not isinstance(bytes_val, (int, float)):
        return 0.0
    if not math.isfinite(bytes_val) or not bytes_val:
        return 0.0
    return round(float(bytes_val) / (1024 ** 3), 1)


def extract_highlighted_packages(manifest: Dict[str, Any]) -> List[str]:
    """Return formatted strings for notable packages found in the manifest."""
    found: List[str] = []
    seen: set = set()
    if not isinstance(manifest, dict):
        return found
    records = _as_dict(manifest.get("packages")).get("records")
    if not isinstance(records, list):
        return found
    for record in records:
        if not isinstance(record, dict):
            continue
        raw_name = record.get("name")
        if not isinstance(raw_name, str) or not raw_name.strip():
            continue
        norm_name = normalize_package_name(raw_name.strip())
        if norm_name in _NORMALIZED_HIGHLIGHTS and norm_name not in seen:
            seen.add(norm_name)
            raw_version = record.get("version")
            version = str(raw_version) if raw_version not in (None, "") else "unknown"
            found.append(f"{norm_name} (v{version})")
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
    hw = _as_dict(m.get("hardware"))
    raw_cpu = _as_dict(hw.get("cpu")).get("model")
    cpu_model = raw_cpu if isinstance(raw_cpu, str) and raw_cpu else "unknown CPU"
    ram_gb = bytes_to_gb(hw.get("memory_total_bytes", 0))
    gpu_summary = _format_gpus(hw)
    gpu_text = f", accelerated by {gpu_summary}" if gpu_summary else ""

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
            all_packages = _extract_valid_packages(m)
            if all_packages:
                if len(all_packages) <= 10:
                    packages_text = f"Recorded third-party dependencies include {', '.join(all_packages)}."
                else:
                    top = all_packages[:10]
                    rem = len(all_packages) - len(top)
                    packages_text = (
                        f"Recorded third-party dependencies include {', '.join(top)}, "
                        f"and {rem} additional package{'s' if rem != 1 else ''} "
                        f"({len(all_packages)} total)."
                    )
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

    short_commit = git_commit[:8] if len(git_commit) >= 8 else git_commit
    python_impl_display = python_impl.capitalize()

    if format_type == "latex":
        os_name = _escape_latex(os_name)
        cpu_model = _escape_latex(cpu_model)
        gpu_text = _escape_latex(gpu_text)
        python_version = _escape_latex(python_version)
        python_impl_display = _escape_latex(python_impl_display)
        packages_text = _escape_latex(packages_text)
        short_commit = _escape_latex(short_commit)
        git_repo_text = _escape_latex(git_repo_text)
        pubrun_version_text = _escape_latex(pubrun_version_text)

    template = LATEX_TEMPLATE if format_type == "latex" else MARKDOWN_TEMPLATE

    rendered = template.format(
        os_name=os_name,
        cpu_model=cpu_model,
        ram_gb=ram_gb,
        gpu_text=gpu_text,
        python_version=python_version,
        python_impl=python_impl_display,
        packages_text=packages_text,
        git_commit=short_commit,
        git_repo_text=git_repo_text,
        pubrun_version_text=pubrun_version_text
    ).strip()

    fp_counts = _summarize_manifest_data_files(m)
    fp_note = _format_file_provenance_note(fp_counts, format_type)
    if fp_note:
        anchor = "\n\n%% Ensure you add" if format_type == "latex" else "\n\n**References:**"
        if anchor in rendered:
            rendered = rendered.replace(anchor, f" {fp_note}{anchor}", 1)
        else:
            rendered = f"{rendered}\n\n{fp_note}"

    failed = _failed_sections(m)
    if failed:
        if format_type == "latex":
            escaped = ", ".join(_escape_latex(sec) for sec in failed)
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


def _gpus_of(m: Dict[str, Any]) -> str:
    summary = _format_gpus(_as_dict(_as_dict(m).get("hardware")))
    return summary if summary else "none"


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
    if pkgs:
        return ", ".join(sorted(pkgs))
    all_pkgs = sorted(_extract_valid_packages(m))
    if all_pkgs:
        if len(all_pkgs) <= 10:
            return ", ".join(all_pkgs)
        return f"{', '.join(all_pkgs[:10])} (+{len(all_pkgs) - 10} more; {len(all_pkgs)} recorded)"
    return "(standard library only)"


_VARIANCE_FIELDS = [
    ("Operating system", _os_of),
    ("CPU", _cpu_of),
    ("RAM", _ram_of),
    ("GPU", _gpus_of),
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

    per_run_fp = [_summarize_manifest_data_files(m) for m in manifests]
    agg_fp: Dict[str, int] = {
        key: sum(c[key] for c in per_run_fp)
        for key in (
            "total",
            "verified",
            "asserted",
            "identified_only",
            "over_budget",
            "pending",
            "changed",
            "failed_or_unavailable",
        )
    }
    runs_with_files = sum(1 for c in per_run_fp if c["total"] > 0)
    multi_fp_note = (
        _format_file_provenance_note(
            agg_fp,
            format_type,
            multi_run_count=n,
            runs_with_files=runs_with_files,
        )
        if agg_fp["total"] > 0
        else ""
    )

    if format_type == "latex":
        parts = [base, "", f"% {count_note}"]
        if varying:
            parts.append("% Environment varied across the aggregated runs:")
            for label, values in varying:
                joined = "; ".join(_escape_latex(v) for v in values)
                parts.append(f"%   {_escape_latex(label)}: {joined}")
        if multi_fp_note:
            parts.append(multi_fp_note)
        if rest_has_failures and all_failed_sections:
            escaped = ", ".join(_escape_latex(sec) for sec in all_failed_sections)
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
    if multi_fp_note:
        parts.append("")
        parts.append(multi_fp_note)
    if rest_has_failures and all_failed_sections:
        parts.append("")
        parts.append(
            f"*Note: partial provenance across {affected_runs} of {n} runs; "
            f"capture failed for: {', '.join(all_failed_sections)}.*"
        )
    return "\n".join(parts).strip()
