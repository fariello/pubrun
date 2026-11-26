import os
import sys
import json
import pytest
from pathlib import Path
import pubrun

def test_report_and_artifact(tmp_path):
    import pubrun.tracker
    pubrun.tracker._active_run = None

    old_cwd = Path.cwd
    try:
        Path.cwd = staticmethod(lambda: tmp_path)
        tracker = pubrun.start(console={"capture_mode": "off"})

        # Test report
        pubrun.report("eval_metrics", {"accuracy": 0.985})
        report_file = tracker.run_dir / "eval_metrics.json"
        assert report_file.exists()
        with open(report_file, "r") as f:
            data = json.load(f)
        assert data["accuracy"] == 0.985

        # Test string report
        pubrun.report("raw_text", "some plain text")
        txt_file = tracker.run_dir / "raw_text.txt"
        assert txt_file.exists()
        assert txt_file.read_text().strip() == "some plain text"

        # Test artifact
        pubrun.artifact("output.bin", b"\x00\x01\x02")
        bin_file = tracker.run_dir / "output.bin"
        assert bin_file.exists()
        assert bin_file.read_bytes() == b"\x00\x01\x02"

        # Test text artifact
        pubrun.artifact("output.txt", "hello")
        artifact_txt = tracker.run_dir / "output.txt"
        assert artifact_txt.exists()
        assert artifact_txt.read_text().strip() == "hello"

        tracker.stop()
    finally:
        Path.cwd = old_cwd
        pubrun.tracker._active_run = None


def test_pubrun_print(tmp_path):
    import pubrun.tracker
    pubrun.tracker._active_run = None
    old_cwd = Path.cwd
    try:
        Path.cwd = staticmethod(lambda: tmp_path)
        tracker = pubrun.start(console={"capture_mode": "off"})

        pubrun.print("hello", "world", sep="-")

        log_file = tracker.run_dir / "stdout.log"
        assert log_file.exists()
        content = log_file.read_text()
        assert "hello-world" in content

        tracker.stop()
    finally:
        Path.cwd = old_cwd
        pubrun.tracker._active_run = None


def test_pubrun_open_provenance(tmp_path):
    import pubrun.tracker
    pubrun.tracker._active_run = None
    old_cwd = Path.cwd
    try:
        Path.cwd = staticmethod(lambda: tmp_path)

        input_file = tmp_path / "dataset.txt"
        input_file.write_text("dataset content line 1\nline 2", encoding="utf-8")

        # level="hash" to exercise content hashing (the default is now "stat").
        tracker = pubrun.start(console={"capture_mode": "off"},
                               capture={"file_io": {"level": "hash"}})

        with pubrun.open(input_file, "r") as f:
            lines = f.readlines()
        assert len(lines) == 2

        output_file = tmp_path / "output_data.bin"
        with pubrun.open(output_file, "wb") as f:
            f.write(b"output data content")

        tracker.stop()

        manifest_path = tracker.run_dir / "manifest.json"
        assert manifest_path.exists()
        with open(manifest_path, "r") as f:
            manifest = json.load(f)

        assert "data_files" in manifest
        inputs = manifest["data_files"]["inputs"]
        outputs = manifest["data_files"]["outputs"]

        assert len(inputs) == 1
        assert inputs[0]["path"] == str(input_file.resolve())
        assert inputs[0]["size_bytes"] == os.path.getsize(input_file)
        import hashlib
        expected_sha = hashlib.sha256(input_file.read_bytes()).hexdigest()
        assert inputs[0]["sha256"] == expected_sha

        assert len(outputs) == 1
        assert outputs[0]["path"] == str(output_file.resolve())
        assert outputs[0]["size_bytes"] == len(b"output data content")
        expected_out_sha = hashlib.sha256(b"output data content").hexdigest()
        assert outputs[0]["sha256"] == expected_out_sha

    finally:
        Path.cwd = old_cwd
        pubrun.tracker._active_run = None


def test_explicit_subprocess_and_popen(tmp_path):
    import pubrun.tracker
    pubrun.tracker._active_run = None
    old_cwd = Path.cwd
    try:
        Path.cwd = staticmethod(lambda: tmp_path)
        tracker = pubrun.start(console={"capture_mode": "off"})

        res = pubrun.subprocess.run([sys.executable, "-c", "print('explicit subprocess')"], capture_output=True, text=True)
        assert res.returncode == 0
        assert "explicit subprocess" in res.stdout

        with pubrun.popen(f"{sys.executable} -c \"print('explicit popen')\"") as pipe:
            out = pipe.read()
        assert "explicit popen" in out

        tracker.stop()

        manifest_path = tracker.run_dir / "manifest.json"
        assert manifest_path.exists()
        with open(manifest_path, "r") as f:
            manifest = json.load(f)

        subprocs = manifest.get("subprocesses", [])
        assert len(subprocs) == 2
        cmd_argvs = [s["argv"] for s in subprocs]
        assert any("explicit subprocess" in str(arg) for arg in cmd_argvs)
        assert any("explicit popen" in str(arg) for arg in cmd_argvs)

    finally:
        Path.cwd = old_cwd
        pubrun.tracker._active_run = None


