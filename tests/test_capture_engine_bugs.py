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
from pubrun.capture.console import ConsoleInterceptor, TqdmSafeTee
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


class TestConsoleResumeAfterMigration:
    def test_single_stream_reopen_failure_marks_partial_and_keeps_sibling(
        self, tmp_path, monkeypatch, caplog
    ):
        dir1 = tmp_path / "d1"
        dir2 = tmp_path / "d2"
        dir1.mkdir()
        dir2.mkdir()

        interceptor = ConsoleInterceptor(dir1, mode="basic")
        assert interceptor.start() is True
        real_open = open

        def fail_stdout_in_dir2(path, *args, **kwargs):
            if str(path) == str(dir2 / "stdout.log"):
                raise PermissionError(
                    "cannot open https://user:topsecret@host/stdout.log"
                )
            return real_open(path, *args, **kwargs)

        try:
            sys.stdout.write("before out\n")
            sys.stderr.write("before err\n")
            was_fh = interceptor.suspend_for_migration()

            monkeypatch.setattr("builtins.open", fail_stdout_in_dir2)
            with caplog.at_level(logging.DEBUG, logger="pubrun"):
                interceptor.resume_after_migration(dir2, reenable_faulthandler=was_fh)
            monkeypatch.undo()

            assert interceptor.run_dir == dir2
            assert interceptor.stdout_log is None
            assert interceptor.stdout_tee is not None
            assert interceptor.stdout_tee.log_file is None
            assert interceptor.stdout_tee._log_write_failed is True

            assert interceptor.stderr_log is not None
            assert interceptor.stderr_tee is not None
            assert interceptor.stderr_tee.log_file is interceptor.stderr_log
            assert interceptor.stderr_tee._log_write_failed is False
            assert interceptor._faulthandler_owned is was_fh

            sys.stdout.write("after out\n")
            sys.stderr.write("after err\n")
        finally:
            monkeypatch.undo()
            result = interceptor.stop()

        assert result["capture_state"]["status"] == "partial"
        assert "after err" in (dir2 / "stderr.log").read_text(encoding="utf-8")
        debug_msgs = [r.getMessage() for r in caplog.records]
        assert any("stdout.log" in msg and "[REDACTED]" in msg for msg in debug_msgs)
        assert all("topsecret" not in msg for msg in debug_msgs)

    def test_both_streams_reopen_failure_marks_partial(self, tmp_path):
        dir1 = tmp_path / "d1"
        dir1.mkdir()
        missing_dir = tmp_path / "missing_dir"

        interceptor = ConsoleInterceptor(dir1, mode="basic")
        assert interceptor.start() is True
        try:
            was_fh = interceptor.suspend_for_migration()
            interceptor.resume_after_migration(
                missing_dir, reenable_faulthandler=was_fh
            )
            assert interceptor.stdout_log is None
            assert interceptor.stderr_log is None
            assert interceptor.stdout_tee is not None
            assert interceptor.stderr_tee is not None
            assert interceptor.stdout_tee.log_file is None
            assert interceptor.stderr_tee.log_file is None
            assert interceptor.stdout_tee._log_write_failed is True
            assert interceptor.stderr_tee._log_write_failed is True
            assert interceptor._faulthandler_owned is False
        finally:
            result = interceptor.stop()

        assert result["capture_state"]["status"] == "partial"

    def test_resume_after_failed_start_opens_no_files_and_stays_failed(self, tmp_path):
        missing_initial = tmp_path / "no_such_initial_dir"
        dir2 = tmp_path / "d2"
        dir2.mkdir()

        interceptor = ConsoleInterceptor(missing_initial, mode="basic")
        assert interceptor.start() is False
        try:
            interceptor.resume_after_migration(dir2, reenable_faulthandler=True)
            assert interceptor.run_dir == dir2
            assert interceptor.stdout_log is None
            assert interceptor.stderr_log is None
            assert not (dir2 / "stdout.log").exists()
            assert not (dir2 / "stderr.log").exists()
            assert interceptor._faulthandler_owned is False
        finally:
            result = interceptor.stop()

        assert result["capture_state"]["status"] == "failed"


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
        redaction._compile_secret_pattern.cache_clear()
        cfg = {"redaction": {"sensitive_keys_regex": "[unclosed"}}
        with caplog.at_level(logging.WARNING, logger="pubrun"):
            pat = redaction._get_secret_pattern(cfg)
        assert pat.pattern == redaction.DEFAULT_SECRET_REGEX
        # Only DEFAULT_SECRET_REGEX should be cached, never the invalid regex.
        assert redaction._compile_secret_pattern.cache_info().currsize == 1
        assert any("sensitive_keys_regex" in r.getMessage() for r in caplog.records)
        out = redaction.redact_argv(["x", "--password", "S3CRET"], cfg)
        assert "S3CRET" not in out

    def test_pattern_lru_cache_is_bounded_at_64(self):
        redaction._compile_secret_pattern.cache_clear()
        for i in range(80):
            pat = redaction._get_secret_pattern(
                {"redaction": {"sensitive_keys_regex": f"custom_secret_{i}"}}
            )
            assert pat.search(f"custom_secret_{i}") is not None
        info = redaction._compile_secret_pattern.cache_info()
        assert info.maxsize == 64
        assert info.currsize == 64

    def test_iterative_deep_json_and_cycle_redaction(self, monkeypatch):
        import json as _json

        # 1. Direct _redact_any handles 1,500 levels of nesting without RecursionError.
        deep: dict = {"password": "TOP_SECRET_VALUE", "safe": "ok"}
        for _ in range(1500):
            deep = {"nested": deep}
        redacted = redaction._redact_any(deep, {})
        cur = redacted
        for _ in range(1500):
            cur = cur["nested"]
        assert cur["password"] == "[REDACTED]"
        assert cur["safe"] == "ok"

        # 2. Cyclic container references terminate cleanly and still redact secrets.
        cyc: dict = {"api_key": "CYCLE_SECRET"}
        cyc["self"] = cyc
        cyc_out = redaction._redact_any(cyc, {})
        assert cyc_out["api_key"] == "[REDACTED]"
        assert cyc_out["self"] is cyc_out

        # 3. 1,500-level JSON string redacts secrets on every Python version
        # (via iterative _redact_any on Python 3.12+ or RecursionError fallback on <3.12).
        deep_json_str = (
            '{"a":' * 1500
            + '{"password":"DEEP_JSON_PW","credentials":{"raw":"NESTED_OBJ_SECRET"},"ok":"https://u:uri_pw@db/x"}'
            + "}" * 1500
        )
        out_str = redaction._redact_value_string_heuristics(deep_json_str, {})
        assert "DEEP_JSON_PW" not in out_str
        assert "NESTED_OBJ_SECRET" not in out_str
        assert "uri_pw" not in out_str
        assert '"password": "[REDACTED]"' in out_str or '"password":"[REDACTED]"' in out_str
        assert '"credentials": "[REDACTED]"' in out_str or '"credentials":"[REDACTED]"' in out_str

        # 4. Simulated json.loads RecursionError explicitly exercises fallback even on shallow JSON.
        def raise_rec(*a, **k):
            raise RecursionError("simulated recursion limit")

        monkeypatch.setattr(_json, "loads", raise_rec)
        shallow_out = redaction._redact_value_string_heuristics(
            '{"token": "FALLBACK_TOK", "credentials": {"raw": "OBJ_SEC"}, "note": "Bearer MY_BEARER_123"}',
            {},
        )
        assert "FALLBACK_TOK" not in shallow_out
        assert "OBJ_SEC" not in shallow_out
        assert "MY_BEARER_123" not in shallow_out
        assert '"token": "[REDACTED]"' in shallow_out
        assert '"credentials": "[REDACTED]"' in shallow_out

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
        if platform == "win32":
            monkeypatch.setattr(hw, "_get_windows_gpus_native", lambda: [])
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
        assert gpus[1]["memory_total_bytes"] == 4 * 1024 ** 3


