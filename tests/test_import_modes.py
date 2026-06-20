"""Tests for import mode resolution, bootstrap state, and conflict detection."""
import os
import json
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

    def test_four_modes_defined(self):
        assert len(MODES) == 4
        assert VALID_MODES == {"auto", "noauto", "nopatch", "minimal"}

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
            env={**os.environ, "PUBRUN_AUTO_START": "true"}
        )
        assert result.returncode == 0, f"stderr: {result.stderr}"
        data = json.loads(result.stdout.strip())
        assert data["active"] is True


# =============================================================================
# Phase 3: Bootstrap state and conflict detection
# =============================================================================

@pytest.fixture(autouse=False)
def clean_bootstrap():
    """Reset bootstrap state before and after each test that uses it."""
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
        assert imports["selected_mode"] in ("auto", "noauto", "nopatch", "minimal")
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
        assert lock_data["import_mode"] in ("auto", "noauto", "nopatch", "minimal", None)
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
        """P3-R1: pubrun run --mode X actually sets PUBRUN_IMPORT_MODE=X in child."""
        result = subprocess.run(
            [PYTHON, "-m", "pubrun", "run", "--mode", "nopatch", "--",
             PYTHON, "-c", "import os; print(os.environ.get('PUBRUN_IMPORT_MODE', ''))"],
            capture_output=True, text=True, timeout=10
        )
        assert result.returncode == 0
        assert result.stdout.strip() == "nopatch"

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

    def test_noauto_as_pbr_alias(self, tmp_path):
        """The 'as pbr' alias convention works."""
        script = f"""
import os, sys, json
os.chdir({str(tmp_path)!r})
import pubrun.noauto as pbr
pbr.start()
run = pbr.get_current_run()
print(json.dumps({{"active": run is not None, "version": pbr.__version__}}))
pbr.stop()
"""
        result = subprocess.run(
            [PYTHON, "-c", script],
            capture_output=True, text=True, timeout=15
        )
        assert result.returncode == 0, f"stderr: {result.stderr}"
        data = json.loads(result.stdout.strip())
        assert data["active"] is True
        # Version should be a non-empty string (don't hardcode to avoid breakage on bump)
        assert isinstance(data["version"], str) and len(data["version"]) > 0

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
            env={**os.environ, "PUBRUN_AUTO_START": "false", "PUBRUN_IMPORT_MODE": ""}
        )
        assert result.returncode == 0, f"stderr: {result.stderr}"
        data = json.loads(result.stdout.strip())
        assert data["active"] is False
