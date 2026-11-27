"""Internal packaged benchmark runtime helpers for pubrun.

Standard-library only and side-effect free: importing this subpackage never
imports ``pubrun.core`` or selects an import mode.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

__all__ = [
    "find_checkout_root",
    "default_results_dir",
    "get_workload_path",
    "get_submit_script_path",
]


def find_checkout_root(start: Optional[Path] = None) -> Optional[Path]:
    """Return the nearest verified pubrun source checkout containing *start*.

    Inspects *start* (default ``Path.cwd()``) and its parent directories,
    returning the first directory that contains ``benchmarks/harness.py`` and
    a ``pyproject.toml`` declaring ``name = "pubrun"``. Returns ``None`` when
    *start* is outside a verified checkout, even if ``pubrun`` itself is
    imported from an editable source checkout.
    """
    try:
        base = (Path(start) if start is not None else Path.cwd()).resolve()
    except OSError:
        return None

    from pubrun import _pyproject_declares_pubrun

    for candidate in (base,) + tuple(base.parents):
        harness = candidate / "benchmarks" / "harness.py"
        pyproject = candidate / "pyproject.toml"
        if harness.is_file() and pyproject.is_file():
            try:
                if _pyproject_declares_pubrun(pyproject):
                    return candidate
            except Exception:
                continue
    return None


def _package_checkout_root() -> Optional[Path]:
    """Return the verified checkout root for the imported ``pubrun`` package, or ``None``.

    Returns ``None`` for wheel installations in ``site-packages``.
    """
    from pubrun import _is_verified_source_checkout

    pkg_dir = Path(__file__).resolve().parents[1]
    root = _is_verified_source_checkout(pkg_dir)
    return Path(root) if root is not None else None


def default_results_dir(cwd: Optional[Path] = None) -> Path:
    """Return the default writable directory for benchmark results.

    Resolution order:
    1. The ``PUBRUN_RESULTS_DIR`` environment variable, when set and non-empty.
    2. ``<checkout_root>/benchmarks/results`` when *cwd* (default ``Path.cwd()``)
       is inside a verified ``pubrun`` source checkout whose ``benchmarks/``
       directory exists.
    3. ``<cwd>/pubrun-bench-results`` otherwise.
    """
    env_dir = os.environ.get("PUBRUN_RESULTS_DIR", "").strip()
    if env_dir:
        return Path(env_dir)

    checkout_root = find_checkout_root(cwd)
    if checkout_root is not None and (checkout_root / "benchmarks").is_dir():
        return checkout_root / "benchmarks" / "results"

    base = Path(cwd) if cwd is not None else Path.cwd()
    return base / "pubrun-bench-results"


def get_workload_path(filename: str) -> Path:
    """Return the path to a packaged benchmark workload script."""
    return Path(__file__).resolve().parent / "workloads" / filename


def get_submit_script_path(filename: str) -> Path:
    """Return the path to a packaged high-performance computing submission script."""
    return Path(__file__).resolve().parent / "scripts" / filename
