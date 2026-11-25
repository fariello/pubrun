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

_VALID_STAGES = frozenset({"startup", "final", "single"})
_VALID_OBSERVED_AT = frozenset({"startup", "final", "startup_and_final"})
_NON_TRANSITIVE_UNRESOLVED_REASONS = frozenset(
    {
        "ambiguous",
        "unmapped_site_package",
        "missing_metadata",
        "metadata_error",
    }
)
_TRANSITIVE_UNRESOLVED_REASONS = frozenset(
    {
        "missing_transitive_dependency",
        "unparseable_marker",
    }
)
_PACKAGE_RECORD_KEYS = (
    "name",
    "version",
    "location",
    "editable",
    "source",
    "required_by",
    "import_names",
    "observed_at",
)
_FINAL_NO_HOOK_COVERAGE_NOTE = (
    "Package capture ran at startup and finalization without a global import hook; "
    "modules imported after startup and removed from sys.modules before finalization "
    "cannot be observed."
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

    # On Windows, site.getsitepackages() includes the bare Python installation
    # prefix alongside lib/site-packages. Treating bare prefix as a site-packages
    # root would misclassify stdlib DLLs/ and Lib/ files as site-packages.
    prefix_roots: Set[str] = set()
    for raw_prefix in (
        sys.prefix,
        getattr(sys, "base_prefix", None),
        sys.exec_prefix,
        getattr(sys, "base_exec_prefix", None),
    ):
        if isinstance(raw_prefix, str) and raw_prefix:
            norm_prefix = _normalize_real_path(raw_prefix)
            if norm_prefix:
                prefix_roots.add(norm_prefix)

    def _add(candidate: Any, *, exclude_prefixes: bool = False) -> None:
        if isinstance(candidate, str) and candidate:
            norm = _normalize_real_path(candidate)
            if norm and norm not in seen:
                if exclude_prefixes and norm in prefix_roots:
                    return
                seen.add(norm)
                roots.append(norm)

    try:
        for path_entry in site.getsitepackages():
            _add(path_entry, exclude_prefixes=True)
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

    # On Windows, stdlib C extensions (*.pyd) live under <prefix>/DLLs, which is
    # outside sysconfig's stdlib/platstdlib (Lib) and matters on Python < 3.10
    # where sys.stdlib_module_names does not exist.
    if os.name == "nt":
        for raw_prefix in (
            getattr(sys, "base_exec_prefix", None),
            sys.exec_prefix,
            getattr(sys, "base_prefix", None),
            sys.prefix,
        ):
            if isinstance(raw_prefix, str) and raw_prefix:
                dlls_dir = os.path.join(raw_prefix, "DLLs")
                norm_dlls = _normalize_real_path(dlls_dir)
                if norm_dlls and norm_dlls not in stdlib_roots:
                    stdlib_roots.append(norm_dlls)

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


def _combine_observed_at(a: Optional[str], b: Optional[str]) -> Optional[str]:
    """Combine two ``observed_at`` stage tags into ``startup``, ``final``, or ``startup_and_final``."""
    vals = {v for v in (a, b) if v in _VALID_OBSERVED_AT}
    if "startup_and_final" in vals or ("startup" in vals and "final" in vals):
        return "startup_and_final"
    if "startup" in vals:
        return "startup"
    if "final" in vals:
        return "final"
    return None


def _copy_package_record(rec: Dict[str, Any]) -> Dict[str, Any]:
    """Return a schema-clean defensive copy of a package record dict."""
    cleaned: Dict[str, Any] = {}
    for key in _PACKAGE_RECORD_KEYS:
        if key not in rec:
            continue
        val = rec[key]
        if isinstance(val, list):
            cleaned[key] = list(val)
        else:
            cleaned[key] = val
    if "version" not in cleaned:
        cleaned["version"] = None
    return cleaned


def _normalize_unresolved_entry(
    entry: Dict[str, Any],
    *,
    default_observed_at: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """Return a schema-valid defensive copy of an ``unresolved`` record."""
    if not isinstance(entry, dict):
        return None
    raw_mod = entry.get("module")
    mod = raw_mod.strip() if isinstance(raw_mod, str) and raw_mod.strip() else "<unknown>"
    raw_reason = entry.get("reason")
    if not isinstance(raw_reason, str) or raw_reason not in (
        _NON_TRANSITIVE_UNRESOLVED_REASONS | _TRANSITIVE_UNRESOLVED_REASONS
    ):
        return None
    raw_cands = entry.get("candidates")
    candidates = sorted(
        {str(c) for c in raw_cands if isinstance(c, str) and c}
        if isinstance(raw_cands, (list, tuple, set))
        else ()
    )
    raw_obs = entry.get("observed_at")
    if raw_obs in _VALID_OBSERVED_AT:
        observed_at: Optional[str] = raw_obs
    else:
        observed_at = default_observed_at if default_observed_at in _VALID_OBSERVED_AT else None
    raw_detail = entry.get("detail")
    detail = raw_detail if isinstance(raw_detail, str) else (
        None if raw_detail is None else str(raw_detail)
    )
    return {
        "module": mod,
        "reason": raw_reason,
        "candidates": candidates,
        "observed_at": observed_at,
        "detail": detail,
    }


def _dedupe_strings(items: List[str]) -> List[str]:
    """Deduplicate non-empty strings while preserving first-seen order."""
    out: List[str] = []
    seen: Set[str] = set()
    for item in items:
        if isinstance(item, str) and item and item not in seen:
            seen.add(item)
            out.append(item)
    return out


def _build_capture_state(
    status: str,
    *,
    detail: Optional[str] = None,
    warnings: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Construct a schema-valid ``capture_state`` dict omitting empty ``detail``."""
    state: Dict[str, Any] = {"status": status}
    if isinstance(detail, str) and detail:
        state["detail"] = detail
    deduped = _dedupe_strings(warnings or [])
    if deduped:
        state["warnings"] = deduped
    return state


def _coverage_notes_for(mode: str, stage: str) -> List[str]:
    """Return factual coverage-boundary notes for ``(mode, stage)``."""
    if stage == "final" and mode in ("imported-only", "imported-transitive"):
        return [_FINAL_NO_HOOK_COVERAGE_NOTE]
    return []


def resolve_packages_snapshot(
    config: Dict[str, Any],
    *,
    stage: str = "single",
    include_transitive: bool = True,
) -> Dict[str, Any]:
    """Resolve packages according to ``config`` and return the full structured snapshot.

    The returned dict conforms to ``schemas/manifest.schema.json`` and includes
    ``mode``, ``snapshot_stage``, ``records`` (with per-record ``import_names`` and
    ``observed_at``), ``unresolved``, ``local_modules``, ``coverage_notes``, and
    ``capture_state``. When ``mode == "off"``, returns
    ``{"capture_state": {"status": "suppressed"}}`` with ``"mode"`` omitted.
    """
    cfg = (config.get("capture") or {}).get("packages") or {}
    mode = cfg.get("mode", "imported-only")

    if mode == "off":
        return {"capture_state": {"status": "suppressed"}}

    eff_stage = stage if stage in _VALID_STAGES else "single"
    obs_stage: Optional[str] = eff_stage if eff_stage in ("startup", "final") else None

    records: List[Dict[str, Any]] = []
    raw_unresolved: List[Dict[str, Any]] = []
    local_modules: List[str] = []
    warnings: List[str] = []
    status = "complete"
    detail: Optional[str] = None

    try:
        index = _get_distribution_index(use_cache=True)

        if mode in ("imported-only", "imported-transitive"):
            imported_records, raw_unresolved, local_modules = _resolve_imported_modules(index)
            for rec in imported_records:
                rec["observed_at"] = obs_stage
                if rec.get("import_names") is None:
                    rec["import_names"] = []
            records = imported_records
            if mode == "imported-transitive" and include_transitive:
                transitive_records, transitive_unresolved = _resolve_transitive_closure(
                    imported_records, index
                )
                for rec in transitive_records:
                    rec["import_names"] = None
                    rec["observed_at"] = None
                records = imported_records + transitive_records
                raw_unresolved.extend(transitive_unresolved)
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
                    rec = _record_from_dist_info(info)
                    rec["import_names"] = None
                    rec["observed_at"] = None
                    records.append(rec)
            raw_unresolved.extend(dict(err) for err in index.metadata_errors)
        else:
            # full-environment (or unrecognized mode treated as full-environment)
            for info in index.by_normalized_name.values():
                rec = _record_from_dist_info(info)
                rec["import_names"] = None
                rec["observed_at"] = None
                records.append(rec)
            raw_unresolved.extend(dict(err) for err in index.metadata_errors)
    except Exception as exc:
        status = "partial"
        detail = f"{type(exc).__name__}: {exc}" if str(exc) else type(exc).__name__
        warnings.append(f"Package capture error: {detail}")

    unresolved: List[Dict[str, Any]] = []
    for entry in raw_unresolved:
        cleaned_entry = _normalize_unresolved_entry(entry, default_observed_at=obs_stage)
        if cleaned_entry is not None:
            unresolved.append(cleaned_entry)

    if unresolved:
        status = "partial"
        unresolved.sort(
            key=lambda item: (
                item["module"].lower(),
                item["reason"].lower(),
                (item.get("detail") or "").lower(),
            )
        )
        for entry in unresolved:
            warnings.append(_format_unresolved_warning(entry))

    cleaned_records: List[Dict[str, Any]] = []
    for rec in records:
        name = rec.get("name")
        if not isinstance(name, str) or not name:
            continue
        cleaned_records.append(_copy_package_record(rec))
    # Null-guard the sort key as defense in depth (IPD 20260705 EC-08).
    sorted_records = sorted(cleaned_records, key=lambda x: (x.get("name") or "").lower())

    return {
        "mode": mode,
        "snapshot_stage": eff_stage,
        "records": sorted_records,
        "unresolved": unresolved,
        "local_modules": sorted({m for m in local_modules if isinstance(m, str) and m}),
        "coverage_notes": _coverage_notes_for(mode, eff_stage),
        "capture_state": _build_capture_state(status, detail=detail, warnings=warnings),
    }


def merge_package_snapshots(
    startup_data: Optional[Dict[str, Any]],
    final_data: Optional[Dict[str, Any]],
    config: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Merge startup and finalization package snapshots without mutating either input.

    Retains startup-only imported distributions (for example, modules deleted from
    ``sys.modules`` before finalization) with ``observed_at = "startup"``, marks
    late imports ``observed_at = "final"``, merges persistent modules as
    ``observed_at = "startup_and_final"`` with unioned ``import_names``, and
    recomputes recursive transitive closure once over the merged imported set when
    effective mode is ``imported-transitive``.
    """
    effective_mode: Optional[str] = None
    if isinstance(config, dict):
        cfg_pkg = (config.get("capture") or {}).get("packages")
        if isinstance(cfg_pkg, dict) and cfg_pkg.get("mode") is not None:
            effective_mode = cfg_pkg.get("mode")
    if effective_mode is None and isinstance(final_data, dict):
        effective_mode = final_data.get("mode")
    if effective_mode is None:
        effective_mode = "imported-only"

    if effective_mode == "off":
        return {"capture_state": {"status": "suppressed"}}

    startup = startup_data if isinstance(startup_data, dict) else {}
    final = final_data if isinstance(final_data, dict) else {}

    _startup_cs_raw = startup.get("capture_state")
    _final_cs_raw = final.get("capture_state")
    startup_cs: Dict[str, Any] = _startup_cs_raw if isinstance(_startup_cs_raw, dict) else {}
    final_cs: Dict[str, Any] = _final_cs_raw if isinstance(_final_cs_raw, dict) else {}
    startup_status = startup_cs.get("status")
    final_status = final_cs.get("status")

    startup_usable = bool(startup) and startup_status != "suppressed"
    startup_warnings = (
        [str(w) for w in (startup_cs.get("warnings") or ()) if isinstance(w, str) and w]
        if startup_usable
        else []
    )
    final_warnings = [
        str(w) for w in (final_cs.get("warnings") or ()) if isinstance(w, str) and w
    ]

    if effective_mode in ("imported-only", "imported-transitive"):
        startup_imported: Dict[str, Dict[str, Any]] = {}
        if startup_usable:
            for rec in startup.get("records") or ():
                if not isinstance(rec, dict) or rec.get("source") != "imported":
                    continue
                name = rec.get("name")
                if not isinstance(name, str) or not name:
                    continue
                norm = normalize_package_name(name)
                startup_imported[norm] = rec

        final_imported: Dict[str, Dict[str, Any]] = {}
        for rec in final.get("records") or ():
            if not isinstance(rec, dict) or rec.get("source") != "imported":
                continue
            name = rec.get("name")
            if not isinstance(name, str) or not name:
                continue
            norm = normalize_package_name(name)
            final_imported[norm] = rec

        merged_imported: List[Dict[str, Any]] = []
        version_warnings: List[str] = []
        version_changed = False

        for norm_key in sorted(set(startup_imported.keys()) | set(final_imported.keys())):
            s_rec = startup_imported.get(norm_key)
            f_rec = final_imported.get(norm_key)
            if s_rec is not None and f_rec is None:
                rec_copy = _copy_package_record(s_rec)
                rec_copy["source"] = "imported"
                rec_copy["observed_at"] = "startup"
                merged_imported.append(rec_copy)
            elif s_rec is None and f_rec is not None:
                rec_copy = _copy_package_record(f_rec)
                rec_copy["source"] = "imported"
                rec_copy["observed_at"] = "final"
                merged_imported.append(rec_copy)
            elif s_rec is not None and f_rec is not None:
                rec_copy = _copy_package_record(f_rec)
                rec_copy["source"] = "imported"
                rec_copy["observed_at"] = "startup_and_final"
                s_names = s_rec.get("import_names")
                f_names = f_rec.get("import_names")
                if s_names is None and f_names is None:
                    rec_copy["import_names"] = None
                else:
                    combined_names: Set[str] = set()
                    for seq in (s_names, f_names):
                        if isinstance(seq, list):
                            combined_names.update(n for n in seq if isinstance(n, str) and n)
                    rec_copy["import_names"] = sorted(combined_names)
                s_ver = s_rec.get("version")
                f_ver = f_rec.get("version")
                if s_ver != f_ver:
                    version_changed = True
                    version_warnings.append(
                        f"Package '{rec_copy['name']}' version changed during run: "
                        f"{s_ver or 'unknown'} -> {f_ver or 'unknown'}"
                    )
                merged_imported.append(rec_copy)

        # Merge non-transitive unresolved entries by (module, reason), discarding
        # prior transitive unresolved entries so fresh closure avoids duplicates.
        non_trans_by_key: Dict[Tuple[str, str], Dict[str, Any]] = {}
        discarded_transitive_warnings: Set[str] = set()

        def _ingest_unresolved(raw_list: Any, default_obs: str) -> None:
            if not isinstance(raw_list, list):
                return
            for raw_entry in raw_list:
                cleaned = _normalize_unresolved_entry(
                    raw_entry, default_observed_at=default_obs
                )
                if cleaned is None:
                    continue
                if cleaned["reason"] in _TRANSITIVE_UNRESOLVED_REASONS:
                    discarded_transitive_warnings.add(_format_unresolved_warning(cleaned))
                    continue
                key = (cleaned["module"], cleaned["reason"])
                existing = non_trans_by_key.get(key)
                if existing is None:
                    non_trans_by_key[key] = cleaned
                else:
                    existing["candidates"] = sorted(
                        set(existing["candidates"]) | set(cleaned["candidates"])
                    )
                    existing["observed_at"] = _combine_observed_at(
                        existing.get("observed_at"), cleaned.get("observed_at")
                    )
                    if cleaned.get("detail"):
                        existing["detail"] = cleaned["detail"]

        if startup_usable:
            _ingest_unresolved(startup.get("unresolved"), "startup")
        _ingest_unresolved(final.get("unresolved"), "final")

        all_records: List[Dict[str, Any]] = list(merged_imported)
        all_unresolved: List[Dict[str, Any]] = list(non_trans_by_key.values())
        transitive_error_detail: Optional[str] = None
        transitive_error_warnings: List[str] = []

        if effective_mode == "imported-transitive":
            try:
                index = _get_distribution_index(use_cache=True)
                trans_records, trans_unresolved = _resolve_transitive_closure(
                    merged_imported, index
                )
                for rec in trans_records:
                    rec_copy = _copy_package_record(rec)
                    rec_copy["import_names"] = None
                    rec_copy["observed_at"] = None
                    all_records.append(rec_copy)
                for entry in trans_unresolved:
                    cleaned = _normalize_unresolved_entry(entry, default_observed_at="final")
                    if cleaned is not None:
                        cleaned["observed_at"] = "final"
                        all_unresolved.append(cleaned)
            except Exception as exc:
                transitive_error_detail = (
                    f"{type(exc).__name__}: {exc}" if str(exc) else type(exc).__name__
                )
                transitive_error_warnings.append(
                    f"Package transitive resolution error: {transitive_error_detail}"
                )

        all_records.sort(key=lambda x: (x.get("name") or "").lower())
        all_unresolved.sort(
            key=lambda item: (
                item["module"].lower(),
                item["reason"].lower(),
                (item.get("detail") or "").lower(),
            )
        )

        local_set: Set[str] = set()
        if startup_usable:
            for mod in startup.get("local_modules") or ():
                if isinstance(mod, str) and mod:
                    local_set.add(mod)
        for mod in final.get("local_modules") or ():
            if isinstance(mod, str) and mod:
                local_set.add(mod)

        combined_warnings: List[str] = []
        for w in startup_warnings + final_warnings:
            if w not in discarded_transitive_warnings:
                combined_warnings.append(w)
        for entry in all_unresolved:
            combined_warnings.append(_format_unresolved_warning(entry))
        combined_warnings.extend(version_warnings)
        combined_warnings.extend(transitive_error_warnings)

        details: List[str] = []
        for cand_detail in (
            startup_cs.get("detail") if startup_usable else None,
            final_cs.get("detail"),
            transitive_error_detail,
        ):
            if isinstance(cand_detail, str) and cand_detail and cand_detail not in details:
                details.append(cand_detail)
        merged_detail = "; ".join(details) if details else None

        is_partial = (
            bool(all_unresolved)
            or (startup_usable and startup_status in ("partial", "failed"))
            or (final_status in ("partial", "failed"))
            or version_changed
            or bool(transitive_error_detail)
        )
        merged_status = "partial" if is_partial else "complete"

        return {
            "mode": effective_mode,
            "snapshot_stage": "final",
            "records": all_records,
            "unresolved": all_unresolved,
            "local_modules": sorted(local_set),
            "coverage_notes": _coverage_notes_for(effective_mode, "final"),
            "capture_state": _build_capture_state(
                merged_status, detail=merged_detail, warnings=combined_warnings
            ),
        }

    # Non-import modes: top-level-installed and full-environment.
    non_import_records: List[Dict[str, Any]] = []
    for rec in final.get("records") or ():
        if not isinstance(rec, dict):
            continue
        name = rec.get("name")
        if not isinstance(name, str) or not name:
            continue
        rec_copy = _copy_package_record(rec)
        if rec_copy.get("source") != "imported":
            rec_copy["import_names"] = None
            rec_copy["observed_at"] = None
        non_import_records.append(rec_copy)
    non_import_records.sort(key=lambda x: (x.get("name") or "").lower())

    non_import_unresolved: List[Dict[str, Any]] = []
    for entry in final.get("unresolved") or ():
        cleaned = _normalize_unresolved_entry(entry, default_observed_at="final")
        if cleaned is not None:
            non_import_unresolved.append(cleaned)
    non_import_unresolved.sort(
        key=lambda item: (
            item["module"].lower(),
            item["reason"].lower(),
            (item.get("detail") or "").lower(),
        )
    )

    non_import_warnings = list(startup_warnings) + list(final_warnings)
    for entry in non_import_unresolved:
        non_import_warnings.append(_format_unresolved_warning(entry))

    non_import_details: List[str] = []
    for cand_detail in (
        startup_cs.get("detail") if startup_usable else None,
        final_cs.get("detail"),
    ):
        if isinstance(cand_detail, str) and cand_detail and cand_detail not in non_import_details:
            non_import_details.append(cand_detail)
    non_import_detail = "; ".join(non_import_details) if non_import_details else None

    non_import_partial = (
        bool(non_import_unresolved)
        or (startup_usable and (startup_status in ("partial", "failed") or bool(startup_warnings)))
        or (final_status in ("partial", "failed"))
    )
    non_import_status = "partial" if non_import_partial else "complete"

    return {
        "mode": effective_mode,
        "snapshot_stage": "final",
        "records": non_import_records,
        "unresolved": non_import_unresolved,
        "local_modules": sorted(
            {m for m in (final.get("local_modules") or ()) if isinstance(m, str) and m}
        ),
        "coverage_notes": _dedupe_strings(
            [str(n) for n in (final.get("coverage_notes") or ()) if isinstance(n, str) and n]
        ),
        "capture_state": _build_capture_state(
            non_import_status, detail=non_import_detail, warnings=non_import_warnings
        ),
    }


def get_packages(
    config: Dict[str, Any],
    *,
    stage: str = "single",
    include_transitive: bool = True,
) -> Dict[str, Any]:
    """Capture installed Python packages via ``importlib.metadata``.

    Modes:
    - ``imported-only``: Only packages already loaded in ``sys.modules`` (default).
    - ``imported-transitive``: Imported packages plus their declared dependencies.
    - ``top-level-installed``: Installed distributions not required by other distributions.
    - ``full-environment``: Every distribution in the environment.

    Args:
        config: Resolved pubrun configuration.
        stage: Lifecycle stage tag (``"startup"``, ``"final"``, or ``"single"``).
        include_transitive: When ``False`` in ``imported-transitive`` mode,
            resolve imported distributions only so ``merge_package_snapshots`` can
            compute the recursive transitive closure once over the merged set.
    """
    return resolve_packages_snapshot(
        config,
        stage=stage,
        include_transitive=include_transitive,
    )
