"""Tests for IPD-A: filesystem classification, system metrics, and manifest enrichment.

Covers the run-time I/O/env capture that makes post-hoc diagnosis (IPD-B `pubrun inspect`)
possible, plus the two additive manifest flags that disambiguate subprocess / file-open
provenance. Critically includes the hang-safety guarantee: the fstype probe must classify
via /proc/mounts parsing and NEVER call the blocking statvfs/df/stat path.
"""
import sys
import json
import pytest
from pathlib import Path

from pubrun.capture import filesystem as fs
from pubrun.capture import system_metrics as sm


# --------------------------------------------------------------------------- filesystem

class TestFilesystemClassification:

    def test_network_fstype_detection(self):
        assert fs._is_network_fstype("nfs")
        assert fs._is_network_fstype("nfs4")
        assert fs._is_network_fstype("lustre")
        assert fs._is_network_fstype("cifs")
        assert fs._is_network_fstype("fuse.sshfs")
        assert not fs._is_network_fstype("ext4")
        assert not fs._is_network_fstype("xfs")
        assert not fs._is_network_fstype("tmpfs")
        assert not fs._is_network_fstype("")

    def test_longest_prefix_match(self):
        entries = [("/", "ext4"), ("/scratch", "lustre"), ("/scratch/user", "nfs4")]
        # /scratch/user/run -> nfs4 (longest matching prefix), not lustre or ext4
        mp, ft = fs._longest_prefix_fstype("/scratch/user/run/x", entries)
        assert (mp, ft) == ("/scratch/user", "nfs4")
        # /scratch/other -> lustre
        mp, ft = fs._longest_prefix_fstype("/scratch/other", entries)
        assert (mp, ft) == ("/scratch", "lustre")
        # /home/x -> falls back to root ext4
        mp, ft = fs._longest_prefix_fstype("/home/x", entries)
        assert (mp, ft) == ("/", "ext4")

    def test_unescape_mount_field(self):
        assert fs._unescape_mount_field(r"/mnt/with\040space") == "/mnt/with space"
        assert fs._unescape_mount_field("/plain") == "/plain"

    @pytest.mark.skipif(not sys.platform.startswith("linux"), reason="Linux /proc only")
    def test_get_filesystem_classifies_local(self):
        out = fs.get_filesystem({}, {"tmp": "/tmp", "root": "/"})
        assert out["capture_state"]["status"] == "complete"
        assert out["root"]["fstype"] in ("ext4", "xfs", "btrfs", "overlay", "tmpfs", "zfs")
        assert out["root"]["is_network"] is False
        assert "mount_point" in out["tmp"]

    def test_get_filesystem_unsupported_platform(self, monkeypatch):
        monkeypatch.setattr(fs.sys, "platform", "sunos5")
        out = fs.get_filesystem({}, {"x": "/x"})
        assert out["capture_state"]["status"] == "failed"

    @pytest.mark.skipif(not sys.platform.startswith("linux"), reason="Linux /proc only")
    def test_fstype_probe_never_calls_blocking_statvfs(self, monkeypatch):
        """HANG-SAFETY (HIGH): the probe must classify via /proc/mounts parsing and must
        NOT call the blocking os.statvfs on the target path (which hangs on a sick NFS
        mount). Make statvfs explode; classification must still succeed via /proc/mounts.

        (We ban only os.statvfs here — not os.stat — because os.path.exists legitimately
        stats the LOCAL /proc/mounts file; the invariant is "never statvfs/df the target
        mount", which is what actually blocks on a wedged NFS mount.)
        """
        def _boom(*a, **k):
            raise AssertionError("os.statvfs must not be used for fstype (blocks on sick NFS)")
        monkeypatch.setattr(fs.os, "statvfs", _boom, raising=False)
        out = fs.get_filesystem({}, {"root": "/"})
        assert out["capture_state"]["status"] == "complete"
        assert out["root"]["fstype"]  # classified without statvfs-ing the mount

    def test_get_filesystem_never_raises(self, monkeypatch):
        """A parsing failure yields capture_state=failed, never an exception."""
        monkeypatch.setattr(fs, "_parse_proc_mounts", lambda: (_ for _ in ()).throw(OSError("boom")))
        monkeypatch.setattr(fs.sys, "platform", "linux")
        monkeypatch.setattr(fs.os.path, "exists", lambda p: True)
        out = fs.get_filesystem({}, {"x": "/x"})
        assert out["capture_state"]["status"] == "failed"


# ------------------------------------------------------------------------- system metrics

class TestSystemMetrics:

    @pytest.mark.skipif(not sys.platform.startswith("linux"), reason="Linux /proc/meminfo")
    def test_get_system_memory(self):
        mem = sm.get_system_memory()
        assert mem is not None
        assert mem["total_bytes"] > 0
        assert "available_bytes" in mem

    def test_get_load_average(self):
        load = sm.get_load_average()
        # Available on Linux/macOS; may be None elsewhere — accept either but validate shape.
        if load is not None:
            assert set(load) == {"1min", "5min", "15min"}

    def test_iowait_pct_between_math(self):
        # iowait ticks 10->20 (delta 10), total 100->200 (delta 100) => 10%
        assert sm.iowait_pct_between((10, 100), (20, 200)) == 10.0
        # no advance -> None
        assert sm.iowait_pct_between((10, 100), (10, 100)) is None
        # missing sample -> None
        assert sm.iowait_pct_between(None, (20, 200)) is None

    def test_meminfo_parse_failure_returns_none(self, monkeypatch):
        monkeypatch.setattr(sm.sys, "platform", "linux")
        monkeypatch.setattr(sm.os.path, "exists", lambda p: True)
        def _boom(*a, **k):
            raise OSError("boom")
        monkeypatch.setattr("builtins.open", _boom)
        assert sm.get_system_memory() is None  # never raises


