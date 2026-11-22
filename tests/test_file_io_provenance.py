"""Tests for IPD-E Phase 1: graded pubrun.open() provenance levels + /proc/self/io totals.

The `[capture.file_io].level` ladder is `none | name | stat | realpath | hash` (progressive;
default `stat`). `stat` records size/mtime/ctime (no hash); `hash` computes sha256 from the
on-disk bytes (correct regardless of read path); `none` records nothing. `/proc/self/io`
byte totals are captured (Linux) in the resource watcher's `io_counters`.
"""
import os
import sys
import json
import hashlib
import pytest
from pathlib import Path

import pubrun
import pubrun.tracker


@pytest.fixture
def tracked(tmp_path):
    """Factory: tracked(level) -> (manifest dict) after opening one input + one output."""
    def _factory(level=None, hashed_input=True):
        pubrun.tracker._active_run = None
        old = Path.cwd
        try:
            Path.cwd = staticmethod(lambda: tmp_path)
            kwargs = {"console": {"capture_mode": "off"}}
            if level is not None:
                kwargs["capture"] = {"file_io": {"level": level}}
            t = pubrun.start(**kwargs)
            inp = tmp_path / "in.txt"
            inp.write_text("alpha\nbeta\ngamma\n", encoding="utf-8")
            with pubrun.open(inp, "r") as f:
                f.read()
            out = tmp_path / "out.bin"
            with pubrun.open(out, "wb") as f:
                f.write(b"payload-bytes")
            t.stop()
            return json.loads((Path(t.run_dir) / "manifest.json").read_text()), tmp_path
        finally:
            Path.cwd = old
            pubrun.tracker._active_run = None
    return _factory


class TestFileIoLevels:

    def test_default_is_stat_metadata_no_hash(self, tracked):
        manifest, tmp = tracked()  # no level -> default stat
        inp = manifest["data_files"]["inputs"][0]
        assert inp["size_bytes"] == os.path.getsize(tmp / "in.txt")
        assert "mtime" in inp and "ctime" in inp
        assert inp["sha256"] is None  # stat level does NOT hash

    def test_hash_level_matches_on_disk(self, tracked):
        manifest, tmp = tracked("hash")
        inp = manifest["data_files"]["inputs"][0]
        out = manifest["data_files"]["outputs"][0]
        assert inp["sha256"] == hashlib.sha256((tmp / "in.txt").read_bytes()).hexdigest()
        # write-mode hash is the on-disk file too (correctness fix)
        assert out["sha256"] == hashlib.sha256(b"payload-bytes").hexdigest()

    def test_name_level_no_stat_no_hash(self, tracked):
        manifest, tmp = tracked("name")
        inp = manifest["data_files"]["inputs"][0]
        assert "path" in inp
        assert inp["sha256"] is None
        assert "size_bytes" not in inp  # name level records path only

    def test_realpath_level_includes_realpath_but_no_hash(self, tracked):
        manifest, tmp = tracked("realpath")
        inp = manifest["data_files"]["inputs"][0]
        assert "realpath" in inp
        assert "size_bytes" in inp  # realpath is above stat, so includes stat
        assert inp["sha256"] is None

    def test_none_level_records_nothing(self, tracked):
        manifest, tmp = tracked("none")
        assert manifest["data_files"]["inputs"] == []
        assert manifest["data_files"]["outputs"] == []

    def test_pubrun_open_returns_usable_file(self, tmp_path):
        """The proxy must behave like a normal file for reads/iteration/context mgmt."""
        pubrun.tracker._active_run = None
        old = Path.cwd
        try:
            Path.cwd = staticmethod(lambda: tmp_path)
            t = pubrun.start(console={"capture_mode": "off"})
            p = tmp_path / "data.txt"
            p.write_text("l1\nl2\nl3\n")
            with pubrun.open(p, "r") as f:
                assert f.readline() == "l1\n"
                assert [ln.strip() for ln in f] == ["l2", "l3"]  # iteration works
            t.stop()
        finally:
            Path.cwd = old
            pubrun.tracker._active_run = None

    def test_max_hash_bytes_skips_large_files(self, tmp_path):
        pubrun.tracker._active_run = None
        old = Path.cwd
        try:
            Path.cwd = staticmethod(lambda: tmp_path)
            t = pubrun.start(console={"capture_mode": "off"},
                             capture={"file_io": {"level": "hash", "max_hash_bytes": 4}})
            p = tmp_path / "big.bin"
            p.write_bytes(b"0123456789")  # 10 bytes > 4 cap
            with pubrun.open(p, "rb") as f:
                f.read()
            t.stop()
            m = json.loads((Path(t.run_dir) / "manifest.json").read_text())
            assert m["data_files"]["inputs"][0]["sha256"] is None  # skipped (too large)
        finally:
            Path.cwd = old
            pubrun.tracker._active_run = None


