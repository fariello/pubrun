import os
import json
import fnmatch
from typing import Any, Dict, List, Tuple


def _is_path_var(key_path: str) -> bool:
    """Return True if the key looks like a PATH-style variable."""
    return "PATH" in key_path.upper()


def _format_epoch(ts: float, include_float: bool) -> str:
    try:
        from datetime import datetime, timezone
        dt = datetime.fromtimestamp(ts, tz=timezone.utc)
        fmt_str = dt.strftime("%Y-%m-%d %H:%M:%S")
        if include_float:
            return f"{fmt_str} ({ts})"
        return fmt_str
    except Exception:
        return str(ts)


def _normalize_manifest(manifest: Dict[str, Any], ignores: List[str], depth: str = "basic") -> Dict[str, Any]:
    """Flatten a manifest into a one-dimensional dict suitable for diffing.

    Environment variables and packages are expanded into individual keys.
    Keys matching any pattern in ``ignores`` are excluded.
    """
    flat = {}

    # Helper to check if a key matches any ignore pattern
    def _should_ignore(key: str) -> bool:
        for ig in ignores:
            if "*" in ig:
                if fnmatch.fnmatch(key, ig):
                    return True
            elif key.startswith(ig):
                return True
        return False

    # 1. Environment variables expanded into individual keys. Guard against a
    # non-list `variables` or non-dict entries from a foreign/edited manifest.
    env_section = manifest.get("environment", {})
    env_vars = env_section.get("variables", []) if isinstance(env_section, dict) else []
    if isinstance(env_vars, list):
        for var in env_vars:
            if not isinstance(var, dict):
                continue
            name = var.get("name")
            val = var.get("value")
            if isinstance(val, dict):
                val = val.get("value")

            full_key = f"environment.{name}"
            if not _should_ignore(full_key):
                flat[full_key] = str(val) if val is not None else ""

    # 2. Packages expanded into individual keys (same guarding).
    pkg_section = manifest.get("packages", {})
    pkgs = pkg_section.get("records", []) if isinstance(pkg_section, dict) else []
    if isinstance(pkgs, list):
        for p in pkgs:
            if not isinstance(p, dict):
                continue
            name = p.get("name")
            ver = p.get("version", "unknown")
            full_key = f"packages.{name}"
            if not _should_ignore(full_key):
                flat[full_key] = ver

    # 3. Recursively flatten everything else
    def _recruit_val(v: Any, full_key: str) -> None:
        if _should_ignore(full_key):
            return

        if isinstance(v, dict):
            for sub_k, sub_v in v.items():
                _recruit_val(sub_v, f"{full_key}.{sub_k}")
        elif isinstance(v, list):
            if not v:
                flat[full_key] = []
            elif all(isinstance(x, (str, int, float, bool)) or x is None for x in v):
                # Also check and format elements if they are epoch floats
                formatted_list = []
                for x in v:
                    if isinstance(x, (int, float)) and full_key.endswith("_utc"):
                        formatted_list.append(_format_epoch(float(x), include_float=(depth != "basic")))
                    else:
                        formatted_list.append(x)
                flat[full_key] = formatted_list
            else:
                for idx, item in enumerate(v):
                    _recruit_val(item, f"{full_key}.{idx}")
        else:
            if isinstance(v, (int, float)) and full_key.endswith("_utc"):
                flat[full_key] = _format_epoch(float(v), include_float=(depth != "basic"))
            else:
                flat[full_key] = v

    def _recruit(d: Dict[str, Any], prefix: str = "") -> None:
        for k, v in d.items():
            if k in ["environment", "packages"] and prefix == "":
                continue # Already handled above
            _recruit_val(v, f"{prefix}{k}")

    _recruit(manifest)
    return flat


