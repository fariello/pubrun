"""End-to-end reproducibility assessment and preflight scenarios (backlog ``q3bll1``).

Every scenario drives a real tracked script with ``sys.executable`` inside ``tmp_path``,
then inspects the resulting run through real ``python -m pubrun`` subprocesses. Git
repositories are created with explicit ``-c user.name=... -c user.email=...`` so the tests
do not depend on a global Git identity. Where a scenario needs an environment the test
machine cannot produce (a different package version, a failed capture section), the test
edits the recorded manifest after the real run, which is what a manifest from another
machine looks like to the report tooling.
"""
import hashlib
import json
import os
import socket
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional

import pytest

from pubrun.report.checks import assess_run
from pubrun.report.reproducibility import NON_GUARANTEE_DISCLAIMER
from pubrun.report.utils import hydrate_manifest_with_report

_SRC_DIR = Path(__file__).resolve().parents[1] / "src"
_GIT_ID = ["-c", "user.name=pubrun-test", "-c", "user.email=pubrun-test@example.invalid"]


def _env(tmp_path: Path, extra: Optional[Dict[str, str]] = None) -> Dict[str, str]:
    env = {k: v for k, v in os.environ.items() if not k.startswith(("PUBRUN_", "GIT_"))}
    existing = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = f"{_SRC_DIR}{os.pathsep}{existing}" if existing else str(_SRC_DIR)
    # Keep any user-level pubrun config out of the runs under test.
    env["XDG_CONFIG_HOME"] = str(tmp_path / "xdg-config")
    env["APPDATA"] = str(tmp_path / "xdg-config")
    env["NO_COLOR"] = "1"
    if extra:
        env.update(extra)
    return env


def _git(repo: Path, *args: str) -> None:
    subprocess.run(["git", *_GIT_ID, *args], cwd=str(repo), check=True,
                   capture_output=True, text=True, timeout=60)


def _init_repo(repo: Path) -> None:
    (repo / ".gitignore").write_text("runs/\n__pycache__/\n", encoding="utf-8")
    _git(repo, "init", "-q", ".")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "init")


def _write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _track(project: Path, script: str, *args: str,
           extra_env: Optional[Dict[str, str]] = None, expect_rc: int = 0) -> Path:
    """Run a tracked script and return the run directory it produced."""
    before = set((project / "runs").glob("pubrun-*")) if (project / "runs").is_dir() else set()
    r = subprocess.run([sys.executable, script, *args], cwd=str(project),
                       env=_env(project, extra_env), capture_output=True, text=True, timeout=120)
    assert r.returncode == expect_rc, f"rc={r.returncode}\nSTDOUT:{r.stdout}\nSTDERR:{r.stderr}"
    new = sorted(set((project / "runs").glob("pubrun-*")) - before)
    assert len(new) == 1, f"expected one new run dir, got {new}"
    assert (new[0] / "manifest.json").is_file()
    return new[0]


def _cli(project: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, "-m", "pubrun", *args], cwd=str(project),
                          env=_env(project), capture_output=True, text=True, timeout=120)


def _cli_json(project: Path, *args: str, expect_rc: int = 0) -> dict:
    r = _cli(project, *args)
    assert r.returncode == expect_rc, f"rc={r.returncode}\nSTDOUT:{r.stdout}\nSTDERR:{r.stderr}"
    return json.loads(r.stdout)


def _load(run_dir: Path) -> dict:
    return json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))


