"""Tests for import mode resolution, bootstrap state, and conflict detection."""
import os
import json
import pathlib
import subprocess
import sys
import warnings
import pytest

from pubrun._modes import MODES, VALID_MODES, get_mode_behavior, resolve_mode_name
from pubrun._config_boot import resolve_import_mode
from pubrun._bootstrap import (
    select_mode,
    is_mode_selected,
    get_selected_mode,
    get_selected_behavior,
    mark_core_loaded,
    is_core_loaded,
    get_import_metadata,
    reset_state,
    PubrunImportModeConflictError,
    PubrunImportModeConflictWarning,
    PubrunImportModeTooLateWarning,
)


PYTHON = sys.executable


class TestModeDefinitions:
    """Unit tests for _modes.py."""

    def test_modes_defined(self):
        assert len(MODES) == 6
        assert VALID_MODES == {"auto", "noauto", "nopatch", "noconsole", "minimal", "full"}

    def test_auto_mode_behavior(self):
        b = get_mode_behavior("auto")
        assert b == {
            "auto_start": True,
            "global_hooks": True,
            "patch_subprocesses": True,
            "patch_console": True,
            "signal_hooks": True,
        }

    def test_noauto_mode_behavior(self):
        b = get_mode_behavior("noauto")
        assert b == {
            "auto_start": False,
            "global_hooks": True,
            "patch_subprocesses": True,
            "patch_console": True,
            "signal_hooks": True,
        }

    def test_nopatch_mode_behavior(self):
        b = get_mode_behavior("nopatch")
        assert b == {
            "auto_start": True,
            "global_hooks": False,
            "patch_subprocesses": False,
            "patch_console": False,
            "signal_hooks": True,
        }

    def test_noconsole_mode_behavior(self):
        b = get_mode_behavior("noconsole")
        assert b == {
            "auto_start": True,
            "global_hooks": True,
            "patch_subprocesses": True,
            "patch_console": False,
            "signal_hooks": True,
        }

    def test_minimal_mode_behavior(self):
        b = get_mode_behavior("minimal")
        assert b == {
            "auto_start": False,
            "global_hooks": False,
            "patch_subprocesses": False,
            "patch_console": False,
            "signal_hooks": False,
        }

    def test_unknown_mode_falls_back_to_auto(self):
        b = get_mode_behavior("invalid")
        assert b == {
            "auto_start": True,
            "global_hooks": True,
            "patch_subprocesses": True,
            "patch_console": True,
            "signal_hooks": True,
        }

    def test_get_mode_behavior_returns_copy(self):
        b1 = get_mode_behavior("auto")
        b1["auto_start"] = False
        b2 = get_mode_behavior("auto")
        assert b2["auto_start"] is True

    def test_resolve_mode_name(self):
        assert resolve_mode_name(True, True) == "auto"
        assert resolve_mode_name(False, True) == "noauto"
        assert resolve_mode_name(True, False) == "nopatch"
        assert resolve_mode_name(False, False) == "minimal"


class TestConfigBootResolver:
    """Unit tests for _config_boot.py resolve_import_mode()."""

    def test_default_is_auto(self, monkeypatch):
        monkeypatch.delenv("PUBRUN_IMPORT_MODE", raising=False)
        monkeypatch.delenv("PUBRUN_AUTO_START", raising=False)
        mode, source = resolve_import_mode()
        assert mode == "auto"
        assert source == "default"

    def test_pubrun_import_mode_env_minimal(self, monkeypatch):
        monkeypatch.setenv("PUBRUN_IMPORT_MODE", "minimal")
        monkeypatch.delenv("PUBRUN_AUTO_START", raising=False)
        mode, source = resolve_import_mode()
        assert mode == "minimal"
        assert source == "env:PUBRUN_IMPORT_MODE"

    def test_pubrun_import_mode_env_nopatch(self, monkeypatch):
        monkeypatch.setenv("PUBRUN_IMPORT_MODE", "nopatch")
        mode, source = resolve_import_mode()
        assert mode == "nopatch"
        assert source == "env:PUBRUN_IMPORT_MODE"

    def test_pubrun_import_mode_case_insensitive(self, monkeypatch):
        monkeypatch.setenv("PUBRUN_IMPORT_MODE", "NOAUTO")
        mode, source = resolve_import_mode()
        assert mode == "noauto"

    def test_pubrun_import_mode_invalid_falls_through(self, monkeypatch):
        monkeypatch.setenv("PUBRUN_IMPORT_MODE", "bogus")
        monkeypatch.delenv("PUBRUN_AUTO_START", raising=False)
        mode, source = resolve_import_mode()
        # Invalid PUBRUN_IMPORT_MODE is ignored; falls to default
        assert mode == "auto"
        assert source == "default"

    def test_legacy_auto_start_false(self, monkeypatch):
        monkeypatch.delenv("PUBRUN_IMPORT_MODE", raising=False)
        monkeypatch.setenv("PUBRUN_AUTO_START", "false")
        mode, source = resolve_import_mode()
        assert mode == "noauto"
        assert source == "env:PUBRUN_AUTO_START"

    def test_legacy_auto_start_true(self, monkeypatch):
        monkeypatch.delenv("PUBRUN_IMPORT_MODE", raising=False)
        monkeypatch.setenv("PUBRUN_AUTO_START", "true")
        mode, source = resolve_import_mode()
        assert mode == "auto"
        assert source == "env:PUBRUN_AUTO_START"

    def test_import_mode_takes_precedence_over_auto_start(self, monkeypatch):
        monkeypatch.setenv("PUBRUN_IMPORT_MODE", "minimal")
        monkeypatch.setenv("PUBRUN_AUTO_START", "true")
        mode, source = resolve_import_mode()
        assert mode == "minimal"
        assert source == "env:PUBRUN_IMPORT_MODE"

    def test_config_file_imports_mode(self, tmp_path, monkeypatch):
        """[imports].mode in .pubrun.toml is respected."""
        toml_file = tmp_path / ".pubrun.toml"
        toml_file.write_text('[imports]\nmode = "nopatch"\n', encoding="utf-8")
        monkeypatch.chdir(tmp_path)
        monkeypatch.delenv("PUBRUN_IMPORT_MODE", raising=False)
        monkeypatch.delenv("PUBRUN_AUTO_START", raising=False)
        mode, source = resolve_import_mode()
        assert mode == "nopatch"
        assert source == "config:[imports].mode"

    def test_config_file_core_auto_start_false(self, tmp_path, monkeypatch):
        """[core].auto_start = false in .pubrun.toml maps to noauto."""
        toml_file = tmp_path / ".pubrun.toml"
        toml_file.write_text('[core]\nauto_start = false\n', encoding="utf-8")
        monkeypatch.chdir(tmp_path)
        monkeypatch.delenv("PUBRUN_IMPORT_MODE", raising=False)
        monkeypatch.delenv("PUBRUN_AUTO_START", raising=False)
        mode, source = resolve_import_mode()
        assert mode == "noauto"
        assert source == "config:[core].auto_start"

    def test_env_overrides_config_file(self, tmp_path, monkeypatch):
        """Environment variable takes precedence over config file."""
        toml_file = tmp_path / ".pubrun.toml"
        toml_file.write_text('[imports]\nmode = "minimal"\n', encoding="utf-8")
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("PUBRUN_IMPORT_MODE", "auto")
        mode, source = resolve_import_mode()
        assert mode == "auto"
        assert source == "env:PUBRUN_IMPORT_MODE"


class TestBootSequenceIntegration:
    """Subprocess tests verifying the boot sequence uses the centralized resolver."""

    def test_default_auto_starts(self, tmp_path):
        """Default behavior: import pubrun auto-starts."""
        script = f"""
import os, sys, json
os.chdir({str(tmp_path)!r})
os.environ.pop('PUBRUN_IMPORT_MODE', None)
os.environ.pop('PUBRUN_RUN_MODE_OVERRIDE', None)
os.environ['PUBRUN_AUTO_START'] = 'true'
for mod in list(sys.modules.keys()):
    if 'pubrun' in mod:
        del sys.modules[mod]
import pubrun
run = pubrun.get_current_run()
print(json.dumps({{"active": run is not None}}))
if run:
    pubrun.stop()
"""
        result = subprocess.run(
            [PYTHON, "-c", script],
            capture_output=True, text=True, timeout=15,
            env={**os.environ, "PUBRUN_AUTO_START": "true", "PUBRUN_RUN_MODE_OVERRIDE": ""}
        )
        assert result.returncode == 0, f"stderr: {result.stderr}"
        data = json.loads(result.stdout.strip())
        assert data["active"] is True