def unflatten_manifest(flat_dict: Dict[str, Any]) -> Dict[str, Any]:
    """Reconstruct a nested dict from dot-separated flat keys.

    Tolerates prefix collisions: if the flat keys contain both a scalar leaf
    and a deeper key under the same prefix (e.g. a package literally named
    ``numpy.core`` or an env var containing a dot), walking into the scalar
    would raise ``TypeError``. When that happens, keep the last write under a
    suffixed key rather than crashing the export. (IPD 20260705 EC-18.)
    """
    result: Dict[str, Any] = {}
    for k, v in flat_dict.items():
        parts = k.split('.')
        d = result
        ok = True
        for part in parts[:-1]:
            existing = d.get(part) if isinstance(d, dict) else None
            if not isinstance(existing, dict):
                if part in d:
                    # A scalar already occupies this prefix; cannot descend.
                    ok = False
                    break
                d[part] = {}
            d = d[part]
        if not ok:
            # Preserve the value under the fully-qualified flat key so nothing
            # is silently lost, without corrupting the nested structure.
            result[k] = v
            continue
        leaf = parts[-1]
        if isinstance(d.get(leaf), dict) and not isinstance(v, dict):
            # A nested subtree already occupies this leaf; keep both by
            # storing the scalar under the flat key.
            result[k] = v
        else:
            d[leaf] = v
    return result


def compare_manifests(raw_a: Dict[str, Any], raw_b: Dict[str, Any], ignores: List[str] = [], show_same: bool = False, depth: str = "basic") -> Dict[str, Any]:
    """Compare two manifests and return added, removed, modified, and same keys.

    Args:
        raw_a: Baseline manifest.
        raw_b: Comparison manifest.
        ignores: Key prefixes to exclude from diffing.
        show_same: If True, populate the ``"same"`` bucket.
        depth: The diff depth level ("basic", "standard", or "deep").
    """
    flat_a = _normalize_manifest(raw_a, ignores, depth)
    flat_b = _normalize_manifest(raw_b, ignores, depth)

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
            if isinstance(val_a, list) and isinstance(val_b, list):
                # Diff lists of simple elements. Compare by a type-tagged key so
                # bool/int do NOT alias (True == 1, False == 0 in plain ==),
                # which would produce wrong added/removed/reordered markers.
                # (IPD 20260705 EC-19.)
                def _tag(x: Any) -> Any:
                    return (type(x).__name__, x)

                set_a = {_tag(x) for x in val_a}
                set_b = {_tag(x) for x in val_b}
                added_items = [x for x in val_b if _tag(x) not in set_a]
                removed_items = [x for x in val_a if _tag(x) not in set_b]

                common_a = [x for x in val_a if _tag(x) in set_b]
                common_b = [x for x in val_b if _tag(x) in set_a]
                order_changed = [_tag(x) for x in common_a] != [_tag(x) for x in common_b]

                diff_report["modified"][k] = {
                    "type": "list_diff",
                    "added": added_items,
                    "removed": removed_items,
                    "order_changed": order_changed,
                    "old": val_a,
                    "new": val_b
                }
            # PATH-style variable: split on OS path separator
            elif _is_path_var(k) and isinstance(val_a, str) and isinstance(val_b, str):
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


def export_manifest(raw: Dict[str, Any], ignores: List[str], fmt: str = "txt", depth: str = "basic") -> str:
    """Export a flattened manifest as a text or JSON string.

    Args:
        raw: Loaded manifest dictionary.
        ignores: Key prefixes to exclude.
        fmt: Output format (``"txt"`` or ``"json"``).
        depth: The diff depth level ("basic", "standard", or "deep").
    """
    flat = _normalize_manifest(raw, ignores, depth)

    if fmt.lower() == "json":
        nested = unflatten_manifest(flat)
        return json.dumps(nested, indent=2, sort_keys=True)

    # Text flattened line by line sorting optimally
    lines = []
    for k in sorted(flat.keys()):
        lines.append(f"{k} = {flat[k]}")
    return "\n".join(lines)
