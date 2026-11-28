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
            monkeypatch.delenv("FORCE_COLOR", raising=False)
        else:
            monkeypatch.delenv("NO_COLOR", raising=False)
            monkeypatch.setenv("FORCE_COLOR", "1")
        _make_completed(runs_base, "algn0001", age_seconds=100)
        _make_running(runs_base, "algn0002")
        runs = scan_runs(str(runs_base))
        output = render_short_list(runs)
        if not no_color:
            assert "\x1b[" in output
            assert "\x1b[2m" not in output
        else:
            assert "\x1b[" not in output
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

    def test_non_tty_piped_status_emits_no_ansi(self, runs_base, monkeypatch):
        import sys as _sys

        monkeypatch.delenv("NO_COLOR", raising=False)
        monkeypatch.delenv("FORCE_COLOR", raising=False)
        monkeypatch.setattr(_sys.stdout, "isatty", lambda: False)
        _make_completed(runs_base, "pipe0001", age_seconds=60)
        runs = scan_runs(str(runs_base))
        output = render_short_list(runs)
        assert "\x1b[" not in output

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


# --------------------------------------------------------------------------
# BUG-C1 & BUG-U5: _resolve_output_dir non-dict/non-string safety and $VAR expansion
# --------------------------------------------------------------------------

class TestResolveOutputDirHardening:
    def test_scan_runs_tolerates_non_dict_core_section(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        (tmp_path / ".pubrun.toml").write_text('core = "bad"\n', encoding="utf-8")
        default_runs = tmp_path / "runs"
        default_runs.mkdir()
        _make_completed(default_runs, "nondict1", age_seconds=10)
        runs = scan_runs()
        assert [r.run_id for r in runs] == ["nondict1"]

    def test_scan_runs_tolerates_non_string_output_dir(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        (tmp_path / ".pubrun.toml").write_text("[core]\noutput_dir = 123\n", encoding="utf-8")
        default_runs = tmp_path / "runs"
        default_runs.mkdir()
        _make_completed(default_runs, "badtype1", age_seconds=10)
        runs = scan_runs()
        assert [r.run_id for r in runs] == ["badtype1"]

    def test_scan_runs_expands_env_vars_in_config_and_explicit_output_dir(
        self, tmp_path, monkeypatch
    ):
        target = tmp_path / "expanded_base" / "sub"
        target.mkdir(parents=True)
        _make_completed(target, "envexp01", age_seconds=10)
        monkeypatch.setenv("PUBRUN_TEST_STATUS_BASE", str(tmp_path / "expanded_base"))

        # Explicit str and Path with $VAR
        assert [r.run_id for r in scan_runs("$PUBRUN_TEST_STATUS_BASE/sub")] == ["envexp01"]
        assert [r.run_id for r in scan_runs(Path("$PUBRUN_TEST_STATUS_BASE/sub"))] == ["envexp01"]

        # Config-derived output_dir with $VAR
        monkeypatch.chdir(tmp_path)
        (tmp_path / ".pubrun.toml").write_text(
            '[core]\noutput_dir = "$PUBRUN_TEST_STATUS_BASE/sub"\n',
            encoding="utf-8",
        )
        assert [r.run_id for r in scan_runs()] == ["envexp01"]


# --------------------------------------------------------------------------
# BUG-C3: lockless startup manifest with outcome == "running"
# --------------------------------------------------------------------------

class TestLocklessRunningManifestClassification:
    def _write_lockless_running(
        self,
        base: Path,
        run_id: str,
        *,
        pid=None,
        hostname=None,
        started_at_utc=None,
    ) -> Path:
        run_dir = base / f"pubrun-worker-20260101T000000Z-1111-{run_id}"
        run_dir.mkdir(parents=True)
        manifest = {
            "schema_version": "1.0",
            "run": {"run_id": run_id},
            "status": {"outcome": "running"},
            "timing": {"started_at_utc": started_at_utc},
            "process": {"pid": pid} if pid is not None else {},
            "host": {"hostname": hostname} if hostname is not None else {},
        }
        (run_dir / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
        return run_dir

    def test_lockless_running_manifest_dead_pid_classifies_as_crashed(self, runs_base):
        from pubrun.capture.liveness import get_hostname
        from pubrun.status import STATUS_CRASHED

        run_dir = self._write_lockless_running(
            runs_base,
            "deadpid1",
            pid=99999999,
            hostname=get_hostname(),
            started_at_utc=time.time() - 60.0,
        )
        info = RunInfo(run_dir)
        assert info.status == STATUS_CRASHED

    def test_lockless_running_manifest_missing_pid_classifies_as_crashed(self, runs_base):
        from pubrun.capture.liveness import get_hostname
        from pubrun.status import STATUS_CRASHED

        run_dir = self._write_lockless_running(
            runs_base,
            "nopid001",
            pid=None,
            hostname=get_hostname(),
            started_at_utc=time.time() - 60.0,
        )
        info = RunInfo(run_dir)
        assert info.status == STATUS_CRASHED

    def test_lockless_running_manifest_remote_hostname_classifies_as_crashed(self, runs_base):
        import os
        from pubrun.capture.liveness import get_process_start_time
        from pubrun.status import STATUS_CRASHED

        pid = os.getpid()
        started = get_process_start_time(pid) or time.time()
        run_dir = self._write_lockless_running(
            runs_base,
            "remhost1",
            pid=pid,
            hostname="remote-host-that-is-not-this-one.invalid",
            started_at_utc=started,
        )
        info = RunInfo(run_dir)
        assert info.status == STATUS_CRASHED

    def test_lockless_running_manifest_live_local_pid_classifies_as_running(self, runs_base):
        import os
        from pubrun.capture.liveness import get_hostname, get_process_start_time

        pid = os.getpid()
        started = get_process_start_time(pid) or time.time()
        run_dir = self._write_lockless_running(
            runs_base,
            "livepid1",
            pid=pid,
            hostname=get_hostname(),
            started_at_utc=started,
        )
        info = RunInfo(run_dir)
        assert info.status == STATUS_RUNNING
        assert info.elapsed is not None and info.elapsed >= 0.0


# --------------------------------------------------------------------------
# BUG-C6: find_run whitespace stripping and multi-collision recency ambiguity
# --------------------------------------------------------------------------

class TestFindRunStrippingAndMultiCollision:
    def test_find_run_strips_whitespace_for_prefix_and_substring(self, runs_base):
        from pubrun.status import find_run

        _make_completed(runs_base, "abcd9999", age_seconds=20, script="train")
        _make_completed(runs_base, "zzzz1111", age_seconds=10, script="eval")

        by_prefix = find_run(" abcd ", str(runs_base))
        assert by_prefix is not None
        assert by_prefix.run_id == "abcd9999"

        by_substr = find_run(" train ", str(runs_base))
        assert by_substr is not None
        assert by_substr.run_id == "abcd9999"

    def test_find_run_raises_ambiguous_with_all_candidates_on_multi_id_recency_collision(
        self, runs_base
    ):
        from pubrun.status import AmbiguousRunSelectorError, find_run

        # Two older runs sharing run_id="1" plus a newer run at recency index 1.
        _make_completed(runs_base, "1", age_seconds=300, script="older_a")
        _make_completed(runs_base, "1", age_seconds=200, script="older_b")
        _make_completed(runs_base, "newest99", age_seconds=10, script="newest")

        with pytest.raises(AmbiguousRunSelectorError) as exc_info:
            find_run("1", str(runs_base))

        err = exc_info.value
        assert err.by_recency is not None
        assert err.by_recency.run_id == "newest99"
        assert err.by_id is not None
        assert err.by_id.run_id == "1"
        assert len(err.candidates) == 3
        candidate_dirs = {c.run_dir.name for c in err.candidates}
        assert len(candidate_dirs) == 3


# --------------------------------------------------------------------------
# BUG-C10: _dir_size symlinks/OSError and RunInfo non-dict JSON degradation
# --------------------------------------------------------------------------

class TestDirSizeAndNonDictJsonResilience:
    def test_dir_size_skips_symlinks_and_tolerates_per_entry_oserror(
        self, tmp_path, monkeypatch
    ):
        import os
        from pubrun.status import _dir_size

        external = tmp_path / "external_big.bin"
        external.write_bytes(b"x" * 10000)

        run_dir = tmp_path / "run_sizing"
        run_dir.mkdir()
        keep = run_dir / "keep.bin"
        keep.write_bytes(b"a" * 120)
        unreadable = run_dir / "vanishing.bin"
        unreadable.write_bytes(b"b" * 50)

        symlink_created = False
        try:
            os.symlink(external, run_dir / "link_to_external.bin")
            os.symlink(tmp_path / "missing_target.bin", run_dir / "broken_link.bin")
            symlink_created = True
        except OSError:
            symlink_created = False

        # First verify symlinks are excluded (only keep + unreadable = 170 bytes).
        assert _dir_size(run_dir) == 170
        if symlink_created:
            assert (run_dir / "link_to_external.bin").is_symlink()

        # Now simulate a per-entry OSError on one file; the other file is still counted.
        orig_stat = Path.stat

        def flaky_stat(self, *args, **kwargs):
            if self.name == "vanishing.bin":
                raise OSError("entry vanished")
            return orig_stat(self, *args, **kwargs)

        monkeypatch.setattr(Path, "stat", flaky_stat)
        assert _dir_size(run_dir) == 120

    @pytest.mark.parametrize(
        "payload",
        [
            "[]",
            "null",
            '{"run": null, "status": null, "git": [], "invocation": {"script": "bad", "argv": 123}, "signals": "bad", "process": 42}',
        ],
    )
    def test_run_info_degrades_safely_on_non_dict_manifest_and_malformed_sections(
        self, runs_base, payload
    ):
        from pubrun.status import STATUS_CRASHED

        run_dir = runs_base / "pubrun-badjson-20260101T000000Z-1234-badj0001"
        run_dir.mkdir()
        (run_dir / "manifest.json").write_text(payload, encoding="utf-8")

        info = RunInfo(run_dir)
        if payload in ("[]", "null"):
            assert info.status == STATUS_CRASHED
            assert info.manifest is None
            assert info.run_id == "badj0001"
        else:
            assert info.run_id is None
            assert info.script is None
            assert info.args is None
            assert info.pid is None

    @pytest.mark.parametrize("payload", ["[]", "null"])
    def test_run_info_degrades_to_crashed_on_non_dict_lock_and_enrich_manifest(
        self, runs_base, payload
    ):
        from pubrun.status import STATUS_CRASHED

        lock_dir = runs_base / "pubrun-badlock-20260101T000000Z-1234-badl0001"
        lock_dir.mkdir()
        (lock_dir / ".pubrun.lock").write_text(payload, encoding="utf-8")
        info = RunInfo(lock_dir)
        assert info.status == STATUS_CRASHED
        assert info.lock_data is None
        assert info.run_id == "badl0001"

        enrich_dir = runs_base / "pubrun-enrich-20260101T000000Z-999999-enr00001"
        enrich_dir.mkdir()
        (enrich_dir / ".pubrun.lock").write_text(
            json.dumps({"run_id": "enr00001", "pid": 999999, "started_at_utc": 1700000000.0}),
            encoding="utf-8",
        )
        (enrich_dir / "manifest.json").write_text(payload, encoding="utf-8")
        enriched = RunInfo(enrich_dir)
        assert enriched.status == STATUS_CRASHED
        assert enriched.manifest is None


# --------------------------------------------------------------------------
# TEST-U11: close_out_crashed_run TOCTOU refusal and empty-lock fallback
# --------------------------------------------------------------------------

class TestCrashCloseoutToctouAndEmptyLockFallback:
    def test_close_out_crashed_run_refuses_live_local_pid_toctou(self, runs_base):
        import os
        from pubrun.capture.liveness import get_hostname, get_process_start_time

        pid = os.getpid()
        started = get_process_start_time(pid) or time.time()
        run_dir = runs_base / f"pubrun-live-20260101T000000Z-{pid}-toctou01"
        run_dir.mkdir()
        lock = {
            "run_id": "toctou01",
            "pid": pid,
            "started_at_utc": started,
            "hostname": get_hostname(),
        }
        (run_dir / ".pubrun.lock").write_text(json.dumps(lock), encoding="utf-8")
        startup_manifest = {
            "schema_version": "1.0",
            "run": {"run_id": "toctou01"},
            "status": {"outcome": "running"},
            "timing": {"started_at_utc": started},
        }
        (run_dir / "manifest.json").write_text(json.dumps(startup_manifest), encoding="utf-8")

        close_out_crashed_run(run_dir, lock)

        assert (run_dir / ".pubrun.lock").exists()
        after = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
        assert after["status"]["outcome"] == "running"

    def test_close_out_crashed_run_reconstructs_run_id_and_mtime_from_empty_lock(
        self, runs_base
    ):
        import os

        run_dir = runs_base / "pubrun-train-20260101T000000Z-999999-deadbeef"
        run_dir.mkdir()
        lock_path = run_dir / ".pubrun.lock"
        lock_path.write_text("{}", encoding="utf-8")
        fixed_mtime = 1700001234.0
        os.utime(lock_path, (fixed_mtime, fixed_mtime))

        close_out_crashed_run(run_dir, {})

        assert not lock_path.exists()
        manifest = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
        assert manifest["run"]["run_id"] == "deadbeef"
        assert manifest["status"]["outcome"] == "crashed"
        assert abs(manifest["timing"]["started_at_utc"] - fixed_mtime) < 2.0
