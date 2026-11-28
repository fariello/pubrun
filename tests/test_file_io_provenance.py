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
        try:
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
        try:
            t = pubrun.start(console={"capture_mode": "off"})
            p = tmp_path / "data.txt"
            p.write_text("l1\nl2\nl3\n")
            with pubrun.open(p, "r") as f:
                assert f.readline() == "l1\n"
                assert [ln.strip() for ln in f] == ["l2", "l3"]  # iteration works
            t.stop()
        finally:
            pubrun.tracker._active_run = None

    def test_max_hash_bytes_skips_large_files(self, tmp_path):
        pubrun.tracker._active_run = None
        try:
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
    try:
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
                if os.name == "nt":
                    # Windows NTFS forbids os.replace() while the target has an open handle;
                    # mutate in place to exercise text-read change detection on Windows.
                    with open(p, "a", encoding="utf-8") as writer:
                        writer.write("version 2 is different\n")
                else:
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


class TestProxyEdgeMethods:

    def test_read1_stream_hashes_and_sets_eof(self, tmp_path):
        p = tmp_path / "read1.bin"
        payload = bytes(range(100))
        p.write_bytes(payload)

        def _work(_base, _run):
            chunks = []
            with pubrun.open(p, "rb") as fh:
                while True:
                    chunk = fh.read1(16)
                    if not chunk:
                        break
                    chunks.append(chunk)
            assert b"".join(chunks) == payload

        m = _run_with_file_io(tmp_path, {"level": "hash"}, _work)
        rec = m["data_files"]["inputs"][0]
        assert rec["access_observations"]["eof_reached"] is True
        assert rec["access_observations"]["bytes_read"] == 100
        assert rec["hash_status"] == "completed"
        assert rec["observation_time"] == "during_stream"
        assert rec["sha256"] == hashlib.sha256(payload).hexdigest()

    def test_readinto1_stream_hashes_and_sets_eof(self, tmp_path):
        p = tmp_path / "readinto1.bin"
        payload = (b"abcdefgh" * 96)  # 768 bytes
        assert len(payload) == 768
        p.write_bytes(payload)

        def _work(_base, _run):
            out = bytearray()
            buf = bytearray(100)
            with pubrun.open(p, "rb") as fh:
                while True:
                    n = fh.readinto1(buf)
                    if not n:
                        break
                    out.extend(buf[:n])
            assert bytes(out) == payload

        m = _run_with_file_io(tmp_path, {"level": "hash"}, _work)
        rec = m["data_files"]["inputs"][0]
        assert rec["access_observations"]["eof_reached"] is True
        assert rec["observation_time"] == "during_stream"
        assert rec["hash_stats"]["extra_read_bytes"] == 0
        assert rec["sha256"] == hashlib.sha256(payload).hexdigest()

    def test_binary_readlines_hint_controls_eof(self, tmp_path):
        payload = b"a\nb\nc\n"
        p_partial = tmp_path / "partial.bin"
        p_full = tmp_path / "full.bin"
        p_partial.write_bytes(payload)
        p_full.write_bytes(payload)

        def _work(_base, _run):
            with pubrun.open(p_partial, "rb") as fh:
                assert fh.readlines(1) == [b"a\n"]
            with pubrun.open(p_full, "rb") as fh:
                assert fh.readlines() == [b"a\n", b"b\n", b"c\n"]

        m = _run_with_file_io(tmp_path, {"level": "hash"}, _work)
        by_name = {Path(r["path"]).name: r for r in m["data_files"]["inputs"]}
        expected_sha = hashlib.sha256(payload).hexdigest()

        partial = by_name["partial.bin"]
        assert partial["access_observations"]["eof_reached"] is False
        assert partial["access_observations"]["bytes_read"] == 2
        assert partial["observation_time"] == "at_close"
        assert partial["hash_stats"]["extra_read_bytes"] == 6
        assert partial["sha256"] == expected_sha

        full = by_name["full.bin"]
        assert full["access_observations"]["eof_reached"] is True
        assert full["observation_time"] == "during_stream"
        assert full["sha256"] == expected_sha

    def test_truncate_back_under_budget_is_hashed_at_close(self, tmp_path):
        p_trunc = tmp_path / "trunc.bin"
        p_over = tmp_path / "over.bin"

        def _work(_base, _run):
            with pubrun.open(p_trunc, "wb") as fh:
                fh.write(b"x" * 20)
                fh.truncate(5)
            with pubrun.open(p_over, "wb") as fh:
                fh.write(b"x" * 20)

        m = _run_with_file_io(tmp_path, {"level": "hash", "max_hash_bytes": 10}, _work)
        by_name = {Path(r["path"]).name: r for r in m["data_files"]["outputs"]}

        trunc_rec = by_name["trunc.bin"]
        assert trunc_rec["access_observations"]["truncate_used"] is True
        assert trunc_rec["hash_status"] == "completed"
        assert trunc_rec["observation_time"] == "at_close"
        assert trunc_rec["sha256"] == hashlib.sha256(b"x" * 5).hexdigest()

        over_rec = by_name["over.bin"]
        assert over_rec["hash_status"] == "over_budget"
        assert over_rec["sha256"] is None

    def test_exclusive_create_xb_hashes_during_stream(self, tmp_path):
        p = tmp_path / "exclusive.bin"

        def _work(_base, _run):
            with pubrun.open(p, "xb") as fh:
                fh.write(b"exclusive\n")
            with pytest.raises(FileExistsError):
                pubrun.open(p, "xb")

        m = _run_with_file_io(tmp_path, {"level": "hash"}, _work)
        outputs = m["data_files"]["outputs"]
        assert len(outputs) == 1
        rec = outputs[0]
        assert rec["open_disposition"] == "exclusive_create"
        assert rec["hash_status"] == "completed"
        assert rec["observation_time"] == "during_stream"
        assert rec["sha256"] == hashlib.sha256(b"exclusive\n").hexdigest()


