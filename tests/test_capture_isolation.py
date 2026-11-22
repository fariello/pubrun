"""Behavioral tests for per-engine capture isolation, narrow ghost-mode rollback,
independent finalization cleanup, bounded I/O warnings, lifecycle edge cases, and
import-mode enforcement (IPD ed0yds)."""

import atexit
import json
import logging
import os
import signal
import subprocess
import sys
import threading
import time
from pathlib import Path

import pytest

import pubrun
import pubrun.tracker as tracker_mod
import pubrun.writer as writer_mod
from pubrun import audit_run, get_current_run, start, stop, tracked_run
from pubrun.capture.console import ConsoleInterceptor
from pubrun.capture.resources import ResourceWatcher
from pubrun.capture.signals import SignalExitCapture
from pubrun.capture.subprocesses import SubprocessSpy
from pubrun.events import EventStream
from pubrun.tracker import MAX_CAPTURE_ERRORS, Run
from pubrun.writer import ArtifactWriter

_SCHEMA_PATH = Path(__file__).resolve().parents[1] / "schemas" / "manifest.schema.json"
_SRC_DIR = str(Path(__file__).resolve().parents[1] / "src")
PYTHON = sys.executable


def _worktree_env(**extra: str) -> dict:
    """Return an env dict with this worktree's src/ prepended to PYTHONPATH."""
    env = dict(os.environ)
    existing = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = f"{_SRC_DIR}{os.pathsep}{existing}" if existing else _SRC_DIR
    env.pop("PUBRUN_IMPORT_MODE", None)
    env.pop("PUBRUN_AUTO_START", None)
    env.update(extra)
    return env


def _validate_manifest_if_jsonschema(manifest: dict) -> None:
    try:
        import jsonschema
    except ImportError:
        return
    schema = json.loads(_SCHEMA_PATH.read_text(encoding="utf-8"))
    jsonschema.validate(manifest, schema)


# =============================================================================
# 1. Per-engine fault injection & self-caught failed returns
# =============================================================================

_ALL_ENGINES = [
    "invocation",
    "git",
    "process",
    "python",
    "packages",
    "environment",
    "hardware",
    "host",
    "filesystem",
    "subprocesses",
    "console",
    "events",
    "resources",
    "signals",
]


@pytest.mark.parametrize("engine", _ALL_ENGINES)
def test_per_engine_fault_injection_isolates_failure_and_redacts_secrets(
    tmp_path, monkeypatch, caplog, engine
):
    """Injecting a secret-bearing exception into any individual capture engine
    must keep the run active, preserve unrelated healthy sections, redact secrets,
    record a structured capture-error, mark capture.capture_state partial, and
    preserve the host function's return value."""
    monkeypatch.setattr("pathlib.Path.cwd", lambda: tmp_path)
    fake_token = "sk-" + "test000011112222"
    err_msg = f"boom in {engine} --api-key={fake_token}\nsecond line"

    def _raise(*args, **kwargs):
        raise RuntimeError(err_msg)

    overrides = {
        "console": {"capture_mode": "off"},
        "events": {"enabled": False},
        "capture": {
            "subprocesses": {"enabled": False},
            "resources": {"depth": "off"},
            "signals": {"enabled": True},
        },
    }

    if engine == "invocation":
        monkeypatch.setattr(tracker_mod, "get_invocation", _raise)
    elif engine == "git":
        monkeypatch.setattr(tracker_mod, "get_git", _raise)
    elif engine == "process":
        monkeypatch.setattr(tracker_mod, "get_process_info", _raise)
    elif engine == "python":
        monkeypatch.setattr(tracker_mod, "get_python_runtime", _raise)
    elif engine == "packages":
        monkeypatch.setattr(tracker_mod, "get_packages", _raise)
    elif engine == "environment":
        monkeypatch.setattr(tracker_mod, "get_environment", _raise)
    elif engine == "hardware":
        monkeypatch.setattr(tracker_mod, "get_hardware", _raise)
    elif engine == "host":
        monkeypatch.setattr(tracker_mod, "get_host", _raise)
    elif engine == "filesystem":
        import pubrun.capture.filesystem as fs_mod
        monkeypatch.setattr(fs_mod, "get_filesystem", _raise)
    elif engine == "subprocesses":
        overrides["capture"]["subprocesses"]["enabled"] = True
        monkeypatch.setattr(SubprocessSpy, "install", classmethod(lambda cls, *a, **k: _raise()))
    elif engine == "console":
        overrides["console"]["capture_mode"] = "standard"
        monkeypatch.setattr(ConsoleInterceptor, "start", _raise)
    elif engine == "events":
        overrides["events"]["enabled"] = True
        monkeypatch.setattr(tracker_mod, "EventStream", _raise)
    elif engine == "resources":
        overrides["capture"]["resources"]["depth"] = "basic"
        monkeypatch.setattr(ResourceWatcher, "start", _raise)
    elif engine == "signals":
        overrides["capture"]["signals"]["enabled"] = True
        monkeypatch.setattr(SignalExitCapture, "install", _raise)

    with caplog.at_level(logging.WARNING, logger="pubrun"):
        @audit_run(**overrides)
        def host_work():
            cur = get_current_run()
            assert cur is not None
            assert cur.is_active is True
            assert cur._outcome == "running"
            if cur._hardware_future_done is not None:
                cur._hardware_future_done.wait(timeout=3.0)
            return ("host-ok", cur.run_dir)

        result, run_dir = host_work()

    assert result == "host-ok"
    assert get_current_run() is None

    manifest = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
    _validate_manifest_if_jsonschema(manifest)

    # Host script outcome remains completed; capture is honestly partial.
    assert manifest["status"]["outcome"] == "completed"
    assert manifest["capture"]["capture_state"]["status"] == "partial"
    assert engine in manifest["capture"]["capture_state"]["detail"]

    # Unrelated sections survive as complete.
    if engine != "process":
        assert manifest["process"]["capture_state"]["status"] == "complete"
    if engine != "python":
        assert manifest["python"]["capture_state"]["status"] == "complete"
    if engine == "hardware":
        assert manifest["host"]["capture_state"]["status"] == "complete"
        assert manifest["filesystem"]["capture_state"]["status"] == "complete"
    if engine == "host":
        assert manifest["hardware"]["capture_state"]["status"] == "complete"
        assert manifest["filesystem"]["capture_state"]["status"] == "complete"
    if engine == "filesystem":
        assert manifest["hardware"]["capture_state"]["status"] == "complete"
        assert manifest["host"]["capture_state"]["status"] == "complete"

    # Section-level capture_state for sections present in manifest.
    if engine not in ("subprocesses", "events"):
        cs = manifest[engine]["capture_state"]
        assert cs["status"] == "failed"
        detail = cs.get("detail", "")
        assert detail
        assert "\n" not in detail
        assert len(detail) <= 240
        assert fake_token not in detail

    # Structured capture-error entry in errors.records.
    matching = [
        rec
        for rec in manifest["errors"]["records"]
        if rec.get("kind") == "capture-error" and rec.get("section") == engine
    ]
    assert len(matching) >= 1
    rec = matching[0]
    assert rec["stage"] == "bootstrap"
    assert rec["type"] == "RuntimeError"
    assert rec["traceback"] is None
    assert fake_token not in (rec["message"] or "")
    assert "\n" not in (rec["message"] or "")
    assert len(rec["message"] or "") <= 240

    # Emitted warnings also redact the secret and remain bounded.
    assert fake_token not in caplog.text