def _save(run_dir: Path, manifest: dict) -> None:
    (run_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")


def _cat(assessment: dict, name: str) -> dict:
    for c in assessment["categories"]:
        if c["name"] == name:
            return c
    raise AssertionError(f"category {name} missing")


def _codes(assessment: dict) -> List[str]:
    return [f["code"] for f in assessment["findings"]]


def _finding(assessment: dict, code: str) -> dict:
    for f in assessment["findings"]:
        if f["code"] == code:
            return f
    raise AssertionError(f"finding {code} missing; have {_codes(assessment)}")


def _check(assessment: dict, name: str) -> dict:
    for c in assessment["preflight"]["checks"]:
        if c["name"] == name:
            return c
    raise AssertionError(f"preflight check {name} missing")


def _input_check(assessment: dict, filename: str) -> dict:
    # Match by basename: the recorded absolute path may be the resolved real path
    # (for example /private/var on macOS) rather than the path the test built.
    for c in assessment["preflight"]["checks"]:
        if c["name"].startswith("input:") and Path(c["name"][len("input:"):]).name == filename:
            return c
    raise AssertionError(f"input check for {filename} missing")


_EXPECTED_KEYS = {
    "schema_version", "mode", "summary", "next_action", "next_actions", "disclaimer",
    "categories", "findings", "parent_metadata", "preflight",
}


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    project = tmp_path / "proj"
    project.mkdir()
    _write(project / "train.py", "import pubrun\nprint('trained')\n")
    _init_repo(project)
    return project


# 1. Adequate recorded evidence, with the non-guarantee disclaimer on every output form.
def test_adequate_evidence_still_carries_non_guarantee_disclaimer(repo: Path, tmp_path: Path):
    run = _track(repo, "train.py")

    a = _cli_json(repo, "inspect", str(run), "--json")
    assert set(a) == _EXPECTED_KEYS
    assert a["mode"] == "manifest"
    assert a["disclaimer"] == NON_GUARANTEE_DISCLAIMER
    assert _cat(a, "source")["status"] == "adequate"
    assert _cat(a, "source")["evidence_status"] == "observed"
    assert _cat(a, "runtime")["status"] == "adequate"
    assert not any(f["comparison"] == "mismatch" for f in a["findings"])
    assert a["preflight"]["requested"] is False

    pf = _cli_json(repo, "inspect", str(run), "--preflight", "--json")
    assert pf["mode"] == "preflight"
    assert pf["disclaimer"] == NON_GUARANTEE_DISCLAIMER
    for name in ("python_version", "python_implementation", "entrypoint_script", "git_source"):
        assert _check(pf, name)["comparison"] == "match", name
    assert pf["preflight"]["counts"]["mismatch"] == 0

    text = _cli(repo, "inspect", str(run))
    assert text.returncode == 0
    assert "do not guarantee" in text.stdout

    # A sparse, legacy-shaped manifest never claims the run is reproducible either.
    sparse = tmp_path / "legacy" / "pubrun-legacy"
    _write(sparse / "manifest.json", json.dumps({"run": {"run_id": "legacy"}}))
    legacy = _cli_json(repo, "inspect", str(sparse), "--json")
    assert legacy["disclaimer"] == NON_GUARANTEE_DISCLAIMER
    for name in ("source", "runtime", "dependencies", "invocation"):
        assert _cat(legacy, name)["status"] == "not_checked", name
        assert _cat(legacy, name)["evidence_status"] == "not_checked", name
    strict_unknown = _cli(repo, "inspect", str(sparse), "--fail-on", "unknown")
    assert strict_unknown.returncode == 1


# 2. Dirty source without a recorded diff.
def test_dirty_source_without_recorded_diff(repo: Path):
    with open(repo / "train.py", "a", encoding="utf-8") as fh:
        fh.write("# local edit\n")
    run = _track(repo, "train.py")
    assert _load(run)["git"]["dirty"] is True

    a = _cli_json(repo, "inspect", str(run), "--json")
    src = _cat(a, "source")
    assert src["status"] == "gaps"
    assert "git_dirty_unrecorded" in src["finding_codes"]
    f = _finding(a, "git_dirty_unrecorded")
    assert f["severity"] == "warn" and f["impact"] == "material"

    pf = _cli_json(repo, "inspect", str(run), "--preflight", "--json")
    assert _check(pf, "git_source")["comparison"] != "match"
    assert _cli(repo, "inspect", str(run), "--fail-on", "mismatch").returncode == 1


# 3. Missing dependencies: package capture off, or an empty package list.
def test_missing_dependency_evidence_is_not_checked(repo: Path):
    _write(repo / ".pubrun.toml", '[capture.packages]\nmode = "off"\n')
    run = _track(repo, "train.py")

    a = _cli_json(repo, "inspect", str(run), "--json")
    dep = _cat(a, "dependencies")
    assert dep["status"] == "not_checked"
    assert dep["evidence_status"] == "not_checked"
    assert "packages_off" in dep["finding_codes"]
    assert _cli(repo, "inspect", str(run), "--fail-on", "unknown").returncode == 1

    pf = _cli_json(repo, "inspect", str(run), "--preflight", "--json")
    assert _cat(pf, "dependencies")["status"] != "adequate"
    assert not any(c["category"] == "dependencies" and c["comparison"] == "match"
                   for c in pf["preflight"]["checks"])


# 4. Package version mismatch and a missing package on preflight.
def test_package_mismatch_and_missing_package_on_preflight(repo: Path):
    run = _track(repo, "train.py")
    manifest = _load(run)
    records = manifest["packages"]["records"]
    assert records, "the tracked run must record at least pubrun itself"
    records[0] = dict(records[0], version="0.0.0.dev0", editable=False)
    records.append({"name": "pubrun-e2e-definitely-not-installed", "version": "1.0.0",
                    "editable": False, "source": "imported"})
    _save(run, manifest)

    pf = _cli_json(repo, "inspect", str(run), "--preflight", "--json")
    assert _cat(pf, "dependencies")["status"] == "mismatch"
    codes = _codes(pf)
    assert "preflight_package_version_mismatch" in codes
    assert "preflight_package_missing" in codes
    for code in ("preflight_package_version_mismatch", "preflight_package_missing"):
        f = _finding(pf, code)
        assert f["comparison"] == "mismatch" and f["impact"] == "material"
    assert pf["preflight"]["counts"]["mismatch"] >= 1

    gated = _cli(repo, "inspect", str(run), "--preflight", "--fail-on", "mismatch")
    assert gated.returncode == 1


# 5. Missing and content-changed inputs, and stat-only evidence that is not a match.
def test_missing_and_changed_inputs_differ_from_stat_only(repo: Path):
    _write(repo / "hashed.csv", "a,b\n1,2\n")
    _write(repo / "statonly.csv", "c,d\n3,4\n")
    _write(repo / "train.py",
           "import pubrun\n"
           "pubrun.register_input('hashed.csv', level='hash')\n"
           "pubrun.register_input('statonly.csv')\n")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "inputs")
    run = _track(repo, "train.py")
    clean = _cli_json(repo, "inspect", str(run), "--preflight", "--json")
    assert _input_check(clean, "hashed.csv")["comparison"] == "match"
    assert _input_check(clean, "hashed.csv")["evidence_status"] == "observed"
    stat = _input_check(clean, "statonly.csv")
    assert stat["comparison"] == "unknown"
    assert stat["evidence_status"] == "not_checked"
    assert _cli(repo, "inspect", str(run), "--preflight", "--fail-on", "unknown").returncode == 1

    (repo / "hashed.csv").write_text("a,b\n9,9\n", encoding="utf-8")
    changed = _cli_json(repo, "inspect", str(run), "--preflight", "--json")
    f = _finding(changed, "preflight_input_hash_mismatch")
    assert f["comparison"] == "mismatch" and f["severity"] == "warn"
    assert _cat(changed, "inputs_outputs")["status"] == "mismatch"

    (repo / "hashed.csv").unlink()
    missing = _cli_json(repo, "inspect", str(run), "--preflight", "--json")
    f = _finding(missing, "preflight_input_missing")
    assert f["comparison"] == "mismatch"
    assert f["evidence_status"] == "unavailable"
    assert _cli(repo, "inspect", str(run), "--preflight", "--fail-on", "mismatch").returncode == 1