# =============================================================================
# Phase 3: Bootstrap state and conflict detection
# =============================================================================

@pytest.fixture(autouse=False)
def clean_bootstrap(monkeypatch):
    """Reset bootstrap state before and after each test that uses it."""
    monkeypatch.delenv("PUBRUN_RUN_MODE_OVERRIDE", raising=False)
    reset_state()
    yield
    reset_state()


class TestBootstrapState:
    """Tests for _bootstrap.py state tracking."""

    def test_initial_state_is_unselected(self, clean_bootstrap):
        assert not is_mode_selected()
        assert get_selected_mode() is None
        assert get_selected_behavior() is None
        assert not is_core_loaded()

    def test_select_mode_sets_state(self, clean_bootstrap):
        behavior = select_mode("minimal", "test", "unit-test")
        assert is_mode_selected()
        assert get_selected_mode() == "minimal"
        assert get_selected_behavior() == {
            "auto_start": False,
            "global_hooks": False,
            "patch_subprocesses": False,
            "patch_console": False,
            "signal_hooks": False,
        }
        assert behavior == {
            "auto_start": False,
            "global_hooks": False,
            "patch_subprocesses": False,
            "patch_console": False,
            "signal_hooks": False,
        }

    def test_mark_core_loaded(self, clean_bootstrap):
        assert not is_core_loaded()
        mark_core_loaded()
        assert is_core_loaded()

    def test_get_import_metadata_structure(self, clean_bootstrap):
        select_mode("auto", "pubrun", "default")
        meta = get_import_metadata()
        assert meta["selected_mode"] == "auto"
        assert meta["selected_behavior"] == {
            "auto_start": True,
            "global_hooks": True,
            "patch_subprocesses": True,
            "patch_console": True,
            "signal_hooks": True,
        }
        assert meta["selected_by"] == "pubrun"
        assert meta["selected_source"] == "default"
        assert isinstance(meta["selected_at_utc"], float)
        assert meta["conflicts_detected"] == 0
        assert len(meta["requests"]) == 1
        assert meta["requests"][0]["selected"] is True

    def test_reset_state_clears_everything(self, clean_bootstrap):
        select_mode("nopatch", "test", "unit")
        mark_core_loaded()
        reset_state()
        assert not is_mode_selected()
        assert not is_core_loaded()


class TestConflictDetection:
    """Tests for import-mode conflict detection."""

    def test_same_mode_no_conflict(self, clean_bootstrap, monkeypatch):
        monkeypatch.setenv("PUBRUN_IMPORT_CONFLICT", "error")
        select_mode("auto", "pubrun", "default")
        # Same mode again should NOT raise
        behavior = select_mode("auto", "pubrun.auto", "explicit")
        assert behavior == {
            "auto_start": True,
            "global_hooks": True,
            "patch_subprocesses": True,
            "patch_console": True,
            "signal_hooks": True,
        }
        meta = get_import_metadata()
        assert meta["conflicts_detected"] == 0

    def test_different_mode_warns_by_default(self, clean_bootstrap, monkeypatch):
        monkeypatch.setenv("PUBRUN_IMPORT_CONFLICT", "warn")
        select_mode("auto", "pubrun", "default")
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            select_mode("noauto", "pubrun.noauto", "explicit")
        assert len(w) == 1
        assert issubclass(w[0].category, PubrunImportModeConflictWarning)
        assert "Conflicting" in str(w[0].message)

    def test_different_mode_errors_when_configured(self, clean_bootstrap, monkeypatch):
        monkeypatch.setenv("PUBRUN_IMPORT_CONFLICT", "error")
        select_mode("auto", "pubrun", "default")
        with pytest.raises(PubrunImportModeConflictError, match="Conflicting"):
            select_mode("minimal", "pubrun.minimal", "explicit")

    def test_different_mode_silent_when_ignore(self, clean_bootstrap, monkeypatch):
        monkeypatch.setenv("PUBRUN_IMPORT_CONFLICT", "ignore")
        select_mode("auto", "pubrun", "default")
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            select_mode("noauto", "pubrun.noauto", "explicit")
        # No warnings emitted
        conflict_warnings = [x for x in w if issubclass(x.category, PubrunImportModeConflictWarning)]
        assert len(conflict_warnings) == 0
        # But metadata still records the conflict
        meta = get_import_metadata()
        assert meta["conflicts_detected"] == 1

    def test_first_mode_wins(self, clean_bootstrap, monkeypatch):
        monkeypatch.setenv("PUBRUN_IMPORT_CONFLICT", "ignore")
        select_mode("minimal", "first_caller", "test")
        select_mode("auto", "second_caller", "test")
        # First mode wins
        assert get_selected_mode() == "minimal"
        assert get_selected_behavior() == {
            "auto_start": False,
            "global_hooks": False,
            "patch_subprocesses": False,
            "patch_console": False,
            "signal_hooks": False,
        }

    def test_conflict_records_core_loaded_state(self, clean_bootstrap, monkeypatch):
        monkeypatch.setenv("PUBRUN_IMPORT_CONFLICT", "ignore")
        select_mode("auto", "pubrun", "default")
        mark_core_loaded()
        select_mode("noauto", "pubrun.noauto", "explicit")
        meta = get_import_metadata()
        conflict_req = [r for r in meta["requests"] if r["conflict"]]
        assert len(conflict_req) == 1
        assert conflict_req[0]["core_loaded_at_request"] is True

    def test_max_requests_limit(self, clean_bootstrap, monkeypatch):
        monkeypatch.setenv("PUBRUN_IMPORT_CONFLICT", "ignore")
        select_mode("auto", "pubrun", "default")
        # Flood with duplicate requests
        for i in range(100):
            select_mode("auto", f"caller_{i}", "test")
        meta = get_import_metadata()
        assert len(meta["requests"]) <= 50

    def test_cli_run_mode_override_wins_without_conflict(self, clean_bootstrap, monkeypatch):
        monkeypatch.setenv("PUBRUN_RUN_MODE_OVERRIDE", "minimal")
        monkeypatch.setenv("PUBRUN_IMPORT_CONFLICT", "error")
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            behavior = select_mode("full", "pubrun.full", "explicit")
        assert len(w) == 0
        assert behavior == get_mode_behavior("minimal")
        assert get_selected_mode() == "minimal"
        assert get_selected_behavior() == get_mode_behavior("minimal")
        meta = get_import_metadata()
        assert meta["selected_mode"] == "minimal"
        assert meta["selected_by"] == "cli:pubrun run --mode"
        assert meta["selected_source"] == "cli:pubrun run --mode"
        assert meta["conflicts_detected"] == 0
        assert len(meta["requests"]) == 2
        assert meta["requests"][0]["requested_mode"] == "minimal"
        assert meta["requests"][0]["selected_by"] == "cli:pubrun run --mode"
        assert meta["requests"][0]["effective_behavior"] == get_mode_behavior("minimal")
        assert meta["requests"][0]["selected"] is True
        assert meta["requests"][0]["conflict"] is False
        assert meta["requests"][1]["requested_mode"] == "full"
        assert meta["requests"][1]["selected_by"] == "pubrun.full"
        assert meta["requests"][1]["effective_behavior"] == get_mode_behavior("full")
        assert meta["requests"][1]["selected"] is False
        assert meta["requests"][1]["conflict"] is False

    def test_cli_run_mode_override_matching_mode_records_one_request(
        self, clean_bootstrap, monkeypatch
    ):
        monkeypatch.setenv("PUBRUN_RUN_MODE_OVERRIDE", "minimal")
        behavior = select_mode("minimal", "pubrun", "env:PUBRUN_IMPORT_MODE")
        assert behavior == get_mode_behavior("minimal")
        meta = get_import_metadata()
        assert meta["selected_by"] == "cli:pubrun run --mode"
        assert meta["selected_source"] == "cli:pubrun run --mode"
        assert len(meta["requests"]) == 1
        assert meta["requests"][0]["selected"] is True
        assert meta["requests"][0]["conflict"] is False

    def test_cli_run_mode_override_subsequent_calls_non_conflicting_and_capped(
        self, clean_bootstrap, monkeypatch
    ):
        monkeypatch.setenv("PUBRUN_RUN_MODE_OVERRIDE", "minimal")
        monkeypatch.setenv("PUBRUN_IMPORT_CONFLICT", "error")
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            first = select_mode("minimal", "pubrun", "env:PUBRUN_IMPORT_MODE")
            second = select_mode("full", "pubrun.full", "explicit")
            third = select_mode("noconsole", "pubrun.noconsole", "explicit")
            for i in range(60):
                select_mode("auto", f"caller_{i}", "explicit")
        assert len(w) == 0
        expected = get_mode_behavior("minimal")
        assert first == expected
        assert second == expected
        assert third == expected
        meta = get_import_metadata()
        assert meta["conflicts_detected"] == 0
        assert len(meta["requests"]) <= 50
        assert meta["requests"][1]["requested_mode"] == "full"
        assert meta["requests"][1]["selected"] is False
        assert meta["requests"][1]["conflict"] is False
        assert meta["requests"][2]["requested_mode"] == "noconsole"
        assert meta["requests"][2]["selected"] is False
        assert meta["requests"][2]["conflict"] is False

    def test_cli_run_mode_override_invalid_value_ignored(self, clean_bootstrap, monkeypatch):
        monkeypatch.setenv("PUBRUN_RUN_MODE_OVERRIDE", "bogus")
        behavior = select_mode("full", "pubrun.full", "explicit")
        assert behavior == get_mode_behavior("full")
        meta = get_import_metadata()
        assert meta["selected_mode"] == "full"
        assert meta["selected_by"] == "pubrun.full"
        assert meta["selected_source"] == "explicit"