def test_additional_bootstrap_edge_failures_isolated(tmp_path, monkeypatch):
    """Verify resolve_console_mode(), ConsoleInterceptor.start() returning False,
    set_poll_timeout(), _hardware_thread.start(), and EventStream open failure
    are all isolated without promoting to ghost mode."""
    monkeypatch.setattr("pathlib.Path.cwd", lambda: tmp_path)

    # 1. resolve_console_mode raising
    import pubrun.capture.console as console_mod
    monkeypatch.setattr(
        console_mod,
        "resolve_console_mode",
        lambda *a, **k: (_ for _ in ()).throw(RuntimeError("bad console mode")),
    )
    run = Run(overrides={"console": {"capture_mode": "standard"}})
    assert run.is_active is True
    assert run.console_data["capture_state"]["status"] == "failed"
    run.stop()
    manifest = json.loads((run.run_dir / "manifest.json").read_text(encoding="utf-8"))
    _validate_manifest_if_jsonschema(manifest)
    assert manifest["console"]["capture_state"]["status"] == "failed"
    assert manifest["capture"]["capture_state"]["status"] == "partial"

    # 2. ConsoleInterceptor.start() returning False (self-rolled-back open error)
    monkeypatch.undo()
    monkeypatch.setattr("pathlib.Path.cwd", lambda: tmp_path)
    def _fail_console_start(self):
        self._failed_detail = "PermissionError: cannot open stdout.log"
        return False
    monkeypatch.setattr(ConsoleInterceptor, "start", _fail_console_start)
    run2 = Run(overrides={"console": {"capture_mode": "standard"}})
    assert run2.is_active is True
    assert run2.console_interceptor is None
    assert run2.console_data["capture_state"]["status"] == "failed"
    run2.stop()
    manifest2 = json.loads((run2.run_dir / "manifest.json").read_text(encoding="utf-8"))
    _validate_manifest_if_jsonschema(manifest2)
    assert manifest2["console"]["capture_state"]["status"] == "failed"
    assert manifest2["capture"]["capture_state"]["status"] == "partial"
    assert any(r.get("section") == "console" for r in manifest2["errors"]["records"])

    # 3. set_poll_timeout raising
    monkeypatch.undo()
    monkeypatch.setattr("pathlib.Path.cwd", lambda: tmp_path)
    import pubrun.capture.resources as res_mod
    monkeypatch.setattr(
        res_mod,
        "set_poll_timeout",
        lambda *a, **k: (_ for _ in ()).throw(RuntimeError("bad poll timeout")),
    )
    run3 = Run(overrides={"capture": {"resources": {"depth": "basic"}}})
    assert run3.is_active is True
    assert run3.resource_watcher is None
    run3.stop()
    manifest3 = json.loads((run3.run_dir / "manifest.json").read_text(encoding="utf-8"))
    _validate_manifest_if_jsonschema(manifest3)
    assert manifest3["resources"]["capture_state"]["status"] == "failed"
    assert manifest3["capture"]["capture_state"]["status"] == "partial"

    # 4. EventStream._file is None after open failure
    monkeypatch.undo()
    monkeypatch.setattr("pathlib.Path.cwd", lambda: tmp_path)
    import builtins
    real_open = builtins.open
    def _deny_events(path, *a, **kw):
        if "events.jsonl" in str(path):
            raise PermissionError("events denied")
        return real_open(path, *a, **kw)
    monkeypatch.setattr(builtins, "open", _deny_events)
    run4 = Run(overrides={"events": {"enabled": True}})
    assert run4.is_active is True
    assert run4.event_stream is None
    run4.stop()
    manifest4 = json.loads((run4.run_dir / "manifest.json").read_text(encoding="utf-8"))
    _validate_manifest_if_jsonschema(manifest4)
    assert manifest4["capture"]["capture_state"]["status"] == "partial"
    assert any(r.get("section") == "events" for r in manifest4["errors"]["records"])

    # 5. _hardware_thread.start() raising -> must set _hardware_future_done immediately
    monkeypatch.undo()
    monkeypatch.setattr("pathlib.Path.cwd", lambda: tmp_path)
    orig_thread_start = threading.Thread.start
    def _fail_hw_thread_start(self):
        if self.name == "pubrun-hw":
            raise RuntimeError("can't start new thread")
        return orig_thread_start(self)
    monkeypatch.setattr(threading.Thread, "start", _fail_hw_thread_start)
    run5 = Run()
    assert run5.is_active is True
    assert run5._hardware_future_done.is_set() is True
    t0 = time.monotonic()
    run5.stop()
    elapsed = time.monotonic() - t0
    assert elapsed < 1.5, f"stop() waited on unstarted hardware thread ({elapsed:.2f}s)"
    manifest5 = json.loads((run5.run_dir / "manifest.json").read_text(encoding="utf-8"))
    _validate_manifest_if_jsonschema(manifest5)
    assert manifest5["hardware"]["capture_state"]["status"] == "failed"
    assert manifest5["host"]["capture_state"]["status"] == "failed"
    assert manifest5["filesystem"]["capture_state"]["status"] == "failed"
    assert manifest5["capture"]["capture_state"]["status"] == "partial"


