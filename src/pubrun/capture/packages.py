"""Resolve loaded and installed Python modules to distribution metadata.

Uses only the Python standard library and supports Python 3.8 through 3.14.
This module never imports target modules to identify them.
"""
from collections import deque
from dataclasses import dataclass, field
import csv
import importlib.machinery
import importlib.metadata
import inspect
import json
import os
from pathlib import Path, PurePosixPath
import re
import site
import stat
import sys
import sysconfig
import threading
from typing import Any, Dict, FrozenSet, List, Optional, Set, Tuple

from pubrun.capture._markers import (
    default_marker_environment,
    evaluate_marker,
    parse_requirement,
)

# Keep references to the unmodified stdlib lookup functions so we can detect
# monkeypatched test providers without triggering redundant site-packages scans.
_ORIG_DISTRIBUTION = importlib.metadata.distribution
_ORIG_VERSION = importlib.metadata.version

# PEP 503 normalization pattern collapsing runs of '-', '_', and '.' to '-'.
_PEP503_RE = re.compile(r"[-_.]+")

# Detects marker clauses gated on a positive `extra` comparison (used by
# `top-level-installed` so optional extra dependencies do not hide root packages).
_EXTRA_MARKER_RE = re.compile(
    r"""(?:\bextra\b\s*(?:==|===|\bin\b)\s*['"]|['"][^'"]*['"]\s*(?:==|===|\bin\b)\s*\bextra\b)"""
)

_MISSING = object()

# Allowed keys in schemas/manifest.schema.json until child plan ijipnx extends it.
_SCHEMA_PACKAGE_RECORD_KEYS = (
    "name",
    "version",
    "location",
    "editable",
    "source",
    "required_by",
)


@dataclass
class _DistInfo:
    """Cached metadata summary for one installed Python distribution."""

    name: str
    normalized_name: str
    version: Optional[str]
    location: Optional[str]
    editable: Optional[bool]
    requires: Tuple[str, ...]
    top_levels: Tuple[str, ...]
    dist: Any
    metadata_error: Optional[str] = None


@dataclass
class _DistributionIndex:
    """Single-pass index mapping installed distributions and top-level modules."""

    fingerprint: Tuple[Any, ...]
    by_normalized_name: Dict[str, _DistInfo]
    module_to_dists: Dict[str, List[_DistInfo]]
    metadata_errors: Tuple[Dict[str, Any], ...]
    error_by_module: Dict[str, List[Dict[str, Any]]] = field(default_factory=dict)
    error_by_dist_name: Dict[str, List[Dict[str, Any]]] = field(default_factory=dict)
    _resolved_files_cache: Dict[int, FrozenSet[str]] = field(
        default_factory=dict, repr=False
    )
    _files_lock: threading.Lock = field(default_factory=threading.Lock, repr=False)


_CACHE_LOCK = threading.Lock()
_CACHED_FINGERPRINT: Optional[Tuple[Any, ...]] = None
_CACHED_INDEX: Optional[_DistributionIndex] = None
_CACHED_PROVIDER: Any = None


def normalize_package_name(name: str) -> str:
    """Return the PEP 503 normalized form of a Python distribution name."""
    return _PEP503_RE.sub("-", name).lower()


def _parse_req_name(req_str: str) -> str:
    """Extract the package name from a PEP 508 requirement string."""
    parsed = parse_requirement(req_str)
    return parsed.name if parsed is not None else ""


def _safe_getattr(obj: Any, attr: str, default: Any = None) -> Any:
    """Read an attribute without letting lazy or broken proxies raise."""
    try:
        return getattr(obj, attr, default)
    except Exception:
        return default


def _normalize_real_path(path_str: str) -> Optional[str]:
    """Return ``os.path.normcase(os.path.realpath(path_str))`` or None on error."""
    if not path_str:
        return None
    try:
        return os.path.normcase(os.path.realpath(path_str))
    except OSError:
        return None


def _norm_path_is_within(norm_path: str, norm_root: str) -> bool:
    """Return True when pre-normalized ``norm_path`` lies within ``norm_root``."""
    try:
        return os.path.commonpath([norm_path, norm_root]) == norm_root
    except ValueError:
        return False


def _path_is_within(path_str: str, root_str: str) -> bool:
    """Return True when ``path_str`` lies inside ``root_str`` on path boundaries."""
    if not path_str or not root_str:
        return False
    norm_path = _normalize_real_path(path_str)
    norm_root = _normalize_real_path(root_str)
    if norm_path is None or norm_root is None:
        return False
    return _norm_path_is_within(norm_path, norm_root)


def _has_site_packages_component(path_str: str) -> bool:
    """Return True when a path contains a site-packages or dist-packages component."""
    try:
        parts = Path(path_str).parts
    except Exception:
        return False
    return any(part.lower() in ("site-packages", "dist-packages") for part in parts)


def _get_site_packages_roots() -> Tuple[str, ...]:
    """Return deduplicated normalized site-packages and library root paths."""
    roots: List[str] = []
    seen: Set[str] = set()

    def _add(candidate: Any) -> None:
        if isinstance(candidate, str) and candidate:
            norm = _normalize_real_path(candidate)
            if norm and norm not in seen:
                seen.add(norm)
                roots.append(norm)

    try:
        for path_entry in site.getsitepackages():
            _add(path_entry)
    except Exception:
        pass

    try:
        _add(site.getusersitepackages())
    except Exception:
        pass

    try:
        paths = sysconfig.get_paths()
        _add(paths.get("purelib"))
        _add(paths.get("platlib"))
    except Exception:
        pass

    return tuple(roots)


