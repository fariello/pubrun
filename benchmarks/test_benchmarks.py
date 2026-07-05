"""pytest-benchmark micro-suite for pubrun hot paths.

This file is NOT collected by the default `pytest` run: the project sets
`testpaths = ["tests"]`, so a bare `pytest` never looks in `benchmarks/`.

Run it explicitly (requires the optional extra `pip install -e .[bench]`):

    pytest benchmarks/ -o addopts="" --benchmark-only

`-o addopts=""` clears the repo's global coverage addopts (`--cov=...`), which
would otherwise distort pytest-benchmark timings. (Do not use `-p no:cov`: that
disables the cov plugin but leaves the now-unrecognized `--cov` flags in
addopts, which errors out.)
"""
import builtins

import pytest

# Skip cleanly if the optional [bench] extra is not installed.
pytest.importorskip("pytest_benchmark")


def test_bench_import_pubrun_cost(benchmark):
    """Cost of importing the pubrun capture config path (warm import)."""
    from pubrun.config import resolve_config
    benchmark(resolve_config)


def test_bench_builtin_open_read(benchmark, tmp_path):
    """Baseline: builtins.open read of a small buffer (no pubrun proxy)."""
    p = tmp_path / "data.bin"
    p.write_bytes(b"x" * (1024 * 1024))

    def read():
        with builtins.open(p, "rb") as f:
            while f.read(65536):
                pass

    benchmark(read)


def test_bench_pubrun_print(benchmark, capsys):
    """Cost of pubrun.print vs builtin (no active run -> minimal path)."""
    from pubrun.core import print as pubrun_print

    def loop():
        for _ in range(100):
            pubrun_print("x")

    benchmark(loop)
    capsys.readouterr()  # drain captured output
