"""Behavioral tests for capture code paths edited during the mypy burn-down."""

import gc
import os
import subprocess
import sys
from typing import Any, List, Optional, Tuple

import pytest

from pubrun.capture import filesystem, packages
from pubrun.capture.subprocesses import SubprocessSpy


def _spawn_and_collect_unwaited_child(exit_code: int) -> Tuple[int, Any]:
    """Start a stdin-gated child, force cyclic GC of its Popen, and wait without reaping."""
    p: Any = subprocess.Popen(
        [sys.executable, "-c", f"import sys; sys.stdin.read(); sys.exit({exit_code})"],
        stdin=subprocess.PIPE,
    )
    pid = p.pid
    stdin_pipe = p.stdin
    assert stdin_pipe is not None

    # Create a reference cycle so cyclic GC clears weakrefs before Popen.__del__ runs.
    # Because the child is still blocked on stdin, Popen.__del__ cannot reap it and
    # queues it on SubprocessSpy's pending_running deque instead.
    p._aw_cycle = p
    del p
    gc.collect()

    return pid, stdin_pipe


@pytest.mark.skipif(
    not hasattr(os, "waitid") or not hasattr(os, "WNOWAIT"),
    reason="requires POSIX os.waitid with WNOWAIT",
)
@pytest.mark.filterwarnings("ignore::ResourceWarning")
def test_finalize_harvests_exit_code_of_collected_unwaited_child() -> None:
    SubprocessSpy.install(max_records=100)
    stdin_pipe: Optional[Any] = None
    try:
        pid, stdin_pipe = _spawn_and_collect_unwaited_child(5)
        stdin_pipe.close()
        os.waitid(os.P_PID, pid, os.WEXITED | os.WNOWAIT)

        SubprocessSpy.finalize_all()
        recs = SubprocessSpy.get_records()
        assert len(recs) == 1
        assert recs[0]["exit_code"] == 5
        assert recs[0]["capture_state"] == {"status": "failed"}
    finally:
        if stdin_pipe is not None and not stdin_pipe.closed:
            stdin_pipe.close()
        SubprocessSpy.uninstall()
        subprocess._cleanup()  # type: ignore[attr-defined]


def test_merge_carries_capture_state_detail_and_warnings_from_both_snapshots() -> None:
    startup = {
        "mode": "imported-only",
        "snapshot_stage": "startup",
        "records": [],
        "unresolved": [],
        "local_modules": [],
        "coverage_notes": [],
        "capture_state": {
            "status": "complete",
            "detail": "startup-detail",
            "warnings": ["startup-warning"],
        },
    }
    final = {
        "mode": "imported-only",
        "snapshot_stage": "final",
        "records": [],
        "unresolved": [],
        "local_modules": [],
        "coverage_notes": [],
        "capture_state": {
            "status": "partial",
            "detail": "final-detail",
            "warnings": ["final-warning"],
        },
    }

    merged = packages.merge_package_snapshots(
        startup,
        final,
        config={"capture": {"packages": {"mode": "imported-only"}}},
    )

    cs = merged["capture_state"]
    assert cs["status"] == "partial"
    assert "startup-detail" in cs["detail"]
    assert "final-detail" in cs["detail"]
    assert "startup-warning" in cs["warnings"]
    assert "final-warning" in cs["warnings"]


def test_merge_treats_non_dict_capture_state_as_empty() -> None:
    startup: Any = {
        "mode": "imported-only",
        "snapshot_stage": "startup",
        "records": [],
        "unresolved": [],
        "local_modules": [],
        "coverage_notes": [],
        "capture_state": "not-a-dict",
    }
    final = {
        "mode": "imported-only",
        "snapshot_stage": "final",
        "records": [],
        "unresolved": [],
        "local_modules": [],
        "coverage_notes": [],
        "capture_state": {
            "status": "partial",
            "detail": "final-detail",
            "warnings": ["final-warning"],
        },
    }

    merged = packages.merge_package_snapshots(
        startup,
        final,
        config={"capture": {"packages": {"mode": "imported-only"}}},
    )

    cs = merged["capture_state"]
    assert cs["detail"] == "final-detail"
    assert cs["warnings"] == ["final-warning"]


def test_probe_paths_live_probes_each_entry_path(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Any
) -> None:
    calls: List[str] = []
    real_probe = filesystem.probe_filesystem_live

    def _spy(path: str, wait_budget_s: float = 5.0) -> filesystem.LiveProbe:
        calls.append(path)
        return real_probe(path, wait_budget_s)

    monkeypatch.setattr(filesystem, "probe_filesystem_live", _spy)
    fallback_path = str(tmp_path)
    fs_data: Any = {
        "a": {"path": "/tmp/a", "mount_point": "/tmp"},
        "b": {"mount_point": "/var"},
        "c": {"path": fallback_path},
        "d": {"mount_point": 123},
        "capture_state": {"status": "complete"},
    }

    result = filesystem.probe_paths_live(fs_data, wait_budget_s=0.5)

    assert calls == ["/tmp", "/var", fallback_path]
    assert "live" in result["a"]
    assert "live" in result["b"]
    assert "live" in result["c"]
    assert "live" not in result["d"]
