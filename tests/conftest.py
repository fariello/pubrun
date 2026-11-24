import json
import os
import pathlib
import signal
import sys
import threading

import pytest

import pubrun
import pubrun.tracker


FIXTURES_DIR = pathlib.Path(__file__).parent / "fixtures"
SRC_DIR = pathlib.Path(__file__).resolve().parents[1] / "src"


@pytest.fixture(scope="session", autouse=True)
def _subprocess_pythonpath():
    """Prepend this checkout's ``src`` to ``PYTHONPATH`` for the whole test session.

    ``pythonpath = ["src"]`` in ``pyproject.toml`` changes ``sys.path`` of the pytest process
    only. A child Python process that inherits the environment would otherwise import ``pubrun``
    through the interpreter's editable-install ``.pth`` entry, which may point at a different
    checkout (for example the main checkout when tests run inside a git worktree).
    """
    if not SRC_DIR.is_dir():
        yield
        return
    previous = os.environ.get("PYTHONPATH")
    if previous:
        os.environ["PYTHONPATH"] = f"{SRC_DIR}{os.pathsep}{previous}"
    else:
        os.environ["PYTHONPATH"] = str(SRC_DIR)
    yield
    if previous is None:
        os.environ.pop("PYTHONPATH", None)
    else:
        os.environ["PYTHONPATH"] = previous


@pytest.fixture(autouse=True)
def isolated_cwd(tmp_path, monkeypatch):
    """
    Globally patches the current working directory for ALL tests.
    Ensures 'pubrun_artifacts' or 'manifest.json' files never contaminate
    the actual developer workspace or slurm environments.
    """
    # Monkeypatch the standard library OS tools
    monkeypatch.chdir(tmp_path)
    # Monkeypatch the Pathlib native behavior used by pubrun Config routing
    monkeypatch.setattr("pathlib.Path.cwd", lambda: tmp_path)
    yield


@pytest.fixture(autouse=True)
def clean_active_run():
    """Ensure any unstopped active run and leaked process-global hooks are cleaned up around each test."""
    def _cleanup():
        active = pubrun.tracker._active_run
        if active is not None:
            try:
                if hasattr(active, "stop"):
                    active.ref_count = 1
                    active.stop()
            except Exception:
                pass
            pubrun.tracker._active_run = None
        try:
            from pubrun.capture.subprocesses import SubprocessSpy
            if SubprocessSpy._installed:
                SubprocessSpy.uninstall()
        except Exception:
            pass

    _cleanup()
    yield
    _cleanup()


@pytest.fixture(autouse=True)
def pubrun_state_isolation():
    """Reset pubrun process-global state around every test so test order cannot change outcomes.

    Without this fixture, module globals and process hooks left behind by one test can alter
    later tests depending on execution order. Setup snapshots `os.environ`, `sys.excepthook`,
    `sys.exit`, `sys.stdout`, `sys.stderr`, and the handlers for all platform-defined signals
    in `pubrun.capture.signals._TARGET_SIGNALS`. Teardown stops any leftover active run,
    resets pubrun latches and the commit cache, and restores every snapshotted hook, signal
    handler (on the main thread only), and environment variable that changed.
    """
    from pubrun import _bootstrap as _bs
    import pubrun.capture.signals as _signals
    import pubrun.status as _status

    def _reset():
        try:
            _bs.reset_state()
        except Exception:
            pass
        pubrun.tracker._active_run = None
        try:
            _status._DISPLAY_UTC = False
        except Exception:
            pass

    _env_snapshot = dict(os.environ)
    _orig_excepthook = sys.excepthook
    _orig_exit = sys.exit
    _orig_stdout = sys.stdout
    _orig_stderr = sys.stderr
    _signal_snapshot = {}
    for _sig_name in _signals._TARGET_SIGNALS:
        _sig = getattr(signal, _sig_name, None)
        if _sig is not None:
            try:
                _signal_snapshot[_sig] = signal.getsignal(_sig)
            except (OSError, ValueError, TypeError):
                pass

    _reset()
    yield

    active = pubrun.tracker._active_run
    if active is not None:
        try:
            if hasattr(active, "stop"):
                active.ref_count = 1
                active.stop()
        except Exception:
            pass

    _reset()

    try:
        pubrun._reset_commit_cache()
    except Exception:
        pass
    try:
        _signals._finalizing_active_run = False
    except Exception:
        pass
    try:
        import pubrun.core as _core
        _core.phase._yappi_active = False
    except Exception:
        pass

    if sys.excepthook is not _orig_excepthook:
        sys.excepthook = _orig_excepthook
    if sys.exit is not _orig_exit:
        sys.exit = _orig_exit
    if sys.stdout is not _orig_stdout:
        sys.stdout = _orig_stdout
    if sys.stderr is not _orig_stderr:
        sys.stderr = _orig_stderr
    if threading.current_thread() is threading.main_thread():
        for _sig, _prev in _signal_snapshot.items():
            if _prev is None:
                continue
            try:
                if signal.getsignal(_sig) != _prev:
                    signal.signal(_sig, _prev)
            except (OSError, ValueError, TypeError):
                pass

    # Restore the environment exactly (remove keys a test added, restore ones it changed/removed).
    for k in list(os.environ.keys()):
        if k not in _env_snapshot:
            del os.environ[k]
    for k, v in _env_snapshot.items():
        if os.environ.get(k) != v:
            os.environ[k] = v


@pytest.fixture
def sample_manifest():
    """Load the golden sample manifest fixture."""
    with open(FIXTURES_DIR / "sample_manifest.json", "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture
def default_config():
    """Return a freshly resolved default config with no user/local overrides."""
    from pubrun.config import load_default_config
    return load_default_config()