class _FakeClock:
    """Thread-safe deterministic wall and monotonic clock for explicit API tests."""

    def __init__(self, wall: float = 1_750_000_000.0, mono: float = 987654.321) -> None:
        import threading
        import time as _real_time

        self._lock = threading.Lock()
        self._real_time = _real_time
        self._wall = float(wall)
        self._mono = float(mono)

    def time(self) -> float:
        with self._lock:
            return self._wall

    def perf_counter(self) -> float:
        with self._lock:
            return self._mono

    def advance(self, seconds: float) -> None:
        with self._lock:
            self._mono += seconds
            self._wall += seconds

    def jump_wall(self, delta: float) -> None:
        with self._lock:
            self._wall += delta

    def __getattr__(self, name: str):
        return getattr(self._real_time, name)


def _validate_manifest_against_schema(manifest: dict) -> None:
    jsonschema = pytest.importorskip("jsonschema")
    schema_path = Path(__file__).resolve().parents[1] / "schemas" / "manifest.schema.json"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    jsonschema.validate(manifest, schema)


def test_explicit_subprocess_run_monotonic_and_schema(tmp_path, monkeypatch):
    import subprocess as std_subprocess
    import pubrun.core as core_mod
    import pubrun.tracker as tracker_mod
    import pubrun.writer as writer_mod

    clock = _FakeClock(wall=1_750_000_000.0, mono=987654.321)
    monkeypatch.setattr(core_mod, "time", clock)
    monkeypatch.setattr(tracker_mod, "time", clock)
    monkeypatch.setattr(writer_mod, "time", clock)
    monkeypatch.setattr(Path, "cwd", lambda: tmp_path)

    tracker = pubrun.start(console={"capture_mode": "off"}, capture={"resources": {"depth": "off"}})
    if tracker._hardware_future_done is not None:
        tracker._hardware_future_done.wait(timeout=5.0)

    real_run = core_mod._subprocess.run
    call_steps = iter([
        (0.45, -7200.0),
        (0.22, -7200.0),
        (0.11, -7200.0),
    ])

    def wrapped_run(*args, **kwargs):
        cmd = args[0] if args else kwargs.get("args")
        if isinstance(cmd, list) and cmd and cmd[0] == sys.executable:
            mono_step, wall_jump = next(call_steps)
            clock.advance(mono_step)
            clock.jump_wall(wall_jump)
        return real_run(*args, **kwargs)

    monkeypatch.setattr(core_mod._subprocess, "run", wrapped_run)
    try:
        res_ok = pubrun.subprocess.run(
            [sys.executable, "-c", "print('ok')"], capture_output=True, text=True
        )
        assert res_ok.returncode == 0

        res_nonzero = pubrun.subprocess.run(
            [sys.executable, "-c", "import sys; sys.exit(2)"], capture_output=True, text=True
        )
        assert res_nonzero.returncode == 2

        with pytest.raises(std_subprocess.CalledProcessError):
            pubrun.subprocess.run(
                [sys.executable, "-c", "import sys; sys.exit(3)"], check=True
            )
    finally:
        tracker.stop()

    raw_text = (tracker.run_dir / "manifest.json").read_text(encoding="utf-8")
    assert "987654" not in raw_text
    manifest = json.loads(raw_text)
    _validate_manifest_against_schema(manifest)

    subs = manifest["subprocesses"]
    assert len(subs) == 3

    ok_rec, nz_rec, err_rec = subs
    assert ok_rec["exit_code"] == 0
    assert ok_rec["ended_at_utc"] < ok_rec["started_at_utc"]
    assert ok_rec["elapsed_seconds"] == pytest.approx(0.45, abs=1e-9)
    assert ok_rec["duration_clock"] == "monotonic"
    assert ok_rec["capture_state"] == {"status": "complete"}

    assert nz_rec["exit_code"] == 2
    assert nz_rec["ended_at_utc"] < nz_rec["started_at_utc"]
    assert nz_rec["elapsed_seconds"] == pytest.approx(0.22, abs=1e-9)
    assert nz_rec["duration_clock"] == "monotonic"
    assert nz_rec["capture_state"] == {"status": "failed"}

    assert err_rec["exit_code"] == 3
    assert err_rec["pid"] is None
    assert err_rec["ended_at_utc"] < err_rec["started_at_utc"]
    assert err_rec["elapsed_seconds"] == pytest.approx(0.11, abs=1e-9)
    assert err_rec["duration_clock"] == "monotonic"
    assert "CalledProcessError" in err_rec["error"]
    assert err_rec["capture_state"]["status"] == "failed"
    assert "CalledProcessError" in err_rec["capture_state"]["detail"]