def _get_stdlib_path_context() -> Tuple[Tuple[str, ...], Tuple[str, ...]]:
    """Return pre-normalized ``(stdlib_roots, lib_roots)`` from ``sysconfig``."""
    stdlib_roots: List[str] = []
    lib_roots: List[str] = []
    try:
        paths = sysconfig.get_paths()
    except Exception:
        paths = {}

    for key in ("stdlib", "platstdlib"):
        raw = paths.get(key)
        if isinstance(raw, str) and raw:
            norm = _normalize_real_path(raw)
            if norm and norm not in stdlib_roots:
                stdlib_roots.append(norm)

    for key in ("purelib", "platlib"):
        raw = paths.get(key)
        if isinstance(raw, str) and raw:
            norm = _normalize_real_path(raw)
            if norm and norm not in lib_roots:
                lib_roots.append(norm)

    return tuple(stdlib_roots), tuple(lib_roots)


def _is_site_packages_path(
    path_str: Optional[str],
    site_roots: Optional[Tuple[str, ...]] = None,
) -> bool:
    """Return True if ``path_str`` points inside site-packages or dist-packages."""
    if not isinstance(path_str, str) or not path_str:
        return False
    if _has_site_packages_component(path_str):
        return True
    norm_path = _normalize_real_path(path_str)
    if norm_path is None:
        return False
    roots = _get_site_packages_roots() if site_roots is None else site_roots
    return any(_norm_path_is_within(norm_path, root) for root in roots)


def _is_stdlib_module(
    top_level: str,
    module_obj: Any,
    *,
    stdlib_context: Optional[Tuple[Tuple[str, ...], Tuple[str, ...]]] = None,
) -> bool:
    """Return True if ``top_level`` or ``module_obj`` belongs to Python's standard library."""
    if top_level in sys.builtin_module_names:
        return True

    stdlib_names = getattr(sys, "stdlib_module_names", None)
    if stdlib_names is not None and top_level in stdlib_names:
        return True

    spec = _safe_getattr(module_obj, "__spec__", None)
    origin = _safe_getattr(spec, "origin", None)
    if origin in ("built-in", "frozen"):
        return True

    mod_file = _safe_getattr(module_obj, "__file__", None)
    if (
        not isinstance(mod_file, str)
        and isinstance(origin, str)
        and origin not in ("", "namespace", "built-in", "frozen")
    ):
        mod_file = origin

    if isinstance(mod_file, str) and mod_file:
        if _has_site_packages_component(mod_file):
            return False
        norm_file = _normalize_real_path(mod_file)
        if norm_file is None:
            return False
        stdlib_roots, lib_roots = (
            _get_stdlib_path_context() if stdlib_context is None else stdlib_context
        )
        if any(_norm_path_is_within(norm_file, root) for root in lib_roots):
            return False
        if any(_norm_path_is_within(norm_file, root) for root in stdlib_roots):
            return True

    return False


def _snapshot_sys_modules() -> List[Tuple[str, Any]]:
    """Copy ``sys.modules`` safely even when other threads import concurrently."""
    for _ in range(3):
        try:
            return list(sys.modules.copy().items())
        except RuntimeError:
            continue

    for _ in range(3):
        try:
            return list(sys.modules.items())
        except RuntimeError:
            continue

    keys: List[str] = []
    for _ in range(5):
        try:
            keys = list(sys.modules.keys())
            break
        except RuntimeError:
            continue
    return [(key, sys.modules.get(key)) for key in keys]


def _environment_fingerprint() -> Tuple[Any, ...]:
    """Compute a lightweight fingerprint of the active Python import environment."""
    sys_path_tuple = tuple(sys.path)
    meta_path_types = tuple(type(finder) for finder in sys.meta_path)

    dir_mtimes: List[Tuple[str, Optional[int]]] = []
    for entry in sys_path_tuple:
        path_to_stat = entry if entry else "."
        try:
            st = os.stat(path_to_stat)
            if stat.S_ISDIR(st.st_mode):
                dir_mtimes.append((entry, st.st_mtime_ns))
        except OSError:
            dir_mtimes.append((entry, None))

    return (
        sys_path_tuple,
        meta_path_types,
        tuple(dir_mtimes),
        id(importlib.metadata.distributions),
    )


def _read_metadata_name(meta: Any) -> Optional[str]:
    """Read the distribution ``Name`` field from a metadata mapping or message."""
    if meta is None:
        return None
    if hasattr(meta, "get"):
        value = meta.get("Name")
        if value is None and isinstance(meta, dict):
            for key, val in meta.items():
                if isinstance(key, str) and key.lower() == "name":
                    value = val
                    break
        return value if isinstance(value, str) else None
    try:
        value = meta["Name"]
        return value if isinstance(value, str) else None
    except KeyError:
        return None


def _get_dist_location(dist: Any) -> Optional[str]:
    """Return the distribution's base installation path, or None if unavailable."""
    locate_file = getattr(dist, "locate_file", None)
    if not callable(locate_file):
        return None
    try:
        loc = locate_file("")
        return str(loc) if loc is not None else None
    except Exception:
        return None


def _is_editable_dist(dist: Any) -> bool:
    """Detect PEP 610 editable status from ``direct_url.json`` without exposing URLs."""
    read_text = getattr(dist, "read_text", None)
    if not callable(read_text):
        return False
    try:
        raw = read_text("direct_url.json")
    except Exception:
        return False
    if not raw or not isinstance(raw, str):
        return False

    try:
        data = json.loads(raw)
    except (ValueError, TypeError):
        return "dir_info" in raw

    if not isinstance(data, dict):
        return False
    dir_info = data.get("dir_info")
    return isinstance(dir_info, dict) and dir_info.get("editable") is True


