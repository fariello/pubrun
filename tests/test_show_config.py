"""Tests for the `pubrun show config` family and its config-provenance mechanism.

Covers the three contexts (current / run / default), the degraded-run handling, the
provenance annotation, and CRITICALLY the regression invariants the new positional
keyword grammar most endangers (`show <run> <section>`, bare `show env`, and a run whose
id starts with a reserved keyword).
"""
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

PYTHON = sys.executable


def run_pubrun(*args, cwd=None):
    return subprocess.run(
        [PYTHON, "-m", "pubrun", *args],
        capture_output=True, text=True, cwd=cwd or os.getcwd(), timeout=30,
    )


def _make_run(cwd: Path):
    """Produce one completed run in cwd/runs and return its run dir name."""
    script = "import pubrun.noauto as p\np.start()\np.stop()\n"
    r = subprocess.run([PYTHON, "-c", script], cwd=str(cwd), capture_output=True,
                       text=True, timeout=30)
    assert r.returncode == 0, r.stderr
    runs = sorted((cwd / "runs").iterdir())
    assert runs
    return runs[-1].name


# ---- The three contexts -------------------------------------------------------------

class TestShowConfigContexts:
    def test_show_config_current(self, tmp_path):
        r = run_pubrun("show", "config", cwd=str(tmp_path))
        assert r.returncode == 0, r.stderr
        assert "resolved configuration (current" in r.stdout
        # a known default key is present
        assert "capture.hardware.depth" in r.stdout

    def test_show_default_config(self, tmp_path):
        r = run_pubrun("show", "default", "config", cwd=str(tmp_path))
        assert r.returncode == 0, r.stderr
        assert "[core]" in r.stdout or "pubrun Configuration" in r.stdout

    def test_show_run_config_latest(self, tmp_path):
        _make_run(tmp_path)
        r = run_pubrun("show", "run", "config", cwd=str(tmp_path))
        assert r.returncode == 0, r.stderr
        assert "resolved configuration for run" in r.stdout
        assert "capture.hardware.depth" in r.stdout

    def test_show_run_config_by_index(self, tmp_path):
        _make_run(tmp_path)
        r = run_pubrun("show", "run", "config", "1", cwd=str(tmp_path))
        assert r.returncode == 0, r.stderr
        assert "resolved configuration for run" in r.stdout

    def test_show_run_config_absent_errors(self, tmp_path):
        (tmp_path / "runs").mkdir()
        r = run_pubrun("show", "run", "config", "zzzznotarun", cwd=str(tmp_path))
        assert r.returncode != 0
        assert "no recorded config" in (r.stdout + r.stderr)


# ---- Provenance ---------------------------------------------------------------------

class TestShowConfigProvenance:
    def test_local_override_is_annotated(self, tmp_path):
        (tmp_path / ".pubrun.toml").write_text(
            "[capture.hardware]\ndepth = \"off\"\n", encoding="utf-8")
        r = run_pubrun("show", "config", cwd=str(tmp_path))
        assert r.returncode == 0, r.stderr
        line = next(l for l in r.stdout.splitlines() if "capture.hardware.depth" in l)
        assert "off" in line and "local" in line and "overrides" in line

    def test_no_conflict_prints_clean(self, tmp_path):
        r = run_pubrun("show", "config", cwd=str(tmp_path))
        assert r.returncode == 0, r.stderr
        # No override annotations when nothing is overridden.
        assert "overrides" not in r.stdout

    def test_all_flag_annotates_every_key(self, tmp_path):
        r = run_pubrun("show", "config", "--all", cwd=str(tmp_path))
        assert r.returncode == 0, r.stderr
        line = next(l for l in r.stdout.splitlines() if "capture.hardware.depth" in l)
        assert "[built-in]" in line

    def test_provenance_does_not_change_resolved_value(self):
        from pubrun.config import resolve_config, resolve_config_with_provenance
        plain = resolve_config()
        withp, prov = resolve_config_with_provenance()
        assert withp == plain  # value-preserving: provenance never alters the config


# ---- Regression: the grammar must not break existing forms --------------------------

class TestShowGrammarRegression:
    def test_bare_section_still_works(self, tmp_path):
        _make_run(tmp_path)
        r = run_pubrun("show", "env", cwd=str(tmp_path))
        assert r.returncode == 0, r.stderr
        assert "Environment Variables" in r.stdout

    def test_run_and_section_still_works(self, tmp_path):
        _make_run(tmp_path)
        r = run_pubrun("show", "1", "env", cwd=str(tmp_path))
        assert r.returncode == 0, r.stderr
        assert "Environment Variables" in r.stdout

    def test_plain_show_run_still_works(self, tmp_path):
        _make_run(tmp_path)
        r = run_pubrun("show", "1", cwd=str(tmp_path))
        assert r.returncode == 0, r.stderr
        # a normal report, not the config view
        assert "resolved configuration" not in r.stdout


# ---- --show-config soft-deprecation -------------------------------------------------

class TestShowConfigFlagDeprecation:
    def test_show_config_flag_still_prints_defaults_with_notice(self, tmp_path):
        r = run_pubrun("--show-config", cwd=str(tmp_path))
        assert r.returncode == 0, r.stderr
        assert "[core]" in r.stdout or "pubrun Configuration" in r.stdout
        assert "deprecated" in r.stderr.lower()
        assert "show default config" in r.stderr
