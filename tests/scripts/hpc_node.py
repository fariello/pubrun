"""Simulates a Slurm-array child node that hydrates from a parent meta.json.

Run by tests/test_hpc_hydration_e2e.py. IMPORTANT: PUBRUN_META_REF must be set
BEFORE `import pubrun`, because in auto mode pubrun starts tracking on import; if
the env var were set afterwards it would be too late to influence the run (this
was a latent bug in an earlier version of this fixture).

The child uses `noauto` + an explicit `start()` so the meta_ref and the explicit
capture-suppression config are both in effect before the run begins. Heavy
capture is suppressed here (hardware off, packages off) so that report-time
hydration has something to stitch back from the parent snapshot.
"""
import os
import sys

# A real Slurm array job would export this before launching Python.
os.environ["PUBRUN_META_REF"] = "meta.json"

import pubrun.noauto as pubrun  # noqa: E402  (import after env var is intentional)

print("Starting node...")
tracker = pubrun.start(
    capture={
        "hardware": {"depth": "off"},
        "packages": {"mode": "off"},
    },
)
print("Doing work...")
pubrun.annotate("work", iterations=100)
print("Finished!")
pubrun.stop()

# Emit the run directory so the parent test can locate the child manifest.
sys.stderr.write(f"RUN_DIR={tracker.run_dir}\n")
sys.stderr.flush()