def test_self_caught_failed_engine_return_marks_capture_partial(tmp_path, monkeypatch):
    """An engine returning capture_state.status == 'failed' without raising must
    still cause capture.capture_state.status to be 'partial'."""
    monkeypatch.setattr("pathlib.Path.cwd", lambda: tmp_path)
    monkeypatch.setattr(
        tracker_mod,
        "get_git",
        lambda cfg: {"capture_state": {"status": "failed", "detail": "git binary corrupt"}},
    )
    run = Run()
    run.stop()
    manifest = json.loads((run.run_dir / "manifest.json").read_text(encoding="utf-8"))
    _validate_manifest_if_jsonschema(manifest)
    assert manifest["git"]["capture_state"]["status"] == "failed"
    assert manifest["capture"]["capture_state"]["status"] == "partial"
    assert "git" in manifest["capture"]["capture_state"]["detail"]


def test_capture_error_cap_truncates_and_marks_errors_partial(tmp_path, monkeypatch):
    """Recording more than MAX_CAPTURE_ERRORS entries caps errors.records and
    sets errors.capture_state to partial with omitted count."""
    monkeypatch.setattr("pathlib.Path.cwd", lambda: tmp_path)
    run = Run()
    for i in range(MAX_CAPTURE_ERRORS + 7):
        run._record_capture_error(f"sec_{i}", "runtime", RuntimeError(f"err {i}"), warn=False)
    manifest = run.to_manifest_dict()
    run.stop()
    _validate_manifest_if_jsonschema(manifest)
    assert len(manifest["errors"]["records"]) == MAX_CAPTURE_ERRORS
    assert manifest["errors"]["capture_state"]["status"] == "partial"
    assert "7 additional capture error(s) omitted" in manifest["errors"]["capture_state"]["detail"]


# =============================================================================
# 2. Startup output failure AFTER hooks installed -> transactional rollback
# =============================================================================