class TestImportMetadataInManifest:
    """Tests for pubrun_imports section in manifest and lock file."""

    def test_manifest_contains_pubrun_imports(self):
        from pubrun import start, get_current_run
        tracker = start()
        manifest = tracker.to_manifest_dict()
        assert "pubrun_imports" in manifest
        imports = manifest["pubrun_imports"]
        assert "selected_mode" in imports
        assert "selected_behavior" in imports
        assert "selected_by" in imports
        assert "requests" in imports
        tracker.stop()

    def test_manifest_imports_has_correct_mode(self):
        from pubrun import start
        from pubrun._bootstrap import is_mode_selected, select_mode
        # Ensure state is populated (may have been reset by earlier test fixtures)
        if not is_mode_selected():
            select_mode("auto", "test", "test-fixture")
        tracker = start()
        manifest = tracker.to_manifest_dict()
        imports = manifest["pubrun_imports"]
        assert imports["selected_mode"] in VALID_MODES
        assert isinstance(imports["selected_behavior"], dict)
        assert "auto_start" in imports["selected_behavior"]
        assert "global_hooks" in imports["selected_behavior"]
        tracker.stop()

    def test_lock_file_contains_import_mode(self):
        from pubrun import start
        import json
        tracker = start()
        lock_path = tracker.run_dir / ".pubrun.lock"
        assert lock_path.exists()
        with open(lock_path, "r", encoding="utf-8") as f:
            lock_data = json.load(f)
        assert "import_mode" in lock_data
        assert "import_selected_by" in lock_data
        assert lock_data["import_mode"] in (VALID_MODES | {None})
        tracker.stop()


# =============================================================================
# Phase 6: pubrun run CLI wrapper
# =============================================================================