class TestProcIoCounters:

    @pytest.mark.skipif(not sys.platform.startswith("linux"), reason="Linux /proc/self/io")
    def test_get_proc_io_shape(self):
        from pubrun.capture.system_metrics import get_proc_io
        io = get_proc_io()
        assert io is not None
        assert "rchar" in io and "wchar" in io

    @pytest.mark.skipif(not sys.platform.startswith("linux"), reason="Linux /proc/self/io")
    def test_io_counters_in_manifest(self, tracked):
        manifest, tmp = tracked()
        io = manifest["resources"].get("io_counters")
        assert io is not None
        assert "start" in io and "last" in io


# ---------------------------------------------------------------------------
# Engine guarantees, budgets, identity checks, streaming, and proxy hardening
# ---------------------------------------------------------------------------

def _run_with_file_io(tmp_path, file_io_cfg, fn):
    """Helper running `fn(tmp_path, run)` inside an isolated tracked run."""
    pubrun.tracker._active_run = None
    old_cwd = Path.cwd
    try:
        Path.cwd = staticmethod(lambda: tmp_path)
        t = pubrun.start(
            console={"capture_mode": "off"},
            capture={"file_io": file_io_cfg},
        )
        try:
            fn(tmp_path, t)
        finally:
            t.stop()
        return json.loads((Path(t.run_dir) / "manifest.json").read_text(encoding="utf-8"))
    finally:
        Path.cwd = old_cwd
        pubrun.tracker._active_run = None


class TestDetailLevelHonesty:

    def test_all_five_levels_record_honest_status_and_evidence(self, tracked):
        m_none, _ = tracked("none")
        assert m_none["data_files"]["inputs"] == []
        assert m_none["data_files"]["outputs"] == []
        assert m_none["data_files"]["mixed"] == []
        assert "hashing_summary" not in m_none["data_files"]

        m_name, _ = tracked("name")
        inp_name = m_name["data_files"]["inputs"][0]
        assert "size_bytes" not in inp_name
        assert "mtime" not in inp_name
        assert "inode" not in inp_name
        assert inp_name["hash_status"] == "disabled"
        assert inp_name["evidence_source"] == "observed"
        assert inp_name["evidence_strength"] == "path_only"
        assert inp_name["sha256"] is None
        assert inp_name["digest"] is None

        m_stat, _ = tracked("stat")
        inp_stat = m_stat["data_files"]["inputs"][0]
        assert inp_stat["size_bytes"] > 0
        assert "mtime_ns" in inp_stat and "inode" in inp_stat and "device" in inp_stat
        assert "realpath" not in inp_stat
        assert inp_stat["hash_status"] == "disabled"
        assert inp_stat["evidence_source"] == "observed"
        assert inp_stat["evidence_strength"] == "metadata_only"
        assert inp_stat["sha256"] is None

        m_real, _ = tracked("realpath")
        inp_real = m_real["data_files"]["inputs"][0]
        assert "realpath" in inp_real
        assert inp_real["hash_status"] == "disabled"
        assert inp_real["evidence_source"] == "observed"
        assert inp_real["evidence_strength"] == "metadata_only"
        assert inp_real["sha256"] is None

        m_hash, _ = tracked("hash")
        inp_hash = m_hash["data_files"]["inputs"][0]
        assert inp_hash["hash_status"] == "completed"
        assert inp_hash["evidence_source"] == "observed"
        assert inp_hash["evidence_strength"] == "verified_content"
        assert inp_hash["digest"] == {"algorithm": "sha256", "value": inp_hash["sha256"]}
        assert "hashing_summary" in m_hash["data_files"]

    def test_name_level_performs_zero_fstat_or_stat_calls(self, tmp_path, monkeypatch):
        from pubrun.capture.file_io import FileIdentity

        p = tmp_path / "nostat.txt"
        p.write_text("hello", encoding="utf-8")

        def _forbid(*args, **kwargs):
            raise AssertionError("FileIdentity fstat/stat should not be called at level='name'")

        def _work(base, _run):
            with monkeypatch.context() as mp:
                mp.setattr(FileIdentity, "from_fd", staticmethod(_forbid))
                mp.setattr(FileIdentity, "from_path", staticmethod(_forbid))
                with pubrun.open(p, "r") as fh:
                    assert fh.read() == "hello"

        m = _run_with_file_io(tmp_path, {"level": "name"}, _work)
        inp = m["data_files"]["inputs"][0]
        assert "size_bytes" not in inp
        assert inp["evidence_strength"] == "path_only"