def _extract_top_levels(dist: Any) -> Tuple[str, ...]:
    """Infer top-level import names identically on Python 3.8 through 3.14.

    Mirrors CPython's ``packages_distributions()`` algorithm inside the single
    pass over ``importlib.metadata.distributions()``. Reads ``RECORD`` directly
    when available to avoid per-file ``stat()`` calls on large environments.
    """
    read_text = getattr(dist, "read_text", None)
    if callable(read_text):
        try:
            raw_top = read_text("top_level.txt")
        except Exception:
            raw_top = None
        if raw_top and isinstance(raw_top, str):
            declared = raw_top.split()
            if declared:
                return tuple(dict.fromkeys(declared))

    inferred: List[str] = []
    seen: Set[str] = set()

    def _collect_from_parts(parts: Tuple[str, ...], path_str: str) -> None:
        if parts and len(parts) > 1:
            candidate = parts[0]
        else:
            candidate = inspect.getmodulename(path_str) or path_str
        if candidate and "." not in candidate and candidate != "__pycache__":
            if candidate not in seen:
                seen.add(candidate)
                inferred.append(candidate)

    parsed_record = False
    if callable(read_text):
        try:
            raw_record = read_text("RECORD")
        except Exception:
            raw_record = None
        if raw_record and isinstance(raw_record, str):
            parsed_record = True
            for row in csv.reader(raw_record.splitlines()):
                if not row:
                    continue
                entry = row[0]
                if not entry:
                    continue
                _collect_from_parts(PurePosixPath(entry).parts, entry)

    if not parsed_record:
        try:
            files = getattr(dist, "files", None) or ()
        except Exception:
            files = ()

        for pkg_path in files:
            parts = getattr(pkg_path, "parts", None)
            _collect_from_parts(parts or (), str(pkg_path))

    return tuple(inferred)


def _dist_hint(dist: Any, real_path: Optional[str]) -> str:
    """Return a concise non-empty identifier for a distribution lacking metadata."""
    if real_path:
        base = os.path.basename(real_path)
        if base:
            return base
    raw_path = _safe_getattr(dist, "_path", None)
    if raw_path is not None:
        base = os.path.basename(str(raw_path))
        if base:
            return base
    return "<unknown>"


def _hint_to_normalized_dist_name(hint: str) -> Optional[str]:
    """Derive a normalized distribution name prefix from a ``.dist-info``/``.egg-info`` hint."""
    if not hint or hint == "<unknown>":
        return None
    stem = hint
    for suffix in (".dist-info", ".egg-info"):
        if stem.lower().endswith(suffix):
            stem = stem[: -len(suffix)]
            break
    if "-" in stem:
        stem = stem.split("-", 1)[0]
    stem = stem.strip()
    return normalize_package_name(stem) if stem else None


def _build_distribution_index(fingerprint: Tuple[Any, ...]) -> _DistributionIndex:
    """Scan ``importlib.metadata.distributions()`` once and build lookup tables."""
    by_normalized_name: Dict[str, _DistInfo] = {}
    module_to_dists: Dict[str, List[_DistInfo]] = {}
    metadata_errors: List[Dict[str, Any]] = []
    error_by_module: Dict[str, List[Dict[str, Any]]] = {}
    error_by_dist_name: Dict[str, List[Dict[str, Any]]] = {}

    seen_real_paths: Set[str] = set()
    seen_fallback_keys: Set[Tuple[str, Optional[str], Optional[str]]] = set()

    def _record_error(dist_obj: Any, hint: str, err_entry: Dict[str, Any]) -> None:
        metadata_errors.append(err_entry)
        norm_hint = _hint_to_normalized_dist_name(hint)
        if norm_hint:
            error_by_dist_name.setdefault(norm_hint, []).append(err_entry)
        try:
            for top in _extract_top_levels(dist_obj):
                error_by_module.setdefault(top, []).append(err_entry)
        except Exception:
            pass

    for dist in importlib.metadata.distributions():
        raw_path = _safe_getattr(dist, "_path", None)
        dist_real_path: Optional[str] = None
        if raw_path is not None:
            try:
                dist_real_path = os.path.normcase(os.path.realpath(str(raw_path)))
            except OSError:
                dist_real_path = None
            if dist_real_path is not None and dist_real_path in seen_real_paths:
                continue

        try:
            meta = dist.metadata
            raw_name = _read_metadata_name(meta)
            if not raw_name or not raw_name.strip():
                hint = _dist_hint(dist, dist_real_path)
                err_entry = {
                    "module": hint,
                    "reason": "missing_metadata",
                    "candidates": [],
                    "detail": "Distribution metadata is missing a valid Name field",
                }
                if dist_real_path is not None:
                    seen_real_paths.add(dist_real_path)
                _record_error(dist, hint, err_entry)
                continue

            name = raw_name.strip()
            norm_name = normalize_package_name(name)

            raw_version = getattr(dist, "version", None)
            if raw_version is None:
                version: Optional[str] = None
            elif isinstance(raw_version, str):
                version = raw_version
            else:
                version = str(raw_version)

            location = _get_dist_location(dist)

            if dist_real_path is not None:
                seen_real_paths.add(dist_real_path)
            else:
                fallback_key = (norm_name, version, location)
                if fallback_key in seen_fallback_keys:
                    continue
                seen_fallback_keys.add(fallback_key)

            editable = _is_editable_dist(dist)

            raw_requires = getattr(dist, "requires", None)
            if raw_requires:
                requires = tuple(r for r in raw_requires if isinstance(r, str))
            else:
                requires = ()

            top_levels = _extract_top_levels(dist)

            info = _DistInfo(
                name=name,
                normalized_name=norm_name,
                version=version,
                location=location,
                editable=editable,
                requires=requires,
                top_levels=top_levels,
                dist=dist,
                metadata_error=None,
            )

            by_normalized_name.setdefault(norm_name, info)
            for top in top_levels:
                bucket = module_to_dists.setdefault(top, [])
                if info not in bucket:
                    bucket.append(info)
        except Exception as exc:
            hint = _dist_hint(dist, dist_real_path)
            detail = f"{type(exc).__name__}: {exc}" if str(exc) else type(exc).__name__
            err_entry = {
                "module": hint,
                "reason": "metadata_error",
                "candidates": [],
                "detail": detail,
            }
            if dist_real_path is not None:
                seen_real_paths.add(dist_real_path)
            _record_error(dist, hint, err_entry)

    return _DistributionIndex(
        fingerprint=fingerprint,
        by_normalized_name=by_normalized_name,
        module_to_dists=module_to_dists,
        metadata_errors=tuple(metadata_errors),
        error_by_module=error_by_module,
        error_by_dist_name=error_by_dist_name,
    )


