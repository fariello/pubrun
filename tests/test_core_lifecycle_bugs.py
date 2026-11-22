"""Regression tests for core lifecycle, exit recording, signal, writer, and API bugs.

Covers the bug-audit findings BUG-03, BUG-06, BUG-07, BUG-08, BUG-09, BUG-10,
BUG-29, BUG-30, BUG-31, BUG-32, BUG-33, BUG-34, and BUG-60a. Process-exit
behavior is exercised in real child interpreters so atexit, sys.excepthook,
and sys.exit run exactly as they do for a user script.
"""
import datetime
import json
import os
import signal
import subprocess
import sys
import textwrap
import threading
from pathlib import Path

import pytest

import pubrun
import pubrun.tracker as tracker_mod
from pubrun.capture import signals as signals_mod
from pubrun.capture.signals import SignalExitCapture
from pubrun.events import EventStream

PYTHON = sys.executable
SRC_DIR = str(Path(__file__).resolve().parent.parent / "src")


def _child_env(tmp_path):
    env = dict(os.environ)
    env["PYTHONPATH"] = SRC_DIR + os.pathsep + env.get("PYTHONPATH", "")
    # Keep user-level config out of the child.
    env["HOME"] = str(tmp_path)
    env["USERPROFILE"] = str(tmp_path)
    env["XDG_CONFIG_HOME"] = str(tmp_path / ".xdg")
    for key in ("PUBRUN_IMPORT_MODE", "PUBRUN_PROFILE", "PUBRUN_META_REF"):
        env.pop(key, None)
    return env


def _run_script(tmp_path, body, args=(), timeout=60):
    script = tmp_path / "child_script.py"
    script.write_text(textwrap.dedent(body), encoding="utf-8")
    return subprocess.run(
        [PYTHON, str(script), *args],
        cwd=str(tmp_path),
        env=_child_env(tmp_path),
        capture_output=True,
        text=True,
        timeout=timeout,
    )


def _only_manifest(base):
    manifests = sorted(Path(base).glob("*/manifest.json"))
    assert len(manifests) == 1, f"expected one run under {base}, found {manifests}"
    return json.loads(manifests[0].read_text(encoding="utf-8"))


# =============================================================================
# BUG-03: exception and sys.exit outcome recording
# =============================================================================

class TestExitOutcomeRecording:
    def test_unhandled_exception_records_failed_and_exit_code_1(self, tmp_path):
        res = _run_script(tmp_path, """
            import pubrun
            raise RuntimeError("boom")
        """)
        assert res.returncode == 1
        assert "RuntimeError: boom" in res.stderr
        m = _only_manifest(tmp_path / "runs")
        assert m["status"]["outcome"] == "failed"
        assert m["signals"]["exit_code"] == 1
        assert "RuntimeError" in m["signals"]["exit_exception"]

    def test_sys_exit_nonzero_records_failed_and_code(self, tmp_path):
        res = _run_script(tmp_path, """
            import sys, pubrun
            sys.exit(42)
        """)
        assert res.returncode == 42
        m = _only_manifest(tmp_path / "runs")
        assert m["status"]["outcome"] == "failed"
        assert m["signals"]["exit_code"] == 42

    def test_sys_exit_zero_records_completed(self, tmp_path):
        res = _run_script(tmp_path, """
            import sys, pubrun
            sys.exit(0)
        """)
        assert res.returncode == 0
        m = _only_manifest(tmp_path / "runs")
        assert m["status"]["outcome"] == "completed"
        assert m["signals"]["exit_code"] == 0

    def test_later_sys_exit_overwrites_caught_earlier_one(self, tmp_path):
        res = _run_script(tmp_path, """
            import sys, pubrun
            try:
                sys.exit(5)
            except SystemExit:
                pass
            sys.exit(0)
        """)
        assert res.returncode == 0
        m = _only_manifest(tmp_path / "runs")
        assert m["signals"]["exit_code"] == 0
        assert m["status"]["outcome"] == "completed"

    def test_sys_exit_string_message_is_redacted_and_code_1(self, tmp_path):
        res = _run_script(tmp_path, """
            import sys, pubrun
            sys.exit("fatal: password=hunter2")
        """)
        assert res.returncode == 1
        m = _only_manifest(tmp_path / "runs")
        assert m["signals"]["exit_code"] == 1
        assert m["status"]["outcome"] == "failed"
        assert "hunter2" not in json.dumps(m["signals"])

    def test_keyboard_interrupt_records_interrupted(self, tmp_path):
        res = _run_script(tmp_path, """
            import pubrun
            raise KeyboardInterrupt
        """)
        assert res.returncode != 0
        m = _only_manifest(tmp_path / "runs")
        assert m["status"]["outcome"] == "interrupted"

    def test_normal_return_records_completed(self, tmp_path):
        res = _run_script(tmp_path, """
            import pubrun
            x = 1 + 1
        """)
        assert res.returncode == 0
        m = _only_manifest(tmp_path / "runs")
        assert m["status"]["outcome"] == "completed"
        assert m["signals"]["exit_code"] == 0