class TestIndexingScalingAndWarningCap:

    def test_dedup_index_parity_and_order_across_2000_records(self):
        from pubrun.capture.file_io import append_or_deduplicate_record

        class _DummyRun:
            def __init__(self):
                self.data_files = {"inputs": [], "outputs": [], "mixed": []}

        run = _DummyRun()
        expected_paths = []
        for i in range(2000):
            path = f"/tmp/dataset_{i:04d}.bin"
            expected_paths.append(path)
            rec = {
                "path": path,
                "role": "input",
                "label": None,
                "device": 1,
                "inode": 1000 + i,
                "size_bytes": 64 + i,
                "mtime_ns": 10_000 + i,
                "hash_status": "disabled",
                "digest": None,
                "registration_count": 1,
                "last_observed_at_utc": float(i),
            }
            stored = append_or_deduplicate_record(run, rec)
            assert stored is rec

        assert len(run.data_files["inputs"]) == 2000
        assert [r["path"] for r in run.data_files["inputs"]] == expected_paths

        # Re-registering existing records deduplicates in place without altering order.
        for i in (0, 999, 1999):
            dup = {
                "path": f"/tmp/dataset_{i:04d}.bin",
                "role": "input",
                "label": None,
                "device": 1,
                "inode": 1000 + i,
                "size_bytes": 64 + i,
                "mtime_ns": 10_000 + i,
                "hash_status": "disabled",
                "digest": None,
                "registration_count": 1,
                "last_observed_at_utc": 99999.0,
            }
            stored = append_or_deduplicate_record(run, dup)
            assert stored is run.data_files["inputs"][i]
            assert stored["registration_count"] == 2
            assert stored["last_observed_at_utc"] == 99999.0
        assert len(run.data_files["inputs"]) == 2000

    def test_direct_data_files_and_pending_mutations_rebuild_indexes(self, tmp_path):
        from pubrun.capture.file_io import (
            append_or_deduplicate_record,
            register_file_provenance,
        )

        class _DummyRun:
            def __init__(self):
                self.data_files = {"inputs": [], "outputs": [], "mixed": []}
                self._pending_file_registrations = []
                self.config = {"capture": {"file_io": {"level": "hash"}}}

        run = _DummyRun()
        base = {
            "path": "/tmp/direct.bin",
            "role": "input",
            "label": None,
            "device": 1,
            "inode": 7,
            "size_bytes": 5,
            "mtime_ns": 100,
            "hash_status": "disabled",
            "digest": None,
            "registration_count": 1,
            "last_observed_at_utc": 1.0,
        }
        r1 = append_or_deduplicate_record(run, dict(base))
        assert len(run.data_files["inputs"]) == 1

        # Direct list replacement invalidates cached identity and rebuilds index.
        run.data_files["inputs"] = []
        r2 = append_or_deduplicate_record(run, dict(base))
        assert r2 is not r1
        assert len(run.data_files["inputs"]) == 1

        # Direct append changes length and rebuilds index so a matching key dedups.
        injected = {**base, "path": "/tmp/injected.bin", "inode": 8}
        run.data_files["inputs"].append(injected)
        r3 = append_or_deduplicate_record(run, dict(injected))
        assert r3 is injected
        assert injected["registration_count"] == 2

        # Direct mutation of _pending_file_registrations rebuilds _pending_file_index.
        out_path = tmp_path / "mutated_pending.bin"
        rec_p = register_file_provenance(run, out_path, role="output", defer=True)
        assert rec_p is not None and rec_p["hash_status"] == "pending"
        assert len(run._pending_file_registrations) == 1
        run._pending_file_registrations.clear()
        out_path.write_bytes(b"created-later")
        rec_after = register_file_provenance(run, out_path, role="output", level="hash")
        assert rec_after is not None
        assert rec_after["hash_status"] == "completed"
        assert rec_after["sha256"] == hashlib.sha256(b"created-later").hexdigest()

    def test_pending_upgrade_swap_pop_and_repeat_registration_zero_rehash(
        self, tmp_path, monkeypatch
    ):
        import pubrun.capture.file_io as file_io

        p1 = tmp_path / "out1.bin"
        p2 = tmp_path / "out2.bin"
        p3 = tmp_path / "out3.bin"
        hash_calls = []
        orig_hash = file_io.hash_file_checked

        def _spy_hash(*args, **kwargs):
            hash_calls.append(args[0])
            return orig_hash(*args, **kwargs)

        def _work(_base, run):
            # Register 3 pending outputs so upgrading the first exercises swap-pop.
            r1 = pubrun.register_output(p1, defer=True)
            r2 = pubrun.register_output(p2, defer=True)
            r3 = pubrun.register_output(p3, defer=True)
            assert r1 is not None and r2 is not None and r3 is not None
            assert len(run._pending_file_registrations) == 3

            p1.write_bytes(b"payload-1")
            p2.write_bytes(b"payload-2")
            p3.write_bytes(b"payload-3")

            with monkeypatch.context() as mp:
                mp.setattr(file_io, "hash_file_checked", _spy_hash)
                # First registration after creation upgrades p1 in place (1 hash call).
                up1 = pubrun.register_output(p1, level="hash")
                assert up1 is r1
                assert up1["hash_status"] == "completed"
                assert up1["registration_count"] == 2
                assert len(run._pending_file_registrations) == 2
                assert len(hash_calls) == 1

                # Repeat registration of unchanged p1 must deduplicate with ZERO re-hash.
                rep1 = pubrun.register_output(p1, level="hash")
                assert rep1 is r1
                assert rep1["registration_count"] == 3
                assert len(hash_calls) == 1

                # Swapped element p3 (moved into slot 0) and p2 both upgrade cleanly.
                up3 = pubrun.register_output(p3, level="hash")
                assert up3 is r3
                assert up3["hash_status"] == "completed"
                assert len(run._pending_file_registrations) == 1

                up2 = pubrun.register_output(p2, level="hash")
                assert up2 is r2
                assert up2["hash_status"] == "completed"
                assert run._pending_file_registrations == []

        m = _run_with_file_io(tmp_path, {"level": "hash"}, _work)
        outputs = m["data_files"]["outputs"]
        assert len(outputs) == 3
        by_name = {Path(r["path"]).name: r for r in outputs}
        assert by_name["out1.bin"]["sha256"] == hashlib.sha256(b"payload-1").hexdigest()
        assert by_name["out1.bin"]["registration_count"] == 3
        assert by_name["out2.bin"]["sha256"] == hashlib.sha256(b"payload-2").hexdigest()
        assert by_name["out3.bin"]["sha256"] == hashlib.sha256(b"payload-3").hexdigest()

    def test_warned_invalid_algorithms_capped_at_256(self, caplog):
        import pubrun.capture.file_io as file_io

        saved = set(file_io._warned_invalid_algorithms)
        try:
            file_io._warned_invalid_algorithms.clear()
            with caplog.at_level("WARNING", logger="pubrun"):
                for i in range(300):
                    assert file_io.validate_hash_algorithm(f"invalid-alg-{i}") == "sha256"
            assert isinstance(file_io._warned_invalid_algorithms, set)
            assert len(file_io._warned_invalid_algorithms) == 256
            warn_msgs = [
                r for r in caplog.records if "unsupported [capture.file_io].hash_algorithm" in r.message
            ]
            assert len(warn_msgs) == 256
        finally:
            file_io._warned_invalid_algorithms.clear()
            file_io._warned_invalid_algorithms.update(saved)