# 6. Redacted command-line arguments.
def test_redacted_arguments_are_not_executable_as_printed(repo: Path):
    secret = "s3cr3t-e2e-value"
    run = _track(repo, "train.py", "--api-key", secret, "--epochs", "2")
    for path in run.rglob("*"):
        if path.is_file():
            assert secret not in path.read_text(encoding="utf-8", errors="replace"), path

    a = _cli_json(repo, "inspect", str(run), "--json")
    assert "rerun_command_redacted" in _cat(a, "invocation")["finding_codes"]

    plain = _cli(repo, "rerun", str(run))
    assert plain.returncode == 0
    assert "[REDACTED]" in plain.stdout and secret not in plain.stdout

    pf = _cli(repo, "rerun", str(run), "--preflight")
    assert pf.returncode == 0
    assert pf.stdout.strip().endswith("--epochs 2")
    assert "not directly executable" in pf.stderr

    strict = _cli(repo, "rerun", str(run), "--preflight", "--strict")
    assert strict.returncode == 1
    assert strict.stdout == ""

    j = _cli_json(repo, "rerun", str(run), "--preflight", "--json")
    assert set(j) == {"rerun_command", "executable_as_printed", "assessment"}
    assert j["executable_as_printed"] is False
    assert "[REDACTED]" in j["rerun_command"]
    assert set(j["assessment"]) == _EXPECTED_KEYS


