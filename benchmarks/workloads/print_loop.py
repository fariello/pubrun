"""Print-loop workload: many stdout writes.

Exercises the console tee (when capture_mode != off). Comparing against baseline
isolates the per-write tee/logging tax. Output is small per line to keep the
dominant cost the write path, not formatting.
"""

def _work() -> None:
    for i in range(5000):
        print(f"line {i}")


if __name__ == "__main__":
    _work()