def invalidate_package_cache() -> None:
    """Clear the cached distribution index so the next lookup rescans the environment."""
    global _CACHED_FINGERPRINT, _CACHED_INDEX, _CACHED_PROVIDER
    with _CACHE_LOCK:
        _CACHED_FINGERPRINT = None
        _CACHED_INDEX = None
        _CACHED_PROVIDER = None


def _get_distribution_index(use_cache: bool = True) -> _DistributionIndex:
    """Return the distribution index for the current environment fingerprint."""
    global _CACHED_FINGERPRINT, _CACHED_INDEX, _CACHED_PROVIDER
    fingerprint = _environment_fingerprint()
    if not use_cache:
        return _build_distribution_index(fingerprint)

    provider = importlib.metadata.distributions
    with _CACHE_LOCK:
        if (
            _CACHED_INDEX is not None
            and _CACHED_FINGERPRINT == fingerprint
            and _CACHED_PROVIDER is provider
        ):
            return _CACHED_INDEX

        index = _build_distribution_index(fingerprint)
        _CACHED_FINGERPRINT = fingerprint
        _CACHED_INDEX = index
        _CACHED_PROVIDER = provider
        return index


def get_installed_distribution_versions(use_cache: bool = True) -> Dict[str, Dict[str, Any]]:
    """Return installed distributions keyed by PEP 503 normalized name.

    Uses the cached distribution index and never imports target modules.
    """
    index = _get_distribution_index(use_cache=use_cache)
    return {
        norm_name: {
            "name": info.name,
            "version": info.version,
            "editable": info.editable,
            "location": info.location,
        }
        for norm_name, info in index.by_normalized_name.items()
    }


def _get_candidate_resolved_files(
    index: _DistributionIndex,
    info: _DistInfo,
) -> FrozenSet[str]:
    """Lazily resolve and normalize ``dist.files`` paths for a candidate distribution."""
    key = id(info)
    with index._files_lock:
        cached = index._resolved_files_cache.get(key)
        if cached is not None:
            return cached

    resolved: Set[str] = set()
    try:
        files = getattr(info.dist, "files", None)
    except Exception:
        files = None

    locate_file = getattr(info.dist, "locate_file", None)
    if files and callable(locate_file):
        for pkg_path in files:
            try:
                located = locate_file(pkg_path)
                if located is not None:
                    resolved.add(os.path.normcase(os.path.realpath(str(located))))
            except Exception:
                continue

    result = frozenset(resolved)
    with index._files_lock:
        index._resolved_files_cache[key] = result
    return result


def _extract_concrete_module_file(module_obj: Any) -> Optional[str]:
    """Return a loaded module's concrete file path, ignoring namespace/built-in origins."""
    mod_file = _safe_getattr(module_obj, "__file__", None)
    if isinstance(mod_file, str) and mod_file:
        return mod_file
    spec = _safe_getattr(module_obj, "__spec__", None)
    origin = _safe_getattr(spec, "origin", None)
    if isinstance(origin, str) and origin not in ("", "namespace", "built-in", "frozen"):
        return origin
    return None


def _collapse_matched_import_names(names: Set[str]) -> List[str]:
    """Collapse deeper submodule names when a parent module already matched."""
    ordered = sorted(names)
    collapsed: List[str] = []
    for name in ordered:
        if any(name.startswith(parent + ".") for parent in collapsed):
            continue
        collapsed.append(name)
    return collapsed


