"""Cross-platform unit tests for filesystem, system_metrics, and resources seams."""
import ctypes
import subprocess
import sys
import threading
from types import SimpleNamespace

from pubrun.capture import filesystem, resources, system_metrics


class TestMacFilesystemMountTable:
    """Tests for macOS mount-table parsing and failure handling."""

    def test_mac_mount_table_parses_spaces_and_skips_malformed(self, monkeypatch):
        sample = (
            "/dev/disk1s1 on / (apfs, local, journaled)\n"
            "server:/export on /Volumes/My Share (nfs, nodev, nosuid)\n"
            "malformed line without separator\n"
            "partial on line without parens\n"
        )
        monkeypatch.setattr(subprocess, "check_output", lambda *args, **kwargs: sample)

        assert filesystem._mac_mount_table() == [
            ("/", "apfs"),
            ("/Volumes/My Share", "nfs"),
        ]

    def test_get_filesystem_darwin_timeout_returns_failed(self, monkeypatch):
        def raise_timeout(*args, **kwargs):
            raise subprocess.TimeoutExpired(cmd=["mount"], timeout=2.0)

        monkeypatch.setattr(filesystem.sys, "platform", "darwin")
        monkeypatch.setattr(subprocess, "check_output", raise_timeout)

        res = filesystem.get_filesystem({}, {"out": "/x"})
        assert res["capture_state"]["status"] == "failed"


class TestWindowsFilesystemClassification:
    """Tests for Windows ctypes filesystem classification paths."""

    def test_classify_windows_path_remote_and_api_failures(self, monkeypatch):
        state = {
            "vol_path_ok": 1,
            "vol_root": "Z:\\",
            "vol_info_ok": 1,
            "fs_name": "NTFS",
            "drive_type": 4,  # DRIVE_REMOTE
        }

        class FakeKernel32:
            def GetVolumePathNameW(self, path_ptr, buf, size):
                if not state["vol_path_ok"]:
                    return 0
                buf.value = state["vol_root"]
                return 1

            def GetVolumeInformationW(
                self, root_ptr, vol_buf, vol_size, serial, max_comp, flags, fs_buf, fs_size
            ):
                if not state["vol_info_ok"]:
                    return 0
                fs_buf.value = state["fs_name"]
                return 1

            def GetDriveTypeW(self, root_ptr):
                return state["drive_type"]

        monkeypatch.setattr(
            ctypes,
            "windll",
            SimpleNamespace(kernel32=FakeKernel32()),
            raising=False,
        )

        remote = filesystem._classify_windows_path("Z:\\runs\\out")
        assert remote == {
            "path": "Z:\\runs\\out",
            "mount_point": "Z:\\",
            "fstype": "NTFS",
            "is_network": True,
        }

        state["vol_path_ok"] = 0
        failed = filesystem._classify_windows_path("Z:\\bad")
        assert failed == {
            "path": "Z:\\bad",
            "capture_state": {"status": "failed", "detail": "GetVolumePathNameW failed"},
        }

        state["vol_path_ok"] = 1
        state["vol_info_ok"] = 0
        state["drive_type"] = 3  # DRIVE_FIXED
        unknown_fs = filesystem._classify_windows_path("C:\\local")
        assert unknown_fs["fstype"] == "unknown"
        assert unknown_fs["is_network"] is False

    def test_classify_windows_isolates_errors_and_skips_empty_paths(self, monkeypatch):
        def fake_classify(path):
            if path == "BAD:\\path":
                raise OSError("volume lookup error")
            return {
                "path": path,
                "mount_point": "C:\\",
                "fstype": "NTFS",
                "is_network": False,
            }

        monkeypatch.setattr(filesystem, "_classify_windows_path", fake_classify)

        res = filesystem._classify_windows(
            {"broken": "BAD:\\path", "good": "C:\\work", "empty": ""}
        )
        assert res["capture_state"] == {"status": "complete"}
        assert res["broken"] == {
            "path": "BAD:\\path",
            "capture_state": {"status": "failed", "detail": "volume lookup error"},
        }
        assert res["good"] == {
            "path": "C:\\work",
            "mount_point": "C:\\",
            "fstype": "NTFS",
            "is_network": False,
        }
        assert "empty" not in res