def test_explicit_subprocess_popen_wait_communicate_poll_timeout_and_failure(
    tmp_path, monkeypatch
):
    import subprocess as std_subprocess
    import time as real_time
    import pubrun.core as core_mod
    import pubrun.tracker as tracker_mod
    import pubrun.writer as writer_mod

    clock = _FakeClock(wall=1_750_000_000.0, mono=987654.321)
    monkeypatch.setattr(core_mod, "time", clock)
    monkeypatch.setattr(tracker_mod, "time", clock)
    monkeypatch.setattr(writer_mod, "time", clock)
    monkeypatch.setattr(Path, "cwd", lambda: tmp_path)

    tracker = pubrun.start(console={"capture_mode": "off"}, capture={"resources": {"depth": "off"}})
    try:
        # 1. wait(timeout) raising TimeoutExpired must not log prematurely; final wait logs once.
        p_wait = pubrun.subprocess.Popen([sys.executable, "-c", "import time; time.sleep(0.5)"])
        try:
            with pytest.raises(std_subprocess.TimeoutExpired):
                p_wait.wait(timeout=0.01)
            assert len(getattr(tracker, "manual_subprocess_records", [])) == 0

            clock.advance(0.40)
            clock.jump_wall(-7200.0)
            assert p_wait.wait(timeout=10) == 0
            assert len(tracker.manual_subprocess_records) == 1
        finally:
            if p_wait.poll() is None:
                p_wait.kill()
                p_wait.wait()

        # 2. communicate(timeout) raising TimeoutExpired must not log prematurely.
        p_comm = pubrun.subprocess.Popen(
            [sys.executable, "-c", "import time; time.sleep(0.5); print('comm_done')"],
            stdout=std_subprocess.PIPE,
            text=True,
        )
        try:
            with pytest.raises(std_subprocess.TimeoutExpired):
                p_comm.communicate(timeout=0.01)
            assert len(tracker.manual_subprocess_records) == 1

            clock.advance(0.25)
            clock.jump_wall(-7200.0)
            stdout, _ = p_comm.communicate(timeout=10)
            assert "comm_done" in stdout
            assert len(tracker.manual_subprocess_records) == 2
        finally:
            if p_comm.poll() is None:
                p_comm.kill()
                p_comm.wait()

        # 3. poll() logs once when process completes.
        p_poll = pubrun.subprocess.Popen([sys.executable, "-c", "pass"])
        clock.advance(0.15)
        clock.jump_wall(-7200.0)
        deadline = real_time.monotonic() + 5.0
        rc = p_poll.poll()
        while rc is None and real_time.monotonic() < deadline:
            real_time.sleep(0.01)
            rc = p_poll.poll()
        assert rc == 0
        # Extra poll/wait calls must not duplicate the record.
        assert p_poll.poll() == 0
        assert p_poll.wait() == 0
        assert len(tracker.manual_subprocess_records) == 3

        # 4. Launch failure in Popen.__init__ records failed invocation before re-raising.
        real_popen_init = std_subprocess.Popen.__init__

        def failing_init(self, *args, **kwargs):
            clock.advance(0.08)
            clock.jump_wall(-7200.0)
            raise FileNotFoundError("missing executable")

        monkeypatch.setattr(std_subprocess.Popen, "__init__", failing_init)
        try:
            with pytest.raises(FileNotFoundError, match="missing executable"):
                pubrun.subprocess.Popen(["__missing_explicit_popen__"])
        finally:
            monkeypatch.setattr(std_subprocess.Popen, "__init__", real_popen_init)
    finally:
        tracker.stop()

    raw_text = (tracker.run_dir / "manifest.json").read_text(encoding="utf-8")
    assert "987654" not in raw_text
    manifest = json.loads(raw_text)
    _validate_manifest_against_schema(manifest)

    subs = manifest["subprocesses"]
    assert len(subs) == 4

    r_wait, r_comm, r_poll, r_fail = subs
    assert r_wait["elapsed_seconds"] == pytest.approx(0.40, abs=1e-9)
    assert r_wait["duration_clock"] == "monotonic"
    assert r_wait["ended_at_utc"] < r_wait["started_at_utc"]
    assert r_wait["capture_state"] == {"status": "complete"}
    assert isinstance(r_wait["pid"], int) and r_wait["pid"] >= 0

    assert r_comm["elapsed_seconds"] == pytest.approx(0.25, abs=1e-9)
    assert r_comm["duration_clock"] == "monotonic"
    assert r_comm["ended_at_utc"] < r_comm["started_at_utc"]
    assert r_comm["capture_state"] == {"status": "complete"}

    assert r_poll["elapsed_seconds"] == pytest.approx(0.15, abs=1e-9)
    assert r_poll["duration_clock"] == "monotonic"
    assert r_poll["ended_at_utc"] < r_poll["started_at_utc"]
    assert r_poll["capture_state"] == {"status": "complete"}

    assert r_fail["exit_code"] is None
    assert r_fail["pid"] is None
    assert r_fail["ended_at_utc"] < r_fail["started_at_utc"]
    assert r_fail["elapsed_seconds"] == pytest.approx(0.08, abs=1e-9)
    assert r_fail["duration_clock"] == "monotonic"
    assert "FileNotFoundError" in r_fail["error"]
    assert r_fail["capture_state"]["status"] == "failed"
    assert "FileNotFoundError" in r_fail["capture_state"]["detail"]