class TestPubrunRunCommand:
    """Tests for the 'pubrun run' CLI wrapper."""

    def test_run_help(self):
        result = subprocess.run(
            [PYTHON, "-m", "pubrun", "run", "--help"],
            capture_output=True, text=True, timeout=10
        )
        assert result.returncode == 0
        assert "--mode" in result.stdout
        assert "minimal" in result.stdout

    def test_run_minimal_prevents_auto_start(self, tmp_path):
        script = tmp_path / "check.py"
        script.write_text(
            "import os, json\n"
            f"os.chdir({str(tmp_path)!r})\n"
            "import pubrun\n"
            "print(json.dumps({'active': pubrun.get_current_run() is not None}))\n",
            encoding="utf-8"
        )
        result = subprocess.run(
            [PYTHON, "-m", "pubrun", "run", "--mode", "minimal", "--", PYTHON, str(script)],
            capture_output=True, text=True, timeout=15
        )
        assert result.returncode == 0, f"stderr: {result.stderr}"
        data = json.loads(result.stdout.strip())
        assert data["active"] is False

    def test_run_auto_starts(self, tmp_path):
        script = tmp_path / "check.py"
        script.write_text(
            "import os, json\n"
            f"os.chdir({str(tmp_path)!r})\n"
            "import pubrun\n"
            "print(json.dumps({'active': pubrun.get_current_run() is not None}))\n"
            "if pubrun.get_current_run(): pubrun.stop()\n",
            encoding="utf-8"
        )
        result = subprocess.run(
            [PYTHON, "-m", "pubrun", "run", "--mode", "auto", "--", PYTHON, str(script)],
            capture_output=True, text=True, timeout=15
        )
        assert result.returncode == 0, f"stderr: {result.stderr}"
        data = json.loads(result.stdout.strip())
        assert data["active"] is True

    def test_run_returns_child_exit_code(self):
        result = subprocess.run(
            [PYTHON, "-m", "pubrun", "run", "--", PYTHON, "-c", "import sys; sys.exit(42)"],
            capture_output=True, text=True, timeout=10
        )
        assert result.returncode == 42

    def test_run_sets_import_mode_env_var(self):
        """P3-R1: pubrun run --mode X sets PUBRUN_IMPORT_MODE=X and PUBRUN_RUN_MODE_OVERRIDE=X in child."""
        result = subprocess.run(
            [
                PYTHON, "-m", "pubrun", "run", "--mode", "nopatch", "--",
                PYTHON, "-c",
                "import json, os; print(json.dumps({"
                "'import_mode': os.environ.get('PUBRUN_IMPORT_MODE', ''), "
                "'override': os.environ.get('PUBRUN_RUN_MODE_OVERRIDE', '')}))",
            ],
            capture_output=True, text=True, timeout=10,
        )
        assert result.returncode == 0, f"stderr: {result.stderr}"
        data = json.loads(result.stdout.strip())
        assert data["import_mode"] == "nopatch"
        assert data["override"] == "nopatch"

    def test_run_mode_minimal_overrides_explicit_pubrun_full(self, tmp_path):
        script = (
            "import json\n"
            "import pubrun.full as pubrun\n"
            "from pubrun._bootstrap import get_import_metadata\n"
            "meta = get_import_metadata()\n"
            "print(json.dumps({\n"
            "    'active': pubrun.get_current_run() is not None,\n"
            "    'selected_mode': meta['selected_mode'],\n"
            "    'selected_by': meta['selected_by'],\n"
            "    'selected_source': meta['selected_source'],\n"
            "    'conflicts_detected': meta['conflicts_detected'],\n"
            "}))\n"
        )
        result = subprocess.run(
            [PYTHON, "-m", "pubrun", "run", "--mode", "minimal", "--", PYTHON, "-c", script],
            capture_output=True, text=True, timeout=20, cwd=str(tmp_path),
            env={**os.environ, "PUBRUN_IMPORT_MODE": "", "PUBRUN_RUN_MODE_OVERRIDE": ""},
        )
        assert result.returncode == 0, f"stderr: {result.stderr}"
        data = json.loads(result.stdout.strip().splitlines()[-1])
        assert data["active"] is False
        assert data["selected_mode"] == "minimal"
        assert data["selected_by"] == "cli:pubrun run --mode"
        assert data["selected_source"] == "cli:pubrun run --mode"
        assert data["conflicts_detected"] == 0

    def test_run_mode_noconsole_overrides_explicit_pubrun_full(self, tmp_path):
        script = (
            "import json\n"
            "import pubrun.full as pubrun\n"
            "from pubrun._bootstrap import get_import_metadata, get_selected_behavior\n"
            "run = pubrun.get_current_run()\n"
            "rd = str(run.run_dir) if run is not None else None\n"
            "if run is not None:\n"
            "    pubrun.stop()\n"
            "console_mode = json.load(open(rd + '/manifest.json'))['console']['capture_mode'] if rd else None\n"
            "meta = get_import_metadata()\n"
            "beh = get_selected_behavior() or {}\n"
            "print(json.dumps({\n"
            "    'active': run is not None,\n"
            "    'selected_mode': meta['selected_mode'],\n"
            "    'selected_source': meta['selected_source'],\n"
            "    'patch_console': beh.get('patch_console'),\n"
            "    'console_mode': console_mode,\n"
            "}))\n"
        )
        result = subprocess.run(
            [PYTHON, "-m", "pubrun", "run", "--mode", "noconsole", "--", PYTHON, "-c", script],
            capture_output=True, text=True, timeout=25, cwd=str(tmp_path),
            env={**os.environ, "PUBRUN_IMPORT_MODE": "", "PUBRUN_RUN_MODE_OVERRIDE": ""},
        )
        assert result.returncode == 0, f"stderr: {result.stderr}"
        data = json.loads(result.stdout.strip().splitlines()[-1])
        assert data["active"] is True
        assert data["selected_mode"] == "noconsole"
        assert data["selected_source"] == "cli:pubrun run --mode"
        assert data["patch_console"] is False
        assert data["console_mode"] == "off"

    def test_plain_pubrun_import_mode_loses_to_explicit_pubrun_full(self, tmp_path):
        script = (
            "import json\n"
            "import pubrun.full as pubrun\n"
            "from pubrun._bootstrap import get_import_metadata\n"
            "run = pubrun.get_current_run()\n"
            "if run is not None:\n"
            "    pubrun.stop()\n"
            "meta = get_import_metadata()\n"
            "print(json.dumps({\n"
            "    'active': run is not None,\n"
            "    'selected_mode': meta['selected_mode'],\n"
            "    'selected_source': meta['selected_source'],\n"
            "}))\n"
        )
        result = subprocess.run(
            [PYTHON, "-c", script],
            capture_output=True, text=True, timeout=25, cwd=str(tmp_path),
            env={
                **os.environ,
                "PUBRUN_IMPORT_MODE": "minimal",
                "PUBRUN_RUN_MODE_OVERRIDE": "",
            },
        )
        assert result.returncode == 0, f"stderr: {result.stderr}"
        data = json.loads(result.stdout.strip().splitlines()[-1])
        assert data["active"] is True
        assert data["selected_mode"] == "full"
        assert data["selected_source"] == "explicit"

    def test_invalid_run_mode_override_ignored_for_explicit_pubrun_full(self, tmp_path):
        script = (
            "import json\n"
            "import pubrun.full as pubrun\n"
            "from pubrun._bootstrap import get_import_metadata\n"
            "run = pubrun.get_current_run()\n"
            "if run is not None:\n"
            "    pubrun.stop()\n"
            "meta = get_import_metadata()\n"
            "print(json.dumps({\n"
            "    'active': run is not None,\n"
            "    'selected_mode': meta['selected_mode'],\n"
            "    'selected_source': meta['selected_source'],\n"
            "}))\n"
        )
        result = subprocess.run(
            [PYTHON, "-c", script],
            capture_output=True, text=True, timeout=25, cwd=str(tmp_path),
            env={
                **os.environ,
                "PUBRUN_IMPORT_MODE": "",
                "PUBRUN_RUN_MODE_OVERRIDE": "bogus",
            },
        )
        assert result.returncode == 0, f"stderr: {result.stderr}"
        data = json.loads(result.stdout.strip().splitlines()[-1])
        assert data["active"] is True
        assert data["selected_mode"] == "full"
        assert data["selected_source"] == "explicit"

    @pytest.mark.parametrize(
        "import_block",
        [
            "import pubrun.full as pubrun",
            "import pubrun\nimport pubrun.full\nimport pubrun.noconsole",
            "import pubrun.full\nimport pubrun.nopatch",
        ],
    )
    def test_run_mode_override_no_conflict_under_error_policy(self, import_block, tmp_path):
        script = (
            "import json, warnings\n"
            "with warnings.catch_warnings(record=True) as w:\n"
            "    warnings.simplefilter('always')\n"
            + "\n".join(f"    {line}" for line in import_block.splitlines())
            + "\n"
            "from pubrun._bootstrap import get_import_metadata\n"
            "meta = get_import_metadata()\n"
            "print(json.dumps({\n"
            "    'warnings': [str(x.message) for x in w],\n"
            "    'selected_mode': meta['selected_mode'],\n"
            "    'selected_source': meta['selected_source'],\n"
            "    'conflicts_detected': meta['conflicts_detected'],\n"
            "}))\n"
        )
        result = subprocess.run(
            [PYTHON, "-m", "pubrun", "run", "--mode", "minimal", "--", PYTHON, "-c", script],
            capture_output=True, text=True, timeout=25, cwd=str(tmp_path),
            env={
                **os.environ,
                "PUBRUN_IMPORT_MODE": "",
                "PUBRUN_RUN_MODE_OVERRIDE": "",
                "PUBRUN_IMPORT_CONFLICT": "error",
            },
        )
        assert result.returncode == 0, f"stderr: {result.stderr}"
        data = json.loads(result.stdout.strip().splitlines()[-1])
        assert data["warnings"] == []
        assert data["selected_mode"] == "minimal"
        assert data["selected_source"] == "cli:pubrun run --mode"
        assert data["conflicts_detected"] == 0

    def test_run_no_command_exits_1(self):
        result = subprocess.run(
            [PYTHON, "-m", "pubrun", "run", "--mode", "minimal"],
            capture_output=True, text=True, timeout=10
        )
        assert result.returncode == 1
        assert "No command specified" in result.stderr

    def test_run_bad_command_exits_127(self):
        result = subprocess.run(
            [PYTHON, "-m", "pubrun", "run", "--", "nonexistent_binary_xyz"],
            capture_output=True, text=True, timeout=10
        )
        assert result.returncode == 127
        assert "Cannot execute command" in result.stderr

    @pytest.mark.skipif(sys.platform == "win32", reason="Signal-based exit codes differ on Windows")
    def test_run_signal_killed_child_returns_128_plus_n(self):
        """P2-E10: Child killed by signal should return 128+N exit code."""
        # SIGKILL = 9, so expect exit 137
        script = f"import os, signal; os.kill(os.getpid(), signal.SIGKILL)"
        result = subprocess.run(
            [PYTHON, "-m", "pubrun", "run", "--", PYTHON, "-c", script],
            capture_output=True, text=True, timeout=10
        )
        assert result.returncode == 137  # 128 + 9

    @pytest.mark.skipif(sys.platform == "win32", reason="Windows doesn't raise PermissionError for non-executable files")
    def test_run_permission_error(self, tmp_path):
        """P2-E1: Non-executable command gets clean error, not traceback."""
        # Create a file that exists but isn't executable
        non_exec = tmp_path / "not_executable.sh"
        non_exec.write_text("#!/bin/sh\necho hi", encoding="utf-8")
        non_exec.chmod(0o644)
        result = subprocess.run(
            [PYTHON, "-m", "pubrun", "run", "--", str(non_exec)],
            capture_output=True, text=True, timeout=10
        )
        assert result.returncode == 127
        assert "Cannot execute command" in result.stderr


# =============================================================================
# Hook suppression tests (nopatch/quiet must NOT install global hooks)
# =============================================================================

