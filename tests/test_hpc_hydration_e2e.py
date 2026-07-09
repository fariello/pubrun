"""End-to-end test for HPC parent-child manifest hydration.

This exercises the flagship cluster workflow described in the README's "Advanced
HPC Ecosystems (Global Hydration)" section:

  1. A parent/head node snapshots the environment (`pubrun meta --out meta.json`).
  2. A child array job runs with ``PUBRUN_META_REF=meta.json`` set BEFORE importing
     pubrun, and suppresses heavy capture (hardware/packages off).
  3. At report time, the child manifest is hydrated from the parent snapshot, so the
     rendered picture is complete even though the child never captured hardware/deps.

The child is driven by ``tests/scripts/hpc_node.py`` (a repaired, previously-dead
fixture). See the docstring there for the import-ordering subtlety.

Note on scope: pubrun records ``meta_ref`` at capture time and performs hydration at
REPORT time; setting ``meta_ref`` does not by itself suppress capture (that is done
via explicit ``capture.*`` keys, which the fixture sets). This test asserts that real,
current behavior.
"""
import json
import subprocess
import sys
from pathlib import Path


SCRIPT = Path(__file__).parent / "scripts" / "hpc_node.py"


def _run_child(cwd: Path) -> Path:
    """Run the HPC child fixture in ``cwd`` and return its run directory."""
    proc = subprocess.run(
        [sys.executable, str(SCRIPT)],
        cwd=str(cwd),
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert proc.returncode == 0, f"child failed:\nSTDOUT:{proc.stdout}\nSTDERR:{proc.stderr}"
    run_dir = None
    for line in proc.stderr.splitlines():
        if line.startswith("RUN_DIR="):
            run_dir = Path(line.split("=", 1)[1].strip())
            break
    assert run_dir is not None, f"child did not emit RUN_DIR:\n{proc.stderr}"
    assert run_dir.exists(), f"child run dir does not exist: {run_dir}"
    return run_dir


def test_child_records_meta_ref_and_suppresses_heavy_capture(tmp_path):
    """The child manifest records meta_ref (proving the env var was effective before
    start) and shows hardware/packages suppressed."""
    run_dir = _run_child(tmp_path)
    manifest = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))

    # meta_ref recorded => PUBRUN_META_REF was in effect BEFORE the run started.
    # (If the fixture's import ordering regressed, this would be null.)
    assert manifest.get("meta_ref") == "meta.json"

    # Heavy capture was explicitly suppressed on the child.
    assert manifest["hardware"]["capture_state"]["status"] == "suppressed"
    assert manifest["packages"]["capture_state"]["status"] == "suppressed"
    # Not yet hydrated at capture time.
    assert "is_hydrated" not in manifest["hardware"]


def test_report_time_hydration_stitches_parent_context(tmp_path):
    """After generating a parent meta.json and hydrating the child manifest, the
    child's suppressed sections are filled in from the parent and marked hydrated."""
    from pubrun.report.meta_snapshot import generate_meta_snapshot
    from pubrun.report.utils import hydrate_manifest

    # 1. Parent/head node snapshot.
    parent_meta = tmp_path / "meta.json"
    generate_meta_snapshot(str(parent_meta), depth="deep")
    assert parent_meta.exists()
    parent = json.loads(parent_meta.read_text(encoding="utf-8"))
    assert "hardware" in parent  # parent captured what the child suppressed

    # 2. Child array job.
    run_dir = _run_child(tmp_path)
    manifest_path = run_dir / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest.get("meta_ref") == "meta.json"

    # Place the parent snapshot where the child manifest's meta_ref resolves to
    # (relative to the run dir), mirroring a shared filesystem on a cluster.
    (run_dir / "meta.json").write_text(parent_meta.read_text(encoding="utf-8"), encoding="utf-8")

    # 3. Report-time hydration.
    hydrated, warnings = hydrate_manifest(str(manifest_path), manifest)

    # The suppressed sections are now sourced from the parent and marked hydrated.
    assert hydrated["hardware"].get("is_hydrated") is True
    assert hydrated["packages"].get("is_hydrated") is True
    # The stitched hardware carries the parent's captured data.
    assert hydrated["hardware"].get("cpu") == parent["hardware"].get("cpu")