def test_explicit_popen_monotonic_and_launch_failure_schema(tmp_path, monkeypatch):
    import pubrun.core as core_mod
    import pubrun.tracker as tracker_mod
    import pubrun.writer as writer_mod

    clock = _FakeClock(wall=1_750_000_000.0, mono=987654.321)
    monkeypatch.setattr(core_mod, "time", clock)
    monkeypatch.setattr(tracker_mod, "time", clock)
    monkeypatch.setattr(writer_mod, "time", clock)
    monkeypatch.setattr(Path, "cwd", lambda: tmp_path)

    tracker = pubrun.start(console={"capture_mode": "off"}, capture={"resources": {"depth": "off"}})
    try:
        with pubrun.popen(f"{sys.executable} -c \"print('popen_ok')\"") as pipe:
            out = pipe.read()
            assert "popen_ok" in out
            clock.advance(0.33)
            clock.jump_wall(-7200.0)

        def failing_os_popen(cmd, mode="r", bufsize=-1):
            clock.advance(0.09)
            clock.jump_wall(-7200.0)
            raise OSError("popen launch failed")

        monkeypatch.setattr(os, "popen", failing_os_popen)
        with pytest.raises(OSError, match="popen launch failed"):
            pubrun.popen("bad_popen_cmd")
    finally:
        tracker.stop()

    raw_text = (tracker.run_dir / "manifest.json").read_text(encoding="utf-8")
    assert "987654" not in raw_text
    manifest = json.loads(raw_text)
    _validate_manifest_against_schema(manifest)

    subs = manifest["subprocesses"]
    assert len(subs) == 2

    ok_rec, fail_rec = subs
    assert ok_rec["exit_code"] == 0
    assert ok_rec["ended_at_utc"] < ok_rec["started_at_utc"]
    assert ok_rec["elapsed_seconds"] == pytest.approx(0.33, abs=1e-9)
    assert ok_rec["duration_clock"] == "monotonic"
    assert ok_rec["capture_state"] == {"status": "complete"}

    assert fail_rec["exit_code"] is None
    assert fail_rec["pid"] is None
    assert fail_rec["ended_at_utc"] < fail_rec["started_at_utc"]
    assert fail_rec["elapsed_seconds"] == pytest.approx(0.09, abs=1e-9)
    assert fail_rec["duration_clock"] == "monotonic"
    assert "OSError" in fail_rec["error"]
    assert fail_rec["capture_state"]["status"] == "failed"
    assert "OSError" in fail_rec["capture_state"]["detail"]


@pytest.fixture
def active_run(monkeypatch):
    """Manage active run lifecycle and yappi class latch without patching Path.cwd."""
    import pubrun.tracker

    pubrun.tracker._active_run = None
    monkeypatch.setattr(pubrun.phase, "_yappi_active", False, raising=False)

    def _start(**kwargs):
        opts = {"console": {"capture_mode": "off"}}
        opts.update(kwargs)
        return pubrun.start(**opts)

    yield _start

    active = pubrun.tracker._active_run
    if active is not None:
        try:
            active.stop()
        except Exception:
            pass
        pubrun.tracker._active_run = None


