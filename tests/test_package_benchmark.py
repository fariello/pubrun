"""Behavioral tests for benchmarks/package_capture_bench.py and its scenario entry."""
from __future__ import annotations

import getpass
import importlib.metadata
import importlib.util
import json
import os
import platform
import subprocess
import sys
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[1]
_SCRIPT = _REPO / "benchmarks" / "package_capture_bench.py"
_MODES = ("off", "imported-only", "imported-transitive", "top-level-installed", "full-environment")
_STAT_KEYS = ("n", "median_ms", "iqr_ms", "stdev_ms", "p95_ms", "min_ms", "max_ms")


def _load_module(mod_name: str, rel_path: str):
    path = _REPO / rel_path
    spec = importlib.util.spec_from_file_location(mod_name, path)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules[mod_name] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def bench_run(tmp_path_factory):
    """Run the benchmark once with tiny parameters and return (proc, result, workdir)."""
    workdir = tmp_path_factory.mktemp("pcbench_work")
    out_json = workdir / "out.json"
    proc = subprocess.run(
        [
            sys.executable,
            str(_SCRIPT),
            "--small-count", "4",
            "--large-count", "12",
            "--repetitions", "2",
            "--cold-runs", "1",
            "--workdir", str(workdir),
            "--json-out", str(out_json),
        ],
        capture_output=True,
        text=True,
        timeout=600,
    )
    result = json.loads(out_json.read_text(encoding="utf-8")) if out_json.exists() else None
    return proc, result, workdir


class TestPackageCaptureBenchRun:
    def test_exits_zero_and_writes_json(self, bench_run):
        proc, result, _ = bench_run
        assert proc.returncode == 0, proc.stderr
        assert result is not None
        assert result["schema_version"] == "pubrun-package-capture-bench/1"

    def test_environment_revision_and_filesystem_metadata(self, bench_run):
        _, result, _ = bench_run
        env = result["environment"]
        assert env["python_version"] == platform.python_version()
        assert env["cpu"]["logical_cores"] == os.cpu_count()
        assert "git_revision" in result
        assert result["git_revision"] is None or len(result["git_revision"]) == 12
        assert "workdir" in result["filesystem"]
        assert isinstance(result["workdir_fstype"], str) and result["workdir_fstype"]
        assert isinstance(result["workdir_is_network"], bool)
        assert result["workdir_kind"] == "user-supplied"
        assert result["parameters"]["modes"] == list(_MODES)

    def test_separate_startup_and_finalization_cold_and_warm_stats(self, bench_run):
        _, result, _ = bench_run
        assert set(result["profiles"]) == {"small", "large", "ambient"}
        for profile, pdata in result["profiles"].items():
            assert set(pdata["modes"]) == set(_MODES), profile
            for mode, mdata in pdata["modes"].items():
                assert mdata["failures"] == 0, (profile, mode)
                for phase in ("startup_ms", "finalization_ms"):
                    for kind, expected_n in (("cold", 1), ("warm", 2)):
                        stats = mdata[phase][kind]
                        for key in _STAT_KEYS:
                            assert key in stats, (profile, mode, phase, kind, key)
                        assert stats["n"] == expected_n
                        assert stats["median_ms"] >= 0.0
                assert set(mdata["delta_vs_off_ms"]) == {"startup_ms", "finalization_ms"}

    def test_off_mode_is_suppressed_baseline(self, bench_run):
        _, result, _ = bench_run
        for pdata in result["profiles"].values():
            off = pdata["modes"]["off"]
            assert off["capture_status"] == "suppressed"
            assert off["records"] == 0
            assert off["delta_vs_off_ms"]["finalization_ms"]["warm"] == 0.0

    def test_synthetic_profiles_capture_expected_distributions(self, bench_run):
        _, result, _ = bench_run
        small = result["profiles"]["small"]
        large = result["profiles"]["large"]
        assert small["synthetic_distributions"] == 4
        assert large["synthetic_distributions"] == 12
        assert small["isolated_interpreter"] is True
        # python -S isolation: only the synthetic distributions are installed.
        assert large["modes"]["full-environment"]["indexed_distributions"] == 12
        assert large["modes"]["full-environment"]["records"] == 12
        # One startup import plus one late import, both resolved and merged.
        assert large["modes"]["imported-only"]["records"] == 2
        # Requires-Dist chains make the transitive closure strictly larger.
        assert (
            large["modes"]["imported-transitive"]["records"]
            > large["modes"]["imported-only"]["records"]
        )

    def test_markdown_has_no_identifying_strings(self, bench_run):
        proc, _, workdir = bench_run
        md = proc.stdout
        assert "| imported-transitive |" in md
        assert "/home/" not in md and "/Users/" not in md
        assert str(workdir) not in md
        assert str(Path.home()) not in md
        node = platform.node()
        if node and len(node) >= 3:
            assert node not in md
        try:
            user = getpass.getuser()
        except Exception:
            user = ""
        if user and len(user) >= 3:
            assert f"/{user}" not in md

    def test_json_has_no_workdir_path(self, bench_run):
        _, result, workdir = bench_run
        blob = json.dumps(result)
        assert str(workdir) not in blob
        assert str(Path.home()) not in blob

    def test_workdir_left_clean(self, bench_run):
        _, _, workdir = bench_run
        assert sorted(p.name for p in workdir.iterdir()) == ["out.json"]