def _disambiguate_candidates(
    top: str,
    loaded_entries: List[Tuple[str, Any]],
    candidates: List[_DistInfo],
    index: _DistributionIndex,
) -> Tuple[Dict[str, Tuple[_DistInfo, Set[str]]], List[Dict[str, Any]]]:
    """Disambiguate multiple distributions claiming ``top`` via concrete module origins."""
    concrete_loaded: List[Tuple[str, str]] = []
    for mod_name, mod_obj in loaded_entries:
        raw_file = _extract_concrete_module_file(mod_obj)
        if raw_file:
            try:
                norm_file = os.path.normcase(os.path.realpath(raw_file))
            except OSError:
                continue
            concrete_loaded.append((mod_name, norm_file))

    if not concrete_loaded:
        cand_names = sorted({c.name for c in candidates})
        return (
            {},
            [
                {
                    "module": top,
                    "reason": "ambiguous",
                    "candidates": cand_names,
                    "detail": (
                        f"Module '{top}' matches multiple distributions without "
                        f"a distinguishing loaded file: {', '.join(cand_names)}"
                    ),
                }
            ],
        )

    candidate_files: Dict[int, FrozenSet[str]] = {
        id(cand): _get_candidate_resolved_files(index, cand) for cand in candidates
    }

    matched: Dict[str, Tuple[_DistInfo, Set[str]]] = {}
    unresolved: List[Dict[str, Any]] = []
    ambiguous_seen: Set[str] = set()

    for mod_name, norm_file in concrete_loaded:
        hits = [cand for cand in candidates if norm_file in candidate_files[id(cand)]]
        if not hits:
            # Only use location containment if it uniquely distinguishes candidates
            # in different directories (shared site-packages will match all of them
            # and remain ambiguous).
            loc_hits = [
                cand
                for cand in candidates
                if cand.location and _path_is_within(norm_file, cand.location)
            ]
            if len(loc_hits) == 1:
                hits = loc_hits
            elif len(loc_hits) > 1:
                hits = loc_hits

        if len(hits) == 1:
            winner = hits[0]
            if winner.normalized_name not in matched:
                matched[winner.normalized_name] = (winner, set())
            matched[winner.normalized_name][1].add(mod_name)
        else:
            tied = hits if len(hits) > 1 else candidates
            if mod_name not in ambiguous_seen:
                ambiguous_seen.add(mod_name)
                cand_names = sorted({c.name for c in tied})
                unresolved.append(
                    {
                        "module": mod_name,
                        "reason": "ambiguous",
                        "candidates": cand_names,
                        "detail": (
                            f"Module '{mod_name}' matches multiple distributions: "
                            f"{', '.join(cand_names)}"
                        ),
                    }
                )

    return matched, unresolved


def _fallback_direct_metadata_lookup(
    top: str,
) -> Tuple[Optional[Dict[str, Any]], Optional[Dict[str, Any]]]:
    """Try direct ``importlib.metadata.distribution`` / ``version`` lookup for ``top``.

    Supports PEP 660 editable installs without ``top_level.txt`` or package entries
    in ``RECORD``, custom metadata finders, and minimal test mocks. Returns
    ``(record_dict, unresolved_error_dict)``.
    """
    try:
        dist = importlib.metadata.distribution(top)
    except importlib.metadata.PackageNotFoundError:
        try:
            ver = importlib.metadata.version(top)
        except importlib.metadata.PackageNotFoundError:
            return None, None
        except Exception as exc:
            detail = f"{type(exc).__name__}: {exc}" if str(exc) else type(exc).__name__
            return None, {
                "module": top,
                "reason": "metadata_error",
                "candidates": [],
                "detail": detail,
            }
        return (
            {
                "name": top,
                "version": ver if isinstance(ver, str) or ver is None else str(ver),
                "location": None,
                "editable": None,
                "source": "imported",
                "import_names": [top],
            },
            None,
        )
    except Exception as exc:
        detail = f"{type(exc).__name__}: {exc}" if str(exc) else type(exc).__name__
        return None, {
            "module": top,
            "reason": "metadata_error",
            "candidates": [],
            "detail": detail,
        }

    # Distinguish minimal mocks lacking a `.metadata` attribute from real
    # distributions whose `METADATA` file is missing `Name` or unreadable.
    has_metadata_attr = hasattr(type(dist), "metadata") or "metadata" in getattr(
        dist, "__dict__", {}
    )
    if has_metadata_attr:
        try:
            meta = dist.metadata
        except Exception as exc:
            detail = f"{type(exc).__name__}: {exc}" if str(exc) else type(exc).__name__
            return None, {
                "module": top,
                "reason": "metadata_error",
                "candidates": [],
                "detail": detail,
            }
        raw_name = _read_metadata_name(meta)
        if not raw_name or not raw_name.strip():
            return None, {
                "module": top,
                "reason": "missing_metadata",
                "candidates": [],
                "detail": f"Distribution metadata for '{top}' is missing a valid Name field",
            }
        dist_name = raw_name.strip()
    else:
        dist_name = top

    version = _safe_getattr(dist, "version", _MISSING)
    if version is _MISSING:
        try:
            version = importlib.metadata.version(top)
        except importlib.metadata.PackageNotFoundError:
            version = None
        except Exception:
            version = None
    if version is not None and not isinstance(version, str):
        version = str(version)

    location = _get_dist_location(dist)
    read_text = getattr(dist, "read_text", None)
    editable: Optional[bool] = _is_editable_dist(dist) if callable(read_text) else None

    return (
        {
            "name": dist_name,
            "version": version,
            "location": location,
            "editable": editable,
            "source": "imported",
            "import_names": [top],
        },
        None,
    )


def _is_extra_gated_requirement(req_str: str) -> bool:
    """Return True when a PEP 508 requirement string is gated on an ``extra`` marker."""
    if ";" not in req_str:
        return False
    _, marker_part = req_str.split(";", 1)
    return bool(_EXTRA_MARKER_RE.search(marker_part))


