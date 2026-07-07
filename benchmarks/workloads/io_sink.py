"""Ground-truth I/O workload: write (and, unless the sink is a null device, read back)
a fixed payload against a configurable target.

The target is chosen via the ``PUBRUN_BENCH_IO_TARGET`` env var:
  - a directory path -> a temp file is created there (e.g. ``/dev/shm`` for a RAM-backed
    tmpfs floor, or ``$TMPDIR`` for the default temp filesystem);
  - the literal null device (``/dev/null`` on POSIX, ``NUL`` on Windows) -> write-only
    sink that isolates the pure open()/write path cost from any storage.

These scenarios establish reference floors ("ground truth") for I/O so that the
storage-dependent ``hotpath-open`` numbers can be interpreted against a known baseline.
When pubrun is active with file provenance enabled, this also shows the recording tax on
real I/O; with provenance at the default level it is metadata-only.
"""
import os
import tempfile

_PAYLOAD = b"x" * (8 * 1024 * 1024)  # 8 MiB, matching file_read.py


def _null_device() -> str:
    return "NUL" if os.name == "nt" else "/dev/null"


def _work() -> int:
    target = os.environ.get("PUBRUN_BENCH_IO_TARGET", tempfile.gettempdir())
    total = 0

    # Null-device sink: write only (there is nothing to read back).
    if target in ("/dev/null", "NUL") or os.path.basename(target).upper() == "NUL":
        with open(_null_device(), "wb") as f:
            f.write(_PAYLOAD)
        return len(_PAYLOAD)

    # Directory target: create a temp file there, write, then read it back in chunks.
    fd, path = tempfile.mkstemp(suffix=".bin", dir=target)
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(_PAYLOAD)
        with open(path, "rb") as f:
            while True:
                chunk = f.read(65536)
                if not chunk:
                    break
                total += len(chunk)
    finally:
        try:
            os.unlink(path)
        except OSError:
            pass
    return total


if __name__ == "__main__":
    _work()
