"""Regression tests for capture-engine correctness bugs (IPD m780uj).

Covers BUG-04 (console tee CRLF/locking/paused flush), BUG-05 and BUG-37
(argv/URI redaction and invalid regex), BUG-28 (mount table parsing and live
probe), BUG-35 (thread-child resource accounting), BUG-36 and BUG-62
(liveness), BUG-38 (subprocess wait status and poll reaping), and BUG-61
(GPU capture).
"""
import io
import logging
import os
import subprocess
import sys
import threading
import time
from io import StringIO

import pytest

import pubrun
from pubrun.capture import filesystem as fs
from pubrun.capture import hardware as hw
from pubrun.capture import liveness
from pubrun.capture import redaction
from pubrun.capture import resources
from pubrun.capture.console import TqdmSafeTee
from pubrun.capture.subprocesses import SubprocessSpy


# ---------------------------------------------------------------------------
# BUG-04: console tee
# ---------------------------------------------------------------------------

class TestTeeCrlf:
    def _tee(self):
        log = io.StringIO()
        return TqdmSafeTee(io.StringIO(), log), log

    def test_crlf_lines_preserved(self):
        tee, log = self._tee()
        tee.write("hello world\r\nsecond line\r\n")
        assert log.getvalue() == "hello world\nsecond line\n"
        assert tee.line_count == 2

    def test_crlf_split_across_writes(self):
        tee, log = self._tee()
        tee.write("hello\r")
        tee.write("\n")
        assert log.getvalue() == "hello\n"

    def test_bare_cr_at_chunk_end_still_overwrites(self):
        tee, log = self._tee()
        tee.write("50%\r")
        tee.write("100%\n")
        assert log.getvalue() == "100%\n"

    def test_bare_cr_progress_squashed(self):
        tee, log = self._tee()
        tee.write("50%\r100%\n")
        assert log.getvalue() == "100%\n"

    def test_passthrough_unchanged(self):
        orig = io.StringIO()
        tee = TqdmSafeTee(orig, io.StringIO())
        tee.write("a\r\nb\rc\n")
        assert orig.getvalue() == "a\r\nb\rc\n"

    def test_concurrent_writers_keep_lines_whole(self):
        log = io.StringIO()
        tee = TqdmSafeTee(io.StringIO(), log)
        n_threads, n_lines = 8, 300

        def whole_line_worker(k):
            for i in range(n_lines):
                tee.write(f"t{k}-{i}\n")

        threads = [threading.Thread(target=whole_line_worker, args=(k,)) for k in range(n_threads)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        lines = log.getvalue().splitlines()
        assert tee.line_count == n_threads * n_lines
        assert sorted(lines) == sorted(
            f"t{k}-{i}" for k in range(n_threads) for i in range(n_lines)
        )

    def test_paused_flush_does_not_record_buffer(self):
        orig = io.StringIO()
        log = io.StringIO()
        tee = TqdmSafeTee(orig, log)
        with pubrun.paused():
            tee.write("secret-partial")  # no newline: would sit in the buffer
            tee.flush()
        assert "secret-partial" not in log.getvalue()
        assert "secret-partial" in orig.getvalue()

    def test_paused_flush_still_flushes_original(self):
        flushed = []

        class Orig(io.StringIO):
            def flush(self):
                flushed.append(True)
                super().flush()

        tee = TqdmSafeTee(Orig(), io.StringIO())
        with pubrun.paused():
            tee.flush()
        assert flushed

    def test_paused_flush_leaves_earlier_buffer_for_later(self):
        log = io.StringIO()
        tee = TqdmSafeTee(io.StringIO(), log)
        tee.write("recorded-partial")
        with pubrun.paused():
            tee.flush()
        assert log.getvalue() == ""
        tee.flush()
        assert log.getvalue() == "recorded-partial\n"


# ---------------------------------------------------------------------------
# BUG-05 / BUG-37: redaction
# ---------------------------------------------------------------------------

class TestArgvRedaction:
    def test_boolean_sensitive_flag_before_password(self):
        out = redaction.redact_argv(
            ["train.py", "--use-auth", "--password", "SUPERSECRET"], {}
        )
        assert "SUPERSECRET" not in out
        assert out == ["train.py", "--use-auth", "--password", "[REDACTED]"]

    def test_value_after_sensitive_flag_still_redacted(self):
        out = redaction.redact_argv(["x", "--token", "abc123", "--epochs", "3"], {})
        assert out == ["x", "--token", "[REDACTED]", "--epochs", "3"]

    def test_boolean_flag_followed_by_eq_flag(self):
        out = redaction.redact_argv(["x", "--auth", "--api-key=VALUE"], {})
        assert "VALUE" not in " ".join(out)
        assert out[-1] == "--api-key=[REDACTED]"


class TestSecretPattern:
    def test_invalid_regex_falls_back_without_raising(self, caplog):
        cfg = {"redaction": {"sensitive_keys_regex": "[unclosed"}}
        with caplog.at_level(logging.WARNING, logger="pubrun"):
            pat = redaction._get_secret_pattern(cfg)
        assert pat.pattern == redaction.DEFAULT_SECRET_REGEX
        assert "[unclosed" not in redaction._PATTERN_CACHE
        assert any("sensitive_keys_regex" in r.getMessage() for r in caplog.records)
        out = redaction.redact_argv(["x", "--password", "S3CRET"], cfg)
        assert "S3CRET" not in out

    def test_non_string_regex_falls_back_without_raising(self):
        for bad in (123, ["a"], {"x": 1}):
            cfg = {"redaction": {"sensitive_keys_regex": bad}}
            pat = redaction._get_secret_pattern(cfg)
            assert pat.pattern == redaction.DEFAULT_SECRET_REGEX
            assert redaction.is_secret_key("MY_PASSWORD", cfg) is True

    def test_invalid_regex_does_not_break_popen(self):
        cfg = {"redaction": {"sensitive_keys_regex": "(bad"}}
        SubprocessSpy.install(config=cfg)
        try:
            p = subprocess.Popen([sys.executable, "-c", "pass", "--token", "TKN"])
            assert p.wait() == 0
            rec = SubprocessSpy.get_records()[0]
            assert "TKN" not in rec["argv"]
            assert rec["exit_code"] == 0
        finally:
            SubprocessSpy.uninstall()


class TestUriHeuristics:
    def test_multiple_uri_credentials_all_redacted(self):
        val = "postgres://u:pw1@db1/x git+https://tok2@github.com/r mysql://a:pw3@db3/y"
        out = redaction._redact_value_string_heuristics(val, {})
        for secret in ("pw1", "tok2", "pw3"):
            assert secret not in out
        assert "u:[REDACTED]@db1" in out
        assert "://[REDACTED]@github.com" in out

    def test_userpass_and_token_uri_mixed(self):
        val = "a=https://user:pass@h1/p b=https://ghp_tok@h2/p"
        out = redaction._redact_value_string_heuristics(val, {})
        assert "pass@" not in out and "ghp_tok" not in out

    def test_url_followed_by_email_preserved(self):
        val = "see http://example.com email alice@corp.com"
        assert redaction._redact_value_string_heuristics(val, {}) == val


# ---------------------------------------------------------------------------
# BUG-38: subprocess spy
# ---------------------------------------------------------------------------

class TestSubprocessSpy:
    def teardown_method(self):
        SubprocessSpy.uninstall()

    @pytest.mark.skipif(os.name != "posix", reason="POSIX wait-status semantics")
    def test_os_system_records_exit_code_returns_raw_status(self):
        SubprocessSpy.install()
        ret = os.system("exit 1")
        assert ret == 256  # raw wait status unchanged for the host caller
        rec = SubprocessSpy.get_records()[-1]
        assert rec["exit_code"] == 1
        assert rec["capture_state"]["status"] == "failed"

    @pytest.mark.skipif(os.name != "posix", reason="POSIX wait-status semantics")
    def test_os_system_success(self):
        SubprocessSpy.install()
        assert os.system("exit 0") == 0
        rec = SubprocessSpy.get_records()[-1]
        assert rec["exit_code"] == 0
        assert rec["capture_state"]["status"] == "complete"

    def test_decode_wait_status_fallbacks(self, monkeypatch):
        from pubrun.capture import subprocesses as sp
        if os.name == "posix":
            assert sp._decode_wait_status(256) == 1
            assert sp._decode_wait_status(0) == 0
            # Python 3.8 path (no waitstatus_to_exitcode).
            monkeypatch.delattr(os, "waitstatus_to_exitcode", raising=False)
            assert sp._decode_wait_status(256) == 1
            assert sp._decode_wait_status(9) == -9  # killed by SIGKILL
        assert sp._decode_wait_status(-1) == -1  # undecodable stays as-is
        assert sp._decode_wait_status(None) is None

    def test_poll_reaping_records_exit(self):
        orig_poll = subprocess.Popen.poll
        SubprocessSpy.install()
        assert subprocess.Popen.poll is not orig_poll
        p = subprocess.Popen([sys.executable, "-c", "import sys; sys.exit(3)"])
        deadline = time.time() + 30
        while p.poll() is None and time.time() < deadline:
            time.sleep(0.01)
        assert p.poll() == 3
        rec = SubprocessSpy.get_records()[0]
        assert rec["exit_code"] == 3
        assert rec["capture_state"]["status"] == "failed"
        assert "ended_at_utc" in rec
        assert rec["elapsed_seconds"] >= 0
        assert rec["duration_clock"] == "monotonic"
        ended = rec["ended_at_utc"]
        # Idempotent: later wait()/poll() do not overwrite.
        assert p.wait() == 3
        p.poll()
        assert rec["ended_at_utc"] == ended
        SubprocessSpy.uninstall()
        assert subprocess.Popen.poll is orig_poll

    def test_uninstall_keeps_third_party_poll_wrapper(self):
        orig_poll = subprocess.Popen.poll
        try:
            SubprocessSpy.install(owner="o")
            pubrun_poll = subprocess.Popen.poll

            def tp_poll(self, *a, **kw):
                return pubrun_poll(self, *a, **kw)

            subprocess.Popen.poll = tp_poll
            SubprocessSpy.uninstall(owner="o")
            assert subprocess.Popen.poll is tp_poll
        finally:
            SubprocessSpy.uninstall()
            subprocess.Popen.poll = orig_poll

    def test_install_rollback_restores_poll(self, monkeypatch):
        orig_poll = subprocess.Popen.poll
        real_setattr = setattr

        def failing_setattr(obj, name, val):
            if obj is os and name == "system":
                raise RuntimeError("cannot patch os.system")
            return real_setattr(obj, name, val)

        monkeypatch.setattr("builtins.setattr", failing_setattr)
        with pytest.raises(RuntimeError):
            SubprocessSpy.install()
        monkeypatch.undo()
        assert subprocess.Popen.poll is orig_poll
        assert SubprocessSpy._installed is False


# ---------------------------------------------------------------------------
# BUG-28: filesystem
# ---------------------------------------------------------------------------

class TestMountTable:
    def test_later_mount_on_same_point_wins(self):
        entries = [("/", "ext4"), ("/scratch", "autofs"), ("/scratch", "nfs4")]
        assert fs._longest_prefix_fstype("/scratch/x", entries) == ("/scratch", "nfs4")

    def test_rootfs_shadowed_by_later_root(self):
        entries = [("/", "rootfs"), ("/", "ext4")]
        assert fs._longest_prefix_fstype("/data/u", entries) == ("/", "ext4")

    def test_longer_prefix_still_beats_later_shorter(self):
        entries = [("/scratch", "nfs4"), ("/", "ext4")]
        assert fs._longest_prefix_fstype("/scratch/x", entries) == ("/scratch", "nfs4")

    def test_truncated_octal_escape_preserved(self):
        assert fs._unescape_mount_field("foo\\04") == "foo\\04"

    def test_non_octal_digits_preserved(self):
        assert fs._unescape_mount_field("a\\089b") == "a\\089b"

    def test_valid_escapes_decoded(self):
        assert fs._unescape_mount_field("/mnt/with\\040space") == "/mnt/with space"
        assert fs._unescape_mount_field("\\011y") == "\ty"


class TestLiveProbe:
    def test_thread_start_failure_releases_semaphore(self, monkeypatch, tmp_path):
        def boom(self):
            raise RuntimeError("can't start new thread")

        before = fs._live_probe_sem._value
        monkeypatch.setattr(threading.Thread, "start", boom)
        probe = fs.probe_filesystem_live(str(tmp_path), wait_budget_s=0.1)
        monkeypatch.undo()
        res = probe.result()
        assert res["status"] == "error"
        assert "can't start new thread" in res["detail"]
        assert fs._live_probe_sem._value == before

    def test_repeated_failures_do_not_exhaust_cap(self, monkeypatch, tmp_path):
        monkeypatch.setattr(
            threading.Thread, "start", lambda self: (_ for _ in ()).throw(RuntimeError("x"))
        )
        for _ in range(fs._MAX_LIVE_PROBES + 2):
            assert fs.probe_filesystem_live(str(tmp_path), 0.01).result()["status"] == "error"
        monkeypatch.undo()
        res = fs.probe_filesystem_live(str(tmp_path), 5.0).result()
        assert res["status"] in ("complete", "error")


# ---------------------------------------------------------------------------
# BUG-35: Linux thread-child resource accounting
# ---------------------------------------------------------------------------

def _mock_proc(monkeypatch, files, tasks):
    real_open = open
    real_listdir = os.listdir

    def mock_open(path, *args, **kwargs):
        p = str(path)
        if p in files:
            return StringIO(files[p])
        if p.startswith("/proc/"):
            raise FileNotFoundError(p)
        return real_open(path, *args, **kwargs)

    def mock_listdir(path):
        p = str(path)
        if p in tasks:
            return list(tasks[p])
        if p.startswith("/proc/"):
            raise FileNotFoundError(p)
        return real_listdir(path)

    monkeypatch.setattr("builtins.open", mock_open)
    monkeypatch.setattr(os, "listdir", mock_listdir)


@pytest.mark.skipif(not hasattr(os, "sysconf"), reason="POSIX sysconf required")
class TestThreadChildren:
    def _setup(self, monkeypatch):
        me = 4242
        monkeypatch.setattr(os, "getpid", lambda: me)
        files = {
            f"/proc/{me}/statm": "200 100 0 0 0 0 0",
            f"/proc/5001/statm": "100 40 0 0 0 0 0",
            f"/proc/5002/statm": "100 10 0 0 0 0 0",
            f"/proc/{me}/task/{me}/children": "",
            f"/proc/{me}/task/4243/children": "5001",  # worker thread's child
            f"/proc/5001/task/5001/children": "5002",
            f"/proc/5002/task/5002/children": "",
            f"/proc/{me}/stat": f"{me} (py) S " + " ".join(["0"] * 10) + " 7 3 0",
            "/proc/5001/stat": "5001 (child proc) S " + " ".join(["0"] * 10) + " 20 5 0",
            "/proc/5002/stat": "5002 (g) S " + " ".join(["0"] * 10) + " 1 1 0",
        }
        tasks = {
            f"/proc/{me}/task": [str(me), "4243"],
            "/proc/5001/task": ["5001"],
            "/proc/5002/task": ["5002"],
        }
        _mock_proc(monkeypatch, files, tasks)
        return me

    def test_child_pids_cover_all_threads(self, monkeypatch):
        me = self._setup(monkeypatch)
        assert resources._get_linux_child_pids(me) == [5001]

    def test_tree_rss_includes_worker_thread_children(self, monkeypatch):
        page = os.sysconf("SC_PAGE_SIZE")
        self._setup(monkeypatch)
        assert resources._get_tree_rss_linux() == (100 + 40 + 10) * page

    def test_tree_cpu_includes_worker_thread_children(self, monkeypatch):
        self._setup(monkeypatch)
        assert resources._get_tree_cpu_jiffies_linux() == (7 + 3) + (20 + 5) + (1 + 1)


# ---------------------------------------------------------------------------
# BUG-36 / BUG-62: liveness
# ---------------------------------------------------------------------------

class TestScriptMatch:
    def test_sanitized_stem_matches_path_with_space_split(self):
        assert liveness._match_script_in_tokens("my_train", ["python3", "/x/my", "train.py"]) is True

    def test_sanitized_stem_matches_path_with_space_token(self):
        assert liveness._match_script_in_tokens("my_train", ["python3", "/x/my train.py"]) is True

    def test_stem_matches_py_basename(self):
        assert liveness._match_script_in_tokens("train", ["python3", "/x/train.py"]) is True

    def test_exact_basename(self):
        assert liveness._match_script_in_tokens("train.py", ["/usr/bin/python", "/x/train.py"]) is True

    def test_suffix_lookalike_is_inconclusive(self):
        assert liveness._match_script_in_tokens("train.py", ["/usr/bin/python", "/x/train.py.bak"]) is None
        assert liveness._match_script_in_tokens("train", ["/usr/bin/python", "/x/train.py.bak"]) is None

    def test_absent_is_false(self):
        assert liveness._match_script_in_tokens("train.py", ["/usr/bin/python", "/x/other.py"]) is False
        assert liveness._match_script_in_tokens("train", ["/usr/bin/python", "/x/other.py"]) is False

    def test_special_chars_sanitized(self):
        assert liveness._match_script_in_tokens("run_v2_", ["python", "/a/run(v2).py"]) is True


class TestMacStartTime:
    def test_passes_c_locale_and_parses(self, monkeypatch):
        captured = {}

        class R:
            returncode = 0
            stdout = "Thu May 31 14:02:17 2026\n"

        def fake_run(cmd, **kw):
            captured.update(kw)
            return R()

        monkeypatch.setattr(liveness.subprocess, "run", fake_run)
        ts = liveness._get_start_time_macos(123)
        from datetime import datetime
        assert ts == datetime(2026, 5, 31, 14, 2, 17).timestamp()
        assert captured["env"]["LC_ALL"] == "C"
        assert captured["env"]["LC_TIME"] == "C"

    def test_parse_independent_of_strptime_locale(self, monkeypatch):
        import datetime as dt_mod

        class NoStrptime(dt_mod.datetime):
            @classmethod
            def strptime(cls, *a, **k):
                raise ValueError("locale mismatch")

        monkeypatch.setattr(dt_mod, "datetime", NoStrptime)
        assert liveness._parse_c_locale_lstart("Mon Jan  5 01:02:03 2026") is not None
        assert liveness._parse_c_locale_lstart("lun. janv. 5 01:02:03 2026") is None

    def test_garbage_returns_none(self, monkeypatch):
        class R:
            returncode = 0
            stdout = "not a date"

        monkeypatch.setattr(liveness.subprocess, "run", lambda cmd, **kw: R())
        assert liveness._get_start_time_macos(1) is None


# ---------------------------------------------------------------------------
# BUG-61: GPU capture
# ---------------------------------------------------------------------------

class TestGpuFallback:
    def _run(self, monkeypatch, platform, wmic_out=None, sp_out=None):
        def fake_check_output(cmd, **kw):
            if cmd[0] == "nvidia-smi":
                raise FileNotFoundError("nvidia-smi")
            if cmd[0] == "wmic":
                return wmic_out
            if cmd[0] == "system_profiler":
                return sp_out
            raise AssertionError(cmd)

        monkeypatch.setattr(hw.sys, "platform", platform)
        monkeypatch.setattr(hw.subprocess, "check_output", fake_check_output)
        return hw._get_gpus({}, 1.0)

    def test_windows_negative_adapter_ram(self, monkeypatch):
        out = "Node,AdapterRAM,DriverVersion,Name\nPC,-1048576,31.0,Big GPU\nPC,1073741824,30.0,Small GPU\n"
        gpus = self._run(monkeypatch, "win32", wmic_out=out)
        assert gpus[0]["memory_total_bytes"] == (-1048576) & 0xFFFFFFFF
        assert gpus[0]["model"] == "Big GPU"
        assert gpus[1]["memory_total_bytes"] == 1073741824

    def test_windows_blank_adapter_ram(self, monkeypatch):
        out = "Node,AdapterRAM,DriverVersion,Name\nPC,,31.0,Virtual\n"
        gpus = self._run(monkeypatch, "win32", wmic_out=out)
        assert gpus[0]["memory_total_bytes"] is None

    def test_macos_multi_gpu(self, monkeypatch):
        out = (
            "Graphics/Displays:\n\n"
            "    Intel UHD Graphics 630:\n\n"
            "      Chipset Model: Intel UHD Graphics 630\n"
            "      VRAM (Dynamic, Max): 1536 MB\n\n"
            "    AMD Radeon Pro 5500M:\n\n"
            "      Chipset Model: AMD Radeon Pro 5500M\n"
            "      VRAM (Total): 4 GB\n"
        )
        gpus = self._run(monkeypatch, "darwin", sp_out=out)
        assert [g["model"] for g in gpus] == ["Intel UHD Graphics 630", "AMD Radeon Pro 5500M"]
        assert "memory_total_bytes" not in gpus[0]
        assert gpus[1]["memory_total_bytes"] is None
