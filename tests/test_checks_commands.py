"""Tests for IPD-B: `pubrun self-check` and `pubrun inspect`, and the shared findings
module `pubrun.report.checks`.

Key invariants:
- `import pubrun` must NOT import `pubrun.report.checks` (it is CLI-only, off the host path).
- inspect must be HONEST: never claim a feature was "off" when the manifest only shows an
  absence of records (subprocess/file-I/O) unless the definitive flag says so.
- terse-by-default; --show-suggestions expands; --json always full; NO_COLOR respected;
  --strict exits non-zero on warnings; the different-host banner fires only on a mismatch.
"""
import os
import sys
import json
import subprocess
import pytest
from pathlib import Path

PYTHON = sys.executable

from pubrun.report import checks


def run_pubrun(*args, cwd=None, env=None):
    cmd = [PYTHON, "-m", "pubrun"] + list(args)
    e = dict(os.environ)
    src_dir = Path(__file__).resolve().parents[1] / "src"
    if src_dir.is_dir():
        existing = e.get("PYTHONPATH", "")
        e["PYTHONPATH"] = f"{src_dir}{os.pathsep}{existing}" if existing else str(src_dir)
    if env:
        e.update(env)
    return subprocess.run(cmd, capture_output=True, text=True, cwd=cwd or os.getcwd(),
                          timeout=30, env=e)


# ------------------------------------------------------------------- import isolation

def test_import_pubrun_does_not_import_checks():
    """The findings module must not be pulled in by `import pubrun` (host-path safety)."""
    code = "import pubrun, sys; print('pubrun.report.checks' in sys.modules)"
    res = subprocess.run([PYTHON, "-c", code], capture_output=True, text=True, timeout=30)
    assert res.returncode == 0
    assert res.stdout.strip() == "False"


def test_import_and_run_makes_no_statvfs_call(tmp_path):
    """HANG-SAFETY (IPD data-quality): the always-on `import pubrun` + a tracked run must
    NOT invoke the blocking live probe (os.statvfs). If it did, a wedged NFS mount could
    hang a user's host script at import. The live probe is diagnostic/bench-ONLY."""
    code = (
        "import os\n"
        "os.statvfs = lambda *a, **k: (_ for _ in ()).throw(AssertionError('statvfs called on host path'))\n"
        "import pubrun\n"
        "pubrun.start(output_dir=r'%s')\n"
        "pubrun.stop()\n"
        "print('ok')\n" % str(tmp_path / "runs")
    )
    res = subprocess.run([PYTHON, "-c", code], capture_output=True, text=True, timeout=60)
    assert res.returncode == 0, res.stderr
    assert res.stdout.strip().endswith("ok")


class TestLiveFsHealthFindings:
    """self-check surfaces hung/slow mounts as honest, system-wide WARNINGs."""

    def test_hung_probe_emits_systemwide_warning(self):
        fs_data = {"tmpdir": {"path": "/scratch/tmp", "mount_point": "/scratch",
                              "fstype": "nfs4", "live": {"status": "pending", "hung": True,
                                                         "waited_s": 5.0}},
                   "capture_state": {"status": "complete"}}
        found = checks._live_fs_health_findings(fs_data)
        assert len(found) == 1
        f = found[0]
        assert f["severity"] == "warn" and f["code"] == "fs_hung_tmpdir"
        # Honest: system-wide framing, no fabricated slowdown magnitude.
        text = f"{f['message']} {f.get('suggestion', '')}"
        assert "not just pubrun" in text
        assert "%" not in f["message"]  # no invented number

    def test_slow_probe_states_measured_elapsed(self):
        fs_data = {"tmpdir": {"path": "/scratch/tmp", "mount_point": "/scratch",
                              "fstype": "nfs4", "live": {"status": "complete", "slow": True,
                                                         "elapsed_s": 34.0}},
                   "capture_state": {"status": "complete"}}
        found = checks._live_fs_health_findings(fs_data)
        assert len(found) == 1 and found[0]["code"] == "fs_slow_tmpdir"
        assert "34" in found[0]["message"]  # measured value may be stated

    def test_healthy_probe_emits_nothing(self):
        fs_data = {"tmpdir": {"path": "/tmp", "mount_point": "/tmp", "fstype": "tmpfs",
                              "live": {"status": "complete", "elapsed_s": 0.001}},
                   "capture_state": {"status": "complete"}}
        assert checks._live_fs_health_findings(fs_data) == []


