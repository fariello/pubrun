"""CPU-bound workload: a fixed, deterministic arithmetic loop.

Runs the same amount of work regardless of whether pubrun is active, so timing
differences between scenarios reflect pubrun's per-run overhead on a compute
workload (e.g. resource-watcher sampling, event flushing), not the work itself.
"""

def _work() -> int:
    total = 0
    for i in range(2_000_000):
        total += (i * i) % 7
    return total


if __name__ == "__main__":
    _work()