class TestHashingBudgets:

    def test_sparse_file_over_per_file_cap_zero_fallback_reads(self, tmp_path, monkeypatch):
        """A sparse multi-GiB file exceeding max_hash_bytes must skip hashing with zero reads."""
        import builtins
        from pubrun.capture.file_io import FileIoBudgetTracker, hash_file_checked

        sparse = tmp_path / "huge_sparse.bin"
        sparse_size = 10 * 1024 * 1024 * 1024  # 10 GiB logical size, ~0 disk blocks
        try:
            with builtins.open(sparse, "wb") as f:
                f.truncate(sparse_size)
            actual_size = os.path.getsize(sparse)
        except OSError:
            actual_size = 0

        if actual_size != sparse_size:
            pytest.skip("filesystem does not support 10 GiB sparse files")

        open_calls = []
        orig_open = builtins.open

        def _spy_open(*args, **kwargs):
            open_calls.append(args)
            return orig_open(*args, **kwargs)

        with monkeypatch.context() as mp:
            mp.setattr(builtins, "open", _spy_open)
            budget = FileIoBudgetTracker(max_hash_bytes=1024)
            res = hash_file_checked(sparse, budget=budget)

        assert res["hash_status"] == "over_budget"
        assert res["sha256"] is None
        assert res["digest"] is None
        assert res["hash_stats"]["bytes_hashed"] == 0
        assert res["hash_stats"]["extra_read_bytes"] == 0
        assert open_calls == []
        assert budget.files_skipped_over_budget == 1

    def test_mocked_terabyte_stat_cap_zero_content_reads(self, tmp_path, monkeypatch):
        """Cross-platform deterministic check: mocked multi-TB st_size skips with zero opens."""
        import builtins
        import types
        from pubrun.capture.file_io import FileIoBudgetTracker, hash_file_checked

        p = tmp_path / "tiny.bin"
        p.write_bytes(b"small")
        real_stat = os.stat(p)

        fake_stat = types.SimpleNamespace(
            st_dev=real_stat.st_dev,
            st_ino=real_stat.st_ino,
            st_size=2 * 1024**4,  # 2 TiB
            st_mtime=real_stat.st_mtime,
            st_ctime=real_stat.st_ctime,
            st_mtime_ns=real_stat.st_mtime_ns,
            st_mode=real_stat.st_mode,
        )

        def _forbid_open(*args, **kwargs):
            raise AssertionError("builtins.open must not be called when st_size > max_hash_bytes")

        with monkeypatch.context() as mp:
            mp.setattr(os, "stat", lambda _p, *a, **kw: fake_stat)
            mp.setattr(os, "lstat", lambda _p, *a, **kw: fake_stat)
            mp.setattr(builtins, "open", _forbid_open)
            budget = FileIoBudgetTracker(max_hash_bytes=1024)
            res = hash_file_checked(p, budget=budget)

        assert res["hash_status"] == "over_budget"
        assert res["sha256"] is None
        assert budget.total_bytes_hashed == 0
        assert budget.files_skipped_over_budget == 1

    def test_max_total_hash_bytes_caps_across_files_with_zero_fallback_reads(self, tmp_path):
        f1 = tmp_path / "f1.bin"
        f2 = tmp_path / "f2.bin"
        f1.write_bytes(b"a" * 16)
        f2.write_bytes(b"b" * 16)

        def _work(_base, _run):
            with pubrun.open(f1, "rb") as fh:
                assert fh.read() == b"a" * 16
            with pubrun.open(f2, "rb") as fh:
                assert fh.read() == b"b" * 16

        m = _run_with_file_io(
            tmp_path,
            {"level": "hash", "max_total_hash_bytes": 20},
            _work,
        )
        inputs = m["data_files"]["inputs"]
        assert len(inputs) == 2
        assert inputs[0]["hash_status"] == "completed"
        assert inputs[0]["sha256"] == hashlib.sha256(b"a" * 16).hexdigest()
        assert inputs[1]["hash_status"] == "over_budget"
        assert inputs[1]["sha256"] is None
        assert inputs[1]["digest"] is None
        assert inputs[1]["hash_stats"]["extra_read_bytes"] == 0
        summary = m["data_files"]["hashing_summary"]
        assert summary["total_bytes_hashed"] == 16
        assert summary["files_hashed"] == 1
        assert summary["files_skipped_over_budget"] == 1

    def test_max_total_hash_seconds_aborts_cleanly(self, tmp_path, monkeypatch):
        from pubrun.capture.file_io import FileIoBudgetTracker, hash_file_checked

        p = tmp_path / "slow.bin"
        p.write_bytes(b"x" * 200)

        # Advance monotonic clock by 1.5s on each chunk read.
        ticks = iter([10.0, 11.5, 11.5, 13.0, 13.0, 14.5])
        budget = FileIoBudgetTracker(max_total_hash_seconds=1.0)
        with monkeypatch.context() as mp:
            mp.setattr("pubrun.capture.file_io.time.monotonic", lambda: next(ticks))
            res = hash_file_checked(p, budget=budget, chunk_size=50)

        assert res["hash_status"] == "over_budget"
        assert res["sha256"] is None
        assert res["digest"] is None
        # Stopped after the very first chunk rather than reading the entire file.
        assert res["hash_stats"]["bytes_hashed"] == 50
        assert budget.files_skipped_over_budget == 1

        # Next file is skipped before even opening because time cap is already reached.
        p2 = tmp_path / "after_timeout.bin"
        p2.write_bytes(b"hello")
        res2 = hash_file_checked(p2, budget=budget)
        assert res2["hash_status"] == "over_budget"
        assert res2["hash_stats"]["bytes_hashed"] == 0
        assert budget.files_skipped_over_budget == 2