def test_report_and_artifact_inactive_error(tmp_path, active_run):
    (tmp_path / ".pubrun.toml").write_text(
        '[events]\non_inactive_annotate = "error"\n', encoding="utf-8"
    )
    with pytest.raises(RuntimeError, match="no run is active"):
        pubrun.report("r", {"a": 1})
    with pytest.raises(RuntimeError, match="no run is active"):
        pubrun.artifact("a.txt", "x")


def test_list_report_summarizes_item_count(active_run):
    tracker = active_run()
    pubrun.report("rows", [1, 2, 3])
    tracker.stop()

    report_path = tracker.run_dir / "rows.json"
    assert report_path.exists()
    assert json.loads(report_path.read_text(encoding="utf-8")) == [1, 2, 3]

    events = [
        json.loads(line)
        for line in (tracker.run_dir / "events.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    report_events = [
        e for e in events if e.get("type") == "annotation" and e.get("name") == "report: rows"
    ]
    assert len(report_events) == 1
    assert report_events[0]["payload"] == {
        "filename": "rows.json",
        "summary": {"items": 3},
    }


def test_report_and_artifact_write_error_logs_warning(active_run, monkeypatch, caplog):
    import logging

    active_run()

    def _disk_full(self, *args, **kwargs):
        raise OSError("disk full")

    with caplog.at_level(logging.WARNING, logger="pubrun"):
        with monkeypatch.context() as mp:
            mp.setattr(Path, "write_text", _disk_full)
            pubrun.report("r", {"a": 1})
            pubrun.artifact("a.txt", "x")

    messages = [r.getMessage() for r in caplog.records if r.levelno == logging.WARNING]
    assert "pubrun: failed to write report 'r': disk full" in messages
    assert "pubrun: failed to write artifact 'a.txt': disk full" in messages


def test_nested_yappi_phase_is_skipped_with_warning(active_run, monkeypatch, caplog):
    import logging
    import types

    calls = []

    class _FakeStats:
        def save(self, path, type="pstat"):
            calls.append("save")
            Path(path).write_text("yappi-profile", encoding="utf-8")

    fake_yappi = types.ModuleType("yappi")
    fake_yappi.start = lambda: calls.append("start")
    fake_yappi.stop = lambda: calls.append("stop")
    fake_yappi.clear_stats = lambda: calls.append("clear")
    fake_yappi.get_func_stats = lambda: _FakeStats()
    monkeypatch.setitem(sys.modules, "yappi", fake_yappi)

    tracker = active_run(capture={"profiling": {"enabled": True, "backend": "yappi"}})
    with caplog.at_level(logging.WARNING, logger="pubrun"):
        with pubrun.phase("outer"):
            assert pubrun.phase._yappi_active is True
            with pubrun.phase("inner"):
                assert pubrun.phase._yappi_active is True

    assert pubrun.phase._yappi_active is False
    assert calls == ["start", "stop", "save", "clear"]
    assert (tracker.run_dir / "profile-outer.prof").exists()
    assert not (tracker.run_dir / "profile-inner.prof").exists()
    messages = [r.getMessage() for r in caplog.records if r.levelno == logging.WARNING]
    assert (
        "pubrun: yappi already active (nested/concurrent phase); "
        "skipping profiling for phase 'inner'"
    ) in messages


def test_yappi_import_error_warns_and_skips(active_run, monkeypatch, caplog):
    import logging

    monkeypatch.setitem(sys.modules, "yappi", None)
    tracker = active_run(capture={"profiling": {"enabled": True, "backend": "yappi"}})
    with caplog.at_level(logging.WARNING, logger="pubrun"):
        with pubrun.phase("train"):
            pass

    messages = [r.getMessage() for r in caplog.records if r.levelno == logging.WARNING]
    assert any(
        msg.startswith("pubrun: profiling backend 'yappi' unavailable:") for msg in messages
    )
    assert list(tracker.run_dir.glob("profile-*.prof")) == []


def test_unknown_backend_warns_and_skips(active_run, caplog):
    import logging

    tracker = active_run(capture={"profiling": {"enabled": True, "backend": "pyinstrument"}})
    with caplog.at_level(logging.WARNING, logger="pubrun"):
        with pubrun.phase("train"):
            pass

    messages = [r.getMessage() for r in caplog.records if r.levelno == logging.WARNING]
    assert messages == [
        "pubrun: profiling backend 'pyinstrument' unavailable: unknown backend"
    ]
    assert list(tracker.run_dir.glob("profile-*.prof")) == []
