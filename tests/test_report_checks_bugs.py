"""Regression tests for self-check, meta snapshot, and report rendering bugs (IPD ihh27o).

Covers BUG-16 (malformed TOML not reported), BUG-47 (findings dropped per check),
BUG-46 (PBS/SGE precedence), BUG-48 (writability walk on relative/nonexistent paths),
BUG-17 (meta depth flags inert), BUG-64a (literal "None" CPU model), BUG-49 (RSS chart
title vs plotted series), and BUG-65 (``host`` never hydrated from a parent meta.json).
"""
import json
import os
import shutil
import sys
from pathlib import Path

import pytest

from pubrun.report import checks
from pubrun.report import meta_snapshot
from pubrun.report.utils import hydrate_manifest, hydrate_manifest_with_report

_ALLOC_AND_MARKER_VARS = (
    "SLURM_JOB_ID", "PBS_JOBID", "LSB_JOBID", "JOB_ID", "PE_HOSTFILE",
    "SGE_ROOT", "SGE_O_HOST", "PBS_ENVIRONMENT", "PBS_O_HOST",
)


@pytest.fixture
def isolated_config(tmp_path, monkeypatch):
    """Point user and local config lookups at empty temp dirs; return (cwd, xdg)."""
    cwd = tmp_path / "proj"
    xdg = tmp_path / "xdg"
    cwd.mkdir()
    xdg.mkdir()
    monkeypatch.chdir(cwd)
    # conftest pins Path.cwd() to tmp_path for every test; follow the real chdir.
    monkeypatch.setattr("pathlib.Path.cwd", lambda: cwd)
    monkeypatch.setenv("XDG_CONFIG_HOME", str(xdg))
    monkeypatch.setenv("APPDATA", str(xdg))
    return cwd, xdg


def _codes(findings):
    return [f["code"] for f in findings]


# --------------------------------------------------------------------------- BUG-16

class TestMalformedConfigDetected:
    def test_valid_config_emits_no_config_invalid(self, isolated_config):
        cwd, _ = isolated_config
        (cwd / ".pubrun.toml").write_text('[core]\noutput_dir = "runs"\n', encoding="utf-8")
        assert "config_invalid" not in _codes(checks._install_health_findings())

    def test_malformed_root_pubrun_toml_warns(self, isolated_config):
        cwd, _ = isolated_config
        bad = cwd / ".pubrun.toml"
        bad.write_text("[core\noutput_dir = ", encoding="utf-8")
        found = [f for f in checks._install_health_findings() if f["code"] == "config_invalid"]
        assert len(found) == 1
        assert found[0]["severity"] == checks.WARN
        assert str(bad) in found[0]["message"]

    def test_malformed_local_config_dir_toml_warns(self, isolated_config):
        cwd, _ = isolated_config
        d = cwd / ".config" / "pubrun"
        d.mkdir(parents=True)
        bad = d / "config.toml"
        bad.write_text("not = = toml", encoding="utf-8")
        found = [f for f in checks._install_health_findings() if f["code"] == "config_invalid"]
        assert [f["severity"] for f in found] == [checks.WARN]
        assert str(bad) in found[0]["message"]

    def test_malformed_user_config_warns(self, isolated_config):
        _, xdg = isolated_config
        d = xdg / "pubrun"
        d.mkdir()
        bad = d / "config.toml"
        bad.write_text("[[[", encoding="utf-8")
        found = [f for f in checks._install_health_findings() if f["code"] == "config_invalid"]
        assert len(found) == 1
        assert str(bad) in found[0]["message"]

    def test_self_check_strict_exits_nonzero_on_malformed_config(self, isolated_config):
        import subprocess
        cwd, xdg = isolated_config
        (cwd / ".pubrun.toml").write_text("[core\n", encoding="utf-8")
        env = dict(os.environ)
        src_dir = Path(__file__).resolve().parents[1] / "src"
        env["PYTHONPATH"] = str(src_dir) + (os.pathsep + env["PYTHONPATH"] if env.get("PYTHONPATH") else "")
        env["XDG_CONFIG_HOME"] = str(xdg)
        env["NO_COLOR"] = "1"
        proc = subprocess.run(
            [sys.executable, "-m", "pubrun", "self-check", "--strict", "--json"],
            cwd=str(cwd), env=env, capture_output=True, text=True, timeout=120,
        )
        assert proc.returncode != 0, proc.stdout + proc.stderr
        data = json.loads(proc.stdout)
        assert "config_invalid" in _codes(data["findings"])
        cfg_checks = [c for c in data["checks"] if c["name"] == "config_valid"]
        assert cfg_checks and cfg_checks[0]["status"] == "warn"