class TestErrorsAndSpecialFiles:

    def test_permission_error_records_failed(self, tmp_path, monkeypatch):
        import builtins
        from pubrun.capture.file_io import FileIoBudgetTracker, hash_file_checked

        p = tmp_path / "secret.bin"
        p.write_bytes(b"topsecret")

        def _deny(*args, **kwargs):
            raise PermissionError("access denied")

        with monkeypatch.context() as mp:
            mp.setattr(builtins, "open", _deny)
            budget = FileIoBudgetTracker()
            res = hash_file_checked(p, budget=budget)

        assert res["hash_status"] == "failed"
        assert "PermissionError" in (res["hash_status_detail"] or "")
        assert res["sha256"] is None
        assert res["digest"] is None
        assert budget.files_failed == 1

    def test_directory_and_missing_refuse_hashing_as_unavailable(self, tmp_path):
        from pubrun.capture.file_io import hash_file_checked

        sub = tmp_path / "subdir"
        sub.mkdir()
        res_dir = hash_file_checked(sub)
        assert res_dir["hash_status"] == "unavailable"
        assert res_dir["entry_type"] == "directory"
        assert res_dir["sha256"] is None

        res_missing = hash_file_checked(tmp_path / "does_not_exist.bin")
        assert res_missing["hash_status"] == "unavailable"
        assert res_missing["entry_type"] == "missing"
        assert res_missing["sha256"] is None

    @pytest.mark.skipif(not hasattr(os, "mkfifo"), reason="POSIX FIFO required")
    def test_fifo_refuses_hashing_without_hanging(self, tmp_path, monkeypatch):
        import builtins
        from pubrun.capture.file_io import hash_file_checked

        fifo = tmp_path / "pipe.fifo"
        os.mkfifo(fifo)

        def _forbid_open(*args, **kwargs):
            raise AssertionError("hash_file_checked must never open a FIFO")

        with monkeypatch.context() as mp:
            mp.setattr(builtins, "open", _forbid_open)
            res = hash_file_checked(fifo)
        assert res["hash_status"] == "unavailable"
        assert res["entry_type"] == "special"
        assert res["sha256"] is None
        assert res["digest"] is None