class TestHookSuppression:
    """Verify that nopatch and quiet modes suppress global hooks."""

    def test_nopatch_no_subprocess_spy(self, tmp_path):
        """nopatch mode does not monkey-patch subprocess.Popen."""
        script = f"""
import os, sys, json, subprocess
os.chdir({str(tmp_path)!r})
os.environ.pop('PUBRUN_RUN_MODE_OVERRIDE', None)
os.environ['PUBRUN_IMPORT_MODE'] = 'nopatch'
# Clear cached modules
for mod in list(sys.modules.keys()):
    if 'pubrun' in mod:
        del sys.modules[mod]
import pubrun
# Check if Popen is patched by looking for the spy wrapper
from pubrun.capture.subprocesses import SubprocessSpy
print(json.dumps({{"spy_installed": SubprocessSpy._installed}}))
pubrun.stop()
"""
        result = subprocess.run(
            [PYTHON, "-c", script],
            capture_output=True, text=True, timeout=15
        )
        assert result.returncode == 0, f"stderr: {result.stderr}"
        data = json.loads(result.stdout.strip())
        assert data["spy_installed"] is False

    def test_nopatch_installs_signal_handlers(self, tmp_path):
        """nopatch mode does install signal handlers."""
        script = f"""
import os, sys, json
os.chdir({str(tmp_path)!r})
os.environ.pop('PUBRUN_RUN_MODE_OVERRIDE', None)
os.environ['PUBRUN_IMPORT_MODE'] = 'nopatch'
for mod in list(sys.modules.keys()):
    if 'pubrun' in mod:
        del sys.modules[mod]
import pubrun
run = pubrun.get_current_run()
has_signal_capture = run.signal_capture is not None if run else False
print(json.dumps({{"signal_capture": has_signal_capture}}))
pubrun.stop()
"""
        result = subprocess.run(
            [PYTHON, "-c", script],
            capture_output=True, text=True, timeout=15
        )
        assert result.returncode == 0, f"stderr: {result.stderr}"
        data = json.loads(result.stdout.strip())
        assert data["signal_capture"] is True

    def test_nopatch_no_console_tee(self, tmp_path):
        """nopatch mode does not wrap sys.stdout/stderr."""
        script = f"""
import os, sys, json
os.chdir({str(tmp_path)!r})
os.environ.pop('PUBRUN_RUN_MODE_OVERRIDE', None)
os.environ['PUBRUN_IMPORT_MODE'] = 'nopatch'
for mod in list(sys.modules.keys()):
    if 'pubrun' in mod:
        del sys.modules[mod]
import pubrun
# stdout should still be the original, not a TqdmSafeTee wrapper
is_original = type(sys.stdout).__name__ != 'TqdmSafeTee'
print(json.dumps({{"stdout_original": is_original}}))
pubrun.stop()
"""
        result = subprocess.run(
            [PYTHON, "-c", script],
            capture_output=True, text=True, timeout=15
        )
        assert result.returncode == 0, f"stderr: {result.stderr}"
        data = json.loads(result.stdout.strip())
        assert data["stdout_original"] is True

    def test_minimal_no_hooks_no_start(self, tmp_path):
        """minimal mode: no auto-start AND no hooks."""
        script = f"""
import os, sys, json
os.chdir({str(tmp_path)!r})
os.environ.pop('PUBRUN_RUN_MODE_OVERRIDE', None)
os.environ['PUBRUN_IMPORT_MODE'] = 'minimal'
for mod in list(sys.modules.keys()):
    if 'pubrun' in mod:
        del sys.modules[mod]
import pubrun
from pubrun.capture.subprocesses import SubprocessSpy
print(json.dumps({{
    "active": pubrun.get_current_run() is not None,
    "spy_installed": SubprocessSpy._installed,
    "stdout_original": type(sys.stdout).__name__ != 'TqdmSafeTee'
}}))
"""
        result = subprocess.run(
            [PYTHON, "-c", script],
            capture_output=True, text=True, timeout=15
        )
        assert result.returncode == 0, f"stderr: {result.stderr}"
        data = json.loads(result.stdout.strip())
        assert data["active"] is False
        assert data["spy_installed"] is False
        assert data["stdout_original"] is True

    def test_auto_mode_installs_hooks(self, tmp_path):
        """auto mode (default) DOES install hooks — control test."""
        script = f"""
import os, sys, json
os.chdir({str(tmp_path)!r})
os.environ.pop('PUBRUN_RUN_MODE_OVERRIDE', None)
os.environ['PUBRUN_IMPORT_MODE'] = 'auto'
for mod in list(sys.modules.keys()):
    if 'pubrun' in mod:
        del sys.modules[mod]
import pubrun
from pubrun.capture.subprocesses import SubprocessSpy
run = pubrun.get_current_run()
has_signal = run.signal_capture is not None if run else False
print(json.dumps({{
    "active": run is not None,
    "spy_installed": SubprocessSpy._installed,
    "signal_capture": has_signal
}}))
pubrun.stop()
"""
        result = subprocess.run(
            [PYTHON, "-c", script],
            capture_output=True, text=True, timeout=15
        )
        assert result.returncode == 0, f"stderr: {result.stderr}"
        data = json.loads(result.stdout.strip())
        assert data["active"] is True
        assert data["spy_installed"] is True
        assert data["signal_capture"] is True


# =============================================================================
# Phase 4: Namespaced import mode subprocess tests
# =============================================================================

class TestNamespacedImportModes:
    """Subprocess tests verifying `import pubrun.X as pubrun` works."""

    def test_noauto_does_not_auto_start(self, tmp_path):
        script = f"""
import os, sys, json
os.chdir({str(tmp_path)!r})
import pubrun.noauto as pubrun
run = pubrun.get_current_run()
print(json.dumps({{"active": run is not None}}))
"""
        result = subprocess.run(
            [PYTHON, "-c", script],
            capture_output=True, text=True, timeout=15
        )
        assert result.returncode == 0, f"stderr: {result.stderr}"
        data = json.loads(result.stdout.strip())
        assert data["active"] is False

    def test_noauto_allows_explicit_start(self, tmp_path):
        script = f"""
import os, sys, json
os.chdir({str(tmp_path)!r})
import pubrun.noauto as pubrun
pubrun.start()
run = pubrun.get_current_run()
print(json.dumps({{"active": run is not None}}))
pubrun.stop()
"""
        result = subprocess.run(
            [PYTHON, "-c", script],
            capture_output=True, text=True, timeout=15
        )
        assert result.returncode == 0, f"stderr: {result.stderr}"
        data = json.loads(result.stdout.strip())
        assert data["active"] is True

    def test_minimal_does_not_auto_start(self, tmp_path):
        script = f"""
import os, sys, json
os.chdir({str(tmp_path)!r})
import pubrun.minimal as pubrun
run = pubrun.get_current_run()
print(json.dumps({{"active": run is not None}}))
"""
        result = subprocess.run(
            [PYTHON, "-c", script],
            capture_output=True, text=True, timeout=15
        )
        assert result.returncode == 0, f"stderr: {result.stderr}"
        data = json.loads(result.stdout.strip())
        assert data["active"] is False

    def test_auto_does_auto_start(self, tmp_path):
        script = f"""
import os, sys, json
os.chdir({str(tmp_path)!r})
import pubrun.auto as pubrun
run = pubrun.get_current_run()
print(json.dumps({{"active": run is not None}}))
if run:
    pubrun.stop()
"""
        result = subprocess.run(
            [PYTHON, "-c", script],
            capture_output=True, text=True, timeout=15
        )
        assert result.returncode == 0, f"stderr: {result.stderr}"
        data = json.loads(result.stdout.strip())
        assert data["active"] is True

    def test_nopatch_auto_starts(self, tmp_path):
        script = f"""
import os, sys, json
os.chdir({str(tmp_path)!r})
import pubrun.nopatch as pubrun
run = pubrun.get_current_run()
print(json.dumps({{"active": run is not None}}))
if run:
    pubrun.stop()
"""
        result = subprocess.run(
            [PYTHON, "-c", script],
            capture_output=True, text=True, timeout=15
        )
        assert result.returncode == 0, f"stderr: {result.stderr}"
        data = json.loads(result.stdout.strip())
        assert data["active"] is True

    def test_root_import_still_works(self, tmp_path):
        """Plain import pubrun still auto-starts (backward compat)."""
        script = f"""
import os, sys, json
os.chdir({str(tmp_path)!r})
import pubrun
run = pubrun.get_current_run()
print(json.dumps({{"active": run is not None}}))
if run:
    pubrun.stop()
"""
        result = subprocess.run(
            [PYTHON, "-c", script],
            capture_output=True, text=True, timeout=15
        )
        assert result.returncode == 0, f"stderr: {result.stderr}"
        data = json.loads(result.stdout.strip())
        assert data["active"] is True

    def test_legacy_auto_start_false_still_works(self, tmp_path):
        """PUBRUN_AUTO_START=false still prevents auto-start."""
        script = f"""
import os, sys, json
os.chdir({str(tmp_path)!r})
import pubrun
run = pubrun.get_current_run()
print(json.dumps({{"active": run is not None}}))
"""
        result = subprocess.run(
            [PYTHON, "-c", script],
            capture_output=True, text=True, timeout=15,
            env={
                **os.environ,
                "PUBRUN_AUTO_START": "false",
                "PUBRUN_IMPORT_MODE": "",
                "PUBRUN_RUN_MODE_OVERRIDE": "",
            }
        )
        assert result.returncode == 0, f"stderr: {result.stderr}"
        data = json.loads(result.stdout.strip())
        assert data["active"] is False


