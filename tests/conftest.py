import pytest
import os
import pathlib

@pytest.fixture(autouse=True)
def isolated_cwd(tmp_path, monkeypatch):
    """
    Globally patches the current working directory for ALL tests.
    Ensures 'runtrace_artifacts' or 'manifest.json' files never contaminate
    the actual developer workspace or slurm environments.
    """
    # Monkeypatch the standard library OS tools
    monkeypatch.chdir(tmp_path)
    # Monkeypatch the Pathlib native behavior used by runtrace Config routing
    monkeypatch.setattr("pathlib.Path.cwd", lambda: tmp_path)
    yield