class TestChangeDetection:

    def test_modified_in_place_between_open_and_close_sets_file_changed(self, tmp_path):
        p = tmp_path / "mutable.bin"
        p.write_bytes(b"original-content")

        def _work(_base, _run):
            with pubrun.open(p, "rb") as fh:
                assert fh.read(8) == b"original"
                # Mutate the same inode before close()
                with open(p, "ab") as writer:
                    writer.write(b"-mutated-extra")

        m = _run_with_file_io(tmp_path, {"level": "hash"}, _work)
        inp = m["data_files"]["inputs"][0]
        assert inp["hash_status"] == "file_changed"
        assert inp["change_detected"] is True
        assert inp["sha256"] is None
        assert inp["digest"] is None
        assert inp["evidence_strength"] == "changed_unverified"
        assert inp["change_details"] is not None
        assert m["data_files"]["hashing_summary"]["files_changed"] == 1

    def test_replaced_file_between_open_and_close_on_text_read_sets_file_changed(self, tmp_path):
        p = tmp_path / "replaced.txt"
        p.write_text("version 1\n", encoding="utf-8")

        def _work(_base, _run):
            with pubrun.open(p, "r", encoding="utf-8") as fh:
                assert fh.read() == "version 1\n"
                replacement = tmp_path / "replacement.txt"
                replacement.write_text("version 2 is different\n", encoding="utf-8")
                os.replace(replacement, p)

        m = _run_with_file_io(tmp_path, {"level": "hash"}, _work)
        inp = m["data_files"]["inputs"][0]
        assert inp["hash_status"] == "file_changed"
        assert inp["change_detected"] is True
        assert inp["sha256"] is None
        assert inp["digest"] is None
        assert inp["evidence_strength"] == "changed_unverified"

    def test_file_modified_during_hash_file_checked_sets_file_changed(self, tmp_path, monkeypatch):
        from pubrun.capture.file_io import FileIdentity, hash_file_checked

        p = tmp_path / "midhash.bin"
        p.write_bytes(b"0123456789abcdef")
        orig_from_fd = FileIdentity.from_fd
        call_count = {"n": 0}

        def _mutating_from_fd(fd):
            call_count["n"] += 1
            ident = orig_from_fd(fd)
            if call_count["n"] == 2 and ident is not None:
                return FileIdentity(
                    device=ident.device,
                    inode=ident.inode,
                    size_bytes=ident.size_bytes + 4,
                    mtime=ident.mtime + 1.0,
                    ctime=ident.ctime,
                    mtime_ns=ident.mtime_ns + 1_000_000_000,
                    mode=ident.mode,
                )
            return ident

        monkeypatch.setattr(FileIdentity, "from_fd", staticmethod(_mutating_from_fd))
        res = hash_file_checked(p)
        assert res["hash_status"] == "file_changed"
        assert res["change_detected"] is True
        assert res["sha256"] is None
        assert res["digest"] is None

    def test_file_identity_zero_inode_comparison(self):
        from pubrun.capture.file_io import FileIdentity

        a = FileIdentity(device=1, inode=0, size_bytes=10, mtime=1.0, ctime=1.0, mtime_ns=100, mode=0o100644)
        b = FileIdentity(device=2, inode=0, size_bytes=10, mtime=1.0, ctime=1.0, mtime_ns=100, mode=0o100644)
        c = FileIdentity(device=1, inode=0, size_bytes=11, mtime=1.0, ctime=1.0, mtime_ns=100, mode=0o100644)
        assert a.matches(b) is True
        assert a.matches(c) is False