class TestSysExitWrapperContract:
    def test_install_wraps_and_uninstall_restores_sys_exit(self):
        original = sys.exit
        cap = SignalExitCapture()
        cap.install()
        try:
            assert sys.exit is not original
            with pytest.raises(SystemExit) as info:
                sys.exit(7)
            assert info.value.code == 7
            assert cap.get_records()["exit_code"] == 7
        finally:
            cap.uninstall()
        assert sys.exit is original

    def test_uninstall_keeps_third_party_sys_exit(self):
        original = sys.exit
        cap = SignalExitCapture()
        cap.install()

        def third_party_exit(*args):
            raise SystemExit(*args)

        sys.exit = third_party_exit
        try:
            cap.uninstall()
            assert sys.exit is third_party_exit
        finally:
            sys.exit = original

    def test_inactive_wrapper_passes_through_without_recording(self):
        original = sys.exit
        cap = SignalExitCapture()
        cap.install()
        wrapper = sys.exit
        cap.uninstall()
        try:
            with pytest.raises(SystemExit) as info:
                wrapper(9)
            assert info.value.code == 9
            assert cap.get_records()["exit_code"] is None
        finally:
            sys.exit = original

    def test_install_failure_rolls_back_sys_exit_and_excepthook(self, monkeypatch):
        original_exit = sys.exit
        original_hook = sys.excepthook
        cap = SignalExitCapture()

        def failing_install():
            raise RuntimeError("install failed")

        monkeypatch.setattr(cap, "_install_sys_exit", failing_install)
        with pytest.raises(RuntimeError):
            cap.install()
        assert sys.exit is original_exit
        assert sys.excepthook is original_hook
        assert cap.get_records()["capture_state"]["status"] == "failed"

    def test_sys_exit_on_worker_thread_is_not_recorded(self):
        cap = SignalExitCapture()
        cap.install()
        try:
            def worker():
                try:
                    sys.exit(3)
                except SystemExit:
                    pass

            t = threading.Thread(target=worker)
            t.start()
            t.join()
            assert cap.get_records()["exit_code"] is None
        finally:
            cap.uninstall()


# =============================================================================
# BUG-08: signal handler deadlock and re-entrant finalization
# =============================================================================

