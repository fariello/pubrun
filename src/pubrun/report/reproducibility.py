"""Shared reproducibility evidence model and recorded-manifest gap analysis.

This module provides a single read-only, Python standard-library assessment engine
shared by the command-line interface (CLI), terminal user interface (TUI), and
JSON output. It classifies recorded provenance across seven evidence categories,
distinguishes observed, inferred, asserted, inherited, unavailable, and
not-checked evidence, prioritizes concrete next steps, and never emits an
unexplained numerical reproducibility score or claims guaranteed reproduction.

IMPORTANT: this module is CLI/report-only and must never be imported by
``import pubrun`` or the runtime capture path.
"""

import os
from typing import Any, Dict, List, Optional, Tuple, Union

from pubrun.report.utils import HYDRABLE_SECTIONS, HydrationReport

# Severity levels (textual, authoritative; color is optional reinforcement only).
INFO = "info"
WARN = "warn"

# Shared reproducibility taxonomy constants.
EVIDENCE_STATUSES: Tuple[str, ...] = (
    "observed",
    "inferred",
    "asserted",
    "inherited",
    "unavailable",
    "not_checked",
)

CATEGORY_STATUSES: Tuple[str, ...] = (
    "adequate",
    "gaps",
    "mismatch",
    "uncertain",
    "not_checked",
)

IMPACT_LEVELS: Tuple[str, ...] = (
    "material",
    "portability",
    "incidental",
    "informational",
)

COMPARISON_OUTCOMES: Tuple[str, ...] = (
    "match",
    "mismatch",
    "portability_diff",
    "unknown",
    "not_checked",
)

CATEGORY_ORDER: Tuple[str, ...] = (
    "source",
    "runtime",
    "dependencies",
    "inputs_outputs",
    "capture_completeness",
    "parent_metadata",
    "invocation",
)

CATEGORY_LABELS: Dict[str, str] = {
    "source": "Source",
    "runtime": "Runtime",
    "dependencies": "Dependencies",
    "inputs_outputs": "Inputs & Outputs",
    "capture_completeness": "Capture Completeness",
    "parent_metadata": "Parent Metadata",
    "invocation": "Invocation",
}

DEFAULT_STALE_PARENT_SECONDS: float = 86400.0

NON_GUARANTEE_DISCLAIMER: str = (
    "Recorded provenance and an absence of findings support reproduction analysis, "
    "but they do not guarantee equivalent scientific or bitwise results, especially "
    "for legacy or sparse manifests."
)

_DEFAULT_NEXT_ACTION: str = (
    "Run `pubrun inspect --preflight` on the target machine to compare recorded "
    "requirements against the current environment."
)

_CORE_MANIFEST_SECTIONS: Tuple[str, ...] = (
    "run",
    "timing",
    "invocation",
    "status",
    "python",
    "host",
    "packages",
    "git",
)

_NON_COMPLETED_OUTCOMES = frozenset(
    ("running", "failed", "interrupted", "partial", "ghost", "unknown")
)

_CATEGORY_STATUS_LABELS: Dict[str, Tuple[str, str]] = {
    "adequate": ("ADEQUATE", "32"),
    "gaps": ("GAPS", "33"),
    "mismatch": ("MISMATCH", "31"),
    "uncertain": ("UNCERTAIN", "33"),
    "not_checked": ("NOT_CHECKED", "36"),
}

_SEVERITY_LABELS: Dict[str, Tuple[str, str]] = {
    WARN: ("WARN ", "33"),
    INFO: ("INFO ", "32"),
}