# =============================================================================
# Mode-alias public API parity (regression: mode submodules must expose the
# SAME public names as the top-level `import pubrun`).
# =============================================================================

class TestModeAliasApiParity:
    """`import pubrun.<mode> as pubrun` must expose the full public API.

    Previously the mode submodules only rebound 8 of the 12 public names,
    so `pubrun.print` / `pubrun.open` / `pubrun.report` / `pubrun.artifact` /
    `pubrun.subprocess` / `pubrun.popen` raised AttributeError via the alias
    (while top-level `import pubrun` worked). These run in subprocesses because
    import mode is process-global.
    """

    _PUBLIC = [
        "start", "stop", "annotate", "phase", "diff", "audit_run",
        "tracked_run", "get_current_run", "report", "artifact",
        "print", "open", "register_file", "register_input", "register_output",
        "subprocess", "popen",
    ]

    @staticmethod
    def _clean_env():
        env = {
            **os.environ,
            "PUBRUN_IMPORT_MODE": "",
            "PUBRUN_AUTO_START": "",
            "PUBRUN_RUN_MODE_OVERRIDE": "",
        }
        src_dir = pathlib.Path(__file__).resolve().parents[1] / "src"
        if src_dir.is_dir():
            existing = env.get("PYTHONPATH", "")
            env["PYTHONPATH"] = f"{src_dir}{os.pathsep}{existing}" if existing else str(src_dir)
        return env

    @pytest.mark.parametrize("mode", ["auto", "noauto", "nopatch", "noconsole", "minimal", "full"])
    def test_mode_alias_exposes_full_api(self, mode, tmp_path):
        names = json.dumps(self._PUBLIC)
        script = f"""
import json, sys
import pubrun.{mode} as pubrun
import pubrun as base
names = {names}
missing_alias = [n for n in names if not hasattr(pubrun, n)]
missing_base = [n for n in names if not hasattr(base, n)]
mismatched = [
    n for n in names
    if n != "report"
    and hasattr(pubrun, n)
    and hasattr(base, n)
    and getattr(base, n) is not getattr(pubrun, n)
]
file_io_loaded = "pubrun.capture.file_io" in sys.modules
print(json.dumps({{
    "missing_alias": missing_alias,
    "missing_base": missing_base,
    "mismatched": mismatched,
    "file_io_loaded": file_io_loaded,
}}))
try:
    if pubrun.get_current_run():
        pubrun.stop()
except Exception:
    pass
"""
        result = subprocess.run(
            [PYTHON, "-c", script],
            capture_output=True, text=True, timeout=20, cwd=str(tmp_path),
            env=self._clean_env(),
        )
        assert result.returncode == 0, f"stderr: {result.stderr}"
        data = json.loads(result.stdout.strip().splitlines()[-1])
        assert data["missing_alias"] == [], f"{mode} alias missing: {data['missing_alias']}"
        assert data["missing_base"] == [], f"{mode} parent pubrun missing: {data['missing_base']}"
        assert data["mismatched"] == [], f"{mode} parent/alias mismatch: {data['mismatched']}"
        assert data["file_io_loaded"] is False, f"{mode} eagerly imported pubrun.capture.file_io"

    def test_noconsole_alias_print_captures_to_stdout_log(self, tmp_path):
        """pubrun.print via the noconsole alias records to stdout.log even
        though console streams are not wrapped."""
        script = """
import glob, sys
import pubrun.noconsole as pubrun
pubrun.print("captured-line-parity-check")
pubrun.stop()
logs = glob.glob("runs/pubrun-*/stdout.log")
ok = bool(logs) and "captured-line-parity-check" in open(logs[0]).read()
print("CAPTURE_OK" if ok else "CAPTURE_FAIL")
"""
        result = subprocess.run(
            [PYTHON, "-c", script],
            capture_output=True, text=True, timeout=20, cwd=str(tmp_path),
            env=self._clean_env(),
        )
        assert result.returncode == 0, f"stderr: {result.stderr}"
        assert "CAPTURE_OK" in result.stdout, f"stdout: {result.stdout}"

    def test_nopatch_file_registration_lazy_unpatched_and_recorded(self, tmp_path):
        """pubrun.nopatch supports external input/output registration without
        eagerly importing pubrun.capture.file_io or patching builtins.open."""
        in_path = tmp_path / "external_in.csv"
        out_path = tmp_path / "external_out.csv"
        in_path.write_text("col\n1\n", encoding="utf-8")
        script = f"""
import builtins, glob, json, sys
from pathlib import Path

orig_open = builtins.open
import pubrun.nopatch as pubrun

file_io_loaded_after_import = "pubrun.capture.file_io" in sys.modules
open_unpatched_after_import = builtins.open is orig_open

in_path = Path({str(in_path)!r})
out_path = Path({str(out_path)!r})

pubrun.register_input(in_path, label="raw_input")
with builtins.open(out_path, "w", encoding="utf-8") as fh:
    fh.write("result\\n42\\n")
pubrun.register_output(out_path, label="derived_output")
pubrun.stop()

open_unpatched_after_stop = builtins.open is orig_open
manifests = glob.glob("runs/pubrun-*/manifest.json")
assert len(manifests) == 1, f"expected 1 manifest, got {{manifests}}"
manifest = json.loads(Path(manifests[0]).read_text(encoding="utf-8"))
data_files = manifest.get("data_files", {{}})
print(json.dumps({{
    "file_io_loaded_after_import": file_io_loaded_after_import,
    "open_unpatched_after_import": open_unpatched_after_import,
    "open_unpatched_after_stop": open_unpatched_after_stop,
    "inputs": data_files.get("inputs", []),
    "outputs": data_files.get("outputs", []),
}}))
"""
        result = subprocess.run(
            [PYTHON, "-c", script],
            capture_output=True, text=True, timeout=20, cwd=str(tmp_path),
            env=self._clean_env(),
        )
        assert result.returncode == 0, f"stderr: {result.stderr}"
        data = json.loads(result.stdout.strip().splitlines()[-1])
        assert data["file_io_loaded_after_import"] is False
        assert data["open_unpatched_after_import"] is True
        assert data["open_unpatched_after_stop"] is True
        assert len(data["inputs"]) == 1
        assert data["inputs"][0]["label"] == "raw_input"
        assert data["inputs"][0]["registration_source"] == "register_input"
        assert data["inputs"][0]["path"] == os.path.abspath(str(in_path))
        assert len(data["outputs"]) == 1
        assert data["outputs"][0]["label"] == "derived_output"
        assert data["outputs"][0]["registration_source"] == "register_output"
        assert data["outputs"][0]["path"] == os.path.abspath(str(out_path))

    def test_minimal_file_registration_lazy_unpatched_and_recorded(self, tmp_path):
        """pubrun.minimal supports explicit start/stop external file registration
        without eagerly importing pubrun.capture.file_io or patching builtins.open."""
        in_path = tmp_path / "minimal_in.txt"
        out_path = tmp_path / "minimal_out.txt"
        in_path.write_text("alpha\n", encoding="utf-8")
        script = f"""
import builtins, glob, json, sys
from pathlib import Path

orig_open = builtins.open
import pubrun.minimal as pubrun

file_io_loaded_after_import = "pubrun.capture.file_io" in sys.modules
open_unpatched_after_import = builtins.open is orig_open
active_after_import = pubrun.get_current_run() is not None

pubrun.start()
file_io_loaded_after_start = "pubrun.capture.file_io" in sys.modules
open_unpatched_after_start = builtins.open is orig_open

in_path = Path({str(in_path)!r})
out_path = Path({str(out_path)!r})

pubrun.register_input(in_path, label="minimal_input")
pubrun.register_output(out_path, label="minimal_output", defer=True)
with builtins.open(out_path, "w", encoding="utf-8") as fh:
    fh.write("beta\\n")
pubrun.stop()

open_unpatched_after_stop = builtins.open is orig_open
manifests = glob.glob("runs/pubrun-*/manifest.json")
assert len(manifests) == 1, f"expected 1 manifest, got {{manifests}}"
manifest = json.loads(Path(manifests[0]).read_text(encoding="utf-8"))
data_files = manifest.get("data_files", {{}})
print(json.dumps({{
    "file_io_loaded_after_import": file_io_loaded_after_import,
    "open_unpatched_after_import": open_unpatched_after_import,
    "active_after_import": active_after_import,
    "file_io_loaded_after_start": file_io_loaded_after_start,
    "open_unpatched_after_start": open_unpatched_after_start,
    "open_unpatched_after_stop": open_unpatched_after_stop,
    "inputs": data_files.get("inputs", []),
    "outputs": data_files.get("outputs", []),
}}))
"""
        result = subprocess.run(
            [PYTHON, "-c", script],
            capture_output=True, text=True, timeout=20, cwd=str(tmp_path),
            env=self._clean_env(),
        )
        assert result.returncode == 0, f"stderr: {result.stderr}"
        data = json.loads(result.stdout.strip().splitlines()[-1])
        assert data["file_io_loaded_after_import"] is False
        assert data["open_unpatched_after_import"] is True
        assert data["active_after_import"] is False
        assert data["file_io_loaded_after_start"] is False
        assert data["open_unpatched_after_start"] is True
        assert data["open_unpatched_after_stop"] is True
        assert len(data["inputs"]) == 1
        assert data["inputs"][0]["label"] == "minimal_input"
        assert data["inputs"][0]["registration_source"] == "register_input"
        assert data["inputs"][0]["path"] == os.path.abspath(str(in_path))
        assert len(data["outputs"]) == 1
        assert data["outputs"][0]["label"] == "minimal_output"
        assert data["outputs"][0]["registration_source"] == "register_output"
        assert data["outputs"][0]["registered_before_creation"] is True
        assert data["outputs"][0]["path"] == os.path.abspath(str(out_path))


