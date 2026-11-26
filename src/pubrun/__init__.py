"""
pubrun - Zero-dependency Python execution provenance and telemetry capture.

Usage
-----
1. Auto-start (default)::

    import pubrun  # Tracking begins on import.

2. Explicit control::

    import pubrun

    tracker = pubrun.start(capture={"hardware": {"depth": "deep"}})
    pubrun.annotate("loading_datasets", batches=400, mode="lazy")

    with pubrun.phase("gradient_descent"):
        train_model()

    tracker.stop()

3. Decorator::

    @pubrun.audit_run(capture={"hardware": {"depth": "basic"}})
    def evaluate_node():
        ...

4. Import modes::

    import pubrun.auto as pubrun     # Explicit default: auto-start.
    import pubrun.full as pubrun     # Auto-start; force console capture on (capture everything).
    import pubrun.noauto as pubrun   # No auto-start; start() manually.
    import pubrun.nopatch as pubrun  # Auto-start, no global hooks.
    import pubrun.noconsole as pubrun # Auto-start, no console wrapping.
    import pubrun.minimal as pubrun  # No auto-start, no hooks.
"""
import sys
import threading as _threading

# -- Metadata ----------------------------------------------------------------
try:
    if sys.version_info >= (3, 8):
        from importlib.metadata import version as _pkg_version
    else:
        from importlib_metadata import version as _pkg_version
    __version__ = _pkg_version("pubrun")
except Exception:
    __version__ = "1.0.0"  # fallback for editable installs / dev

# Commit hash resolution is deferred via PEP 562 module __getattr__ so importing
# pubrun (especially pubrun.minimal / pubrun.noauto and installed wheels) never
# launches a git subprocess at import time. Installed wheels read version-checked
# build metadata without invoking git; verified pubrun source checkouts resolve
# live HEAD lazily with ownership validation and no stale COMMIT fallback.
_COMMIT_UNSET = object()
_cached_commit = _COMMIT_UNSET
_commit_lock = _threading.Lock()
_GIT_ENV_STRIP = ("GIT_DIR", "GIT_WORK_TREE", "GIT_COMMON_DIR", "GIT_INDEX_FILE")


def _is_valid_sha(value):
    if not isinstance(value, str):
        return False
    import re as _re
    return bool(_re.fullmatch(r"[0-9a-fA-F]{40}(?:[0-9a-fA-F]{24})?", value))


def _pyproject_declares_pubrun(pyproject_path):
    toml_mod = None
    if sys.version_info >= (3, 11):
        try:
            import tomllib as toml_mod
        except ImportError:
            toml_mod = None
    else:
        try:
            import tomli as toml_mod
        except ImportError:
            toml_mod = None

    if toml_mod is not None:
        with open(pyproject_path, "rb") as fh:
            data = toml_mod.load(fh)
        if not isinstance(data, dict):
            return False
        project = data.get("project")
        return isinstance(project, dict) and project.get("name") == "pubrun"

    # Fallback parser used only when neither tomllib nor tomli is importable.
    import re as _re
    in_project = False
    name_re = _re.compile(r"""^name\s*=\s*(?:"pubrun"|'pubrun')(?:\s*(?:#.*)?)?$""")
    with open(pyproject_path, "r", encoding="utf-8") as fh:
        for raw_line in fh:
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("["):
                if in_project:
                    return False
                header = line.split("#", 1)[0].strip()
                if header == "[project]":
                    in_project = True
                continue
            if in_project and name_re.match(line):
                return True
    return False


def _is_verified_source_checkout(pkg_dir):
    """Return repo root Path when pkg_dir is a verified pubrun source checkout."""
    try:
        from pathlib import Path
        pkg_path = Path(pkg_dir)
        if pkg_path.name != "pubrun" or pkg_path.parent.name != "src":
            return None
        repo_root = pkg_path.parent.parent
        if not (repo_root / ".git").exists():
            return None
        pyproject_path = repo_root / "pyproject.toml"
        if not pyproject_path.is_file():
            return None
        if not _pyproject_declares_pubrun(pyproject_path):
            return None
        return repo_root
    except Exception:
        return None