class TestStreamingVsFallback:

    def test_sequential_binary_read_hashes_during_stream(self, tmp_path):
        p = tmp_path / "seq.bin"
        payload = b"line1\nline2\nline3\n"
        p.write_bytes(payload)

        def _work(_base, _run):
            with pubrun.open(p, "rb") as fh:
                assert fh.read() == payload

        m = _run_with_file_io(tmp_path, {"level": "hash"}, _work)
        inp = m["data_files"]["inputs"][0]
        assert inp["hash_status"] == "completed"
        assert inp["observation_time"] == "during_stream"
        assert inp["hash_stats"]["extra_read_bytes"] == 0
        assert inp["hash_stats"]["bytes_hashed"] == len(payload)
        assert inp["sha256"] == hashlib.sha256(payload).hexdigest()
        assert m["data_files"]["hashing_summary"]["total_bytes_hashed"] == len(payload)

    def test_sequential_binary_iteration_hashes_during_stream(self, tmp_path):
        p = tmp_path / "lines.bin"
        payload = b"alpha\nbeta\ngamma\n"
        p.write_bytes(payload)

        def _work(_base, _run):
            collected = []
            with pubrun.open(p, "rb") as fh:
                for line in fh:
                    collected.append(line)
            assert b"".join(collected) == payload

        m = _run_with_file_io(tmp_path, {"level": "hash"}, _work)
        inp = m["data_files"]["inputs"][0]
        assert inp["hash_status"] == "completed"
        assert inp["observation_time"] == "during_stream"
        assert inp["hash_stats"]["extra_read_bytes"] == 0
        assert inp["sha256"] == hashlib.sha256(payload).hexdigest()

    def test_sequential_binary_readinto_bytearray_and_array(self, tmp_path):
        import array

        p1 = tmp_path / "ba.bin"
        p1.write_bytes(b"0123456789abcdef")

        p2 = tmp_path / "arr.bin"
        src_arr = array.array("i", [10, 20, 30, 40])
        raw_arr_bytes = src_arr.tobytes()
        p2.write_bytes(raw_arr_bytes)

        def _work(_base, _run):
            with pubrun.open(p1, "rb") as fh:
                buf = bytearray(6)
                out = bytearray()
                while True:
                    n = fh.readinto(buf)
                    if not n:
                        break
                    out.extend(buf[:n])
                assert bytes(out) == b"0123456789abcdef"

            with pubrun.open(p2, "rb") as fh:
                dst_arr = array.array("i", [0, 0, 0, 0])
                n = fh.readinto(dst_arr)
                assert n == len(raw_arr_bytes)
                assert dst_arr.tobytes() == raw_arr_bytes

        m = _run_with_file_io(tmp_path, {"level": "hash"}, _work)
        inputs = m["data_files"]["inputs"]
        assert len(inputs) == 2
        assert inputs[0]["observation_time"] == "during_stream"
        assert inputs[0]["hash_stats"]["extra_read_bytes"] == 0
        assert inputs[0]["sha256"] == hashlib.sha256(b"0123456789abcdef").hexdigest()

        assert inputs[1]["observation_time"] == "during_stream"
        assert inputs[1]["hash_stats"]["extra_read_bytes"] == 0
        assert inputs[1]["sha256"] == hashlib.sha256(raw_arr_bytes).hexdigest()

    def test_sequential_binary_write_and_writelines_hash_during_stream(self, tmp_path):
        p1 = tmp_path / "w1.bin"
        p2 = tmp_path / "w2.bin"

        def _work(_base, _run):
            with pubrun.open(p1, "wb") as fh:
                fh.write(b"part1-")
                fh.write(memoryview(b"part2"))
            with pubrun.open(p2, "wb") as fh:
                # Single-use generator ensures writelines does not double-consume.
                fh.writelines(chunk for chunk in [b"a", b"b", b"c"])

        m = _run_with_file_io(tmp_path, {"level": "hash"}, _work)
        outputs = m["data_files"]["outputs"]
        assert len(outputs) == 2
        assert outputs[0]["observation_time"] == "during_stream"
        assert outputs[0]["hash_stats"]["extra_read_bytes"] == 0
        assert outputs[0]["sha256"] == hashlib.sha256(b"part1-part2").hexdigest()

        assert outputs[1]["observation_time"] == "during_stream"
        assert outputs[1]["hash_stats"]["extra_read_bytes"] == 0
        assert outputs[1]["sha256"] == hashlib.sha256(b"abc").hexdigest()

    def test_partial_read_seek_reread_and_raw_access_fallback_without_double_counting(self, tmp_path):
        payload = b"0123456789abcdef"
        p_partial = tmp_path / "partial.bin"
        p_seek = tmp_path / "seek.bin"
        p_raw = tmp_path / "raw.bin"
        for p in (p_partial, p_seek, p_raw):
            p.write_bytes(payload)

        def _work(_base, _run):
            with pubrun.open(p_partial, "rb") as fh:
                assert fh.read(4) == b"0123"
            with pubrun.open(p_seek, "rb") as fh:
                assert fh.read(6) == b"012345"
                fh.seek(0)
                assert fh.read() == payload
            with pubrun.open(p_raw, "rb") as fh:
                _ = fh.raw
                assert fh.read() == payload

        m = _run_with_file_io(tmp_path, {"level": "hash"}, _work)
        inputs = m["data_files"]["inputs"]
        assert len(inputs) == 3
        expected = hashlib.sha256(payload).hexdigest()
        for rec in inputs:
            assert rec["hash_status"] == "completed"
            assert rec["observation_time"] == "at_close"
            assert rec["sha256"] == expected
            assert rec["hash_stats"]["extra_read_bytes"] == len(payload)

        # Total bytes hashed across all three files is 3 * len(payload), NOT double-counted.
        assert m["data_files"]["hashing_summary"]["total_bytes_hashed"] == 3 * len(payload)
        assert m["data_files"]["hashing_summary"]["files_hashed"] == 3

    def test_text_and_append_modes_fallback_with_exact_whole_file_digests(self, tmp_path):
        p_txt = tmp_path / "text.txt"
        p_txt.write_text("hello text\n", encoding="utf-8")
        p_out = tmp_path / "out.txt"
        p_app = tmp_path / "append.bin"
        p_app.write_bytes(b"prefix-")

        def _work(_base, _run):
            with pubrun.open(p_txt, "r", encoding="utf-8") as fh:
                assert fh.read() == "hello text\n"
            with pubrun.open(p_out, "w", encoding="utf-8") as fh:
                fh.write("written text\n")
            with pubrun.open(p_app, "ab") as fh:
                fh.write(b"suffix")

        m = _run_with_file_io(tmp_path, {"level": "hash"}, _work)
        inp = m["data_files"]["inputs"][0]
        assert inp["observation_time"] == "at_close"
        assert inp["sha256"] == hashlib.sha256(p_txt.read_bytes()).hexdigest()

        out_w, out_a = m["data_files"]["outputs"]
        assert out_w["observation_time"] == "at_close"
        assert out_w["open_disposition"] == "write"
        assert out_w["sha256"] == hashlib.sha256(p_out.read_bytes()).hexdigest()

        assert out_a["observation_time"] == "at_close"
        assert out_a["open_disposition"] == "append"
        assert out_a["sha256"] == hashlib.sha256(b"prefix-suffix").hexdigest()