class TestHpcLoginNodeNudge:
    """self-check nudges toward compute-node benchmarking on an HPC login node (INFO)."""

    def test_login_node_emits_info_not_warn(self, monkeypatch):
        import shutil
        monkeypatch.setattr(shutil, "which", lambda t: "/usr/bin/sbatch" if t == "sbatch" else None)
        for v in ("SLURM_JOB_ID", "PBS_JOBID", "LSB_JOBID", "JOB_ID"):
            monkeypatch.delenv(v, raising=False)
        found = checks._hpc_login_node_findings()
        assert len(found) == 1
        f = found[0]
        # INFO (not WARN) so `self-check --strict` is not tripped on every login node.
        assert f["severity"] == "info" and f["code"] == "hpc_login_node"
        assert "pubrun bench" in (f.get("suggestion") or "")

    def test_on_compute_node_no_nudge(self, monkeypatch):
        import shutil
        monkeypatch.setattr(shutil, "which", lambda t: "/usr/bin/sbatch" if t == "sbatch" else None)
        monkeypatch.setenv("SLURM_JOB_ID", "42")
        assert checks._hpc_login_node_findings() == []

    def test_no_scheduler_no_nudge(self, monkeypatch):
        import shutil
        monkeypatch.setattr(shutil, "which", lambda t: None)
        assert checks._hpc_login_node_findings() == []


# ------------------------------------------------------------------- findings unit tests

def _fake_manifest(**over):
    m = {
        "host": {"hostname": "compute-042", "capture_state": {"status": "complete"}},
        "resources": {"scope": "process", "capture_state": {"status": "complete"}},
        "console": {"capture_mode": "standard"},
        "hardware": {"capture_state": {"status": "complete"}},
        "packages": {"capture_state": {"status": "complete"}},
        "git": {"capture_state": {"status": "complete"}},
        "subprocesses": [],
        "data_files": {"inputs": [], "outputs": []},
        "capture": {"subprocesses_enabled": True, "file_provenance_available": True},
        "pubrun_imports": {"selected_mode": "auto", "selected_behavior": {"patch_subprocesses": True}},
    }
    m.update(over)
    return m