def test_startup_output_failure_rolls_back_all_owned_hooks_and_enters_ghost_mode(
    tmp_path, monkeypatch, capsys
):
    """When write_startup_manifest() fails after hooks are installed, Run must
    latch _finalized under _run_lock, roll back SubprocessSpy, ConsoleInterceptor,
    ResourceWatcher, EventStream, SignalExitCapture, .pubrun.lock, and atexit,
    emit one bounded redacted stderr warning, and publish _active_run as ghost."""
    monkeypatch.setattr("pathlib.Path.cwd", lambda: tmp_path)

    orig_stdout = sys.stdout
    orig_stderr = sys.stderr
    orig_popen_init = subprocess.Popen.__init__
    orig_popen_wait = subprocess.Popen.wait
    orig_os_system = os.system
    orig_excepthook = sys.excepthook
    orig_sigint = signal.getsignal(signal.SIGINT)

    fake_token = "sk-" + "ghost000011112222"
    created_watchers = []
    created_streams = []
    orig_rw_init = ResourceWatcher.__init__
    orig_es_init = EventStream.__init__

    def _track_rw(self, *args, **kwargs):
        orig_rw_init(self, *args, **kwargs)
        created_watchers.append(self)

    def _track_es(self, *args, **kwargs):
        orig_es_init(self, *args, **kwargs)
        created_streams.append(self)

    monkeypatch.setattr(ResourceWatcher, "__init__", _track_rw)
    monkeypatch.setattr(EventStream, "__init__", _track_es)

    # Fail _atomic_json_write at startup with a secret-bearing PermissionError.
    def _fail_atomic(path, data):
        raise PermissionError(f"read-only mount token={fake_token}\ntraceback-should-not-appear")

    monkeypatch.setattr(writer_mod, "_atomic_json_write", _fail_atomic)

    atexit_registered = []
    orig_atexit_register = atexit.register
    monkeypatch.setattr(atexit, "register", lambda fn, *a, **k: atexit_registered.append(fn))

    try:
        run = start(
            console={"capture_mode": "standard"},
            events={"enabled": True},
            capture={
                "subprocesses": {"enabled": True},
                "resources": {"depth": "basic", "sample_interval_seconds": 0.1},
                "signals": {"enabled": True},
            },
        )
    finally:
        monkeypatch.setattr(atexit, "register", orig_atexit_register)

    # Entered ghost mode cleanly
    assert run._outcome == "ghost"
    assert run.is_active is False
    assert run._finalized is True
    assert run.writer is None
    assert get_current_run() is run

    # Every owned hook/worker/handle/lock was rolled back
    assert SubprocessSpy._installed is False
    assert subprocess.Popen.__init__ is orig_popen_init
    assert subprocess.Popen.wait is orig_popen_wait
    assert os.system is orig_os_system
    assert sys.stdout is orig_stdout
    assert sys.stderr is orig_stderr
    assert sys.excepthook is orig_excepthook
    assert signal.getsignal(signal.SIGINT) is orig_sigint
    assert not (run.run_dir / Run.LOCK_FILENAME).exists()
    assert atexit_registered == []

    assert len(created_watchers) == 1
    assert not created_watchers[0].is_alive()
    assert len(created_streams) == 1
    assert created_streams[0]._file is None

    # Bounded redacted warning on stderr (single warning, no secret, no traceback)
    captured = capsys.readouterr()
    assert "Ghost Mode" in captured.err
    assert fake_token not in captured.err
    assert "Traceback" not in captured.err

    # Nested start() while ghost run is active skips _merge_and_migrate and increments ref_count
    migrate_calls = []
    monkeypatch.setattr(run, "_merge_and_migrate", lambda ov: migrate_calls.append(ov))
    nested = start(core={"output_dir": str(tmp_path / "other")})
    assert nested is run
    assert run.ref_count == 2
    assert migrate_calls == []

    # Stopping nested then outer preserves ghost outcome and clears _active_run
    nested.stop(outcome="completed")
    assert get_current_run() is run
    run.stop(outcome="completed")
    assert run._outcome == "ghost"
    assert get_current_run() is None


# =============================================================================
# 3. Mid-run output loss / read-only storage & bounded warnings
# =============================================================================

def test_event_stream_write_failure_detaches_and_warns_once_outside_lock(
    tmp_path, caplog
):
    """A broken EventStream handle closes and detaches _file under _lock, emits
    at most one bounded redacted warning OUTSIDE _lock (no deadlock if a logging
    handler re-enters emit()), and does not retry broken writes."""
    fake_token = "sk-" + "event000011112222"
    write_attempts = {"count": 0}

    class BrokenFile:
        def write(self, s):
            write_attempts["count"] += 1
            raise OSError(f"ENOSPC api_key={fake_token}")

        def writelines(self, lines):
            write_attempts["count"] += 1
            raise OSError(f"ENOSPC api_key={fake_token}")

        def flush(self):
            raise OSError("ENOSPC")

        def close(self):
            pass

    stream = EventStream(tmp_path, config={"events": {"enabled": True}})
    real_f = stream._file
    stream._file = BrokenFile()
    real_f.close()

    # Attach a logging handler that re-enters stream.emit() to prove the warning
    # is emitted OUTSIDE stream._lock (would deadlock otherwise).
    reentered = []

    class ReentrantHandler(logging.Handler):
        def emit(self, record):
            reentered.append(record.getMessage())
            stream.emit("annotation", name="from_log_handler")

    pubrun_logger = logging.getLogger("pubrun")
    handler = ReentrantHandler(level=logging.WARNING)
    pubrun_logger.addHandler(handler)
    try:
        with caplog.at_level(logging.WARNING, logger="pubrun"):
            for i in range(10):
                stream.emit("annotation", name=f"ev_{i}")
    finally:
        pubrun_logger.removeHandler(handler)

    assert stream._file is None
    assert stream._write_failed is True
    assert stream._last_error is not None
    assert fake_token not in stream._last_error
    # Only the first emit attempted a syscall; subsequent calls returned immediately.
    assert write_attempts["count"] == 1
    # Exactly one warning emitted, and handler re-entry succeeded without deadlock.
    event_warnings = [r for r in caplog.records if "event stream write failed" in r.message]
    assert len(event_warnings) == 1
    assert fake_token not in event_warnings[0].message
    assert len(reentered) >= 1


