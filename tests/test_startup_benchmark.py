"""Behavioral tests for benchmarks/startup_breakdown.py and startup-auto-default."""
from __future__ import annotations

import contextlib
import copy
import getpass
import importlib.util
import json
import os
import platform
import subprocess
import sys
from pathlib import Path

import pytest

PYTHON = sys.executable
_REPO = Path(__file__).resolve().parents[1]
_BREAKDOWN_SCRIPT = _REPO / "benchmarks" / "startup_breakdown.py"


@contextlib.contextmanager
def _loaded_module(mod_name: str, rel_path: str):
    """Load a script by repo-relative path and restore ``sys.path`` and ``sys.modules`` on exit."""
    path = _REPO / rel_path
    spec = importlib.util.spec_from_file_location(mod_name, path)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    saved_path = list(sys.path)
    saved_modules = dict(sys.modules)
    try:
        sys.modules[mod_name] = mod
        spec.loader.exec_module(mod)
        yield mod
    finally:
        sys.path[:] = saved_path
        for key in list(sys.modules):
            if key not in saved_modules:
                sys.modules.pop(key, None)
        for key, prev_mod in saved_modules.items():
            if sys.modules.get(key) is not prev_mod:
                sys.modules[key] = prev_mod


class TestStartupAutoDefaultScenario:
    """Verify benchmarks/scenarios.py exposes startup-auto-default alongside existing scenarios."""

    def test_startup_auto_default_registered(self):
        with _loaded_module("_test_scenarios_startup", "benchmarks/scenarios.py") as mod:
            scns = mod.all_scenarios()
        by_name = {s.name: s for s in scns}
        assert "startup-auto-default" in by_name
        scn = by_name["startup-auto-default"]
        assert scn.group == "startup"
        assert scn.mode == "auto"
        assert scn.workload == "noop.py"
        assert scn.config == {}
        # Existing startup scenarios remain intact.
        for existing in (
            "baseline-noop",
            "import-auto",
            "import-noauto",
            "import-nopatch",
            "import-noconsole",
            "import-minimal",
        ):
            assert existing in by_name


class TestBreakdownStatisticsAndRedaction:
    """Direct behavioral tests for small-n statistics and strict redaction."""

    def test_compute_stats_handles_empty_single_and_multi(self):
        with _loaded_module("_test_sb_stats", "benchmarks/startup_breakdown.py") as mod:
            st0 = mod.compute_stats([], failures=2)
            assert st0 == {
                "n": 0,
                "failures": 2,
                "median_ms": None,
                "mean_ms": None,
                "p95_ms": None,
                "stdev_ms": None,
                "iqr_ms": None,
            }

            st1 = mod.compute_stats([12.3456], failures=0)
            assert st1["n"] == 1
            assert st1["median_ms"] == 12.346
            assert st1["mean_ms"] == 12.346
            assert st1["p95_ms"] == 12.346
            assert st1["stdev_ms"] == 0.0
            assert st1["iqr_ms"] == 0.0

            st5 = mod.compute_stats([10.0, 20.0, 30.0, 40.0, 50.0], failures=1)
            assert st5["n"] == 5
            assert st5["failures"] == 1
            assert st5["median_ms"] == 30.0
            assert st5["mean_ms"] == 30.0
            assert st5["iqr_ms"] == 20.0
            assert st5["p95_ms"] == 48.0
            assert st5["stdev_ms"] > 0.0

    def test_redact_breakdown_scrubs_home_host_user_workdir_and_repo(self, tmp_path):
        with _loaded_module("_test_sb_redact", "benchmarks/startup_breakdown.py") as mod:
            with _loaded_module("_test_share_safety_sb", "benchmarks/share_safety.py") as ss:
                home = os.path.expanduser("~")
                user = getpass.getuser()
                host = platform.node() or "testhost"
                custom_workdir = str(tmp_path / "custom-shared-mount")

                raw = {
                    "schema": mod.SCHEMA_VERSION,
                    "environment": {
                        "hostname": host,
                        "username": user,
                        "workdir": custom_workdir,
                        "note": (
                            f"user={user} home={home}/x host={host} "
                            f"wd={custom_workdir} repo={_REPO}"
                        ),
                        "filesystem": {
                            "workdir": {"fstype": "ext4", "is_network": False},
                        },
                    },
                }
                red = mod.redact_breakdown(raw, extra_needles=[custom_workdir])
                blob = json.dumps(red)

                assert custom_workdir not in blob
                assert str(_REPO) not in blob
                if home and home != "~":
                    assert home not in blob
                if host and len(host) >= 3:
                    assert host not in blob
                if user and len(user) >= 3:
                    assert user not in blob
                assert red["environment"]["hostname"] == "<redacted>"
                assert red["environment"]["username"] == "<redacted>"
                assert red["environment"]["workdir"] == "<redacted>"
                assert red["environment"]["filesystem"]["workdir"]["fstype"] == "ext4"

                ok, reasons = ss.check_share_safe(red)
                assert ok, reasons

    def test_validate_redacted_output_rejects_leaked_home_path(self):
        with _loaded_module("_test_sb_val", "benchmarks/startup_breakdown.py") as mod:
            leaked_path = "/" + "home/" + "alice/secret/run"
            unsafe = {
                "schema": mod.SCHEMA_VERSION,
                "environment": {"note": f"leaked {leaked_path}"},
            }
            ok, reasons = mod.validate_redacted_output(unsafe)
            assert not ok
            assert reasons