def _make_finding(
    severity: str,
    code: str,
    message: str,
    suggestion: Optional[str] = None,
    *,
    category: str,
    evidence_status: str,
    impact: str = "informational",
    comparison: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Build a JSON-serializable finding preserving legacy ``checks.py`` keys."""
    return {
        "severity": severity,
        "code": code,
        "message": message,
        "suggestion": suggestion,
        "category": category,
        "evidence_status": evidence_status,
        "impact": impact,
        "comparison": comparison,
        "details": dict(details) if isinstance(details, dict) else {},
    }


def _capture_state_status(section: Any) -> Optional[str]:
    """Safely extract ``section['capture_state']['status']`` when present."""
    if isinstance(section, dict):
        cs = section.get("capture_state")
        if isinstance(cs, dict):
            status = cs.get("status")
            if isinstance(status, str):
                return status
    return None


def _capture_state_detail(section: Any) -> Optional[str]:
    """Safely extract ``section['capture_state']['detail']`` when present."""
    if isinstance(section, dict):
        cs = section.get("capture_state")
        if isinstance(cs, dict):
            detail = cs.get("detail")
            if isinstance(detail, str) and detail.strip():
                return detail.strip()
    return None


def _unwrap_hostname(raw_hostname: Any) -> Optional[str]:
    """Return a plain hostname string, ignoring redacted/hashed/unavailable payloads."""
    if isinstance(raw_hostname, str):
        return raw_hostname if raw_hostname else None
    if isinstance(raw_hostname, dict):
        rep = raw_hostname.get("representation")
        if rep is None or rep == "plain":
            val = raw_hostname.get("value")
            if isinstance(val, str) and val:
                return val
    return None


def _hydration_report_to_dict(
    hydration_report: Optional[Union[HydrationReport, Dict[str, Any]]]
) -> Optional[Dict[str, Any]]:
    """Normalize a ``HydrationReport`` or dict into a plain dict, or None."""
    if hydration_report is None:
        return None
    if isinstance(hydration_report, HydrationReport):
        return hydration_report.to_dict()
    if isinstance(hydration_report, dict):
        return {
            "meta_ref": hydration_report.get("meta_ref"),
            "resolved_path": hydration_report.get("resolved_path"),
            "status": hydration_report.get("status", "none"),
            "inherited_sections": list(hydration_report.get("inherited_sections") or []),
            "direct_sections": list(hydration_report.get("direct_sections") or []),
            "parent_started_at_utc": hydration_report.get("parent_started_at_utc"),
            "child_started_at_utc": hydration_report.get("child_started_at_utc"),
            "age_seconds": hydration_report.get("age_seconds"),
            "script_modified_after_parent": hydration_report.get(
                "script_modified_after_parent"
            ),
            "identity_mismatches": list(
                hydration_report.get("identity_mismatches") or []
            ),
            "warnings": list(hydration_report.get("warnings") or []),
        }
    return None


def _format_age(seconds: float) -> str:
    """Format an elapsed duration in seconds as a concise human-readable string."""
    abs_sec = abs(seconds)
    if abs_sec >= 86400.0:
        return f"{abs_sec / 86400.0:.1f} days ({abs_sec:.0f}s)"
    if abs_sec >= 3600.0:
        return f"{abs_sec / 3600.0:.1f} hours ({abs_sec:.0f}s)"
    if abs_sec >= 60.0:
        return f"{abs_sec / 60.0:.1f} minutes ({abs_sec:.0f}s)"
    return f"{abs_sec:.1f}s"


def _assess_source(
    manifest: Dict[str, Any],
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """Assess source-code provenance (git state and entrypoint script hash)."""
    findings: List[Dict[str, Any]] = []
    git = manifest.get("git")
    git_dict = git if isinstance(git, dict) else {}
    git_status = _capture_state_status(git_dict)
    git_inherited = bool(git_dict.get("is_hydrated"))
    git_ev = "inherited" if git_inherited else "observed"

    commit = git_dict.get("commit") if isinstance(git_dict.get("commit"), str) else None
    dirty = git_dict.get("dirty")
    short_commit = commit[:8] if commit else None

    if git_status == "suppressed":
        findings.append(
            _make_finding(
                INFO,
                "git_off",
                "git/source-code state was not captured.",
                "Enable `[capture.git]` if you want it recorded.",
                category="source",
                evidence_status="unavailable",
                impact="informational",
            )
        )
    elif git_status == "timeout":
        detail = _capture_state_detail(git_dict)
        suffix = f" ({detail})" if detail else ""
        findings.append(
            _make_finding(
                WARN,
                "git_timeout",
                f"Git provenance capture timed out{suffix}; source commit and dirty state are unavailable.",
                "Increase `[capture.git].timeout` or check repository filesystem latency so source state is recorded.",
                category="source",
                evidence_status="unavailable",
                impact="material",
                details={"detail": detail} if detail else {},
            )
        )
    elif git_status == "failed":
        detail = _capture_state_detail(git_dict)
        suffix = f" ({detail})" if detail else ""
        findings.append(
            _make_finding(
                WARN,
                "git_failed",
                f"Git provenance capture failed{suffix}; source commit and dirty state are unavailable.",
                "Verify `git` is working in the repository so source provenance can be recorded.",
                category="source",
                evidence_status="unavailable",
                impact="material",
                details={"detail": detail} if detail else {},
            )
        )
    elif git_status == "partial":
        detail = _capture_state_detail(git_dict)
        suffix = f" ({detail})" if detail else ""
        findings.append(
            _make_finding(
                WARN,
                "git_partial",
                f"Git provenance capture was partial{suffix}; source identity may be incomplete.",
                "Inspect repository health and re-capture full git metadata for reproducible source tracking.",
                category="source",
                evidence_status="unavailable",
                impact="material",
                details={"detail": detail} if detail else {},
            )
        )
    elif git_status == "unavailable":
        detail = _capture_state_detail(git_dict)
        suffix = f" ({detail})" if detail else ""
        findings.append(
            _make_finding(
                INFO,
                "git_unavailable",
                f"Git source provenance is unavailable{suffix}.",
                "Run inside a Git repository with `git` installed to record commit and dirty state.",
                category="source",
                evidence_status="unavailable",
                impact="informational",
                details={"detail": detail} if detail else {},
            )
        )
    elif git_dict:
        if commit:
            has_diff = bool(git_dict.get("diff") or git_dict.get("patch"))
            if dirty is True and not has_diff:
                findings.append(
                    _make_finding(
                        WARN,
                        "git_dirty_unrecorded",
                        f"Git working tree was dirty at commit {short_commit} and uncommitted changes were not recorded.",
                        "Commit or stash changes before running (or save a `git diff` alongside the run) so the exact source state can be reproduced.",
                        category="source",
                        evidence_status=git_ev,
                        impact="material",
                        details={"commit": commit, "branch": git_dict.get("branch")},
                    )
                )
            elif dirty is None:
                findings.append(
                    _make_finding(
                        INFO,
                        "git_dirty_not_checked",
                        f"Git commit {short_commit} was recorded, but working-tree dirty state was not checked.",
                        "Enable `[capture.git].check_dirty = true` to verify whether uncommitted edits were present.",
                        category="source",
                        evidence_status="not_checked",
                        impact="informational",
                        details={"commit": commit},
                    )
                )
        else:
            findings.append(
                _make_finding(
                    INFO,
                    "git_commit_missing",
                    "No Git commit hash was recorded in the manifest.",
                    "Run inside a Git repository with at least one commit to record exact source revision.",
                    category="source",
                    evidence_status="unavailable",
                    impact="informational",
                )
            )

    invocation = manifest.get("invocation")
    inv_dict = invocation if isinstance(invocation, dict) else {}
    entrypoint_type = inv_dict.get("entrypoint_type")
    script = inv_dict.get("script") if isinstance(inv_dict.get("script"), dict) else {}
    script_sha256 = script.get("sha256") if isinstance(script.get("sha256"), str) else None

    if entrypoint_type == "script" and not script_sha256:
        skip_reason = script.get("sha256_skipped")
        reason_text = f" ({skip_reason})" if isinstance(skip_reason, str) and skip_reason else ""
        findings.append(
            _make_finding(
                INFO,
                "script_unhashed",
                f"Entrypoint script has no recorded SHA-256 content hash{reason_text}.",
                "Track the script in a clean Git commit or ensure it is within the script hash size limit so content identity is recorded.",
                category="source",
                evidence_status="not_checked",
                impact="informational",
                details={
                    "script_path": script.get("path"),
                    "sha256_skipped": skip_reason,
                },
            )
        )

    codes = [f["code"] for f in findings]
    warn_count = sum(1 for f in findings if f["severity"] == WARN)
    info_count = sum(1 for f in findings if f["severity"] == INFO)

    if any(f.get("comparison") == "mismatch" for f in findings):
        cat_status = "mismatch"
    elif warn_count > 0:
        cat_status = "gaps"
    elif (not git_dict or git_status == "suppressed") and not script_sha256:
        cat_status = "not_checked"
    elif any(
        code in codes
        for code in ("git_unavailable", "git_commit_missing", "git_dirty_not_checked", "script_unhashed")
    ):
        cat_status = "uncertain"
    else:
        cat_status = "adequate"

    if commit:
        cat_ev = git_ev
    elif script_sha256:
        cat_ev = "observed"
    elif git_status == "suppressed" or (not git_dict and not script):
        cat_ev = "not_checked"
    else:
        cat_ev = "unavailable"

    if cat_status == "adequate":
        src_note = " (inherited from parent snapshot)" if git_inherited else ""
        if commit:
            cat_summary = f"Clean Git commit {short_commit} recorded{src_note}."
        else:
            cat_summary = "Entrypoint script SHA-256 hash recorded."
    elif warn_count > 0:
        cat_summary = f"Source provenance has {warn_count} material gap(s)."
    elif cat_status == "not_checked":
        cat_summary = "Source-code provenance was not recorded."
    else:
        cat_summary = "Source provenance is incomplete or only partially verified."

    return findings, {
        "name": "source",
        "label": CATEGORY_LABELS["source"],
        "status": cat_status,
        "evidence_status": cat_ev,
        "summary": cat_summary,
        "finding_codes": codes,
        "warn_count": warn_count,
        "info_count": info_count,
    }


def _assess_runtime(
    manifest: Dict[str, Any],
    current_hostname: Optional[str],
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """Assess Python runtime, host platform, and hardware provenance."""
    findings: List[Dict[str, Any]] = []
    python_sec = manifest.get("python")
    host_sec = manifest.get("host")
    hw_sec = manifest.get("hardware")

    python_dict = python_sec if isinstance(python_sec, dict) else {}
    host_dict = host_sec if isinstance(host_sec, dict) else {}
    hw_dict = hw_sec if isinstance(hw_sec, dict) else {}

    py_status = _capture_state_status(python_dict)
    hw_status = _capture_state_status(hw_dict)

    run_host = _unwrap_hostname(host_dict.get("hostname"))
    if current_hostname and run_host and current_hostname != run_host:
        findings.append(
            _make_finding(
                WARN,
                "different_host",
                f"this run executed on '{run_host}', but you are inspecting from "
                f"'{current_hostname}'. Any live environment checks reflect THIS machine, "
                f"not where the run ran (common on HPC: run on a compute node, inspect on "
                f"the head node).",
                None,
                category="runtime",
                evidence_status="observed",
                impact="portability",
                comparison="portability_diff",
                details={
                    "recorded_hostname": run_host,
                    "current_hostname": current_hostname,
                },
            )
        )

    if hw_status == "suppressed":
        findings.append(
            _make_finding(
                INFO,
                "hardware_off",
                "hardware was not captured.",
                "Enable `[capture.hardware]` if you want it recorded.",
                category="runtime",
                evidence_status="unavailable",
                impact="informational",
            )
        )

    has_python = bool(python_dict.get("version"))
    has_host_os = bool(host_dict.get("os_name"))

    if not has_python and py_status not in ("failed", "timeout", "partial"):
        findings.append(
            _make_finding(
                INFO,
                "python_runtime_missing",
                "Python interpreter version was not recorded in the manifest.",
                "Enable Python runtime capture so interpreter version and environment kind are documented.",
                category="runtime",
                evidence_status="unavailable",
                impact="informational",
            )
        )

    if not has_host_os and _capture_state_status(host_dict) not in (
        "failed",
        "timeout",
        "partial",
    ):
        findings.append(
            _make_finding(
                INFO,
                "host_info_missing",
                "Host operating system details were not recorded in the manifest.",
                "Ensure host metadata capture is enabled to record OS and platform identity.",
                category="runtime",
                evidence_status="unavailable",
                impact="informational",
            )
        )

    codes = [f["code"] for f in findings]
    warn_count = sum(1 for f in findings if f["severity"] == WARN)
    info_count = sum(1 for f in findings if f["severity"] == INFO)

    any_inherited = bool(python_dict.get("is_hydrated") or hw_dict.get("is_hydrated"))
    if any_inherited and (has_python or hw_dict):
        cat_ev = "inherited"
    elif has_python or has_host_os:
        cat_ev = "observed"
    elif not python_dict and not host_dict and not hw_dict:
        cat_ev = "not_checked"
    else:
        cat_ev = "unavailable"

    if any(f.get("comparison") == "mismatch" for f in findings):
        cat_status = "mismatch"
    elif any(f["severity"] == WARN and f.get("impact") == "material" for f in findings):
        cat_status = "gaps"
    elif not python_dict and not host_dict and not hw_dict:
        cat_status = "not_checked"
    elif codes:
        cat_status = "uncertain"
    else:
        cat_status = "adequate"

    if cat_status == "adequate":
        note = " (partially inherited from parent snapshot)" if any_inherited else ""
        cat_summary = f"Python runtime, host OS, and hardware metadata recorded{note}."
    elif "different_host" in codes:
        cat_summary = (
            f"Run executed on '{run_host}' rather than current host '{current_hostname}'."
        )
    elif cat_status == "not_checked":
        cat_summary = "Runtime and host metadata were not recorded."
    else:
        cat_summary = "Runtime or hardware metadata is incomplete."

    return findings, {
        "name": "runtime",
        "label": CATEGORY_LABELS["runtime"],
        "status": cat_status,
        "evidence_status": cat_ev,
        "summary": cat_summary,
        "finding_codes": codes,
        "warn_count": warn_count,
        "info_count": info_count,
    }


def _assess_dependencies(
    manifest: Dict[str, Any],
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """Assess captured Python package dependency inventory and mode caveats."""
    findings: List[Dict[str, Any]] = []
    pkg_sec = manifest.get("packages")
    pkg_dict = pkg_sec if isinstance(pkg_sec, dict) else {}
    pkg_status = _capture_state_status(pkg_dict)
    pkg_inherited = bool(pkg_dict.get("is_hydrated"))
    pkg_ev = "inherited" if pkg_inherited else "observed"

    if pkg_status == "suppressed":
        findings.append(
            _make_finding(
                INFO,
                "packages_off",
                "package inventory was not captured.",
                "Enable `[capture.packages]` if you want it recorded.",
                category="dependencies",
                evidence_status="unavailable",
                impact="informational",
            )
        )
    elif pkg_status == "partial":
        detail = _capture_state_detail(pkg_dict)
        suffix = f" ({detail})" if detail else ""
        findings.append(
            _make_finding(
                WARN,
                "packages_partial",
                f"Package inventory capture was partial{suffix}; some dependencies may be missing.",
                "Check package metadata errors and re-run with full package capture enabled.",
                category="dependencies",
                evidence_status="unavailable",
                impact="material",
                details={"detail": detail} if detail else {},
            )
        )
    elif pkg_status in ("failed", "timeout"):
        detail = _capture_state_detail(pkg_dict)
        suffix = f" ({detail})" if detail else ""
        findings.append(
            _make_finding(
                WARN,
                "packages_failed",
                f"Package inventory capture {pkg_status}{suffix}; dependency versions are unavailable.",
                "Inspect environment metadata health and re-capture package versions.",
                category="dependencies",
                evidence_status="unavailable",
                impact="material",
                details={"status": pkg_status, "detail": detail},
            )
        )
    elif pkg_status == "unavailable":
        detail = _capture_state_detail(pkg_dict)
        suffix = f" ({detail})" if detail else ""
        findings.append(
            _make_finding(
                INFO,
                "packages_unavailable",
                f"Package inventory is unavailable{suffix}.",
                "Verify `importlib.metadata` is accessible in the Python environment.",
                category="dependencies",
                evidence_status="unavailable",
                impact="informational",
                details={"detail": detail} if detail else {},
            )
        )
    elif pkg_dict:
        records = pkg_dict.get("records")
        valid_records = (
            [r for r in records if isinstance(r, dict)]
            if isinstance(records, list)
            else []
        )
        mode = pkg_dict.get("mode") if isinstance(pkg_dict.get("mode"), str) else None

        if pkg_status == "complete" and isinstance(records, list) and len(valid_records) == 0 and mode:
            findings.append(
                _make_finding(
                    INFO,
                    "packages_empty",
                    f"Package capture completed in '{mode}' mode with zero third-party packages recorded.",
                    "Confirm whether the run used only the Python standard library or whether dependencies were imported after snapshot.",
                    category="dependencies",
                    evidence_status=pkg_ev,
                    impact="informational",
                    details={"mode": mode},
                )
            )

        if mode == "imported-only":
            findings.append(
                _make_finding(
                    INFO,
                    "packages_imported_only_scope",
                    "Package capture used 'imported-only' mode, which records only directly imported modules and may miss transitive or unrecorded environment packages.",
                    'Use `[capture.packages].mode = "full-environment"` or `"imported-transitive"` for broader dependency coverage.',
                    category="dependencies",
                    evidence_status=pkg_ev,
                    impact="informational",
                    details={"mode": mode, "record_count": len(valid_records)},
                )
            )

        editable_names = [
            str(r["name"])
            for r in valid_records
            if r.get("editable") is True and r.get("name")
        ]
        if editable_names:
            preview = ", ".join(editable_names[:5])
            extra = "" if len(editable_names) <= 5 else f" (+{len(editable_names) - 5} more)"
            findings.append(
                _make_finding(
                    INFO,
                    "packages_editable_present",
                    f"{len(editable_names)} editable package install(s) recorded ({preview}{extra}); editable packages depend on local source state beyond version numbers.",
                    "Record clean Git commits for editable dependencies or install versioned wheels before archiving results.",
                    category="dependencies",
                    evidence_status=pkg_ev,
                    impact="portability",
                    details={
                        "count": len(editable_names),
                        "packages": editable_names[:20],
                    },
                )
            )

        # Defensive inspection of optional richer fields from sibling Set dep-capture (w4hxkh).
        unresolved = pkg_dict.get("unresolved")
        if isinstance(unresolved, list) and len(unresolved) > 0:
            findings.append(
                _make_finding(
                    INFO,
                    "packages_unresolved_modules",
                    f"{len(unresolved)} imported module(s) could not be mapped to an installed distribution.",
                    "Inspect `packages.unresolved` for local, namespace, or ambiguous modules that may require manual pinning.",
                    category="dependencies",
                    evidence_status="unavailable",
                    impact="informational",
                    details={"count": len(unresolved)},
                )
            )

        snapshot_stage = pkg_dict.get("snapshot_stage")
        if snapshot_stage == "startup":
            findings.append(
                _make_finding(
                    INFO,
                    "packages_startup_snapshot",
                    "Package inventory was captured at startup; modules imported later during execution may not be listed.",
                    "Use finalization-stage package capture or `full-environment` mode to capture late imports.",
                    category="dependencies",
                    evidence_status=pkg_ev,
                    impact="informational",
                    details={"snapshot_stage": snapshot_stage},
                )
            )

    codes = [f["code"] for f in findings]
    warn_count = sum(1 for f in findings if f["severity"] == WARN)
    info_count = sum(1 for f in findings if f["severity"] == INFO)

    if any(f.get("comparison") == "mismatch" for f in findings):
        cat_status = "mismatch"
    elif warn_count > 0:
        cat_status = "gaps"
    elif not pkg_dict or pkg_status == "suppressed":
        cat_status = "not_checked"
    elif codes:
        cat_status = "uncertain"
    else:
        cat_status = "adequate"

    if pkg_status == "suppressed" or not pkg_dict:
        cat_ev = "not_checked"
    elif pkg_status in ("partial", "failed", "timeout", "unavailable"):
        cat_ev = "unavailable"
    else:
        cat_ev = pkg_ev

    if cat_status == "adequate":
        count = len(pkg_dict.get("records") or []) if isinstance(pkg_dict.get("records"), list) else 0
        note = " (inherited from parent snapshot)" if pkg_inherited else ""
        cat_summary = f"Recorded {count} package version(s){note}."
    elif warn_count > 0:
        cat_summary = "Package dependency capture was incomplete or failed."
    elif cat_status == "not_checked":
        cat_summary = "Package inventory was not captured."
    else:
        cat_summary = "Package inventory was recorded with coverage or editable-install caveats."

    return findings, {
        "name": "dependencies",
        "label": CATEGORY_LABELS["dependencies"],
        "status": cat_status,
        "evidence_status": cat_ev,
        "summary": cat_summary,
        "finding_codes": codes,
        "warn_count": warn_count,
        "info_count": info_count,
    }


def _record_is_asserted(rec: Dict[str, Any]) -> bool:
    """Return True when a file provenance record carries an asserted caller digest."""
    if rec.get("evidence_source") == "asserted" or rec.get("source") == "asserted":
        return True
    if rec.get("hash_status") == "asserted":
        return True
    caller_digest = rec.get("caller_digest")
    has_observed_digest = bool(rec.get("sha256")) or (
        isinstance(rec.get("digest"), dict) and bool(rec["digest"].get("value"))
    )
    return isinstance(caller_digest, dict) and bool(caller_digest.get("value")) and not has_observed_digest


def _record_has_observed_digest(rec: Dict[str, Any]) -> bool:
    """Return True when a file provenance record carries an observed content hash."""
    if _record_is_asserted(rec):
        return False
    if isinstance(rec.get("sha256"), str) and rec["sha256"]:
        return True
    digest = rec.get("digest")
    if isinstance(digest, dict) and isinstance(digest.get("value"), str) and digest["value"]:
        return True
    if isinstance(rec.get("md5"), str) and rec["md5"]:
        return True
    return False


def _assess_inputs_outputs(
    manifest: Dict[str, Any],
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """Assess recorded data-file provenance and argv-inferred input files."""
    findings: List[Dict[str, Any]] = []

    data_files = manifest.get("data_files")
    df_dict = data_files if isinstance(data_files, dict) else {}
    df_inputs = df_dict.get("inputs") if isinstance(df_dict.get("inputs"), list) else []
    df_outputs = df_dict.get("outputs") if isinstance(df_dict.get("outputs"), list) else []
    df_mixed = df_dict.get("mixed") if isinstance(df_dict.get("mixed"), list) else []
    all_df = [r for r in (df_inputs + df_outputs + df_mixed) if isinstance(r, dict)]

    invocation = manifest.get("invocation")
    inv_dict = invocation if isinstance(invocation, dict) else {}
    inv_inputs_raw = inv_dict.get("inputs") if isinstance(inv_dict.get("inputs"), list) else []
    inv_inputs = [r for r in inv_inputs_raw if isinstance(r, dict)]

    if not all_df and not inv_inputs:
        findings.append(
            _make_finding(
                INFO,
                "no_file_provenance",
                "no file-I/O provenance was recorded - pubrun does NOT patch open() "
                "globally, so file reads/writes are only recorded if the script calls "
                "`pubrun.open()` (or `pubrun.subprocess`).",
                "Use `pubrun.open(...)` in place of `open(...)` to record input/output "
                "files (path + hash).",
                category="inputs_outputs",
                evidence_status="not_checked",
                impact="informational",
            )
        )
        return findings, {
            "name": "inputs_outputs",
            "label": CATEGORY_LABELS["inputs_outputs"],
            "status": "not_checked",
            "evidence_status": "not_checked",
            "summary": "No tracked data files or argv-inferred inputs were recorded.",
            "finding_codes": ["no_file_provenance"],
            "warn_count": 0,
            "info_count": 1,
        }

    observed_hashed_count = 0
    asserted_count = 0
    stat_only_count = 0
    changed_count = 0
    over_budget_count = 0
    failed_hash_count = 0

    if not all_df and inv_inputs:
        findings.append(
            _make_finding(
                INFO,
                "inputs_argv_inferred_only",
                f"{len(inv_inputs)} input path(s) were inferred heuristically from command-line arguments, and `pubrun.open()` file provenance was not used.",
                "Use `pubrun.open(...)` or `pubrun.register_input(...)` to record observed input and output file provenance.",
                category="inputs_outputs",
                evidence_status="inferred",
                impact="informational",
                details={"inferred_count": len(inv_inputs)},
            )
        )
        unhashed_inferred = [
            r for r in inv_inputs if not r.get("is_dir") and not r.get("md5") and not r.get("sha256")
        ]
        if unhashed_inferred:
            findings.append(
                _make_finding(
                    INFO,
                    "inputs_unhashed",
                    f"{len(unhashed_inferred)} argv-inferred input file(s) recorded stat metadata only; content hashes are not checked.",
                    'Enable `[capture.inputs].compute_md5 = true` or use `pubrun.open()` with `[capture.file_io].level = "hash"`.',
                    category="inputs_outputs",
                    evidence_status="not_checked",
                    impact="informational",
                    details={"unhashed_count": len(unhashed_inferred)},
                )
            )
    else:
        for rec in all_df:
            hash_status = rec.get("hash_status")
            if hash_status == "file_changed" or rec.get("change_detected") is True:
                changed_count += 1
            elif hash_status == "over_budget":
                over_budget_count += 1
            elif hash_status in ("failed", "unavailable"):
                failed_hash_count += 1
            elif _record_is_asserted(rec):
                asserted_count += 1
            elif _record_has_observed_digest(rec):
                observed_hashed_count += 1
            else:
                if rec.get("entry_type") not in ("directory", "unsupported_remote_uri"):
                    stat_only_count += 1

        if changed_count > 0:
            findings.append(
                _make_finding(
                    WARN,
                    "file_hash_changed",
                    f"{changed_count} tracked file(s) changed while hashing or during capture; recorded content digest may not match the bytes consumed.",
                    "Avoid mutating input or output files concurrently while a tracked run is hashing them.",
                    category="inputs_outputs",
                    evidence_status="observed",
                    impact="material",
                    details={"count": changed_count},
                )
            )
        if failed_hash_count > 0:
            findings.append(
                _make_finding(
                    WARN,
                    "file_hash_unavailable",
                    f"Content hashing failed or the file was unavailable for {failed_hash_count} tracked file(s).",
                    "Ensure tracked files remain readable until capture finalizes.",
                    category="inputs_outputs",
                    evidence_status="unavailable",
                    impact="material",
                    details={"count": failed_hash_count},
                )
            )
        if over_budget_count > 0:
            findings.append(
                _make_finding(
                    INFO,
                    "file_hash_over_budget",
                    f"{over_budget_count} tracked file(s) exceeded the hashing size or time budget; content hashes are not checked.",
                    "Increase `[capture.file_io]` hash budget limits or register verified external digests if full content hashing is required.",
                    category="inputs_outputs",
                    evidence_status="not_checked",
                    impact="informational",
                    details={"count": over_budget_count},
                )
            )
        if asserted_count > 0:
            findings.append(
                _make_finding(
                    INFO,
                    "file_provenance_asserted_only",
                    f"{asserted_count} tracked file(s) carry caller-asserted digests rather than pubrun-observed content hashes.",
                    "Hash files directly with `pubrun.open()` or verify asserted digests before relying on content equality.",
                    category="inputs_outputs",
                    evidence_status="asserted",
                    impact="informational",
                    details={"count": asserted_count},
                )
            )
        if stat_only_count > 0:
            findings.append(
                _make_finding(
                    INFO,
                    "file_provenance_unhashed",
                    f"{stat_only_count} tracked file(s) recorded stat metadata only (size/mtime); content hash is not checked.",
                    'Set `[capture.file_io].level = "hash"` to record SHA-256 content digests for tracked files.',
                    category="inputs_outputs",
                    evidence_status="not_checked",
                    impact="informational",
                    details={"count": stat_only_count},
                )
            )

    codes = [f["code"] for f in findings]
    warn_count = sum(1 for f in findings if f["severity"] == WARN)
    info_count = sum(1 for f in findings if f["severity"] == INFO)

    if any(f.get("comparison") == "mismatch" for f in findings):
        cat_status = "mismatch"
    elif warn_count > 0:
        cat_status = "gaps"
    elif codes:
        cat_status = "uncertain"
    else:
        cat_status = "adequate"

    if observed_hashed_count > 0:
        cat_ev = "observed"
    elif asserted_count > 0:
        cat_ev = "asserted"
    elif not all_df and inv_inputs:
        cat_ev = "inferred"
    elif failed_hash_count > 0:
        cat_ev = "unavailable"
    elif stat_only_count > 0:
        cat_ev = "observed"
    else:
        cat_ev = "not_checked"

    if cat_status == "adequate":
        cat_summary = f"Observed content digests recorded for {observed_hashed_count} tracked file(s)."
    elif warn_count > 0:
        cat_summary = "One or more tracked files had hashing failures or concurrent modifications."
    elif not all_df and inv_inputs:
        cat_summary = f"Only argv-inferred paths ({len(inv_inputs)}) were recorded without `pubrun.open()` provenance."
    elif asserted_count > 0 and observed_hashed_count == 0:
        cat_summary = f"{asserted_count} file(s) carry caller-asserted digests rather than observed hashes."
    else:
        cat_summary = "Tracked file provenance is partially unhashed (stat-only or over-budget)."

    return findings, {
        "name": "inputs_outputs",
        "label": CATEGORY_LABELS["inputs_outputs"],
        "status": cat_status,
        "evidence_status": cat_ev,
        "summary": cat_summary,
        "finding_codes": codes,
        "warn_count": warn_count,
        "info_count": info_count,
    }


def _recorded_network_fs_findings(fs_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Produce manifest-scoped network filesystem findings matching ``checks.py``."""
    findings: List[Dict[str, Any]] = []
    human = {
        "pubrun_install": (
            "pubrun is installed on a network filesystem",
            "Consider a node-local venv (e.g. on local scratch / $TMPDIR) or "
            "`pip install --target` to local disk; import/startup over NFS/Lustre "
            "can be markedly slower.",
        ),
        "output_dir": (
            "the run output directory is on a network filesystem",
            "Consider setting `[core].output_dir` to node-local storage and copying "
            "results back afterward; pubrun writes to this dir throughout a run.",
        ),
        "tmpdir": (
            "$TMPDIR is on a network filesystem",
            "Point $TMPDIR at node-local storage for faster temp I/O.",
        ),
    }
    for label, entry in fs_data.items():
        if label == "capture_state" or not isinstance(entry, dict):
            continue
        if entry.get("is_network"):
            title, sugg = human.get(label, (f"{label} is on a network filesystem", None))
            mp = entry.get("mount_point", entry.get("path", "?"))
            ft = entry.get("fstype", "?")
            findings.append(
                _make_finding(
                    WARN,
                    f"netfs_{label}",
                    f"this run's {title} ({mp}, {ft}).",
                    sugg,
                    category="capture_completeness",
                    evidence_status="observed",
                    impact="portability",
                    details={"label": label, "mount_point": mp, "fstype": ft},
                )
            )
    return findings


def _assess_capture_completeness(
    manifest: Dict[str, Any],
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """Assess run outcome, capture states, config notices, subprocesses, and determinism."""
    findings: List[Dict[str, Any]] = []

    # 1. Run outcome.
    status_sec = manifest.get("status")
    if isinstance(status_sec, dict):
        outcome = status_sec.get("outcome")
        if isinstance(outcome, str) and outcome in _NON_COMPLETED_OUTCOMES:
            findings.append(
                _make_finding(
                    WARN,
                    "run_outcome_incomplete",
                    f"Run outcome is '{outcome}' rather than 'completed'; outputs and provenance may be incomplete.",
                    "Inspect run logs and errors before relying on or reproducing this run.",
                    category="capture_completeness",
                    evidence_status="observed",
                    impact="material",
                    details={
                        "outcome": outcome,
                        "exit_code": status_sec.get("exit_code"),
                    },
                )
            )

    # 2. Recorded config notices (preserves checks.py).
    cfg = manifest.get("config")
    if isinstance(cfg, dict):
        for notice in cfg.get("notices", []) or []:
            if not isinstance(notice, dict):
                continue
            findings.append(
                _make_finding(
                    WARN,
                    notice.get("code", "config_notice"),
                    notice.get("message", "a config setting was ignored or deprecated."),
                    "Update your pubrun configuration; see docs/configuration.md.",
                    category="capture_completeness",
                    evidence_status="observed",
                    impact="informational",
                )
            )

    # 3. Recorded network-filesystem signals (preserves checks.py).
    fs_data = manifest.get("filesystem")
    if isinstance(fs_data, dict):
        findings.extend(_recorded_network_fs_findings(fs_data))

    # 4. Resources & console (preserves checks.py).
    res = manifest.get("resources")
    res_status = _capture_state_status(res)
    if res_status == "suppressed":
        findings.append(
            _make_finding(
                WARN,
                "resources_off",
                "resource monitoring was OFF (no RSS/CPU/RAM/load recorded).",
                "Set `[capture.resources].depth` to `standard` to record resource usage "
                "(low overhead; see docs/performance.md).",
                category="capture_completeness",
                evidence_status="unavailable",
                impact="informational",
            )
        )
    elif isinstance(res, dict) and res.get("scope") not in ("tree", None):
        findings.append(
            _make_finding(
                WARN,
                "resources_process_scope",
                "process-tree resources were NOT captured (only the main process).",
                'Set `[capture.resources].scope = "tree"` to sum RSS/CPU across child '
                "processes (multiprocessing/Dask/Ray). Slight extra sampling cost.",
                category="capture_completeness",
                evidence_status="observed",
                impact="informational",
            )
        )

    console = manifest.get("console")
    if isinstance(console, dict) and console.get("capture_mode") == "off":
        findings.append(
            _make_finding(
                INFO,
                "console_off",
                "console output was not captured (capture_mode = off).",
                'Set `[console].capture_mode = "standard"` to record stdout/stderr.',
                category="capture_completeness",
                evidence_status="unavailable",
                impact="informational",
            )
        )

    # 5. Scan remaining top-level sections for failed/timeout/partial/pending capture_state.
    # git and packages have dedicated findings in their owning categories.
    _dedicated_capture_sections = frozenset(("git", "packages"))
    for sec_name, sec_val in manifest.items():
        if not isinstance(sec_val, dict):
            continue
        st = _capture_state_status(sec_val)
        if st in ("failed", "timeout", "partial") and sec_name not in _dedicated_capture_sections:
            detail = _capture_state_detail(sec_val)
            suffix = f" ({detail})" if detail else ""
            findings.append(
                _make_finding(
                    WARN,
                    f"{sec_name}_capture_{st}",
                    f"Section '{sec_name}' capture ended with status '{st}'{suffix}.",
                    f"Inspect errors or configuration for `{sec_name}` capture so provenance is complete.",
                    category="capture_completeness",
                    evidence_status="unavailable",
                    impact="material",
                    details={"section": sec_name, "status": st, "detail": detail},
                )
            )
        elif st == "pending":
            findings.append(
                _make_finding(
                    INFO,
                    f"{sec_name}_capture_pending",
                    f"Section '{sec_name}' capture was still pending when the manifest was written.",
                    "Confirm that the run finalized cleanly so deferred sections complete.",
                    category="capture_completeness",
                    evidence_status="not_checked",
                    impact="informational",
                    details={"section": sec_name, "status": st},
                )
            )

    # 6. Optional errors.records capture-error entries (defensive tolerance for x21s6w).
    errors_sec = manifest.get("errors")
    if isinstance(errors_sec, dict) and isinstance(errors_sec.get("records"), list):
        cap_errors = [
            e
            for e in errors_sec["records"]
            if isinstance(e, dict) and e.get("kind") == "capture-error"
        ]
        if cap_errors:
            findings.append(
                _make_finding(
                    WARN,
                    "capture_errors_recorded",
                    f"{len(cap_errors)} capture-error record(s) were logged during provenance capture.",
                    "Inspect `errors.records` in the manifest to identify which capture probes failed.",
                    category="capture_completeness",
                    evidence_status="observed",
                    impact="material",
                    details={"count": len(cap_errors)},
                )
            )

    # 7. Import mode subprocess patching permission (preserves checks.py).
    imports = manifest.get("pubrun_imports")
    behavior = imports.get("selected_behavior", {}) if isinstance(imports, dict) else {}
    if isinstance(behavior, dict) and behavior.get("patch_subprocesses") is False:
        findings.append(
            _make_finding(
                INFO,
                "mode_no_subprocess_patch",
                f"the import mode ('{imports.get('selected_mode')}') did not permit "
                "subprocess tracking.",
                "Use the default `import pubrun` (auto) mode to allow subprocess capture.",
                category="capture_completeness",
                evidence_status="not_checked",
                impact="informational",
            )
        )

    # 8. Subprocess tracking flag vs empty subprocess list (preserves checks.py).
    cap = manifest.get("capture")
    subs = manifest.get("subprocesses")
    subs_list = subs if isinstance(subs, list) else []
    sub_flag = cap.get("subprocesses_enabled") if isinstance(cap, dict) else None
    if sub_flag is False:
        findings.append(
            _make_finding(
                WARN,
                "subprocess_tracking_off",
                "subprocess tracking was OFF - no child processes were recorded.",
                "Enable `[capture.subprocesses].enabled = true` to record subprocess calls.",
                category="capture_completeness",
                evidence_status="unavailable",
                impact="material",
            )
        )
    elif sub_flag is None and not subs_list:
        findings.append(
            _make_finding(
                INFO,
                "subprocess_unknown",
                "no subprocesses were recorded - either subprocess tracking was disabled "
                "or none were spawned (this run's manifest predates the enabled-flag, so it "
                "cannot be determined).",
                "pubrun records subprocesses only when `[capture.subprocesses]` is enabled.",
                category="capture_completeness",
                evidence_status="unavailable",
                impact="informational",
            )
        )

    # 9. Determinism / random seeds.
    det = manifest.get("determinism")
    registered_seeds = det.get("registered_seeds") if isinstance(det, dict) else None
    if not isinstance(registered_seeds, list) or len(registered_seeds) == 0:
        findings.append(
            _make_finding(
                INFO,
                "determinism_seeds_not_recorded",
                "No random seeds were registered; nondeterminism in numerical or ML libraries is not tracked automatically.",
                "Register random seeds explicitly if your workflow requires deterministic random state.",
                category="capture_completeness",
                evidence_status="not_checked",
                impact="informational",
            )
        )

    # 10. Sparse or legacy manifest detection.
    present_core = sum(
        1 for sec in _CORE_MANIFEST_SECTIONS if isinstance(manifest.get(sec), dict)
    )
    has_schema_version = isinstance(manifest.get("schema_version"), str) and bool(
        manifest.get("schema_version")
    )
    has_capture_flags = isinstance(cap, dict) and "subprocesses_enabled" in cap
    is_sparse_or_legacy = (not has_schema_version) or (not has_capture_flags) or (present_core < 4)
    if is_sparse_or_legacy:
        findings.append(
            _make_finding(
                INFO,
                "sparse_or_legacy_manifest",
                "This manifest is sparse or uses a legacy format (missing schema_version, capture flags, or core sections); absence of warnings does not imply complete provenance.",
                "Re-run with a current version of pubrun to capture full structured provenance.",
                category="capture_completeness",
                evidence_status="unavailable",
                impact="informational",
                details={
                    "has_schema_version": has_schema_version,
                    "has_capture_flags": has_capture_flags,
                    "present_core_sections": present_core,
                },
            )
        )

    codes = [f["code"] for f in findings]
    warn_count = sum(1 for f in findings if f["severity"] == WARN)
    info_count = sum(1 for f in findings if f["severity"] == INFO)

    # Informational-only determinism reminder does not downgrade an otherwise adequate manifest.
    non_seed_info = [
        f for f in findings if f["severity"] == INFO and f["code"] != "determinism_seeds_not_recorded"
    ]

    if any(f.get("comparison") == "mismatch" for f in findings):
        cat_status = "mismatch"
    elif warn_count > 0:
        cat_status = "gaps"
    elif non_seed_info:
        cat_status = "uncertain"
    else:
        cat_status = "adequate"

    if is_sparse_or_legacy and present_core == 0:
        cat_ev = "unavailable"
    else:
        cat_ev = "observed"

    if cat_status == "adequate":
        cat_summary = "Run completed with expected capture sections recorded."
    elif warn_count > 0:
        cat_summary = f"Capture completeness has {warn_count} warning(s)."
    else:
        cat_summary = "Manifest capture completeness has informational gaps or legacy omissions."

    return findings, {
        "name": "capture_completeness",
        "label": CATEGORY_LABELS["capture_completeness"],
        "status": cat_status,
        "evidence_status": cat_ev,
        "summary": cat_summary,
        "finding_codes": codes,
        "warn_count": warn_count,
        "info_count": info_count,
    }


def _assess_parent_metadata(
    manifest: Dict[str, Any],
    hydration_dict: Optional[Dict[str, Any]],
    stale_parent_seconds: Optional[float],
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """Assess parent ``meta_ref`` snapshot hydration availability, age, and identity."""
    findings: List[Dict[str, Any]] = []

    if hydration_dict is not None:
        status = hydration_dict.get("status", "none")
        meta_ref = hydration_dict.get("meta_ref")
        inherited = list(hydration_dict.get("inherited_sections") or [])
        direct = list(hydration_dict.get("direct_sections") or [])
        age_seconds = hydration_dict.get("age_seconds")
        script_drift = hydration_dict.get("script_modified_after_parent")
        mismatches = list(hydration_dict.get("identity_mismatches") or [])

        if status == "none":
            return findings, {
                "name": "parent_metadata",
                "label": CATEGORY_LABELS["parent_metadata"],
                "status": "adequate",
                "evidence_status": "observed",
                "summary": "No parent meta_ref snapshot referenced; all recorded sections come directly from this run.",
                "finding_codes": [],
                "warn_count": 0,
                "info_count": 0,
            }

        if status in (
            "missing",
            "blocked_by_policy",
            "invalid_extension",
            "invalid_json",
            "invalid_type",
            "failed",
        ):
            suggestion_map = {
                "missing": "Restore or locate the parent `meta.json` snapshot referenced by `meta_ref`, or re-run with direct capture enabled.",
                "blocked_by_policy": "Configure `[report].meta_ref_allowed_dirs` or `[report].allow_external_meta_ref = true` if this external parent snapshot is trusted.",
                "invalid_extension": "Ensure `meta_ref` points to a `.json` snapshot produced by `pubrun meta`.",
                "invalid_json": "Verify that the parent `meta.json` file is intact and valid JSON.",
                "invalid_type": "Verify that `meta_ref` points to a valid `pubrun-meta-snapshot` JSON object.",
                "failed": "Inspect parent `meta.json` readability and permissions, then re-run inspection.",
            }
            warnings_list = hydration_dict.get("warnings") or []
            detail_msg = (
                warnings_list[0]
                if warnings_list
                else f"Parent meta_ref '{meta_ref}' hydration failed with status '{status}'."
            )
            findings.append(
                _make_finding(
                    WARN,
                    f"parent_metadata_{status}",
                    f"Parent metadata snapshot could not be loaded ({status}): {detail_msg}",
                    suggestion_map[status],
                    category="parent_metadata",
                    evidence_status="unavailable",
                    impact="material",
                    details={
                        "meta_ref": meta_ref,
                        "resolved_path": hydration_dict.get("resolved_path"),
                        "hydration_status": status,
                    },
                )
            )
            return findings, {
                "name": "parent_metadata",
                "label": CATEGORY_LABELS["parent_metadata"],
                "status": "gaps",
                "evidence_status": "unavailable",
                "summary": f"Parent snapshot '{meta_ref}' is unavailable ({status}); missing sections were not invented.",
                "finding_codes": [f"parent_metadata_{status}"],
                "warn_count": 1,
                "info_count": 0,
            }

        # status == "hydrated"
        if script_drift is True:
            findings.append(
                _make_finding(
                    WARN,
                    "parent_metadata_script_drift",
                    "The child script was modified after the parent meta.json snapshot was created; inherited environment and dependency sections may be out of sync.",
                    "Regenerate the parent `meta.json` snapshot (`pubrun meta`) after script or environment changes before launching child runs.",
                    category="parent_metadata",
                    evidence_status="inherited",
                    impact="material",
                    details={
                        "meta_ref": meta_ref,
                        "inherited_sections": inherited,
                    },
                )
            )

        if isinstance(age_seconds, (int, float)) and not isinstance(age_seconds, bool):
            if age_seconds < 0:
                findings.append(
                    _make_finding(
                        WARN,
                        "parent_metadata_postdated",
                        f"Parent meta.json snapshot timestamp is newer than the child run start time by {_format_age(age_seconds)} (post-dated parent snapshot).",
                        "Verify that `meta_ref` points to the snapshot taken before this child run and check cluster clock synchronization.",
                        category="parent_metadata",
                        evidence_status="inherited",
                        impact="material",
                        details={"age_seconds": age_seconds, "meta_ref": meta_ref},
                    )
                )
            elif stale_parent_seconds is not None and age_seconds > stale_parent_seconds:
                findings.append(
                    _make_finding(
                        INFO,
                        "parent_metadata_stale",
                        f"Parent meta.json snapshot was {_format_age(age_seconds)} old when the child run started (threshold: {_format_age(stale_parent_seconds)}).",
                        "Refresh the parent `meta.json` snapshot if packages or system state changed while the job waited in the queue.",
                        category="parent_metadata",
                        evidence_status="inherited",
                        impact="informational",
                        details={
                            "age_seconds": age_seconds,
                            "threshold_seconds": stale_parent_seconds,
                            "meta_ref": meta_ref,
                        },
                    )
                )

        if mismatches:
            fields_desc = ", ".join(
                f"{m.get('field')} (parent={m.get('parent')!r}, child={m.get('child')!r})"
                for m in mismatches
            )
            findings.append(
                _make_finding(
                    WARN,
                    "parent_metadata_identity_mismatch",
                    f"Parent meta.json snapshot identity differs from directly observed child fields: {fields_desc}.",
                    "Confirm the parent snapshot matches the child execution environment or capture those sections directly on the child run.",
                    category="parent_metadata",
                    evidence_status="inherited",
                    impact="material",
                    comparison="mismatch",
                    details={"mismatches": mismatches, "meta_ref": meta_ref},
                )
            )

        if inherited:
            inherited_str = ", ".join(inherited)
            direct_str = ", ".join(direct) if direct else "none"
            findings.append(
                _make_finding(
                    INFO,
                    "parent_metadata_inherited",
                    f"Sections inherited from parent snapshot '{meta_ref}': {inherited_str} (direct child sections: {direct_str}). Inherited context reflects the parent snapshot, and script mtime alone does not prove dependencies matched at child runtime.",
                    "Capture critical sections directly in the child run when per-node dependency or runtime verification is required.",
                    category="parent_metadata",
                    evidence_status="inherited",
                    impact="informational",
                    details={
                        "meta_ref": meta_ref,
                        "inherited_sections": inherited,
                        "direct_sections": direct,
                    },
                )
            )

        codes = [f["code"] for f in findings]
        warn_count = sum(1 for f in findings if f["severity"] == WARN)
        info_count = sum(1 for f in findings if f["severity"] == INFO)

        if mismatches:
            cat_status = "mismatch"
        elif warn_count > 0:
            cat_status = "gaps"
        elif "parent_metadata_stale" in codes:
            cat_status = "uncertain"
        else:
            cat_status = "adequate"

        cat_ev = "inherited" if inherited else "observed"
        if cat_status == "mismatch":
            cat_summary = f"Parent snapshot '{meta_ref}' disagrees with directly observed child identity."
        elif cat_status == "gaps":
            cat_summary = f"Parent snapshot '{meta_ref}' has drift or timestamp anomalies."
        elif cat_status == "uncertain":
            cat_summary = f"Parent snapshot '{meta_ref}' was hydrated ({len(inherited)} inherited section(s)) but exceeded the staleness threshold."
        elif inherited:
            cat_summary = f"Hydrated {len(inherited)} section(s) from parent snapshot '{meta_ref}' ({', '.join(inherited)})."
        else:
            cat_summary = f"Parent snapshot '{meta_ref}' verified; all hydrable sections were already captured directly on the child."

        return findings, {
            "name": "parent_metadata",
            "label": CATEGORY_LABELS["parent_metadata"],
            "status": cat_status,
            "evidence_status": cat_ev,
            "summary": cat_summary,
            "finding_codes": codes,
            "warn_count": warn_count,
            "info_count": info_count,
        }

    # No HydrationReport supplied: inspect raw manifest.
    raw_meta_ref = manifest.get("meta_ref")
    hydrated_sections = [
        sec
        for sec in HYDRABLE_SECTIONS
        if isinstance(manifest.get(sec), dict) and manifest[sec].get("is_hydrated") is True
    ]
    if hydrated_sections:
        inherited_str = ", ".join(hydrated_sections)
        findings.append(
            _make_finding(
                INFO,
                "parent_metadata_inherited",
                f"Sections marked inherited from parent snapshot: {inherited_str}. Inherited context reflects the parent snapshot, and script mtime alone does not prove dependencies matched at child runtime.",
                "Use `hydrate_manifest_with_report` to also evaluate parent snapshot age and identity mismatches.",
                category="parent_metadata",
                evidence_status="inherited",
                impact="informational",
                details={
                    "meta_ref": raw_meta_ref,
                    "inherited_sections": hydrated_sections,
                },
            )
        )
        return findings, {
            "name": "parent_metadata",
            "label": CATEGORY_LABELS["parent_metadata"],
            "status": "uncertain",
            "evidence_status": "inherited",
            "summary": f"Manifest contains {len(hydrated_sections)} inherited section(s), but parent snapshot age and identity were not evaluated.",
            "finding_codes": ["parent_metadata_inherited"],
            "warn_count": 0,
            "info_count": 1,
        }

    if raw_meta_ref:
        findings.append(
            _make_finding(
                INFO,
                "parent_metadata_not_hydrated",
                f"Manifest references parent snapshot '{raw_meta_ref}', but parent hydration was not evaluated.",
                "Hydrate the manifest with `hydrate_manifest_with_report` before assessment to verify parent snapshot availability, age, and identity.",
                category="parent_metadata",
                evidence_status="not_checked",
                impact="informational",
                details={"meta_ref": raw_meta_ref},
            )
        )
        return findings, {
            "name": "parent_metadata",
            "label": CATEGORY_LABELS["parent_metadata"],
            "status": "not_checked",
            "evidence_status": "not_checked",
            "summary": f"Parent snapshot '{raw_meta_ref}' is referenced but was not hydrated.",
            "finding_codes": ["parent_metadata_not_hydrated"],
            "warn_count": 0,
            "info_count": 1,
        }

    return findings, {
        "name": "parent_metadata",
        "label": CATEGORY_LABELS["parent_metadata"],
        "status": "adequate",
        "evidence_status": "observed",
        "summary": "No parent meta_ref snapshot referenced; all recorded sections come directly from this run.",
        "finding_codes": [],
        "warn_count": 0,
        "info_count": 0,
    }


def _assess_invocation(
    manifest: Dict[str, Any],
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """Assess recorded command, working directory, and redacted CLI/env values."""
    findings: List[Dict[str, Any]] = []

    invocation = manifest.get("invocation")
    inv_dict = invocation if isinstance(invocation, dict) else {}
    argv = inv_dict.get("argv") if isinstance(inv_dict.get("argv"), list) else None
    rerun_cmd = (
        inv_dict.get("rerun_command")
        if isinstance(inv_dict.get("rerun_command"), str)
        else None
    )
    wd = (
        inv_dict.get("working_directory")
        if isinstance(inv_dict.get("working_directory"), dict)
        else {}
    )

    argv_redacted = bool(
        argv and any(isinstance(arg, str) and "[REDACTED]" in arg for arg in argv)
    )
    rerun_redacted = bool(rerun_cmd and "[REDACTED]" in rerun_cmd)
    if argv_redacted or rerun_redacted:
        findings.append(
            _make_finding(
                WARN,
                "rerun_command_redacted",
                "Recorded CLI arguments or rerun_command contain [REDACTED] placeholders; the command is not directly executable as printed without supplying redacted arguments.",
                "Supply the redacted argument values manually before executing the recorded command.",
                category="invocation",
                evidence_status="observed",
                impact="material",
                details={
                    "argv_redacted": argv_redacted,
                    "rerun_command_redacted": rerun_redacted,
                },
            )
        )

    if inv_dict and not rerun_cmd and not argv:
        findings.append(
            _make_finding(
                INFO,
                "invocation_command_missing",
                "Neither `rerun_command` nor `argv` was recorded in the invocation section.",
                "Verify invocation capture completed so the launch command is preserved.",
                category="invocation",
                evidence_status="unavailable",
                impact="informational",
            )
        )

    if inv_dict and not wd.get("path"):
        findings.append(
            _make_finding(
                INFO,
                "working_directory_missing",
                "No working directory path was recorded in `invocation.working_directory`.",
                "Record working directory context so relative paths in CLI arguments can be resolved.",
                category="invocation",
                evidence_status="unavailable",
                impact="informational",
            )
        )

    # Check redacted environment variables: both redacted/hashed representations
    # and heuristic [REDACTED] markers inside plain string values.
    env_sec = manifest.get("environment")
    env_dict = env_sec if isinstance(env_sec, dict) else {}
    env_vars = env_dict.get("variables") if isinstance(env_dict.get("variables"), list) else []
    redacted_env_names: List[str] = []
    for entry in env_vars:
        if not isinstance(entry, dict):
            continue
        name = entry.get("name")
        val_obj = entry.get("value")
        is_redacted = False
        if isinstance(val_obj, dict):
            rep = val_obj.get("representation")
            if rep in ("redacted", "hashed"):
                is_redacted = True
            elif rep == "plain":
                plain_val = val_obj.get("value")
                if isinstance(plain_val, str) and "[REDACTED]" in plain_val:
                    is_redacted = True
        elif isinstance(val_obj, str) and "[REDACTED]" in val_obj:
            is_redacted = True
        if is_redacted:
            redacted_env_names.append(str(name) if name else "<unnamed>")

    if redacted_env_names:
        preview = ", ".join(redacted_env_names[:5])
        extra = (
            ""
            if len(redacted_env_names) <= 5
            else f" (+{len(redacted_env_names) - 5} more)"
        )
        findings.append(
            _make_finding(
                INFO,
                "env_vars_redacted",
                f"{len(redacted_env_names)} recorded environment variable(s) were redacted or hashed ({preview}{extra}); required secret values must be provided when re-running.",
                "Provide the required redacted environment variables in your shell or job environment before re-running.",
                category="invocation",
                evidence_status="observed",
                impact="informational",
                details={
                    "count": len(redacted_env_names),
                    "variables": redacted_env_names[:20],
                },
            )
        )

    codes = [f["code"] for f in findings]
    warn_count = sum(1 for f in findings if f["severity"] == WARN)
    info_count = sum(1 for f in findings if f["severity"] == INFO)

    if any(f.get("comparison") == "mismatch" for f in findings):
        cat_status = "mismatch"
    elif warn_count > 0:
        cat_status = "gaps"
    elif not inv_dict:
        cat_status = "not_checked"
    elif codes:
        cat_status = "uncertain"
    else:
        cat_status = "adequate"

    if not inv_dict:
        cat_ev = "not_checked"
    elif "invocation_command_missing" in codes and not wd.get("path"):
        cat_ev = "unavailable"
    else:
        cat_ev = "observed"

    if cat_status == "adequate":
        cat_summary = "Recorded command and working directory are present without redacted arguments."
    elif warn_count > 0:
        cat_summary = "Recorded command contains redacted placeholders and cannot be executed verbatim."
    elif cat_status == "not_checked":
        cat_summary = "Invocation details were not recorded."
    else:
        cat_summary = "Invocation recorded with redacted environment variables or missing fields."

    return findings, {
        "name": "invocation",
        "label": CATEGORY_LABELS["invocation"],
        "status": cat_status,
        "evidence_status": cat_ev,
        "summary": cat_summary,
        "finding_codes": codes,
        "warn_count": warn_count,
        "info_count": info_count,
    }


def _finding_action_priority(finding: Dict[str, Any]) -> Tuple[int, int, str]:
    """Return a deterministic sort key prioritizing the highest-value next action.

    Order:
    1. Unavailable or broken evidence (warn + unavailable, or capture errors)
    2. Material recorded gaps (warn + material, or mismatch)
    3. Other warnings (portability, config notices, resource scope)
    4. Informational improvements (ordered by category order)
    """
    severity = finding.get("severity", INFO)
    ev = finding.get("evidence_status", "")
    impact = finding.get("impact", "informational")
    comparison = finding.get("comparison")
    code = finding.get("code", "")
    category = finding.get("category", "")

    try:
        cat_idx = CATEGORY_ORDER.index(category)
    except ValueError:
        cat_idx = len(CATEGORY_ORDER)

    if severity == WARN and (ev == "unavailable" or code == "capture_errors_recorded"):
        tier = 0
    elif severity == WARN and (impact == "material" or comparison == "mismatch"):
        tier = 1
    elif severity == WARN:
        tier = 2
    elif ev in ("unavailable", "not_checked"):
        tier = 3
    else:
        tier = 4

    return (tier, cat_idx, code)


def _prioritize_next_actions(findings: List[Dict[str, Any]]) -> Tuple[str, List[str]]:
    """Return ``(next_action, next_actions)`` deduplicated in deterministic priority order."""
    candidates = [f for f in findings if isinstance(f.get("suggestion"), str) and f["suggestion"].strip()]
    ordered = sorted(candidates, key=_finding_action_priority)

    next_actions: List[str] = []
    seen = set()
    for item in ordered:
        sugg = item["suggestion"].strip()
        if sugg not in seen:
            seen.add(sugg)
            next_actions.append(sugg)

    next_action = next_actions[0] if next_actions else _DEFAULT_NEXT_ACTION
    return next_action, next_actions


def _build_summary(
    categories: List[Dict[str, Any]],
    findings: List[Dict[str, Any]],
) -> str:
    """Build a concise one-line human summary of the assessment without any score."""
    warn_count = sum(1 for f in findings if f.get("severity") == WARN)
    info_count = sum(1 for f in findings if f.get("severity") == INFO)
    mismatch_cats = [c["name"] for c in categories if c.get("status") == "mismatch"]
    gap_cats = [c["name"] for c in categories if c.get("status") == "gaps"]
    uncertain_cats = [
        c["name"] for c in categories if c.get("status") in ("uncertain", "not_checked")
    ]

    if warn_count == 0 and not mismatch_cats and not gap_cats:
        if not uncertain_cats:
            return (
                "Recorded provenance appears adequate across all 7 evidence categories "
                "(no warnings found; reproduction is not guaranteed)."
            )
        cat_list = ", ".join(uncertain_cats)
        return (
            f"No material warnings recorded; {len(uncertain_cats)} category(ies) "
            f"have unverified or incomplete evidence ({cat_list})."
        )

    parts: List[str] = []
    if mismatch_cats:
        parts.append(f"mismatches in {', '.join(mismatch_cats)}")
    if gap_cats:
        parts.append(f"gaps in {', '.join(gap_cats)}")
    if not parts:
        parts.append("portability or configuration warnings")

    return (
        f"Found {warn_count} warning(s) and {info_count} informational note(s): "
        + "; ".join(parts)
        + "."
    )


def assess_manifest_reproducibility(
    manifest: Any,
    *,
    manifest_path: Optional[str] = None,
    hydration_report: Optional[Union[HydrationReport, Dict[str, Any]]] = None,
    current_hostname: Optional[str] = None,
    stale_parent_seconds: Optional[float] = DEFAULT_STALE_PARENT_SECONDS,
) -> Dict[str, Any]:
    """Assess recorded reproducibility evidence in a manifest across 7 categories.

    Read-only and never raises; tolerates empty, legacy, or malformed inputs.
    Does not emit numerical reproducibility scores and always includes
    ``NON_GUARANTEE_DISCLAIMER``.
    """
    _ = manifest_path  # Reserved for downstream preflight path resolution.
    hydration_dict = _hydration_report_to_dict(hydration_report)

    try:
        manifest_dict = manifest if isinstance(manifest, dict) else {}
        findings: List[Dict[str, Any]] = []
        categories: List[Dict[str, Any]] = []

        evaluators = (
            lambda: _assess_source(manifest_dict),
            lambda: _assess_runtime(manifest_dict, current_hostname),
            lambda: _assess_dependencies(manifest_dict),
            lambda: _assess_inputs_outputs(manifest_dict),
            lambda: _assess_capture_completeness(manifest_dict),
            lambda: _assess_parent_metadata(
                manifest_dict, hydration_dict, stale_parent_seconds
            ),
            lambda: _assess_invocation(manifest_dict),
        )

        for evaluate in evaluators:
            cat_findings, cat_summary = evaluate()
            findings.extend(cat_findings)
            categories.append(cat_summary)

        next_action, next_actions = _prioritize_next_actions(findings)
        summary = _build_summary(categories, findings)

        return {
            "schema_version": "1.0",
            "mode": "manifest",
            "summary": summary,
            "next_action": next_action,
            "next_actions": next_actions,
            "disclaimer": NON_GUARANTEE_DISCLAIMER,
            "categories": categories,
            "findings": findings,
            "parent_metadata": hydration_dict,
            "preflight": {
                "requested": False,
                "status": "not_checked",
                "counts": {},
                "checks": [],
            },
        }
    except Exception:
        fallback_categories = [
            {
                "name": name,
                "label": CATEGORY_LABELS[name],
                "status": "uncertain",
                "evidence_status": "unavailable",
                "summary": "Assessment could not evaluate this category.",
                "finding_codes": [],
                "warn_count": 0,
                "info_count": 0,
            }
            for name in CATEGORY_ORDER
        ]
        return {
            "schema_version": "1.0",
            "mode": "manifest",
            "summary": "Manifest could not be fully assessed due to malformed input.",
            "next_action": "Validate that manifest.json is a well-formed pubrun manifest object.",
            "next_actions": [
                "Validate that manifest.json is a well-formed pubrun manifest object."
            ],
            "disclaimer": NON_GUARANTEE_DISCLAIMER,
            "categories": fallback_categories,
            "findings": [],
            "parent_metadata": hydration_dict,
            "preflight": {
                "requested": False,
                "status": "not_checked",
                "counts": {},
                "checks": [],
            },
        }


def assess_run(
    manifest: Any,
    *,
    manifest_path: Optional[str] = None,
    hydration_report: Optional[Union[HydrationReport, Dict[str, Any]]] = None,
    current_hostname: Optional[str] = None,
    stale_parent_seconds: Optional[float] = DEFAULT_STALE_PARENT_SECONDS,
) -> Dict[str, Any]:
    """Shared assessment facade delegating to ``assess_manifest_reproducibility``."""
    return assess_manifest_reproducibility(
        manifest,
        manifest_path=manifest_path,
        hydration_report=hydration_report,
        current_hostname=current_hostname,
        stale_parent_seconds=stale_parent_seconds,
    )


def _colorize(text: str, ansi_code: str, use_color: bool) -> str:
    """Wrap ``text`` with an ANSI SGR color code when enabled (never uses DIM code 2)."""
    if not use_color or not ansi_code or ansi_code == "2":
        return text
    return f"\033[{ansi_code}m{text}\033[0m"


def format_reproducibility_summary(assessment: Dict[str, Any]) -> str:
    """Format a terse plain-text reproducibility summary for CLI and TUI surfaces."""
    if not isinstance(assessment, dict):
        return f"Summary: Unavailable.\nNote: {NON_GUARANTEE_DISCLAIMER}"

    lines: List[str] = []
    summary = assessment.get("summary") or "No reproducibility summary available."
    lines.append(f"Summary: {summary}")

    categories = assessment.get("categories") or []
    if isinstance(categories, list) and categories:
        flagged = [
            f"{c.get('label', c.get('name', '?'))} [{str(c.get('status', '?')).upper()}]"
            for c in categories
            if isinstance(c, dict) and c.get("status") != "adequate"
        ]
        if flagged:
            lines.append("Categories needing attention: " + ", ".join(flagged))
        else:
            lines.append(
                f"Categories: all {len(categories)} evidence categories adequate."
            )

    parent_meta = assessment.get("parent_metadata")
    if isinstance(parent_meta, dict) and parent_meta.get("inherited_sections"):
        inherited = ", ".join(str(s) for s in parent_meta["inherited_sections"])
        lines.append(
            f"Inherited from parent snapshot: {inherited} "
            "(script mtime alone does not prove dependencies matched)."
        )

    next_action = assessment.get("next_action") or _DEFAULT_NEXT_ACTION
    lines.append(f"Next step: {next_action}")

    disclaimer = assessment.get("disclaimer") or NON_GUARANTEE_DISCLAIMER
    lines.append(f"Note: {disclaimer}")
    return "\n".join(lines)


def format_reproducibility_detail(
    assessment: Dict[str, Any],
    *,
    use_color: bool = False,
) -> str:
    """Format a category table and per-finding detail view for CLI and TUI surfaces.

    Honors ``NO_COLOR`` and never emits ANSI DIM (code 2). Textual status labels
    are always authoritative.
    """
    color_active = bool(use_color) and not bool(os.environ.get("NO_COLOR", ""))
    if not isinstance(assessment, dict):
        return f"Summary: Unavailable.\nNote: {NON_GUARANTEE_DISCLAIMER}"

    lines: List[str] = []
    summary = assessment.get("summary") or "No reproducibility summary available."
    lines.append(f"Summary: {summary}")
    lines.append("")

    categories = assessment.get("categories") or []
    if isinstance(categories, list) and categories:
        lines.append("Evidence categories:")
        for cat in categories:
            if not isinstance(cat, dict):
                continue
            status_key = str(cat.get("status", "uncertain"))
            label_txt, ansi = _CATEGORY_STATUS_LABELS.get(
                status_key, (status_key.upper(), "33")
            )
            badge = _colorize(f"[{label_txt:<11}]", ansi, color_active)
            cat_label = str(cat.get("label") or cat.get("name") or "Unknown")
            ev_status = str(cat.get("evidence_status") or "unknown")
            cat_summary = str(cat.get("summary") or "")
            lines.append(
                f"  {badge} {cat_label:<20} (evidence: {ev_status}) - {cat_summary}"
            )

    findings = assessment.get("findings") or []
    if isinstance(findings, list) and findings:
        lines.append("")
        lines.append("Findings:")
        for item in findings:
            if not isinstance(item, dict):
                continue
            sev = str(item.get("severity", INFO))
            sev_txt, ansi = _SEVERITY_LABELS.get(sev, ("INFO ", "32"))
            badge = _colorize(f"[{sev_txt}]", ansi, color_active)
            code = str(item.get("code") or "finding")
            ev = str(item.get("evidence_status") or "unknown")
            msg = str(item.get("message") or "")
            lines.append(f"  {badge} {code} ({ev}): {msg}")
            sugg = item.get("suggestion")
            if isinstance(sugg, str) and sugg.strip():
                lines.append(f"      -> {sugg.strip()}")

    lines.append("")
    next_action = assessment.get("next_action") or _DEFAULT_NEXT_ACTION
    lines.append(f"Next step: {next_action}")

    disclaimer = assessment.get("disclaimer") or NON_GUARANTEE_DISCLAIMER
    lines.append(f"Note: {disclaimer}")
    return "\n".join(lines)