def test_mid_run_output_loss_bounds_writer_warnings_and_still_restores_hooks(
    tmp_path, monkeypatch, caplog
):
    """If storage becomes unwritable mid-run, write_artifacts() returns False with
    at most one bounded redacted warning while stop() still restores all hooks and
    clears _active_run."""
    monkeypatch.setattr("pathlib.Path.cwd", lambda: tmp_path)
    orig_stdout = sys.stdout
    orig_popen_init = subprocess.Popen.__init__

    run = start(
        console={"capture_mode": "standard"},
        events={"enabled": True},
        capture={
            "subprocesses": {"enabled": True},
            "resources": {"depth": "basic", "sample_interval_seconds": 0.1},
            "signals": {"enabled": True},
        },
    )
    assert run.is_active is True
    assert SubprocessSpy._installed is True

    fake_token = "sk-" + "writer000011112222"

    def _fail_write(path, data):
        raise PermissionError(f"disk read-only password={fake_token}")

    monkeypatch.setattr(writer_mod, "_atomic_json_write", _fail_write)

    with caplog.at_level(logging.WARNING, logger="pubrun"):
        run.stop(outcome="completed")
        # Calling write_artifacts again must not spam another warning.
        ok_again = run.writer.write_artifacts()

    assert ok_again is False
    assert run.writer.last_error is not None
    assert fake_token not in run.writer.last_error
    assert SubprocessSpy._installed is False
    assert subprocess.Popen.__init__ is orig_popen_init
    assert sys.stdout is orig_stdout
    assert get_current_run() is None

    writer_warnings = [
        r for r in caplog.records
        if "failed to write" in r.message
    ]
    assert len(writer_warnings) == 1
    assert "failed to write execution artifacts" in writer_warnings[0].message
    assert fake_token not in writer_warnings[0].message


def test_artifact_writer_nonfatal_methods_and_config_failure(tmp_path, monkeypatch, caplog):
    """methods.{md,tex} failure is non-fatal (returns True), and config.resolved.json
    failure still writes manifest.json and returns True with one bounded warning."""

    class _DummyRun:
        def __init__(self, run_dir, config):
            self.run_dir = run_dir
            self.config = config
            self._finalized = False
            self.finalize_called = 0
            self.to_manifest_called = 0

        def _finalize_state(self):
            self._finalized = True
            self.finalize_called += 1

        def to_manifest_dict(self):
            self.to_manifest_called += 1
            return {"run_id": "dummy_id"}

    # 1. methods generation failure is non-fatal
    run_dir_1 = tmp_path / "r1"
    run1 = _DummyRun(run_dir_1, {"methods": {"format": "markdown"}})
    import pubrun.report.methods as methods_mod
    monkeypatch.setattr(
        methods_mod,
        "generate_report",
        lambda *a, **k: (_ for _ in ()).throw(RuntimeError("methods boom")),
    )
    w1 = ArtifactWriter(run1)
    assert w1.write_artifacts() is True
    assert (run_dir_1 / "manifest.json").exists()
    assert w1.last_error is None
    # Duplicate call on finalized run returns True without rewriting
    assert w1.write_artifacts() is True
    assert run1.to_manifest_called == 1

    # 2. config.resolved.json fails while manifest.json succeeds
    monkeypatch.undo()
    run_dir_2 = tmp_path / "r2"
    run2 = _DummyRun(run_dir_2, {"methods": {"format": "markdown"}})
    orig_atomic = writer_mod._atomic_json_write

    def _fail_config_only(path, data):
        if Path(path).name == "config.resolved.json":
            raise PermissionError("config.resolved.json locked")
        return orig_atomic(path, data)

    monkeypatch.setattr(writer_mod, "_atomic_json_write", _fail_config_only)
    w2 = ArtifactWriter(run2)
    with caplog.at_level(logging.WARNING, logger="pubrun"):
        assert w2.write_artifacts() is True
    assert (run_dir_2 / "manifest.json").exists()
    assert w2.last_error is not None
    assert "PermissionError" in w2.last_error
    cfg_warns = [r for r in caplog.records if "config.resolved.json" in r.message]
    assert len(cfg_warns) == 1


# =============================================================================
# 4. Second cleanup failure and SubprocessSpy.finalize_all() separation
# =============================================================================