def _read_packaged_resource(filename):
    import importlib.resources as _pkg_resources
    if sys.version_info >= (3, 9):
        return _pkg_resources.files(__name__).joinpath(filename).read_text(encoding="utf-8")
    return _pkg_resources.read_text(__name__, filename, encoding="utf-8")


def _read_packaged_commit(expected_version):
    """Read build-stamped commit identity for an installed package without git."""
    try:
        raw_meta = _read_packaged_resource("_build_meta.json")
    except FileNotFoundError:
        # Legacy wheel fallback: COMMIT is consulted only when _build_meta.json is absent.
        try:
            raw_commit = _read_packaged_resource("COMMIT").strip()
            return raw_commit if _is_valid_sha(raw_commit) else None
        except Exception:
            return None
    except Exception:
        return None

    try:
        import json as _json
        meta = _json.loads(raw_meta)
    except Exception:
        return None

    if not isinstance(meta, dict):
        return None
    commit = meta.get("commit")
    meta_version = meta.get("version")
    if not _is_valid_sha(commit):
        return None
    if not isinstance(meta_version, str) or not meta_version.strip():
        return None
    if expected_version and meta_version != expected_version:
        return None
    return commit


def _resolve_checkout_commit(repo_root, timeout=1.0):
    """Resolve live HEAD in a verified pubrun source checkout with one bounded git call."""
    try:
        import os as _os
        import shutil as _shutil
        import subprocess as _sp

        clean_env = {k: v for k, v in _os.environ.items() if k not in _GIT_ENV_STRIP}
        git_exe = _shutil.which("git", path=clean_env.get("PATH"))
        if not git_exe:
            return None
        cmd = [git_exe, "-C", str(repo_root), "rev-parse", "--show-toplevel", "HEAD"]

        def _run_bounded():
            proc = _sp.Popen(
                cmd,
                stdin=_sp.DEVNULL,
                stdout=_sp.PIPE,
                stderr=_sp.PIPE,
                text=True,
                env=clean_env,
            )
            try:
                stdout, _ = proc.communicate(timeout=timeout)
                return proc.returncode, stdout
            except _sp.TimeoutExpired:
                if _os.name == "nt":
                    try:
                        taskkill = _os.path.join(
                            _os.environ.get("SystemRoot", r"C:\Windows"),
                            "System32",
                            "taskkill.exe",
                        )
                        if not _os.path.isfile(taskkill):
                            taskkill = "taskkill"
                        _sp.run(
                            [taskkill, "/F", "/T", "/PID", str(proc.pid)],
                            stdin=_sp.DEVNULL,
                            stdout=_sp.DEVNULL,
                            stderr=_sp.DEVNULL,
                            timeout=2.0,
                        )
                    except Exception:
                        pass
                try:
                    proc.kill()
                except Exception:
                    pass
                try:
                    proc.wait(timeout=0.5)
                except Exception:
                    pass
                return None, ""

        spy_mod = sys.modules.get("pubrun.capture.subprocesses")
        if spy_mod is not None and hasattr(spy_mod, "disable_spy"):
            with spy_mod.disable_spy():
                returncode, stdout = _run_bounded()
        else:
            returncode, stdout = _run_bounded()

        if returncode != 0:
            return None
        lines = [line.strip() for line in stdout.splitlines() if line.strip()]
        if len(lines) != 2:
            return None
        toplevel, head = lines
        if _os.path.normcase(_os.path.realpath(toplevel)) != _os.path.normcase(
            _os.path.realpath(str(repo_root))
        ):
            return None
        if not _is_valid_sha(head):
            return None
        return head
    except Exception:
        return None


def _resolve_commit():
    try:
        from pathlib import Path
        pkg_dir = Path(__file__).resolve().parent
    except Exception:
        return None
    repo_root = _is_verified_source_checkout(pkg_dir)
    if repo_root is not None:
        return _resolve_checkout_commit(repo_root)
    return _read_packaged_commit(__version__)