class TestLiveProbeSemaphoreSeam:
    """Tests for LiveProbe semaphore injection, cap exhaustion, and release."""

    def test_live_probe_exhausted_semaphore_returns_skipped(self, tmp_path):
        sem = threading.BoundedSemaphore(1)
        assert sem.acquire(blocking=False) is True
        try:
            probe = filesystem.LiveProbe(str(tmp_path), 0.1, semaphore=sem)
            assert probe.result() == {
                "status": "skipped",
                "detail": "probe cap reached",
            }
        finally:
            sem.release()

    def test_live_probe_error_releases_injected_semaphore_not_global(
        self, monkeypatch, tmp_path
    ):
        def raise_dead(path):
            raise OSError("dead")

        monkeypatch.setattr(filesystem, "_statvfs_metrics", raise_dead)
        global_before = filesystem._live_probe_sem._value
        sem = threading.BoundedSemaphore(1)

        probe = filesystem.LiveProbe(str(tmp_path), 1.0, semaphore=sem)
        probe._thread.join(timeout=5.0)

        res = probe.result()
        assert res["status"] == "error"
        assert res["detail"] == "dead"
        assert sem.acquire(blocking=False) is True
        sem.release()
        assert filesystem._live_probe_sem._value == global_before


class TestProcPathSeams:
    """Tests for /proc path seams in filesystem.py and system_metrics.py."""

    def test_parse_proc_mountinfo_seam_unescapes_and_skips_malformed(self, tmp_path):
        mountinfo = tmp_path / "mountinfo"
        mountinfo.write_text(
            "36 35 98:0 / /mnt/with\\040space rw,noatime master:1 - ext4 /dev/sda1 rw\n"
            "malformed short line\n"
            "37 35 98:1 / /no/sep rw,noatime master:2 ext4 /dev/sda2 rw\n"
            "38 35 98:2 / /trailing/sep rw,noatime -\n",
            encoding="utf-8",
        )
        assert filesystem._parse_proc_mountinfo(str(mountinfo)) == [
            ("/mnt/with space", "ext4"),
        ]

    def test_parse_proc_mounts_seam_returns_pairs(self, tmp_path):
        mounts = tmp_path / "mounts"
        mounts.write_text(
            "/dev/sda1 / ext4 rw 0 0\n"
            "server:/share /mnt/my\\040nfs nfs4 rw 0 0\n"
            "short_line\n",
            encoding="utf-8",
        )
        assert filesystem._parse_proc_mounts(str(mounts)) == [
            ("/", "ext4"),
            ("/mnt/my nfs", "nfs4"),
        ]

    def test_read_proc_stat_cpu_times_seam_and_edge_cases(self, monkeypatch, tmp_path):
        monkeypatch.setattr(system_metrics.sys, "platform", "linux")

        valid = tmp_path / "stat_valid"
        valid.write_text("cpu  10 0 5 80 5 0 0 0 0 0\ncpu0 5 0 2 40 2\n", encoding="utf-8")
        assert system_metrics.read_proc_stat_cpu_times(str(valid)) == (5, 100)

        too_few = tmp_path / "stat_short"
        too_few.write_text("cpu  10 0 5 80\n", encoding="utf-8")
        assert system_metrics.read_proc_stat_cpu_times(str(too_few)) is None

        wrong_line = tmp_path / "stat_wrong"
        wrong_line.write_text("cpu0 10 0 5 80 5 0 0 0 0 0\n", encoding="utf-8")
        assert system_metrics.read_proc_stat_cpu_times(str(wrong_line)) is None

        # Passing a directory triggers a read error -> None
        assert system_metrics.read_proc_stat_cpu_times(str(tmp_path)) is None

        # Non-Linux returns None even with a valid file
        monkeypatch.setattr(system_metrics.sys, "platform", "darwin")
        assert system_metrics.read_proc_stat_cpu_times(str(valid)) is None

    def test_get_proc_io_seam_and_edge_cases(self, monkeypatch, tmp_path):
        monkeypatch.setattr(system_metrics.sys, "platform", "linux")

        io_file = tmp_path / "proc_io"
        io_file.write_text(
            "rchar: 123\n"
            "wchar: not_an_int\n"
            "read_bytes: 45\n"
            "ignored_key: 999\n",
            encoding="utf-8",
        )
        assert system_metrics.get_proc_io(str(io_file)) == {
            "rchar": 123,
            "read_bytes": 45,
        }

        empty_file = tmp_path / "proc_io_empty"
        empty_file.write_text("", encoding="utf-8")
        assert system_metrics.get_proc_io(str(empty_file)) is None

        monkeypatch.setattr(system_metrics.sys, "platform", "win32")
        assert system_metrics.get_proc_io(str(io_file)) is None

    def test_get_system_memory_seam_converts_kb_to_bytes(self, monkeypatch, tmp_path):
        monkeypatch.setattr(system_metrics.sys, "platform", "linux")

        meminfo = tmp_path / "meminfo"
        meminfo.write_text(
            "MemTotal:       100 kB\n"
            "MemFree:         20 kB\n"
            "MemAvailable:    50 kB\n"
            "Cached:          10 kB\n"
            "Buffers:          5 kB\n",
            encoding="utf-8",
        )
        assert system_metrics.get_system_memory(str(meminfo)) == {
            "total_bytes": 100 * 1024,
            "free_bytes": 20 * 1024,
            "available_bytes": 50 * 1024,
            "cached_bytes": 10 * 1024,
        }

        monkeypatch.setattr(system_metrics.sys, "platform", "darwin")
        assert system_metrics.get_system_memory(str(meminfo)) is None

    def test_default_paths_work_without_arguments(self):
        if sys.platform.startswith("linux"):
            mounts = filesystem._parse_proc_mounts()
            mountinfo = filesystem._parse_proc_mountinfo()
            mem = system_metrics.get_system_memory()
            cpu_times = system_metrics.read_proc_stat_cpu_times()
            proc_io = system_metrics.get_proc_io()

            assert mounts and len(mounts) > 0
            assert mountinfo and len(mountinfo) > 0
            assert mem is not None and len(mem) > 0
            assert cpu_times is not None and len(cpu_times) == 2
            assert proc_io is not None and len(proc_io) > 0
        else:
            assert system_metrics.get_system_memory() is None
            assert system_metrics.read_proc_stat_cpu_times() is None
            assert system_metrics.get_proc_io() is None