class TestManifestFindings:

    def test_different_host_banner_fires_on_mismatch(self):
        f = checks.manifest_findings(_fake_manifest(), current_hostname="login-01")
        assert any(x["code"] == "different_host" for x in f)

    def test_no_banner_on_same_host(self):
        f = checks.manifest_findings(_fake_manifest(), current_hostname="compute-042")
        assert not any(x["code"] == "different_host" for x in f)

    def test_process_scope_flagged(self):
        f = checks.manifest_findings(_fake_manifest(), current_hostname="compute-042")
        assert any(x["code"] == "resources_process_scope" for x in f)

    def test_tree_scope_not_flagged(self):
        m = _fake_manifest(resources={"scope": "tree", "capture_state": {"status": "complete"}})
        f = checks.manifest_findings(m, current_hostname="compute-042")
        assert not any(x["code"] == "resources_process_scope" for x in f)

    def test_subprocess_definitively_off_with_flag(self):
        m = _fake_manifest(capture={"subprocesses_enabled": False, "file_provenance_available": True})
        f = checks.manifest_findings(m, current_hostname="compute-042")
        assert any(x["code"] == "subprocess_tracking_off" for x in f)

    def test_subprocess_ambiguous_without_flag_is_honest(self):
        """Old manifest (no flag) + empty list: must NOT claim 'off' — honest 'unknown'."""
        m = _fake_manifest(capture={})  # no subprocesses_enabled flag
        f = checks.manifest_findings(m, current_hostname="compute-042")
        codes = [x["code"] for x in f]
        assert "subprocess_tracking_off" not in codes  # must not falsely assert OFF
        assert "subprocess_unknown" in codes
        # the honest finding must mention it cannot be determined
        msg = next(x["message"] for x in f if x["code"] == "subprocess_unknown")
        assert "cannot be determined" in msg or "either" in msg

    def test_no_file_provenance_finding_mentions_open(self):
        f = checks.manifest_findings(_fake_manifest(), current_hostname="compute-042")
        nf = next((x for x in f if x["code"] == "no_file_provenance"), None)
        assert nf is not None
        assert "pubrun.open" in (nf["suggestion"] or "") or "open()" in nf["message"]

    def test_resources_off_suppressed(self):
        m = _fake_manifest(resources={"capture_state": {"status": "suppressed"}})
        f = checks.manifest_findings(m, current_hostname="compute-042")
        assert any(x["code"] == "resources_off" for x in f)

    def test_never_raises_on_garbage(self):
        assert checks.manifest_findings({}, current_hostname=None) == checks.manifest_findings({}, None)
        checks.manifest_findings({"resources": "notadict", "host": 5}, current_hostname="x")

    def test_failed_sections_emit_warn_distinct_from_suppressed(self):
        m = _fake_manifest(
            git={"capture_state": {"status": "failed", "detail": "git binary crashed\nsecond line"}},
            hardware={"capture_state": {"status": "failed", "detail": "lscpu failed " + ("a" * 240)}},
            packages={"capture_state": {"status": "failed", "detail": "metadata broken"}},
            resources={"capture_state": {"status": "failed", "detail": "sampler error"}},
            console={"capture_state": {"status": "failed", "detail": "tee error"}},
        )
        findings = checks.manifest_findings(m, current_hostname="compute-042")
        by_code = {f["code"]: f for f in findings}

        for sec in ("git", "hardware", "packages", "resources", "console"):
            code = f"{sec}_capture_failed"
            assert code in by_code, f"missing {code} in {list(by_code)}"
            assert by_code[code]["severity"] == checks.WARN
            assert f"{sec}_off" not in by_code
            assert "errors.records" in (by_code[code].get("suggestion") or "")

        # No duplicate legacy git_failed/packages_failed codes alongside *_capture_failed.
        assert "git_failed" not in by_code
        assert "packages_failed" not in by_code

        # Detail is single-line and bounded.
        assert "\n" not in by_code["git_capture_failed"]["message"]
        assert "..." in by_code["hardware_capture_failed"]["message"]
        assert len(by_code["hardware_capture_failed"]["message"]) < 240

        # Suppressed stays distinct from failed.
        m_supp = _fake_manifest(
            resources={"capture_state": {"status": "suppressed"}},
            git={"capture_state": {"status": "suppressed"}},
            packages={"capture_state": {"status": "suppressed"}},
        )
        supp_codes = {f["code"] for f in checks.manifest_findings(m_supp, current_hostname="compute-042")}
        assert "resources_off" in supp_codes
        assert "git_off" in supp_codes
        assert "packages_off" in supp_codes
        assert "resources_capture_failed" not in supp_codes
        assert "git_capture_failed" not in supp_codes
        assert "packages_capture_failed" not in supp_codes

    def test_capture_error_records_deduplicated_and_truncation_surfaced(self):
        m = _fake_manifest(
            git={"capture_state": {"status": "failed", "detail": "git failed"}},
            errors={
                "records": [
                    {"kind": "capture-error", "section": "git", "message": "duplicate of failed git section"},
                    {"kind": "capture-error", "section": "subprocesses", "message": "popen hook error 1"},
                    {"kind": "capture-error", "section": "subprocesses", "message": "popen hook error 2"},
                    {"kind": "capture-error", "section": "events", "message": "events write failed"},
                    {"kind": "capture-error", "section": "writer", "message": "manifest temp write failed"},
                    {"kind": "capture-error", "section": None, "message": "unattributed failure"},
                    {"kind": "warning", "section": "other", "message": "not a capture-error"},
                ],
                "capture_state": {
                    "status": "partial",
                    "detail": "12 additional capture error(s) omitted",
                },
            },
        )
        findings = checks.manifest_findings(m, current_hostname="compute-042")
        codes = [f["code"] for f in findings]

        # Already-failed git section is not duplicated as capture_error_git or capture_errors_recorded.
        assert codes.count("git_capture_failed") == 1
        assert "capture_error_git" not in codes
        assert "capture_errors_recorded" not in codes

        # Additional capture-error sections are deduplicated per section with WARN severity.
        assert codes.count("capture_error_subprocesses") == 1
        assert codes.count("capture_error_events") == 1
        assert codes.count("capture_error_writer") == 1
        assert codes.count("capture_error_general") == 1
        assert "capture_error_other" not in codes

        by_code = {f["code"]: f for f in findings}
        sub_f = by_code["capture_error_subprocesses"]
        assert sub_f["severity"] == checks.WARN
        assert "popen hook error 1" in sub_f["message"]
        assert "(+1 more)" in sub_f["message"]

        assert by_code["capture_error_events"]["severity"] == checks.WARN
        assert by_code["capture_error_writer"]["severity"] == checks.WARN
        assert by_code["capture_error_general"]["severity"] == checks.WARN

        # Truncation detail from errors.capture_state is surfaced once without spam.
        assert codes.count("errors_capture_partial") == 1
        assert "12 additional capture error(s) omitted" in by_code["errors_capture_partial"]["message"]

    def test_real_fault_injected_manifest_propagates_redacted_detail(self, tmp_path, monkeypatch):
        import pubrun.tracker as tracker_mod
        from pubrun import start

        monkeypatch.setattr("pathlib.Path.cwd", lambda: tmp_path)
        tracker_mod._active_run = None
        secret = "sk-inspect-secret-12345"
        monkeypatch.setattr(
            tracker_mod,
            "get_git",
            lambda *a, **k: (_ for _ in ()).throw(RuntimeError(f"git crash --api-key={secret}")),
        )
        run = start(
            console={"capture_mode": "off"},
            events={"enabled": False},
            capture={"subprocesses": {"enabled": False}, "resources": {"depth": "off"}, "signals": {"enabled": False}},
        )
        if getattr(run, "_hardware_future_done", None) is not None:
            run._hardware_future_done.wait(timeout=3.0)
        run_dir = run.run_dir
        run.stop()

        manifest = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
        findings = checks.manifest_findings(manifest)
        git_f = next((f for f in findings if f["code"] == "git_capture_failed"), None)
        assert git_f is not None
        assert git_f["severity"] == checks.WARN
        assert secret not in git_f["message"]
        assert "REDACTED" in git_f["message"]