def test_independent_finalization_survives_multiple_cleanup_failures(
    tmp_path, monkeypatch
):
    """When SubprocessSpy.finalize_all(), ConsoleInterceptor.stop(), and
    signal_capture.get_records() all raise during stop(), SubprocessSpy.uninstall(),
    ResourceWatcher.stop(), EventStream.close(), profiler.disable(),
    SignalExitCapture.uninstall(), lock removal, _active_run reset, and manifest
    writing must all still run cleanly."""
    monkeypatch.setattr("pathlib.Path.cwd", lambda: tmp_path)
    orig_popen_init = subprocess.Popen.__init__
    orig_excepthook = sys.excepthook

    run = start(
        console={"capture_mode": "standard"},
        events={"enabled": True},
        capture={
            "subprocesses": {"enabled": True},
            "resources": {"depth": "basic", "sample_interval_seconds": 0.1},
            "signals": {"enabled": True},
        },
    )
    assert SubprocessSpy._installed is True
    assert run.console_interceptor is not None
    assert run.resource_watcher is not None
    assert run.event_stream is not None
    assert run.signal_capture is not None

    # Attach a fake active profiler to verify orphaned profiler cleanup still runs.
    profiler_disabled = []

    class FakeProfiler:
        def disable(self):
            profiler_disabled.append(True)

    run._active_profilers.append(FakeProfiler())

    # Inject multiple cleanup failures:
    # (a) SubprocessSpy.finalize_all raises -> uninstall MUST still run!
    monkeypatch.setattr(
        SubprocessSpy,
        "finalize_all",
        classmethod(lambda cls: (_ for _ in ()).throw(RuntimeError("finalize_all boom"))),
    )
    # (b) ConsoleInterceptor.stop raises -> console_data MUST become failed (not pending)!
    #     Save original stop to restore streams in finally so pytest stdout stays clean.
    orig_console_stop = run.console_interceptor.stop
    monkeypatch.setattr(
        run.console_interceptor,
        "stop",
        lambda: (_ for _ in ()).throw(RuntimeError("console stop boom")),
    )
    # (c) signal_capture.get_records raises -> signal_capture.uninstall MUST still run!
    monkeypatch.setattr(
        run.signal_capture,
        "get_records",
        lambda: (_ for _ in ()).throw(RuntimeError("signal records boom")),
    )

    try:
        run.stop(outcome="completed")
    finally:
        # Cleanly restore the console interceptor whose stop() we intentionally broke.
        orig_console_stop()

    # SubprocessSpy.uninstall STILL ran despite finalize_all() raising!
    assert SubprocessSpy._installed is False
    assert subprocess.Popen.__init__ is orig_popen_init
    # ResourceWatcher, EventStream, profiler, SignalExitCapture, lock file, and _active_run all cleaned up!
    assert not run.resource_watcher.is_alive()
    assert run.event_stream._file is None
    assert profiler_disabled == [True]
    assert run._active_profilers == []
    assert sys.excepthook is orig_excepthook
    assert not (run.run_dir / Run.LOCK_FILENAME).exists()
    assert get_current_run() is None

    # Final manifest was still written, schema-valid, with all finalization errors recorded
    manifest = json.loads((run.run_dir / "manifest.json").read_text(encoding="utf-8"))
    _validate_manifest_if_jsonschema(manifest)
    assert manifest["console"]["capture_state"]["status"] == "failed"
    assert manifest["signals"]["capture_state"]["status"] == "failed"
    assert manifest["capture"]["capture_state"]["status"] == "partial"

    fin_sections = {
        rec["section"]
        for rec in manifest["errors"]["records"]
        if rec.get("kind") == "capture-error" and rec.get("stage") == "finalization"
    }
    assert {"subprocesses", "console", "signals"}.issubset(fin_sections)


def test_uninstall_failure_still_cleans_later_engines(tmp_path, monkeypatch):
    """If SubprocessSpy.uninstall() AND ConsoleInterceptor.stop() both raise,
    later cleanup steps still complete."""
    monkeypatch.setattr("pathlib.Path.cwd", lambda: tmp_path)
    orig_excepthook = sys.excepthook

    run = start(
        console={"capture_mode": "standard"},
        events={"enabled": True},
        capture={
            "subprocesses": {"enabled": True},
            "resources": {"depth": "basic", "sample_interval_seconds": 0.1},
            "signals": {"enabled": True},
        },
    )
    orig_spy_uninstall = SubprocessSpy.uninstall
    orig_console_stop = run.console_interceptor.stop

    monkeypatch.setattr(
        SubprocessSpy,
        "uninstall",
        classmethod(lambda cls, **kw: (_ for _ in ()).throw(RuntimeError("uninstall boom"))),
    )
    monkeypatch.setattr(
        run.console_interceptor,
        "stop",
        lambda: (_ for _ in ()).throw(RuntimeError("console stop boom")),
    )

    try:
        run.stop(outcome="completed")
    finally:
        orig_console_stop()
        orig_spy_uninstall()

    assert not run.resource_watcher.is_alive()
    assert run.event_stream._file is None
    assert sys.excepthook is orig_excepthook
    assert not (run.run_dir / Run.LOCK_FILENAME).exists()
    assert get_current_run() is None
    assert (run.run_dir / "manifest.json").exists()


