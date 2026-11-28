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

4. Import modes (``[console].capture_mode`` defaults to ``"off"``)::

    import pubrun.auto as pubrun      # Explicit default: auto-start.
    import pubrun.full as pubrun      # Auto-start; force console capture on (capture everything).
    import pubrun.noauto as pubrun    # No auto-start; call start() manually.
    import pubrun.nopatch as pubrun   # Auto-start; skip subprocess and console patches (signal hooks stay active).
    import pubrun.noconsole as pubrun # Auto-start; skip console wrapping.
    import pubrun.minimal as pubrun   # No auto-start, no subprocess/console/signal hooks.

Public API (``__all__``, 20 symbols)
------------------------------------
- ``start(**kwargs)``: Start a tracking run (or merge overrides into the active run).
- ``stop()``: Stop the active run and write artifacts.
- ``annotate(message, **kwargs)``: Emit an annotation event into ``events.jsonl``.
- ``phase(name)``: Context manager timing a named stage in ``events.jsonl``.
- ``paused()``: Context manager muting console and subprocess recording in the current thread.
- ``diff(run_dir_a, run_dir_b, ...)``: Compare two run manifests and return a structured diff.
- ``audit_run(func, **kwargs)``: Decorator wrapping a function in a tracked run.
- ``tracked_run(**kwargs)``: Context manager wrapping a block in a tracked run.
- ``get_current_run()``: Return the active ``Run`` instance, or ``None``.
- ``report(name, data)``: Save a structured JSON/text report into the active run directory.
- ``artifact(filename, content)``: Save a raw text or binary file into the active run directory.
- ``print(*args, **kwargs)``: Drop-in ``print()`` wrapper appending stdout to ``stdout.log``.
- ``open(file, mode, **kwargs)``: Drop-in ``open()`` wrapper recording file provenance.
- ``register_file(path, role, ...)``: Register an external input, output, or mixed file.
- ``register_input(path, ...)``: Register an external input file.
- ``register_output(path, ...)``: Register an external output file.
- ``subprocess``: Explicit ``subprocess.run`` / ``subprocess.Popen`` provenance wrappers.
- ``popen(cmd, ...)``: Explicit ``os.popen`` provenance wrapper.
- ``__version__``: Package version string (lazily resolved via PEP 562).
- ``__commit__``: Source or build commit SHA string, or ``None`` (lazily resolved via PEP 562).
"""
import sys
import threading as _threading
from typing import Any as _Any, List as _List, Optional as _Optional, Tuple as _Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    __version__: str
    __commit__: _Optional[str]

# -- Metadata ----------------------------------------------------------------
# Both __version__ and __commit__ are deferred via PEP 562 module __getattr__ so
# importing pubrun (especially pubrun.minimal / pubrun.noauto and installed wheels)
# never imports importlib.metadata or launches a git subprocess at import time.
# Installed wheels read version-checked build metadata without invoking git;
# verified pubrun source checkouts resolve live HEAD lazily with ownership
# validation and no stale COMMIT fallback.
_VERSION_UNSET = object()
_cached_version: _Any = _VERSION_UNSET
_version_lock = _threading.Lock()

_COMMIT_UNSET = object()
_cached_commit: _Any = _COMMIT_UNSET
_commit_lock = _threading.Lock()
_GIT_ENV_STRIP = ("GIT_DIR", "GIT_WORK_TREE", "GIT_COMMON_DIR", "GIT_INDEX_FILE")


def _is_valid_sha(value: _Any) -> bool:
    if not isinstance(value, str):
        return False
    import re as _re
    return bool(_re.fullmatch(r"[0-9a-fA-F]{40}(?:[0-9a-fA-F]{24})?", value))


def _read_pyproject_project_meta(
    pyproject_path: _Any,
) -> _Tuple[_Optional[str], _Optional[str]]:
    """Read ``[project]`` ``name`` and ``version`` from ``pyproject.toml``."""
    import builtins

    toml_mod: _Any = None
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
        with builtins.open(pyproject_path, "rb") as fh:
            data = toml_mod.load(fh)
        if not isinstance(data, dict):
            return None, None
        project = data.get("project")
        if not isinstance(project, dict):
            return None, None
        raw_name = project.get("name")
        raw_version = project.get("version")
        name_val = raw_name if isinstance(raw_name, str) else None
        ver_val = (
            raw_version.strip()
            if isinstance(raw_version, str) and raw_version.strip()
            else None
        )
        return name_val, ver_val

    # Fallback parser used only when neither tomllib nor tomli is importable.
    import re as _re
    in_project = False
    found_name: _Optional[str] = None
    found_version: _Optional[str] = None
    field_re = _re.compile(
        r"""^(name|version)\s*=\s*(?:"([^"]*)"|'([^']*)')(?:\s*(?:#.*)?)?$"""
    )
    with builtins.open(pyproject_path, "r", encoding="utf-8") as fh:
        for raw_line in fh:
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("["):
                if in_project:
                    break
                header = line.split("#", 1)[0].strip()
                if header == "[project]":
                    in_project = True
                continue
            if in_project:
                match = field_re.match(line)
                if match:
                    key = match.group(1)
                    val = match.group(2) if match.group(2) is not None else match.group(3)
                    if key == "name":
                        found_name = val
                    elif key == "version" and val and val.strip():
                        found_version = val.strip()
    return found_name, found_version


