#!/usr/bin/env python3
"""Source-checkout compatibility shim for ``src/pubrun/_bench/harness.py``.

Ensures the checkout ``src/`` tree is importable and selects ``pubrun.minimal``
before importing ``pubrun._bench.harness`` so direct execution or import never
triggers ``pubrun`` auto-start.
"""
from __future__ import annotations

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


class _HarnessShim(types.ModuleType):
    """Forwarding module proxy so monkeypatching targets ``pubrun._bench.harness``."""

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


def _bootstrap_and_load() -> types.ModuleType:
    repo_root = Path(__file__).resolve().parent.parent
    src_root = repo_root / "src"
    if src_root.is_dir():
        src_str = str(src_root)
        if src_str not in sys.path:
            sys.path.insert(0, src_str)

    # Select pubrun.minimal BEFORE importing any pubrun._bench module so neither
    # `python benchmarks/harness.py` nor importing this shim ever auto-starts pubrun.
    if "pubrun" not in sys.modules:
        import pubrun.minimal  # noqa: F401

    from pubrun._bench import harness as bench_harness
    from pubrun._bench import share_safety as bench_share_safety

    # Keep any already-loaded checkout share_safety shim bound to the exact
    # pubrun._bench.share_safety module object that bench_harness.main() calls.
    ss_shim = sys.modules.get("share_safety")
    if ss_shim is not None and hasattr(ss_shim, "_rebind_shim_target"):
        ss_shim._rebind_shim_target(bench_share_safety)

    registered = sys.modules.get(__name__)
    if __name__ != "__main__" and registered is not None and registered.__dict__ is globals():
        object.__setattr__(registered, "_shim_target", bench_harness)
        registered.__class__ = _HarnessShim
    else:
        for attr, val in vars(bench_harness).items():
            if not (attr.startswith("__") and attr.endswith("__")):
                globals()[attr] = val
    return bench_harness


_bench_harness_target = _bootstrap_and_load()
del _bootstrap_and_load

if __name__ == "__main__":
    _bench_harness_target.main()
else:
    del _bench_harness_target
