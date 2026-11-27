"""File-read workload: stat-only versus full-hashing file provenance cost.

pubrun never patches the global ``open()``. File provenance is recorded only for
files opened through ``pubrun.open()`` or registered with
``pubrun.register_input()``. This workload measures what that costs, per mode,
selected by the ``PUBRUN_BENCH_FILE_MODE`` environment variable:

- ``baseline``           : read with ``builtins.open()``; pubrun is NEVER imported.
- ``open-stat``          : read through ``pubrun.open()`` at ``level = "stat"``
                           (open-fd ``fstat`` only, zero extra bytes read).
- ``open-hash-stream``   : read sequentially through ``pubrun.open()`` at
                           ``level = "hash"``; the digest is computed from the
                           bytes the caller already read (zero extra bytes read).
- ``open-hash-fallback`` : as above, but a ``seek()`` invalidates the single-pass
                           stream, so pubrun re-reads the whole file at close.
- ``register-stat``      : read with ``builtins.open()`` (an unmodified library),
                           then ``pubrun.register_input()`` at ``level = "stat"``.
- ``register-hash``      : as above at ``level = "hash"`` (pubrun re-reads the
                           file to hash it).

The file size defaults to 8 MiB and is configurable with
``PUBRUN_BENCH_FILE_BYTES``.

Under the benchmark harness the pubrun-active modes run inside the auto-started
run, with ``[capture.file_io].level`` set by the scenario config. Run standalone
with ``--measure-detail`` to execute one mode inside a temporary
``pubrun.tracked_run()`` and print JSON metrics: ``total_s``,
``close_or_register_s``, ``extra_read_bytes``, ``hash_status``,
``observation_time`` and, on Linux, ``/proc/self/io`` ``rchar``/``read_bytes``
deltas. Every temporary file and run directory is removed afterwards.
"""
from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile
import time
from typing import Any, Dict, Optional, Sequence, Tuple

MODES = (
    "baseline",
    "open-stat",
    "open-hash-stream",
    "open-hash-fallback",
    "register-stat",
    "register-hash",
)
_CHUNK = 65536
_DEFAULT_BYTES = 8 * 1024 * 1024


def _mode() -> str:
    mode = os.environ.get("PUBRUN_BENCH_FILE_MODE", "baseline")
    if mode not in MODES:
        raise SystemExit(f"unknown PUBRUN_BENCH_FILE_MODE {mode!r}; expected one of {MODES}")
    return mode


def _size() -> int:
    try:
        return max(1, int(os.environ.get("PUBRUN_BENCH_FILE_BYTES", _DEFAULT_BYTES)))
    except ValueError:
        return _DEFAULT_BYTES


def level_for(mode: str) -> str:
    """The [capture.file_io].level a mode requires ("none" for baseline)."""
    if mode == "baseline":
        return "none"
    return "stat" if mode.endswith("-stat") else "hash"


def _make_file(n_bytes: int) -> str:
    fd, path = tempfile.mkstemp(suffix=".bin")
    with os.fdopen(fd, "wb") as f:
        remaining = n_bytes
        block = b"x" * _CHUNK
        while remaining > 0:
            f.write(block[: min(_CHUNK, remaining)])
            remaining -= _CHUNK
    return path


def _drain(f: Any) -> int:
    total = 0
    while True:
        chunk = f.read(_CHUNK)
        if not chunk:
            return total
        total += len(chunk)


def _read_once(mode: str, path: str) -> Tuple[int, float]:
    """Read ``path`` per ``mode``. Return (bytes_read, close_or_register_seconds)."""
    if mode in ("baseline", "register-stat", "register-hash"):
        with open(path, "rb") as f:  # builtins.open: an unmodified library
            total = _drain(f)
        if mode == "baseline":
            return total, 0.0
        import pubrun  # lazy: never imported in baseline mode

        t0 = time.perf_counter()
        pubrun.register_input(path, label="bench_input")
        return total, time.perf_counter() - t0

    import pubrun  # lazy: never imported in baseline mode

    fh: Any = pubrun.open(path, "rb")
    try:
        if mode == "open-hash-fallback":
            fh.seek(0)  # any seek invalidates the single-pass stream hash
        total = _drain(fh)
    finally:
        t0 = time.perf_counter()
        fh.close()
        dt = time.perf_counter() - t0
    return total, dt


def _work() -> int:
    mode = _mode()
    path = _make_file(_size())
    try:
        total, _ = _read_once(mode, path)
    finally:
        try:
            os.unlink(path)
        except OSError:
            pass
    return total


def _proc_io() -> Dict[str, int]:
    """Linux /proc/self/io counters, or {} where unavailable."""
    out: Dict[str, int] = {}
    try:
        with open("/proc/self/io", "r", encoding="ascii") as f:
            for line in f:
                key, _, val = line.partition(":")
                if key in ("rchar", "read_bytes"):
                    out[key] = int(val.strip())
    except (OSError, ValueError):
        return {}
    return out


def measure_detail(mode: str) -> Dict[str, Any]:
    """Run one mode inside a temporary tracked run and return its metrics."""
    workdir = tempfile.mkdtemp(prefix="pubrun-bench-file-")
    old_cwd = os.getcwd()
    path: Optional[str] = None
    try:
        os.chdir(workdir)
        path = _make_file(_size())
        record: Optional[Dict[str, Any]] = None
        if mode == "baseline":
            io0 = _proc_io()
            t0 = time.perf_counter()
            _, step_s = _read_once(mode, path)
            total_s = time.perf_counter() - t0
            io1 = _proc_io()
        else:
            os.environ.setdefault("PUBRUN_AUTO_START", "false")
            import pubrun

            with pubrun.tracked_run(
                output_dir=os.path.join(workdir, "runs"),
                capture={"file_io": {"level": level_for(mode)}},
            ) as active:
                run: Any = getattr(active, "run_tracker", active)
                io0 = _proc_io()
                t0 = time.perf_counter()
                _, step_s = _read_once(mode, path)
                total_s = time.perf_counter() - t0
                io1 = _proc_io()
                run_dir = str(run.run_dir)
            with open(os.path.join(run_dir, "manifest.json"), "r", encoding="utf-8") as f:
                manifest = json.load(f)
            inputs = (manifest.get("data_files") or {}).get("inputs") or []
            matches = [
                r for r in inputs if os.path.basename(str(r.get("path"))) == os.path.basename(path)
            ]
            record = matches[-1] if matches else None
        result: Dict[str, Any] = {
            "mode": mode,
            "level": level_for(mode),
            "file_bytes": _size(),
            "total_s": round(total_s, 6),
            "close_or_register_s": round(step_s, 6),
            "extra_read_bytes": ((record or {}).get("hash_stats") or {}).get("extra_read_bytes", 0),
            "hash_status": (record or {}).get("hash_status"),
            "observation_time": (record or {}).get("observation_time"),
        }
        if io0 and io1:
            result["proc_io_delta"] = {k: io1[k] - io0[k] for k in io0 if k in io1}
        return result
    finally:
        os.chdir(old_cwd)
        if path:
            try:
                os.unlink(path)
            except OSError:
                pass
        shutil.rmtree(workdir, ignore_errors=True)


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if "--measure-detail" in args:
        print(json.dumps(measure_detail(_mode()), sort_keys=True))
        return 0
    _work()
    return 0


if __name__ == "__main__":
    sys.exit(main())
