#!/usr/bin/env python3
"""Source-checkout compatibility shim for ``src/pubrun/_bench/share_safety.py``.

Loads the canonical packaged share-safety validator directly by file path (or
reuses ``sys.modules["pubrun._bench.share_safety"]`` when already imported)
without importing ``pubrun``. This keeps Continuous Integration (CI) intake
validation (which runs without ``pubrun`` installed) and local checkout scripts
working with zero auto-start side effects.
"""
from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path
from typing import Any, List

_SHIM_OWN_ATTRS = frozenset(
    {
        "_shim_target",
        "__class__",
        "__dict__",
        "__spec__",
        "__loader__",
        "__package__",
        "__path__",
        "__file__",
        "__name__",
        "__cached__",
        "__doc__",
    }
)


class _ShareSafetyShim(types.ModuleType):
    """Forwarding module proxy so monkeypatching targets the canonical module."""

    def _rebind_shim_target(self, target: types.ModuleType) -> None:
        object.__setattr__(self, "_shim_target", target)

    def __getattr__(self, name: str) -> Any:
        return getattr(object.__getattribute__(self, "_shim_target"), name)

    def __setattr__(self, name: str, value: Any) -> None:
        if name in _SHIM_OWN_ATTRS:
            object.__setattr__(self, name, value)
        else:
            setattr(object.__getattribute__(self, "_shim_target"), name, value)

    def __delattr__(self, name: str) -> None:
        if name in _SHIM_OWN_ATTRS:
            object.__delattr__(self, name)
        else:
            delattr(object.__getattribute__(self, "_shim_target"), name)

    def __dir__(self) -> List[str]:
        target = object.__getattribute__(self, "_shim_target")
        own = object.__getattribute__(self, "__dict__").keys()
        return sorted(set(dir(target)) | set(own))


def _load_canonical_share_safety() -> types.ModuleType:
    existing = sys.modules.get("pubrun._bench.share_safety")
    if isinstance(existing, types.ModuleType):
        return existing
    target_path = (
        Path(__file__).resolve().parent.parent / "src" / "pubrun" / "_bench" / "share_safety.py"
    )
    spec = importlib.util.spec_from_file_location(
        "_pubrun_bench_share_safety_standalone", target_path
    )
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not load canonical share_safety from {target_path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _install_shim() -> None:
    target = _load_canonical_share_safety()
    registered = sys.modules.get(__name__)
    if registered is not None and registered.__dict__ is globals():
        object.__setattr__(registered, "_shim_target", target)
        registered.__class__ = _ShareSafetyShim
    else:
        for attr, val in vars(target).items():
            if not (attr.startswith("__") and attr.endswith("__")):
                globals()[attr] = val


_install_shim()
del _install_shim, _load_canonical_share_safety
