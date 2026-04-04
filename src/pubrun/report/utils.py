import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Tuple
from datetime import datetime

logger = logging.getLogger("pubrun")

def hydrate_manifest(manifest_path: str, manifest: Dict[str, Any]) -> Tuple[Dict[str, Any], List[str]]:
    """
    If the manifest dictates a meta_ref, this utility fetches the overarching parent JSON map,
    cross-references the execution modification times for configuration drift, and natively merges 
    the heavy dependencies back into the child manifest in-memory.
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
                # Handle strictly conforming "Z" suffix representing UTC
                pt_str = parent_snap_started.replace("Z", "+00:00")
                pt_dt = datetime.fromisoformat(pt_str)
                # If script was modified AFTER the snapshot was finalized
                if child_script_mtime > pt_dt.timestamp():
                    warnings.append(f"Drift Detected: The script was modified after the parent meta.json snapshot was generated on {parent_snap_started}. Deep dependencies may be severely out of sync.")
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