# 7. Unavailable, moved, or policy-blocked parent snapshot, versus an inherited one.
def test_parent_snapshot_unavailable_blocked_and_inherited(repo: Path, tmp_path: Path):
    _write(repo / ".pubrun.toml", '[capture.packages]\nmode = "off"\n')
    run = _track(repo, "train.py", extra_env={"PUBRUN_META_REF": "meta.json"})
    assert _load(run)["meta_ref"] == "meta.json"
    original = (run / "manifest.json").read_bytes()

    missing = _cli_json(repo, "inspect", str(run), "--json")
    assert missing["parent_metadata"]["status"] == "missing"
    pm = _cat(missing, "parent_metadata")
    assert pm["evidence_status"] == "unavailable"
    assert "parent_metadata_missing" in pm["finding_codes"]
    assert _cat(missing, "dependencies")["status"] == "not_checked"

    meta = run / "meta.json"
    r = _cli(repo, "meta", "--out", str(meta))
    assert r.returncode == 0, r.stderr
    inherited = _cli_json(repo, "inspect", str(run), "--json")
    assert inherited["parent_metadata"]["status"] == "hydrated"
    assert "packages" in inherited["parent_metadata"]["inherited_sections"]
    assert _cat(inherited, "dependencies")["evidence_status"] == "inherited"
    assert "parent_metadata_inherited" in _cat(inherited, "parent_metadata")["finding_codes"]
    # Hydration is in memory only.
    assert (run / "manifest.json").read_bytes() == original

    snap = json.loads(meta.read_text(encoding="utf-8"))
    snap["timing"]["started_at_utc"] -= 3 * 86400
    meta.write_text(json.dumps(snap), encoding="utf-8")
    stale = _cli_json(repo, "inspect", str(run), "--json")
    assert "parent_metadata_stale" in _cat(stale, "parent_metadata")["finding_codes"]

    outside = tmp_path / "elsewhere" / "meta.json"
    outside.parent.mkdir()
    meta.replace(outside)
    manifest = _load(run)
    manifest["meta_ref"] = str(outside)
    _save(run, manifest)
    blocked = _cli_json(repo, "inspect", str(run), "--json")
    assert blocked["parent_metadata"]["status"] == "blocked_by_policy"
    assert "parent_metadata_blocked_by_policy" in _cat(blocked, "parent_metadata")["finding_codes"]
    assert _cat(blocked, "parent_metadata")["evidence_status"] == "unavailable"
    assert blocked["parent_metadata"]["inherited_sections"] == []