# ---------------------------------------------------------------------------
# ROLL-31 / ROLL-34: liveness caching/locale/guards, iowait clamping, filesystem
# ---------------------------------------------------------------------------

class TestLivenessCrossPlatformHardening:
    def test_win_dll_and_struct_caching_and_fake_precedence(self, monkeypatch):
        import ctypes
        from types import SimpleNamespace

        created = []

        class FakeFunc:
            def __init__(self, fn):
                self._fn = fn
                self.argtypes = None
                self.restype = None

            def __call__(self, *args):
                return self._fn(*args)

        class FakeWinDLL:
            def __init__(self, name, use_last_error=False):
                created.append((name, use_last_error))
                self.name = name
                if name == "kernel32":
                    self.OpenProcess = FakeFunc(lambda access, inherit, pid: 77)
                    self.GetExitCodeProcess = FakeFunc(lambda h, ptr: 1)
                    self.GetProcessTimes = FakeFunc(lambda h, c, e, k, u: 1)
                    self.CloseHandle = FakeFunc(lambda h: 1)
                elif name == "psapi":
                    def _get_mem(handle, counters_ptr, cb):
                        counters_ptr._obj.WorkingSetSize = 987654
                        return 1
                    self.GetProcessMemoryInfo = FakeFunc(_get_mem)

        monkeypatch.setattr(liveness, "_WIN_KERNEL32", None)
        monkeypatch.setattr(liveness, "_WIN_PSAPI", None)
        monkeypatch.setattr(liveness, "_PROCESS_MEMORY_COUNTERS_CLS", None)
        monkeypatch.setattr(ctypes, "WinDLL", FakeWinDLL, raising=False)
        real_sentinel = FakeWinDLL("kernel32")
        created.clear()
        monkeypatch.setattr(
            ctypes, "windll", SimpleNamespace(kernel32=real_sentinel), raising=False
        )

        # Two consecutive polls instantiate kernel32 and psapi once and reuse struct class.
        assert liveness._get_rss_windows(100) == 987654
        cls1 = liveness._PROCESS_MEMORY_COUNTERS_CLS
        k32_1 = liveness._WIN_KERNEL32
        psapi_1 = liveness._WIN_PSAPI
        assert liveness._get_rss_windows(100) == 987654
        assert liveness._PROCESS_MEMORY_COUNTERS_CLS is cls1
        assert liveness._WIN_KERNEL32 is k32_1
        assert liveness._WIN_PSAPI is psapi_1
        assert created == [("kernel32", True), ("psapi", True)]

        # A monkeypatched non-WinDLL fake kernel32 ALWAYS wins over cached _WIN_KERNEL32
        # and never has argtypes/restype mutated on it.
        class PlainFakeKernel32:
            def OpenProcess(self, access, inherit, pid):
                return 88

            def K32GetProcessMemoryInfo(self, handle, counters_ptr, cb):
                counters_ptr._obj.WorkingSetSize = 123456
                return 1

            def CloseHandle(self, handle):
                return 1

        plain_fake = PlainFakeKernel32()
        monkeypatch.setattr(
            ctypes, "windll", SimpleNamespace(kernel32=plain_fake), raising=False
        )
        assert liveness._get_win_kernel32() is plain_fake
        assert liveness._get_rss_windows(100) == 123456
        assert not hasattr(plain_fake.K32GetProcessMemoryInfo, "argtypes")

    def test_macos_cpu_passes_lc_all_c(self, monkeypatch):
        captured = {}

        class R:
            returncode = 0
            stdout = "23.4\n"

        def fake_run(cmd, **kw):
            captured.update(kw)
            return R()

        monkeypatch.setattr(liveness.subprocess, "run", fake_run)
        assert liveness._get_cpu_macos(123) == 23.4
        assert captured["env"]["LC_ALL"] == "C"

    def test_linux_proc_stat_malformed_and_nonpositive_clk_tck(self, monkeypatch):
        stat_text = {"content": "no parens at all 1 2 3\n"}

        def fake_open(path, *a, **k):
            if path == "/proc/99/stat":
                return StringIO(stat_text["content"])
            if path == "/proc/stat":
                return StringIO("btime 1000\n")
            if path == "/proc/uptime":
                return StringIO("500.0 100.0\n")
            raise FileNotFoundError(path)

        monkeypatch.setattr(liveness, "open", fake_open, raising=False)
        monkeypatch.setattr(liveness.os, "sysconf", lambda name: 100, raising=False)

        # Missing right paren -> None (must not slice from index 1)
        assert liveness._get_start_time_linux(99) is None
        assert liveness._get_cpu_linux(99) is None

        # Valid stat line but clock_ticks <= 0 -> None (no ZeroDivisionError)
        stat_text["content"] = "99 (py) S " + " ".join(["0"] * 18) + " 500 0\n"
        monkeypatch.setattr(liveness.os, "sysconf", lambda name: 0, raising=False)
        assert liveness._get_start_time_linux(99) is None
        assert liveness._get_cpu_linux(99) is None

        monkeypatch.setattr(liveness.os, "sysconf", lambda name: -1, raising=False)
        assert liveness._get_start_time_linux(99) is None
        assert liveness._get_cpu_linux(99) is None

        # Missing os.sysconf raises AttributeError -> caught and returns None
        monkeypatch.delattr(liveness.os, "sysconf", raising=False)
        assert liveness._get_start_time_linux(99) is None
        assert liveness._get_cpu_linux(99) is None

    def test_iowait_pct_between_clamped_to_0_100(self):
        from pubrun.capture import system_metrics as sm

        assert sm.iowait_pct_between((50, 100), (40, 200)) == 0.0
        assert sm.iowait_pct_between((10, 100), (200, 200)) == 100.0
        assert sm.iowait_pct_between((10, 100), (35, 200)) == 25.0