# --------------------------------------------------------------------------- BUG-47

class TestLiveChecksKeepsEveryFinding:
    def test_multiple_filesystem_findings_each_get_a_check(self, monkeypatch):
        fake = [
            checks._finding(checks.WARN, "netfs_tmpdir", "tmp is on NFS.", "use local tmp"),
            checks._finding(checks.WARN, "netfs_output_dir", "output is on NFS.", "use local out"),
            checks._finding(checks.WARN, "fs_slow_pubrun_install", "install slow.", "move it"),
        ]
        monkeypatch.setattr(checks, "live_findings", lambda: list(fake))
        check_list, findings = checks.live_checks()
        assert findings == fake
        fs = [c for c in check_list if c["name"] == "filesystems"]
        assert [c["detail"] for c in fs] == [f["message"] for f in fake]
        assert all(c["status"] == "warn" for c in fs)
        # Every other catalog entry is still reported once as OK.
        others = [c for c in check_list if c["name"] != "filesystems"]
        assert len(others) == len(checks._CHECK_CATALOG) - 1
        assert all(c["status"] == "ok" for c in others)
        # Each detail matches exactly one finding message (what --show-suggestions keys on).
        msgs = {f["message"] for f in findings}
        assert all(c["detail"] in msgs for c in fs)

    def test_self_check_counts_every_warning(self, monkeypatch, capsys):
        from pubrun import __main__ as cli
        fake = [
            checks._finding(checks.WARN, "netfs_tmpdir", "tmp is on NFS.", "use local tmp"),
            checks._finding(checks.WARN, "netfs_output_dir", "output is on NFS.", "use local out"),
        ]
        monkeypatch.setattr(checks, "live_findings", lambda: list(fake))
        monkeypatch.setenv("NO_COLOR", "1")
        cli._run_self_check(show_suggestions=True, as_json=False, strict=False)
        out = capsys.readouterr().out
        assert "tmp is on NFS." in out and "output is on NFS." in out
        assert "-> use local tmp" in out and "-> use local out" in out
        assert "2 concern(s)" in out


# --------------------------------------------------------------------------- BUG-46