def _get_commit():
    global _cached_commit
    if _cached_commit is _COMMIT_UNSET:
        with _commit_lock:
            if _cached_commit is _COMMIT_UNSET:
                _cached_commit = _resolve_commit()
    return _cached_commit


def _reset_commit_cache():
    """Reset cached commit resolution state for deterministic test isolation."""
    global _cached_commit
    with _commit_lock:
        _cached_commit = _COMMIT_UNSET
        globals().pop("__commit__", None)


def __getattr__(name):
    if name == "__commit__":
        return _get_commit()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__():
    return sorted(set(globals()) | set(__all__))

# Publication name (matches the author's existing academic publication record so
# citations aggregate correctly). The full legal name appears in LICENSE/NOTICE.
__author__ = "Gabriele Fariello"
__license__ = "Apache-2.0"
__copyright__ = "Copyright 2007-2026 Gabriele Fariello"
__credit__ = __author__  # backward-compatible alias

__all__ = [
    "start",
    "stop",
    "annotate",
    "phase",
    "paused",
    "diff",
    "audit_run",
    "tracked_run",
    "get_current_run",
    "report",
    "artifact",
    "print",
    "open",
    "register_file",
    "register_input",
    "register_output",
    "subprocess",
    "popen",
    "__version__",
    "__commit__",
]

# -- Target-aware routing -----------------------------------------------------
# When Python processes `import pubrun.noauto`, it loads pubrun/__init__.py
# first. We detect this and defer core loading to the mode submodule.
from pubrun._bootstrap import is_mode_submodule_import_in_progress as _is_mode_import  # noqa: E402

if not _is_mode_import():
    # Root import: load core and execute boot sequence (auto-start if configured)
    from pubrun.core import (  # noqa: F401, E402
        start,
        stop,
        annotate,
        phase,
        paused,
        diff,
        audit_run,
        tracked_run,
        get_current_run,
        report,
        artifact,
        print,
        open,
        register_file,
        register_input,
        register_output,
        subprocess,
        popen,
        _run_lock,
        _execute_boot_sequence,
    )
    _execute_boot_sequence()
    del _execute_boot_sequence
else:
    # Mode submodule import in progress — defer everything to the submodule.
    # The submodule will import pubrun.core and populate pubrun.* attributes.
    # If the submodule import fails, we need a safety net so pubrun isn't
    # left permanently broken (P2-B5).
    import atexit as _atexit

    def _ensure_core_loaded():
        """Safety net: if mode submodule failed, load core as fallback."""
        import pubrun as _pkg
        if not hasattr(_pkg, "start"):
            try:
                from pubrun.core import (
                    start, stop, annotate, phase, paused, diff,
                    audit_run, tracked_run, get_current_run,
                    report, artifact, print, open,
                    register_file, register_input, register_output,
                    subprocess, popen,
                    _run_lock,
                )
                _pkg.start = start
                _pkg.stop = stop
                _pkg.annotate = annotate
                _pkg.phase = phase
                _pkg.paused = paused
                _pkg.diff = diff
                _pkg.audit_run = audit_run
                _pkg.tracked_run = tracked_run
                _pkg.get_current_run = get_current_run
                # `pubrun.report` is a CallableModule (pubrun/report/__init__.py): BOTH callable
                # as the report() API AND a subpackage exposing pubrun.report.output/checks/
                # diagnostics. Import the subpackage so the attribute is that CallableModule; do
                # NOT do `_pkg.report = report` (the plain function shadows the subpackage and
                # breaks `import pubrun.report.<submodule>`).
                import pubrun.report  # noqa: F401
                _pkg.artifact = artifact
                _pkg.print = print
                _pkg.open = open
                _pkg.register_file = register_file
                _pkg.register_input = register_input
                _pkg.register_output = register_output
                _pkg.subprocess = subprocess
                _pkg.popen = popen
                _pkg._run_lock = _run_lock
            except Exception:
                pass

    _atexit.register(_ensure_core_loaded)
    del _atexit

del _is_mode_import
