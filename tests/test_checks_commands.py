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


class TestSelfCheckCLI:
    def test_self_check_runs_exit_zero_by_default(self):
        res = run_pubrun("self-check")
        assert res.returncode == 0
        assert "self-check" in res.stdout.lower()

    def test_self_check_json_well_formed(self):
        res = run_pubrun("self-check", "--json")
        assert res.returncode == 0
        json.loads(res.stdout)  # must parse

    def test_self_check_help_no_color_marker(self):
        # NO_COLOR must be respected (no ANSI escape in output).
        res = run_pubrun("self-check", env={"NO_COLOR": "1"})
        assert "\033[" not in res.stdout


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
