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


class TestInspectReproducibilityAndPreflightCLI:
    """Behavioral CLI tests for shared reproducibility assessment and preflight in `pubrun inspect` (IPD 3lqtlt)."""

    @staticmethod
    def _write_manifest(run_dir: Path, manifest: dict) -> Path:
        run_dir.mkdir(parents=True, exist_ok=True)
        path = run_dir / "manifest.json"
        path.write_text(json.dumps(manifest), encoding="utf-8")
        return path

    @staticmethod
    def _clean_manifest(tmp_path: Path, *, hostname: str, extra: dict = None) -> dict:
        import platform

        script = tmp_path / "train.py"
        if not script.exists():
            script.write_text("print('ok')\n", encoding="utf-8")
        import hashlib

        script_sha = hashlib.sha256(script.read_bytes()).hexdigest()
        data_file = tmp_path / "input.csv"
        if not data_file.exists():
            data_file.write_text("x,y\n1,2\n", encoding="utf-8")
        data_sha = hashlib.sha256(data_file.read_bytes()).hexdigest()

        m = {
            "schema_version": "1.0",
            "manifest_type": "pubrun-manifest",
            "run": {"run_id": "20261122-010000-clean1", "capture_state": {"status": "complete"}},
            "timing": {"started_at_utc": 1780250000.0, "elapsed_seconds": 2.0},
            "status": {"outcome": "completed", "exit_code": 0, "capture_state": {"status": "complete"}},
            "host": {
                "hostname": hostname,
                "os_name": platform.system(),
                "capture_state": {"status": "complete"},
            },
            "python": {
                "version": platform.python_version(),
                "executable": sys.executable,
                "capture_state": {"status": "complete"},
            },
            "hardware": {"cpu": {"model": "TestCPU"}, "capture_state": {"status": "complete"}},
            "packages": {
                "mode": "full-environment",
                "records": [],
                "capture_state": {"status": "complete"},
            },
            "git": {"capture_state": {"status": "suppressed"}},
            "invocation": {
                "entrypoint_type": "script",
                "script": {"path": str(script), "basename": "train.py", "sha256": script_sha},
                "argv": [str(script), "--seed", "7"],
                "working_directory": {"path": str(tmp_path)},
                "rerun_command": f"cd {tmp_path} && python {script} --seed 7",
            },
            "resources": {"scope": "tree", "capture_state": {"status": "complete"}},
            "console": {"capture_mode": "standard", "capture_state": {"status": "complete"}},
            "subprocesses": [],
            "capture": {"subprocesses_enabled": True, "file_provenance_available": True},
            "pubrun_imports": {"selected_mode": "auto", "selected_behavior": {"patch_subprocesses": True}},
            "determinism": {"registered_seeds": [{"name": "random", "value": 7}]},
            "config": {"notices": []},
            "errors": {"records": [], "capture_state": {"status": "complete"}},
            "data_files": {
                "inputs": [
                    {
                        "path": str(data_file),
                        "sha256": data_sha,
                        "size_bytes": data_file.stat().st_size,
                        "hash_status": "completed",
                        "evidence_source": "observed",
                        "evidence_strength": "verified_content",
                    }
                ],
                "outputs": [],
                "mixed": [],
            },
        }
        if extra:
            m.update(extra)
        return m

    def test_inspect_json_ten_key_schema_and_preflight_mode(self, tmp_path):
        import socket
        from pubrun.report.reproducibility import NON_GUARANTEE_DISCLAIMER

        cur_host = socket.gethostname()
        run_dir = tmp_path / "runs" / "pubrun-schema1"
        manifest = self._clean_manifest(tmp_path, hostname=cur_host)
        self._write_manifest(run_dir, manifest)

        expected_keys = {
            "schema_version",
            "mode",
            "summary",
            "next_action",
            "next_actions",
            "disclaimer",
            "categories",
            "findings",
            "parent_metadata",
            "preflight",
        }

        res = run_pubrun("inspect", str(run_dir), "--json", env={"NO_COLOR": "1"})
        assert res.returncode == 0, res.stderr
        data = json.loads(res.stdout)
        assert expected_keys.issubset(set(data.keys()))
        assert data["mode"] == "manifest"
        assert data["disclaimer"] == NON_GUARANTEE_DISCLAIMER
        assert data["preflight"]["requested"] is False
        assert isinstance(data["findings"], list)
        assert len(data["categories"]) == 7

        res_pf = run_pubrun("inspect", str(run_dir), "--preflight", "--json", env={"NO_COLOR": "1"})
        assert res_pf.returncode == 0, res_pf.stderr
        pf_data = json.loads(res_pf.stdout)
        assert expected_keys.issubset(set(pf_data.keys()))
        assert pf_data["mode"] == "preflight"
        assert pf_data["preflight"]["requested"] is True
        assert isinstance(pf_data["preflight"]["checks"], list) and pf_data["preflight"]["checks"]

    def test_inspect_human_terse_verbose_no_color_and_different_host_deduplication(self, tmp_path):
        from pubrun.report.reproducibility import NON_GUARANTEE_DISCLAIMER

        run_dir = tmp_path / "runs" / "pubrun-diffhost"
        manifest = self._clean_manifest(
            tmp_path,
            hostname="remote-compute-node-99",
            extra={
                "git": {
                    "commit": "1234567890abcdef" * 2 + "12345678",
                    "dirty": True,
                    "capture_state": {"status": "complete"},
                },
            },
        )
        self._write_manifest(run_dir, manifest)

        # Terse default: header, banner once, summary, next step, disclaimer, no ANSI under NO_COLOR=1.
        res_terse = run_pubrun("inspect", str(run_dir), env={"NO_COLOR": "1"})
        assert res_terse.returncode == 0, res_terse.stderr
        assert "\033[" not in res_terse.stdout
        assert "\033[" not in res_terse.stderr
        assert "pubrun inspect:" in res_terse.stdout.lower()
        assert "=" * 60 in res_terse.stdout
        assert res_terse.stdout.count("remote-compute-node-99") >= 1
        assert "Summary:" in res_terse.stdout
        assert "Next step:" in res_terse.stdout
        assert NON_GUARANTEE_DISCLAIMER in res_terse.stdout
        assert "--preflight" in res_terse.stdout

        # Verbose (-v): banner shown once, different_host NOT duplicated in Findings section.
        res_verb = run_pubrun("inspect", str(run_dir), "-v", env={"NO_COLOR": "1"})
        assert res_verb.returncode == 0, res_verb.stderr
        assert "\033[" not in res_verb.stdout
        assert "Evidence categories:" in res_verb.stdout
        assert "Findings:" in res_verb.stdout
        assert "->" in res_verb.stdout
        assert res_verb.stdout.count("this run executed on 'remote-compute-node-99'") == 1
        assert "different_host (" not in res_verb.stdout

        # Preflight verbose with NO_COLOR=1 also emits zero ANSI escapes and includes Preflight checks.
        res_pf_v = run_pubrun("inspect", str(run_dir), "--preflight", "-v", env={"NO_COLOR": "1"})
        assert res_pf_v.returncode == 0, res_pf_v.stderr
        assert "\033[" not in res_pf_v.stdout
        assert "Preflight checks:" in res_pf_v.stdout
        assert res_pf_v.stdout.count("this run executed on 'remote-compute-node-99'") == 1

        # JSON retains different_host inside findings.
        res_json = run_pubrun("inspect", str(run_dir), "--json", env={"NO_COLOR": "1"})
        assert res_json.returncode == 0
        codes = [f["code"] for f in json.loads(res_json.stdout)["findings"]]
        assert "different_host" in codes

    def test_inspect_hydrates_meta_ref_parent_snapshot(self, tmp_path):
        import socket

        cur_host = socket.gethostname()
        runs_dir = tmp_path / "runs"
        run_dir = runs_dir / "pubrun-child1"
        run_dir.mkdir(parents=True)

        # Parent meta.json placed inside the child run dir (always allowed by default sandbox policy).
        meta_doc = {
            "schema_version": "1.0",
            "manifest_type": "pubrun-meta-snapshot",
            "timing": {"started_at_utc": 1780249900.0},
            "host": {"hostname": cur_host, "os_name": "Linux"},
            "hardware": {"cpu": {"model": "ParentCPU"}, "memory_total_bytes": 16 * 1024**3, "capture_state": {"status": "complete"}},
            "packages": {
                "mode": "full-environment",
                "records": [{"name": "pytest", "version": "8.0.0"}],
                "capture_state": {"status": "complete"},
            },
        }
        (run_dir / "meta.json").write_text(json.dumps(meta_doc), encoding="utf-8")

        child = self._clean_manifest(
            tmp_path,
            hostname=cur_host,
            extra={
                "meta_ref": "meta.json",
                "hardware": {"capture_state": {"status": "suppressed"}},
                "packages": {"capture_state": {"status": "suppressed"}},
            },
        )
        self._write_manifest(run_dir, child)

        res = run_pubrun("inspect", str(run_dir), "--json", env={"NO_COLOR": "1"})
        assert res.returncode == 0, res.stderr
        data = json.loads(res.stdout)
        assert data["parent_metadata"]["status"] == "hydrated"
        assert "hardware" in data["parent_metadata"]["inherited_sections"]
        assert "packages" in data["parent_metadata"]["inherited_sections"]
        codes = {f["code"] for f in data["findings"]}
        assert "parent_metadata_inherited" in codes
        assert "hardware_off" not in codes
        assert "packages_off" not in codes

        res_human = run_pubrun("inspect", str(run_dir), env={"NO_COLOR": "1"})
        assert res_human.returncode == 0
        assert "Inherited from parent snapshot:" in res_human.stdout

    def test_inspect_strict_and_fail_on_thresholds(self, tmp_path):
        import socket

        cur_host = socket.gethostname()

        # 1. Portability-only WARN (different_host): --strict fails (warn), --fail-on mismatch passes!
        port_dir = tmp_path / "runs" / "pubrun-portability"
        port_manifest = self._clean_manifest(tmp_path, hostname="other-cluster-node")
        self._write_manifest(port_dir, port_manifest)

        assert run_pubrun("inspect", str(port_dir), "--preflight", env={"NO_COLOR": "1"}).returncode == 0
        assert run_pubrun("inspect", str(port_dir), "--preflight", "--strict", env={"NO_COLOR": "1"}).returncode == 1
        res_mm_pass = run_pubrun(
            "inspect", str(port_dir), "--preflight", "--fail-on", "mismatch", env={"NO_COLOR": "1"}
        )
        assert res_mm_pass.returncode == 0, res_mm_pass.stdout + res_mm_pass.stderr

        # 2. Material mismatch (missing package version on preflight): --fail-on mismatch exits 1.
        mm_dir = tmp_path / "runs" / "pubrun-mismatch"
        mm_manifest = self._clean_manifest(
            tmp_path,
            hostname=cur_host,
            extra={
                "packages": {
                    "mode": "full-environment",
                    "records": [{"name": "definitely-not-installed-pkg-xyz", "version": "9.9.9"}],
                    "capture_state": {"status": "complete"},
                }
            },
        )
        self._write_manifest(mm_dir, mm_manifest)

        assert run_pubrun("inspect", str(mm_dir), "--preflight", env={"NO_COLOR": "1"}).returncode == 0
        assert (
            run_pubrun("inspect", str(mm_dir), "--preflight", "--fail-on", "mismatch", env={"NO_COLOR": "1"}).returncode
            == 1
        )

        # 3. Unknown check (stat-only input without digest): --fail-on mismatch passes, --fail-on unknown exits 1.
        unk_dir = tmp_path / "runs" / "pubrun-unknown"
        stat_file = tmp_path / "stat_only.csv"
        stat_file.write_text("col\n1\n", encoding="utf-8")
        unk_manifest = self._clean_manifest(
            tmp_path,
            hostname=cur_host,
            extra={
                "data_files": {
                    "inputs": [
                        {
                            "path": str(stat_file),
                            "size_bytes": stat_file.stat().st_size,
                            "hash_status": "disabled",
                            "evidence_source": "observed",
                            "evidence_strength": "metadata_only",
                        }
                    ],
                    "outputs": [],
                    "mixed": [],
                }
            },
        )
        self._write_manifest(unk_dir, unk_manifest)

        assert (
            run_pubrun("inspect", str(unk_dir), "--preflight", "--fail-on", "mismatch", env={"NO_COLOR": "1"}).returncode
            == 0
        )
        assert (
            run_pubrun("inspect", str(unk_dir), "--preflight", "--fail-on", "unknown", env={"NO_COLOR": "1"}).returncode
            == 1
        )
        # --fail-on unknown also activates strict exit checking WITHOUT --preflight (manifest mode).
        assert (
            run_pubrun("inspect", str(unk_dir), "--fail-on", "unknown", env={"NO_COLOR": "1"}).returncode == 1
        )

    def test_cross_surface_agreement_inspect_rerun_show_and_tui_formatter(self, tmp_path):
        import socket
        from pubrun.report.reproducibility import (
            NON_GUARANTEE_DISCLAIMER,
            assess_run,
            format_reproducibility_summary,
        )
        from pubrun.report.utils import hydrate_manifest_with_report

        cur_host = socket.gethostname()
        run_dir = tmp_path / "runs" / "pubrun-cross"
        manifest = self._clean_manifest(
            tmp_path,
            hostname=cur_host,
            extra={
                "git": {
                    "commit": "abcdef0123456789" * 2 + "abcdef01",
                    "dirty": True,
                    "capture_state": {"status": "complete"},
                },
            },
        )
        manifest_path = self._write_manifest(run_dir, manifest)

        # 1. inspect --json
        res_inspect = run_pubrun("inspect", str(run_dir), "--json", env={"NO_COLOR": "1"})
        assert res_inspect.returncode == 0, res_inspect.stderr
        data_inspect = json.loads(res_inspect.stdout)

        # 2. inspect --preflight --json
        res_inspect_pf = run_pubrun("inspect", str(run_dir), "--preflight", "--json", env={"NO_COLOR": "1"})
        assert res_inspect_pf.returncode == 0, res_inspect_pf.stderr
        data_inspect_pf = json.loads(res_inspect_pf.stdout)

        # 3. rerun --preflight --json
        res_rerun_pf = run_pubrun("rerun", str(run_dir), "--preflight", "--json", env={"NO_COLOR": "1"})
        assert res_rerun_pf.returncode == 0, res_rerun_pf.stderr
        data_rerun_pf = json.loads(res_rerun_pf.stdout)

        # 4. pubrun show (standard)
        res_show = run_pubrun("show", str(run_dir), env={"NO_COLOR": "1"})
        assert res_show.returncode == 0, res_show.stderr

        # 5. Direct engine + TUI formatter
        hydrated, _, report = hydrate_manifest_with_report(str(manifest_path), manifest)
        direct_manifest = assess_run(
            hydrated,
            manifest_path=str(manifest_path),
            hydration_report=report,
            current_hostname=cur_host,
            preflight=False,
        )
        tui_summary = format_reproducibility_summary(direct_manifest)

        # inspect --preflight --json and rerun --preflight --json must match identically.
        assert data_rerun_pf["assessment"]["categories"] == data_inspect_pf["categories"]
        assert data_rerun_pf["assessment"]["findings"] == data_inspect_pf["findings"]
        assert data_rerun_pf["assessment"]["next_action"] == data_inspect_pf["next_action"]
        assert data_rerun_pf["assessment"]["preflight"] == data_inspect_pf["preflight"]

        # inspect --json and direct engine (used by show + TUI) agree on categories, findings, next_action.
        assert data_inspect["categories"] == direct_manifest["categories"]
        assert [f["code"] for f in data_inspect["findings"]] == [
            f["code"] for f in direct_manifest["findings"]
        ]
        assert data_inspect["next_action"] == direct_manifest["next_action"]

        # show and TUI formatter both include the same summary, next_action, and disclaimer.
        assert direct_manifest["summary"] in res_show.stdout
        assert direct_manifest["next_action"] in res_show.stdout
        assert NON_GUARANTEE_DISCLAIMER in res_show.stdout
        assert direct_manifest["summary"] in tui_summary
        assert direct_manifest["next_action"] in tui_summary
        assert NON_GUARANTEE_DISCLAIMER in tui_summary