@pytest.mark.skipif(not hasattr(signal, "SIGUSR1"), reason="POSIX signals required")
class TestSignalSafety:
    def test_signal_recorded_while_capture_lock_is_held(self):
        received = []
        previous = signal.signal(signal.SIGUSR1, lambda s, f: received.append(s))
        cap = SignalExitCapture()
        try:
            cap.install()
            done = threading.Event()

            def deliver():
                with cap._lock:
                    os.kill(os.getpid(), signal.SIGUSR1)
                done.set()

            worker = threading.Thread(target=deliver, daemon=True)
            worker.start()
            worker.join(timeout=10)
            assert done.is_set(), "signal delivery deadlocked against capture lock"
            names = [r["signal_name"] for r in cap.get_records()["signals_received"]]
            assert "SIGUSR1" in names
            assert received == [signal.SIGUSR1]
        finally:
            cap.uninstall()
            signal.signal(signal.SIGUSR1, previous)

    def test_sigterm_while_main_thread_holds_lock_finalizes(self, tmp_path):
        res = _run_script(tmp_path, """
            import os, signal, pubrun
            run = pubrun.get_current_run()
            with run.signal_capture._lock:
                os.kill(os.getpid(), signal.SIGTERM)
        """, timeout=30)
        assert res.returncode == -signal.SIGTERM
        m = _only_manifest(tmp_path / "runs")
        names = [r["signal_name"] for r in m["signals"]["signals_received"]]
        assert "SIGTERM" in names
        assert m["status"]["outcome"] == "interrupted"

    def test_nested_finalize_does_not_reenter_write_artifacts(self, monkeypatch):
        calls = []

        class FakeWriter:
            def write_artifacts(self):
                calls.append("write")
                signals_mod._finalize_active_run()

        class FakeRun:
            writer = FakeWriter()

        monkeypatch.setattr(tracker_mod, "_active_run", FakeRun())
        signals_mod._finalize_active_run()
        assert calls == ["write"]
        # The latch is released afterwards, so a later finalization still runs.
        signals_mod._finalize_active_run()
        assert calls == ["write", "write"]


# =============================================================================
# BUG-29 and BUG-10: output_base_dir, stop() ordering, override accumulation
# =============================================================================

class TestRunLifecycle:
    def test_filesystem_output_dir_present_in_manifest(self, tmp_path):
        out = tmp_path / "out"
        run = pubrun.start(output_dir=str(out))
        hw = run._hardware_future_done
        if hw is not None:
            hw.wait(timeout=10)
        run.stop()
        m = json.loads((run.run_dir / "manifest.json").read_text(encoding="utf-8"))
        assert "output_dir" in m["filesystem"]
        assert m["filesystem"]["output_dir"]["path"] == str(out)

    def test_stop_unpublishes_active_run_before_finalization(self, tmp_path, monkeypatch):
        run = pubrun.start(output_dir=str(tmp_path / "out"))
        seen = []
        original = run._finalize_state

        def spy():
            seen.append(pubrun.get_current_run())
            original()

        monkeypatch.setattr(run, "_finalize_state", spy)
        run.stop()
        assert seen and seen[0] is None
        assert pubrun.get_current_run() is None

    def test_repeated_start_preserves_prior_api_overrides(self, tmp_path):
        out = tmp_path / "out"
        overrides = {"events": {"flush_interval_events": 7}}
        run = pubrun.start(output_dir=str(out), **overrides)
        try:
            again = pubrun.start(methods={"format": "latex"})
            assert again is run
            assert run.config["events"]["flush_interval_events"] == 7
            assert run.config["methods"]["format"] == "latex"
            assert run.config["core"]["output_dir"] == str(out)
            # The caller's dict is not mutated by normalization.
            assert overrides == {"events": {"flush_interval_events": 7}}
            run.stop()
        finally:
            run.stop()
        assert (run.run_dir / "methods.tex").exists()

    def test_migration_updates_output_base_dir(self, tmp_path):
        first = tmp_path / "first"
        second = tmp_path / "second"
        run = pubrun.start(output_dir=str(first))
        try:
            pubrun.start(output_dir=str(second))
            assert run.run_dir.parent == second
            assert Path(run.output_base_dir) == second
            run.stop()
        finally:
            run.stop()
        assert (second / run.run_dir.name / "manifest.json").exists()

    def test_core_start_active_branch_forwards_overrides(self, tmp_path):
        run = pubrun.start(output_dir=str(tmp_path / "out"))
        try:
            again = pubrun.start(events={"flush_interval_events": 3})
            assert again is run
            assert run.ref_count == 2
            assert run.config["events"]["flush_interval_events"] == 3
            run.stop()
        finally:
            run.stop()


