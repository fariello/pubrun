"""Tests for IPD-A: filesystem classification, system metrics, and manifest enrichment.

Covers the run-time I/O/env capture that makes post-hoc diagnosis (IPD-B `pubrun inspect`)
possible, plus the two additive manifest flags that disambiguate subprocess / file-open
provenance. Critically includes the hang-safety guarantee: the fstype probe must classify
via /proc/mounts parsing and NEVER call the blocking statvfs/df/stat path.
"""
import os
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
        """A parsing failure yields capture_state=failed, never an exception. Both the
        mountinfo (preferred) and /proc/mounts (fallback) parsers must fail to exercise this."""
        monkeypatch.setattr(fs, "_parse_proc_mountinfo", lambda: (_ for _ in ()).throw(OSError("boom")))
        monkeypatch.setattr(fs, "_parse_proc_mounts", lambda: (_ for _ in ()).throw(OSError("boom")))
        monkeypatch.setattr(fs.sys, "platform", "linux")
        monkeypatch.setattr(fs.os.path, "exists", lambda p: True)
        out = fs.get_filesystem({}, {"x": "/x"})
        assert out["capture_state"]["status"] == "failed"


# ------------------------------------------------- IPD (2026-07-07): mountinfo + live probe

class TestMountinfoParse:

    @pytest.mark.skipif(not sys.platform.startswith("linux"), reason="Linux /proc only")
    def test_mountinfo_parses_and_is_preferred(self):
        entries = fs._parse_proc_mountinfo()
        assert entries and all(len(e) == 2 for e in entries)
        # get_filesystem should classify "/" via mountinfo without error.
        out = fs.get_filesystem({}, {"root": "/"})
        assert out["capture_state"]["status"] == "complete"
        assert out["root"]["fstype"]

    def test_mountinfo_parser_handles_bind_overlay_nfs(self, tmp_path, monkeypatch):
        sample = (
            "36 35 98:0 / /rootfs rw - ext4 /dev/root rw\n"
            "40 36 0:32 /bind /mnt/bind rw shared:2 - ext4 /dev/root rw\n"
            "41 36 0:33 / /mnt/over rw - overlay overlay rw,lowerdir=/a\n"
            "42 36 0:34 / /mnt/nfs rw - nfs4 server:/exp rw\n"
        )
        f = tmp_path / "mountinfo"
        f.write_text(sample)
        _real_open = open
        monkeypatch.setattr("builtins.open",
                            lambda p, *a, **k: _real_open(f, *a, **k) if "mountinfo" in str(p) else _real_open(p, *a, **k))
        entries = dict(fs._parse_proc_mountinfo())
        assert entries["/mnt/nfs"] == "nfs4"
        assert entries["/mnt/over"] == "overlay"
        assert entries["/mnt/bind"] == "ext4"


class TestLiveProbe:
    """Threaded statvfs probe: decoupled wait budget vs. lifetime; never hangs the caller."""

    def test_fast_return_complete(self):
        p = fs.probe_filesystem_live("/tmp" if os.name != "nt" else "C:\\", 5.0)
        r = p.result()
        assert r["status"] == "complete"
        assert "total_bytes" in r or "avail_bytes" in r

    def test_hang_reports_pending_and_does_not_block(self, monkeypatch):
        import time as _t
        started = _t.monotonic()

        def _sleep_forever(path):
            _t.sleep(30)  # simulate a wedged mount; daemon is abandoned, never joined.
            return {}
        monkeypatch.setattr(fs, "_statvfs_metrics", _sleep_forever)
        p = fs.probe_filesystem_live("/whatever", wait_budget_s=0.2)
        waited = _t.monotonic() - started
        assert waited < 5  # caller unblocked at ~budget, NOT at 30s
        r = p.result()
        assert r["status"] == "pending" and r.get("hung") is True
        # A second probe still starts and returns promptly (the abandoned daemon did not
        # deadlock the caller or exhaust the probe cap). It also sleeps under this patch,
        # so it too reports pending within its short budget — the point is it does not hang.
        started2 = _t.monotonic()
        p2 = fs.probe_filesystem_live("/other", wait_budget_s=0.2)
        assert (_t.monotonic() - started2) < 5
        assert "status" in p2.result()

    def test_slow_return_marked_slow_on_late_read(self, monkeypatch):
        import time as _t

        def _slow(path):
            _t.sleep(0.4)  # returns AFTER the caller's budget but is alive
            return {"total_bytes": 1, "free_bytes": 1, "avail_bytes": 1}
        monkeypatch.setattr(fs, "_statvfs_metrics", _slow)
        p = fs.probe_filesystem_live("/x", wait_budget_s=0.1)
        # Immediately after init the probe is still pending.
        assert p.result()["status"] == "pending"
        _t.sleep(0.5)  # let the daemon finish; re-read (non-blocking) picks up the late result
        r = p.result()
        assert r["status"] == "complete" and r.get("slow") is True
        assert r["elapsed_s"] > 0.1

    def test_probe_paths_dedupes_by_mount(self, monkeypatch):
        calls = []
        real = fs.probe_filesystem_live

        def _spy(path, wait_budget_s=5.0):
            calls.append(path)
            return real(path, wait_budget_s)
        monkeypatch.setattr(fs, "probe_filesystem_live", _spy)
        # Two labels on the SAME mount point -> ONE probe.
        fs_data = {
            "a": {"path": "/tmp/a", "mount_point": "/tmp", "fstype": "tmpfs"},
            "b": {"path": "/tmp/b", "mount_point": "/tmp", "fstype": "tmpfs"},
            "capture_state": {"status": "complete"},
        }
        fs.probe_paths_live(fs_data)
        assert len(calls) == 1  # deduped
        assert "live" in fs_data["a"] and "live" in fs_data["b"]


