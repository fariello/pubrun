import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Tuple
from datetime import datetime

logger = logging.getLogger("pubrun")

def hydrate_manifest(manifest_path: str, manifest: Dict[str, Any]) -> Tuple[Dict[str, Any], List[str]]:
    """
    Binds missing heavy diagnostic subsets from an overarching parent meta-snapshot.
    
    If the manifest dictates a meta_ref, this utility fetches the overlapping JSON map,
    cross-references the execution modification times for configuration drift, and natively merges 
    the heavy dependencies back into the child manifest in-memory.

    Args:
        manifest_path (str): A string representing the absolute or relative origin mapping path of the target manifest.
        manifest (Dict[str, Any]): The mapped manifest JSON payload string keys natively loaded into python memory.

    Returns:
        Tuple[Dict[str, Any], List[str]]: The structurally complete hydrated dictionary mapping alongside potential drift warning triggers.

    Assumptions:
        - An active security sandbox check verifies that the target `meta_ref` pointer rigidly targets `.json` extensions, deflecting path-traversal read exploitation.
        
    Example:
        >>> new_map, warnings = hydrate_manifest("/manifest.json", raw_manifest)
    """
    warnings = []
    
    meta_ref = manifest.get("meta_ref")
    if not meta_ref:
        return manifest, warnings
        
    try:
        manifest_dir = Path(manifest_path).parent
        meta_path = manifest_dir / meta_ref
        
        # Resolve it securely
        meta_path = meta_path.resolve()
        
        # Sandbox check: warn (but don't block) if meta_ref points outside the manifest dir.
        # HPC workflows legitimately reference shared parent meta.json files.
        if not meta_path.name.endswith(".json"):
            warnings.append(f"Security Sandbox Triggered: meta_ref '{meta_ref}' does not point to a valid .json snapshot file.")
            return manifest, warnings

        try:
            if not meta_path.is_relative_to(manifest_dir.resolve()):
                warnings.append(f"meta_ref '{meta_ref}' resolves outside the run directory to '{meta_path}'. Verify this is intentional.")
        except (TypeError, AttributeError):
            # is_relative_to not available before Python 3.9; skip check
            pass
        
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
        # We natively merge heavy global context blocks ONLY if the child run suppressed them.
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