# ------------------------------------------------------------------- manifest enrichment

class TestManifestEnrichment:
    """The new keys appear in a real run's manifest and existing keys are preserved."""

    @pytest.fixture
    def manifest(self, tmp_path):
        import pubrun
        import pubrun.tracker
        old_cwd = Path.cwd
        try:
            Path.cwd = staticmethod(lambda: tmp_path)
            pubrun.tracker._active_run = None
            t = pubrun.start()
            t.stop()
            run_dir = Path(t.run_dir)
        finally:
            Path.cwd = old_cwd
            pubrun.tracker._active_run = None
        return json.loads((run_dir / "manifest.json").read_text())

    def test_filesystem_section_present(self, manifest):
        assert "filesystem" in manifest
        assert "capture_state" in manifest["filesystem"]

    def test_capture_flags_present(self, manifest):
        cap = manifest["capture"]
        assert "subprocesses_enabled" in cap
        assert isinstance(cap["subprocesses_enabled"], bool)
        assert cap["file_provenance_available"] is True

    def test_existing_keys_preserved(self, manifest):
        # Anti-regression: the additions must not drop/rename pre-existing sections.
        for key in ("host", "hardware", "resources", "console", "subprocesses",
                    "python", "packages", "git", "capture", "data_files", "status"):
            assert key in manifest

    @pytest.mark.skipif(not sys.platform.startswith("linux"), reason="Linux system metrics")
    def test_resources_system_metrics_present(self, manifest):
        res = manifest.get("resources", {})
        # Resource watcher is on by default (depth=standard) with system_metrics=true,
        # so at least the memory/load sections should appear.
        assert "system_memory" in res or "load_average" in res


class TestResComprehensiveRender:
    """`pubrun res` (metric='all') renders the full resource set; cpu/mem stay focused."""

    def _write_manifest(self, tmp_path):
        import json as _json
        run = tmp_path / "runs" / "pubrun-x"
        run.mkdir(parents=True)
        manifest = {
            "run_id": "x", "invocation": {"script": {"basename": "s.py"}},
            "status": {"outcome": "completed"},
            "resources": {
                "scope": "tree",
                "peak_rss_bytes": 50 * 1024 * 1024,
                "end_rss_bytes": 40 * 1024 * 1024,
                "peak_cpu_percent": 42.0,
                "peak_tree_rss_bytes": 120 * 1024 * 1024,
                "system_memory": {"start": {"total_bytes": 32 * 1024**3, "available_bytes": 20 * 1024**3},
                                  "min_available": {"available_bytes": 15 * 1024**3}},
                "load_average": {"start": {"1min": 1.5}, "max_1min": 3.0},
                "system_iowait_pct": {"last": 2.0, "max": 5.0},
                "io_counters": {"delta": {"read_bytes": 10 * 1024 * 1024, "write_bytes": 2 * 1024 * 1024,
                                          "rchar": 12 * 1024 * 1024, "wchar": 3 * 1024 * 1024}},
                "capture_state": {"status": "complete"},
            },
        }
        mpath = run / "manifest.json"
        mpath.write_text(_json.dumps(manifest))
        return str(mpath)

    def test_res_renders_all_fields(self, tmp_path, capsys):
        from pubrun.report.diagnostics import print_resources_report
        print_resources_report(self._write_manifest(tmp_path), metric="all")
        out = capsys.readouterr().out
        assert "Peak Tree RSS" in out
        assert "System RAM" in out
        assert "Load Average" in out
        assert "Node iowait" in out and "indicative only" in out
        assert "Disk I/O" in out

    def test_cpu_metric_stays_focused(self, tmp_path, capsys):
        from pubrun.report.diagnostics import print_resources_report
        print_resources_report(self._write_manifest(tmp_path), metric="cpu")
        out = capsys.readouterr().out
        assert "Peak CPU" in out
        # The comprehensive-only lines must NOT appear under the single 'cpu' metric.
        assert "System RAM" not in out
        assert "Load Average" not in out
        assert "Disk I/O" not in out

    def test_old_manifest_without_new_fields_renders_cleanly(self, tmp_path, capsys):
        import json as _json
        from pubrun.report.diagnostics import print_resources_report
        run = tmp_path / "runs" / "pubrun-old"
        run.mkdir(parents=True)
        m = {"run_id": "old", "invocation": {"script": {"basename": "s.py"}}, "status": {"outcome": "completed"},
             "resources": {"scope": "process", "peak_rss_bytes": 1024 * 1024,
                           "peak_cpu_percent": 5.0, "capture_state": {"status": "complete"}}}
        mpath = run / "manifest.json"; mpath.write_text(_json.dumps(m))
        print_resources_report(str(mpath), metric="all")  # must not raise
        out = capsys.readouterr().out
        assert "Peak RSS" in out
        assert "System RAM" not in out  # absent field omitted, no crash