class TestLiveFindings:
    def test_live_findings_returns_list(self):
        assert isinstance(checks.live_findings(), list)

    def test_summarize_no_warns(self):
        assert "No configuration" in checks.summarize([{"severity": "info", "code": "x", "message": "m"}])


# ------------------------------------------------------------------------- CLI behavior

@pytest.fixture
def one_run(tmp_path):
    import pubrun
    import pubrun.tracker
    old = Path.cwd
    try:
        Path.cwd = staticmethod(lambda: tmp_path)
        pubrun.tracker._active_run = None
        t = pubrun.start()
        t.stop()
    finally:
        Path.cwd = old
        pubrun.tracker._active_run = None
    return tmp_path


class TestLiveChecksModel:
    """IPD-D: live_checks() reports every logical check (incl. the passing ones)."""

    def test_returns_checks_and_findings(self):
        check_list, findings = checks.live_checks()
        assert isinstance(check_list, list) and isinstance(findings, list)
        assert check_list, "expected a non-empty catalog of checks"
        for c in check_list:
            assert set(c) >= {"name", "label", "status", "detail"}
            assert c["status"] in ("ok", "warn", "info")
        # A check reported as warn/info must carry a detail message (from its finding).
        for c in check_list:
            if c["status"] != "ok":
                assert c["detail"]

    def test_findings_unchanged_by_live_checks(self):
        # live_checks() must return the SAME findings live_findings() would (strict keys on it).
        _, findings = checks.live_checks()
        from pubrun.report.checks import live_findings
        assert [f["code"] for f in findings] == [f["code"] for f in live_findings()]