class TestSchedulerDisambiguation:
    @pytest.fixture(autouse=True)
    def _clean_env(self, monkeypatch):
        for v in _ALLOC_AND_MARKER_VARS:
            monkeypatch.delenv(v, raising=False)

    @staticmethod
    def _only(monkeypatch, tool):
        monkeypatch.setattr(shutil, "which", lambda t: f"/usr/bin/{t}" if t == tool else None)

    @pytest.mark.parametrize("var", ["JOB_ID", "PE_HOSTFILE"])
    def test_sge_compute_node_no_nudge(self, monkeypatch, var):
        self._only(monkeypatch, "qsub")
        monkeypatch.setenv("SGE_ROOT", "/opt/sge")
        monkeypatch.setenv(var, "123")
        assert checks._hpc_login_node_findings() == []

    def test_pbs_compute_node_no_nudge(self, monkeypatch):
        self._only(monkeypatch, "qsub")
        monkeypatch.setenv("PBS_JOBID", "99.server")
        assert checks._hpc_login_node_findings() == []

    def test_sge_login_node_labelled_sge(self, monkeypatch):
        self._only(monkeypatch, "qsub")
        monkeypatch.setenv("SGE_ROOT", "/opt/sge")
        out = checks._hpc_login_node_findings()
        assert len(out) == 1 and out[0]["severity"] == checks.INFO
        assert "SGE/Grid Engine" in out[0]["message"]
        assert "PBS" not in out[0]["message"]

    def test_pbs_login_node_labelled_pbs(self, monkeypatch):
        self._only(monkeypatch, "qsub")
        monkeypatch.setenv("PBS_O_HOST", "login1")
        out = checks._hpc_login_node_findings()
        assert len(out) == 1
        assert "PBS/Torque login node" in out[0]["message"]

    def test_qsub_without_markers_is_ambiguous(self, monkeypatch):
        self._only(monkeypatch, "qsub")
        out = checks._hpc_login_node_findings()
        assert len(out) == 1
        assert "PBS/Torque or SGE" in out[0]["message"]

    def test_slurm_and_lsf_still_detected(self, monkeypatch):
        self._only(monkeypatch, "sbatch")
        assert "Slurm" in checks._hpc_login_node_findings()[0]["message"]
        self._only(monkeypatch, "bsub")
        out = checks._hpc_login_node_findings()
        assert "LSF" in out[0]["message"] and out[0]["severity"] == checks.INFO

    def test_any_allocation_suppresses_even_other_scheduler_tools(self, monkeypatch):
        self._only(monkeypatch, "sbatch")
        monkeypatch.setenv("PBS_JOBID", "1")
        assert checks._hpc_login_node_findings() == []


# --------------------------------------------------------------------------- BUG-48

class TestOutputWritability:
    def _with_output_dir(self, monkeypatch, value):
        real = checks._live_paths

        def fake():
            p = real()
            p["output_dir"] = value
            return p
        monkeypatch.setattr(checks, "_live_paths", fake)

    @pytest.mark.skipif(sys.platform == "win32" or (hasattr(os, "geteuid") and os.geteuid() == 0),
                        reason="POSIX permission semantics; root bypasses W_OK")
    def test_relative_nested_path_checked_against_readonly_cwd(self, isolated_config, monkeypatch):
        cwd, _ = isolated_config
        self._with_output_dir(monkeypatch, os.path.join("a", "b", "runs"))
        os.chmod(cwd, 0o555)
        try:
            found = [f for f in checks._install_health_findings()
                     if f["code"] == "output_not_writable"]
        finally:
            os.chmod(cwd, 0o755)
        assert len(found) == 1 and found[0]["severity"] == checks.WARN

    def test_relative_nested_path_writable_cwd_ok(self, isolated_config, monkeypatch):
        self._with_output_dir(monkeypatch, os.path.join("a", "b", "runs"))
        assert "output_not_writable" not in _codes(checks._install_health_findings())

    def test_nonexistent_root_terminates_and_warns(self, isolated_config, monkeypatch):
        # Simulate a root that does not exist (e.g. a missing Windows drive letter): every
        # path is reported missing, so the walk must stop at dirname()'s fixed point.
        self._with_output_dir(monkeypatch, os.path.join(os.sep, "nope", "runs"))
        monkeypatch.setattr(checks.os.path, "exists", lambda p: False)
        monkeypatch.setattr(checks.os.path, "isdir", lambda p: False)
        found = [f for f in checks._install_health_findings()
                 if f["code"] == "output_not_writable"]
        assert len(found) == 1 and found[0]["severity"] == checks.WARN


# --------------------------------------------------------------------------- BUG-17 / 64a

