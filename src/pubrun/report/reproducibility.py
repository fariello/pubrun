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

import hashlib
import math
import os
import platform
import re
import socket
import stat
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, Union

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
DEFAULT_MAX_HASH_BYTES: int = 104_857_600  # 100 MiB (OQ-01)
DEFAULT_GIT_TIMEOUT: float = 5.0
FAIL_ON_MODES: Tuple[str, ...] = ("warn", "mismatch", "unknown")

_HASH_CHUNK_BYTES: int = 65536  # 64 KiB read-only streaming chunks
_SUPPORTED_PREFLIGHT_HASH_ALGS: Tuple[str, ...] = ("sha256", "md5", "sha1", "sha512")
_GIT_ENV_STRIP_KEYS: Tuple[str, ...] = (
    "GIT_DIR",
    "GIT_WORK_TREE",
    "GIT_COMMON_DIR",
    "GIT_INDEX_FILE",
)
_PY_VERSION_RE = re.compile(r"^\s*(\d+)\.(\d+)(?:\.(\d+))?")

NON_GUARANTEE_DISCLAIMER: str = (
    "Recorded provenance and an absence of findings support reproduction analysis, "
    "but they do not guarantee equivalent scientific or bitwise results, especially "
    "for legacy or sparse manifests."
)

_DEFAULT_NEXT_ACTION: str = (
    "Run `pubrun inspect --preflight` on the target machine to compare recorded "
    "requirements against the current environment."
)

