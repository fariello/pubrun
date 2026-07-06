"""File-read workload: reads a temp file in chunks.

When pubrun is active with its patched open(), each read is hashed incrementally.
Comparing this scenario with pubrun active vs the baseline isolates the
per-byte hashing tax on the host's real file I/O.
"""
import os
import tempfile


def _work() -> int:
    total = 0
    fd, path = tempfile.mkstemp(suffix=".bin")
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(b"x" * (8 * 1024 * 1024))  # 8 MiB
        # Read it back in chunks (uses the possibly-patched open()).
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