class TestResourcesSystemMetricsAndPlatformRss:
    """Deterministic unit tests for resources.py aggregation, RSS readers, and poll timeout."""

    def test_system_metrics_aggregation(self, monkeypatch):
        mem_samples = iter(
            [
                {"available_bytes": 50, "tag": "start"},
                {"available_bytes": 30, "tag": "first"},
                {"available_bytes": 30, "tag": "tie"},
                {"available_bytes": 40, "tag": "last"},
            ]
        )
        load_samples = iter(
            [
                {"1min": 1.0},
                {"1min": 3.0},
                {"1min": 2.0},
                {"1min": 0.5},
            ]
        )
        cpu_samples = iter([(0, 0), (30, 100), (40, 200), (50, 300)])
        io_samples = iter(
            [
                {"rchar": 100, "wchar": 10, "read_bytes": 1, "write_bytes": 2},
                {"rchar": 200, "wchar": 15, "read_bytes": 3, "write_bytes": 2},
                {"rchar": 300, "wchar": 20, "read_bytes": 6, "write_bytes": 2},
                {"rchar": 400, "wchar": 25, "read_bytes": 9, "write_bytes": 2},
            ]
        )

        monkeypatch.setattr(system_metrics, "get_system_memory", lambda: next(mem_samples))
        monkeypatch.setattr(system_metrics, "get_load_average", lambda: next(load_samples))
        monkeypatch.setattr(
            system_metrics, "read_proc_stat_cpu_times", lambda: next(cpu_samples)
        )
        monkeypatch.setattr(system_metrics, "get_proc_io", lambda: next(io_samples))

        watcher = resources.ResourceWatcher(None, 1.0, system_metrics=True)
        watcher._sample_system_metrics()
        watcher._sample_system_metrics()
        watcher._sample_system_metrics()

        manifest = watcher.to_manifest_dict()
        assert manifest["system_memory"]["min_available"] == {
            "available_bytes": 30,
            "tag": "first",
        }
        assert manifest["system_memory"]["last"] == {
            "available_bytes": 40,
            "tag": "last",
        }
        assert manifest["load_average"]["max_1min"] == 3.0
        assert manifest["load_average"]["last"] == {"1min": 0.5}
        assert manifest["system_iowait_pct"] == {"last": 10.0, "max": 30.0}
        assert manifest["io_counters"]["delta"] == {
            "rchar": 300,
            "wchar": 15,
            "read_bytes": 8,
            "write_bytes": 0,
        }

    def test_get_rss_windows_ctypes_and_wmic_fallback(self, monkeypatch):
        monkeypatch.setattr(resources.sys, "platform", "win32")

        def fake_get_current_process():
            return 77

        def fake_k32_get_mem_info(handle, counters_ptr, size):
            counters_ptr._obj.WorkingSetSize = 654321
            return 1

        fake_kernel32 = SimpleNamespace(
            GetCurrentProcess=fake_get_current_process,
            K32GetProcessMemoryInfo=fake_k32_get_mem_info,
        )
        monkeypatch.setattr(
            ctypes,
            "windll",
            SimpleNamespace(kernel32=fake_kernel32),
            raising=False,
        )

        assert resources._get_rss_windows() == 654321

        # Fallback to wmic when ctypes.windll is unavailable
        monkeypatch.setattr(ctypes, "windll", None, raising=False)
        monkeypatch.setattr(
            subprocess,
            "check_output",
            lambda *args, **kwargs: "WorkingSetSize\n999\n",
        )
        assert resources._get_rss_windows() == 999

    def test_get_rss_darwin_uses_poll_timeout_and_handles_timeout(self, monkeypatch):
        captured = {}

        def fake_check_output(cmd, **kwargs):
            captured["timeout"] = kwargs.get("timeout")
            return "2048\n"

        monkeypatch.setattr(resources, "_poll_timeout", 1.5)
        monkeypatch.setattr(subprocess, "check_output", fake_check_output)

        assert resources._get_rss_darwin() == 2048 * 1024
        assert captured["timeout"] == 1.5

        def raise_timeout(cmd, **kwargs):
            raise subprocess.TimeoutExpired(cmd=cmd, timeout=1.5)

        monkeypatch.setattr(subprocess, "check_output", raise_timeout)
        assert resources._get_rss_darwin() == -1

    def test_set_poll_timeout_sets_and_resets_default(self, monkeypatch):
        monkeypatch.setattr(resources, "_poll_timeout", resources._poll_timeout)

        resources.set_poll_timeout(7)
        assert resources._poll_timeout == 7.0

        resources.set_poll_timeout("abc")
        assert resources._poll_timeout == resources._DEFAULT_POLL_TIMEOUT

        resources.set_poll_timeout(9)
        assert resources._poll_timeout == 9.0

        resources.set_poll_timeout(None)  # type: ignore[arg-type]
        assert resources._poll_timeout == resources._DEFAULT_POLL_TIMEOUT
