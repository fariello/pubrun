"""pytest-benchmark micro-suite and schema/5 contract tests for pubrun.

This file is NOT collected by the default `pytest` run: the project sets
`testpaths = ["tests"]`, so a bare `pytest` never looks in `benchmarks/`.

Run the micro-benchmarks explicitly (requires `pip install -e .[bench]`):

    pytest benchmarks/ --benchmark-only
"""
import builtins
import contextlib
import copy
import importlib.util
import json
import math
import sys
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[1]


@contextlib.contextmanager
def _load(mod_name: str, rel: str):
    before_path = list(sys.path)
    before_modules = dict(sys.modules)
    path = _REPO / rel
    spec = importlib.util.spec_from_file_location(mod_name, path)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules[mod_name] = mod
    try:
        spec.loader.exec_module(mod)
    except Exception:
        sys.path[:] = before_path
        for name in list(sys.modules):
            if name not in before_modules:
                sys.modules.pop(name, None)
        for name, prev in before_modules.items():
            if sys.modules.get(name) is not prev:
                sys.modules[name] = prev
        raise
    added_during_load = [name for name in sys.modules if name not in before_modules]
    overwritten_during_load = {
        name: prev
        for name, prev in before_modules.items()
        if sys.modules.get(name) is not prev
    }
    try:
        yield mod
    finally:
        sys.path[:] = before_path
        for name in added_during_load:
            sys.modules.pop(name, None)
        for name, prev in overwritten_during_load.items():
            sys.modules[name] = prev


@pytest.fixture(scope="module")
def schema5_run(tmp_path_factory):
    """Execute the schema/5 harness once per module for read-only shape and conformance tests."""
    work_dir = tmp_path_factory.mktemp("schema5_run")
    out = work_dir / "r.unredacted.json"
    with _load("_bench_harness_s5", "benchmarks/harness.py") as h:
        # 2 iters x 1 pass + baseline: fast, exercises the full shape once.
        result = h.run(2, out, passes=1, mode="default", baseline_pass=True)
        on_disk = json.loads(out.read_text(encoding="utf-8"))
        yield h, out, result, on_disk


# --------------------------------------------------------------- child env isolation (BUG-E5)