class TestBreakdownCLIValidation:
    """Verify CLI flag validation rejects out-of-range values and invalid policies cleanly."""

    @pytest.mark.parametrize(
        "extra_args",
        [
            ["--iterations", "0"],
            ["--iterations", "-3"],
            ["--passes", "0"],
            ["--warmup", "-1"],
            ["--durability-policies", "bogus"],
            ["--durability-policies", "default,invalid"],
            ["--durability-policies", ""],
        ],
    )
    def test_invalid_flags_exit_nonzero(self, extra_args):
        proc = subprocess.run(
            [PYTHON, str(_BREAKDOWN_SCRIPT)] + extra_args,
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert proc.returncode != 0
        assert "error:" in proc.stderr.lower()

    def test_workdir_regular_file_rejected(self, tmp_path):
        not_a_dir = tmp_path / "regular.txt"
        not_a_dir.write_text("keep me", encoding="utf-8")
        proc = subprocess.run(
            [
                PYTHON,
                str(_BREAKDOWN_SCRIPT),
                "--iterations",
                "1",
                "--passes",
                "1",
                "--warmup",
                "0",
                "--workdir",
                str(not_a_dir),
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert proc.returncode != 0
        assert not_a_dir.read_text(encoding="utf-8") == "keep me"


@pytest.mark.slow
class TestBreakdownEndToEnd:
    """End-to-end subprocess CLI tests covering timings, phases, counters, layouts, and cleanup."""

    def test_cli_two_passes_two_iterations_and_workdir_cleanup(self, tmp_path):
        workdir = tmp_path / "bench-parent-xyz"
        workdir.mkdir()
        sibling = workdir / "keep-sibling.txt"
        sibling.write_text("pre-existing user file", encoding="utf-8")
        out_json = tmp_path / "breakdown.redacted.json"

        # Pollute child-affecting env vars to confirm isolation inside the benchmark.
        polluted_cfg = tmp_path / "polluted_xdg" / "pubrun"
        polluted_cfg.mkdir(parents=True)
        (polluted_cfg / "config.toml").write_text(
            '[core]\nauto_start = false\nimport_mode = "minimal"\n',
            encoding="utf-8",
        )
        env = dict(os.environ)
        env["PUBRUN_IMPORT_MODE"] = "minimal"
        env["PUBRUN_AUTO_START"] = "false"
        env["PUBRUN_PROFILE"] = "deep"
        env["XDG_CONFIG_HOME"] = str(tmp_path / "polluted_xdg")

        proc = subprocess.run(
            [
                PYTHON,
                str(_BREAKDOWN_SCRIPT),
                "--iterations",
                "2",
                "--passes",
                "2",
                "--warmup",
                "0",
                "--workdir",
                str(workdir),
                "--out",
                str(out_json),
            ],
            capture_output=True,
            text=True,
            env=env,
            timeout=240,
        )
        assert proc.returncode == 0, proc.stderr
        assert out_json.is_file()

        # Verify --workdir cleanup removed only the ephemeral subdir and preserved sibling.
        assert sibling.is_file()
        assert sibling.read_text(encoding="utf-8") == "pre-existing user file"
        assert list(workdir.iterdir()) == [sibling]

        data = json.loads(out_json.read_text(encoding="utf-8"))
        assert data["schema"] == "pubrun-startup-breakdown/1"
        assert data["config"]["iterations"] == 2
        assert data["config"]["passes"] == 2
        assert data["config"]["warmup"] == 0
        assert data["config"]["custom_workdir"] is True

        # Environment and filesystem metadata (no raw path or mount_point fields).
        env_meta = data["environment"]
        assert {"os", "python_version", "cpu", "git_commit", "filesystem"} <= set(env_meta)
        fs = env_meta["filesystem"]
        for key in ("workdir", "tmpdir", "pubrun_install"):
            assert key in fs
            assert "fstype" in fs[key]
            assert "is_network" in fs[key]
            assert "path" not in fs[key]
            assert "mount_point" not in fs[key]

        # Expected scenarios across baselines, import layouts, auto, and phased.
        scns = data["scenarios"]
        expected_scenarios = {
            "bare-python-noop",
            "bare-python-cpu-burn",
            "import-minimal-checkout",
            "import-minimal-installed",
            "import-minimal-installed-nested",
            "import-noauto-checkout",
            "import-noauto-installed",
            "import-noauto-installed-nested",
            "auto-noop-default",
            "phased-noop-default",
            "auto-cpu-burn-default",
            "phased-cpu-burn-default",
        }
        assert expected_scenarios <= set(scns)

        # Verify cold (pass 1) and warm (pass 2) stats on every scenario.
        for name in expected_scenarios:
            passes = scns[name]["passes"]
            assert len(passes) == 2
            assert passes[0]["pass"] == 1 and passes[0]["label"] == "cold"
            assert passes[1]["pass"] == 2 and passes[1]["label"] == "warm"
            for p in passes:
                assert p["n"] == 2
                assert p["failures"] == 0
                for stat_key in ("median_ms", "mean_ms", "p95_ms", "stdev_ms", "iqr_ms"):
                    assert isinstance(p[stat_key], (int, float))
                    assert p[stat_key] >= 0.0

        # Verify separate import, startup, workload, and finalization phases.
        for phased_name in ("phased-noop-default", "phased-cpu-burn-default"):
            for p in scns[phased_name]["passes"]:
                phases = p["phases"]
                for ph_key in ("import", "startup", "workload", "finalization"):
                    assert ph_key in phases
                    assert phases[ph_key]["n"] == 2
                    assert phases[ph_key]["median_ms"] >= 0.0

        # Verify instrumented counters on auto and phased runs (confirming isolation worked).
        for run_name in (
            "auto-noop-default",
            "phased-noop-default",
            "auto-cpu-burn-default",
            "phased-cpu-burn-default",
        ):
            c = scns[run_name]["counters"]
            assert c["git_spawns"] >= 1
            assert c["manifest_writes"] >= 2
            assert c["config_writes"] >= 1
            assert c["fsync_total"] >= 1
            assert c["writer_json_calls"] >= 2
            assert c["writer_json_ms"] >= 0.0

        # Verify import-only counter presence across checkout, installed, and nested layouts.
        for imp_name in (
            "import-minimal-checkout",
            "import-minimal-installed",
            "import-minimal-installed-nested",
            "import-noauto-checkout",
            "import-noauto-installed",
            "import-noauto-installed-nested",
        ):
            c = scns[imp_name]["counters"]
            assert isinstance(c["git_spawns"], int) and c["git_spawns"] >= 0
            assert c["manifest_writes"] == 0

        # Verify short and long workload absolute ms and relative overhead %.
        default_ov = data["overhead_summary"]["default"]
        for bucket in ("short", "long"):
            assert len(default_ov[bucket]["passes"]) == 2
            for row in default_ov[bucket]["passes"]:
                assert isinstance(row["absolute_overhead_ms"], (int, float))
                assert isinstance(row["relative_overhead_pct"], (int, float))
                assert isinstance(row["fixed_import_ms"], (int, float))
                assert isinstance(row["fixed_startup_ms"], (int, float))
                assert isinstance(row["fixed_finalization_ms"], (int, float))

        # Verify strict redaction and check_share_safe on JSON and stdout Markdown.
        with _loaded_module("_test_share_safety_e2e", "benchmarks/share_safety.py") as ss:
            ok, reasons = ss.check_share_safe(data)
        assert ok, reasons
        raw_json_text = out_json.read_text(encoding="utf-8")
        combined = raw_json_text + "\n" + proc.stdout
        assert str(workdir) not in combined
        assert str(_REPO) not in combined
        home = os.path.expanduser("~")
        if home and home != "~":
            assert home not in combined
        host = platform.node()
        if host and len(host) >= 3:
            assert host not in combined

    def test_cli_single_iteration_and_explicit_durability_policy(self, tmp_path):
        out_json = tmp_path / "single.json"
        proc = subprocess.run(
            [
                PYTHON,
                str(_BREAKDOWN_SCRIPT),
                "--iterations",
                "1",
                "--passes",
                "1",
                "--warmup",
                "0",
                "--durability-policies",
                "default,fsync",
                "--out",
                str(out_json),
            ],
            capture_output=True,
            text=True,
            timeout=180,
        )
        assert proc.returncode == 0, proc.stderr
        data = json.loads(out_json.read_text(encoding="utf-8"))
        assert data["config"]["durability_policies"] == ["default", "fsync"]
        assert "auto-noop-default" in data["scenarios"]
        assert "auto-noop-fsync" in data["scenarios"]
        assert "fsync" in data["overhead_summary"]

        p0 = data["scenarios"]["bare-python-noop"]["passes"][0]
        assert p0["n"] == 1
        assert p0["stdev_ms"] == 0.0
        assert p0["iqr_ms"] == 0.0
        assert p0["p95_ms"] == p0["median_ms"]

    def test_cli_does_not_autostart_pubrun_in_caller_cwd_and_accepts_short_relative_workdir(
        self, tmp_path
    ):
        caller_cwd = tmp_path / "clean_caller_cwd"
        caller_cwd.mkdir()
        rel_workdir = caller_cwd / "tmp"
        rel_workdir.mkdir()

        # Strip any PUBRUN_* overrides so default auto-start would trigger if the parent
        # benchmark script accidentally imported root `pubrun` instead of `pubrun.minimal`.
        clean_env = {k: v for k, v in os.environ.items() if not k.startswith("PUBRUN_")}
        proc = subprocess.run(
            [
                PYTHON,
                str(_BREAKDOWN_SCRIPT),
                "--iterations",
                "1",
                "--passes",
                "1",
                "--warmup",
                "0",
                "--workdir",
                "tmp",
            ],
            cwd=str(caller_cwd),
            env=clean_env,
            capture_output=True,
            text=True,
            timeout=180,
        )
        assert proc.returncode == 0, proc.stderr
        # No `runs/` directory or stray artifacts created in caller_cwd, and `tmp/` is empty again.
        assert [p.name for p in caller_cwd.iterdir()] == ["tmp"]
        assert list(rel_workdir.iterdir()) == []


def _strip_markers(text: str) -> str:
    return text.replace("<redacted>", "")


class TestBreakdownScrubBoundaries:
    """A short username must not corrupt `<redacted>` markers, the schema, or fixed metadata."""

    @staticmethod
    def _patch_identity(monkeypatch, mod, user: str) -> None:
        monkeypatch.setattr(mod.getpass, "getuser", lambda: user)
        monkeypatch.setattr(mod.platform, "node", lambda: "box")
        for key in ("USER", "USERNAME", "LOGNAME"):
            monkeypatch.setenv(key, user)
        monkeypatch.setenv("HOME", "/nonexistent-home-for-test")
        monkeypatch.setenv("USERPROFILE", "/nonexistent-home-for-test")

    @pytest.mark.parametrize("user", ["ed", "pub", "run", "startup", "benchmark"])
    def test_redact_breakdown_keeps_markers_schema_and_metadata(self, monkeypatch, user):
        with _loaded_module("_test_sb_boundary_" + user, "benchmarks/startup_breakdown.py") as mod:
            self._patch_identity(monkeypatch, mod, user)
            raw = {
                "schema": mod.SCHEMA_VERSION,
                "environment": {
                    "hostname": "box",
                    "os": {"release": f"6.8.0-{user}"},
                    "note": f"started by {user} in /data/{user}/work; marked as edited",
                    "pubrun_version": "1.0.0",
                },
                "scenarios": {
                    "import-minimal-installed-nested": {
                        "workload": "noop.py",
                        "layout": "installed-nested",
                        "passes": [{"pass": 1, "label": "cold"}],
                    },
                },
            }
            red = mod.redact_breakdown(raw)

            assert red["schema"] == mod.SCHEMA_VERSION
            scn = red["scenarios"]["import-minimal-installed-nested"]
            assert scn["workload"] == "noop.py"
            assert scn["layout"] == "installed-nested"
            assert scn["passes"][0]["label"] == "cold"
            assert red["environment"]["hostname"] == "<redacted>"
            assert red["environment"]["os"]["release"] == "6.8.0-<redacted>"
            assert red["environment"]["note"] == (
                "started by <redacted> in /data/<redacted>/work; marked as edited"
            )
            leftover = _strip_markers(json.dumps(red))
            assert "<" not in leftover and ">" not in leftover

            assert mod.validate_redacted_output(red) == (True, [])

    def test_scrub_text_keeps_existing_marker_and_redacts_standalone_user(self, monkeypatch):
        with _loaded_module("_test_sb_boundary_text_ed", "benchmarks/startup_breakdown.py") as mod:
            self._patch_identity(monkeypatch, mod, "ed")
            out = mod.scrub_text("host <redacted> run by ed, edited")
            assert out == "host <redacted> run by <redacted>, edited"

    def test_scrub_text_keeps_schema_line(self, monkeypatch):
        with _loaded_module(
            "_test_sb_boundary_text_startup", "benchmarks/startup_breakdown.py"
        ) as mod:
            self._patch_identity(monkeypatch, mod, "startup")
            line = "- Schema: `pubrun-startup-breakdown/1`"
            assert mod.scrub_text(line) == line

    def test_validate_refuses_standalone_username(self, monkeypatch):
        with _loaded_module("_test_sb_boundary_val_pub", "benchmarks/startup_breakdown.py") as mod:
            self._patch_identity(monkeypatch, mod, "pub")
            ok, reasons = mod.validate_redacted_output(
                {"schema": mod.SCHEMA_VERSION, "environment": {"note": "owner pub"}}
            )
            assert ok is False
            assert "identifying substring remains in JSON payload" in reasons

    @pytest.mark.slow
    @pytest.mark.parametrize("user", ["pub", "ed"])
    def test_cli_with_short_username_emits_intact_output(self, tmp_path, user):
        out_json = tmp_path / f"breakdown-{user}.json"
        env = dict(os.environ)
        for key in ("LOGNAME", "USER", "USERNAME"):
            env[key] = user
        proc = subprocess.run(
            [
                PYTHON,
                str(_BREAKDOWN_SCRIPT),
                "--iterations",
                "1",
                "--passes",
                "1",
                "--warmup",
                "0",
                "--out",
                str(out_json),
            ],
            capture_output=True,
            text=True,
            env=env,
            timeout=180,
        )
        assert proc.returncode == 0, proc.stderr
        text = out_json.read_text(encoding="utf-8")
        data = json.loads(text)
        assert data["schema"] == "pubrun-startup-breakdown/1"
        layouts = {scn["layout"] for scn in data["scenarios"].values()}
        assert layouts == {"checkout", "installed", "installed-nested", "none"}
        assert "import-minimal-installed-nested" in proc.stdout
        for blob in (text, proc.stdout):
            leftover = _strip_markers(blob)
            assert "<" not in leftover and ">" not in leftover
