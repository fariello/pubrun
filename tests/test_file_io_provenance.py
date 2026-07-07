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