class TestSelfCheckCLI:
    def test_self_check_runs_exit_zero_by_default(self):
        res = run_pubrun("self-check")
        assert res.returncode == 0
        assert "self-check" in res.stdout.lower()

    def test_itemized_default_shows_per_check_and_timing(self):
        # Default (no flags) itemizes each check and prints a timing footer.
        res = run_pubrun("self-check", env={"NO_COLOR": "1"})
        assert res.returncode == 0
        # one line per check with a canonical prefix
        assert "[ OK  ]" in res.stdout or "[WARN ]" in res.stdout
        assert "checks in" in res.stdout and "s —" in res.stdout  # "N checks in 0.01s — ..."

    def test_quiet_is_one_liner(self):
        res = run_pubrun("self-check", "--quiet", env={"NO_COLOR": "1"})
        assert res.returncode == 0
        # terse verdict, NOT the itemized per-check list
        assert "checks in" not in res.stdout
        assert "self-check" in res.stdout.lower()

    def test_json_includes_checks_and_elapsed(self):
        res = run_pubrun("self-check", "--json")
        assert res.returncode == 0
        data = json.loads(res.stdout)
        assert "checks" in data and "findings" in data and "elapsed_seconds" in data
        assert isinstance(data["checks"], list) and data["checks"]

    def test_help_no_color_marker(self):
        # NO_COLOR must be respected (no ANSI escape in output).
        res = run_pubrun("self-check", env={"NO_COLOR": "1"})
        assert "\033[" not in res.stdout


class TestMetaVerbose:
    """IPD-D: meta itemizes each gathered section + outcome + total time; JSON still written."""

    def test_meta_itemizes_and_writes_json(self, tmp_path):
        out = tmp_path / "meta.json"
        res = run_pubrun("meta", "--out", str(out), env={"NO_COLOR": "1"}, cwd=str(tmp_path))
        assert res.returncode == 0
        # per-section outcomes + total-time footer
        assert "[ OK  ] hardware:" in res.stdout
        assert "[ OK  ] python:" in res.stdout
        assert "packages:" in res.stdout
        assert "environment sections in" in res.stdout
        # JSON source-of-truth still written
        assert out.exists()
        data = json.loads(out.read_text())
        assert data["manifest_type"] == "pubrun-meta-snapshot"
        for sec in ("hardware", "python", "packages", "git", "environment", "host"):
            assert sec in data


class TestInspectCLI:
    def test_inspect_terse_default(self, one_run):
        res = run_pubrun("inspect", cwd=str(one_run))
        assert res.returncode == 0
        assert "inspect" in res.stdout.lower()

    def test_inspect_show_suggestions_expands(self, one_run):
        res = run_pubrun("inspect", "--show-suggestions", cwd=str(one_run))
        assert res.returncode == 0
        # expanded form has the "->" suggestion arrows
        assert "->" in res.stdout

    def test_inspect_json_full(self, one_run):
        res = run_pubrun("inspect", "--json", cwd=str(one_run))
        assert res.returncode == 0
        data = json.loads(res.stdout)
        assert "findings" in data

    def test_inspect_no_runs_errors(self, tmp_path):
        res = run_pubrun("inspect", cwd=str(tmp_path))
        assert res.returncode != 0