class TestEnvironmentKind:

    def test_venv_vs_system(self, monkeypatch):
        from pubrun.capture.python_runtime import environment_kind
        out = environment_kind()
        assert out["environment_kind"] in ("venv", "system", "conda", "virtualenv", "frozen")
        assert isinstance(out["in_venv"], bool)
        assert isinstance(out["sys_path_len"], int) and out["sys_path_len"] >= 0

    def test_conda_detected_via_prefix(self, monkeypatch, tmp_path):
        from pubrun.capture import python_runtime as pr
        monkeypatch.setattr(pr.sys, "prefix", str(tmp_path))
        monkeypatch.setenv("CONDA_PREFIX", str(tmp_path))
        assert pr.environment_kind()["environment_kind"] == "conda"

    def test_survives_redaction_shape(self):
        # The env-kind fields expose no path/username -> a redactor scanning for those
        # would leave them intact. Assert they are plain scalars.
        from pubrun.capture.python_runtime import environment_kind
        out = environment_kind()
        for k in ("environment_kind", "in_venv", "sys_path_len", "pyenv"):
            assert not isinstance(out[k], (dict, list))


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
        # New comprehensive labels (peak/avg/min from samples, peak fallback with no events.jsonl).
        assert "RSS (tree)" in out
        assert "System RAM" in out
        assert "Load Average" in out
        assert "Node iowait" in out and "indicative only" in out
        assert "Disk I/O" in out

    def test_cpu_metric_stays_focused(self, tmp_path, capsys):
        from pubrun.report.diagnostics import print_resources_report
        print_resources_report(self._write_manifest(tmp_path), metric="cpu")
        out = capsys.readouterr().out
        assert "CPU (main)" in out and "peak 42.0%" in out
        # The comprehensive-only lines must NOT appear under the single 'cpu' metric.
        assert "System RAM" not in out
        assert "Load Average" not in out
        assert "Disk I/O" not in out
        assert "RSS (tree)" not in out

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
        assert "RSS (main)" in out and "peak 1.00 MB" in out
        assert "System RAM" not in out  # absent field omitted, no crash


# ------------------------------------------------- IPD-C: report/res richness (2026-07-07)

class TestTreeCpuCapture:
    """Tree CPU is computed from summed CPU-TIME deltas (not instantaneous-% sum)."""

    @pytest.mark.skipif(not sys.platform.startswith("linux"), reason="Linux /proc CPU time")
    def test_tree_cpu_computed_from_time_deltas(self, monkeypatch):
        from pubrun.capture import resources as R
        w = R.ResourceWatcher(type("T", (), {"event_stream": None})(), interval_seconds=1.0, scope="tree")
        w._clk_tck = 100  # 100 jiffies/sec
        # First poll: establishes the baseline, returns 0 (no delta yet).
        monkeypatch.setattr(R, "_get_tree_cpu_jiffies_linux", lambda: 1000)
        monkeypatch.setattr(R.time, "perf_counter", lambda: 10.0)
        assert w._poll_tree_cpu() == 0.0
        # Second poll: +50 jiffies over 1.0s wall = 0.5 CPU-seconds / 1s = 50%.
        monkeypatch.setattr(R, "_get_tree_cpu_jiffies_linux", lambda: 1050)
        monkeypatch.setattr(R.time, "perf_counter", lambda: 11.0)
        assert w._poll_tree_cpu() == 50.0

    @pytest.mark.skipif(not sys.platform.startswith("linux"), reason="Linux /proc CPU time")
    def test_tree_cpu_can_exceed_100_and_is_not_clamped(self, monkeypatch):
        from pubrun.capture import resources as R
        w = R.ResourceWatcher(type("T", (), {"event_stream": None})(), interval_seconds=1.0, scope="tree")
        w._clk_tck = 100
        monkeypatch.setattr(R, "_get_tree_cpu_jiffies_linux", lambda: 0)
        monkeypatch.setattr(R.time, "perf_counter", lambda: 0.0)
        w._poll_tree_cpu()
        # +400 jiffies over 1s = 4 CPU-seconds/s = 400% (4 cores busy) -> not clamped.
        monkeypatch.setattr(R, "_get_tree_cpu_jiffies_linux", lambda: 400)
        monkeypatch.setattr(R.time, "perf_counter", lambda: 1.0)
        assert w._poll_tree_cpu() == 400.0