_DEFAULT_PREFLIGHT_NEXT_ACTION: str = (
    "Review the preflight comparison checks above before re-running; matching "
    "preflight checks do not guarantee identical results."
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


_MAX_DETAIL_LEN: int = 160


def _capture_state_detail(section: Any) -> Optional[str]:
    """Safely extract ``section['capture_state']['detail']`` when present."""
    if isinstance(section, dict):
        cs = section.get("capture_state")
        if isinstance(cs, dict):
            detail = cs.get("detail")
            if isinstance(detail, str) and detail.strip():
                return detail.strip()
    return None


def _bound_detail(text: Any, max_len: int = _MAX_DETAIL_LEN) -> str:
    """Collapse whitespace to a single line and bound detail length."""
    if not isinstance(text, str):
        return ""
    cleaned = " ".join(text.split())
    if not cleaned:
        return ""
    if len(cleaned) <= max_len:
        return cleaned
    return cleaned[: max(0, max_len - 3)].rstrip() + "..."


def _normalize_error_section(raw: Any) -> str:
    """Normalize an ``errors.records`` section name into a finding-code suffix."""
    if not isinstance(raw, str):
        return "general"
    normalized = re.sub(r"[^a-z0-9_]+", "_", raw.strip().lower()).strip("_")
    return normalized or "general"


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
        detail = _bound_detail(_capture_state_detail(git_dict))
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
        detail = _bound_detail(_capture_state_detail(git_dict))
        suffix = f" ({detail})" if detail else ""
        findings.append(
            _make_finding(
                WARN,
                "git_capture_failed",
                f"Section 'git' capture failed{suffix}.",
                "Inspect `errors.records` in manifest.json and diagnostic logs for `git` capture failures.",
                category="source",
                evidence_status="unavailable",
                impact="material",
                details={"detail": detail} if detail else {},
            )
        )
    elif git_status == "partial":
        detail = _bound_detail(_capture_state_detail(git_dict))
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
        detail = _bound_detail(_capture_state_detail(git_dict))
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
        detail = _bound_detail(_capture_state_detail(pkg_dict))
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
    elif pkg_status == "failed":
        detail = _bound_detail(_capture_state_detail(pkg_dict))
        suffix = f" ({detail})" if detail else ""
        findings.append(
            _make_finding(
                WARN,
                "packages_capture_failed",
                f"Section 'packages' capture failed{suffix}.",
                "Inspect `errors.records` in manifest.json and diagnostic logs for `packages` capture failures.",
                category="dependencies",
                evidence_status="unavailable",
                impact="material",
                details={"status": "failed", "detail": detail or None},
            )
        )
    elif pkg_status == "timeout":
        detail = _bound_detail(_capture_state_detail(pkg_dict))
        suffix = f" ({detail})" if detail else ""
        findings.append(
            _make_finding(
                WARN,
                "packages_timeout",
                f"Package inventory capture timed out{suffix}; dependency versions are unavailable.",
                "Inspect environment metadata health and re-capture package versions.",
                category="dependencies",
                evidence_status="unavailable",
                impact="material",
                details={"status": "timeout", "detail": detail or None},
            )
        )
    elif pkg_status == "unavailable":
        detail = _bound_detail(_capture_state_detail(pkg_dict))
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


def _is_caller_digest_mismatch(rec: Dict[str, Any]) -> bool:
    """Return True when a record indicates a verified caller digest mismatched content."""
    if rec.get("hash_status_detail") == "caller_digest_mismatch":
        return True
    caller_digest = rec.get("caller_digest")
    if isinstance(caller_digest, dict) and caller_digest.get("verified") is False:
        return True
    return False


def _has_nonempty_digest_value(rec: Dict[str, Any]) -> bool:
    """Return True when a record carries a non-empty digest, sha256, or md5 value."""
    digest = rec.get("digest")
    if isinstance(digest, dict):
        val = digest.get("value")
        if isinstance(val, str) and val.strip():
            return True
    sha256 = rec.get("sha256")
    if isinstance(sha256, str) and sha256.strip():
        return True
    md5 = rec.get("md5")
    if isinstance(md5, str) and md5.strip():
        return True
    return False


def _classify_file_record(rec: Dict[str, Any]) -> str:
    """Classify a single ``data_files`` record by evidence strength and hashing outcome."""
    hash_status = rec.get("hash_status")
    evidence_strength = rec.get("evidence_strength")
    evidence_source = rec.get("evidence_source")

    if hash_status == "file_changed" or rec.get("change_detected") is True:
        return "changed"
    if hash_status == "failed" or _is_caller_digest_mismatch(rec):
        return "failed"
    if hash_status == "unavailable":
        return "unavailable"
    if hash_status == "over_budget":
        return "over_budget"
    if hash_status == "completed" or evidence_strength == "verified_content":
        return "verified" if _has_nonempty_digest_value(rec) else "identified_only"
    if (
        hash_status == "asserted"
        or evidence_strength == "asserted_content"
        or evidence_source == "asserted"
    ):
        return "asserted"
    if hash_status == "pending":
        return "pending"
    if hash_status == "disabled" or evidence_strength in ("metadata_only", "path_only"):
        return "identified_only"
    if hash_status is None and evidence_strength is None and evidence_source is None:
        return "verified" if _has_nonempty_digest_value(rec) else "identified_only"
    if evidence_strength == "unavailable":
        return "unavailable"
    if evidence_strength == "changed_unverified":
        return "changed"
    return "identified_only"


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
                "globally, so files are recorded only via `pubrun.open()`, "
                "`pubrun.register_input()`, `pubrun.register_output()`, or `pubrun.register_file()`.",
                "Use `pubrun.open(...)` or register external files with "
                "`pubrun.register_input(...)` / `pubrun.register_output(...)` to record input/output provenance.",
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

    verified_count = 0
    changed_count = 0
    failed_count = 0
    unavailable_count = 0
    mismatch_count = 0
    over_budget_count = 0
    asserted_count = 0
    identified_only_count = 0
    pending_unverified_count = 0

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
            cls = _classify_file_record(rec)
            is_unverified_asserted = (
                cls == "asserted"
                or (
                    rec.get("evidence_source") == "asserted"
                    and rec.get("hash_status") != "completed"
                )
            )
            if cls == "verified":
                verified_count += 1
            elif cls == "changed":
                changed_count += 1
            elif cls == "failed":
                failed_count += 1
                if _is_caller_digest_mismatch(rec):
                    mismatch_count += 1
            elif cls == "unavailable":
                unavailable_count += 1
            elif cls == "over_budget":
                over_budget_count += 1
            elif cls == "pending":
                if not is_unverified_asserted:
                    pending_unverified_count += 1
            elif cls == "identified_only":
                if not is_unverified_asserted:
                    identified_only_count += 1

            if is_unverified_asserted:
                asserted_count += 1

        if changed_count > 0:
            findings.append(
                _make_finding(
                    WARN,
                    "file_provenance_changed",
                    f"{changed_count} tracked file(s) changed between access and hashing; recorded content evidence is unverified.",
                    "Avoid mutating tracked input or output files while a run is reading or hashing them.",
                    category="inputs_outputs",
                    evidence_status="observed",
                    impact="material",
                    details={"count": changed_count},
                )
            )

        failed_or_unavail = failed_count + unavailable_count
        if failed_or_unavail > 0:
            mismatch_note = (
                f" (including {mismatch_count} caller-digest mismatch(es))"
                if mismatch_count > 0
                else ""
            )
            findings.append(
                _make_finding(
                    WARN,
                    "file_provenance_hash_failed",
                    f"Content hashing failed or target was unavailable for {failed_or_unavail} tracked file(s){mismatch_note}.",
                    "Inspect `data_files` `hash_status_detail` in manifest.json and verify target readability or caller-supplied digests.",
                    category="inputs_outputs",
                    evidence_status="unavailable",
                    impact="material",
                    details={
                        "count": failed_or_unavail,
                        "mismatch_count": mismatch_count,
                    },
                )
            )

        if over_budget_count > 0:
            findings.append(
                _make_finding(
                    INFO,
                    "file_provenance_over_budget",
                    f"{over_budget_count} tracked file(s) exceeded the hashing size or time budget and were not content-hashed.",
                    "Increase `[capture.file_io]` budget limits or supply verified external digests if content verification is required.",
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
                    f"{asserted_count} tracked file(s) carry caller-asserted digests that were not independently verified by pubrun.",
                    "Pass `verify_digest=True` to `pubrun.register_input()` / `pubrun.register_output()` or hash with `pubrun.open()` for verified content evidence.",
                    category="inputs_outputs",
                    evidence_status="asserted",
                    impact="informational",
                    details={"count": asserted_count},
                )
            )

        unverified_total = identified_only_count + pending_unverified_count
        if unverified_total > 0:
            if identified_only_count > 0 and pending_unverified_count > 0:
                unverified_msg = (
                    f"{unverified_total} tracked file(s) lack verified content hashes "
                    f"({identified_only_count} path/metadata-only, {pending_unverified_count} pending output(s))."
                )
            elif pending_unverified_count > 0:
                unverified_msg = (
                    f"{pending_unverified_count} tracked output file(s) remain pending without verified content hashes."
                )
            else:
                unverified_msg = (
                    f"{identified_only_count} tracked file(s) recorded path or stat metadata only without verified content hashes."
                )
            findings.append(
                _make_finding(
                    INFO,
                    "file_provenance_unverified_paths",
                    unverified_msg,
                    'Set `[capture.file_io].level = "hash"` or pass `level="hash"` to `pubrun.register_input()` / `pubrun.register_output()` to record content hashes.',
                    category="inputs_outputs",
                    evidence_status="not_checked",
                    impact="informational",
                    details={
                        "count": unverified_total,
                        "identified_only_count": identified_only_count,
                        "pending_count": pending_unverified_count,
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
    elif codes:
        cat_status = "uncertain"
    else:
        cat_status = "adequate"

    failed_hash_count = failed_count + unavailable_count
    if verified_count > 0:
        cat_ev = "observed"
    elif asserted_count > 0:
        cat_ev = "asserted"
    elif not all_df and inv_inputs:
        cat_ev = "inferred"
    elif failed_hash_count > 0:
        cat_ev = "unavailable"
    elif identified_only_count > 0:
        cat_ev = "observed"
    else:
        cat_ev = "not_checked"

    if cat_status == "adequate":
        cat_summary = f"Observed content digests recorded for {verified_count} tracked file(s)."
    elif warn_count > 0:
        cat_summary = "One or more tracked files had hashing failures or concurrent modifications."
    elif not all_df and inv_inputs:
        cat_summary = f"Only argv-inferred paths ({len(inv_inputs)}) were recorded without `pubrun.open()` provenance."
    elif asserted_count > 0 and verified_count == 0:
        cat_summary = f"{asserted_count} file(s) carry caller-asserted digests rather than observed hashes."
    else:
        cat_summary = "Tracked file provenance is partially unhashed (stat-only, pending, or over-budget)."

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
    # git and packages have dedicated findings in their owning categories, but still
    # participate in failed-section deduplication for errors.records below.
    _dedicated_capture_sections = frozenset(("git", "packages"))
    failed_sections: Set[str] = set()
    for sec_name, sec_val in manifest.items():
        if not isinstance(sec_val, dict):
            continue
        st = _capture_state_status(sec_val)
        if st == "failed":
            failed_sections.add(_normalize_error_section(sec_name))
        if st in ("failed", "timeout", "partial") and sec_name not in _dedicated_capture_sections:
            detail = _bound_detail(_capture_state_detail(sec_val))
            suffix = f" ({detail})" if detail else ""
            if st == "failed":
                msg = f"Section '{sec_name}' capture failed{suffix}."
                sugg = (
                    f"Inspect `errors.records` in manifest.json and diagnostic logs "
                    f"for `{sec_name}` capture failures."
                )
            elif sec_name == "errors" and st == "partial":
                msg = (
                    f"Capture errors list was truncated ({detail})."
                    if detail
                    else "Section 'errors' capture ended with status 'partial'."
                )
                sugg = "Inspect diagnostic logs for additional omitted capture errors."
            else:
                msg = f"Section '{sec_name}' capture ended with status '{st}'{suffix}."
                sugg = (
                    f"Inspect errors or configuration for `{sec_name}` capture "
                    "so provenance is complete."
                )
            findings.append(
                _make_finding(
                    WARN,
                    f"{sec_name}_capture_{st}",
                    msg,
                    sugg,
                    category="capture_completeness",
                    evidence_status="unavailable",
                    impact="material",
                    details={"section": sec_name, "status": st, "detail": detail or None},
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

    # 6. Per-section deduplicated errors.records capture-error entries.
    errors_sec = manifest.get("errors")
    if isinstance(errors_sec, dict) and isinstance(errors_sec.get("records"), list):
        cap_errors = [
            rec
            for rec in errors_sec["records"]
            if isinstance(rec, dict) and rec.get("kind") == "capture-error"
        ]
        if cap_errors:
            grouped: Dict[str, Tuple[str, int]] = {}
            for rec in cap_errors:
                sec_key = _normalize_error_section(rec.get("section"))
                if sec_key in failed_sections:
                    continue
                raw_msg = rec.get("message")
                if not isinstance(raw_msg, str) or not raw_msg.strip():
                    raw_msg = rec.get("type")
                bounded = _bound_detail(raw_msg) or "capture error"
                if sec_key in grouped:
                    first_msg, count = grouped[sec_key]
                    grouped[sec_key] = (first_msg, count + 1)
                else:
                    grouped[sec_key] = (bounded, 1)

            existing_codes = {f["code"] for f in findings}
            for sec_key, (first_msg, count) in grouped.items():
                code = f"capture_error_{sec_key}"
                if code in existing_codes:
                    continue
                count_suffix = f" (+{count - 1} more)" if count > 1 else ""
                findings.append(
                    _make_finding(
                        WARN,
                        code,
                        f"Capture error recorded for '{sec_key}': {first_msg}{count_suffix}.",
                        "Inspect `errors.records` in manifest.json and diagnostic logs "
                        "for capture failure details.",
                        category="capture_completeness",
                        evidence_status="observed",
                        impact="material",
                        details={
                            "section": sec_key,
                            "count": count,
                            "detail": first_msg,
                        },
                    )
                )
                existing_codes.add(code)

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

    if severity == WARN and (
        ev == "unavailable"
        or code.startswith("capture_error_")
        or code.endswith("_capture_failed")
    ):
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


def _prioritize_next_actions(
    findings: List[Dict[str, Any]],
    *,
    default_action: str = _DEFAULT_NEXT_ACTION,
) -> Tuple[str, List[str]]:
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

    next_action = next_actions[0] if next_actions else default_action
    return next_action, next_actions


def _build_summary(
    categories: List[Dict[str, Any]],
    findings: List[Dict[str, Any]],
    *,
    preflight: Optional[Dict[str, Any]] = None,
) -> str:
    """Build a concise one-line human summary of the assessment without any score."""
    warn_count = sum(1 for f in findings if f.get("severity") == WARN)
    info_count = sum(1 for f in findings if f.get("severity") == INFO)
    mismatch_cats = [c["name"] for c in categories if c.get("status") == "mismatch"]
    gap_cats = [c["name"] for c in categories if c.get("status") == "gaps"]
    uncertain_cats = [
        c["name"] for c in categories if c.get("status") in ("uncertain", "not_checked")
    ]

    if isinstance(preflight, dict) and preflight.get("requested") is True:
        counts = preflight.get("counts") if isinstance(preflight.get("counts"), dict) else {}
        mismatch_n = int(counts.get("mismatch", 0))
        unknown_n = int(counts.get("unknown", 0))
        not_checked_n = int(counts.get("not_checked", 0))
        port_n = int(counts.get("portability_diff", 0))
        match_n = int(counts.get("match", 0))
        if warn_count == 0 and mismatch_n == 0 and not mismatch_cats and not gap_cats:
            if unknown_n > 0 or not_checked_n > 0 or uncertain_cats:
                return (
                    f"Preflight found no material mismatches ({match_n} matched, "
                    f"{port_n} portability diff(s), {unknown_n} unknown, "
                    f"{not_checked_n} not checked); reproduction is not guaranteed."
                )
            return (
                f"Preflight checks matched across checked requirements ({match_n} matched, "
                f"{port_n} portability diff(s); reproduction is not guaranteed)."
            )
        parts: List[str] = []
        if mismatch_n > 0 or mismatch_cats:
            cat_str = f" in {', '.join(mismatch_cats)}" if mismatch_cats else ""
            parts.append(f"{mismatch_n} preflight mismatch(es){cat_str}")
        if gap_cats:
            parts.append(f"gaps in {', '.join(gap_cats)}")
        if not parts:
            parts.append("portability or configuration warnings")
        return (
            f"Preflight found {warn_count} warning(s) and {info_count} informational note(s): "
            + "; ".join(parts)
            + "."
        )

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

    parts = []
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


def _make_preflight_check(
    name: str,
    category: str,
    comparison: str,
    evidence_status: str,
    impact: str,
    severity: str,
    message: str,
    *,
    details: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Build one JSON-serializable preflight comparison check record."""
    return {
        "name": name,
        "category": category,
        "comparison": comparison,
        "evidence_status": evidence_status,
        "impact": impact,
        "severity": severity,
        "message": message,
        "details": dict(details) if isinstance(details, dict) else {},
    }


def _unwrap_preflight_hostname(raw_hostname: Any) -> Optional[str]:
    """Extract a plain hostname string for comparison, ignoring redacted markers."""
    if isinstance(raw_hostname, str):
        cleaned = raw_hostname.strip()
        if cleaned and "[REDACTED]" not in cleaned:
            return cleaned
        return None
    if isinstance(raw_hostname, dict):
        if raw_hostname.get("representation") == "plain":
            val = raw_hostname.get("value")
            if isinstance(val, str):
                cleaned = val.strip()
                if cleaned and "[REDACTED]" not in cleaned:
                    return cleaned
    return None


def _safe_gethostname() -> Optional[str]:
    """Return the current machine hostname, or None if unavailable."""
    try:
        host = socket.gethostname()
        return host.strip() if isinstance(host, str) and host.strip() else None
    except Exception:
        return None


def _stream_file_digest(path: Path, algorithm: str) -> str:
    """Compute a hex digest of a regular file read-only in 64 KiB streaming chunks."""
    hasher = hashlib.new(algorithm)
    with open(path, "rb") as fh:
        while True:
            chunk = fh.read(_HASH_CHUNK_BYTES)
            if not chunk:
                break
            hasher.update(chunk)
    return hasher.hexdigest()


def _preflight_runtime(
    manifest_dict: Dict[str, Any],
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Compare recorded Python runtime, host platform, and CPU architecture."""
    checks: List[Dict[str, Any]] = []
    findings: List[Dict[str, Any]] = []

    # --- Python runtime ---
    python_sec = manifest_dict.get("python")
    python_dict = python_sec if isinstance(python_sec, dict) else {}
    py_cap = _capture_state_status(python_dict)
    cur_major, cur_minor, cur_patch = (
        sys.version_info[0],
        sys.version_info[1],
        sys.version_info[2],
    )
    cur_ver_str = f"{cur_major}.{cur_minor}.{cur_patch}"

    if not python_dict or py_cap == "suppressed":
        checks.append(
            _make_preflight_check(
                "python_version",
                "runtime",
                "unknown",
                "not_checked",
                "informational",
                INFO,
                f"Recorded Python runtime metadata was not captured; cannot compare against current Python {cur_ver_str}.",
                details={"current_version": cur_ver_str},
            )
        )
    elif py_cap in ("failed", "timeout", "unavailable"):
        checks.append(
            _make_preflight_check(
                "python_version",
                "runtime",
                "unknown",
                "unavailable",
                "informational",
                INFO,
                f"Recorded Python runtime metadata is unavailable ({py_cap}); cannot compare against current Python {cur_ver_str}.",
                details={"capture_status": py_cap, "current_version": cur_ver_str},
            )
        )
    else:
        raw_ver = python_dict.get("version")
        ver_match = _PY_VERSION_RE.match(raw_ver) if isinstance(raw_ver, str) else None
        if ver_match is None:
            checks.append(
                _make_preflight_check(
                    "python_version",
                    "runtime",
                    "unknown",
                    "unavailable",
                    "informational",
                    INFO,
                    f"Recorded Python version is missing or unparseable; cannot compare against current Python {cur_ver_str}.",
                    details={"recorded_version": raw_ver, "current_version": cur_ver_str},
                )
            )
        else:
            rec_major = int(ver_match.group(1))
            rec_minor = int(ver_match.group(2))
            rec_patch = int(ver_match.group(3)) if ver_match.group(3) is not None else None
            rec_ver_str = (
                f"{rec_major}.{rec_minor}.{rec_patch}"
                if rec_patch is not None
                else f"{rec_major}.{rec_minor}"
            )
            ver_details = {
                "recorded_version": rec_ver_str,
                "current_version": cur_ver_str,
            }
            if (rec_major, rec_minor) != (cur_major, cur_minor):
                msg = (
                    f"Recorded Python version is {rec_ver_str}, while the current "
                    f"interpreter is {cur_ver_str} (major.minor differs; behavior or "
                    f"package compatibility may vary)."
                )
                checks.append(
                    _make_preflight_check(
                        "python_version",
                        "runtime",
                        "mismatch",
                        "observed",
                        "material",
                        WARN,
                        msg,
                        details=ver_details,
                    )
                )
                findings.append(
                    _make_finding(
                        WARN,
                        "preflight_python_version_mismatch",
                        msg,
                        f"Use a Python {rec_major}.{rec_minor} environment to match the recorded interpreter version.",
                        category="runtime",
                        evidence_status="observed",
                        impact="material",
                        comparison="mismatch",
                        details=ver_details,
                    )
                )
            elif rec_patch is not None and rec_patch != cur_patch:
                msg = (
                    f"Recorded Python patch version is {rec_ver_str}, while the current "
                    f"interpreter is {cur_ver_str} (same major.minor, different patch release)."
                )
                checks.append(
                    _make_preflight_check(
                        "python_version",
                        "runtime",
                        "portability_diff",
                        "observed",
                        "portability",
                        INFO,
                        msg,
                        details=ver_details,
                    )
                )
                findings.append(
                    _make_finding(
                        INFO,
                        "preflight_python_patch_diff",
                        msg,
                        None,
                        category="runtime",
                        evidence_status="observed",
                        impact="portability",
                        comparison="portability_diff",
                        details=ver_details,
                    )
                )
            else:
                checks.append(
                    _make_preflight_check(
                        "python_version",
                        "runtime",
                        "match",
                        "observed",
                        "informational",
                        INFO,
                        f"Current Python version {cur_ver_str} matches recorded Python {rec_ver_str}.",
                        details=ver_details,
                    )
                )

        # Python implementation.
        rec_impl = python_dict.get("implementation")
        cur_impl = getattr(sys.implementation, "name", None) or ""
        if not isinstance(rec_impl, str) or not rec_impl.strip():
            checks.append(
                _make_preflight_check(
                    "python_implementation",
                    "runtime",
                    "unknown",
                    "unavailable",
                    "informational",
                    INFO,
                    f"Recorded Python implementation was not captured; current interpreter is '{cur_impl}'.",
                    details={"current_implementation": cur_impl},
                )
            )
        else:
            rec_impl_clean = rec_impl.strip()
            impl_details = {
                "recorded_implementation": rec_impl_clean,
                "current_implementation": cur_impl,
            }
            if rec_impl_clean.lower() != cur_impl.lower():
                msg = (
                    f"Recorded Python implementation is '{rec_impl_clean}', while the "
                    f"current interpreter is '{cur_impl}'."
                )
                checks.append(
                    _make_preflight_check(
                        "python_implementation",
                        "runtime",
                        "mismatch",
                        "observed",
                        "material",
                        WARN,
                        msg,
                        details=impl_details,
                    )
                )
                findings.append(
                    _make_finding(
                        WARN,
                        "preflight_python_implementation_mismatch",
                        msg,
                        f"Run under a '{rec_impl_clean}' interpreter to match the recorded runtime implementation.",
                        category="runtime",
                        evidence_status="observed",
                        impact="material",
                        comparison="mismatch",
                        details=impl_details,
                    )
                )
            else:
                checks.append(
                    _make_preflight_check(
                        "python_implementation",
                        "runtime",
                        "match",
                        "observed",
                        "informational",
                        INFO,
                        f"Current Python implementation '{cur_impl}' matches recorded '{rec_impl_clean}'.",
                        details=impl_details,
                    )
                )

        # Python environment kind (unwrapping dict from python_runtime.environment_kind()).
        rec_env_kind = python_dict.get("environment_kind")
        cur_env_kind: Optional[str] = None
        try:
            from pubrun.capture.python_runtime import environment_kind as _get_env_kind

            env_info = _get_env_kind()
            if isinstance(env_info, dict):
                raw_kind = env_info.get("environment_kind")
                if isinstance(raw_kind, str) and raw_kind.strip():
                    cur_env_kind = raw_kind.strip()
        except Exception:
            cur_env_kind = None

        if not isinstance(rec_env_kind, str) or not rec_env_kind.strip() or not cur_env_kind:
            checks.append(
                _make_preflight_check(
                    "python_environment_kind",
                    "runtime",
                    "unknown",
                    "unavailable",
                    "informational",
                    INFO,
                    "Recorded or current Python environment kind is unavailable.",
                    details={
                        "recorded_environment_kind": rec_env_kind,
                        "current_environment_kind": cur_env_kind,
                    },
                )
            )
        else:
            rec_kind_clean = rec_env_kind.strip()
            env_details = {
                "recorded_environment_kind": rec_kind_clean,
                "current_environment_kind": cur_env_kind,
            }
            if rec_kind_clean != cur_env_kind:
                msg = (
                    f"Recorded Python environment kind is '{rec_kind_clean}', while the "
                    f"current environment is '{cur_env_kind}'."
                )
                checks.append(
                    _make_preflight_check(
                        "python_environment_kind",
                        "runtime",
                        "portability_diff",
                        "observed",
                        "portability",
                        INFO,
                        msg,
                        details=env_details,
                    )
                )
                findings.append(
                    _make_finding(
                        INFO,
                        "preflight_python_env_kind_diff",
                        msg,
                        None,
                        category="runtime",
                        evidence_status="observed",
                        impact="portability",
                        comparison="portability_diff",
                        details=env_details,
                    )
                )
            else:
                checks.append(
                    _make_preflight_check(
                        "python_environment_kind",
                        "runtime",
                        "match",
                        "observed",
                        "informational",
                        INFO,
                        f"Current Python environment kind '{cur_env_kind}' matches recorded '{rec_kind_clean}'.",
                        details=env_details,
                    )
                )

    # --- Host OS, OS minor release, and hostname ---
    host_sec = manifest_dict.get("host")
    host_dict = host_sec if isinstance(host_sec, dict) else {}
    host_cap = _capture_state_status(host_dict)
    cur_os = platform.system()
    cur_os_ver = platform.release()
    cur_host = _safe_gethostname()

    if not host_dict or host_cap == "suppressed":
        checks.append(
            _make_preflight_check(
                "host_os",
                "runtime",
                "unknown",
                "not_checked",
                "informational",
                INFO,
                f"Recorded host metadata was not captured; current OS is '{cur_os}'.",
                details={"current_os_name": cur_os},
            )
        )
    elif host_cap in ("failed", "timeout", "unavailable"):
        checks.append(
            _make_preflight_check(
                "host_os",
                "runtime",
                "unknown",
                "unavailable",
                "informational",
                INFO,
                f"Recorded host metadata is unavailable ({host_cap}); current OS is '{cur_os}'.",
                details={"capture_status": host_cap, "current_os_name": cur_os},
            )
        )
    else:
        rec_os = host_dict.get("os_name")
        if not isinstance(rec_os, str) or not rec_os.strip():
            checks.append(
                _make_preflight_check(
                    "host_os",
                    "runtime",
                    "unknown",
                    "unavailable",
                    "informational",
                    INFO,
                    f"Recorded host OS name is missing; current OS is '{cur_os}'.",
                    details={"current_os_name": cur_os},
                )
            )
        else:
            rec_os_clean = rec_os.strip()
            os_details = {"recorded_os_name": rec_os_clean, "current_os_name": cur_os}
            if rec_os_clean != cur_os:
                msg = (
                    f"Recorded operating system is '{rec_os_clean}', while the current "
                    f"machine runs '{cur_os}' (platform portability difference)."
                )
                checks.append(
                    _make_preflight_check(
                        "host_os",
                        "runtime",
                        "portability_diff",
                        "observed",
                        "portability",
                        INFO,
                        msg,
                        details=os_details,
                    )
                )
                findings.append(
                    _make_finding(
                        INFO,
                        "preflight_os_diff",
                        msg,
                        None,
                        category="runtime",
                        evidence_status="observed",
                        impact="portability",
                        comparison="portability_diff",
                        details=os_details,
                    )
                )
            else:
                checks.append(
                    _make_preflight_check(
                        "host_os",
                        "runtime",
                        "match",
                        "observed",
                        "informational",
                        INFO,
                        f"Current operating system '{cur_os}' matches recorded '{rec_os_clean}'.",
                        details=os_details,
                    )
                )
                rec_os_ver = host_dict.get("os_version")
                if isinstance(rec_os_ver, str) and rec_os_ver.strip():
                    rec_os_ver_clean = rec_os_ver.strip()
                    os_ver_details = {
                        "recorded_os_version": rec_os_ver_clean,
                        "current_os_version": cur_os_ver,
                    }
                    if rec_os_ver_clean != cur_os_ver:
                        msg = (
                            f"Recorded OS release is '{rec_os_ver_clean}', while the current "
                            f"machine reports '{cur_os_ver}' (incidental OS release difference)."
                        )
                        checks.append(
                            _make_preflight_check(
                                "host_os_version",
                                "runtime",
                                "portability_diff",
                                "observed",
                                "incidental",
                                INFO,
                                msg,
                                details=os_ver_details,
                            )
                        )
                        findings.append(
                            _make_finding(
                                INFO,
                                "preflight_os_version_diff",
                                msg,
                                None,
                                category="runtime",
                                evidence_status="observed",
                                impact="incidental",
                                comparison="portability_diff",
                                details=os_ver_details,
                            )
                        )
                    else:
                        checks.append(
                            _make_preflight_check(
                                "host_os_version",
                                "runtime",
                                "match",
                                "observed",
                                "informational",
                                INFO,
                                f"Current OS release '{cur_os_ver}' matches recorded '{rec_os_ver_clean}'.",
                                details=os_ver_details,
                            )
                        )

        # Hostname (safely unwrapping redacted-value dicts).
        raw_hostname = host_dict.get("hostname")
        rec_host = _unwrap_preflight_hostname(raw_hostname)
        if rec_host is None or cur_host is None:
            rep = (
                raw_hostname.get("representation")
                if isinstance(raw_hostname, dict)
                else None
            )
            reason = f"redacted or {rep}" if rep else "unavailable"
            checks.append(
                _make_preflight_check(
                    "host_hostname",
                    "runtime",
                    "unknown",
                    "unavailable",
                    "incidental",
                    INFO,
                    f"Recorded hostname is {reason} and was not compared against current host '{cur_host or 'unknown'}'.",
                    details={
                        "recorded_hostname_representation": rep,
                        "current_hostname": cur_host,
                    },
                )
            )
        elif rec_host != cur_host:
            host_details = {
                "recorded_hostname": rec_host,
                "current_hostname": cur_host,
            }
            msg = (
                f"Recorded hostname is '{rec_host}', while the current machine is "
                f"'{cur_host}' (incidental host difference)."
            )
            checks.append(
                _make_preflight_check(
                    "host_hostname",
                    "runtime",
                    "portability_diff",
                    "observed",
                    "incidental",
                    INFO,
                    msg,
                    details=host_details,
                )
            )
            findings.append(
                _make_finding(
                    INFO,
                    "preflight_hostname_diff",
                    msg,
                    None,
                    category="runtime",
                    evidence_status="observed",
                    impact="incidental",
                    comparison="portability_diff",
                    details=host_details,
                )
            )
        else:
            checks.append(
                _make_preflight_check(
                    "host_hostname",
                    "runtime",
                    "match",
                    "observed",
                    "informational",
                    INFO,
                    f"Current hostname '{cur_host}' matches recorded hostname.",
                    details={
                        "recorded_hostname": rec_host,
                        "current_hostname": cur_host,
                    },
                )
            )

    # --- Hardware CPU architecture ---
    hw_sec = manifest_dict.get("hardware")
    hw_dict = hw_sec if isinstance(hw_sec, dict) else {}
    hw_cap = _capture_state_status(hw_dict)
    cur_arch = platform.machine()

    if not hw_dict or hw_cap == "suppressed":
        checks.append(
            _make_preflight_check(
                "cpu_architecture",
                "runtime",
                "unknown",
                "not_checked",
                "informational",
                INFO,
                f"Recorded hardware metadata was not captured; current CPU architecture is '{cur_arch}'.",
                details={"current_architecture": cur_arch},
            )
        )
    elif hw_cap in ("failed", "timeout", "unavailable"):
        checks.append(
            _make_preflight_check(
                "cpu_architecture",
                "runtime",
                "unknown",
                "unavailable",
                "informational",
                INFO,
                f"Recorded hardware metadata is unavailable ({hw_cap}); current CPU architecture is '{cur_arch}'.",
                details={"capture_status": hw_cap, "current_architecture": cur_arch},
            )
        )
    else:
        cpu_dict = hw_dict.get("cpu") if isinstance(hw_dict.get("cpu"), dict) else {}
        rec_arch = cpu_dict.get("architecture")
        if not isinstance(rec_arch, str) or not rec_arch.strip():
            checks.append(
                _make_preflight_check(
                    "cpu_architecture",
                    "runtime",
                    "unknown",
                    "unavailable",
                    "informational",
                    INFO,
                    f"Recorded CPU architecture is missing; current machine reports '{cur_arch}'.",
                    details={"current_architecture": cur_arch},
                )
            )
        else:
            rec_arch_clean = rec_arch.strip()
            arch_details = {
                "recorded_architecture": rec_arch_clean,
                "current_architecture": cur_arch,
            }
            if rec_arch_clean.lower() != (cur_arch or "").lower():
                msg = (
                    f"Recorded CPU architecture is '{rec_arch_clean}', while the current "
                    f"machine reports '{cur_arch}' (architecture portability difference)."
                )
                checks.append(
                    _make_preflight_check(
                        "cpu_architecture",
                        "runtime",
                        "portability_diff",
                        "observed",
                        "portability",
                        INFO,
                        msg,
                        details=arch_details,
                    )
                )
                findings.append(
                    _make_finding(
                        INFO,
                        "preflight_cpu_arch_diff",
                        msg,
                        None,
                        category="runtime",
                        evidence_status="observed",
                        impact="portability",
                        comparison="portability_diff",
                        details=arch_details,
                    )
                )
            else:
                checks.append(
                    _make_preflight_check(
                        "cpu_architecture",
                        "runtime",
                        "match",
                        "observed",
                        "informational",
                        INFO,
                        f"Current CPU architecture '{cur_arch}' matches recorded '{rec_arch_clean}'.",
                        details=arch_details,
                    )
                )

    return checks, findings


def _preflight_packages(
    manifest_dict: Dict[str, Any],
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Compare recorded package versions against currently installed distributions."""
    checks: List[Dict[str, Any]] = []
    findings: List[Dict[str, Any]] = []

    pkg_sec = manifest_dict.get("packages")
    pkg_dict = pkg_sec if isinstance(pkg_sec, dict) else {}
    pkg_cap = _capture_state_status(pkg_dict)

    if not pkg_dict or pkg_cap == "suppressed":
        checks.append(
            _make_preflight_check(
                "packages",
                "dependencies",
                "not_checked",
                "not_checked",
                "informational",
                INFO,
                "Recorded package inventory was not captured; installed packages were not compared.",
            )
        )
        return checks, findings

    if pkg_cap in ("failed", "timeout", "unavailable"):
        checks.append(
            _make_preflight_check(
                "packages",
                "dependencies",
                "unknown",
                "unavailable",
                "informational",
                INFO,
                f"Recorded package inventory is unavailable ({pkg_cap}); installed packages could not be compared.",
                details={"capture_status": pkg_cap},
            )
        )
        return checks, findings

    raw_records = pkg_dict.get("records")
    if not isinstance(raw_records, list):
        checks.append(
            _make_preflight_check(
                "packages",
                "dependencies",
                "unknown",
                "unavailable",
                "informational",
                INFO,
                "Recorded package list is missing or malformed; installed packages could not be compared.",
            )
        )
        return checks, findings

    valid_records = [
        rec
        for rec in raw_records
        if isinstance(rec, dict)
        and isinstance(rec.get("name"), str)
        and rec["name"].strip()
    ]
    if not valid_records:
        checks.append(
            _make_preflight_check(
                "packages",
                "dependencies",
                "not_checked",
                "not_checked",
                "informational",
                INFO,
                "Manifest recorded zero named packages; no package versions were checked.",
                details={"mode": pkg_dict.get("mode")},
            )
        )
        return checks, findings

    try:
        from pubrun.capture.packages import (
            get_installed_distribution_versions,
            normalize_package_name,
        )

        installed = get_installed_distribution_versions()
    except Exception as exc:
        msg = f"Could not inspect installed Python packages in the current environment ({type(exc).__name__})."
        checks.append(
            _make_preflight_check(
                "packages",
                "dependencies",
                "unknown",
                "unavailable",
                "material",
                WARN,
                msg,
                details={"error": type(exc).__name__},
            )
        )
        findings.append(
            _make_finding(
                WARN,
                "preflight_packages_probe_failed",
                msg,
                "Verify Python environment package metadata is readable.",
                category="dependencies",
                evidence_status="unavailable",
                impact="material",
                comparison="unknown",
                details={"error": type(exc).__name__},
            )
        )
        return checks, findings

    pkg_mode = pkg_dict.get("mode") if isinstance(pkg_dict.get("mode"), str) else None
    seen_norms = set()
    matched_names: List[str] = []
    editable_caveat_names: List[str] = []
    installed_only_editable: List[str] = []

    for rec in valid_records:
        rec_name = rec["name"].strip()
        norm_name = normalize_package_name(rec_name)
        if norm_name in seen_norms:
            continue
        seen_norms.add(norm_name)

        rec_ver = rec.get("version")
        rec_editable = rec.get("editable") is True
        inst_entry = installed.get(norm_name)

        if inst_entry is None:
            ver_label = (
                str(rec_ver)
                if rec_ver is not None and str(rec_ver).strip()
                else "unknown"
            )
            details = {
                "package": rec_name,
                "normalized_name": norm_name,
                "recorded_version": rec_ver,
                "installed_version": None,
                "status": "missing",
            }
            msg = (
                f"Recorded package '{rec_name}' (version {ver_label}) is missing from "
                f"the current Python environment."
            )
            sugg = (
                f"Install '{rec_name}=={rec_ver}' in your target environment before re-running."
                if isinstance(rec_ver, str) and rec_ver.strip() and rec_ver.strip().lower() != "unknown"
                else f"Install '{rec_name}' in your target environment before re-running."
            )
            checks.append(
                _make_preflight_check(
                    f"package:{norm_name}",
                    "dependencies",
                    "mismatch",
                    "observed",
                    "material",
                    WARN,
                    msg,
                    details=details,
                )
            )
            findings.append(
                _make_finding(
                    WARN,
                    "preflight_package_missing",
                    msg,
                    sugg,
                    category="dependencies",
                    evidence_status="observed",
                    impact="material",
                    comparison="mismatch",
                    details=details,
                )
            )
            continue

        inst_ver = inst_entry.get("version")
        inst_editable = inst_entry.get("editable") is True

        rec_ver_unknown = (
            rec_ver is None
            or (isinstance(rec_ver, str) and rec_ver.strip().lower() in ("", "unknown"))
        )
        if rec_ver_unknown:
            details = {
                "package": rec_name,
                "normalized_name": norm_name,
                "recorded_version": rec_ver,
                "installed_version": inst_ver,
            }
            msg = (
                f"Package '{rec_name}' is installed (version {inst_ver or 'unknown'}), "
                f"but the recorded version was missing or unknown."
            )
            checks.append(
                _make_preflight_check(
                    f"package:{norm_name}",
                    "dependencies",
                    "unknown",
                    "unavailable",
                    "informational",
                    INFO,
                    msg,
                    details=details,
                )
            )
            findings.append(
                _make_finding(
                    INFO,
                    "preflight_package_version_unknown",
                    msg,
                    None,
                    category="dependencies",
                    evidence_status="unavailable",
                    impact="informational",
                    comparison="unknown",
                    details=details,
                )
            )
            continue

        rec_ver_str = str(rec_ver).strip()
        if inst_ver is None or not str(inst_ver).strip():
            details = {
                "package": rec_name,
                "normalized_name": norm_name,
                "recorded_version": rec_ver_str,
                "installed_version": None,
            }
            msg = (
                f"Package '{rec_name}' is installed, but its current version metadata "
                f"is unavailable to compare against recorded version {rec_ver_str}."
            )
            checks.append(
                _make_preflight_check(
                    f"package:{norm_name}",
                    "dependencies",
                    "unknown",
                    "unavailable",
                    "informational",
                    INFO,
                    msg,
                    details=details,
                )
            )
            continue

        inst_ver_str = str(inst_ver).strip()
        if inst_ver_str != rec_ver_str:
            details = {
                "package": rec_name,
                "normalized_name": norm_name,
                "recorded_version": rec_ver_str,
                "installed_version": inst_ver_str,
                "recorded_editable": rec_editable,
                "installed_editable": inst_editable,
            }
            msg = (
                f"Package '{rec_name}' version differs: recorded {rec_ver_str}, "
                f"installed {inst_ver_str}."
            )
            checks.append(
                _make_preflight_check(
                    f"package:{norm_name}",
                    "dependencies",
                    "mismatch",
                    "observed",
                    "material",
                    WARN,
                    msg,
                    details=details,
                )
            )
            findings.append(
                _make_finding(
                    WARN,
                    "preflight_package_version_mismatch",
                    msg,
                    f"Install '{rec_name}=={rec_ver_str}' if exact dependency version parity is required.",
                    category="dependencies",
                    evidence_status="observed",
                    impact="material",
                    comparison="mismatch",
                    details=details,
                )
            )
            continue

        matched_names.append(rec_name)
        if rec_editable or inst_editable:
            editable_caveat_names.append(rec_name)
            if inst_editable and not rec_editable:
                installed_only_editable.append(rec_name)

    if matched_names:
        caveats: List[str] = []
        if editable_caveat_names:
            preview = ", ".join(editable_caveat_names[:5])
            extra = (
                ""
                if len(editable_caveat_names) <= 5
                else f" (+{len(editable_caveat_names) - 5} more)"
            )
            caveats.append(
                f"editable install(s) present ({preview}{extra}); version equality does not verify local editable source"
            )
        if pkg_mode == "imported-only":
            caveats.append(
                "recorded packages.mode was 'imported-only', so unrecorded or transitive packages were not checked"
            )
        caveat_suffix = f" ({'; '.join(caveats)})" if caveats else ""
        checks.append(
            _make_preflight_check(
                "packages_matched",
                "dependencies",
                "match",
                "observed",
                "informational",
                INFO,
                f"{len(matched_names)} recorded package(s) match installed versions{caveat_suffix}.",
                details={
                    "matched_count": len(matched_names),
                    "matched_packages": matched_names,
                    "editable_caveat_packages": editable_caveat_names,
                    "mode": pkg_mode,
                    "caveats": caveats,
                },
            )
        )
        if installed_only_editable:
            preview = ", ".join(installed_only_editable[:5])
            extra = (
                ""
                if len(installed_only_editable) <= 5
                else f" (+{len(installed_only_editable) - 5} more)"
            )
            findings.append(
                _make_finding(
                    INFO,
                    "preflight_packages_editable_caveat",
                    f"{len(installed_only_editable)} matched package(s) are currently installed in editable mode ({preview}{extra}); version match alone does not prove identical code.",
                    "Verify the editable source tree matches the recorded run or install versioned distributions.",
                    category="dependencies",
                    evidence_status="observed",
                    impact="portability",
                    comparison="match",
                    details={"packages": installed_only_editable[:20]},
                )
            )

    return checks, findings


def _preflight_source(
    manifest_dict: Dict[str, Any],
    *,
    cwd: Optional[Union[str, os.PathLike]],
    check_hashes: bool,
    max_hash_bytes: int,
    git_timeout: float,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Compare recorded Git commit/dirty state and entrypoint script identity."""
    checks: List[Dict[str, Any]] = []
    findings: List[Dict[str, Any]] = []

    # --- Git state ---
    git_sec = manifest_dict.get("git")
    git_dict = git_sec if isinstance(git_sec, dict) else {}
    git_cap = _capture_state_status(git_dict)
    rec_commit_raw = git_dict.get("commit")
    rec_commit = (
        rec_commit_raw.strip()
        if isinstance(rec_commit_raw, str) and rec_commit_raw.strip()
        else None
    )
    rec_dirty = git_dict.get("dirty")
    rec_repo_root_raw = git_dict.get("repo_root")
    rec_repo_root = (
        rec_repo_root_raw.strip()
        if isinstance(rec_repo_root_raw, str) and rec_repo_root_raw.strip()
        else None
    )

    if not git_dict or git_cap == "suppressed":
        checks.append(
            _make_preflight_check(
                "git_source",
                "source",
                "unknown",
                "not_checked",
                "informational",
                INFO,
                "Recorded Git provenance was not captured; current repository state was not compared.",
            )
        )
    elif git_cap in ("unavailable", "failed", "timeout", "partial") or not rec_commit:
        checks.append(
            _make_preflight_check(
                "git_source",
                "source",
                "unknown",
                "unavailable",
                "informational",
                INFO,
                "Recorded Git commit is unavailable; current repository state cannot be verified against it.",
                details={"capture_status": git_cap},
            )
        )
    else:
        try:
            timeout_val = float(git_timeout)
            if not math.isfinite(timeout_val) or timeout_val <= 0:
                timeout_val = DEFAULT_GIT_TIMEOUT
        except (TypeError, ValueError):
            timeout_val = DEFAULT_GIT_TIMEOUT

        deadline = time.monotonic() + timeout_val
        clean_env = {
            k: v for k, v in os.environ.items() if k not in _GIT_ENV_STRIP_KEYS
        }

        def _run_readonly_git(
            target: Path, git_args: List[str]
        ) -> Tuple[str, Optional[str]]:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                return ("timeout", None)
            try:
                from pubrun.capture.subprocesses import disable_spy

                with disable_spy():
                    res = subprocess.run(
                        ["git", "-C", str(target)] + git_args,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True,
                        timeout=remaining,
                        env=clean_env,
                    )
                if res.returncode == 0:
                    return ("ok", res.stdout)
                return ("error", res.stderr)
            except subprocess.TimeoutExpired:
                return ("timeout", None)
            except FileNotFoundError:
                return ("missing_git", None)
            except OSError as exc:
                return ("error", str(exc))

        if cwd is not None:
            probed_dir = Path(cwd)
            head_status, head_out = _run_readonly_git(probed_dir, ["rev-parse", "HEAD"])
        else:
            probed_dir = Path.cwd()
            head_status, head_out = _run_readonly_git(probed_dir, ["rev-parse", "HEAD"])
            if head_status == "error" and rec_repo_root:
                try:
                    fallback_dir = Path(rec_repo_root)
                    if fallback_dir.is_dir() and fallback_dir != probed_dir:
                        probed_dir = fallback_dir
                        head_status, head_out = _run_readonly_git(
                            probed_dir, ["rev-parse", "HEAD"]
                        )
                except OSError:
                    pass

        short_rec = rec_commit[:8]
        if head_status == "timeout":
            msg = f"Read-only Git probe timed out after {timeout_val:g}s while checking repository '{probed_dir}'."
            details = {
                "recorded_commit": rec_commit,
                "probed_dir": str(probed_dir),
                "git_timeout": timeout_val,
            }
            checks.append(
                _make_preflight_check(
                    "git_source",
                    "source",
                    "unknown",
                    "unavailable",
                    "material",
                    WARN,
                    msg,
                    details=details,
                )
            )
            findings.append(
                _make_finding(
                    WARN,
                    "preflight_git_timeout",
                    msg,
                    "Verify repository filesystem health or pass a larger `git_timeout` to compare Git state.",
                    category="source",
                    evidence_status="unavailable",
                    impact="material",
                    comparison="unknown",
                    details=details,
                )
            )
        elif head_status in ("missing_git", "error"):
            reason_text = (
                "git binary is not installed"
                if head_status == "missing_git"
                else f"'{probed_dir}' is not a readable Git repository"
            )
            checks.append(
                _make_preflight_check(
                    "git_source",
                    "source",
                    "unknown",
                    "unavailable",
                    "informational",
                    INFO,
                    f"Current Git state could not be checked ({reason_text}); recorded commit was {short_rec}.",
                    details={
                        "recorded_commit": rec_commit,
                        "probed_dir": str(probed_dir),
                        "reason": head_status,
                    },
                )
            )
        else:
            cur_commit = (head_out or "").strip()
            short_cur = cur_commit[:8] if cur_commit else "unknown"
            if cur_commit != rec_commit:
                details = {
                    "recorded_commit": rec_commit,
                    "current_commit": cur_commit,
                    "probed_dir": str(probed_dir),
                }
                msg = (
                    f"Git commit differs in '{probed_dir}': recorded {short_rec}, "
                    f"current HEAD is {short_cur}."
                )
                checks.append(
                    _make_preflight_check(
                        "git_source",
                        "source",
                        "mismatch",
                        "observed",
                        "material",
                        WARN,
                        msg,
                        details=details,
                    )
                )
                findings.append(
                    _make_finding(
                        WARN,
                        "preflight_git_commit_mismatch",
                        msg,
                        f"Check out commit {short_rec} in a separate worktree or branch before re-running.",
                        category="source",
                        evidence_status="observed",
                        impact="material",
                        comparison="mismatch",
                        details=details,
                    )
                )
            else:
                st_status, st_out = _run_readonly_git(
                    probed_dir, ["status", "--porcelain"]
                )
                if st_status == "timeout":
                    msg = f"Read-only `git status` timed out after {timeout_val:g}s while checking repository '{probed_dir}'."
                    details = {
                        "recorded_commit": rec_commit,
                        "current_commit": cur_commit,
                        "probed_dir": str(probed_dir),
                        "git_timeout": timeout_val,
                    }
                    checks.append(
                        _make_preflight_check(
                            "git_source",
                            "source",
                            "unknown",
                            "unavailable",
                            "material",
                            WARN,
                            msg,
                            details=details,
                        )
                    )
                    findings.append(
                        _make_finding(
                            WARN,
                            "preflight_git_timeout",
                            msg,
                            "Verify repository filesystem health or pass a larger `git_timeout` to compare Git working-tree state.",
                            category="source",
                            evidence_status="unavailable",
                            impact="material",
                            comparison="unknown",
                            details=details,
                        )
                    )
                elif st_status != "ok":
                    checks.append(
                        _make_preflight_check(
                            "git_source",
                            "source",
                            "unknown",
                            "unavailable",
                            "informational",
                            INFO,
                            f"Git HEAD matches {short_rec}, but current working-tree cleanliness could not be queried.",
                            details={
                                "recorded_commit": rec_commit,
                                "current_commit": cur_commit,
                                "probed_dir": str(probed_dir),
                            },
                        )
                    )
                else:
                    cur_dirty = bool((st_out or "").strip())
                    details = {
                        "recorded_commit": rec_commit,
                        "current_commit": cur_commit,
                        "recorded_dirty": rec_dirty,
                        "current_dirty": cur_dirty,
                        "probed_dir": str(probed_dir),
                    }
                    if rec_dirty is True:
                        dirty_note = (
                            " The current working tree also has uncommitted changes."
                            if cur_dirty
                            else ""
                        )
                        msg = (
                            f"Git HEAD matches recorded commit {short_rec}, but the recorded run "
                            f"had uncommitted changes that were not captured, so HEAD equality "
                            f"does not prove identical source.{dirty_note}"
                        )
                        checks.append(
                            _make_preflight_check(
                                "git_source",
                                "source",
                                "unknown",
                                "observed",
                                "material",
                                WARN,
                                msg,
                                details=details,
                            )
                        )
                        findings.append(
                            _make_finding(
                                WARN,
                                "preflight_git_recorded_dirty",
                                msg,
                                "Inspect any saved diff or compare source files manually because the recorded run had uncaptured uncommitted changes.",
                                category="source",
                                evidence_status="observed",
                                impact="material",
                                comparison="unknown",
                                details=details,
                            )
                        )
                    elif cur_dirty:
                        msg = (
                            f"Git HEAD matches recorded commit {short_rec}, but the current "
                            f"working tree in '{probed_dir}' has uncommitted changes."
                        )
                        checks.append(
                            _make_preflight_check(
                                "git_source",
                                "source",
                                "mismatch",
                                "observed",
                                "material",
                                WARN,
                                msg,
                                details=details,
                            )
                        )
                        findings.append(
                            _make_finding(
                                WARN,
                                "preflight_git_working_tree_dirty",
                                msg,
                                "Commit, stash, or revert local changes before re-running to match the clean recorded commit.",
                                category="source",
                                evidence_status="observed",
                                impact="material",
                                comparison="mismatch",
                                details=details,
                            )
                        )
                    elif rec_dirty is False:
                        checks.append(
                            _make_preflight_check(
                                "git_source",
                                "source",
                                "match",
                                "observed",
                                "informational",
                                INFO,
                                f"Current Git HEAD {short_cur} matches recorded commit {short_rec} and both trees are clean.",
                                details=details,
                            )
                        )
                    else:
                        checks.append(
                            _make_preflight_check(
                                "git_source",
                                "source",
                                "unknown",
                                "not_checked",
                                "informational",
                                INFO,
                                f"Current Git HEAD {short_cur} matches recorded commit {short_rec} and is clean, but recorded dirty state was not checked.",
                                details=details,
                            )
                        )

    # --- Entrypoint script ---
    inv_sec = manifest_dict.get("invocation")
    inv_dict = inv_sec if isinstance(inv_sec, dict) else {}
    entrypoint_type = inv_dict.get("entrypoint_type")
    script_dict = inv_dict.get("script") if isinstance(inv_dict.get("script"), dict) else {}
    raw_path = (
        script_dict.get("path").strip()
        if isinstance(script_dict.get("path"), str) and script_dict.get("path").strip()
        else None
    )
    raw_real = (
        script_dict.get("real_path").strip()
        if isinstance(script_dict.get("real_path"), str) and script_dict.get("real_path").strip()
        else None
    )

    if entrypoint_type != "script" or (not raw_path and not raw_real):
        checks.append(
            _make_preflight_check(
                "entrypoint_script",
                "source",
                "not_checked",
                "not_checked",
                "informational",
                INFO,
                "Entrypoint is not a recorded script file; script identity was not checked.",
                details={"entrypoint_type": entrypoint_type},
            )
        )
        return checks, findings

    base_dir = Path(cwd) if cwd is not None else Path.cwd()
    if raw_path:
        path_obj = Path(raw_path)
        if not path_obj.is_absolute():
            candidate = base_dir / path_obj
            if cwd is None and not candidate.exists() and raw_real:
                resolved_script = Path(raw_real)
            else:
                resolved_script = candidate
        else:
            if not path_obj.exists() and raw_real and Path(raw_real).exists():
                resolved_script = Path(raw_real)
            else:
                resolved_script = path_obj
    else:
        resolved_script = Path(raw_real)  # type: ignore[arg-type]

    try:
        st = os.stat(resolved_script)
    except OSError:
        st = None

    if st is None or not stat.S_ISREG(st.st_mode):
        msg = f"Recorded entrypoint script '{resolved_script}' is missing, unreadable, or not a regular file."
        details = {
            "recorded_path": raw_path,
            "recorded_real_path": raw_real,
            "resolved_path": str(resolved_script),
        }
        checks.append(
            _make_preflight_check(
                "entrypoint_script",
                "source",
                "mismatch",
                "unavailable",
                "material",
                WARN,
                msg,
                details=details,
            )
        )
        findings.append(
            _make_finding(
                WARN,
                "preflight_script_missing",
                msg,
                "Locate the recorded entrypoint script or run preflight from the project working directory.",
                category="source",
                evidence_status="unavailable",
                impact="material",
                comparison="mismatch",
                details=details,
            )
        )
        return checks, findings

    rec_sha256 = (
        script_dict.get("sha256").strip()
        if isinstance(script_dict.get("sha256"), str) and script_dict.get("sha256").strip()
        else None
    )
    rec_size = (
        script_dict.get("size")
        if isinstance(script_dict.get("size"), int) and not isinstance(script_dict.get("size"), bool)
        else None
    )

    if rec_sha256 and check_hashes:
        if st.st_size > max_hash_bytes:
            checks.append(
                _make_preflight_check(
                    "entrypoint_script",
                    "source",
                    "not_checked",
                    "not_checked",
                    "informational",
                    INFO,
                    f"Entrypoint script '{resolved_script}' ({st.st_size} bytes) exceeds max_hash_bytes ({max_hash_bytes} bytes); content hash was not checked.",
                    details={
                        "resolved_path": str(resolved_script),
                        "size_bytes": st.st_size,
                        "max_hash_bytes": max_hash_bytes,
                    },
                )
            )
            return checks, findings

        try:
            cur_sha256 = _stream_file_digest(resolved_script, "sha256")
        except OSError as exc:
            msg = f"Entrypoint script '{resolved_script}' could not be read for SHA-256 verification ({type(exc).__name__})."
            details = {"resolved_path": str(resolved_script), "error": type(exc).__name__}
            checks.append(
                _make_preflight_check(
                    "entrypoint_script",
                    "source",
                    "mismatch",
                    "unavailable",
                    "material",
                    WARN,
                    msg,
                    details=details,
                )
            )
            findings.append(
                _make_finding(
                    WARN,
                    "preflight_script_missing",
                    msg,
                    "Ensure the entrypoint script is readable before re-running.",
                    category="source",
                    evidence_status="unavailable",
                    impact="material",
                    comparison="mismatch",
                    details=details,
                )
            )
            return checks, findings

        if cur_sha256.lower() == rec_sha256.lower():
            checks.append(
                _make_preflight_check(
                    "entrypoint_script",
                    "source",
                    "match",
                    "observed",
                    "informational",
                    INFO,
                    f"Entrypoint script '{resolved_script}' matches recorded SHA-256 digest.",
                    details={
                        "resolved_path": str(resolved_script),
                        "recorded_sha256": rec_sha256,
                        "current_sha256": cur_sha256,
                    },
                )
            )
        else:
            msg = f"Entrypoint script '{resolved_script}' content differs from the recorded SHA-256 digest."
            details = {
                "resolved_path": str(resolved_script),
                "recorded_sha256": rec_sha256,
                "current_sha256": cur_sha256,
            }
            checks.append(
                _make_preflight_check(
                    "entrypoint_script",
                    "source",
                    "mismatch",
                    "observed",
                    "material",
                    WARN,
                    msg,
                    details=details,
                )
            )
            findings.append(
                _make_finding(
                    WARN,
                    "preflight_script_hash_mismatch",
                    msg,
                    "Inspect script differences or check out the recorded source revision before re-running.",
                    category="source",
                    evidence_status="observed",
                    impact="material",
                    comparison="mismatch",
                    details=details,
                )
            )
    else:
        if rec_size is not None and st.st_size != rec_size:
            msg = (
                f"Entrypoint script '{resolved_script}' size differs: recorded "
                f"{rec_size} bytes, current {st.st_size} bytes."
            )
            details = {
                "resolved_path": str(resolved_script),
                "recorded_size": rec_size,
                "current_size": st.st_size,
            }
            checks.append(
                _make_preflight_check(
                    "entrypoint_script",
                    "source",
                    "mismatch",
                    "observed",
                    "material",
                    WARN,
                    msg,
                    details=details,
                )
            )
            findings.append(
                _make_finding(
                    WARN,
                    "preflight_script_size_mismatch",
                    msg,
                    "Inspect script modifications before re-running.",
                    category="source",
                    evidence_status="observed",
                    impact="material",
                    comparison="mismatch",
                    details=details,
                )
            )
        else:
            reason = (
                "check_hashes=False was requested"
                if not check_hashes and rec_sha256
                else "no SHA-256 hash was recorded"
            )
            checks.append(
                _make_preflight_check(
                    "entrypoint_script",
                    "source",
                    "unknown",
                    "not_checked",
                    "informational",
                    INFO,
                    f"Entrypoint script '{resolved_script}' exists locally, but content hash was not checked ({reason}).",
                    details={
                        "resolved_path": str(resolved_script),
                        "recorded_size": rec_size,
                        "current_size": st.st_size,
                        "check_hashes": check_hashes,
                    },
                )
            )

    return checks, findings


def _extract_input_digest(rec: Dict[str, Any]) -> Tuple[Optional[str], Optional[str]]:
    """Return ``(algorithm, hex_value)`` from a recorded input file dict, or ``(None, None)``."""
    raw_sha256 = rec.get("sha256")
    if isinstance(raw_sha256, str) and raw_sha256.strip():
        return ("sha256", raw_sha256.strip())

    digest_obj = rec.get("digest")
    if isinstance(digest_obj, dict):
        alg = digest_obj.get("algorithm")
        val = digest_obj.get("value")
        if isinstance(alg, str) and alg.strip() and isinstance(val, str) and val.strip():
            return (alg.strip().lower(), val.strip())

    caller_digest = rec.get("caller_digest")
    if isinstance(caller_digest, dict):
        alg = caller_digest.get("algorithm")
        val = caller_digest.get("value")
        if isinstance(alg, str) and alg.strip() and isinstance(val, str) and val.strip():
            return (alg.strip().lower(), val.strip())

    raw_md5 = rec.get("md5")
    if isinstance(raw_md5, str) and raw_md5.strip():
        return ("md5", raw_md5.strip())

    return (None, None)


def _resolve_input_local_path(
    rec: Dict[str, Any],
    base_dir: Path,
) -> Tuple[Optional[Path], str]:
    """Resolve a recorded input path locally from ``realpath``, ``real_path``, or ``path``."""
    raw_realpath = rec.get("realpath") if isinstance(rec.get("realpath"), str) else ""
    raw_real_path = rec.get("real_path") if isinstance(rec.get("real_path"), str) else ""
    raw_path = rec.get("path") if isinstance(rec.get("path"), str) else ""

    raw_realpath = raw_realpath.strip()
    raw_real_path = raw_real_path.strip()
    raw_path = raw_path.strip()

    display = raw_path or raw_realpath or raw_real_path
    primary_raw = raw_realpath or raw_real_path or raw_path
    if not primary_raw:
        return None, ""

    primary = Path(primary_raw)
    if not primary.is_absolute():
        primary = base_dir / primary

    if not primary.exists() and raw_path:
        rel_candidate = Path(raw_path)
        if not rel_candidate.is_absolute():
            alt = base_dir / rel_candidate
            if alt.exists():
                return alt, display

    return primary, display


def _preflight_inputs(
    manifest_dict: Dict[str, Any],
    *,
    cwd: Optional[Union[str, os.PathLike]],
    check_hashes: bool,
    max_hash_bytes: int,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Compare accessible recorded input files against local files read-only."""
    checks: List[Dict[str, Any]] = []
    findings: List[Dict[str, Any]] = []

    data_files = manifest_dict.get("data_files")
    df_dict = data_files if isinstance(data_files, dict) else {}
    df_inputs = df_dict.get("inputs") if isinstance(df_dict.get("inputs"), list) else []
    df_mixed = df_dict.get("mixed") if isinstance(df_dict.get("mixed"), list) else []

    inv_sec = manifest_dict.get("invocation")
    inv_dict = inv_sec if isinstance(inv_sec, dict) else {}
    inv_inputs = inv_dict.get("inputs") if isinstance(inv_dict.get("inputs"), list) else []

    base_dir = Path(cwd) if cwd is not None else Path.cwd()

    # Collect and deduplicate by normalized path, preferring richer observed
    # data_files records with digests over argv-inferred invocation.inputs records.
    deduped: Dict[str, Tuple[Tuple[int, int], Dict[str, Any], Path, str, str]] = {}
    order_keys: List[str] = []

    raw_sources: List[Tuple[str, List[Any]]] = [
        ("data_files", df_inputs + df_mixed),
        ("invocation", inv_inputs),
    ]
    for origin, rec_list in raw_sources:
        for rec in rec_list:
            if not isinstance(rec, dict):
                continue
            resolved_path, display = _resolve_input_local_path(rec, base_dir)
            if resolved_path is None:
                continue

            is_asserted = _record_is_asserted(rec)
            alg, digest_val = _extract_input_digest(rec)
            if origin == "data_files":
                basis = "asserted" if is_asserted else "observed"
                src_rank = 2
            else:
                basis = "asserted" if is_asserted else "inferred"
                src_rank = 1

            digest_rank = (
                2 if (digest_val and not is_asserted) else (1 if digest_val else 0)
            )
            rank = (src_rank, digest_rank)

            try:
                norm_key = (
                    os.path.normcase(os.path.realpath(str(resolved_path)))
                    if resolved_path.exists()
                    else os.path.normcase(os.path.normpath(str(resolved_path)))
                )
            except OSError:
                norm_key = os.path.normcase(os.path.normpath(str(resolved_path)))

            if norm_key not in deduped:
                deduped[norm_key] = (rank, rec, resolved_path, display, basis)
                order_keys.append(norm_key)
            elif rank > deduped[norm_key][0]:
                deduped[norm_key] = (rank, rec, resolved_path, display, basis)

    if not order_keys:
        checks.append(
            _make_preflight_check(
                "inputs",
                "inputs_outputs",
                "not_checked",
                "not_checked",
                "informational",
                INFO,
                "No input file records were present in the manifest; local inputs were not checked.",
            )
        )
        return checks, findings

    for norm_key in order_keys:
        _, rec, resolved_path, display, basis = deduped[norm_key]
        check_name = f"input:{display}"

        if rec.get("entry_type") == "unsupported_remote_uri":
            checks.append(
                _make_preflight_check(
                    check_name,
                    "inputs_outputs",
                    "not_checked",
                    "not_checked",
                    "informational",
                    INFO,
                    f"Input '{display}' is a remote URI; preflight is strictly offline and does not fetch remote data.",
                    details={"path": display, "evidence_basis": basis},
                )
            )
            continue

        try:
            st = os.stat(resolved_path)
        except OSError:
            st = None

        if st is None:
            msg = f"Recorded input '{display}' ({resolved_path}) is missing or inaccessible locally."
            details = {
                "path": display,
                "resolved_path": str(resolved_path),
                "evidence_basis": basis,
            }
            checks.append(
                _make_preflight_check(
                    check_name,
                    "inputs_outputs",
                    "mismatch",
                    "unavailable",
                    "material",
                    WARN,
                    msg,
                    details=details,
                )
            )
            findings.append(
                _make_finding(
                    WARN,
                    "preflight_input_missing",
                    msg,
                    f"Ensure input '{display}' is present and readable at '{resolved_path}' before re-running.",
                    category="inputs_outputs",
                    evidence_status="unavailable",
                    impact="material",
                    comparison="mismatch",
                    details=details,
                )
            )
            continue

        # Recorded directory (e.g. invocation.inputs with is_dir=True or data_files directory).
        if rec.get("is_dir") is True or rec.get("entry_type") == "directory":
            if stat.S_ISDIR(st.st_mode):
                checks.append(
                    _make_preflight_check(
                        check_name,
                        "inputs_outputs",
                        "unknown",
                        "not_checked",
                        "informational",
                        INFO,
                        f"Recorded input directory '{display}' exists locally, but directory contents are not hashed.",
                        details={
                            "path": display,
                            "resolved_path": str(resolved_path),
                            "is_dir": True,
                            "evidence_basis": basis,
                        },
                    )
                )
            else:
                msg = f"Recorded input '{display}' was a directory, but '{resolved_path}' is no longer a directory."
                details = {
                    "path": display,
                    "resolved_path": str(resolved_path),
                    "expected_is_dir": True,
                    "evidence_basis": basis,
                }
                checks.append(
                    _make_preflight_check(
                        check_name,
                        "inputs_outputs",
                        "mismatch",
                        "unavailable",
                        "material",
                        WARN,
                        msg,
                        details=details,
                    )
                )
                findings.append(
                    _make_finding(
                        WARN,
                        "preflight_input_type_mismatch",
                        msg,
                        f"Verify that '{resolved_path}' points to the expected input directory.",
                        category="inputs_outputs",
                        evidence_status="unavailable",
                        impact="material",
                        comparison="mismatch",
                        details=details,
                    )
                )
            continue

        # Guard against non-regular files (directories, FIFOs, sockets, device nodes).
        if not stat.S_ISREG(st.st_mode):
            checks.append(
                _make_preflight_check(
                    check_name,
                    "inputs_outputs",
                    "not_checked",
                    "not_checked",
                    "informational",
                    INFO,
                    f"Input '{display}' ({resolved_path}) is not a regular file; skipped read-only hashing to avoid blocking.",
                    details={
                        "path": display,
                        "resolved_path": str(resolved_path),
                        "evidence_basis": basis,
                    },
                )
            )
            continue

        alg, expected_digest = _extract_input_digest(rec)
        raw_size_bytes = rec.get("size_bytes")
        raw_size = rec.get("size")
        if isinstance(raw_size_bytes, int) and not isinstance(raw_size_bytes, bool):
            rec_size: Optional[int] = raw_size_bytes
        elif isinstance(raw_size, int) and not isinstance(raw_size, bool):
            rec_size = raw_size
        else:
            rec_size = None

        if alg and expected_digest and check_hashes:
            if st.st_size > max_hash_bytes:
                checks.append(
                    _make_preflight_check(
                        check_name,
                        "inputs_outputs",
                        "not_checked",
                        "not_checked",
                        "informational",
                        INFO,
                        f"Input '{display}' ({st.st_size} bytes) exceeds max_hash_bytes ({max_hash_bytes} bytes); content hash was not checked.",
                        details={
                            "path": display,
                            "resolved_path": str(resolved_path),
                            "size_bytes": st.st_size,
                            "max_hash_bytes": max_hash_bytes,
                            "evidence_basis": basis,
                        },
                    )
                )
                continue

            if alg not in _SUPPORTED_PREFLIGHT_HASH_ALGS:
                checks.append(
                    _make_preflight_check(
                        check_name,
                        "inputs_outputs",
                        "not_checked",
                        "not_checked",
                        "informational",
                        INFO,
                        f"Input '{display}' uses unsupported digest algorithm '{alg}'; content hash was not checked.",
                        details={
                            "path": display,
                            "resolved_path": str(resolved_path),
                            "algorithm": alg,
                            "evidence_basis": basis,
                        },
                    )
                )
                continue

            try:
                actual_digest = _stream_file_digest(resolved_path, alg)
            except OSError as exc:
                msg = f"Input '{display}' ({resolved_path}) could not be read for {alg} hashing ({type(exc).__name__})."
                details = {
                    "path": display,
                    "resolved_path": str(resolved_path),
                    "error": type(exc).__name__,
                    "evidence_basis": basis,
                }
                checks.append(
                    _make_preflight_check(
                        check_name,
                        "inputs_outputs",
                        "mismatch",
                        "unavailable",
                        "material",
                        WARN,
                        msg,
                        details=details,
                    )
                )
                findings.append(
                    _make_finding(
                        WARN,
                        "preflight_input_missing",
                        msg,
                        f"Ensure input '{display}' is readable before re-running.",
                        category="inputs_outputs",
                        evidence_status="unavailable",
                        impact="material",
                        comparison="mismatch",
                        details=details,
                    )
                )
                continue

            ev_status = "asserted" if basis == "asserted" else "observed"
            basis_note = (
                " (verified against caller-asserted digest)"
                if basis == "asserted"
                else ""
            )
            details = {
                "path": display,
                "resolved_path": str(resolved_path),
                "algorithm": alg,
                "recorded_digest": expected_digest,
                "current_digest": actual_digest,
                "evidence_basis": basis,
            }
            if actual_digest.lower() == expected_digest.lower():
                checks.append(
                    _make_preflight_check(
                        check_name,
                        "inputs_outputs",
                        "match",
                        ev_status,
                        "informational",
                        INFO,
                        f"Input '{display}' matches recorded {alg} digest{basis_note}.",
                        details=details,
                    )
                )
            else:
                msg = f"Input '{display}' content differs from recorded {alg} digest{basis_note}."
                checks.append(
                    _make_preflight_check(
                        check_name,
                        "inputs_outputs",
                        "mismatch",
                        ev_status,
                        "material",
                        WARN,
                        msg,
                        details=details,
                    )
                )
                findings.append(
                    _make_finding(
                        WARN,
                        "preflight_input_hash_mismatch",
                        msg,
                        f"Verify that input '{display}' contains the expected dataset version before re-running.",
                        category="inputs_outputs",
                        evidence_status=ev_status,
                        impact="material",
                        comparison="mismatch",
                        details=details,
                    )
                )
        else:
            if rec_size is not None and st.st_size != rec_size:
                msg = (
                    f"Input '{display}' size differs: recorded {rec_size} bytes, "
                    f"current {st.st_size} bytes."
                )
                details = {
                    "path": display,
                    "resolved_path": str(resolved_path),
                    "recorded_size": rec_size,
                    "current_size": st.st_size,
                    "evidence_basis": basis,
                }
                checks.append(
                    _make_preflight_check(
                        check_name,
                        "inputs_outputs",
                        "mismatch",
                        "observed",
                        "material",
                        WARN,
                        msg,
                        details=details,
                    )
                )
                findings.append(
                    _make_finding(
                        WARN,
                        "preflight_input_size_mismatch",
                        msg,
                        f"Verify that input '{display}' matches the recorded file before re-running.",
                        category="inputs_outputs",
                        evidence_status="observed",
                        impact="material",
                        comparison="mismatch",
                        details=details,
                    )
                )
            elif not check_hashes and alg and expected_digest:
                checks.append(
                    _make_preflight_check(
                        check_name,
                        "inputs_outputs",
                        "not_checked",
                        "not_checked",
                        "informational",
                        INFO,
                        f"Input '{display}' exists locally, but content hashing was disabled (`check_hashes=False`); content identity was not verified.",
                        details={
                            "path": display,
                            "resolved_path": str(resolved_path),
                            "recorded_size": rec_size,
                            "current_size": st.st_size,
                            "check_hashes": False,
                            "evidence_basis": basis,
                        },
                    )
                )
            else:
                checks.append(
                    _make_preflight_check(
                        check_name,
                        "inputs_outputs",
                        "unknown",
                        "not_checked",
                        "informational",
                        INFO,
                        f"Input '{display}' exists locally (stat-only; no content digest was recorded), so content identity was not verified.",
                        details={
                            "path": display,
                            "resolved_path": str(resolved_path),
                            "recorded_size": rec_size,
                            "current_size": st.st_size,
                            "evidence_basis": basis,
                        },
                    )
                )

    return checks, findings


def _preflight_invocation(
    manifest_dict: Dict[str, Any],
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Check recorded working directory presence and command redaction status."""
    checks: List[Dict[str, Any]] = []
    findings: List[Dict[str, Any]] = []

    inv_sec = manifest_dict.get("invocation")
    inv_dict = inv_sec if isinstance(inv_sec, dict) else {}

    wd = (
        inv_dict.get("working_directory")
        if isinstance(inv_dict.get("working_directory"), dict)
        else {}
    )
    wd_path = (
        wd.get("path").strip()
        if isinstance(wd.get("path"), str) and wd.get("path").strip()
        else None
    )
    if not wd_path:
        checks.append(
            _make_preflight_check(
                "working_directory",
                "invocation",
                "not_checked",
                "not_checked",
                "informational",
                INFO,
                "No working directory path was recorded in the manifest.",
            )
        )
    else:
        try:
            wd_exists = Path(wd_path).is_dir()
        except OSError:
            wd_exists = False
        if wd_exists:
            checks.append(
                _make_preflight_check(
                    "working_directory",
                    "invocation",
                    "match",
                    "observed",
                    "informational",
                    INFO,
                    f"Recorded working directory '{wd_path}' exists locally.",
                    details={"recorded_working_directory": wd_path},
                )
            )
        else:
            msg = f"Recorded working directory '{wd_path}' does not exist locally (relocated or different host path)."
            details = {"recorded_working_directory": wd_path}
            checks.append(
                _make_preflight_check(
                    "working_directory",
                    "invocation",
                    "portability_diff",
                    "observed",
                    "portability",
                    INFO,
                    msg,
                    details=details,
                )
            )
            findings.append(
                _make_finding(
                    INFO,
                    "preflight_working_directory_missing",
                    msg,
                    "Run from your local project directory and adjust any hardcoded paths in the recorded command.",
                    category="invocation",
                    evidence_status="observed",
                    impact="portability",
                    comparison="portability_diff",
                    details=details,
                )
            )

    argv = inv_dict.get("argv") if isinstance(inv_dict.get("argv"), list) else None
    rerun_cmd = (
        inv_dict.get("rerun_command")
        if isinstance(inv_dict.get("rerun_command"), str) and inv_dict.get("rerun_command").strip()
        else None
    )
    if not argv and not rerun_cmd:
        checks.append(
            _make_preflight_check(
                "rerun_command",
                "invocation",
                "unknown",
                "unavailable",
                "informational",
                INFO,
                "No rerun_command or argv was recorded in the manifest.",
            )
        )
    else:
        argv_redacted = bool(
            argv and any(isinstance(arg, str) and "[REDACTED]" in arg for arg in argv)
        )
        rerun_redacted = bool(rerun_cmd and "[REDACTED]" in rerun_cmd)
        if argv_redacted or rerun_redacted:
            msg = (
                "Recorded rerun_command or argv contains [REDACTED] placeholders and "
                "cannot be executed verbatim without supplying redacted values."
            )
            details = {
                "argv_redacted": argv_redacted,
                "rerun_command_redacted": rerun_redacted,
            }
            checks.append(
                _make_preflight_check(
                    "rerun_command",
                    "invocation",
                    "mismatch",
                    "observed",
                    "material",
                    WARN,
                    msg,
                    details=details,
                )
            )
            findings.append(
                _make_finding(
                    WARN,
                    "preflight_rerun_command_redacted",
                    msg,
                    "Supply the redacted argument values manually before executing the recorded command.",
                    category="invocation",
                    evidence_status="observed",
                    impact="material",
                    comparison="mismatch",
                    details=details,
                )
            )
        else:
            checks.append(
                _make_preflight_check(
                    "rerun_command",
                    "invocation",
                    "match",
                    "observed",
                    "informational",
                    INFO,
                    "Recorded command contains no [REDACTED] placeholders.",
                )
            )

    return checks, findings


def _summarize_preflight_status(counts: Dict[str, int]) -> str:
    """Derive overall preflight comparison status from check outcome counts."""
    if counts.get("mismatch", 0) > 0:
        return "mismatch"
    if counts.get("unknown", 0) > 0:
        return "unknown"
    if counts.get("portability_diff", 0) > 0:
        return "portability_diff"
    if counts.get("match", 0) > 0:
        return "match"
    return "not_checked"


def compare_with_current_environment(
    manifest: Any,
    *,
    manifest_path: Optional[str] = None,
    cwd: Optional[Union[str, os.PathLike]] = None,
    check_hashes: bool = True,
    max_hash_bytes: int = DEFAULT_MAX_HASH_BYTES,
    git_timeout: float = DEFAULT_GIT_TIMEOUT,
) -> Dict[str, Any]:
    """Compare supported recorded manifest evidence against the current local environment.

    Strictly read-only, offline, and never raises. Never executes recorded commands,
    installs packages, fetches remote data, or mutates disk state, environment
    variables, or random seeds.
    """
    _ = manifest_path
    manifest_dict = manifest if isinstance(manifest, dict) else {}
    try:
        effective_max_hash = int(max_hash_bytes)
        if effective_max_hash < 0:
            effective_max_hash = 0
    except (TypeError, ValueError):
        effective_max_hash = DEFAULT_MAX_HASH_BYTES

    checks: List[Dict[str, Any]] = []
    findings: List[Dict[str, Any]] = []

    probes = (
        ("runtime", lambda: _preflight_runtime(manifest_dict)),
        ("dependencies", lambda: _preflight_packages(manifest_dict)),
        (
            "source",
            lambda: _preflight_source(
                manifest_dict,
                cwd=cwd,
                check_hashes=bool(check_hashes),
                max_hash_bytes=effective_max_hash,
                git_timeout=git_timeout,
            ),
        ),
        (
            "inputs_outputs",
            lambda: _preflight_inputs(
                manifest_dict,
                cwd=cwd,
                check_hashes=bool(check_hashes),
                max_hash_bytes=effective_max_hash,
            ),
        ),
        ("invocation", lambda: _preflight_invocation(manifest_dict)),
    )

    for cat_name, probe in probes:
        try:
            probe_checks, probe_findings = probe()
            checks.extend(probe_checks)
            findings.extend(probe_findings)
        except Exception as exc:
            checks.append(
                _make_preflight_check(
                    f"{cat_name}_probe",
                    cat_name,
                    "unknown",
                    "unavailable",
                    "informational",
                    INFO,
                    f"Preflight probe for '{cat_name}' could not complete ({type(exc).__name__}).",
                    details={"error": type(exc).__name__},
                )
            )

    counts = {
        outcome: sum(1 for c in checks if c.get("comparison") == outcome)
        for outcome in COMPARISON_OUTCOMES
    }
    overall_status = _summarize_preflight_status(counts)

    return {
        "requested": True,
        "status": overall_status,
        "counts": counts,
        "checks": checks,
        "findings": findings,
    }


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
    preflight: bool = False,
    cwd: Optional[Union[str, os.PathLike]] = None,
    check_hashes: bool = True,
    max_hash_bytes: int = DEFAULT_MAX_HASH_BYTES,
    git_timeout: float = DEFAULT_GIT_TIMEOUT,
) -> Dict[str, Any]:
    """Shared reproducibility assessment facade with optional read-only offline preflight."""
    assessment = assess_manifest_reproducibility(
        manifest,
        manifest_path=manifest_path,
        hydration_report=hydration_report,
        current_hostname=current_hostname,
        stale_parent_seconds=stale_parent_seconds,
    )
    if not preflight:
        return assessment

    preflight_result = compare_with_current_environment(
        manifest,
        manifest_path=manifest_path,
        cwd=cwd,
        check_hashes=check_hashes,
        max_hash_bytes=max_hash_bytes,
        git_timeout=git_timeout,
    )

    assessment["mode"] = "preflight"
    assessment["preflight"] = {
        "requested": True,
        "status": preflight_result["status"],
        "counts": preflight_result["counts"],
        "checks": preflight_result["checks"],
    }

    existing_codes = {f.get("code") for f in assessment["findings"]}
    for pf in preflight_result["findings"]:
        code = pf.get("code")
        # Avoid duplicating or contradicting recorded findings already emitted in base analysis.
        if code == "preflight_rerun_command_redacted" and "rerun_command_redacted" in existing_codes:
            continue
        if code == "preflight_hostname_diff" and "different_host" in existing_codes:
            continue
        assessment["findings"].append(pf)

    # Recompute affected category summaries and statuses (mismatch overrides gaps/uncertain/adequate).
    preflight_checks = preflight_result["checks"]
    for cat in assessment["categories"]:
        cat_name = cat["name"]
        cat_findings = [f for f in assessment["findings"] if f.get("category") == cat_name]
        cat_checks = [c for c in preflight_checks if c.get("category") == cat_name]

        cat["finding_codes"] = [f["code"] for f in cat_findings]
        cat["warn_count"] = sum(1 for f in cat_findings if f.get("severity") == WARN)
        cat["info_count"] = sum(1 for f in cat_findings if f.get("severity") == INFO)

        has_mismatch = any(
            f.get("comparison") == "mismatch" for f in cat_findings
        ) or any(c.get("comparison") == "mismatch" for c in cat_checks)
        has_material_warn = any(
            f.get("severity") == WARN and f.get("impact") == "material"
            for f in cat_findings
        ) or any(
            c.get("severity") == WARN and c.get("impact") == "material"
            for c in cat_checks
        )
        has_unknown_check = any(c.get("comparison") == "unknown" for c in cat_checks)

        prev_status = cat.get("status")
        if has_mismatch:
            cat["status"] = "mismatch"
            mismatch_count = sum(
                1 for c in cat_checks if c.get("comparison") == "mismatch"
            )
            if mismatch_count > 0:
                cat["summary"] = (
                    f"Preflight found {mismatch_count} material mismatch(es) in "
                    f"{cat['label'].lower()}."
                )
        elif prev_status == "gaps" or has_material_warn:
            cat["status"] = "gaps"
        elif prev_status == "adequate" and has_unknown_check:
            cat["status"] = "uncertain"

    next_action, next_actions = _prioritize_next_actions(
        assessment["findings"],
        default_action=_DEFAULT_PREFLIGHT_NEXT_ACTION,
    )
    assessment["next_action"] = next_action
    assessment["next_actions"] = next_actions
    assessment["summary"] = _build_summary(
        assessment["categories"],
        assessment["findings"],
        preflight=assessment["preflight"],
    )
    assessment["disclaimer"] = NON_GUARANTEE_DISCLAIMER
    return assessment


def should_fail_strict(assessment: Any, *, fail_on: str = "warn") -> bool:
    """Evaluate strict exit criteria against a reproducibility assessment dict.

    Supported ``fail_on`` values:
    - ``"warn"``: True if any finding has ``severity == "warn"``.
    - ``"mismatch"``: True if any finding has ``comparison == "mismatch"`` or
      ``(impact == "material" and severity == "warn")``, or any preflight check
      has ``comparison == "mismatch"``.
    - ``"unknown"``: True if ``fail_on="mismatch"`` is True, or any preflight
      check has ``comparison in ("unknown", "not_checked")``, or (when
      ``preflight.requested`` is False) any category has
      ``status in ("uncertain", "not_checked")``.
    """
    if fail_on not in FAIL_ON_MODES:
        raise ValueError(
            f"Unsupported fail_on value: {fail_on!r}; expected one of {', '.join(FAIL_ON_MODES)}."
        )
    if not isinstance(assessment, dict):
        return False

    findings = [
        f for f in (assessment.get("findings") or []) if isinstance(f, dict)
    ]
    preflight = assessment.get("preflight")
    preflight_dict = preflight if isinstance(preflight, dict) else {}
    preflight_requested = preflight_dict.get("requested") is True
    checks = [
        c for c in (preflight_dict.get("checks") or []) if isinstance(c, dict)
    ]
    categories = [
        c for c in (assessment.get("categories") or []) if isinstance(c, dict)
    ]

    if fail_on == "warn":
        return any(f.get("severity") == WARN for f in findings)

    mismatch_triggered = (
        any(
            f.get("comparison") == "mismatch"
            or (f.get("impact") == "material" and f.get("severity") == WARN)
            for f in findings
        )
        or any(c.get("comparison") == "mismatch" for c in checks)
    )
    if fail_on == "mismatch":
        return mismatch_triggered

    # fail_on == "unknown"
    if mismatch_triggered:
        return True
    if any(c.get("comparison") in ("unknown", "not_checked") for c in checks):
        return True
    if not preflight_requested:
        if any(c.get("status") in ("uncertain", "not_checked") for c in categories):
            return True
    return False


def _colorize(text: str, ansi_code: str, use_color: bool) -> str:
    """Wrap ``text`` with an ANSI SGR color code when enabled (never uses DIM code 2)."""
    if not use_color or not ansi_code or ansi_code == "2":
        return text
    return f"\033[{ansi_code}m{text}\033[0m"


_PREFLIGHT_OUTCOME_LABELS: Dict[str, Tuple[str, str]] = {
    "match": ("MATCH      ", "32"),
    "mismatch": ("MISMATCH   ", "31"),
    "portability_diff": ("PORTABILITY", "36"),
    "unknown": ("UNKNOWN    ", "33"),
    "not_checked": ("NOT_CHECKED", "36"),
}


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

    preflight = assessment.get("preflight")
    if isinstance(preflight, dict) and preflight.get("requested") is True:
        counts = preflight.get("counts") if isinstance(preflight.get("counts"), dict) else {}
        pf_status = str(preflight.get("status") or "unknown").upper()
        lines.append(
            f"Preflight [{pf_status}]: "
            f"{int(counts.get('match', 0))} match, "
            f"{int(counts.get('mismatch', 0))} mismatch, "
            f"{int(counts.get('portability_diff', 0))} portability_diff, "
            f"{int(counts.get('unknown', 0))} unknown, "
            f"{int(counts.get('not_checked', 0))} not_checked."
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

    preflight = assessment.get("preflight")
    if isinstance(preflight, dict) and preflight.get("requested") is True:
        pf_checks = preflight.get("checks") or []
        if isinstance(pf_checks, list) and pf_checks:
            lines.append("")
            lines.append("Preflight checks:")
            for chk in pf_checks:
                if not isinstance(chk, dict):
                    continue
                comp = str(chk.get("comparison", "unknown"))
                label_txt, ansi = _PREFLIGHT_OUTCOME_LABELS.get(
                    comp, (comp.upper(), "33")
                )
                badge = _colorize(f"[{label_txt:<11}]", ansi, color_active)
                chk_name = str(chk.get("name") or "check")
                ev = str(chk.get("evidence_status") or "unknown")
                msg = str(chk.get("message") or "")
                lines.append(f"  {badge} {chk_name} ({ev}): {msg}")

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