def _pyproject_declares_pubrun(pyproject_path: _Any) -> bool:
    name, _ = _read_pyproject_project_meta(pyproject_path)
    return name == "pubrun"


def _is_verified_source_checkout(pkg_dir: _Any) -> _Any:
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


def _read_packaged_resource(filename: str) -> str:
    import importlib.resources as _pkg_resources
    if sys.version_info >= (3, 9):
        return _pkg_resources.files(__name__).joinpath(filename).read_text(encoding="utf-8")
    return _pkg_resources.read_text(__name__, filename, encoding="utf-8")


def _resolve_version() -> str:
    """Resolve package version lazily with a deterministic fallback chain."""
    try:
        if sys.version_info >= (3, 8):
            from importlib.metadata import version as _pkg_version
        else:
            from importlib_metadata import version as _pkg_version
        ver = _pkg_version("pubrun")
        if isinstance(ver, str) and ver.strip():
            return ver.strip()
    except Exception:
        pass

    # 1. Verified source checkout pyproject.toml [project].version
    try:
        from pathlib import Path
        pkg_dir = Path(__file__).resolve().parent
        repo_root = _is_verified_source_checkout(pkg_dir)
        if repo_root is not None:
            _, checkout_ver = _read_pyproject_project_meta(repo_root / "pyproject.toml")
            if checkout_ver:
                return checkout_ver
    except Exception:
        pass

    # 2. Packaged _build_meta.json "version"
    try:
        import json as _json
        raw_meta = _read_packaged_resource("_build_meta.json")
        meta = _json.loads(raw_meta)
        if isinstance(meta, dict):
            meta_ver = meta.get("version")
            if isinstance(meta_ver, str) and meta_ver.strip():
                return meta_ver.strip()
    except Exception:
        pass

    # 3. Deterministic unknown fallback (replaces stale "1.0.0")
    return "0.0.0+unknown"


def _get_version() -> str:
    global _cached_version
    if _cached_version is _VERSION_UNSET:
        with _version_lock:
            if _cached_version is _VERSION_UNSET:
                _cached_version = _resolve_version()
    return str(_cached_version)


def _reset_version_cache() -> None:
    """Reset cached version resolution state for deterministic test isolation."""
    global _cached_version
    with _version_lock:
        _cached_version = _VERSION_UNSET
        globals().pop("__version__", None)


def _read_packaged_commit(expected_version: _Optional[str]) -> _Optional[str]:
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
    return str(commit)


def _resolve_checkout_commit(repo_root: _Any, timeout: float = 1.0) -> _Optional[str]:
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

        def _kill_and_reap(proc: _Any) -> None:
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

        def _run_bounded() -> _Tuple[_Optional[int], str]:
            with _sp.Popen(
                cmd,
                stdin=_sp.DEVNULL,
                stdout=_sp.PIPE,
                stderr=_sp.PIPE,
                text=True,
                env=clean_env,
            ) as proc:
                try:
                    stdout, _ = proc.communicate(timeout=timeout)
                    return proc.returncode, stdout
                except _sp.TimeoutExpired:
                    _kill_and_reap(proc)
                    return None, ""
                except BaseException:
                    try:
                        still_running = proc.poll() is None
                    except Exception:
                        still_running = True
                    if still_running:
                        _kill_and_reap(proc)
                    raise

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


def _resolve_commit() -> _Optional[str]:
    try:
        from pathlib import Path
        pkg_dir = Path(__file__).resolve().parent
    except Exception:
        return None
    repo_root = _is_verified_source_checkout(pkg_dir)
    if repo_root is not None:
        return _resolve_checkout_commit(repo_root)
    return _read_packaged_commit(_get_version())


def _get_commit() -> _Optional[str]:
    global _cached_commit
    if _cached_commit is _COMMIT_UNSET:
        with _commit_lock:
            if _cached_commit is _COMMIT_UNSET:
                _cached_commit = _resolve_commit()
    return _cached_commit if isinstance(_cached_commit, str) else None


def _reset_commit_cache() -> None:
    """Reset cached commit resolution state for deterministic test isolation."""
    global _cached_commit
    with _commit_lock:
        _cached_commit = _COMMIT_UNSET
        globals().pop("__commit__", None)


def __getattr__(name: str) -> _Any:
    if name == "__version__":
        return _get_version()
    if name == "__commit__":
        return _get_commit()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__() -> _List[str]:
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