@pytest.fixture
def recorded_meta(monkeypatch):
    """Replace collectors with recorders returning minimal data; return captured cfgs."""
    seen = {}

    def make(name, data):
        def fn(cfg):
            seen[name] = cfg
            return data
        return fn

    monkeypatch.setattr(meta_snapshot, "get_hardware", make(
        "hardware", {"cpu": {"model": "EPYC"}, "capture_state": {"status": "complete"}}))
    monkeypatch.setattr(meta_snapshot, "get_python_runtime", make(
        "python", {"version": "3.11.8", "capture_state": {"status": "complete"}}))
    monkeypatch.setattr(meta_snapshot, "get_packages", make(
        "packages", {"records": [], "capture_state": {"status": "complete"}}))
    monkeypatch.setattr(meta_snapshot, "get_git", make(
        "git", {"commit": None, "capture_state": {"status": "complete"}}))
    monkeypatch.setattr(meta_snapshot, "get_environment", make(
        "environment", {"variables": [], "capture_state": {"status": "complete"}}))
    monkeypatch.setattr(meta_snapshot, "get_host", make(
        "host", {"hostname": "h", "os_name": "Linux", "capture_state": {"status": "complete"}}))
    return seen


class TestMetaSnapshotDepth:
    def test_depths_map_to_distinct_capture_config(self, tmp_path, recorded_meta, capsys):
        results = {}
        for depth in ("basic", "standard", "deep"):
            recorded_meta.clear()
            meta_snapshot.generate_meta_snapshot(str(tmp_path / f"{depth}.json"), depth)
            cap = recorded_meta["hardware"]["capture"]
            results[depth] = cap
            for name in ("hardware", "python", "packages", "git", "environment", "host"):
                assert recorded_meta[name]["capture"]["hardware"]["depth"] == depth
        b, s, d = results["basic"], results["standard"], results["deep"]
        assert b["environment"]["mode"] == "off" and b["packages"]["mode"] == "off"
        assert b["git"]["check_dirty"] is False
        assert b["hardware"]["capture_gpu_clock_speed"] is False
        assert s["environment"]["mode"] == "filtered"
        assert s["packages"]["mode"] == "top-level-installed"
        assert s["git"]["check_dirty"] is True
        assert s["hardware"]["capture_gpu_clock_speed"] is False
        assert d["environment"]["mode"] == "filtered"
        assert d["packages"]["mode"] == "full-environment"
        assert d["hardware"]["capture_gpu_clock_speed"] is True
        for cap in (b, s, d):
            assert cap["host"]["depth"] == cap["hardware"]["depth"]
            assert cap["python"]["depth"] == cap["hardware"]["depth"]

    def test_no_deprecated_core_profile_override(self, tmp_path, monkeypatch, recorded_meta, capsys):
        seen_overrides = []
        real = meta_snapshot.resolve_config

        def spy(overrides=None):
            seen_overrides.append(overrides)
            return real(overrides)
        monkeypatch.setattr(meta_snapshot, "resolve_config", spy)
        meta_snapshot.generate_meta_snapshot(str(tmp_path / "m.json"), "standard")
        assert seen_overrides and "core" not in seen_overrides[0]

    @pytest.mark.parametrize("bad", ["", "full", "DEEP", None])
    def test_invalid_depth_rejected(self, tmp_path, bad, capsys):
        with pytest.raises(ValueError):
            meta_snapshot.generate_meta_snapshot(str(tmp_path / "m.json"), bad)
        assert not (tmp_path / "m.json").exists()

    def test_basic_real_capture_suppresses_env_and_packages(self, tmp_path, monkeypatch, capsys):
        # Real environment/packages collectors; heavy ones stubbed for speed.
        monkeypatch.setattr(meta_snapshot, "get_hardware",
                            lambda cfg: {"cpu": {"model": "x"}, "capture_state": {"status": "complete"}})
        monkeypatch.setattr(meta_snapshot, "get_git",
                            lambda cfg: {"capture_state": {"status": "complete"}})
        out = tmp_path / "m.json"
        meta_snapshot.generate_meta_snapshot(str(out), "basic")
        data = json.loads(out.read_text(encoding="utf-8"))
        assert data["environment"]["capture_state"]["status"] == "suppressed"
        assert data["packages"]["capture_state"]["status"] == "suppressed"
        text = capsys.readouterr().out
        env_line = [ln for ln in text.splitlines() if "environment:" in ln][0]
        assert "[WARN" not in env_line and "[INFO" in env_line

    def test_deep_preserves_secret_redaction(self, tmp_path, monkeypatch, capsys):
        monkeypatch.setenv("PUBRUN_TEST_SECRET_TOKEN", "hunter2-do-not-leak")
        monkeypatch.setattr(meta_snapshot, "get_hardware",
                            lambda cfg: {"cpu": {"model": "x"}, "capture_state": {"status": "complete"}})
        monkeypatch.setattr(meta_snapshot, "get_git",
                            lambda cfg: {"capture_state": {"status": "complete"}})
        monkeypatch.setattr(meta_snapshot, "get_packages",
                            lambda cfg: {"records": [], "capture_state": {"status": "complete"}})
        out = tmp_path / "m.json"
        meta_snapshot.generate_meta_snapshot(str(out), "deep")
        raw = out.read_text(encoding="utf-8")
        assert "hunter2-do-not-leak" not in raw
        data = json.loads(raw)
        assert data["environment"]["mode"] == "filtered"
        rec = [v for v in data["environment"]["variables"] if v["name"] == "PUBRUN_TEST_SECRET_TOKEN"]
        assert rec and rec[0]["value"]["representation"] in ("redacted", "hashed")

    def test_null_cpu_model_prints_unknown(self, tmp_path, monkeypatch, recorded_meta, capsys):
        monkeypatch.setattr(meta_snapshot, "get_hardware",
                            lambda cfg: {"cpu": {"model": None}, "capture_state": {"status": "complete"}})
        meta_snapshot.generate_meta_snapshot(str(tmp_path / "m.json"), "basic")
        line = [ln for ln in capsys.readouterr().out.splitlines() if "hardware:" in ln][0]
        assert "unknown" in line and "None" not in line