class TestFilesystemCrossPlatformFixes:
    def test_windows_dynamic_volume_buffer_for_long_path(self, monkeypatch):
        import ctypes
        from types import SimpleNamespace

        seen_sizes = []

        class FakeKernel32:
            def GetVolumePathNameW(self, path_ptr, buf, size):
                seen_sizes.append(size)
                buf.value = "C:\\"
                return 1

            def GetVolumeInformationW(self, root_ptr, vol_buf, vol_size, s, m, f, fs_buf, fs_size):
                fs_buf.value = "NTFS"
                return 1

            def GetDriveTypeW(self, root_ptr):
                return 3

        monkeypatch.setattr(
            ctypes, "windll", SimpleNamespace(kernel32=FakeKernel32()), raising=False
        )
        long_path = "C:\\" + ("nested_dir\\" * 120) + "file.txt"
        assert len(long_path) > 1024
        res = fs._classify_windows_path(long_path)
        assert res["mount_point"] == "C:\\"
        assert res["fstype"] == "NTFS"
        assert seen_sizes == [len(long_path) + 2]

    def test_posix_leading_double_slash_normalized(self):
        entries = [("/", "ext4"), ("/scratch", "nfs4")]
        assert fs._longest_prefix_fstype("//scratch/run", entries) == ("/scratch", "nfs4")
        classified = fs._classify_path_linux("//scratch/run", entries)
        assert classified["mount_point"] == "/scratch"
        assert classified["fstype"] == "nfs4"
        assert classified["is_network"] is True

    def test_macos_case_insensitive_mount_prefix_preserves_casing(self, monkeypatch):
        entries = [("/", "apfs"), ("/Volumes/DataDrive", "nfs")]
        assert fs._longest_prefix_fstype(
            "/volumes/datadrive/runs/1", entries, case_insensitive=False
        ) == ("/", "apfs")
        assert fs._longest_prefix_fstype(
            "/volumes/datadrive/runs/1", entries, case_insensitive=True
        ) == ("/Volumes/DataDrive", "nfs")

        monkeypatch.setattr(fs.sys, "platform", "darwin")
        monkeypatch.setattr(fs, "_mac_mount_table", lambda: entries)
        res = fs.get_filesystem({}, {"out": "/volumes/datadrive/runs/1"})
        assert res["out"]["mount_point"] == "/Volumes/DataDrive"
        assert res["out"]["fstype"] == "nfs"
        assert res["out"]["is_network"] is True