class TestMaxTrackedFilesCapAndSchema:

    def _validate_manifest_schema(self, manifest):
        jsonschema = pytest.importorskip("jsonschema")
        schema_path = Path(__file__).resolve().parents[1] / "schemas" / "manifest.schema.json"
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        jsonschema.validate(manifest, schema)

    def test_resolve_file_io_config_max_tracked_files_validation(self):
        from types import SimpleNamespace
        from pubrun.capture.file_io import resolve_file_io_config

        def _resolve(val):
            run = SimpleNamespace(config={"capture": {"file_io": {"max_tracked_files": val}}})
            return resolve_file_io_config(run)["max_tracked_files"]

        assert resolve_file_io_config(SimpleNamespace(config={}))["max_tracked_files"] == 5000
        assert _resolve(0) == 0
        assert _resolve(100) == 100
        assert _resolve(-1) == 5000
        assert _resolve(-999) == 5000
        assert _resolve(True) == 5000
        assert _resolve(False) == 5000
        assert _resolve(None) == 5000
        assert _resolve("not-a-number") == 5000
        assert _resolve(float("nan")) == 5000

    def test_max_tracked_files_100_enforces_cap_preserves_dedup_and_upgrades_and_schema(
        self, tmp_path
    ):
        def _work(base, run):
            # 40 files via pubrun.open()
            for i in range(40):
                p = base / f"open_{i:03d}.bin"
                with pubrun.open(p, "wb") as fh:
                    fh.write(f"open-{i}".encode())

            # 40 files via register_input()
            first_input = base / "reg_in_000.bin"
            for i in range(40):
                p = base / f"reg_in_{i:03d}.bin"
                p.write_bytes(f"in-{i}".encode())
                rec = pubrun.register_input(p)
                assert rec is not None

            # 20 pending outputs via register_output(defer=True) -> reaches cap of 100
            tracked_pending = base / "pending_000.bin"
            for i in range(20):
                p = base / f"pending_{i:03d}.bin"
                rec = pubrun.register_output(p, defer=True)
                assert rec is not None
            assert len(run._pending_file_registrations) == 20

            # Beyond cap: 5 pubrun.open(), 10 register_input(), 10 register_output(defer=True)
            # -> 25 truncated records total.
            for i in range(5):
                p = base / f"over_open_{i:03d}.bin"
                with pubrun.open(p, "wb") as fh:
                    fh.write(b"dropped-open")

            for i in range(10):
                p = base / f"over_in_{i:03d}.bin"
                p.write_bytes(b"dropped-in")
                assert pubrun.register_input(p) is None

            for i in range(10):
                p = base / f"over_pending_{i:03d}.bin"
                assert pubrun.register_output(p, defer=True) is None

            assert len(run._pending_file_registrations) <= 100
            assert len(run._pending_file_registrations) == 20

            # At the cap, deduplication of an already-tracked input STILL succeeds.
            dup_rec = pubrun.register_input(first_input)
            assert dup_rec is not None
            assert dup_rec["registration_count"] == 2

            # At the cap, in-place upgrade of an already-tracked pending output STILL succeeds.
            tracked_pending.write_bytes(b"upgraded-at-cap")
            up_rec = pubrun.register_output(tracked_pending)
            assert up_rec is not None
            assert up_rec["hash_status"] != "pending"
            assert up_rec["registration_count"] == 2
            assert len(run._pending_file_registrations) == 19

        m = _run_with_file_io(
            tmp_path,
            {"level": "stat", "max_tracked_files": 100},
            _work,
        )
        df = m["data_files"]
        total_stored = len(df["inputs"]) + len(df["outputs"]) + len(df["mixed"])
        assert total_stored == 100
        assert df["records_truncated"] == 25
        self._validate_manifest_schema(m)

    def test_uncapped_manifest_omits_records_truncated_and_validates(self, tmp_path):
        def _work(base, _run):
            p = base / "single.bin"
            p.write_bytes(b"hello")
            assert pubrun.register_input(p) is not None

        m = _run_with_file_io(tmp_path, {"level": "stat", "max_tracked_files": 10}, _work)
        assert "records_truncated" not in m["data_files"]
        assert len(m["data_files"]["inputs"]) == 1
        self._validate_manifest_schema(m)

    def test_max_tracked_files_zero_records_nothing_and_skips_hashing(
        self, tmp_path, monkeypatch
    ):
        import pubrun.capture.file_io as file_io

        def _forbid_hash(*args, **kwargs):
            raise AssertionError("hash_file_checked must not run when max_tracked_files=0")

        def _work(base, _run):
            inp = base / "zero_in.bin"
            inp.write_bytes(b"should-not-hash")
            out = base / "zero_out.bin"
            with monkeypatch.context() as mp:
                mp.setattr(file_io, "hash_file_checked", _forbid_hash)
                with pubrun.open(inp, "rb") as fh:
                    assert fh.read() == b"should-not-hash"
                with pubrun.open(out, "wb") as fh:
                    fh.write(b"written-no-hash")
                assert pubrun.register_input(inp, level="hash") is None
                assert pubrun.register_output(out, level="hash", defer=True) is None

        m = _run_with_file_io(
            tmp_path,
            {"level": "hash", "max_tracked_files": 0},
            _work,
        )
        df = m["data_files"]
        assert df["inputs"] == []
        assert df["outputs"] == []
        assert df["mixed"] == []
        assert df["records_truncated"] == 4
        assert "hashing_summary" not in df
        self._validate_manifest_schema(m)