# --------------------------------------------------------------------------- BUG-64a pins

def _report_manifest(tmp_path, cpu_model=None):
    m = {
        "schema_version": "1.0",
        "manifest_type": "pubrun-manifest",
        "run": {"run_id": "r1"},
        "timing": {"started_at_utc": 1780250000.0, "ended_at_utc": 1780250060.0, "elapsed_seconds": 60.0},
        "invocation": {"argv": ["t.py"], "script": {"basename": "t.py"}},
        "status": {"outcome": "completed", "capture_state": {"status": "complete"}},
        "python": {"version": "3.11.5", "capture_state": {"status": "complete"}},
        "git": {"commit": "abc", "branch": "main", "dirty": False, "capture_state": {"status": "complete"}},
        "hardware": {"cpu": {"model": cpu_model, "architecture": "aarch64"},
                     "memory_total_bytes": 8 * 1024**3, "capture_state": {"status": "complete"}},
        "host": {"os_name": "Linux", "os_version": "6.8.0", "hostname": "arm-01",
                 "capture_state": {"status": "complete"}},
        "packages": {"records": [], "capture_state": {"status": "complete"}},
        "environment": {"variables": [], "capture_state": {"status": "complete"}},
        "resources": {"capture_state": {"status": "suppressed"}},
        "meta_ref": None,
    }
    run_dir = tmp_path / "runs" / "pubrun-r1"
    run_dir.mkdir(parents=True)
    p = run_dir / "manifest.json"
    p.write_text(json.dumps(m), encoding="utf-8")
    return m, str(p)


class TestNullCpuModelPins:
    def test_methods_reports_never_render_none(self, tmp_path):
        from pubrun.report.methods import generate_report, generate_report_multi
        m, _ = _report_manifest(tmp_path)
        for fmt in ("markdown", "latex"):
            assert "None" not in generate_report(m, fmt)
            assert "None" not in generate_report_multi([m, dict(m)], fmt)

    def test_print_report_never_renders_none(self, tmp_path, capsys, monkeypatch):
        from pubrun.report.diagnostics import print_report
        monkeypatch.setenv("NO_COLOR", "1")
        _, path = _report_manifest(tmp_path)
        print_report(path, "standard")
        out = capsys.readouterr().out
        host_lines = [ln for ln in out.splitlines() if ln.startswith("Host")]
        assert host_lines and "None" not in host_lines[0] and "unknown" in host_lines[0]


