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
import importlib.util
import json
import math
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[1]


def _load(mod_name: str, rel: str):
    path = _REPO / rel
    spec = importlib.util.spec_from_file_location(mod_name, path)
    mod = importlib.util.module_from_spec(spec)
    import sys as _sys
    _sys.modules[mod_name] = mod
    spec.loader.exec_module(mod)
    return mod


# --------------------------------------------------------------- schema/5 result shape

class TestSchema5Shape:
    """The compact, non-redundant schema/5 result (IPD 20260720): defines scenarios once,
    stores raw 6-dp timings grouped per pass, drops recomputable stats, both timestamps."""

    def _make(self, tmp_path):
        h = _load("_bench_harness_s5", "benchmarks/harness.py")
        out = tmp_path / "r.unredacted.json"
        # 2 iters x 1 pass + baseline: fast, but exercises the full shape.
        result = h.run(2, out, passes=1, mode="default", baseline_pass=True)
        on_disk = json.loads(out.read_text(encoding="utf-8"))
        return h, out, result, on_disk

    def test_schema_is_v5(self):
        import re
        src = (_REPO / "benchmarks" / "harness.py").read_text()
        assert re.search(r'"schema":\s*"pubrun-benchmark/5"', src)

    def test_compact_no_indent(self, tmp_path):
        _h, out, _r, _d = self._make(tmp_path)
        text = out.read_text(encoding="utf-8")
        assert "\n" not in text.rstrip("\n")          # single line -> compact
        assert ": " not in text and '",\n' not in text  # no pretty separators

    def test_scenario_defs_present_and_no_top_scenarios(self, tmp_path):
        _h, _out, result, on_disk = self._make(tmp_path)
        assert "scenario_defs" in on_disk and on_disk["scenario_defs"]
        assert "scenarios" not in on_disk           # the schema/1 alias is gone (PR-001)
        d = next(iter(on_disk["scenario_defs"].values()))
        assert {"group", "mode", "workload", "config"} <= set(d)
        # Static defs are defined ONCE (not repeated inside a pass).
        p0 = on_disk["pass_results"][0]
        assert set(p0.keys()) <= {"pass", "pass_env", "timings", "failures", "skipped"}

    def test_both_timestamps_present(self, tmp_path):
        _h, _out, _r, on_disk = self._make(tmp_path)
        assert "generated_utc" in on_disk and on_disk["generated_utc"].endswith("+00:00")
        gl = on_disk["generated_local"]
        # local ISO-8601 WITH offset (not 'Z', not naive): last 6 chars are +HH:MM / -HH:MM.
        assert gl[-6] in "+-" and gl[-3] == ":"

    def test_timings_rounded_6dp_and_grouped_by_pass(self, tmp_path):
        _h, _out, _r, on_disk = self._make(tmp_path)
        tim = on_disk["pass_results"][0]["timings"]
        assert tim, "a measured pass should have timings"
        for samples in tim.values():
            for v in samples:
                assert round(v, 6) == v            # stored at 6 dp

    def test_no_stored_stats(self, tmp_path):
        _h, _out, _r, on_disk = self._make(tmp_path)
        # No derived-stat fields anywhere in a pass entry (recomputable from timings).
        blob = json.dumps(on_disk["pass_results"][0])
        for k in ("median_s", "mean_s", "p95_s", "stdev_s", "min_s", "max_s"):
            assert f'"{k}"' not in blob

    def test_baseline_same_compact_shape(self, tmp_path):
        _h, _out, _r, on_disk = self._make(tmp_path)
        b = on_disk["baseline"]
        assert b["pass"] == 0 and b["uncaptured"] is True
        assert set(b.keys()) <= {"pass", "uncaptured", "pass_env", "timings", "failures", "skipped"}
        assert "scenarios" not in b               # no per-scenario stats/descriptors

    def test_round_trips(self, tmp_path):
        _h, out, _r, on_disk = self._make(tmp_path)
        assert json.loads(out.read_text(encoding="utf-8")) == on_disk


class TestSchema5AggregateParity:
    """PR-003 anti-regression: aggregate output from a /4 file (stored stats) and the
    equivalent /5 file (recomputed from timings) is identical within float tolerance."""

    def test_parity_from_same_timings(self):
        agg = _load("_bench_agg_parity", "benchmarks/aggregate.py")
        # A hand-built pair from IDENTICAL timings: one in /4 shape (stored stats), one in /5.
        timings = {
            "baseline-noop": [0.010, 0.011, 0.012, 0.010, 0.013],
            "import-auto": [0.030, 0.031, 0.029, 0.032, 0.030],
        }
        defs = {
            "baseline-noop": {"group": "startup", "mode": "baseline", "workload": "noop.py"},
            "import-auto": {"group": "startup", "mode": "auto", "workload": "noop.py"},
        }
        h = _load("_bench_harness_parity", "benchmarks/harness.py")
        scen4 = {}
        for name, t in timings.items():
            d = defs[name]
            scen4[name] = {**d, "config": {}, "failures": 0, "timings": list(t), **h._stats(t)}
        run4 = {"schema": "pubrun-benchmark/4", "machine": {}, "scenarios": scen4}
        run5 = {
            "schema": "pubrun-benchmark/5", "machine": {},
            "scenario_defs": {n: {**defs[n], "config": {}} for n in defs},
            "pass_results": [{"pass": 1, "pass_env": {},
                              "timings": {n: list(t) for n, t in timings.items()},
                              "failures": {n: 0 for n in timings}}],
        }
        r4 = {r["scenario"]: r for r in agg.build_rows([run4])}
        r5 = {r["scenario"]: r for r in agg.build_rows([run5])}
        assert set(r4) == set(r5)
        for name in r4:
            for f in ("median_ms", "p95_ms", "stdev_ms", "overhead_ms", "overhead_pct"):
                a, b = r4[name][f], r5[name][f]
                if a is None or b is None:
                    assert a == b
                else:
                    assert math.isclose(a, b, rel_tol=1e-9, abs_tol=1e-6), (name, f, a, b)
            assert r4[name]["n"] == r5[name]["n"]

    def test_aggregate_reads_both_versions(self):
        agg = _load("_bench_agg_both", "benchmarks/aggregate.py")
        run5 = {"schema": "pubrun-benchmark/5", "machine": {},
                "scenario_defs": {"baseline-noop": {"group": "startup", "mode": "baseline",
                                                    "workload": "noop.py", "config": {}}},
                "pass_results": [{"pass": 1, "pass_env": {},
                                  "timings": {"baseline-noop": [0.01, 0.02]},
                                  "failures": {"baseline-noop": 0}}]}
        run4 = {"schema": "pubrun-benchmark/4", "machine": {},
                "scenarios": {"baseline-noop": {"group": "startup", "mode": "baseline",
                                                "workload": "noop.py", "median_s": 0.015, "n": 2}}}
        assert agg.build_rows([run4])       # /4 still aggregates
        assert agg.build_rows([run5])       # /5 aggregates