class TestBenchChildEnvIsolation:
    """Ambient PUBRUN_* variables must not leak into benchmark child environments."""

    def test_ambient_pubrun_vars_stripped_while_preserving_scenario_env(
        self, monkeypatch, tmp_path
    ):
        ambient = {
            "PUBRUN_OUTPUT_DIR": str(tmp_path / "ambient-out"),
            "PUBRUN_RUN_MODE_OVERRIDE": "minimal",
            "PUBRUN_PROFILE": "ambient-profile",
            "PUBRUN_AUTO_START": "0",
            "PUBRUN_BENCH_IO_TARGET": str(tmp_path / "ambient-io"),
        }
        for key, value in ambient.items():
            monkeypatch.setenv(key, value)
        monkeypatch.setenv("PUBRUN_TEST_SENTINEL", "must-be-stripped")
        monkeypatch.setenv("UNRELATED_BENCH_TEST_VAR", "keep-me")

        with _load("_bench_harness_env_iso", "benchmarks/harness.py") as h:
            child_env = h._child_env_with_checkout_src()
            for key in (*ambient, "PUBRUN_TEST_SENTINEL"):
                assert key not in child_env
            assert child_env["UNRELATED_BENCH_TEST_VAR"] == "keep-me"

            scns_by_name = {s.name: s for s in h._scenarios.all_scenarios()}

            # Pubrun-active scenario keeps PUBRUN_IMPORT_MODE and drops all ambient PUBRUN_*.
            auto_scn = scns_by_name["import-auto"]
            _argv_auto, env_auto = h._build_child_command(auto_scn, tmp_path)
            assert env_auto["PUBRUN_IMPORT_MODE"] == "auto"
            for key in (*ambient, "PUBRUN_TEST_SENTINEL"):
                assert key not in env_auto

            # Scenario with explicit scn.env keeps its explicit PUBRUN_BENCH_IO_TARGET.
            devnull_scn = scns_by_name["io-baseline-devnull"]
            _argv_devnull, env_devnull = h._build_child_command(devnull_scn, tmp_path)
            assert env_devnull["PUBRUN_BENCH_IO_TARGET"] == devnull_scn.env["PUBRUN_BENCH_IO_TARGET"]
            assert env_devnull["PUBRUN_BENCH_IO_TARGET"] != ambient["PUBRUN_BENCH_IO_TARGET"]
            for key in (
                "PUBRUN_OUTPUT_DIR",
                "PUBRUN_RUN_MODE_OVERRIDE",
                "PUBRUN_PROFILE",
                "PUBRUN_AUTO_START",
                "PUBRUN_IMPORT_MODE",
                "PUBRUN_TEST_SENTINEL",
            ):
                assert key not in env_devnull

            # Baseline scenario without scn.env does not inherit ambient PUBRUN_BENCH_IO_TARGET.
            tmpdir_scn = scns_by_name["io-baseline-tmpdir"]
            _argv_tmpdir, env_tmpdir = h._build_child_command(tmpdir_scn, tmp_path)
            for key in (*ambient, "PUBRUN_TEST_SENTINEL"):
                assert key not in env_tmpdir

            # _run_pass sets PUBRUN_PROFILE="default" unconditionally and strips ambient PUBRUN_*.
            pass_envs = []

            def _capture_pass(argv, env, cwd):
                pass_envs.append(dict(env))
                return 0.001

            harness_target = getattr(h, "_shim_target", h)
            monkeypatch.setattr(h._scenarios, "all_scenarios", lambda: [auto_scn])
            monkeypatch.setattr(harness_target, "_time_once", _capture_pass)
            h._run_pass(1, iterations=1, warmup=0, workdir=tmp_path / "measured")
            assert len(pass_envs) == 1
            assert pass_envs[0]["PUBRUN_PROFILE"] == "default"
            assert pass_envs[0]["PUBRUN_IMPORT_MODE"] == "auto"
            for key in (
                "PUBRUN_OUTPUT_DIR",
                "PUBRUN_RUN_MODE_OVERRIDE",
                "PUBRUN_AUTO_START",
                "PUBRUN_BENCH_IO_TARGET",
                "PUBRUN_TEST_SENTINEL",
            ):
                assert key not in pass_envs[0]

            # _run_baseline_pass strips ambient PUBRUN_* while preserving explicit scn.env.
            baseline_envs = {}

            def _capture_baseline(argv, env, cwd):
                baseline_envs[cwd.name] = dict(env)
                return 0.001

            monkeypatch.setattr(h._scenarios, "all_scenarios", lambda: [devnull_scn, tmpdir_scn])
            monkeypatch.setattr(harness_target, "_time_once", _capture_baseline)
            h._run_baseline_pass(iterations=1, warmup=0, workdir=tmp_path / "baseline")
            assert (
                baseline_envs["io-baseline-devnull"]["PUBRUN_BENCH_IO_TARGET"]
                == devnull_scn.env["PUBRUN_BENCH_IO_TARGET"]
            )
            assert "PUBRUN_OUTPUT_DIR" not in baseline_envs["io-baseline-devnull"]
            assert "PUBRUN_BENCH_IO_TARGET" not in baseline_envs["io-baseline-tmpdir"]
            assert "PUBRUN_PROFILE" not in baseline_envs["io-baseline-tmpdir"]


# --------------------------------------------------------------- schema/5 result shape

class TestSchema5Shape:
    """The compact, non-redundant schema/5 result (IPD 20260720): defines scenarios once,
    stores raw 6-dp timings grouped per pass, drops recomputable stats, both timestamps."""

    @pytest.mark.slow
    def test_schema_is_v5(self, schema5_run):
        _h, _out, result, on_disk = schema5_run
        assert result["schema"] == "pubrun-benchmark/5"
        assert on_disk["schema"] == "pubrun-benchmark/5"

    @pytest.mark.slow
    def test_compact_no_indent(self, schema5_run):
        _h, out, _r, _d = schema5_run
        text = out.read_text(encoding="utf-8")
        assert "\n" not in text.rstrip("\n")          # single line -> compact
        assert ": " not in text and '",\n' not in text  # no pretty separators

    @pytest.mark.slow
    def test_scenario_defs_present_and_no_top_scenarios(self, schema5_run):
        _h, _out, _result, on_disk = schema5_run
        assert "scenario_defs" in on_disk and on_disk["scenario_defs"]
        assert "scenarios" not in on_disk           # the schema/1 alias is gone (PR-001)
        d = next(iter(on_disk["scenario_defs"].values()))
        assert {"group", "mode", "workload", "config"} <= set(d)
        # Static defs are defined ONCE (not repeated inside a pass).
        p0 = on_disk["pass_results"][0]
        assert set(p0.keys()) <= {"pass", "pass_env", "timings", "failures", "skipped"}

    @pytest.mark.slow
    def test_both_timestamps_present(self, schema5_run):
        _h, _out, _r, on_disk = schema5_run
        assert "generated_utc" in on_disk and on_disk["generated_utc"].endswith("+00:00")
        gl = on_disk["generated_local"]
        # local ISO-8601 WITH offset (not 'Z', not naive): last 6 chars are +HH:MM / -HH:MM.
        assert gl[-6] in "+-" and gl[-3] == ":"

    @pytest.mark.slow
    def test_timings_rounded_6dp_and_grouped_by_pass(self, schema5_run):
        _h, _out, _r, on_disk = schema5_run
        tim = on_disk["pass_results"][0]["timings"]
        assert tim, "a measured pass should have timings"
        for samples in tim.values():
            for v in samples:
                assert round(v, 6) == v            # stored at 6 dp

    @pytest.mark.slow
    def test_no_stored_stats(self, schema5_run):
        _h, _out, _r, on_disk = schema5_run
        # No derived-stat fields anywhere in a pass entry (recomputable from timings).
        blob = json.dumps(on_disk["pass_results"][0])
        for k in ("median_s", "mean_s", "p95_s", "stdev_s", "min_s", "max_s"):
            assert f'"{k}"' not in blob

    @pytest.mark.slow
    def test_baseline_same_compact_shape(self, schema5_run):
        _h, _out, _r, on_disk = schema5_run
        b = on_disk["baseline"]
        assert b["pass"] == 0 and b["uncaptured"] is True
        assert set(b.keys()) <= {"pass", "uncaptured", "pass_env", "timings", "failures", "skipped"}
        assert "scenarios" not in b               # no per-scenario stats/descriptors

    @pytest.mark.slow
    def test_round_trips(self, schema5_run):
        _h, out, _r, on_disk = schema5_run
        assert json.loads(out.read_text(encoding="utf-8")) == on_disk


