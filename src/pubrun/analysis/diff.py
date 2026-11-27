import collections
import fnmatch
import json
import math
import ntpath
import os
import posixpath
import re
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

_POSIX_OS_TOKENS = (
    "linux",
    "darwin",
    "mac",
    "bsd",
    "unix",
    "posix",
    "sunos",
    "solaris",
    "aix",
    "ubuntu",
    "debian",
    "fedora",
    "centos",
    "rhel",
    "rocky",
    "alma",
    "alpine",
    "arch",
    "suse",
)


def _infer_manifest_os_family(manifest: Any) -> Optional[str]:
    """Infer ``'windows'``, ``'posix'``, or ``None`` from ``manifest['host']['os_name']``."""
    if not isinstance(manifest, dict):
        return None
    host = manifest.get("host")
    if not isinstance(host, dict):
        return None
    raw_os = host.get("os_name")
    if isinstance(raw_os, dict):
        rep = raw_os.get("representation")
        if rep is None or rep == "plain":
            raw_os = raw_os.get("value")
        else:
            return None
    if not isinstance(raw_os, str) or not raw_os.strip():
        return None
    os_lower = raw_os.strip().lower()
    if os_lower.startswith("win"):
        return "windows"
    if any(tok in os_lower for tok in _POSIX_OS_TOKENS):
        return "posix"
    return None


def _infer_pathsep(manifest: Any) -> str:
    family = _infer_manifest_os_family(manifest)
    if family == "windows":
        return ";"
    if family == "posix":
        return ":"
    return os.pathsep


def _infer_basename(manifest: Any, path_str: str) -> str:
    family = _infer_manifest_os_family(manifest)
    if family == "windows":
        return ntpath.basename(path_str)
    if family == "posix":
        return posixpath.basename(path_str)
    return os.path.basename(path_str)


def _tag(x: Any) -> Any:
    """Type-tagged comparison key preserving bool/int distinction and ``NaN == NaN``."""
    if isinstance(x, float) and math.isnan(x):
        return ("float", "nan")
    return (type(x).__name__, x)


def _values_equal(a: Any, b: Any) -> bool:
    """Compare flattened manifest values with ``NaN == NaN`` and ``bool``/``int`` distinct."""
    if isinstance(a, list) and isinstance(b, list):
        if len(a) != len(b):
            return False
        return all(_values_equal(x, y) for x, y in zip(a, b))
    return bool(_tag(a) == _tag(b))


def _compile_ignores(ignores: List[str]) -> Callable[[str], bool]:
    """Pre-split ignores into exact set, dot-boundary prefix tuple, and case-sensitive glob regex."""
    exact_set: Set[str] = set()
    prefix_list: List[str] = []
    glob_patterns: List[str] = []
    for ig in ignores:
        if not isinstance(ig, str) or not ig:
            continue
        if "*" in ig or "?" in ig or "[" in ig:
            glob_patterns.append(fnmatch.translate(ig))
        elif ig.endswith("."):
            prefix_list.append(ig)
        else:
            exact_set.add(ig)
            prefix_list.append(ig + ".")
    prefix_tuple: Tuple[str, ...] = tuple(prefix_list)
    glob_re = (
        re.compile("|".join(f"(?:{pat})" for pat in glob_patterns))
        if glob_patterns
        else None
    )

    def _should_ignore(key: str) -> bool:
        if key in exact_set:
            return True
        if prefix_tuple and key.startswith(prefix_tuple):
            return True
        if glob_re is not None and glob_re.match(key) is not None:
            return True
        return False

    return _should_ignore


def _sanitize_json_floats(val: Any) -> Any:
    """Recursively replace non-finite floats (NaN/Inf/-Inf) with ``None``."""
    if isinstance(val, float):
        return None if not math.isfinite(val) else val
    if isinstance(val, dict):
        return {k: _sanitize_json_floats(v) for k, v in val.items()}
    if isinstance(val, list):
        return [_sanitize_json_floats(item) for item in val]
    if isinstance(val, tuple):
        return [_sanitize_json_floats(item) for item in val]
    return val