class TestStreamingHashFastPath:

    def test_uncapped_streaming_bypasses_check_stream_progress_with_exact_digests(
        self, tmp_path, monkeypatch
    ):
        from pubrun.capture.file_io import FileIoBudgetTracker

        progress_calls = []
        orig_check = FileIoBudgetTracker.check_stream_progress

        def _spy_check(self, pending_bytes, pending_seconds):
            progress_calls.append((pending_bytes, pending_seconds))
            return orig_check(self, pending_bytes, pending_seconds)

        p_write = tmp_path / "fast_write.bin"
        p_read = tmp_path / "fast_read.bin"
        expected_write = b"bytes-chunk-" + bytes(bytearray(b"bytearray-chunk-")) + b"mv-chunk"
        expected_read = b"R" * 4096 + b"tail"
        p_read.write_bytes(expected_read)

        def _work(_base, run):
            with monkeypatch.context() as mp:
                mp.setattr(FileIoBudgetTracker, "check_stream_progress", _spy_check)
                with pubrun.open(p_write, "wb") as fh:
                    fh.write(b"bytes-chunk-")
                    fh.write(bytearray(b"bytearray-chunk-"))
                    fh.write(memoryview(b"mv-chunk"))

                out_buf = bytearray()
                buf = bytearray(1024)
                with pubrun.open(p_read, "rb") as fh:
                    while True:
                        n = fh.readinto(buf)
                        if not n:
                            break
                        out_buf.extend(buf[:n])
                assert bytes(out_buf) == expected_read

                out_buf1 = bytearray()
                buf1 = bytearray(1024)
                with pubrun.open(p_read, "rb") as fh:
                    while True:
                        n = fh.readinto1(buf1)
                        if not n:
                            break
                        out_buf1.extend(buf1[:n])
                assert bytes(out_buf1) == expected_read

        m = _run_with_file_io(tmp_path, {"level": "hash"}, _work)
        assert progress_calls == []

        out_rec = m["data_files"]["outputs"][0]
        assert out_rec["observation_time"] == "during_stream"
        assert out_rec["sha256"] == hashlib.sha256(expected_write).hexdigest()
        assert out_rec["hash_stats"]["bytes_hashed"] == len(expected_write)
        assert out_rec["hash_stats"]["extra_read_bytes"] == 0

        in_rec = m["data_files"]["inputs"][0]
        assert in_rec["observation_time"] == "during_stream"
        assert in_rec["sha256"] == hashlib.sha256(expected_read).hexdigest()
        assert in_rec["hash_stats"]["bytes_hashed"] == len(expected_read)
        assert in_rec["registration_count"] == 2

        summary = m["data_files"]["hashing_summary"]
        assert summary["total_bytes_hashed"] == len(expected_write) + 2 * len(expected_read)

    def test_partial_binary_write_hashes_only_written_prefix(self, tmp_path):
        from pubrun.capture.file_io import ProvenanceFileProxy

        p = tmp_path / "partial_write.bin"

        class _PartialWriter:
            def __init__(self, real_fh):
                self._fh = real_fh

            def write(self, data):
                # Write only the first 4 bytes to simulate a non-blocking partial write.
                prefix = bytes(data)[:4]
                return self._fh.write(prefix)

            def flush(self):
                return self._fh.flush()

            def fileno(self):
                return self._fh.fileno()

            def close(self):
                return self._fh.close()

        def _work(_base, run):
            real_fh = open(p, "wb")
            proxy = ProvenanceFileProxy(
                _PartialWriter(real_fh), p, "wb", run, level="hash"
            )
            with proxy as fh:
                n1 = fh.write(b"ABCDxxxx")
                n2 = fh.write(bytearray(b"EFGHyyyy"))
                assert n1 == 4
                assert n2 == 4

        m = _run_with_file_io(tmp_path, {"level": "hash"}, _work)
        assert p.read_bytes() == b"ABCDEFGH"
        rec = m["data_files"]["outputs"][0]
        assert rec["hash_status"] == "completed"
        assert rec["observation_time"] == "during_stream"
        assert rec["sha256"] == hashlib.sha256(b"ABCDEFGH").hexdigest()
        assert rec["hash_stats"]["bytes_hashed"] == 8

    def test_capped_streaming_small_per_file_cap_and_large_64k_intervals(
        self, tmp_path, monkeypatch
    ):
        from pubrun.capture.file_io import FileIoBudgetTracker

        # 1. Small per-file cap (max_hash_bytes=10) aborts immediately lock-free.
        p_small_over = tmp_path / "small_over.bin"
        p_small_ok = tmp_path / "small_ok.bin"

        def _work_small(_base, _run):
            with pubrun.open(p_small_over, "wb") as fh:
                fh.write(b"12345")
                fh.write(b"678901")  # 11 bytes > 10 -> aborts immediately
            with pubrun.open(p_small_ok, "wb") as fh:
                fh.write(b"1234567890")  # exactly 10 bytes

        m_small = _run_with_file_io(
            tmp_path,
            {"level": "hash", "max_hash_bytes": 10},
            _work_small,
        )
        by_name = {Path(r["path"]).name: r for r in m_small["data_files"]["outputs"]}
        assert by_name["small_over.bin"]["hash_status"] == "over_budget"
        assert by_name["small_over.bin"]["sha256"] is None
        assert by_name["small_over.bin"]["hash_stats"]["extra_read_bytes"] == 0
        assert by_name["small_over.bin"]["hash_stats"]["bytes_hashed"] == 0
        assert by_name["small_ok.bin"]["hash_status"] == "completed"
        assert by_name["small_ok.bin"]["observation_time"] == "during_stream"
        assert by_name["small_ok.bin"]["hash_stats"]["extra_read_bytes"] == 0
        assert by_name["small_ok.bin"]["sha256"] == hashlib.sha256(b"1234567890").hexdigest()

        # 2. Large >= 64 KiB stream checks progress at 64 KiB intervals + close.
        progress_calls = []
        orig_check = FileIoBudgetTracker.check_stream_progress

        def _spy_check(self, pending_bytes, pending_seconds):
            progress_calls.append(pending_bytes)
            return orig_check(self, pending_bytes, pending_seconds)

        p_big_ok = tmp_path / "big_ok.bin"
        p_big_over = tmp_path / "big_over.bin"
        chunk = b"Z" * 4096
        big_payload = chunk * 40  # 160 KiB

        def _work_big(_base, _run):
            with monkeypatch.context() as mp:
                mp.setattr(FileIoBudgetTracker, "check_stream_progress", _spy_check)
                with pubrun.open(p_big_ok, "wb") as fh:
                    for _ in range(40):
                        fh.write(chunk)
                with pubrun.open(p_big_over, "wb") as fh:
                    for _ in range(40):
                        fh.write(chunk)

        m_big = _run_with_file_io(
            tmp_path,
            {"level": "hash", "max_total_hash_bytes": 200 * 1024},
            _work_big,
        )
        # First file (160 KiB): checked at 64 KiB, 128 KiB, and close (160 KiB).
        # Second file: checked at 64 KiB (total 224 KiB > 200 KiB) -> aborts mid-stream.
        assert 65536 in progress_calls
        assert 131072 in progress_calls
        assert len(progress_calls) < 10

        big_by_name = {Path(r["path"]).name: r for r in m_big["data_files"]["outputs"]}
        assert big_by_name["big_ok.bin"]["hash_status"] == "completed"
        assert big_by_name["big_ok.bin"]["observation_time"] == "during_stream"
        assert big_by_name["big_ok.bin"]["sha256"] == hashlib.sha256(big_payload).hexdigest()
        assert big_by_name["big_ok.bin"]["hash_stats"]["bytes_hashed"] == len(big_payload)
        assert big_by_name["big_over.bin"]["hash_status"] == "over_budget"
        assert big_by_name["big_over.bin"]["sha256"] is None
        assert big_by_name["big_over.bin"]["hash_stats"]["extra_read_bytes"] == 0
        assert big_by_name["big_over.bin"]["hash_stats"]["bytes_hashed"] == 0
        assert m_big["data_files"]["hashing_summary"]["total_bytes_hashed"] == len(big_payload)

    def test_small_chunk_stream_hash_time_cap_enforced_and_recorded(
        self, tmp_path, monkeypatch
    ):
        """Small-chunk (<64 KiB) streams enforce max_total_hash_seconds and record hash_duration_seconds."""
        import time as real_time
        import pubrun.capture.file_io as file_io

        class _SteppedMonotonic:
            def __init__(self, step: float) -> None:
                self._now = 100.0
                self._step = step
                self.calls = 0

            def monotonic(self) -> float:
                self.calls += 1
                if self.calls % 2 == 0:
                    self._now += self._step
                return self._now

            def __getattr__(self, name: str):
                return getattr(real_time, name)

        small_chunk = b"a" * 128
        assert len(small_chunk) * 6 < file_io.DEFAULT_CHUNK_SIZE

        # 1. Tight cap: 6 small chunks at 0.3s each against 0.5s cap aborts after chunk 2 lock-free.
        tight_clock = _SteppedMonotonic(step=0.3)
        p_tight = tmp_path / "small_tight.bin"

        def _work_tight(_base, _run):
            with monkeypatch.context() as mp:
                mp.setattr(file_io, "time", tight_clock)
                with pubrun.open(p_tight, "wb") as fh:
                    for _ in range(6):
                        fh.write(small_chunk)

        m_tight = _run_with_file_io(
            tmp_path,
            {"level": "hash", "max_total_hash_seconds": 0.5},
            _work_tight,
        )
        rec_tight = m_tight["data_files"]["outputs"][0]
        assert rec_tight["hash_status"] == "over_budget"
        assert rec_tight["sha256"] is None
        assert rec_tight["digest"] is None
        assert rec_tight["hash_stats"]["extra_read_bytes"] == 0
        assert rec_tight["hash_stats"]["bytes_hashed"] == 0
        # Only chunks 1 (0.3s) and 2 (0.6s > 0.5s) were timed (2 calls each); chunks 3-6 skipped.
        assert tight_clock.calls == 4

        # 2. Generous cap: small chunks complete during_stream with accurate positive duration.
        gen_clock = _SteppedMonotonic(step=0.25)
        p_gen = tmp_path / "small_generous.bin"

        def _work_gen(_base, _run):
            with monkeypatch.context() as mp:
                mp.setattr(file_io, "time", gen_clock)
                with pubrun.open(p_gen, "wb") as fh:
                    for _ in range(3):
                        fh.write(small_chunk)

        m_gen = _run_with_file_io(
            tmp_path,
            {"level": "hash", "max_total_hash_seconds": 10.0},
            _work_gen,
        )
        rec_gen = m_gen["data_files"]["outputs"][0]
        assert rec_gen["hash_status"] == "completed"
        assert rec_gen["observation_time"] == "during_stream"
        assert rec_gen["sha256"] == hashlib.sha256(small_chunk * 3).hexdigest()
        assert rec_gen["hash_stats"]["extra_read_bytes"] == 0
        assert rec_gen["hash_stats"]["bytes_hashed"] == len(small_chunk) * 3
        assert rec_gen["hash_stats"]["hash_duration_seconds"] == pytest.approx(0.75, abs=1e-6)
        assert m_gen["data_files"]["hashing_summary"]["total_hash_seconds"] == pytest.approx(
            0.75, abs=1e-6
        )

        # 3. Cumulative multi-file small-chunk budget enforced at close().
        cum_clock = _SteppedMonotonic(step=0.35)
        p_cum1 = tmp_path / "cum1.bin"
        p_cum2 = tmp_path / "cum2.bin"

        def _work_cum(_base, _run):
            with monkeypatch.context() as mp:
                mp.setattr(file_io, "time", cum_clock)
                with pubrun.open(p_cum1, "wb") as fh:
                    fh.write(small_chunk)
                with pubrun.open(p_cum2, "wb") as fh:
                    fh.write(small_chunk)

        m_cum = _run_with_file_io(
            tmp_path,
            {"level": "hash", "max_total_hash_seconds": 0.5},
            _work_cum,
        )
        cum_by_name = {Path(r["path"]).name: r for r in m_cum["data_files"]["outputs"]}
        assert cum_by_name["cum1.bin"]["hash_status"] == "completed"
        assert cum_by_name["cum1.bin"]["observation_time"] == "during_stream"
        assert cum_by_name["cum1.bin"]["hash_stats"]["hash_duration_seconds"] == pytest.approx(
            0.35, abs=1e-6
        )
        assert cum_by_name["cum2.bin"]["hash_status"] == "over_budget"
        assert cum_by_name["cum2.bin"]["sha256"] is None
        assert cum_by_name["cum2.bin"]["hash_stats"]["extra_read_bytes"] == 0
        assert cum_by_name["cum2.bin"]["hash_stats"]["bytes_hashed"] == 0

    def test_concurrent_max_tracked_files_cap_across_open_and_register(self, tmp_path):
        """Concurrent pubrun.open, register_input, and register_output(defer=True) honor max_tracked_files."""
        import threading

        cap = 15
        files_per_thread = 5
        num_threads = 9  # 3 open, 3 register_input, 3 register_output(defer=True)
        total_attempts = num_threads * files_per_thread

        # Pre-create input files for register_input threads.
        for tid in range(3, 6):
            for idx in range(files_per_thread):
                (tmp_path / f"reg_in_{tid}_{idx}.bin").write_bytes(f"in-{tid}-{idx}".encode())

        def _work(base, _run):
            barrier = threading.Barrier(num_threads)
            errors = []

            def _worker(tid):
                try:
                    barrier.wait(timeout=5.0)
                    for idx in range(files_per_thread):
                        if tid < 3:
                            p = base / f"open_out_{tid}_{idx}.bin"
                            with pubrun.open(p, "wb") as fh:
                                fh.write(f"open-{tid}-{idx}".encode())
                        elif tid < 6:
                            p = base / f"reg_in_{tid}_{idx}.bin"
                            pubrun.register_input(p)
                        else:
                            p = base / f"defer_out_{tid}_{idx}.bin"
                            pubrun.register_output(p, defer=True)
                except Exception as exc:
                    errors.append(exc)

            threads = [
                threading.Thread(target=_worker, args=(tid,)) for tid in range(num_threads)
            ]
            for t in threads:
                t.start()
            for t in threads:
                t.join(timeout=15.0)
            assert errors == []

        m = _run_with_file_io(
            tmp_path,
            {"level": "stat", "max_tracked_files": cap},
            _work,
        )
        df = m["data_files"]
        total_stored = len(df["inputs"]) + len(df["outputs"]) + len(df["mixed"])
        assert total_stored == cap
        assert df["records_truncated"] == total_attempts - cap
        TestMaxTrackedFilesCapAndSchema()._validate_manifest_schema(m)
