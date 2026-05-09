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
    """Ensure _active_run is reset after each test to prevent cross-test pollution."""
    yield
    pubrun.tracker._active_run = None


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