class TestMixedModesAndAlgorithms:

    def test_classify_open_mode_covers_all_python_modes(self):
        from pubrun.capture.file_io import classify_open_mode

        assert classify_open_mode("r") == ("input", "read")
        assert classify_open_mode("rb") == ("input", "read")
        assert classify_open_mode("w") == ("output", "write")
        assert classify_open_mode("wb") == ("output", "write")
        assert classify_open_mode("a") == ("output", "append")
        assert classify_open_mode("ab") == ("output", "append")
        assert classify_open_mode("x") == ("output", "exclusive_create")
        assert classify_open_mode("xb") == ("output", "exclusive_create")
        for mixed in ("r+", "rb+", "r+b", "w+", "wb+", "a+", "ab+", "x+", "xb+"):
            assert classify_open_mode(mixed) == ("input_output", "read_write")

    def test_mixed_modes_land_in_data_files_mixed_with_whole_file_digests(self, tmp_path):
        p_rp = tmp_path / "rp.bin"
        p_rp.write_bytes(b"abcd")
        p_wp = tmp_path / "wp.bin"
        p_ap = tmp_path / "ap.bin"
        p_ap.write_bytes(b"start-")
        p_xp = tmp_path / "xp.bin"

        def _work(_base, _run):
            with pubrun.open(p_rp, "r+b") as fh:
                assert fh.read(2) == b"ab"
                fh.write(b"XY")
            with pubrun.open(p_wp, "w+b") as fh:
                fh.write(b"hello")
                fh.seek(0)
                assert fh.read() == b"hello"
            with pubrun.open(p_ap, "a+b") as fh:
                fh.write(b"end")
                fh.seek(0)
                assert fh.read() == b"start-end"
            with pubrun.open(p_xp, "x+b") as fh:
                fh.write(b"created")
                fh.seek(0)
                assert fh.read() == b"created"

        m = _run_with_file_io(tmp_path, {"level": "hash"}, _work)
        assert m["data_files"]["inputs"] == []
        assert m["data_files"]["outputs"] == []
        mixed = m["data_files"]["mixed"]
        assert len(mixed) == 4
        expected_contents = [b"abXY", b"hello", b"start-end", b"created"]
        for rec, content in zip(mixed, expected_contents):
            assert rec["role"] == "input_output"
            assert rec["open_disposition"] == "read_write"
            assert rec["hash_status"] == "completed"
            assert rec["observation_time"] == "at_close"
            assert rec["sha256"] == hashlib.sha256(content).hexdigest()

    def test_non_sha256_algorithm_and_invalid_algorithm_fallback(self, tmp_path, caplog):
        p = tmp_path / "alg.bin"
        p.write_bytes(b"digest-test")

        def _work(_base, _run):
            with pubrun.open(p, "rb") as fh:
                fh.read()

        m512 = _run_with_file_io(
            tmp_path,
            {"level": "hash", "hash_algorithm": "sha512"},
            _work,
        )
        rec = m512["data_files"]["inputs"][0]
        assert rec["hash_status"] == "completed"
        assert rec["hash_algorithm"] == "sha512"
        assert rec["sha256"] is None
        assert rec["digest"] == {
            "algorithm": "sha512",
            "value": hashlib.sha512(b"digest-test").hexdigest(),
        }

        with caplog.at_level("WARNING", logger="pubrun"):
            m_bad = _run_with_file_io(
                tmp_path,
                {"level": "hash", "hash_algorithm": "not-a-real-algo-xxi3nc"},
                _work,
            )
        rec_bad = m_bad["data_files"]["inputs"][0]
        assert rec_bad["hash_algorithm"] == "sha256"
        assert rec_bad["sha256"] == hashlib.sha256(b"digest-test").hexdigest()
        assert any("not-a-real-algo-xxi3nc" in r.message for r in caplog.records)


