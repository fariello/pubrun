"""Behavioral test for the clean_runs dry-run confirmation table."""
import json
import time
from pathlib import Path

from pubrun.status import clean_runs


def _make_finished_run(
    base: Path,
    run_id: str,
    outcome: str,
    exit_code: int,
    age_seconds: float,
    script: str = "train",
) -> Path:
    run_dir = base / f"pubrun-{script}-20260101T000000Z-1234-{run_id}"
    run_dir.mkdir(parents=True)
    started = time.time() - age_seconds
    manifest = {
        "schema_version": "1.0",
        "run": {"run_id": run_id},
        "status": {"outcome": outcome},
        "timing": {
            "started_at_utc": started,
            "ended_at_utc": started + 1.0,
            "elapsed_seconds": 1.0,
        },
        "invocation": {
            "script": {"basename": f"{script}.py"},
            "argv": [f"{script}.py"],
        },
        "signals": {"exit_code": exit_code},
        "host": {"hostname": "node-a"},
        "process": {"pid": 1234},
    }
    (run_dir / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    return run_dir


def test_clean_dry_run_table_shows_each_run_exit_code(tmp_path: Path, capsys) -> None:
    runs_base = tmp_path / "runs"
    runs_base.mkdir()
    _make_finished_run(runs_base, "okrun001", "completed", 0, age_seconds=120.0)
    _make_finished_run(runs_base, "fail0003", "failed", 3, age_seconds=60.0)

    deleted = clean_runs(
        output_dir=str(runs_base),
        dry_run=True,
        status_filter="completed,failed",
    )

    assert deleted == 0
    lines = capsys.readouterr().out.splitlines()
    header = next(line for line in lines if "RUN ID" in line and "EXIT" in line and "AGE" in line)
    exit_start = header.index("EXIT")
    exit_end = header.index("AGE")

    exit_by_run_id = {}
    for line in lines:
        for run_id in ("okrun001", "fail0003"):
            if run_id in line:
                exit_by_run_id[run_id] = line[exit_start:exit_end].strip()

    assert exit_by_run_id == {"okrun001": "0", "fail0003": "3"}
