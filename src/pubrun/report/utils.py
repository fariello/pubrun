"""Report utilities including structured parent meta_ref hydration."""

import copy
from dataclasses import dataclass, field
import json
import logging
import math
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("pubrun")

HYDRABLE_SECTIONS: Tuple[str, ...] = (
    "hardware",
    "process",
    "python",
    "packages",
    "environment",
    "git",
)

_HYDRATION_INCOMPLETE_STATUSES = frozenset(
    ("suppressed", "off", "unavailable", "unknown", "partial")
)

_NON_OBSERVED_IDENTITY_STATUSES = frozenset(
    ("suppressed", "off", "unavailable", "unknown", "partial", "failed", "timeout")
)

HYDRATION_STATUSES: Tuple[str, ...] = (
    "none",
    "hydrated",
    "missing",
    "blocked_by_policy",
    "invalid_extension",
    "invalid_json",
    "invalid_type",
    "failed",
)


@dataclass
class HydrationReport:
    """Structured report describing parent ``meta_ref`` hydration results."""

    meta_ref: Optional[str] = None
    resolved_path: Optional[str] = None
    status: str = "none"
    inherited_sections: List[str] = field(default_factory=list)
    direct_sections: List[str] = field(default_factory=list)
    parent_started_at_utc: Optional[float] = None
    child_started_at_utc: Optional[float] = None
    age_seconds: Optional[float] = None
    script_modified_after_parent: Optional[bool] = None
    identity_mismatches: List[Dict[str, Any]] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Return a JSON-serializable dictionary copy of this report."""
        return {
            "meta_ref": self.meta_ref,
            "resolved_path": self.resolved_path,
            "status": self.status,
            "inherited_sections": list(self.inherited_sections),
            "direct_sections": list(self.direct_sections),
            "parent_started_at_utc": self.parent_started_at_utc,
            "child_started_at_utc": self.child_started_at_utc,
            "age_seconds": self.age_seconds,
            "script_modified_after_parent": self.script_modified_after_parent,
            "identity_mismatches": [dict(item) for item in self.identity_mismatches],
            "warnings": list(self.warnings),
        }


def _is_numeric(value: Any) -> bool:
    """Return True if ``value`` is a finite int or float (excluding bool)."""
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
    )


def _section_capture_status(section: Any) -> Optional[str]:
    """Safely extract ``section['capture_state']['status']`` if present."""
    if not isinstance(section, dict):
        return None
    capture_state = section.get("capture_state")
    if isinstance(capture_state, dict):
        status = capture_state.get("status")
        if isinstance(status, str):
            return status
    return None


def _is_direct_section(section: Any) -> bool:
    """Return True when a child section dict was directly captured."""
    if not isinstance(section, dict):
        return False
    status = _section_capture_status(section)
    return status not in _HYDRATION_INCOMPLETE_STATUSES


def _unwrap_plain_string(value: Any) -> Optional[str]:
    """Return a non-empty plain string, unwrapping plain redacted-value dicts."""
    if isinstance(value, str):
        return value if value else None
    if isinstance(value, dict):
        representation = value.get("representation")
        if representation is None or representation == "plain":
            inner = value.get("value")
            if isinstance(inner, str) and inner:
                return inner
    return None


def _extract_identity_field(
    doc: Dict[str, Any],
    section_name: str,
    field_name: str,
    *,
    require_direct: bool = False,
) -> Optional[str]:
    """Extract a comparable identity string from ``doc[section_name][field_name]``."""
    section = doc.get(section_name)
    if not isinstance(section, dict):
        return None
    status = _section_capture_status(section)
    if require_direct and status in _NON_OBSERVED_IDENTITY_STATUSES:
        return None
    if status in ("suppressed", "off", "unavailable", "failed", "timeout"):
        return None
    return _unwrap_plain_string(section.get(field_name))


def _compare_parent_child_identity(
    parent_meta: Dict[str, Any],
    child_manifest: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """Compare directly observed parent and child host, python, and git identity."""
    mismatches: List[Dict[str, Any]] = []
    comparisons = (
        ("host", "hostname", "host.hostname"),
        ("host", "os_name", "host.os_name"),
        ("python", "version", "python.version"),
        ("git", "commit", "git.commit"),
    )
    for section_name, field_name, label in comparisons:
        parent_val = _extract_identity_field(parent_meta, section_name, field_name)
        child_val = _extract_identity_field(
            child_manifest,
            section_name,
            field_name,
            require_direct=True,
        )
        if parent_val is not None and child_val is not None and parent_val != child_val:
            mismatches.append(
                {
                    "field": label,
                    "parent": parent_val,
                    "child": child_val,
                }
            )
    return mismatches


def _is_meta_ref_allowed(meta_path: Path, manifest_dir: Path) -> bool:
    """Check if a resolved meta_ref path is allowed by configuration.

    By default, meta_ref must resolve within the manifest's parent directory.
    The ``[report].allow_external_meta_ref`` and ``[report].meta_ref_allowed_dirs``
    config keys can relax this constraint for HPC workflows.

    Returns True if the path is permitted, False otherwise.
    """
    from pubrun.config import resolve_config

    config = resolve_config()
    report_cfg = config.get("report", {})

    # Escape hatch: allow all external refs
    if report_cfg.get("allow_external_meta_ref", False):
        return True

    resolved_manifest_dir = manifest_dir.resolve()
    resolved_meta = meta_path.resolve()

    # Check if meta_path is inside the manifest directory tree
    try:
        resolved_meta.relative_to(resolved_manifest_dir)
        return True
    except ValueError:
        pass

    # Check against the explicit allowlist
    allowed_dirs = report_cfg.get("meta_ref_allowed_dirs", [])
    for allowed in allowed_dirs:
        allowed_path = Path(allowed).resolve()
        try:
            resolved_meta.relative_to(allowed_path)
            return True
        except ValueError:
            continue

    return False


def hydrate_manifest_with_report(
    manifest_path: str,
    manifest: Dict[str, Any],
) -> Tuple[Dict[str, Any], List[str], HydrationReport]:
    """Merge parent ``meta.json`` context into a child manifest with a structured report.

    Does not mutate the caller's ``manifest`` dictionary in place. Preserves the
    security check order (``.json`` extension check, then ``_is_meta_ref_allowed``
    policy check) before probing file existence or reading disk content.

    Args:
        manifest_path: Path to the child ``manifest.json`` file.
        manifest: Parsed child manifest dictionary.

    Returns:
        ``(hydrated_manifest, warnings, report)`` where ``report`` is a
        ``HydrationReport`` describing hydration outcome, inherited versus
        direct sections, parent age, script drift, and identity mismatches.
    """
    warnings: List[str] = []

    if not isinstance(manifest, dict):
        warnings.append(
            f"Failed to hydrate meta_ref: expected manifest dict, got {type(manifest).__name__}."
        )
        report = HydrationReport(status="failed", warnings=list(warnings))
        return {}, warnings, report

    direct_sections = [
        sec for sec in HYDRABLE_SECTIONS if _is_direct_section(manifest.get(sec))
    ]
    timing = manifest.get("timing")
    child_started_at_utc: Optional[float] = None
    if isinstance(timing, dict) and _is_numeric(timing.get("started_at_utc")):
        child_started_at_utc = float(timing["started_at_utc"])

    hydrated: Dict[str, Any] = dict(manifest)

    meta_ref = manifest.get("meta_ref")
    if meta_ref is None or (isinstance(meta_ref, str) and not meta_ref.strip()):
        report = HydrationReport(
            meta_ref=None if meta_ref is None else meta_ref,
            resolved_path=None,
            status="none",
            inherited_sections=[],
            direct_sections=direct_sections,
            parent_started_at_utc=None,
            child_started_at_utc=child_started_at_utc,
            age_seconds=None,
            script_modified_after_parent=None,
            identity_mismatches=[],
            warnings=[],
        )
        return hydrated, warnings, report

    if not isinstance(meta_ref, str):
        warnings.append(
            f"Invalid meta_ref: expected a string path, got {type(meta_ref).__name__}."
        )
        report = HydrationReport(
            meta_ref=str(meta_ref),
            resolved_path=None,
            status="invalid_type",
            inherited_sections=[],
            direct_sections=direct_sections,
            child_started_at_utc=child_started_at_utc,
            warnings=list(warnings),
        )
        return hydrated, warnings, report

    resolved_path_str: Optional[str] = None
    try:
        manifest_dir = Path(manifest_path).parent
        meta_path = (manifest_dir / meta_ref).resolve()
        resolved_path_str = str(meta_path)

        # 1. Sandbox check: reject if meta_ref does not point to a .json file.
        if not meta_path.name.endswith(".json"):
            warnings.append(
                f"Security: meta_ref '{meta_ref}' does not point to a .json file. Rejected."
            )
            report = HydrationReport(
                meta_ref=meta_ref,
                resolved_path=resolved_path_str,
                status="invalid_extension",
                inherited_sections=[],
                direct_sections=direct_sections,
                child_started_at_utc=child_started_at_utc,
                warnings=list(warnings),
            )
            return hydrated, warnings, report

        # 2. Security: reject meta_ref paths outside allowed directories before existence probe.
        if not _is_meta_ref_allowed(meta_path, manifest_dir):
            warnings.append(
                f"Security: meta_ref '{meta_ref}' resolves to '{meta_path}' which is outside "
                f"the allowed directories. Set [report].allow_external_meta_ref = true or add "
                f"the parent directory to [report].meta_ref_allowed_dirs to permit this."
            )
            report = HydrationReport(
                meta_ref=meta_ref,
                resolved_path=resolved_path_str,
                status="blocked_by_policy",
                inherited_sections=[],
                direct_sections=direct_sections,
                child_started_at_utc=child_started_at_utc,
                warnings=list(warnings),
            )
            return hydrated, warnings, report

        # 3. Existence check.
        if not meta_path.exists():
            warnings.append(
                f"Linked Parent Meta Snapshot '{meta_ref}' not found at {meta_path}. "
                f"The diagnostic output will lack deep dependencies."
            )
            report = HydrationReport(
                meta_ref=meta_ref,
                resolved_path=resolved_path_str,
                status="missing",
                inherited_sections=[],
                direct_sections=direct_sections,
                child_started_at_utc=child_started_at_utc,
                warnings=list(warnings),
            )
            return hydrated, warnings, report

        # 4. Load JSON.
        try:
            with open(meta_path, "r", encoding="utf-8") as f:
                meta = json.load(f)
        except json.JSONDecodeError as exc:
            warnings.append(
                f"Invalid JSON in parent meta snapshot '{meta_ref}': {exc}"
            )
            report = HydrationReport(
                meta_ref=meta_ref,
                resolved_path=resolved_path_str,
                status="invalid_json",
                inherited_sections=[],
                direct_sections=direct_sections,
                child_started_at_utc=child_started_at_utc,
                warnings=list(warnings),
            )
            return hydrated, warnings, report

        # 5. Validate payload type and manifest_type when present.
        if not isinstance(meta, dict):
            warnings.append(
                f"Invalid parent meta snapshot '{meta_ref}': expected JSON object, "
                f"got {type(meta).__name__}."
            )
            report = HydrationReport(
                meta_ref=meta_ref,
                resolved_path=resolved_path_str,
                status="invalid_type",
                inherited_sections=[],
                direct_sections=direct_sections,
                child_started_at_utc=child_started_at_utc,
                warnings=list(warnings),
            )
            return hydrated, warnings, report

        if "manifest_type" in meta and meta.get("manifest_type") != "pubrun-meta-snapshot":
            warnings.append(
                f"Invalid parent meta snapshot '{meta_ref}': expected manifest_type "
                f"'pubrun-meta-snapshot', got {meta.get('manifest_type')!r}."
            )
            report = HydrationReport(
                meta_ref=meta_ref,
                resolved_path=resolved_path_str,
                status="invalid_type",
                inherited_sections=[],
                direct_sections=direct_sections,
                child_started_at_utc=child_started_at_utc,
                warnings=list(warnings),
            )
            return hydrated, warnings, report

        # 6. Compute timestamps, parent age, script drift, and identity mismatches.
        parent_timing = meta.get("timing")
        parent_started_at_utc: Optional[float] = None
        if isinstance(parent_timing, dict) and _is_numeric(
            parent_timing.get("started_at_utc")
        ):
            parent_started_at_utc = float(parent_timing["started_at_utc"])

        age_seconds: Optional[float] = None
        if child_started_at_utc is not None and parent_started_at_utc is not None:
            age_seconds = child_started_at_utc - parent_started_at_utc

        invocation = manifest.get("invocation")
        script = invocation.get("script") if isinstance(invocation, dict) else None
        child_script_mtime: Optional[float] = None
        if isinstance(script, dict) and _is_numeric(script.get("mtime")):
            child_script_mtime = float(script["mtime"])

        script_modified_after_parent: Optional[bool] = None
        if child_script_mtime is not None and parent_started_at_utc is not None:
            script_modified_after_parent = child_script_mtime > parent_started_at_utc
            if script_modified_after_parent:
                warnings.append(
                    "Drift Detected: The script was modified after the parent meta.json "
                    "snapshot was tracking structurally. Deep dependencies may be severely "
                    "out of sync."
                )

        identity_mismatches = _compare_parent_child_identity(meta, manifest)

        # 7. Merge missing or incomplete hydrable sections without mutating inputs.
        inherited_sections: List[str] = []
        for sec in HYDRABLE_SECTIONS:
            if not _is_direct_section(manifest.get(sec)):
                parent_section = meta.get(sec)
                if isinstance(parent_section, dict):
                    copied_section = copy.deepcopy(parent_section)
                    copied_section["is_hydrated"] = True
                    hydrated[sec] = copied_section
                    inherited_sections.append(sec)

        report = HydrationReport(
            meta_ref=meta_ref,
            resolved_path=resolved_path_str,
            status="hydrated",
            inherited_sections=inherited_sections,
            direct_sections=direct_sections,
            parent_started_at_utc=parent_started_at_utc,
            child_started_at_utc=child_started_at_utc,
            age_seconds=age_seconds,
            script_modified_after_parent=script_modified_after_parent,
            identity_mismatches=identity_mismatches,
            warnings=list(warnings),
        )
        return hydrated, warnings, report

    except Exception as exc:
        logger.debug("Failed to hydrate meta_ref '%s': %s", meta_ref, exc)
        warnings.append(f"Failed to hydrate meta_ref: {exc}")
        report = HydrationReport(
            meta_ref=meta_ref,
            resolved_path=resolved_path_str,
            status="failed",
            inherited_sections=[],
            direct_sections=direct_sections,
            child_started_at_utc=child_started_at_utc,
            warnings=list(warnings),
        )
        return hydrated, warnings, report


def hydrate_manifest(
    manifest_path: str,
    manifest: Dict[str, Any],
) -> Tuple[Dict[str, Any], List[str]]:
    """Merge parent meta.json context into a child manifest.

    If the manifest references a ``meta_ref``, loads the parent snapshot
    and fills in any missing or suppressed sections (hardware, process,
    python, packages, environment, git). Also checks for environmental
    drift by comparing script mtime against the parent snapshot timestamp.

    Args:
        manifest_path: Path to the child manifest.json file.
        manifest: The parsed manifest dictionary.

    Returns:
        (hydrated_manifest, warnings): The enriched manifest and a list
        of human-readable warning strings (drift, missing parent, etc.).
    """
    hydrated, warnings, _ = hydrate_manifest_with_report(manifest_path, manifest)
    return hydrated, warnings