# =============================================================================
# BUG-09: writer serialization and startup isolation
# =============================================================================

class TestWriterSerialization:
    def test_path_and_date_config_values_write_all_artifacts(self, tmp_path):
        out = tmp_path / "out"
        run = pubrun.start(
            output_dir=out,  # a pathlib.Path, not a str
            notes={"day": datetime.date(2026, 1, 2), "at": datetime.datetime(2026, 1, 2, 3, 4, 5)},
        )
        assert run._outcome != "ghost"
        assert run.run_dir.parent == out
        run.stop()
        cfg = json.loads((run.run_dir / "config.resolved.json").read_text(encoding="utf-8"))
        assert cfg["core"]["output_dir"] == str(out)
        assert cfg["notes"]["day"] == "2026-01-02"
        assert cfg["notes"]["at"] == "2026-01-02 03:04:05"
        m = json.loads((run.run_dir / "manifest.json").read_text(encoding="utf-8"))
        assert m["status"]["outcome"] == "completed"
        assert (run.run_dir / "methods.md").exists()

    def test_startup_config_write_failure_keeps_run_out_of_ghost_mode(self, tmp_path, monkeypatch):
        from pubrun import writer as writer_mod

        def failing_config_write(self, out_dir, *, stage):
            raise OSError("disk full for config")

        monkeypatch.setattr(writer_mod.ArtifactWriter, "_write_config_if_needed", failing_config_write)
        run = pubrun.start(output_dir=str(tmp_path / "out"))
        assert run._outcome != "ghost"
        assert pubrun.get_current_run() is run
        assert (run.run_dir / "manifest.json").exists()
        assert "disk full" in (run.writer.last_error or "")
        run.stop()
        m = json.loads((run.run_dir / "manifest.json").read_text(encoding="utf-8"))
        assert m["status"]["outcome"] == "completed"

    def test_finalize_config_write_failure_still_writes_manifest(self, tmp_path, monkeypatch):
        from pubrun import writer as writer_mod
        run = pubrun.start(output_dir=str(tmp_path / "out"))

        def failing_config_write(self, out_dir, *, stage):
            raise OSError("config unwritable")

        monkeypatch.setattr(writer_mod.ArtifactWriter, "_write_config_if_needed", failing_config_write)
        run.stop()
        m = json.loads((run.run_dir / "manifest.json").read_text(encoding="utf-8"))
        assert m["status"]["outcome"] == "completed"
        assert (run.run_dir / "methods.md").exists()


# =============================================================================
# BUG-60a: EventStream close safety
# =============================================================================

class _FlushFailingFile:
    def __init__(self, exc):
        self.exc = exc
        self.closed = False

    def writelines(self, lines):
        pass

    def write(self, line):
        pass

    def flush(self):
        raise self.exc

    def close(self):
        self.closed = True


class TestEventStreamClose:
    def test_close_releases_descriptor_when_flush_raises_oserror(self, tmp_path):
        es = EventStream(tmp_path, config={"events": {}})
        fake = _FlushFailingFile(OSError("disk gone"))
        es._file = fake
        es.close()
        assert fake.closed is True
        assert es._file is None

    def test_close_releases_descriptor_when_flush_raises_baseexception(self, tmp_path):
        es = EventStream(tmp_path, config={"events": {}})
        fake = _FlushFailingFile(KeyboardInterrupt())
        es._file = fake
        with pytest.raises(KeyboardInterrupt):
            es.close()
        assert fake.closed is True
        assert es._file is None

    def test_migrate_releases_old_descriptor_when_flush_raises(self, tmp_path):
        es = EventStream(tmp_path, config={"events": {}})
        fake = _FlushFailingFile(OSError("disk gone"))
        es._file = fake
        new_dir = tmp_path / "moved"
        new_dir.mkdir()
        es.migrate_directory(new_dir)
        try:
            assert fake.closed is True
            assert es.stream_path == new_dir / "events.jsonl"
            assert es._file is not None
        finally:
            es.close()

    def test_concurrent_emit_and_close_is_safe(self, tmp_path):
        es = EventStream(tmp_path, config={"events": {"flush_interval_events": 5}})
        errors = []
        stop = threading.Event()

        def emitter():
            try:
                while not stop.is_set():
                    es.emit("annotation", name="x")
                    es.emit("resource_sample", payload={"n": 1})
            except Exception as exc:
                errors.append(exc)

        threads = [threading.Thread(target=emitter) for _ in range(4)]
        for t in threads:
            t.start()
        es.close()
        stop.set()
        for t in threads:
            t.join(timeout=10)
        assert errors == []
        assert es._file is None
        for line in (tmp_path / "events.jsonl").read_text(encoding="utf-8").splitlines():
            json.loads(line)


