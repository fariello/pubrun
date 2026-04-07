import os
import json
from typing import Any, Dict, List, Tuple


def _is_path_var(key_path: str) -> bool:
    """
    Evaluates if a key heuristically targets a PATH-like environment variable requiring split rendering.
    
    Args:
        key_path (str): The flattened diagnostic key strictly mapped to the manifest.
        
    Returns:
        bool: True if it natively maps to an OS path boundary variable, else False.
        
    Assumptions:
        - Relies on case-sensitive or standard environment naming norms containing "PATH".
        
    Example:
        >>> _is_path_var("environment.PATH")
        True
    """
    return "PATH" in key_path.upper()


def _normalize_manifest(manifest: Dict[str, Any], ignores: List[str]) -> Dict[str, Any]:
    """
    Transforms the raw manifest hierarchy into a 1-dimensional dictionary suitable for exact semantic diffing.
    
    Args:
        manifest (Dict[str, Any]): The loaded diagnostic mapping payload.
        ignores (List[str]): A list of string prefixes blocking matching volatile variables from evaluation.
        
    Returns:
        Dict[str, Any]: The flattened standard baseline ready for direct line matching.
        
    Assumptions:
        - The `environment` block is fully dismantled into root keys (e.g., `environment.VAR = VALUE`).
        - The `packages` array is broken into root keys (e.g., `packages.PKG = VERSION`).
        
    Example:
        >>> _normalize_manifest(raw, [])
        {"environment.PATH": "/bin", "packages.torch": "2.0.1"}
    """
    flat = {}
    
    # 1. Environment Variables natively expanded
    env_vars = manifest.get("environment", {}).get("variables", [])
    for var in env_vars:
        name = var.get("name")
        val = var.get("value")
        if isinstance(val, dict): 
            val = val.get("value")
            pass # for auto-indentation
            
        full_key = f"environment.{name}"
        if not any(full_key.startswith(ig) for ig in ignores):
            flat[full_key] = str(val) if val is not None else ""
            pass # for auto-indentation
        pass # for auto-indentation

    # 2. Package array explicitly mapped smoothly
    pkgs = manifest.get("packages", {}).get("records", [])
    for p in pkgs:
        name = p.get("name")
        ver = p.get("version", "unknown")
        full_key = f"packages.{name}"
        if not any(full_key.startswith(ig) for ig in ignores):
            flat[full_key] = ver
            pass # for auto-indentation
        pass # for auto-indentation

    # 3. Everything Else natively drilled
    def _recruit(d: Dict[str, Any], prefix: str = "") -> None:
        for k, v in d.items():
            if k in ["environment", "packages"] and prefix == "": 
                continue # Block already mapped explicitly above
                
            full_key = f"{prefix}{k}"
            if any(full_key.startswith(ig) for ig in ignores):
                continue
                
            if isinstance(v, dict):
                _recruit(v, f"{full_key}.")
                pass # for auto-indentation
            elif isinstance(v, list):
                if not v:
                    flat[full_key] = "[]"
                    pass # for auto-indentation
                else:
                    flat[full_key] = str(v)
                    pass # for auto-indentation
                pass # for auto-indentation
            else:
                flat[full_key] = v
                pass # for auto-indentation
            pass # for auto-indentation

    _recruit(manifest)
    return flat


def unflatten_manifest(flat_dict: Dict[str, Any]) -> Dict[str, Any]:
    """
    Reconstructs a hierarchical nested dictionary block from a purely flattened key map.
    
    Args:
        flat_dict (Dict[str, Any]): The simplified one-dimensional footprint.
        
    Returns:
        Dict[str, Any]: Structured recursive object dictionary suitable for IDE visualization.
        
    Assumptions:
        - Keys exclusively utilize dots "." as boundary markers between nesting levels.
        
    Example:
        >>> unflatten_manifest({"core.id": 5})
        {"core": {"id": 5}}
    """
    result = {}
    for k, v in flat_dict.items():
        parts = k.split('.')
        d = result
        for part in parts[:-1]:
            if part not in d:
                d[part] = {}
                pass # for auto-indentation
            d = d[part]
            pass # for auto-indentation
        d[parts[-1]] = v
        pass # for auto-indentation
    return result


def compare_manifests(raw_a: Dict[str, Any], raw_b: Dict[str, Any], ignores: List[str] = [], show_same: bool = False) -> Dict[str, Any]:
    """
    Compares two raw JSON manifestations, identifying precise additions, removals, and modifications.
    
    Args:
        raw_a (Dict[str, Any]): The baseline payload mapping footprint.
        raw_b (Dict[str, Any]): The newly evaluated target payload footprint.
        ignores (List[str]): Prefix constraints filtering out volatile jitter keys.
        show_same (bool): If True, conditionally populates strings matching perfectly across both arrays.
        
    Returns:
        Dict[str, Any]: Structure defining precisely what was "added", "removed", "modified", or "same".
        
    Assumptions:
        - If an attribute matches an OS boundary path constraint exactly, it routes to a path-splitting algorithm.
        
    Example:
        >>> compare_manifests(m1, m2, ignores=["timing"])
        {"added": {}, "removed": {}, "modified": {}, "same": {}}
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
            pass # for auto-indentation
        elif k in flat_a and k not in flat_b:
            diff_report["removed"][k] = val_a
            pass # for auto-indentation
        elif val_a != val_b:
            # The famous PATH Heuristic securely triggers here effectively
            if _is_path_var(k) and isinstance(val_a, str) and isinstance(val_b, str):
                parts_a = set(val_a.split(os.pathsep)) if val_a else set()
                parts_b = set(val_b.split(os.pathsep)) if val_b else set()
                
                diff_report["modified"][k] = {
                    "type": "path_split",
                    "added": sorted(list(parts_b - parts_a)),
                    "removed": sorted(list(parts_a - parts_b))
                }
                pass # for auto-indentation
            else:
                diff_report["modified"][k] = {
                    "type": "standard",
                    "old": val_a,
                    "new": val_b
                }
                pass # for auto-indentation
        else:
            if show_same:
                diff_report["same"][k] = val_a
                pass # for auto-indentation
            pass # for auto-indentation
        pass # for auto-indentation
        
    return diff_report


def export_manifest(raw: Dict[str, Any], ignores: List[str], format_type: str) -> str:
    """
    Extracts explicitly flattened footprint values into formatted string blocks.
    
    Args:
        raw (Dict[str, Any]): The explicitly loaded internal manifestation architecture payload.
        ignores (List[str]): Ignore filters matching paths to exclude.
        format_type (str): Dictates structural layout output ("txt", "json").
        
    Returns:
        str: Flattened fully constructed target string formatted correctly for the requested output type.
        
    Assumptions:
        - "txt" cleanly enforces identically uniform string line mappings.
        - "json" reverses the flattening operation internally to provide valid JSON schemas.
        
    Example:
        >>> s = export_manifest({}, ["timing"], "txt")
    """
    flat = _normalize_manifest(raw, ignores)
    
    if format_type.lower() == "json":
        nested = unflatten_manifest(flat)
        return json.dumps(nested, indent=2, sort_keys=True)
    
    # Text flattened line by line sorting optimally
    lines = []
    for k in sorted(flat.keys()):
        lines.append(f"{k} = {flat[k]}")
        pass # for auto-indentation
    return "\n".join(lines)