def _is_path_var(key_path: str) -> bool:
    """Return True if the key is a PATH-style environment variable.

    Only ``environment.<NAME>`` keys whose variable name contains ``PATH`` are
    split on the OS path separator; manifest fields such as
    ``invocation.script.path`` stay scalar diffs.
    """
    prefix = "environment."
    if not key_path.startswith(prefix):
        return False
    return "PATH" in key_path[len(prefix):].upper()


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
    flat: Dict[str, Any] = {}

    _should_ignore = _compile_ignores(ignores)

    # 1. Environment variables expanded into individual keys. Guard against a
    # non-list `variables` or non-dict entries from a foreign/edited manifest.
    env_section = manifest.get("environment", {})
    env_vars = env_section.get("variables", []) if isinstance(env_section, dict) else []
    if isinstance(env_vars, list):
        for var in env_vars:
            if not isinstance(var, dict):
                continue
            name = var.get("name")
            if not isinstance(name, str) or not name:
                continue
            val = var.get("value")
            if isinstance(val, dict):
                rep = val.get("representation")
                if rep == "hashed":
                    hv = val.get("hash_value")
                    algo = val.get("hash_algorithm")
                    if not hv and isinstance(val.get("hash"), dict):
                        hv = val["hash"].get("value")
                        algo = val["hash"].get("algorithm")
                    if hv and algo:
                        val = f"[HASHED:{algo}:{hv}]"
                    elif hv:
                        val = f"[HASHED:{hv}]"
                    else:
                        val = "[HASHED]"
                elif rep == "redacted":
                    val = "[REDACTED]"
                else:
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
            if not isinstance(name, str) or not name:
                continue
            ver = p.get("version", "unknown")
            full_key = f"packages.{name}"
            if not _should_ignore(full_key):
                flat[full_key] = ver

    # 2b. Subprocesses: at --deep, flatten element-by-element (full detail). At --standard,
    # SUMMARIZE as a count + per-process identities (argv[0] basename) so a subprocess-heavy
    # run does not explode into thousands of leaf keys ("basic" already ignores the section).
    # This reuses the same normalized-dict shape (one flat key per identity) rather than a
    # second array code path.
    subs = manifest.get("subprocesses", [])
    if depth != "deep" and isinstance(subs, list) and subs and not _should_ignore("subprocesses"):
        counts: Dict[str, int] = {}
        for sp in subs:
            if not isinstance(sp, dict):
                continue
            argv = sp.get("argv")
            if isinstance(argv, list) and argv:
                ident = _infer_basename(manifest, str(argv[0]))
            else:
                ident = "?"
            counts[ident] = counts.get(ident, 0) + 1
        # One key for the total, plus one per distinct identity with its invocation count.
        tot_key = "subprocesses.count"
        if not _should_ignore(tot_key):
            flat[tot_key] = len(subs)
        for ident, n in counts.items():
            k = f"subprocesses.by_command.{ident}"
            if not _should_ignore(k):
                flat[k] = n

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

    # At non-deep depth we already summarized `subprocesses` above, so skip the element-by-
    # element flatten for it here. At `--deep`, let it flatten fully (full detail).
    _handled_top = ["environment", "packages"]
    if depth != "deep":
        _handled_top.append("subprocesses")

    def _recruit(d: Dict[str, Any], prefix: str = "") -> None:
        for k, v in d.items():
            if k in _handled_top and prefix == "":
                continue  # Already handled above
            _recruit_val(v, f"{prefix}{k}")

    _recruit(manifest)

    # Synthesize explicit legacy timing semantics when comparing timing so legacy
    # wall-clock manifests and new monotonic manifests surface definition changes
    # even when numeric elapsed_seconds match.
    raw_timing = manifest.get("timing")
    if isinstance(raw_timing, dict) and not _should_ignore("timing"):
        from pubrun.status import classify_timing_semantics

        sem = classify_timing_semantics(raw_timing)
        if sem["is_legacy"]:
            if not _should_ignore("timing.duration_clock"):
                flat["timing.duration_clock"] = "wall_clock"
            if not _should_ignore("timing.elapsed_basis"):
                flat["timing.elapsed_basis"] = "wall_clock_legacy"

    # Collapse derived invocation views: `command_line` and `rerun_command` are both derived
    # from `argv`, so a single argv change would otherwise be reported three times. Below
    # `--deep`, when argv is present, drop the two derived views so one argv change = one line.
    if depth != "deep":
        has_argv = any(k == "invocation.argv" or k.startswith("invocation.argv.") for k in flat)
        if has_argv:
            for derived in ("invocation.command_line", "invocation.rerun_command"):
                flat.pop(derived, None)

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