# =============================================================================
# BUG-07: auto-start under python -m
# =============================================================================

class TestPythonDashMBoot:
    def _make_pkg(self, root, name, init_body, main_body):
        pkg = root / name
        pkg.mkdir()
        (pkg / "__init__.py").write_text(textwrap.dedent(init_body), encoding="utf-8")
        (pkg / "__main__.py").write_text(textwrap.dedent(main_body), encoding="utf-8")

    def _run_module(self, tmp_path, *args):
        env = _child_env(tmp_path)
        env["PYTHONPATH"] = SRC_DIR + os.pathsep + str(tmp_path)
        return subprocess.run(
            [PYTHON, "-m", *args], cwd=str(tmp_path), env=env,
            capture_output=True, text=True, timeout=60,
        )

    def test_user_package_importing_pubrun_in_init_autostarts(self, tmp_path):
        self._make_pkg(
            tmp_path, "userpkg_init",
            "import pubrun\nRUN = pubrun.get_current_run()\n",
            "from userpkg_init import RUN\nprint('ACTIVE', RUN is not None)\n",
        )
        res = self._run_module(tmp_path, "userpkg_init")
        assert res.returncode == 0, res.stderr
        assert "ACTIVE True" in res.stdout
        assert len(list((tmp_path / "runs").glob("*/manifest.json"))) == 1

    def test_user_package_importing_pubrun_in_main_autostarts(self, tmp_path):
        self._make_pkg(
            tmp_path, "userpkg_main", "",
            "import pubrun\nprint('ACTIVE', pubrun.get_current_run() is not None)\n",
        )
        res = self._run_module(tmp_path, "userpkg_main")
        assert res.returncode == 0, res.stderr
        assert "ACTIVE True" in res.stdout

    def test_python_dash_m_pubrun_does_not_autostart(self, tmp_path):
        empty = tmp_path / "empty"
        empty.mkdir()
        res = self._run_module(tmp_path, "pubrun", "status", "--dir", str(empty))
        assert res.returncode == 0, res.stderr
        assert not (tmp_path / "runs").exists()
        assert list(empty.iterdir()) == []


# =============================================================================
# BUG-30: diff default ignores
# =============================================================================