class TestFileProvenanceManifestFindings:
    """Behavioral tests for file-provenance evidence distinction in checks.manifest_findings (IPD hm32d9)."""

    def test_empty_data_files_recommends_open_and_register_apis(self):
        m = _fake_manifest(data_files={"inputs": [], "outputs": [], "mixed": []})
        findings = checks.manifest_findings(m, current_hostname="compute-042")
        nf = [f for f in findings if f["code"] == "no_file_provenance"]
        assert len(nf) == 1
        assert nf[0]["severity"] == checks.INFO
        combined = f"{nf[0]['message']} {nf[0].get('suggestion') or ''}"
        assert "pubrun.open" in combined
        assert "pubrun.register_input" in combined
        assert "pubrun.register_output" in combined

    def test_verified_sha256_and_non_sha256_records_emit_no_file_provenance_findings(self):
        m = _fake_manifest(
            data_files={
                "inputs": [
                    {
                        "path": "data/a.csv",
                        "hash_status": "completed",
                        "hash_algorithm": "sha256",
                        "sha256": "a" * 64,
                        "digest": {"algorithm": "sha256", "value": "a" * 64},
                        "evidence_source": "observed",
                        "evidence_strength": "verified_content",
                    }
                ],
                "outputs": [
                    {
                        "path": "out/b.parquet",
                        "hash_status": "completed",
                        "hash_algorithm": "sha512",
                        "sha256": None,
                        "digest": {"algorithm": "sha512", "value": "b" * 128},
                        "evidence_source": "observed",
                        "evidence_strength": "verified_content",
                    }
                ],
                "mixed": [],
            }
        )
        findings = checks.manifest_findings(m, current_hostname="compute-042")
        fp_codes = [
            f["code"]
            for f in findings
            if f["code"].startswith(("file_provenance_", "file_hash_", "no_file_provenance"))
        ]
        assert fp_codes == []

    def test_unverified_paths_stat_only_path_only_and_pending_outputs(self):
        m = _fake_manifest(
            data_files={
                "inputs": [
                    {
                        "path": "data/stat.csv",
                        "hash_status": "disabled",
                        "evidence_source": "observed",
                        "evidence_strength": "metadata_only",
                        "sha256": None,
                    },
                    {
                        "path": "data/name_only.csv",
                        "hash_status": "disabled",
                        "evidence_source": "observed",
                        "evidence_strength": "path_only",
                        "sha256": None,
                    },
                ],
                "outputs": [
                    {
                        "path": "out/deferred.bin",
                        "hash_status": "pending",
                        "evidence_source": "none",
                        "evidence_strength": "path_only",
                        "sha256": None,
                    }
                ],
                "mixed": [],
            }
        )
        findings = checks.manifest_findings(m, current_hostname="compute-042")
        codes = [f["code"] for f in findings]
        assert codes.count("file_provenance_unverified_paths") == 1
        assert "file_provenance_unhashed" not in codes
        unv = next(f for f in findings if f["code"] == "file_provenance_unverified_paths")
        assert unv["severity"] == checks.INFO
        assert "3" in unv["message"]
        assert "pending" in unv["message"].lower()

    def test_asserted_only_and_compound_verify_digest_unavailable(self):
        m = _fake_manifest(
            data_files={
                "inputs": [
                    {
                        "path": "ext/features.parquet",
                        "hash_status": "asserted",
                        "evidence_source": "asserted",
                        "evidence_strength": "asserted_content",
                        "caller_digest": {"algorithm": "sha256", "value": "c" * 64, "verified": None},
                        "digest": {"algorithm": "sha256", "value": "c" * 64},
                        "sha256": None,
                    },
                    {
                        "path": "ext/missing_verified.parquet",
                        "hash_status": "unavailable",
                        "hash_status_detail": "cannot verify caller digest: target is missing",
                        "evidence_source": "asserted",
                        "evidence_strength": "asserted_content",
                        "caller_digest": {"algorithm": "sha256", "value": "d" * 64, "verified": None},
                        "digest": {"algorithm": "sha256", "value": "d" * 64},
                        "sha256": None,
                    },
                ],
                "outputs": [
                    {
                        "path": "out/pending_asserted.bin",
                        "hash_status": "pending",
                        "evidence_source": "asserted",
                        "evidence_strength": "asserted_content",
                        "caller_digest": {"algorithm": "sha256", "value": "e" * 64, "verified": None},
                    }
                ],
                "mixed": [],
            }
        )
        findings = checks.manifest_findings(m, current_hostname="compute-042")
        by_code = {f["code"]: f for f in findings}
        assert "file_provenance_asserted_only" in by_code
        assert by_code["file_provenance_asserted_only"]["severity"] == checks.INFO
        assert "3" in by_code["file_provenance_asserted_only"]["message"]
        assert "file_provenance_hash_failed" in by_code
        assert by_code["file_provenance_hash_failed"]["severity"] == checks.WARN
        assert "file_hash_unavailable" not in by_code
        assert "file_provenance_unverified_paths" not in by_code

    def test_over_budget_changed_failed_caller_mismatch_and_mixed_entries(self):
        m = _fake_manifest(
            data_files={
                "inputs": [
                    {
                        "path": "data/huge.bin",
                        "hash_status": "over_budget",
                        "hash_status_detail": "file size exceeded max_hash_bytes",
                        "evidence_source": "observed",
                        "evidence_strength": "metadata_only",
                    },
                    {
                        "path": "data/mismatch.csv",
                        "hash_status": "failed",
                        "hash_status_detail": "caller_digest_mismatch",
                        "caller_digest": {"algorithm": "sha256", "value": "1" * 64, "verified": False},
                        "evidence_source": "observed",
                        "evidence_strength": "changed_unverified",
                    },
                ],
                "outputs": [],
                "mixed": [
                    {
                        "path": "work/state.db",
                        "hash_status": "file_changed",
                        "change_detected": True,
                        "hash_status_detail": "file changed during hashing",
                        "evidence_source": "observed",
                        "evidence_strength": "changed_unverified",
                    }
                ],
            }
        )
        findings = checks.manifest_findings(m, current_hostname="compute-042")
        codes = [f["code"] for f in findings]
        by_code = {f["code"]: f for f in findings}

        assert codes.count("file_provenance_changed") == 1
        assert codes.count("file_provenance_hash_failed") == 1
        assert codes.count("file_provenance_over_budget") == 1
        assert "file_hash_changed" not in codes
        assert "file_hash_unavailable" not in codes
        assert "file_hash_over_budget" not in codes

        assert by_code["file_provenance_changed"]["severity"] == checks.WARN
        assert by_code["file_provenance_hash_failed"]["severity"] == checks.WARN
        assert "caller-digest mismatch" in by_code["file_provenance_hash_failed"]["message"].lower()
        assert by_code["file_provenance_over_budget"]["severity"] == checks.INFO

    def test_legacy_and_malformed_data_files_degrade_safely(self):
        # Legacy verified record (no hash_status/evidence_strength/evidence_source, sha256 present).
        legacy_verified = _fake_manifest(
            data_files={"inputs": [{"path": "old.csv", "sha256": "f" * 64}], "outputs": []}
        )
        f_leg_v = checks.manifest_findings(legacy_verified, current_hostname="compute-042")
        assert not any(
            f["code"].startswith(("file_provenance_", "file_hash_", "no_file_provenance"))
            for f in f_leg_v
        )

        # Legacy unhashed record (no hash_status, no sha256).
        legacy_unhashed = _fake_manifest(
            data_files={"inputs": [{"path": "old.csv", "size_bytes": 42}], "outputs": []}
        )
        f_leg_u = checks.manifest_findings(legacy_unhashed, current_hostname="compute-042")
        assert any(f["code"] == "file_provenance_unverified_paths" for f in f_leg_u)

        # Malformed data_files structures never raise and fall back to no_file_provenance.
        for bad_df in (None, "not-a-dict", {"inputs": "bad", "outputs": [123, None], "mixed": 7}):
            f_bad = checks.manifest_findings(_fake_manifest(data_files=bad_df), current_hostname="compute-042")
            assert any(f["code"] == "no_file_provenance" for f in f_bad)

    def test_inspect_strict_exits_nonzero_on_warn_and_zero_on_info_only(self, tmp_path):
        import socket

        cur_host = socket.gethostname()

        def _write_run(name: str, data_files: dict) -> Path:
            run_dir = tmp_path / "runs" / name
            run_dir.mkdir(parents=True, exist_ok=True)
            manifest = {
                "run": {"run_id": name, "capture_state": {"status": "complete"}},
                "status": {"outcome": "completed", "exit_code": 0, "capture_state": {"status": "complete"}},
                "host": {"hostname": cur_host, "os_name": "Linux", "capture_state": {"status": "complete"}},
                "python": {"version": "3.11.0", "capture_state": {"status": "complete"}},
                "hardware": {"capture_state": {"status": "complete"}},
                "packages": {"mode": "full-environment", "records": [{"name": "numpy", "version": "1.0"}], "capture_state": {"status": "complete"}},
                "git": {"commit": "a" * 40, "dirty": False, "capture_state": {"status": "complete"}},
                "invocation": {"entrypoint_type": "script", "script": {"path": "x.py", "sha256": "b" * 64}},
                "resources": {"scope": "tree", "capture_state": {"status": "complete"}},
                "console": {"capture_mode": "standard", "capture_state": {"status": "complete"}},
                "subprocesses": [],
                "capture": {"subprocesses_enabled": True, "file_provenance_available": True},
                "pubrun_imports": {"selected_mode": "auto", "selected_behavior": {"patch_subprocesses": True}},
                "determinism": {"registered_seeds": [{"name": "numpy", "value": 1}]},
                "config": {"notices": []},
                "errors": {"records": [], "capture_state": {"status": "complete"}},
                "data_files": data_files,
            }
            (run_dir / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
            return run_dir

        info_dir = _write_run(
            "run-info-only",
            {
                "inputs": [
                    {
                        "path": "data/stat.csv",
                        "hash_status": "disabled",
                        "evidence_source": "observed",
                        "evidence_strength": "metadata_only",
                    },
                    {
                        "path": "data/asserted.csv",
                        "hash_status": "asserted",
                        "evidence_source": "asserted",
                        "evidence_strength": "asserted_content",
                        "caller_digest": {"algorithm": "sha256", "value": "c" * 64, "verified": None},
                    },
                    {
                        "path": "data/big.bin",
                        "hash_status": "over_budget",
                        "evidence_source": "observed",
                        "evidence_strength": "metadata_only",
                    },
                ],
                "outputs": [],
                "mixed": [],
            },
        )
        res_info = run_pubrun("inspect", str(info_dir), "--strict", "--json", env={"NO_COLOR": "1"})
        assert res_info.returncode == 0, res_info.stdout + res_info.stderr
        info_codes = {f["code"] for f in json.loads(res_info.stdout)["findings"]}
        assert "file_provenance_unverified_paths" in info_codes
        assert "file_provenance_asserted_only" in info_codes
        assert "file_provenance_over_budget" in info_codes

        warn_dir = _write_run(
            "run-warn",
            {
                "inputs": [
                    {
                        "path": "data/changed.csv",
                        "hash_status": "file_changed",
                        "change_detected": True,
                        "evidence_source": "observed",
                        "evidence_strength": "changed_unverified",
                    }
                ],
                "outputs": [],
                "mixed": [],
            },
        )
        res_warn = run_pubrun("inspect", str(warn_dir), "--strict", "--json", env={"NO_COLOR": "1"})
        assert res_warn.returncode != 0
        warn_codes = {f["code"] for f in json.loads(res_warn.stdout)["findings"]}
        assert "file_provenance_changed" in warn_codes