_DROP = object()


class TestHostLineNeverRendersNone:
    def _host_line(self, tmp_path, monkeypatch, capsys, overrides):
        from pubrun.report.diagnostics import print_report
        monkeypatch.setenv("NO_COLOR", "1")
        m, path = _report_manifest(tmp_path)
        for key, value in overrides.items():
            if value is _DROP:
                m["host"].pop(key, None)
            else:
                m["host"][key] = value
        Path(path).write_text(json.dumps(m), encoding="utf-8")
        print_report(path, "standard")
        host_lines = [ln for ln in capsys.readouterr().out.splitlines() if ln.startswith("Host")]
        assert len(host_lines) == 1
        return host_lines[0]

    @pytest.mark.parametrize(
        "overrides, expected",
        [
            ({"os_version": _DROP}, "Linux"),
            ({"os_version": None}, "Linux"),
            ({"os_name": _DROP}, "6.8.0"),
            ({"os_name": None}, "6.8.0"),
            ({"os_name": _DROP, "os_version": _DROP}, "unknown OS"),
            ({"os_name": "", "os_version": ""}, "unknown OS"),
            ({"os_name": {"representation": "redacted"}}, "<REDACTED> 6.8.0"),
        ],
        ids=["version-missing", "version-null", "name-missing", "name-null",
             "both-missing", "both-empty", "name-redacted"],
    )
    def test_missing_os_fields(self, tmp_path, monkeypatch, capsys, overrides, expected):
        line = self._host_line(tmp_path, monkeypatch, capsys, overrides)
        assert "None" not in line
        assert "arm-01 - " in line and " (" in line
        os_text = line.split("arm-01 - ", 1)[1].split(" (", 1)[0]
        assert os_text == expected

    def test_complete_host_unchanged(self, tmp_path, monkeypatch, capsys):
        line = self._host_line(tmp_path, monkeypatch, capsys, {})
        assert "arm-01 - Linux 6.8.0 (" in line


# --------------------------------------------------------------------------- BUG-49

