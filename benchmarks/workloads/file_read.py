"""Source-checkout compatibility shim for ``src/pubrun/_bench/workloads/file_read.py``."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

_TARGET_PATH = (
    Path(__file__).resolve().parents[2]
    / "src"
    / "pubrun"
    / "_bench"
    / "workloads"
    / "file_read.py"
)
_SPEC = importlib.util.spec_from_file_location("_pubrun_bench_workload_file_read", _TARGET_PATH)
if _SPEC is None or _SPEC.loader is None:
    raise ImportError(f"Could not load workload from {_TARGET_PATH}")
_MOD = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MOD)
for _attr, _val in vars(_MOD).items():
    if not (_attr.startswith("__") and _attr.endswith("__")):
        globals()[_attr] = _val
del _TARGET_PATH, _SPEC, _MOD, _attr, _val

if __name__ == "__main__":
    sys.exit(main())  # type: ignore[name-defined]