class TestResourceSeriesStats:
    """avg/min/max computed from per-sample events; main + tree; peak fallback with no samples."""

    def _run_with_events(self, tmp_path, samples):
        import json as _json
        run = tmp_path / "runs" / "pubrun-s"
        run.mkdir(parents=True)
        (run / "manifest.json").write_text(_json.dumps({
            "run_id": "s", "invocation": {"script": {"basename": "s.py"}},
            "status": {"outcome": "completed"},
            "resources": {"scope": "tree", "capture_state": {"status": "complete"}},
        }))
        with open(run / "events.jsonl", "w") as f:
            for i, (rss, cpu, trss, tcpu) in enumerate(samples):
                p = {"rss_bytes": rss, "cpu_percent": cpu}
                if trss is not None:
                    p["tree_rss_bytes"] = trss
                if tcpu is not None:
                    p["tree_cpu_percent"] = tcpu
                f.write(_json.dumps({"type": "resource_sample", "timestamp_utc": 1000.0 + i,
                                     "name": "", "payload": p}) + "\n")
        return str(run / "manifest.json")

    def test_avg_min_max_main_and_tree(self, tmp_path, capsys, monkeypatch):
        monkeypatch.setenv("NO_COLOR", "1")  # deterministic (no ANSI) for exact matching
        from pubrun.report.diagnostics import print_resources_report
        # rss 10,20,30 MB ; cpu 10,20,30% ; tree cpu 100,200,300%
        MB = 1024 * 1024
        samples = [(10 * MB, 10.0, 10 * MB, 100.0),
                   (20 * MB, 20.0, 20 * MB, 200.0),
                   (30 * MB, 30.0, 30 * MB, 300.0)]
        print_resources_report(self._run_with_events(tmp_path, samples), metric="all")
        out = capsys.readouterr().out
        assert "CPU (main)   : peak 30.0% / avg 20.0% / min 10.0%" in out
        assert "CPU (tree)" in out and "peak 300.0% / avg 200.0% / min 100.0%" in out
        assert "of one core" in out  # tree-cpu caveat label
        assert "RSS (main)" in out and "peak 30.00 MB / avg 20.00 MB / min 10.00 MB" in out

    def test_series_helper(self, tmp_path):
        from pubrun.report.diagnostics import read_resource_series, _series_stats
        m = self._run_with_events(tmp_path, [(1, 5.0, None, None), (3, 15.0, None, None)])
        from pathlib import Path as _P
        s = read_resource_series(_P(m).parent / "events.jsonl")
        assert s["rss"] == [1, 3] and s["cpu"] == [5.0, 15.0]
        assert _series_stats(s["cpu"]) == (15.0, 10.0, 5.0)
        assert _series_stats([]) is None  # empty -> None (peak-fallback path)


class TestTimelineFormatting:
    """Compact timestamps + oldest-10/newest-10 truncation above 20 events."""

    def _run_with_n_events(self, tmp_path, n):
        import json as _json
        run = tmp_path / "runs" / "pubrun-tl"
        run.mkdir(parents=True)
        (run / "manifest.json").write_text(_json.dumps({
            "run_id": "tl", "invocation": {"script": {"basename": "s.py"}},
            "status": {"outcome": "completed"},
            "timing": {"started_at_utc": 1000.0},
        }))
        with open(run / "events.jsonl", "w") as f:
            for i in range(n):
                f.write(_json.dumps({"type": "annotate", "timestamp_utc": 1000.0 + i,
                                     "name": f"ev{i}", "payload": {}}) + "\n")
        return str(run / "manifest.json")

    def test_compact_timestamp_and_utc(self, tmp_path, capsys):
        from pubrun.report.diagnostics import print_report
        print_report(self._run_with_n_events(tmp_path, 3), depth="basic", utc=True)
        out = capsys.readouterr().out
        # Compact 'YYYY-MM-DD HH:MM:SS' (no microseconds, no +00:00), UTC.
        assert "1970-01-01 00:16:40" in out  # epoch 1000 in UTC
        assert "+00:00" not in out and ".0" not in out.split("Event Timeline")[-1][:200]

    def test_truncation_above_20(self, tmp_path, capsys):
        from pubrun.report.diagnostics import print_report
        print_report(self._run_with_n_events(tmp_path, 25), depth="basic", utc=True)
        out = capsys.readouterr().out
        assert "events truncated" in out
        assert "ev0" in out and "ev24" in out  # oldest + newest shown
        assert "ev12" not in out              # middle truncated

    def test_no_truncation_at_or_below_20(self, tmp_path, capsys):
        from pubrun.report.diagnostics import print_report
        print_report(self._run_with_n_events(tmp_path, 20), depth="basic", utc=True)
        out = capsys.readouterr().out
        assert "truncated" not in out
        assert "ev0" in out and "ev19" in out