class TestSchema5AggregateParity:
    """PR-003 anti-regression: aggregate output from a /4 file (stored stats) and the
    equivalent /5 file (recomputed from timings) is identical within float tolerance."""

    def test_parity_from_same_timings(self):
        with (
            _load("_bench_agg_parity", "benchmarks/aggregate.py") as agg,
            _load("_bench_harness_parity", "benchmarks/harness.py") as h,
        ):
            # A hand-built pair from IDENTICAL timings: one in /4 shape (stored stats), one in /5.
            timings = {
                "baseline-noop": [0.010, 0.011, 0.012, 0.010, 0.013],
                "import-auto": [0.030, 0.031, 0.029, 0.032, 0.030],
            }
            defs = {
                "baseline-noop": {"group": "startup", "mode": "baseline", "workload": "noop.py"},
                "import-auto": {"group": "startup", "mode": "auto", "workload": "noop.py"},
            }
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
        with _load("_bench_agg_both", "benchmarks/aggregate.py") as agg:
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

_COMMITTED_REDACTED_SAMPLES = sorted(
    list((_REPO / "benchmarks" / "results").glob("*.redacted.json"))
    + list((_REPO / "benchmarks" / "data" / "accepted").glob("*.redacted.json")),
    key=lambda p: p.relative_to(_REPO).as_posix(),
)


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

    @pytest.mark.parametrize(
        "sample_path",
        _COMMITTED_REDACTED_SAMPLES or [None],
        ids=lambda p: p.relative_to(_REPO).as_posix() if p is not None else "missing",
    )
    def test_committed_redacted_sample_conforms(self, sample_path):
        """Each committed redacted /5 sample is a valid, real example (guards it from drift)."""
        assert _COMMITTED_REDACTED_SAMPLES and sample_path is not None, (
            "no committed *.redacted.json sample to validate"
        )
        v = self._validator()
        data = json.loads(sample_path.read_text(encoding="utf-8"))
        errs = sorted(v.iter_errors(data), key=lambda e: list(e.absolute_path))
        assert not errs, f"{sample_path.name} does not conform: " + \
            "; ".join(f"{list(e.absolute_path) or '[root]'}: {e.message}" for e in errs[:5])

    @pytest.mark.slow
    def test_fresh_result_and_redaction_conform(self, schema5_run):
        """A freshly-produced /5 result AND its redacted copy both validate."""
        v = self._validator()
        h, _out, result, _on_disk = schema5_run
        assert not list(v.iter_errors(result)), "fresh unredacted /5 result does not conform"
        redacted = h.redact_result(result)
        assert not list(v.iter_errors(redacted)), "redacted /5 result does not conform"
        # redaction preserves the structure (schema-valid) while masking values
        assert redacted["schema"] == "pubrun-benchmark/5"

    @pytest.mark.slow
    def test_broken_result_is_rejected(self, schema5_run):
        """The schema has teeth: structural breakage fails validation."""
        v = self._validator()
        _h, _out, good, _on_disk = schema5_run
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