# =============================================================================
# 5. Lifecycle edge cases: nested, multi-stop, atexit, slow hw worker
# =============================================================================

def test_nested_runs_tracked_run_audit_run_and_multi_stop(tmp_path, monkeypatch):
    """Nested start()/stop(), tracked_run, audit_run, bad merge overrides, and
    triple stop() preserve ref counts, outcomes, and finalized manifests."""
    monkeypatch.setattr("pathlib.Path.cwd", lambda: tmp_path)

    outer = start()
    inner = start()
    assert inner is outer
    assert outer.ref_count == 2

    # Bad overrides in _merge_and_migrate must not crash
    monkeypatch.setattr(
        tracker_mod,
        "resolve_config",
        lambda *a, **k: (_ for _ in ()).throw(ValueError("bad override")),
    )
    outer._merge_and_migrate({"core": {"output_dir": str(tmp_path / "x")}})
    monkeypatch.undo()
    monkeypatch.setattr("pathlib.Path.cwd", lambda: tmp_path)

    inner.stop()
    assert outer.is_active is True
    assert get_current_run() is outer

    outer.stop()
    assert outer.is_active is False
    assert get_current_run() is None

    manifest_path = outer.run_dir / "manifest.json"
    first_text = manifest_path.read_text(encoding="utf-8")

    # Double and triple stop are no-ops and never rewrite the finalized manifest.
    outer.stop(outcome="failed")
    outer.stop(outcome="completed")
    assert outer._outcome == "completed"
    assert manifest_path.read_text(encoding="utf-8") == first_text

    # tracked_run and audit_run with an isolated engine failure
    monkeypatch.setattr(
        tracker_mod,
        "get_packages",
        lambda cfg: (_ for _ in ()).throw(RuntimeError("pkg failure")),
    )
    with tracked_run() as tr:
        assert tr.run_tracker is not None
        assert tr.run_tracker.is_active is True
    assert get_current_run() is None
    tr_manifest = json.loads((tr.run_tracker.run_dir / "manifest.json").read_text(encoding="utf-8"))
    assert tr_manifest["status"]["outcome"] == "completed"
    assert tr_manifest["packages"]["capture_state"]["status"] == "failed"

    with pytest.raises(KeyError):
        @audit_run
        def failing_fn():
            raise KeyError("host error")
        failing_fn()
    assert get_current_run() is None


def test_atexit_auto_finalization_with_isolated_engine_failure(tmp_path):
    """A real subprocess that suffers an engine failure and exits without
    calling stop() still exits 0 and writes a valid partial manifest via atexit."""
    script = f"""
import os, sys, json
os.chdir({str(tmp_path)!r})
import pubrun.noauto as pubrun
import pubrun.tracker as tracker_mod
tracker_mod.get_git = lambda cfg: (_ for _ in ()).throw(RuntimeError("git failed at startup"))
run = pubrun.start()
print(json.dumps({{"run_dir": str(run.run_dir)}}))
# Deliberately do NOT call pubrun.stop(); rely on atexit finalization.
"""
    res = subprocess.run(
        [PYTHON, "-c", script],
        capture_output=True,
        text=True,
        timeout=20,
        env=_worktree_env(),
    )
    assert res.returncode == 0, f"stderr: {res.stderr}"
    info = json.loads(res.stdout.strip().splitlines()[-1])
    run_dir = Path(info["run_dir"])
    manifest_path = run_dir / "manifest.json"
    assert manifest_path.exists()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    _validate_manifest_if_jsonschema(manifest)
    assert manifest["status"]["outcome"] == "completed"
    assert manifest["git"]["capture_state"]["status"] == "failed"
    assert manifest["capture"]["capture_state"]["status"] == "partial"


def test_slow_background_hardware_worker_never_overwrites_finalized_manifest(
    tmp_path, monkeypatch
):
    """If the background hardware worker finishes after stop() has finalized the
    run, it must neither overwrite manifest.json nor mutate finalized errors."""
    monkeypatch.setattr("pathlib.Path.cwd", lambda: tmp_path)

    hw_entered = threading.Event()
    release_hw = threading.Event()

    def _slow_hw(config):
        hw_entered.set()
        release_hw.wait(timeout=5.0)
        raise RuntimeError("late hardware failure after stop")

    monkeypatch.setattr(tracker_mod, "get_hardware", _slow_hw)

    # Shorten _finalize_state's wait by stubbing _hardware_future_done.wait after init
    run = start()
    assert hw_entered.wait(timeout=2.0)

    # Make wait() return immediately to simulate hardware outlasting the 2s wait.
    monkeypatch.setattr(run._hardware_future_done, "wait", lambda timeout=None: False)
    run.stop(outcome="completed")

    manifest_path = run.run_dir / "manifest.json"
    finalized_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert finalized_manifest["status"]["outcome"] == "completed"
    assert finalized_manifest["hardware"]["capture_state"]["status"] == "pending"
    errors_before = list(run._capture_errors)

    # Release the slow worker now that the run is finalized.
    release_hw.set()
    run._hardware_thread.join(timeout=3.0)

    after_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert after_manifest == finalized_manifest
    assert run._capture_errors == errors_before
    assert run.hardware_data["capture_state"]["status"] == "pending"