class TestDeduplicationAndHostPreservation:

    def test_append_or_deduplicate_record_behavior(self, tmp_path):
        from pubrun.capture.file_io import (
            append_or_deduplicate_record,
            finalize_pending_registrations,
        )

        class _DummyRun:
            def __init__(self):
                self.data_files = {"inputs": [], "outputs": [], "mixed": []}

        run = _DummyRun()
        finalize_pending_registrations(run)  # clean no-op hook

        base = {
            "path": "/tmp/a.bin",
            "role": "input",
            "label": "train",
            "device": 1,
            "inode": 42,
            "size_bytes": 10,
            "mtime_ns": 1000,
            "hash_status": "completed",
            "digest": {"algorithm": "sha256", "value": "aaa"},
            "registration_count": 1,
            "last_observed_at_utc": 1.0,
        }
        r1 = append_or_deduplicate_record(run, dict(base))
        r2 = append_or_deduplicate_record(run, {**base, "last_observed_at_utc": 2.0})
        assert r1 is r2
        assert len(run.data_files["inputs"]) == 1
        assert r1["registration_count"] == 2
        assert r1["last_observed_at_utc"] == 2.0

        # Changed digest/mtime preserves a distinct record.
        r3 = append_or_deduplicate_record(
            run,
            {
                **base,
                "mtime_ns": 2000,
                "digest": {"algorithm": "sha256", "value": "bbb"},
            },
        )
        assert r3 is not r1
        assert len(run.data_files["inputs"]) == 2

    def test_builtins_open_unpatched_integer_fd_and_host_exceptions_preserved(self, tmp_path):
        import builtins

        orig_open = builtins.open

        def _work(base, _run):
            assert builtins.open is orig_open

            with pytest.raises(FileNotFoundError):
                pubrun.open(base / "nonexistent.txt", "r")

            # Integer file descriptor passes through cleanly without wrapping failure.
            p = base / "fd_test.txt"
            p.write_text("from-fd", encoding="utf-8")
            fd = os.open(p, os.O_RDONLY)
            with pubrun.open(fd, "r", encoding="utf-8") as fh:
                assert fh.read() == "from-fd"

        m = _run_with_file_io(tmp_path, {"level": "hash"}, _work)
        assert builtins.open is orig_open
        assert m["data_files"]["inputs"] == []
