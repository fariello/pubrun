import os
import json
from typing import Any, Dict, List, Tuple


def _is_path_var(key_path: str) -> bool:
    """Return True if the key looks like a PATH-style variable."""
    return "PATH" in key_path.upper()


def _normalize_manifest(manifest: Dict[str, Any], ignores: List[str]) -> Dict[str, Any]:
    """Flatten a manifest into a one-dimensional dict suitable for diffing.

    Environment variables and packages are expanded into individual keys.
    Keys matching any prefix in ``ignores`` are excluded.
    """
    flat = {}
    
    # 1. Environment variables expanded into individual keys
    env_vars = manifest.get("environment", {}).get("variables", [])
    for var in env_vars:
        name = var.get("name")
        val = var.get("value")
        if isinstance(val, dict): 
            val = val.get("value")
            
        full_key = f"environment.{name}"
        if not any(full_key.startswith(ig) for ig in ignores):
            flat[full_key] = str(val) if val is not None else ""

    # 2. Packages expanded into individual keys
    pkgs = manifest.get("packages", {}).get("records", [])
    for p in pkgs:
        name = p.get("name")
        ver = p.get("version", "unknown")
        full_key = f"packages.{name}"
        if not any(full_key.startswith(ig) for ig in ignores):
            flat[full_key] = ver

    # 3. Everything else recursively flattened
    def _recruit(d: Dict[str, Any], prefix: str = "") -> None:
        for k, v in d.items():
            if k in ["environment", "packages"] and prefix == "": 
                continue # Already handled above
                
            full_key = f"{prefix}{k}"
            if any(full_key.startswith(ig) for ig in ignores):
                continue
                
            if isinstance(v, dict):
                _recruit(v, f"{full_key}.")
            elif isinstance(v, list):
                if not v:
                    flat[full_key] = "[]"
                else:
                    flat[full_key] = str(v)
            else:
                flat[full_key] = v

    _recruit(manifest)
    return flat


def unflatten_manifest(flat_dict: Dict[str, Any]) -> Dict[str, Any]:
    """Reconstruct a nested dict from dot-separated flat keys."""
    result = {}
    for k, v in flat_dict.items():
        parts = k.split('.')
        d = result
        for part in parts[:-1]:
            if part not in d:
                d[part] = {}
            d = d[part]
        d[parts[-1]] = v
    return result


def compare_manifests(raw_a: Dict[str, Any], raw_b: Dict[str, Any], ignores: List[str] = [], show_same: bool = False) -> Dict[str, Any]:
    """Compare two manifests and return added, removed, modified, and same keys.

    Args:
        raw_a: Baseline manifest.
        raw_b: Comparison manifest.
        ignores: Key prefixes to exclude from diffing.
        show_same: If True, populate the ``"same"`` bucket.
    """
    flat_a = _normalize_manifest(raw_a, ignores)
    flat_b = _normalize_manifest(raw_b, ignores)
    
    diff_report = {
        "added": {},    # Exists in B, missing from A
        "removed": {},  # Exists in A, missing from B
        "modified": {}, # Shared key, but value changed
        "same": {},     # Absolute identical matches structurally
    }
    
    all_keys = set(flat_a.keys()).union(set(flat_b.keys()))
    
    for k in sorted(list(all_keys)):
        val_a = flat_a.get(k)
        val_b = flat_b.get(k)
        
        if k not in flat_a and k in flat_b:
            diff_report["added"][k] = val_b
        elif k in flat_a and k not in flat_b:
            diff_report["removed"][k] = val_a
        elif val_a != val_b:
            # PATH-style variable: split on OS path separator
            if _is_path_var(k) and isinstance(val_a, str) and isinstance(val_b, str):
                parts_a = set(val_a.split(os.pathsep)) if val_a else set()
                parts_b = set(val_b.split(os.pathsep)) if val_b else set()
                
                diff_report["modified"][k] = {
                    "type": "path_split",
                    "added": sorted(list(parts_b - parts_a)),
                    "removed": sorted(list(parts_a - parts_b))
                }
            else:
                diff_report["modified"][k] = {
                    "type": "standard",
                    "old": val_a,
                    "new": val_b
                }
        else:
            if show_same:
                diff_report["same"][k] = val_a
        
    return diff_report


def export_manifest(raw: Dict[str, Any], ignores: List[str], fmt: str = "txt") -> str:
    """Export a flattened manifest as a text or JSON string.

    Args:
        raw: Loaded manifest dictionary.
        ignores: Key prefixes to exclude.
        fmt: Output format (``"txt"`` or ``"json"``).
    """
    flat = _normalize_manifest(raw, ignores)
    
    if fmt.lower() == "json":
        nested = unflatten_manifest(flat)
        return json.dumps(nested, indent=2, sort_keys=True)
    
    # Text flattened line by line sorting optimally
    lines = []
    for k in sorted(flat.keys()):
        lines.append(f"{k} = {flat[k]}")
    return "\n".join(lines)