class TestDiffIgnores:
    def _write_manifest(self, d, run_id, pid, extra):
        d.mkdir()
        manifest = {"schema_version": "1", "run": {"run_id": run_id}, "process": {"pid": pid}}
        manifest.update(extra)
        (d / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")

    def test_diff_default_uses_ignore_standard(self, tmp_path):
        a, b = tmp_path / "a", tmp_path / "b"
        self._write_manifest(a, "aaaa", 1, {"user": {"value": 1}})
        self._write_manifest(b, "bbbb", 2, {"user": {"value": 2}})
        delta = pubrun.diff(str(a), str(b))
        changed = set(delta["modified"]) | set(delta["added"]) | set(delta["removed"])
        assert not any(k.startswith("run.run_id") for k in changed)
        assert not any(k.startswith("process.pid") for k in changed)
        assert any(k.startswith("user.value") for k in changed)

    def test_explicit_ignores_override_default(self, tmp_path):
        a, b = tmp_path / "a", tmp_path / "b"
        self._write_manifest(a, "aaaa", 1, {})
        self._write_manifest(b, "bbbb", 2, {})
        delta = pubrun.diff(str(a), str(b), ignores=[])
        assert any(k.startswith("run.run_id") for k in delta["modified"])


# =============================================================================
# BUG-31: audit_run and tracked_run outcome classification
# =============================================================================

class TestDecoratorAndContextOutcomes:
    def _stop_outcomes(self, monkeypatch):
        outcomes = []
        original = tracker_mod.Run.stop

        def spy(self, outcome="completed"):
            outcomes.append(outcome)
            return original(self, outcome=outcome)

        monkeypatch.setattr(tracker_mod.Run, "stop", spy)
        return outcomes

    @pytest.mark.parametrize("exc, expected", [
        (KeyboardInterrupt(), "interrupted"),
        (SystemExit(0), "completed"),
        (SystemExit(None), "completed"),
        (SystemExit(2), "failed"),
        (SystemExit(True), "failed"),
        (ValueError("bad"), "failed"),
    ])
    def test_audit_run_stops_and_classifies(self, tmp_path, monkeypatch, exc, expected):
        outcomes = self._stop_outcomes(monkeypatch)

        @pubrun.audit_run(output_dir=str(tmp_path / "out"))
        def work():
            raise exc

        with pytest.raises(type(exc)):
            work()
        assert outcomes == [expected]
        assert pubrun.get_current_run() is None
        m = _only_manifest(tmp_path / "out")
        assert m["status"]["outcome"] == expected

    def test_audit_run_releases_ref_count_on_keyboard_interrupt(self, tmp_path):
        outer = pubrun.start(output_dir=str(tmp_path / "out"))
        try:
            @pubrun.audit_run()
            def work():
                raise KeyboardInterrupt

            with pytest.raises(KeyboardInterrupt):
                work()
            assert outer.ref_count == 1
        finally:
            outer.stop()

    def test_audit_run_success_completes(self, tmp_path):
        @pubrun.audit_run(output_dir=str(tmp_path / "out"))
        def work():
            return 5

        assert work() == 5
        assert _only_manifest(tmp_path / "out")["status"]["outcome"] == "completed"

    @pytest.mark.parametrize("exc, expected", [
        (KeyboardInterrupt(), "interrupted"),
        (SystemExit(0), "completed"),
        (SystemExit(4), "failed"),
        (RuntimeError("x"), "failed"),
    ])
    def test_tracked_run_classifies(self, tmp_path, exc, expected):
        with pytest.raises(type(exc)):
            with pubrun.tracked_run(output_dir=str(tmp_path / "out")):
                raise exc
        m = _only_manifest(tmp_path / "out")
        assert m["status"]["outcome"] == expected

    def test_tracked_run_records_system_exit_code(self, tmp_path):
        with pytest.raises(SystemExit):
            with pubrun.tracked_run(output_dir=str(tmp_path / "out")):
                raise SystemExit(4)
        m = _only_manifest(tmp_path / "out")
        assert m["signals"]["exit_code"] == 4


# =============================================================================
# BUG-06 and BUG-33: explicit subprocess wrappers and popen iteration
# =============================================================================

def _manual_records(run):
    return list(getattr(run, "manual_subprocess_records", []))


class TestExplicitSubprocessWrappers:
    def test_run_splits_string_command_and_redacts_argv(self, tmp_path):
        run = pubrun.start(output_dir=str(tmp_path / "out"))
        try:
            res = pubrun.subprocess.run("echo hello --password=hunter2", shell=True,
                                        capture_output=True, text=True)
            assert res.returncode == 0
            rec = _manual_records(run)[-1]
            assert rec["argv"][0] == "echo"
            assert rec["argv"][1] == "hello"
            assert "--password=[REDACTED]" in rec["argv"]
            assert "hunter2" not in json.dumps(rec)
        finally:
            run.stop()

    def test_run_called_process_error_records_returncode_and_redacts(self, tmp_path):
        run = pubrun.start(output_dir=str(tmp_path / "out"))
        try:
            with pytest.raises(subprocess.CalledProcessError):
                pubrun.subprocess.run(
                    [PYTHON, "-c", "import sys; sys.exit(6)", "--token", "s3cr3t"], check=True
                )
            rec = _manual_records(run)[-1]
            assert rec["exit_code"] == 6
            assert "CalledProcessError" in rec["error"]
            dumped = json.dumps(rec)
            assert "s3cr3t" not in dumped
        finally:
            run.stop()

    def test_popen_string_command_split_and_redacted(self, tmp_path):
        run = pubrun.start(output_dir=str(tmp_path / "out"))
        try:
            proc = pubrun.subprocess.Popen("echo hi --api-key=abc123", shell=True,
                                           stdout=subprocess.PIPE)
            proc.communicate()
            rec = _manual_records(run)[-1]
            assert rec["argv"][:2] == ["echo", "hi"]
            assert "abc123" not in json.dumps(rec)
            assert rec["exit_code"] == 0
        finally:
            run.stop()

    def test_popen_launch_failure_redacted(self, tmp_path):
        run = pubrun.start(output_dir=str(tmp_path / "out"))
        try:
            with pytest.raises(OSError):
                pubrun.subprocess.Popen(["/nonexistent/binary-xyz", "--password=hunter2"])
            rec = _manual_records(run)[-1]
            assert rec["exit_code"] is None
            assert "hunter2" not in json.dumps(rec)
        finally:
            run.stop()

    @pytest.mark.skipif(sys.platform == "win32", reason="POSIX shell command")
    def test_os_popen_wrapper_iterates_and_redacts(self, tmp_path):
        run = pubrun.start(output_dir=str(tmp_path / "out"))
        try:
            with pubrun.popen("printf 'a\\nb\\nc\\n'; true --password=hunter2") as pipe:
                first = next(pipe)
                rest = [line for line in pipe]
            assert first == "a\n"
            assert rest == ["b\n", "c\n"]
            rec = _manual_records(run)[-1]
            assert rec["argv"][0] == "printf"
            assert "hunter2" not in json.dumps(rec)
            assert rec["exit_code"] == 0
        finally:
            run.stop()

    @pytest.mark.skipif(sys.platform == "win32", reason="POSIX shell command")
    def test_os_popen_for_loop(self, tmp_path):
        run = pubrun.start(output_dir=str(tmp_path / "out"))
        try:
            pipe = pubrun.popen("printf 'x\\ny\\n'")
            lines = [line.strip() for line in pipe]
            pipe.close()
            assert lines == ["x", "y"]
        finally:
            run.stop()


# =============================================================================
# BUG-32: pubrun.print logging targets
# =============================================================================

class TestPubrunPrint:
    def _log(self, run):
        p = run.run_dir / "stdout.log"
        return p.read_text(encoding="utf-8") if p.exists() else ""

    def test_print_to_other_stream_is_not_logged(self, tmp_path, capsys):
        import io
        run = pubrun.start(output_dir=str(tmp_path / "out"))
        try:
            buf = io.StringIO()
            pubrun.print("to-buffer", file=buf)
            pubrun.print("to-stderr", file=sys.stderr)
            pubrun.print("to-stdout")
            assert buf.getvalue() == "to-buffer\n"
            log = self._log(run)
            assert "to-buffer" not in log
            assert "to-stderr" not in log
            assert "to-stdout" in log
        finally:
            run.stop()

    def test_print_inside_paused_is_not_logged(self, tmp_path, capsys):
        run = pubrun.start(output_dir=str(tmp_path / "out"))
        try:
            with pubrun.paused():
                pubrun.print("hidden-line")
            pubrun.print("visible-line")
            log = self._log(run)
            assert "hidden-line" not in log
            assert "visible-line" in log
        finally:
            run.stop()

    def test_print_with_active_console_tee_is_logged_once(self, tmp_path):
        # The child auto-starts at import, so console capture is configured
        # through the project config file rather than a later start() call.
        (tmp_path / ".pubrun.toml").write_text(
            '[console]\ncapture_mode = "basic"\nnon_tty_mode = "basic"\n', encoding="utf-8"
        )
        res = _run_script(tmp_path, """
            import pubrun
            run = pubrun.get_current_run()
            assert run.console_interceptor.stdout_tee is not None
            pubrun.print("dup-marker")
        """)
        assert res.returncode == 0, res.stderr
        assert res.stdout.count("dup-marker") == 1
        _only_manifest(tmp_path / "runs")
        run_dir = next((tmp_path / "runs").iterdir())
        log = (run_dir / "stdout.log").read_text(encoding="utf-8")
        assert log.count("dup-marker") == 1


# =============================================================================
# BUG-34: phase lazy binding, filename sanitization, profiler cleanup
# =============================================================================

class TestPhase:
    def test_phase_binds_run_lazily_in_enter(self, tmp_path):
        ph = pubrun.phase("late")
        assert pubrun.get_current_run() is None
        run = pubrun.start(output_dir=str(tmp_path / "out"))
        try:
            with ph:
                assert ph.run_tracker is run
        finally:
            run.stop()
        events = (run.run_dir / "events.jsonl").read_text(encoding="utf-8")
        assert '"phase_start"' in events and '"late"' in events

    def test_phase_profile_filename_is_sanitized(self, tmp_path):
        out = tmp_path / "out"
        run = pubrun.start(output_dir=str(out), capture={"profiling": {"enabled": True, "backend": "cprofile"}})
        try:
            with pubrun.phase("../../bad:name"):
                sum(range(100))
        finally:
            run.stop()
        profiles = list(run.run_dir.glob("profile-*.prof"))
        assert len(profiles) == 1
        assert profiles[0].parent == run.run_dir
        assert "/" not in profiles[0].name[len("profile-"):]
        assert ".." not in profiles[0].name
        assert ":" not in profiles[0].name
        assert not list(tmp_path.rglob("bad*name*.prof")) or all(
            p.parent == run.run_dir for p in tmp_path.rglob("*.prof")
        )
        events = [json.loads(line) for line in
                  (run.run_dir / "events.jsonl").read_text(encoding="utf-8").splitlines()]
        saved = [e for e in events if e["type"] == "profile_saved"]
        assert saved and saved[0]["name"] == "../../bad:name"
        assert saved[0]["payload"]["path"] == profiles[0].name

    def test_phase_name_with_no_safe_characters_falls_back(self, tmp_path):
        run = pubrun.start(output_dir=str(tmp_path / "out"),
                           capture={"profiling": {"enabled": True, "backend": "cprofile"}})
        try:
            with pubrun.phase("..."):
                pass
        finally:
            run.stop()
        assert [p.name for p in run.run_dir.glob("profile-*.prof")] == ["profile-phase.prof"]

    def test_yappi_released_when_run_stops_inside_phase(self, tmp_path, monkeypatch):
        import types
        state = {"running": False, "stops": 0}
        fake = types.ModuleType("yappi")

        def start():
            state["running"] = True

        def stop():
            state["running"] = False
            state["stops"] += 1

        fake.start = start
        fake.stop = stop
        fake.get_func_stats = lambda: types.SimpleNamespace(save=lambda *a, **k: None)
        fake.clear_stats = lambda: None
        monkeypatch.setitem(sys.modules, "yappi", fake)
        monkeypatch.setattr(pubrun.phase, "_yappi_active", False, raising=False)

        run = pubrun.start(output_dir=str(tmp_path / "out"),
                           capture={"profiling": {"enabled": True, "backend": "yappi"}})
        with pubrun.phase("inner"):
            assert state["running"] is True
            run.stop()
        assert state["running"] is False
        assert state["stops"] == 1
        assert pubrun.phase._yappi_active is False