def compare_manifests(raw_a: Dict[str, Any], raw_b: Dict[str, Any], ignores: Optional[List[str]] = None, show_same: bool = False, depth: str = "basic") -> Dict[str, Any]:
    """Compare two manifests and return added, removed, modified, and same keys.

    Args:
        raw_a: Baseline manifest.
        raw_b: Comparison manifest.
        ignores: Key prefixes to exclude from diffing.
        show_same: If True, populate the ``"same"`` bucket.
        depth: The diff depth level ("basic", "standard", or "deep").
    """
    if ignores is None:
        ignores = []
    flat_a = _normalize_manifest(raw_a, ignores, depth)
    flat_b = _normalize_manifest(raw_b, ignores, depth)

    diff_report: Dict[str, Dict[str, Any]] = {
        "added": {},    # Exists in B, missing from A
        "removed": {},  # Exists in A, missing from B
        "modified": {}, # Shared key, but value changed
        "same": {},     # Absolute identical matches structurally
    }

    all_keys = set(flat_a.keys()).union(set(flat_b.keys()))

    sep_a = _infer_pathsep(raw_a)
    sep_b = _infer_pathsep(raw_b)

    for k in sorted(list(all_keys)):
        val_a = flat_a.get(k)
        val_b = flat_b.get(k)

        if k not in flat_a and k in flat_b:
            diff_report["added"][k] = val_b
        elif k in flat_a and k not in flat_b:
            diff_report["removed"][k] = val_a
        elif not _values_equal(val_a, val_b):
            if isinstance(val_a, list) and isinstance(val_b, list):
                # Diff lists as multisets using type-tagged keys so bool/int do
                # NOT alias, NaN == NaN, and duplicate multiplicity changes report
                # exact added/removed elements without false reordering.
                tags_a = [_tag(x) for x in val_a]
                tags_b = [_tag(x) for x in val_b]
                rem_a = collections.Counter(tags_a)
                rem_b = collections.Counter(tags_b)

                added_items: List[Any] = []
                common_b_tags: List[Any] = []
                for x, t in zip(val_b, tags_b):
                    if rem_a[t] > 0:
                        rem_a[t] -= 1
                        common_b_tags.append(t)
                    else:
                        added_items.append(x)

                removed_items: List[Any] = []
                common_a_tags: List[Any] = []
                for x, t in zip(val_a, tags_a):
                    if rem_b[t] > 0:
                        rem_b[t] -= 1
                        common_a_tags.append(t)
                    else:
                        removed_items.append(x)

                order_changed = common_a_tags != common_b_tags

                diff_report["modified"][k] = {
                    "type": "list_diff",
                    "added": added_items,
                    "removed": removed_items,
                    "order_changed": order_changed,
                    "old": val_a,
                    "new": val_b
                }
            # PATH-style variable: split on each manifest's inferred OS path separator
            elif _is_path_var(k) and isinstance(val_a, str) and isinstance(val_b, str):
                seq_a = val_a.split(sep_a) if val_a else []
                seq_b = val_b.split(sep_b) if val_b else []
                parts_a = set(seq_a)
                parts_b = set(seq_b)
                common_seq_a = [p for p in seq_a if p in parts_b]
                common_seq_b = [p for p in seq_b if p in parts_a]

                diff_report["modified"][k] = {
                    "type": "path_split",
                    "added": sorted(list(parts_b - parts_a)),
                    "removed": sorted(list(parts_a - parts_b)),
                    "order_changed": common_seq_a != common_seq_b,
                    "old": val_a,
                    "new": val_b,
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

    if "timing.elapsed_seconds" in diff_report["modified"]:
        from pubrun.status import classify_timing_semantics

        sem_a = classify_timing_semantics(
            raw_a.get("timing") if isinstance(raw_a, dict) else None
        )
        sem_b = classify_timing_semantics(
            raw_b.get("timing") if isinstance(raw_b, dict) else None
        )
        if (sem_a["elapsed_basis"], sem_a["duration_clock"]) != (
            sem_b["elapsed_basis"],
            sem_b["duration_clock"],
        ):
            old_basis = sem_a["elapsed_basis"] or "unknown"
            old_clock = sem_a["duration_clock"] or "unknown"
            new_basis = sem_b["elapsed_basis"] or "unknown"
            new_clock = sem_b["duration_clock"] or "unknown"
            diff_report["modified"]["timing.elapsed_seconds"]["note"] = (
                f"timing definition changed ({old_basis}/{old_clock} -> {new_basis}/{new_clock})"
            )

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
        nested = _sanitize_json_floats(unflatten_manifest(flat))
        return json.dumps(nested, indent=2, sort_keys=True, allow_nan=False)

    # Text flattened line by line sorting optimally
    lines = []
    for k in sorted(flat.keys()):
        lines.append(f"{k} = {flat[k]}")
    return "\n".join(lines)