def _record_from_dist_info(
    info: _DistInfo,
    *,
    source: Optional[str] = None,
    import_names: Optional[List[str]] = None,
    required_by: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Build a canonical package record dict from a cached ``_DistInfo``."""
    rec: Dict[str, Any] = {
        "name": info.name,
        "version": info.version,
        "location": info.location,
        "editable": info.editable,
    }
    if source is not None:
        rec["source"] = source
    if import_names is not None:
        rec["import_names"] = import_names
    if required_by is not None:
        rec["required_by"] = required_by
    return rec


def _merge_imported_record(
    resolved_by_key: Dict[str, Dict[str, Any]],
    record: Dict[str, Any],
    import_names: List[str],
) -> None:
    """Insert or merge an imported distribution record by normalized name."""
    norm_key = normalize_package_name(record["name"])
    existing = resolved_by_key.get(norm_key)
    if existing is None:
        rec_copy = dict(record)
        rec_copy["import_names"] = sorted(set(import_names))
        resolved_by_key[norm_key] = rec_copy
    else:
        combined = set(existing.get("import_names") or ())
        combined.update(import_names)
        existing["import_names"] = sorted(combined)


def _format_unresolved_warning(entry: Dict[str, Any]) -> str:
    """Build a concise human-readable warning string for an unresolved entry."""
    mod = entry.get("module") or "<unknown>"
    reason = entry.get("reason") or "unresolved"
    detail = entry.get("detail")
    if detail:
        return f"{mod} ({reason}): {detail}"
    candidates = entry.get("candidates") or []
    if candidates:
        return f"{mod} ({reason}): candidates={', '.join(candidates)}"
    return f"{mod} ({reason})"


def _should_run_direct_fallback() -> bool:
    """Return True only when a monkeypatched provider or custom finder may know extra dists."""
    if (
        importlib.metadata.distribution is not _ORIG_DISTRIBUTION
        or importlib.metadata.version is not _ORIG_VERSION
    ):
        return True
    for finder in sys.meta_path:
        if finder is importlib.machinery.PathFinder:
            continue
        if hasattr(finder, "find_distributions"):
            return True
    return False


def _resolve_imported_modules(
    index: _DistributionIndex,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[str]]:
    """Resolve currently loaded ``sys.modules`` entries against ``index``."""
    snapshot = _snapshot_sys_modules()
    site_roots = _get_site_packages_roots()
    stdlib_context = _get_stdlib_path_context()
    allow_direct_fallback = _should_run_direct_fallback()

    grouped: Dict[str, List[Tuple[str, Any]]] = {}
    top_objects: Dict[str, Any] = {}

    for mod_name, mod_obj in snapshot:
        if mod_obj is None or not isinstance(mod_name, str) or not mod_name:
            continue
        top = mod_name.split(".", 1)[0]
        if not top or top == "__main__" or top == "_ast" or top.startswith("__"):
            continue
        grouped.setdefault(top, []).append((mod_name, mod_obj))
        if mod_name == top:
            top_objects[top] = mod_obj

    resolved_by_key: Dict[str, Dict[str, Any]] = {}
    unresolved: List[Dict[str, Any]] = []
    local_modules: Set[str] = set()

    for top in sorted(grouped.keys()):
        entries = grouped[top]
        primary_obj = top_objects.get(top, entries[0][1])

        if _is_stdlib_module(top, primary_obj, stdlib_context=stdlib_context):
            continue

        candidates = index.module_to_dists.get(top, [])

        if len(candidates) == 1:
            info = candidates[0]
            _merge_imported_record(
                resolved_by_key,
                _record_from_dist_info(info, source="imported"),
                [top],
            )
            continue

        if len(candidates) > 1:
            matched, ambig_entries = _disambiguate_candidates(
                top, entries, candidates, index
            )
            for _norm, (info, mod_names) in matched.items():
                collapsed = _collapse_matched_import_names(mod_names)
                _merge_imported_record(
                    resolved_by_key,
                    _record_from_dist_info(info, source="imported"),
                    collapsed,
                )
            unresolved.extend(ambig_entries)
            continue

        # 0 candidates in module_to_dists: first check O(1) index tables.
        norm_top = normalize_package_name(top)
        indexed_errors = index.error_by_module.get(top) or index.error_by_dist_name.get(
            norm_top
        )
        if indexed_errors:
            for err in indexed_errors:
                unresolved.append(
                    {
                        "module": top,
                        "reason": err["reason"],
                        "candidates": list(err.get("candidates") or ()),
                        "detail": err.get("detail") or "Distribution metadata error",
                    }
                )
            continue

        loaded_files = [
            f
            for _, mod_obj in entries
            for f in (_extract_concrete_module_file(mod_obj),)
            if f
        ]
        in_site_packages = any(
            _is_site_packages_path(f, site_roots=site_roots) for f in loaded_files
        )

        # Match indexed distributions that omit package files in RECORD/top_level.txt
        # (such as PEP 660 editable .pth installs or setuptools __editable__ finder
        # shims) in O(1).
        direct_info = index.by_normalized_name.get(norm_top)
        has_only_editable_shims = direct_info is not None and (
            direct_info.editable is True
            and all(t.startswith("__editable__") for t in direct_info.top_levels)
        )
        if direct_info is not None and (
            not direct_info.top_levels or in_site_packages or has_only_editable_shims
        ):
            _merge_imported_record(
                resolved_by_key,
                _record_from_dist_info(direct_info, source="imported"),
                [top],
            )
            continue

        # Only invoke direct importlib.metadata.distribution()/version() when a
        # custom finder or monkeypatched provider can resolve unindexed names.
        if allow_direct_fallback:
            fallback_rec, fallback_err = _fallback_direct_metadata_lookup(top)
            if fallback_err is not None:
                unresolved.append(fallback_err)
                continue
            if fallback_rec is not None:
                _merge_imported_record(
                    resolved_by_key,
                    fallback_rec,
                    fallback_rec.get("import_names") or [top],
                )
                continue

        # Classify unmapped module as unmapped site-package vs local-only module.
        if in_site_packages:
            unresolved.append(
                {
                    "module": top,
                    "reason": "unmapped_site_package",
                    "candidates": [],
                    "detail": (
                        f"Module '{top}' loaded from site-packages has no matching "
                        f"distribution metadata"
                    ),
                }
            )
        else:
            local_modules.add(top)

    records = list(resolved_by_key.values())
    return records, unresolved, sorted(local_modules)


def _read_dist_requires(
    parent_key: str,
    parent_name: str,
    index: _DistributionIndex,
) -> Tuple[str, ...]:
    """Read declared ``Requires-Dist`` strings from ``index`` or direct metadata fallback."""
    info = index.by_normalized_name.get(parent_key)
    if info is not None:
        return info.requires
    try:
        dist = importlib.metadata.distribution(parent_name)
        raw_reqs = getattr(dist, "requires", None)
        if raw_reqs:
            return tuple(r for r in raw_reqs if isinstance(r, str))
    except Exception:
        pass
    return ()


def _resolve_transitive_target(
    dep_name: str,
    dep_norm: str,
    index: _DistributionIndex,
) -> Optional[Tuple[str, str, Dict[str, Any]]]:
    """Resolve a transitive target distribution from ``index`` or direct metadata fallback.

    Returns ``(normalized_name, canonical_name, record_dict)`` or ``None`` when
    the target distribution is not installed.
    """
    dep_info = index.by_normalized_name.get(dep_norm)
    if dep_info is not None:
        return (
            dep_info.normalized_name,
            dep_info.name,
            _record_from_dist_info(dep_info, source="transitive", required_by=[]),
        )

    try:
        dist = importlib.metadata.distribution(dep_name)
    except importlib.metadata.PackageNotFoundError:
        try:
            dep_version = importlib.metadata.version(dep_name)
        except Exception:
            return None
        version_str = (
            dep_version
            if dep_version is None or isinstance(dep_version, str)
            else str(dep_version)
        )
        return (
            dep_norm,
            dep_name,
            {
                "name": dep_name,
                "version": version_str,
                "location": None,
                "editable": None,
                "source": "transitive",
                "required_by": [],
            },
        )
    except Exception:
        return None

    target_name = dep_name
    has_metadata_attr = hasattr(type(dist), "metadata") or "metadata" in getattr(
        dist, "__dict__", {}
    )
    if has_metadata_attr:
        try:
            raw_name = _read_metadata_name(dist.metadata)
            if raw_name and raw_name.strip():
                target_name = raw_name.strip()
        except Exception:
            pass

    version = _safe_getattr(dist, "version", _MISSING)
    if version is _MISSING:
        try:
            version = importlib.metadata.version(dep_name)
        except Exception:
            version = None
    if version is not None and not isinstance(version, str):
        version = str(version)

    location = _get_dist_location(dist)
    read_text = getattr(dist, "read_text", None)
    editable: Optional[bool] = _is_editable_dist(dist) if callable(read_text) else None
    target_key = normalize_package_name(target_name)

    return (
        target_key,
        target_name,
        {
            "name": target_name,
            "version": version,
            "location": location,
            "editable": editable,
            "source": "transitive",
            "required_by": [],
        },
    )


def _resolve_transitive_closure(
    imported_records: List[Dict[str, Any]],
    index: _DistributionIndex,
    *,
    env: Optional[Dict[str, str]] = None,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Compute a recursive, cycle-safe, PEP 508 marker-aware transitive closure.

    Expands each ``(normalized_name, active_extra)`` state at most once, starting
    from each resolved imported distribution with ``active_extra=""``. Skips
    requirements whose environment markers evaluate to ``False`` (including
    unrequested optional extras), propagates parent-requested extras (such as
    ``dep[fast]``), and records missing applicable dependencies or unparseable
    markers as structured ``unresolved`` entries.
    """
    marker_env = default_marker_environment() if env is None else env

    imported_keys: Set[str] = set()
    queue: deque = deque()
    queued_states: Set[Tuple[str, str]] = set()
    expanded_states: Set[Tuple[str, str]] = set()
    transitive_by_key: Dict[str, Dict[str, Any]] = {}
    required_by: Dict[str, Set[str]] = {}
    unresolved: List[Dict[str, Any]] = []
    unresolved_seen: Set[Tuple[str, str, str]] = set()

    def _enqueue(norm_key: str, canonical_name: str, extra: str) -> None:
        state = (norm_key, extra)
        if state not in expanded_states and state not in queued_states:
            queued_states.add(state)
            queue.append((norm_key, canonical_name, extra))

    def _record_unresolved(module: str, reason: str, detail: Optional[str]) -> None:
        dedup_key = (module, reason, detail or "")
        if dedup_key not in unresolved_seen:
            unresolved_seen.add(dedup_key)
            unresolved.append(
                {
                    "module": module,
                    "reason": reason,
                    "candidates": [],
                    "detail": detail,
                }
            )

    for rec in imported_records:
        name = rec.get("name")
        if not isinstance(name, str) or not name:
            continue
        norm_key = normalize_package_name(name)
        imported_keys.add(norm_key)
        _enqueue(norm_key, name, "")

    while queue:
        parent_key, parent_name, active_extra = queue.popleft()
        state = (parent_key, active_extra)
        if state in expanded_states:
            continue
        expanded_states.add(state)

        requires = _read_dist_requires(parent_key, parent_name, index)
        for req_str in requires:
            if not isinstance(req_str, str) or not req_str.strip():
                continue

            parsed = parse_requirement(req_str)
            if parsed is None:
                _record_unresolved(
                    req_str.strip()[:80],
                    "unparseable_marker",
                    "unparseable requirement string",
                )
                continue

            if parsed.marker is not None:
                eval_res = evaluate_marker(
                    parsed.marker,
                    active_extra=active_extra,
                    env=marker_env,
                )
                if eval_res.matched is False:
                    continue
                if eval_res.matched is None:
                    _record_unresolved(
                        parsed.name,
                        "unparseable_marker",
                        eval_res.error or "unparseable environment marker",
                    )
                    continue

            resolved = _resolve_transitive_target(
                parsed.name,
                parsed.normalized_name,
                index,
            )
            if resolved is None:
                _record_unresolved(
                    parsed.name,
                    "missing_transitive_dependency",
                    f"required by {parent_name}",
                )
                continue

            target_key, target_name, target_rec = resolved
            if target_key != parent_key:
                required_by.setdefault(target_key, set()).add(parent_name)

            if target_key not in imported_keys and target_key not in transitive_by_key:
                transitive_by_key[target_key] = target_rec

            # Always traverse base requirements alongside any requested extras.
            _enqueue(target_key, target_name, "")
            for extra in parsed.extras:
                _enqueue(target_key, target_name, extra)

    for key, rec in transitive_by_key.items():
        rec["required_by"] = sorted(required_by.get(key, set()))

    transitive_records = sorted(
        transitive_by_key.values(),
        key=lambda item: (item.get("name") or "").lower(),
    )
    return transitive_records, unresolved


def resolve_packages_snapshot(config: Dict[str, Any]) -> Dict[str, Any]:
    """Resolve packages according to ``config`` and return the full structured snapshot.

    The returned dict includes ``records`` (with per-record ``import_names`` for
    imported distributions), ``unresolved``, ``local_modules``, and ``capture_state``.
    """
    cfg = (config.get("capture") or {}).get("packages") or {}
    mode = cfg.get("mode", "imported-only")

    if mode == "off":
        return {"capture_state": {"status": "suppressed"}}

    records: List[Dict[str, Any]] = []
    unresolved: List[Dict[str, Any]] = []
    local_modules: List[str] = []
    warnings: List[str] = []
    status = "complete"
    detail: Optional[str] = None

    try:
        index = _get_distribution_index(use_cache=True)

        if mode in ("imported-only", "imported-transitive"):
            records, unresolved, local_modules = _resolve_imported_modules(index)
            if mode == "imported-transitive":
                transitive_records, transitive_unresolved = _resolve_transitive_closure(
                    records, index
                )
                records = records + transitive_records
                unresolved.extend(transitive_unresolved)
        elif mode == "top-level-installed":
            required_by_others: Set[str] = set()
            for info in index.by_normalized_name.values():
                for req_str in info.requires:
                    if _is_extra_gated_requirement(req_str):
                        continue
                    dep_name = _parse_req_name(req_str)
                    if not dep_name:
                        continue
                    dep_norm = normalize_package_name(dep_name)
                    if dep_norm != info.normalized_name:
                        required_by_others.add(dep_norm)

            for norm_name, info in index.by_normalized_name.items():
                if norm_name not in required_by_others:
                    records.append(_record_from_dist_info(info))
            unresolved.extend(dict(err) for err in index.metadata_errors)
        else:
            # full-environment (or unrecognized mode treated as full-environment)
            for info in index.by_normalized_name.values():
                records.append(_record_from_dist_info(info))
            unresolved.extend(dict(err) for err in index.metadata_errors)

        if unresolved:
            status = "partial"
            unresolved.sort(
                key=lambda item: (
                    (item.get("module") or "").lower(),
                    (item.get("reason") or "").lower(),
                )
            )
            seen_warnings: Set[str] = set()
            for entry in unresolved:
                msg = _format_unresolved_warning(entry)
                if msg not in seen_warnings:
                    seen_warnings.add(msg)
                    warnings.append(msg)
    except Exception as exc:
        status = "partial"
        detail = f"{type(exc).__name__}: {exc}" if str(exc) else type(exc).__name__
        warnings.append(f"Package capture error: {detail}")

    capture_state: Dict[str, Any] = {"status": status}
    if detail:
        capture_state["detail"] = detail
    if warnings:
        capture_state["warnings"] = warnings

    # Null-guard the sort key as defense in depth (IPD 20260705 EC-08).
    sorted_records = sorted(records, key=lambda x: (x.get("name") or "").lower())

    return {
        "mode": mode,
        "records": sorted_records,
        "unresolved": unresolved,
        "local_modules": local_modules,
        "capture_state": capture_state,
    }


def get_packages(config: Dict[str, Any]) -> Dict[str, Any]:
    """Capture installed Python packages via ``importlib.metadata``.

    Modes:
    - ``imported-only``: Only packages already loaded in ``sys.modules`` (default).
    - ``imported-transitive``: Imported packages plus their declared dependencies.
    - ``top-level-installed``: Installed distributions not required by other distributions.
    - ``full-environment``: Every distribution in the environment.

    Emits only keys and non-null types accepted by the current
    ``schemas/manifest.schema.json`` until child plan ``ijipnx`` extends the schema.

    Args:
        config: Resolved pubrun configuration.
    """
    snapshot = resolve_packages_snapshot(config)
    if snapshot.get("capture_state", {}).get("status") == "suppressed":
        return snapshot

    schema_records: List[Dict[str, Any]] = []
    for rec in snapshot.get("records") or []:
        name = rec.get("name")
        if not isinstance(name, str) or not name:
            continue
        cleaned: Dict[str, Any] = {}
        for key in _SCHEMA_PACKAGE_RECORD_KEYS:
            if key in rec:
                cleaned[key] = rec[key]
        if "version" not in cleaned:
            cleaned["version"] = None
        schema_records.append(cleaned)

    raw_state = snapshot.get("capture_state") or {"status": "partial"}
    capture_state: Dict[str, Any] = {"status": raw_state.get("status", "partial")}
    raw_detail = raw_state.get("detail")
    if isinstance(raw_detail, str) and raw_detail:
        capture_state["detail"] = raw_detail
    raw_warnings = raw_state.get("warnings")
    if isinstance(raw_warnings, list) and raw_warnings:
        capture_state["warnings"] = [str(w) for w in raw_warnings]

    return {
        "mode": snapshot["mode"],
        "records": sorted(schema_records, key=lambda x: (x.get("name") or "").lower()),
        "capture_state": capture_state,
    }