class TestModeModuleBackgroundCapture:
    """Every import mode completes hardware, host, and filesystem capture.

    Regression for the auto-starting mode modules starting the ``pubrun-hw``
    background thread before ``pubrun._run_lock`` was bound, which left the
    manifest's ``hardware``/``host``/``filesystem`` sections ``pending`` and,
    with ``[capture.hardware].depth = "off"``, disabled auto-start entirely.
    Plain ``pubrun`` is a control that was never affected.
    """

    @staticmethod
    def _env():
        env = {
            k: v for k, v in os.environ.items()
            if k not in ("PUBRUN_IMPORT_MODE", "PUBRUN_AUTO_START", "PUBRUN_RUN_MODE_OVERRIDE")
        }
        src_dir = pathlib.Path(__file__).resolve().parents[1] / "src"
        existing = env.get("PYTHONPATH", "")
        env["PYTHONPATH"] = f"{src_dir}{os.pathsep}{existing}" if existing else str(src_dir)
        return env

    def _run(self, script, tmp_path):
        return subprocess.run(
            [PYTHON, "-c", script],
            capture_output=True, text=True, timeout=60,
            cwd=str(tmp_path), env=self._env(),
        )

    @pytest.mark.parametrize("module", [
        "pubrun", "pubrun.auto", "pubrun.full", "pubrun.noauto",
        "pubrun.nopatch", "pubrun.noconsole", "pubrun.minimal",
    ])
    def test_mode_module_captures_hardware(self, module, tmp_path):
        script = f"""
import json, os, time
import {module} as pubrun
run = pubrun.get_current_run() or pubrun.start()
manifest_path = os.path.join(str(run.run_dir), "manifest.json")
deadline = time.monotonic() + 20
while time.monotonic() < deadline:
    try:
        with open(manifest_path) as fh:
            status = json.load(fh)["hardware"]["capture_state"]["status"]
    except (OSError, ValueError, KeyError):
        status = "pending"
    if status != "pending":
        break
    time.sleep(0.1)
pubrun.stop()
with open(manifest_path) as fh:
    m = json.load(fh)
print(json.dumps({{
    "hardware": m["hardware"]["capture_state"]["status"],
    "has_cpu": "cpu" in m["hardware"],
    "host": m["host"]["capture_state"]["status"],
}}))
"""
        result = self._run(script, tmp_path)
        assert result.returncode == 0, f"stderr: {result.stderr}"
        assert "Exception in thread pubrun-hw" not in result.stderr
        assert "cannot import name '_run_lock'" not in result.stderr
        data = json.loads(result.stdout.strip().splitlines()[-1])
        assert data["hardware"] != "pending"
        assert data["has_cpu"] is True
        assert data["host"] != "pending"

    @pytest.mark.parametrize("module", [
        "pubrun", "pubrun.auto", "pubrun.full", "pubrun.nopatch", "pubrun.noconsole",
    ])
    def test_mode_module_autostarts_with_hardware_off(self, module, tmp_path):
        (tmp_path / ".pubrun.toml").write_text('[capture.hardware]\ndepth = "off"\n')
        script = f"""
import json, os
import {module} as pubrun
run = pubrun.get_current_run()
out = {{"active": run is not None}}
if run is not None:
    manifest_path = os.path.join(str(run.run_dir), "manifest.json")
    pubrun.stop()
    with open(manifest_path) as fh:
        out["hardware"] = json.load(fh)["hardware"]["capture_state"]["status"]
print(json.dumps(out))
"""
        result = self._run(script, tmp_path)
        assert result.returncode == 0, f"stderr: {result.stderr}"
        data = json.loads(result.stdout.strip().splitlines()[-1])
        assert data["active"] is True, f"stderr: {result.stderr}"
        assert "auto-start failed" not in result.stderr
        assert "cannot import name '_run_lock'" not in result.stderr
        assert data["hardware"] == "suppressed"


