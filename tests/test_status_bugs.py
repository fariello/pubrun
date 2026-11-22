"""Regression tests for status.py cleanup, age-filter, closeout, and display bugs.

Covers BUG-01 (empty status filter widening cleanup), BUG-02 (invalid age
silently disabling the age filter), BUG-41 (crashed-run closeout schema),
BUG-60 (selection parsing), and BUG-67 (status column and directory names).
"""
import json
import re
import time
from pathlib import Path

import pytest

from pubrun.status import (
    STATUS_COMPLETED,
    STATUS_RUNNING,
    RunInfo,
    _parse_selection,
    clean_runs,
    close_out_crashed_run,
    filter_runs,
    render_short_list,
    scan_runs,
)

ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")


def _make_completed(base: Path, run_id: str, age_seconds: float, script: str = "train") -> Path:
    run_dir = base / f"pubrun-{script}-20260101T000000Z-1234-{run_id}"
    run_dir.mkdir(parents=True)
    started = time.time() - age_seconds
    manifest = {
        "schema_version": "1.0",
        "run": {"run_id": run_id},
        "status": {"outcome": "completed"},
        "timing": {"started_at_utc": started, "ended_at_utc": started + 1.0, "elapsed_seconds": 1.0},
        "invocation": {"script": {"basename": f"{script}.py"}, "argv": [f"{script}.py", "--epochs=3"]},
        "signals": {"exit_code": 0},
        "host": {"hostname": "node-a"},
        "process": {"pid": 1234},
    }
    (run_dir / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    return run_dir


def _make_running(base: Path, run_id: str) -> Path:
    """A lock on a foreign host started recently is classified as running."""
    run_dir = base / f"pubrun-live-20260101T000000Z-4321-{run_id}"
    run_dir.mkdir(parents=True)
    lock = {
        "pid": 4321,
        # Inside the 48-hour window in which a foreign-host lock counts as running.
        "started_at_utc": time.time() - 3600,
        "script": "live",
        "run_id": run_id,
        "hostname": "some-other-host-that-is-not-this-one.invalid",
        "argv": [],
    }
    (run_dir / ".pubrun.lock").write_text(json.dumps(lock), encoding="utf-8")
    return run_dir


@pytest.fixture
def runs_base(tmp_path):
    base = tmp_path / "runs"
    base.mkdir()
    return base


# --------------------------------------------------------------------------
# BUG-01: status filter that normalizes to nothing must delete nothing
# --------------------------------------------------------------------------

class TestBug01EmptyStatusFilter:
    @pytest.mark.parametrize(
        "status_filter",
        ["running", ["running"], ("running",), {"running"}, "", "   ", ",,,", " , ", [], ["", " "]],
    )
    def test_empty_or_running_only_filter_deletes_nothing(self, runs_base, status_filter, capsys):
        done = _make_completed(runs_base, "done0001", age_seconds=10 * 86400)
        live = _make_running(runs_base, "live0001")
        statuses = {r.run_id: r.status for r in scan_runs(str(runs_base))}
        assert statuses == {"done0001": STATUS_COMPLETED, "live0001": STATUS_RUNNING}

        deleted = clean_runs(output_dir=str(runs_base), status_filter=status_filter, yes=True)

        assert deleted == 0
        assert done.exists()
        assert live.exists()
        assert "Nothing to clean" in capsys.readouterr().out

    def test_tuple_and_set_filters_normalize(self, runs_base):
        done = _make_completed(runs_base, "done0002", age_seconds=10)
        live = _make_running(runs_base, "live0002")
        deleted = clean_runs(output_dir=str(runs_base), status_filter=("Completed ", "running"), yes=True)
        assert deleted == 1
        assert not done.exists()
        assert live.exists()

    def test_running_never_deleted_with_mixed_filter(self, runs_base):
        done = _make_completed(runs_base, "done0003", age_seconds=10)
        live = _make_running(runs_base, "live0003")
        deleted = clean_runs(output_dir=str(runs_base), status_filter="running,completed", yes=True)
        assert deleted == 1
        assert not done.exists()
        assert live.exists()

    def test_running_never_deleted_by_default(self, runs_base):
        done = _make_completed(runs_base, "done0004", age_seconds=10)
        live = _make_running(runs_base, "live0004")
        deleted = clean_runs(output_dir=str(runs_base), yes=True)
        assert deleted == 1
        assert not done.exists()
        assert live.exists()


# --------------------------------------------------------------------------
# BUG-02: invalid age values must fail closed
# --------------------------------------------------------------------------

class TestBug02AgeFilter:
    def _runs(self, base):
        _make_completed(base, "old00001", age_seconds=2 * 3600)   # 2 hours old
        _make_completed(base, "mid00001", age_seconds=45 * 60)    # 45 minutes old
        _make_completed(base, "new00001", age_seconds=10)         # 10 seconds old
        return scan_runs(str(base))

    @pytest.mark.parametrize(
        "older_than,expected",
        [
            ("30m", {"old00001", "mid00001"}),
            ("90s", {"old00001", "mid00001"}),
            ("90m", {"old00001"}),
            ("1h", {"old00001"}),
            ("1d", set()),
            ("0", {"old00001", "mid00001", "new00001"}),
            (" 30M ", {"old00001", "mid00001"}),
        ],
    )
    def test_valid_units_filter_by_age(self, runs_base, older_than, expected):
        runs = self._runs(runs_base)
        got = {r.run_id for r in filter_runs(runs, older_than=older_than)}
        assert got == expected

    @pytest.mark.parametrize(
        "older_than", ["", "   ", "2w", "abc", "-5d", "-1", "nan", "inf", "-inf", "d", 5, 1.5],
    )
    def test_invalid_older_than_raises(self, runs_base, older_than):
        runs = self._runs(runs_base)
        with pytest.raises(ValueError):
            filter_runs(runs, older_than=older_than)

    @pytest.mark.parametrize("older_than_days", [-1.0, float("nan"), float("inf"), True, "3"])
    def test_invalid_older_than_days_raises_and_deletes_nothing(self, runs_base, older_than_days):
        dirs = [_make_completed(runs_base, "x0000001", age_seconds=10 * 86400)]
        with pytest.raises(ValueError):
            clean_runs(output_dir=str(runs_base), older_than_days=older_than_days, yes=True)
        assert all(d.exists() for d in dirs)

    def test_invalid_older_than_in_clean_deletes_nothing(self, runs_base):
        old = _make_completed(runs_base, "old00002", age_seconds=10 * 86400)
        new = _make_completed(runs_base, "new00002", age_seconds=10)
        with pytest.raises(ValueError):
            clean_runs(output_dir=str(runs_base), older_than="abc", yes=True)
        assert old.exists()
        assert new.exists()

    def test_valid_older_than_days_still_works(self, runs_base):
        old = _make_completed(runs_base, "old00003", age_seconds=3 * 86400)
        new = _make_completed(runs_base, "new00003", age_seconds=10)
        deleted = clean_runs(output_dir=str(runs_base), older_than_days=1, yes=True)
        assert deleted == 1
        assert not old.exists()
        assert new.exists()


# --------------------------------------------------------------------------
# BUG-41: crashed-run closeout manifest schema
# --------------------------------------------------------------------------

class TestBug41CrashCloseout:
    def _lock_only(self, base, lock):
        run_dir = base / f"pubrun-train-20260101T000000Z-999999-{lock['run_id']}"
        run_dir.mkdir(parents=True)
        (run_dir / ".pubrun.lock").write_text(json.dumps(lock), encoding="utf-8")
        return run_dir

    def test_fallback_hostname_is_plain_string_and_argv_full(self, runs_base):
        lock = {
            "run_id": "crash001", "pid": 999999, "started_at_utc": 1700000000.0,
            "script": "train", "hostname": "node-7",
            "argv": ["--lr=0.1", "--epochs=3"],
            "sys_argv": ["train.py", "--lr=0.1", "--epochs=3"],
        }
        run_dir = self._lock_only(runs_base, lock)
        close_out_crashed_run(run_dir, lock)

        manifest = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
        assert manifest["host"]["hostname"] == "node-7"
        assert manifest["invocation"]["argv"] == ["train.py", "--lr=0.1", "--epochs=3"]
        assert "argv" not in manifest["process"]
        assert not (run_dir / ".pubrun.lock").exists()

        info = RunInfo(run_dir)
        assert info.hostname == "node-7"
        assert info.args == "--lr=0.1 --epochs=3"

    def test_fallback_hostname_none_when_absent(self, runs_base):
        lock = {"run_id": "crash002", "pid": 999999, "started_at_utc": 1700000000.0}
        run_dir = self._lock_only(runs_base, lock)
        close_out_crashed_run(run_dir, lock)
        manifest = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
        assert manifest["host"]["hostname"] is None
        assert manifest["invocation"]["argv"] == []
        assert RunInfo(run_dir).hostname is None

    def test_legacy_lock_without_sys_argv_prepends_script(self, runs_base):
        lock = {
            "run_id": "crash003", "pid": 999999, "started_at_utc": 1700000000.0,
            "script": "train", "hostname": "node-7", "argv": ["--lr=0.1", "--epochs=3"],
        }
        run_dir = self._lock_only(runs_base, lock)
        close_out_crashed_run(run_dir, lock)
        manifest = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
        assert manifest["invocation"]["argv"] == ["train", "--lr=0.1", "--epochs=3"]
        assert RunInfo(run_dir).args == "--lr=0.1 --epochs=3"

    def test_legacy_lock_argv_already_starting_with_script_not_duplicated(self, runs_base):
        lock = {
            "run_id": "crash004", "pid": 999999, "started_at_utc": 1700000000.0,
            "script": "train", "argv": ["train.py", "--lr=0.1"],
        }
        run_dir = self._lock_only(runs_base, lock)
        close_out_crashed_run(run_dir, lock)
        manifest = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
        assert manifest["invocation"]["argv"] == ["train.py", "--lr=0.1"]

    def test_existing_manifest_host_untouched(self, runs_base):
        run_dir = runs_base / "pubrun-train-20260101T000000Z-999999-crash005"
        run_dir.mkdir()
        host = {"hostname": "orig-host", "os": "linux", "capture_state": {"status": "complete"}}
        manifest = {
            "schema_version": "1.0", "run": {"run_id": "crash005"},
            "status": {"outcome": "running"}, "timing": {"started_at_utc": 1000.0},
            "host": host,
        }
        (run_dir / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
        lock = {"run_id": "crash005", "pid": 999999, "started_at_utc": 1000.0, "hostname": "lock-host"}
        (run_dir / ".pubrun.lock").write_text(json.dumps(lock), encoding="utf-8")
        close_out_crashed_run(run_dir, lock)
        updated = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
        assert updated["host"] == host
        assert updated["status"]["outcome"] == "crashed"

    def test_legacy_dict_hostname_unwrapped_on_load(self, runs_base):
        run_dir = runs_base / "pubrun-train-20260101T000000Z-999999-crash006"
        run_dir.mkdir()
        manifest = {
            "run": {"run_id": "crash006"}, "status": {"outcome": "crashed"},
            "timing": {"started_at_utc": 1000.0},
            "host": {"hostname": {"representation": "plain", "value": "legacy-host"}},
            "invocation": {"argv": ["train.py"]},
        }
        (run_dir / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
        info = RunInfo(run_dir)
        assert info.hostname == "legacy-host"

    def test_legacy_unavailable_dict_hostname_becomes_none(self, runs_base):
        run_dir = runs_base / "pubrun-train-20260101T000000Z-999999-crash007"
        run_dir.mkdir()
        manifest = {
            "run": {"run_id": "crash007"}, "status": {"outcome": "crashed"},
            "host": {"hostname": {"representation": "unavailable", "value": None}},
        }
        (run_dir / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
        assert RunInfo(run_dir).hostname is None


# --------------------------------------------------------------------------
# BUG-60: selection parsing
# --------------------------------------------------------------------------

class TestBug60ParseSelection:
    def test_deduplicates_preserving_order(self):
        items = ["a", "b", "c", "d"]
        assert _parse_selection("3,1,3,1-2,2", items) == ["c", "a", "b"]

    def test_out_of_range_skipped(self):
        items = ["a", "b", "c"]
        assert _parse_selection("0,1,99,2", items) == ["a", "b"]
        assert _parse_selection("5-9", items) == []

    def test_huge_range_is_clamped_and_fast(self):
        items = ["a", "b", "c"]
        t0 = time.monotonic()
        assert _parse_selection("1-999999999", items) == ["a", "b", "c"]
        assert _parse_selection("2-999999999999999", items) == ["b", "c"]
        assert time.monotonic() - t0 < 1.0

    def test_empty_candidates(self):
        assert _parse_selection("1-5", []) == []


# --------------------------------------------------------------------------
# BUG-67: status column alignment and hyphenated script names
# --------------------------------------------------------------------------

class TestBug67Display:
    def _col_offsets(self, output):
        lines = [ANSI_RE.sub("", ln) for ln in output.splitlines()]
        header = lines[0]
        rows = [ln for ln in lines[2:] if ln.strip()][:2]
        return header, rows

    @pytest.mark.parametrize("no_color", [True, False])
    def test_exit_and_elapsed_align_with_header(self, runs_base, monkeypatch, no_color):
        if no_color:
            monkeypatch.setenv("NO_COLOR", "1")
        else:
            monkeypatch.delenv("NO_COLOR", raising=False)
        _make_completed(runs_base, "algn0001", age_seconds=100)
        _make_running(runs_base, "algn0002")
        runs = scan_runs(str(runs_base))
        output = render_short_list(runs)
        if not no_color:
            assert "\x1b[" in output
        header, rows = self._col_offsets(output)
        exit_col = header.index("EXIT")
        elapsed_col = header.index("ELAPSED")
        status_col = header.index("STATUS")
        assert len(rows) == 2
        for row in rows:
            status_text = row[status_col:exit_col].strip()
            assert status_text in (STATUS_COMPLETED, STATUS_RUNNING)
            assert row[exit_col - 1] == " "
            assert row[exit_col] != " "
            assert row[elapsed_col - 1] == " "
            assert row[elapsed_col] != " "

    def test_parse_dir_name_preserves_hyphenated_script(self, runs_base):
        run_dir = runs_base / "pubrun-my-train-script-20260101T000000Z-4242-abcd1234"
        run_dir.mkdir()
        info = RunInfo(run_dir)
        assert info.script == "my-train-script"
        assert info.run_id == "abcd1234"
        assert info.pid == 4242

    def test_parse_dir_name_simple_script(self, runs_base):
        run_dir = runs_base / "pubrun-train-20260101T000000Z-4242-abcd1234"
        run_dir.mkdir()
        info = RunInfo(run_dir)
        assert info.script == "train"
        assert info.run_id == "abcd1234"
