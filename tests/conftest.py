import json
import pytest
import os
import pathlib

import pubrun.tracker


FIXTURES_DIR = pathlib.Path(__file__).parent / "fixtures"


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
    """Ensure _active_run is reset before and after each test to prevent cross-test pollution."""
    pubrun.tracker._active_run = None
    yield
    pubrun.tracker._active_run = None


@pytest.fixture(autouse=True)
def pubrun_state_isolation():
    """Reset pubrun's PROCESS-GLOBAL state around every test so test ORDER cannot change outcomes.

    Without this, module-globals leaked by one test silently changed later tests depending on run
    order (a cluster of order/timing flakes surfaced across the CI matrix; see IPD
    .agents/plans/executed/20260720-0026-01). The specific process-global state that leaks:

    - The `_bootstrap` import-mode latch (`_selected_mode` etc., "first import wins"): reset via the
      library's own `reset_state()` testing hook, NOT by poking individual globals.
    - The `status._DISPLAY_UTC` display toggle (mutated by `set_display_utc`).
    - Process environment variables some tests set directly on `os.environ` (e.g. `NO_COLOR`,
      `PUBRUN_*`) rather than via monkeypatch: snapshot before, restore after, so a leak from one
      test cannot pollute a successor regardless of order.

    This resets ISOLATION state only; it does not change library behavior. Assertions still fail on a
    real regression (they only stop being order-dependent).
    """
    import os as _os
    from pubrun import _bootstrap as _bs
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

    _env_snapshot = dict(_os.environ)
    _reset()
    yield
    _reset()
    # Restore the environment exactly (remove keys a test added, restore ones it changed/removed).
    for k in list(_os.environ.keys()):
        if k not in _env_snapshot:
            del _os.environ[k]
    for k, v in _env_snapshot.items():
        if _os.environ.get(k) != v:
            _os.environ[k] = v


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