class TestModePep561AndColdStart:
    """PEP 561 export/dir/version/commit parity and cold-start import isolation."""

    @staticmethod
    def _clean_env():
        env = {
            k: v for k, v in os.environ.items()
            if k not in ("PUBRUN_IMPORT_MODE", "PUBRUN_AUTO_START", "PUBRUN_RUN_MODE_OVERRIDE")
        }
        src_dir = pathlib.Path(__file__).resolve().parents[1] / "src"
        existing = env.get("PYTHONPATH", "")
        env["PYTHONPATH"] = f"{src_dir}{os.pathsep}{existing}" if existing else str(src_dir)
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        return env

    @pytest.mark.parametrize("mode", ["auto", "full", "noauto", "nopatch", "noconsole", "minimal"])
    def test_mode_submodules_all_dir_version_commit_parity(self, mode, tmp_path):
        script = f"""
import json
import pubrun.{mode} as mod
import pubrun as base

base_all = list(base.__all__)
mod_all = list(mod.__all__)
mod_dir = dir(mod)

v_mod = mod.__version__
v_base = base.__version__
c_mod = mod.__commit__
c_base = base.__commit__

# __version__ and __commit__ must remain dynamic via PEP 562 (not pinned in mod.__dict__).
version_in_dict = "__version__" in mod.__dict__
commit_in_dict = "__commit__" in mod.__dict__

unknown_raised = False
try:
    getattr(mod, "definitely_not_a_real_pubrun_symbol")
except AttributeError:
    unknown_raised = True

# Resetting commit cache on pubrun must remain visible through the mode alias.
base._reset_commit_cache()
c_mod_after_reset = mod.__commit__

print(json.dumps({{
    "base_all_len": len(base_all),
    "mod_all_len": len(mod_all),
    "all_equal": set(mod_all) == set(base_all),
    "paused_in_all": "paused" in mod_all,
    "all_in_dir": set(mod_all).issubset(set(mod_dir)),
    "version_in_dir": "__version__" in mod_dir,
    "commit_in_dir": "__commit__" in mod_dir,
    "version_equal": isinstance(v_mod, str) and v_mod == v_base,
    "commit_equal": c_mod == c_base and c_mod_after_reset == base.__commit__,
    "version_in_dict": version_in_dict,
    "commit_in_dict": commit_in_dict,
    "unknown_raised": unknown_raised,
}}))
if mod.get_current_run() is not None:
    mod.stop()
"""
        result = subprocess.run(
            [PYTHON, "-c", script],
            capture_output=True, text=True, timeout=30,
            cwd=str(tmp_path), env=self._clean_env(),
        )
        assert result.returncode == 0, f"stderr: {result.stderr}"
        data = json.loads(result.stdout.strip().splitlines()[-1])
        assert data["base_all_len"] == 20
        assert data["mod_all_len"] == 20
        assert data["all_equal"] is True
        assert data["paused_in_all"] is True
        assert data["all_in_dir"] is True
        assert data["version_in_dir"] is True
        assert data["commit_in_dir"] is True
        assert data["version_equal"] is True
        assert data["commit_equal"] is True
        assert data["version_in_dict"] is False
        assert data["commit_in_dict"] is False
        assert data["unknown_raised"] is True

    @pytest.mark.parametrize("mode", ["minimal", "noauto"])
    def test_cold_start_import_leaves_heavy_modules_unloaded(self, mode, tmp_path):
        script = f"""
import json, sys
import pubrun.{mode} as mod
active = mod.get_current_run() is not None
capture_mods = sorted(
    m for m in sys.modules if m == "pubrun.capture" or m.startswith("pubrun.capture.")
)
print(json.dumps({{
    "active": active,
    "importlib_metadata": "importlib.metadata" in sys.modules,
    "tracker": "pubrun.tracker" in sys.modules,
    "writer": "pubrun.writer" in sys.modules,
    "events": "pubrun.events" in sys.modules,
    "capture_mods": capture_mods,
}}))
"""
        result = subprocess.run(
            [PYTHON, "-c", script],
            capture_output=True, text=True, timeout=20,
            cwd=str(tmp_path), env=self._clean_env(),
        )
        assert result.returncode == 0, f"stderr: {result.stderr}"
        data = json.loads(result.stdout.strip().splitlines()[-1])
        assert data["active"] is False
        assert data["importlib_metadata"] is False
        assert data["tracker"] is False
        assert data["writer"] is False
        assert data["events"] is False
        assert data["capture_mods"] == []

    def test_packages_mode_off_keeps_packages_module_unloaded(self, tmp_path):
        script = f"""
import json, pathlib, sys
import pubrun.minimal as pubrun
run = pubrun.start(
    output_dir={str(tmp_path / 'runs')!r},
    capture={{"packages": {{"mode": "off"}}, "hardware": {{"depth": "off"}}}},
)
loaded_after_start = "pubrun.capture.packages" in sys.modules
run._finalize_state()
loaded_after_finalize = "pubrun.capture.packages" in sys.modules
pubrun.stop()
loaded_after_stop = "pubrun.capture.packages" in sys.modules
methods_path = pathlib.Path(run.run_dir) / "methods.md"
methods_exists = methods_path.is_file()
methods_text = methods_path.read_text(encoding="utf-8") if methods_exists else ""
print(json.dumps({{
    "loaded_after_start": loaded_after_start,
    "loaded_after_finalize": loaded_after_finalize,
    "loaded_after_stop": loaded_after_stop,
    "methods_exists": methods_exists,
    "methods_text": methods_text,
}}))
"""
        result = subprocess.run(
            [PYTHON, "-c", script],
            capture_output=True, text=True, timeout=20,
            cwd=str(tmp_path), env=self._clean_env(),
        )
        assert result.returncode == 0, f"stderr: {result.stderr}"
        data = json.loads(result.stdout.strip().splitlines()[-1])
        assert data["loaded_after_start"] is False
        assert data["loaded_after_finalize"] is False
        assert data["loaded_after_stop"] is False
        assert data["methods_exists"] is True
        assert "Package capture was disabled by configuration." in data["methods_text"]

    def test_report_methods_import_keeps_packages_and_metadata_unloaded(self, tmp_path):
        script = """
import json, sys
import pubrun.minimal
import pubrun.report.methods as methods

highlighted_manifest = {
    "packages": {"records": [{"name": "Scikit_Learn", "version": "1.5.0"}]}
}
non_highlighted_manifest = {
    "packages": {"records": [{"name": "zope.interface", "version": "6.0"}]}
}

highlighted = methods.extract_highlighted_packages(highlighted_manifest)
highlighted_report = methods.generate_report(highlighted_manifest)
non_highlighted_report = methods.generate_report(non_highlighted_manifest)

print(json.dumps({
    "packages_loaded": "pubrun.capture.packages" in sys.modules,
    "importlib_metadata_loaded": "importlib.metadata" in sys.modules,
    "highlighted": highlighted,
    "highlighted_report": highlighted_report,
    "non_highlighted_report": non_highlighted_report,
}))
"""
        result = subprocess.run(
            [PYTHON, "-c", script],
            capture_output=True, text=True, timeout=20,
            cwd=str(tmp_path), env=self._clean_env(),
        )
        assert result.returncode == 0, f"stderr: {result.stderr}"
        data = json.loads(result.stdout.strip().splitlines()[-1])
        assert data["packages_loaded"] is False
        assert data["importlib_metadata_loaded"] is False
        assert data["highlighted"] == ["scikit-learn (v1.5.0)"]
        assert "scikit-learn (v1.5.0)" in data["highlighted_report"]
        assert "zope-interface (v6.0)" in data["non_highlighted_report"]

    def test_downstream_mypy_strict_no_implicit_reexport_all_modes(self):
        mypy_check = subprocess.run(
            [PYTHON, "-m", "mypy", "--version"],
            capture_output=True, text=True, timeout=15,
        )
        if mypy_check.returncode != 0:
            pytest.skip("mypy not available in this environment")

        src_dir = pathlib.Path(__file__).resolve().parents[1] / "src"
        snippet = (
            "from typing import Optional; "
            "import pubrun.auto, pubrun.full, pubrun.noauto, pubrun.nopatch, "
            "pubrun.noconsole, pubrun.minimal; "
            "v1: str = pubrun.auto.__version__; c1: Optional[str] = pubrun.auto.__commit__; "
            "v2: str = pubrun.full.__version__; c2: Optional[str] = pubrun.full.__commit__; "
            "v3: str = pubrun.noauto.__version__; c3: Optional[str] = pubrun.noauto.__commit__; "
            "v4: str = pubrun.nopatch.__version__; c4: Optional[str] = pubrun.nopatch.__commit__; "
            "v5: str = pubrun.noconsole.__version__; c5: Optional[str] = pubrun.noconsole.__commit__; "
            "v6: str = pubrun.minimal.__version__; c6: Optional[str] = pubrun.minimal.__commit__; "
            "pubrun.noauto.start(); pubrun.noauto.stop()"
        )
        env = {**os.environ, "MYPYPATH": str(src_dir)}
        result = subprocess.run(
            [
                PYTHON,
                "-m",
                "mypy",
                "--config-file",
                os.devnull,
                "--strict",
                "--no-implicit-reexport",
                "--follow-imports=silent",
                "-c",
                snippet,
            ],
            capture_output=True,
            text=True,
            timeout=60,
            env=env,
        )
        assert result.returncode == 0, f"stdout: {result.stdout}\nstderr: {result.stderr}"
