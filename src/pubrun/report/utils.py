import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Tuple
from datetime import datetime

logger = logging.getLogger("pubrun")


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


def hydrate_manifest(manifest_path: str, manifest: Dict[str, Any]) -> Tuple[Dict[str, Any], List[str]]:
    """Merge parent meta.json context into a child manifest.

    If the manifest references a ``meta_ref``, loads the parent snapshot
    and fills in any missing or suppressed sections (hardware, process,
    python, packages, environment, git).  Also checks for environmental
    drift by comparing script mtime against the parent snapshot timestamp.

    Args:
        manifest_path: Path to the child manifest.json file.
        manifest: The parsed manifest dictionary.

    Returns:
        (hydrated_manifest, warnings): The enriched manifest and a list
        of human-readable warning strings (drift, missing parent, etc.).
    """
    warnings = []
    
    meta_ref = manifest.get("meta_ref")
    if not meta_ref:
        return manifest, warnings
        
    try:
        manifest_dir = Path(manifest_path).parent
        meta_path = manifest_dir / meta_ref
        
        # Resolve the meta_ref path
        meta_path = meta_path.resolve()
        
        # Sandbox check: reject if meta_ref does not point to a .json file.
        if not meta_path.name.endswith(".json"):
            warnings.append(f"Security: meta_ref '{meta_ref}' does not point to a .json file. Rejected.")
            return manifest, warnings

        # Security: reject meta_ref paths outside allowed directories.
        if not _is_meta_ref_allowed(meta_path, manifest_dir):
            warnings.append(
                f"Security: meta_ref '{meta_ref}' resolves to '{meta_path}' which is outside "
                f"the allowed directories. Set [report].allow_external_meta_ref = true or add "
                f"the parent directory to [report].meta_ref_allowed_dirs to permit this."
            )
            return manifest, warnings
        
        if not meta_path.exists():
            warnings.append(f"Linked Parent Meta Snapshot '{meta_ref}' not found at {meta_path}. The diagnostic output will lack deep dependencies.")
            return manifest, warnings
            
        with open(meta_path, "r", encoding="utf-8") as f:
            meta = json.load(f)
            
        # 1. Evaluate Drift (Script MTime vs Meta Generation Time)
        child_script_mtime = manifest.get("invocation", {}).get("script", {}).get("mtime")
        parent_snap_started = meta.get("timing", {}).get("started_at_utc")
        
        if child_script_mtime and parent_snap_started:
            try:
                # Direct float comparison for Epoch offsets
                if child_script_mtime > parent_snap_started:
                    warnings.append(f"Drift Detected: The script was modified after the parent meta.json snapshot was tracking structurally. Deep dependencies may be severely out of sync.")
            except Exception as e:
                logger.debug(f"Failed to parse datetime for drift resolution: {e}")
                
        # 2. Dynamic Hydration
        # Merge heavy global context blocks ONLY if the child run suppressed them.
        sections_to_hydrate = ["hardware", "process", "python", "packages", "environment", "git"]
        for sec in sections_to_hydrate:
            # If child didn't track it, or it was actively suppressed due to a lightweight profile...
            if sec not in manifest or manifest[sec].get("capture_state", {}).get("status") in ["suppressed", "off", "unavailable", "unknown", "partial"]:
                if sec in meta:
                    manifest[sec] = meta[sec]
                    # Decorate the manifest node to visually indicate it was sourced from the parent
                    manifest[sec]["is_hydrated"] = True
                    
        return manifest, warnings
            
    except Exception as e:
        warnings.append(f"Failed to hydrate meta_ref: {e}")
        return manifest, warnings