# ------------------------------------------------- schema/5 JSON Schema conformance (IPD 20260720-1418)

class TestSchema5Conformance:
    """The published schemas/benchmark.schema.json must accept real /5 results (full AND
    redacted) and reject a broken one. Uses the dev-only jsonschema dependency."""

    _SCHEMA_PATH = _REPO / "schemas" / "benchmark.schema.json"

    def _validator(self):
        jsonschema = pytest.importorskip("jsonschema")
        schema = json.loads(self._SCHEMA_PATH.read_text(encoding="utf-8"))
        cls = jsonschema.validators.validator_for(schema)
        cls.check_schema(schema)  # the schema document itself is well-formed
        return cls(schema)

    def test_schema_is_well_formed(self):
        self._validator()  # raises if malformed

    def test_committed_redacted_sample_conforms(self):
        """The committed redacted /5 sample is a valid, real example (guards it from drift)."""
        v = self._validator()
        samples = sorted((_REPO / "benchmarks" / "results").glob("*.redacted.json"))
        assert samples, "no committed *.redacted.json sample to validate"
        for s in samples:
            data = json.loads(s.read_text(encoding="utf-8"))
            errs = sorted(v.iter_errors(data), key=lambda e: list(e.absolute_path))
            assert not errs, f"{s.name} does not conform: " + \
                "; ".join(f"{list(e.absolute_path) or '[root]'}: {e.message}" for e in errs[:5])

    def test_fresh_result_and_redaction_conform(self, tmp_path):
        """A freshly-produced /5 result AND its redacted copy both validate."""
        v = self._validator()
        h = _load("_bench_harness_conf", "benchmarks/harness.py")
        out = tmp_path / "r.unredacted.json"
        result = h.run(2, out, passes=1, mode="default", baseline_pass=True)
        assert not list(v.iter_errors(result)), "fresh unredacted /5 result does not conform"
        redacted = h.redact_result(result)
        assert not list(v.iter_errors(redacted)), "redacted /5 result does not conform"
        # redaction preserves the structure (schema-valid) while masking values
        assert redacted["schema"] == "pubrun-benchmark/5"

    def test_broken_result_is_rejected(self, tmp_path):
        """The schema has teeth: structural breakage fails validation."""
        v = self._validator()
        h = _load("_bench_harness_conf2", "benchmarks/harness.py")
        out = tmp_path / "r.unredacted.json"
        good = h.run(2, out, passes=1, mode="default", baseline_pass=True)
        import copy
        bad = copy.deepcopy(good); bad.pop("scenario_defs", None)   # required
        assert not v.is_valid(bad)
        bad2 = copy.deepcopy(good); bad2["schema"] = "pubrun-benchmark/4"  # wrong const
        assert not v.is_valid(bad2)
        bad3 = copy.deepcopy(good)
        name = next(iter(bad3["pass_results"][0]["timings"]))
        bad3["pass_results"][0]["timings"][name] = ["not-a-number"]   # timings must be numbers
        assert not v.is_valid(bad3)


# ---------------------------------------------------------- pytest-benchmark micro-suite
#
# The remaining tests need the optional [bench] extra; skip cleanly (per test) if it is
# absent so the schema-shape tests above still run without the extra installed. (This file is
# also not collected by a bare `pytest`, which only looks in tests/ per testpaths.)
_needs_benchmark = pytest.mark.skipif(
    importlib.util.find_spec("pytest_benchmark") is None,
    reason="requires the optional [bench] extra (pytest-benchmark)",
)


@_needs_benchmark
def test_bench_import_pubrun_cost(benchmark):
    """Cost of importing the pubrun capture config path (warm import)."""
    from pubrun.config import resolve_config
    benchmark(resolve_config)


@_needs_benchmark
def test_bench_builtin_open_read(benchmark, tmp_path):
    """Baseline: builtins.open read of a small buffer (no pubrun proxy)."""
    p = tmp_path / "data.bin"
    p.write_bytes(b"x" * (1024 * 1024))

    def read():
        with builtins.open(p, "rb") as f:
            while f.read(65536):
                pass

    benchmark(read)


@_needs_benchmark
def test_bench_pubrun_print(benchmark, capsys):
    """Cost of pubrun.print vs builtin (no active run -> minimal path)."""
    from pubrun.core import print as pubrun_print

    def loop():
        for _ in range(100):
            pubrun_print("x")

    benchmark(loop)
    capsys.readouterr()  # drain captured output