# =============================================================================
# 6. All six import modes under engine failure and rollback
# =============================================================================

@pytest.mark.parametrize(
    "mode,expect_auto,expect_spy,expect_console_tee,expect_signals",
    [
        ("auto", True, True, False, True),
        ("full", True, True, True, True),
        ("noauto", False, True, False, True),
        ("nopatch", True, False, False, True),
        ("noconsole", True, True, False, True),
        ("minimal", False, False, False, False),
    ],
)
def test_all_six_import_modes_under_engine_failure_and_nested_merge(
    tmp_path, mode, expect_auto, expect_spy, expect_console_tee, expect_signals
):
    """Across all six import modes, an engine failure degrades only that section,
    mode hook permissions hold, and nested start() in nopatch/minimal never
    installs SubprocessSpy."""
    script = f"""
import os, sys, json
os.chdir({str(tmp_path)!r})
import pubrun.{mode} as pubrun
import pubrun.tracker as tracker_mod
from pubrun.capture.subprocesses import SubprocessSpy

auto_active = pubrun.get_current_run() is not None
if auto_active:
    pubrun.stop()

# Inject a git capture failure and start a fresh run under this import mode.
tracker_mod.get_git = lambda cfg: (_ for _ in ()).throw(RuntimeError("git boom"))
run = pubrun.start(capture={{"subprocesses": {{"enabled": True}}}})

# Nested start requesting subprocesses enabled must still obey import mode!
nested = pubrun.start(capture={{"subprocesses": {{"enabled": True}}}})
spy_installed = SubprocessSpy._installed
console_tee = type(sys.stdout).__name__ == 'TqdmSafeTee'
has_signals = run.signal_capture is not None
nested.stop()
run.stop()

manifest = json.loads((run.run_dir / "manifest.json").read_text(encoding="utf-8"))
print(json.dumps({{
    "auto_active": auto_active,
    "spy_installed": spy_installed,
    "console_tee": console_tee,
    "has_signals": has_signals,
    "outcome": manifest["status"]["outcome"],
    "git_status": manifest["git"]["capture_state"]["status"],
    "capture_status": manifest["capture"]["capture_state"]["status"],
    "spy_after_stop": SubprocessSpy._installed,
}}))
"""
    res = subprocess.run(
        [PYTHON, "-c", script],
        capture_output=True,
        text=True,
        timeout=20,
        env=_worktree_env(),
    )
    assert res.returncode == 0, f"mode={mode} stderr: {res.stderr}"
    data = json.loads(res.stdout.strip().splitlines()[-1])
    assert data["auto_active"] is expect_auto
    assert data["spy_installed"] is expect_spy
    assert data["console_tee"] is expect_console_tee
    assert data["has_signals"] is expect_signals
    assert data["outcome"] == "completed"
    assert data["git_status"] == "failed"
    assert data["capture_status"] == "partial"
    assert data["spy_after_stop"] is False


@pytest.mark.parametrize("mode", ["nopatch", "minimal", "noconsole"])
def test_rollback_in_restricted_import_modes_preserves_third_party_hooks(
    tmp_path, monkeypatch, mode
):
    """When startup output fails and triggers rollback in nopatch/minimal/noconsole,
    pre-existing third-party hooks that the mode did not install must remain intact."""
    from pubrun._bootstrap import select_mode

    monkeypatch.setattr("pathlib.Path.cwd", lambda: tmp_path)
    select_mode(mode, f"pubrun.{mode}", "unit-test")

    # Install third-party wrappers before Run()
    orig_stdout = sys.stdout
    orig_popen_init = subprocess.Popen.__init__
    orig_excepthook = sys.excepthook

    class ThirdPartyStream:
        def __init__(self, inner):
            self.inner = inner
        def write(self, s):
            return self.inner.write(s)
        def flush(self):
            return self.inner.flush()
        def isatty(self):
            return False

    tp_stdout = ThirdPartyStream(orig_stdout)
    tp_excepthook = lambda *a: orig_excepthook(*a)

    def tp_popen_init(self, *a, **kw):
        return orig_popen_init(self, *a, **kw)

    monkeypatch.setattr(sys, "stdout", tp_stdout)
    monkeypatch.setattr(sys, "excepthook", tp_excepthook)
    monkeypatch.setattr(subprocess.Popen, "__init__", tp_popen_init)

    # Force startup output write failure to trigger rollback
    monkeypatch.setattr(
        writer_mod.ArtifactWriter,
        "write_startup_manifest",
        lambda self, *a, **kw: False,
    )

    run = Run(
        overrides={
            "console": {"capture_mode": "standard"},
            "capture": {
                "subprocesses": {"enabled": True},
                "signals": {"enabled": True},
            },
        }
    )
    assert run._outcome == "ghost"
    assert sys.stdout is tp_stdout
    assert subprocess.Popen.__init__ is tp_popen_init
    assert sys.excepthook is tp_excepthook
    run.stop()
