"""Declarative benchmark scenarios for pubrun.

Each Scenario describes how to launch one child Python process:

- ``name``     : unique scenario id.
- ``group``    : logical grouping for the report (e.g. "startup", "console").
- ``mode``     : pubrun import behavior for the child. One of the real modes
                 ``auto | noauto | nopatch | noconsole | minimal`` (set via the
                 ``PUBRUN_IMPORT_MODE`` env var), or the sentinel ``"baseline"``
                 which runs the workload with NO pubrun import at all.
- ``workload`` : filename under ``workloads/`` to execute.
- ``config``   : dict written to a temporary ``.pubrun.toml`` for the child
                 (nested pubrun config keys). Empty for baseline.
- ``skip_if``  : optional callable returning a reason string to skip, else None.

The harness turns each Scenario into a fresh subprocess and times it. Scenarios
are intentionally declarative and stdlib-only so this module has no third-party
imports.
"""
from __future__ import annotations

import sys
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional


@dataclass(frozen=True)
class Scenario:
    name: str
    group: str
    mode: str  # "baseline" | auto | noauto | nopatch | noconsole | minimal
    workload: str
    config: Dict = field(default_factory=dict)
    skip_if: Optional[Callable[[], Optional[str]]] = None
    # Extra environment variables for the child process (e.g. a workload's target path).
    env: Dict = field(default_factory=dict)

    @property
    def is_baseline(self) -> bool:
        return self.mode == "baseline"


def _resources(**kw) -> Dict:
    return {"capture": {"resources": {"depth": "standard", **kw}}}


# Common "everything off" config so per-feature scenarios isolate a single feature.
_ALL_OFF = {
    "console": {"capture_mode": "off"},
    "capture": {
        "resources": {"depth": "off"},
        "subprocesses": {"enabled": False},
        "git": {"enabled": False},
        "hardware": {"depth": "off"},
        "packages": {"mode": "off"},
        "signals": {"enabled": False},
    },
    "events": {"enabled": False},
}


def _merge(base: Dict, override: Dict) -> Dict:
    out = {k: (dict(v) if isinstance(v, dict) else v) for k, v in base.items()}
    for k, v in override.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _merge(out[k], v)
        else:
            out[k] = v
    return out


def _off_plus(override: Dict) -> Dict:
    """All-off baseline config with a single feature turned back on."""
    return _merge(_ALL_OFF, override)


def all_scenarios() -> List[Scenario]:
    S: List[Scenario] = []

    # --- Group 1: startup / import overhead (noop workload) -----------------
    S.append(Scenario("baseline-noop", "startup", "baseline", "noop.py"))
    for mode in ("auto", "noauto", "nopatch", "noconsole", "minimal"):
        S.append(Scenario(f"import-{mode}", "startup", mode, "noop.py",
                          config=_ALL_OFF if mode in ("auto", "nopatch", "noconsole") else {}))

    # --- Group 2: per-feature run-time deltas (cpu_burn, one feature on) ----
    S.append(Scenario("feature-baseline", "feature", "baseline", "cpu_burn.py"))
    S.append(Scenario("feature-none", "feature", "auto", "cpu_burn.py", config=_ALL_OFF))
    S.append(Scenario("feature-resources-15s", "feature", "auto", "cpu_burn.py",
                       config=_off_plus(_resources(sample_interval_seconds=15))))
    S.append(Scenario("feature-resources-1s", "feature", "auto", "cpu_burn.py",
                       config=_off_plus(_resources(sample_interval_seconds=1))))
    S.append(Scenario("feature-resources-tree", "feature", "auto", "cpu_burn.py",
                       config=_off_plus(_resources(sample_interval_seconds=1, scope="tree")),
                       skip_if=lambda: "tree scope not implemented on Windows" if sys.platform == "win32" else None))
    S.append(Scenario("feature-subprocesses", "feature", "auto", "cpu_burn.py",
                       config=_off_plus({"capture": {"subprocesses": {"enabled": True}}})))
    S.append(Scenario("feature-git", "feature", "auto", "cpu_burn.py",
                       config=_off_plus({"capture": {"git": {"enabled": True}}})))
    S.append(Scenario("feature-hardware", "feature", "auto", "cpu_burn.py",
                       config=_off_plus({"capture": {"hardware": {"depth": "basic"}}})))
    S.append(Scenario("feature-packages-imported", "feature", "auto", "cpu_burn.py",
                       config=_off_plus({"capture": {"packages": {"mode": "imported-only"}}})))
    S.append(Scenario("feature-packages-full", "feature", "auto", "cpu_burn.py",
                       config=_off_plus({"capture": {"packages": {"mode": "full-environment"}}})))

    # --- Group 3: hot-path taxes --------------------------------------------
    S.append(Scenario("hotpath-open-baseline", "hotpath", "baseline", "file_read.py"))
    S.append(Scenario("hotpath-open-pubrun", "hotpath", "auto", "file_read.py", config=_ALL_OFF))
    S.append(Scenario("hotpath-print-baseline", "hotpath", "baseline", "print_loop.py"))
    S.append(Scenario("hotpath-print-tee", "hotpath", "auto", "print_loop.py",
                       config=_off_plus({"console": {"capture_mode": "standard"}})))

    # --- Group 4: ground-truth I/O baselines (reference floors, not overhead pairs) ---
    # /dev/null: write-only sink; isolates the open()/write path from any storage.
    _null = "NUL" if sys.platform == "win32" else "/dev/null"
    S.append(Scenario("io-baseline-devnull", "io_baseline", "baseline", "io_sink.py",
                      env={"PUBRUN_BENCH_IO_TARGET": _null}))
    # /dev/shm: RAM-backed tmpfs floor (Linux). Skipped where /dev/shm is unavailable.
    S.append(Scenario("io-baseline-devshm", "io_baseline", "baseline", "io_sink.py",
                      env={"PUBRUN_BENCH_IO_TARGET": "/dev/shm"},
                      skip_if=lambda: None if (sys.platform.startswith("linux")
                                               and _dir_writable("/dev/shm"))
                              else "/dev/shm not available on this platform"))
    # $TMPDIR: the default temp filesystem, for direct comparison against the floors above.
    S.append(Scenario("io-baseline-tmpdir", "io_baseline", "baseline", "io_sink.py"))

    return S


def _dir_writable(path: str) -> bool:
    import os
    return os.path.isdir(path) and os.access(path, os.W_OK)