class TestPackageCaptureBenchCli:
    def test_rejects_non_positive_repetitions(self, tmp_path):
        proc = subprocess.run(
            [sys.executable, str(_SCRIPT), "--repetitions", "0", "--workdir", str(tmp_path)],
            capture_output=True,
            text=True,
            timeout=60,
        )
        assert proc.returncode == 2
        assert "--repetitions" in proc.stderr
        assert list(tmp_path.iterdir()) == []


class TestSyntheticEnvironmentBuilder:
    def test_builder_writes_discoverable_distributions(self, tmp_path):
        mod = _load_module("_test_pcbench_builder", "benchmarks/package_capture_bench.py")
        site_dir = mod.build_synthetic_site(tmp_path / "env", 12)
        dists = {
            d.metadata["Name"]: d
            for d in importlib.metadata.distributions(path=[str(site_dir)])
        }
        assert len(dists) == 12
        first = dists["pcbench-dist-0000"]
        reqs = first.requires or []
        assert "pcbench-dist-0001" in reqs
        assert any("python_version" in r for r in reqs)
        assert any(r.startswith("pcbench-dist-0005[fast]") for r in reqs)
        gated = dists["pcbench-dist-0005"]
        assert any('extra == "fast"' in r for r in (gated.requires or []))
        # Import name differs from distribution name.
        assert (first.read_text("top_level.txt") or "").strip() == "pcbench_mod_0000"
        assert (site_dir / "pcbench_mod_0000" / "__init__.py").is_file()

    def test_workload_subsets_are_fixed_and_disjoint(self):
        mod = _load_module("_test_pcbench_workload", "benchmarks/package_capture_bench.py")
        w = mod.synthetic_workload(300)
        assert len(w["startup_modules"]) == 30
        assert len(w["late_modules"]) == 15
        assert not set(w["startup_modules"]) & set(w["late_modules"])
        assert mod.synthetic_workload(300) == w


class TestTransitiveScenario:
    def test_feature_packages_transitive_registered(self):
        mod = _load_module("_test_scenarios_pkg_transitive", "benchmarks/scenarios.py")
        by_name = {s.name: s for s in mod.all_scenarios()}
        scn = by_name["feature-packages-transitive"]
        assert scn.group == "feature"
        assert scn.mode == "auto"
        assert scn.config["capture"]["packages"]["mode"] == "imported-transitive"
        for existing in ("feature-packages-imported", "feature-packages-full"):
            assert existing in by_name