def _resources_run(tmp_path, scope, tree_values):
    run = tmp_path / "runs" / f"pubrun-{scope}"
    run.mkdir(parents=True)
    manifest = {
        "run": {"run_id": "x"}, "invocation": {"script": {"basename": "s.py"}},
        "status": {"outcome": "completed"},
        "resources": {"scope": scope, "capture_state": {"status": "complete"}},
    }
    (run / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    lines = []
    for i in range(5):
        payload = {"rss_bytes": 10 * 1024**2, "cpu_percent": 5.0}
        if tree_values is not None and i < len(tree_values):
            payload["tree_rss_bytes"] = tree_values[i]
        lines.append(json.dumps({"type": "resource_sample", "timestamp_utc": 1000.0 + i,
                                 "payload": payload}))
    (run / "events.jsonl").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return str(run / "manifest.json")


class TestResourcesChartLabel:
    def _mem_title(self, out):
        return [ln for ln in out.splitlines() if ln.startswith("Memory (RSS) History")][0]

    def test_tree_scope_plots_tree_series(self, tmp_path, capsys, monkeypatch):
        from pubrun.report.diagnostics import print_resources_report
        monkeypatch.setenv("NO_COLOR", "1")
        path = _resources_run(tmp_path, "tree", [200 * 1024**2] * 5)
        print_resources_report(path, metric="mem", width=40)
        title = self._mem_title(capsys.readouterr().out)
        assert "(process tree)" in title and "200.00 MB" in title

    def test_tree_scope_without_tree_samples_says_main_process(self, tmp_path, capsys, monkeypatch):
        from pubrun.report.diagnostics import print_resources_report
        monkeypatch.setenv("NO_COLOR", "1")
        path = _resources_run(tmp_path, "tree", None)
        print_resources_report(path, metric="mem", width=40)
        title = self._mem_title(capsys.readouterr().out)
        assert "(main process)" in title and "10.00 MB" in title

    def test_tree_scope_with_partial_tree_samples_falls_back(self, tmp_path, capsys, monkeypatch):
        from pubrun.report.diagnostics import print_resources_report
        monkeypatch.setenv("NO_COLOR", "1")
        path = _resources_run(tmp_path, "tree", [200 * 1024**2] * 3)
        print_resources_report(path, metric="mem", width=40)
        title = self._mem_title(capsys.readouterr().out)
        assert "(main process)" in title and "10.00 MB" in title

    def test_process_scope_says_main_process(self, tmp_path, capsys, monkeypatch):
        from pubrun.report.diagnostics import print_resources_report
        monkeypatch.setenv("NO_COLOR", "1")
        path = _resources_run(tmp_path, "process", [200 * 1024**2] * 5)
        print_resources_report(path, metric="mem", width=40)
        assert "(main process)" in self._mem_title(capsys.readouterr().out)

    def test_tree_series_filtered_with_last(self, tmp_path, capsys, monkeypatch):
        from pubrun.report.diagnostics import print_resources_report
        monkeypatch.setenv("NO_COLOR", "1")
        tree = [100 * 1024**2, 100 * 1024**2, 100 * 1024**2, 300 * 1024**2, 50 * 1024**2]
        path = _resources_run(tmp_path, "tree", tree)
        print_resources_report(path, metric="mem", last="1s", width=40)
        title = self._mem_title(capsys.readouterr().out)
        assert "(process tree)" in title and "300.00 MB" in title

    def test_single_tree_sample_uses_tree_value(self, tmp_path, capsys, monkeypatch):
        from pubrun.report.diagnostics import print_resources_report
        monkeypatch.setenv("NO_COLOR", "1")
        tree = [1 * 1024**2] * 4 + [77 * 1024**2]
        path = _resources_run(tmp_path, "tree", tree)
        # Samples are 1s apart; 0.5s retains only the final sample (parse_duration rejects <= 0).
        print_resources_report(path, metric="mem", last="0.5s", width=40)
        out = capsys.readouterr().out
        assert "Memory: 77.00 MB" in out


# --------------------------------------------------------------------------- BUG-65

class TestHostHydration:
    def _write(self, tmp_path, child_host):
        meta = {
            "manifest_type": "pubrun-meta-snapshot",
            "timing": {"started_at_utc": 1780250080.0},
            "host": {"hostname": "parent-01", "os_name": "Linux",
                     "capture_state": {"status": "complete"}},
        }
        (tmp_path / "meta.json").write_text(json.dumps(meta), encoding="utf-8")
        child = {"meta_ref": "meta.json", "timing": {"started_at_utc": 1780250120.0}}
        if child_host is not None:
            child["host"] = child_host
        return child

    def test_missing_host_hydrated(self, tmp_path):
        child = self._write(tmp_path, None)
        hydrated, _, report = hydrate_manifest_with_report(str(tmp_path / "manifest.json"), child)
        assert hydrated["host"]["hostname"] == "parent-01"
        assert hydrated["host"]["is_hydrated"] is True
        assert "host" in report.inherited_sections
        assert "host" not in child

    def test_suppressed_host_hydrated_via_legacy_api(self, tmp_path):
        child = self._write(tmp_path, {"capture_state": {"status": "suppressed"}})
        hydrated, _ = hydrate_manifest(str(tmp_path / "manifest.json"), child)
        assert hydrated["host"]["hostname"] == "parent-01"
        assert hydrated["host"]["is_hydrated"] is True

    def test_direct_host_preserved_and_mismatch_detected(self, tmp_path):
        direct = {"hostname": "child-07", "os_name": "Linux", "capture_state": {"status": "complete"}}
        child = self._write(tmp_path, dict(direct))
        hydrated, _, report = hydrate_manifest_with_report(str(tmp_path / "manifest.json"), child)
        assert hydrated["host"] == direct
        assert "host" in report.direct_sections
        assert "host" not in report.inherited_sections
        assert {"field": "host.hostname", "parent": "parent-01", "child": "child-07"} \
            in report.identity_mismatches