# 8. Partial or failed capture and a non-completed run outcome.
def test_partial_failed_capture_and_failed_outcome(repo: Path):
    _write(repo / "crash.py", "import pubrun\nraise RuntimeError('boom')\n")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "crash")
    run = _track(repo, "crash.py", expect_rc=1)
    assert _load(run)["status"]["outcome"] == "failed"

    a = _cli_json(repo, "inspect", str(run), "--json")
    cc = _cat(a, "capture_completeness")
    assert cc["status"] == "gaps"
    assert "run_outcome_incomplete" in cc["finding_codes"]

    manifest = _load(run)
    manifest["packages"]["capture_state"] = {"status": "partial"}
    manifest["git"] = {"capture_state": {"status": "timeout"}}
    _save(run, manifest)
    b = _cli_json(repo, "inspect", str(run), "--json")
    assert "packages_partial" in _cat(b, "dependencies")["finding_codes"]
    assert _cat(b, "dependencies")["status"] != "adequate"
    assert "git_timeout" in _cat(b, "source")["finding_codes"]
    assert _cat(b, "source")["status"] != "adequate"
    assert _cli(repo, "inspect", str(run), "--strict").returncode == 1

    manifest["packages"]["capture_state"] = {"status": "failed"}
    manifest["git"] = {"capture_state": {"status": "failed", "detail": "git crash"}}
    _save(run, manifest)
    c = _cli_json(repo, "inspect", str(run), "--json")
    assert "packages_capture_failed" in _cat(c, "dependencies")["finding_codes"]
    assert "git_capture_failed" in _cat(c, "source")["finding_codes"]

    manifest["packages"]["capture_state"] = {"status": "timeout"}
    _save(run, manifest)
    d = _cli_json(repo, "inspect", str(run), "--json")
    assert "packages_timeout" in _cat(d, "dependencies")["finding_codes"]


def _tree_snapshot(root: Path) -> Dict[str, str]:
    out = {}
    for p in sorted(root.rglob("*")):
        # `git status` may opportunistically refresh stat data in .git/index; that is
        # Git's own cache, not a change to the project, so it is excluded.
        if p.is_file() and p.relative_to(root).as_posix() != ".git/index":
            out[str(p.relative_to(root))] = hashlib.sha256(p.read_bytes()).hexdigest()
    return out


# Offline, read-only, no replay: preflight never runs the recorded command.
def test_preflight_never_replays_the_recorded_command(repo: Path):
    _write(repo / "train.py",
           "import pathlib, pubrun\npathlib.Path('SENTINEL').write_text('ran')\n")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "sentinel")
    run = _track(repo, "train.py")
    (repo / "SENTINEL").unlink()
    before = _tree_snapshot(repo)

    for args in (("rerun", str(run), "--preflight"),
                 ("rerun", str(run), "--preflight", "--json"),
                 ("rerun", str(run), "--preflight", "--fail-on", "unknown"),
                 ("inspect", str(run), "--preflight", "--json"),
                 ("inspect", str(run), "--preflight", "-v")):
        r = _cli(repo, *args)
        assert r.returncode in (0, 1), f"{args}: {r.stderr}"
        assert not (repo / "SENTINEL").exists(), f"{args} executed the recorded command"

    assert _tree_snapshot(repo) == before

    for bad in (("rerun", str(run), "--strict"), ("rerun", str(run), "--json"),
                ("rerun", str(run), "--fail-on", "warn")):
        r = _cli(repo, *bad)
        assert r.returncode == 2 and r.stdout == "", bad


# CLI and Python API agree.
def test_cli_and_assess_run_agree(repo: Path):
    run = _track(repo, "train.py")
    path = str(run / "manifest.json")
    with open(path, encoding="utf-8") as fh:
        manifest = json.load(fh)
    hydrated, _warnings, report = hydrate_manifest_with_report(path, manifest)

    def _shape(a: dict):
        return (
            [(c["name"], c["status"], c["evidence_status"]) for c in a["categories"]],
            sorted(_codes(a)),
            a["next_action"],
        )

    host = socket.gethostname()
    api_manifest = assess_run(hydrated, manifest_path=path, hydration_report=report,
                              current_hostname=host)
    api_preflight = assess_run(hydrated, manifest_path=path, hydration_report=report,
                               current_hostname=host, preflight=True, cwd=str(repo))

    cli_manifest = _cli_json(repo, "inspect", str(run), "--json")
    cli_preflight = _cli_json(repo, "inspect", str(run), "--preflight", "--json")
    cli_rerun = _cli_json(repo, "rerun", str(run), "--preflight", "--json")["assessment"]

    assert _shape(cli_manifest) == _shape(api_manifest)
    assert _shape(cli_preflight) == _shape(api_preflight)
    assert _shape(cli_rerun) == _shape(cli_preflight)
    assert ([(c["name"], c["comparison"]) for c in cli_preflight["preflight"]["checks"]]
            == [(c["name"], c["comparison"]) for c in api_preflight["preflight"]["checks"]])
