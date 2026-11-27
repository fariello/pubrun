"""Source-checkout compatibility shim for ``src/pubrun/_bench/scenarios.py``.

Loads the canonical packaged scenario definitions directly by file path (or
reuses ``sys.modules["pubrun._bench.scenarios"]`` when already imported)
without importing ``pubrun``.
"""
from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path


def _load_canonical_scenarios() -> types.ModuleType:
    existing = sys.modules.get("pubrun._bench.scenarios")
    if isinstance(existing, types.ModuleType):
        return existing
    target_path = (
        Path(__file__).resolve().parent.parent / "src" / "pubrun" / "_bench" / "scenarios.py"
    )
    mod_name = "_pubrun_bench_scenarios_standalone"
    cached = sys.modules.get(mod_name)
    if isinstance(cached, types.ModuleType):
        return cached
    spec = importlib.util.spec_from_file_location(mod_name, target_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not load canonical scenarios from {target_path}")
    mod = importlib.util.module_from_spec(spec)
    # Register before exec_module so Python 3.12+ @dataclass resolves cls.__module__.
    sys.modules[mod_name] = mod
    try:
        spec.loader.exec_module(mod)
    except Exception:
        sys.modules.pop(mod_name, None)
        raise
    return mod


_target = _load_canonical_scenarios()
for _attr, _val in vars(_target).items():
    if not (_attr.startswith("__") and _attr.endswith("__")):
        globals()[_attr] = _val
del _target, _attr, _val, _load_canonical_scenarios
