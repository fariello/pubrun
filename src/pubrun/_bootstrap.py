"""
pubrun._bootstrap — Import-mode state, conflict detection, and provenance.

This module tracks which import mode was selected, by whom, and detects
conflicts when multiple imports request different modes.

It is intentionally free of heavy imports and side effects.
"""
import sys
import time
import threading
import warnings
from typing import Any, Dict, List, Optional, Tuple

from pubrun._modes import MODES, get_mode_behavior


# =============================================================================
# Warning and error classes
# =============================================================================

class PubrunImportModeConflictError(RuntimeError):
    """Raised when conflicting pubrun import modes are configured to error."""


class PubrunImportModeConflictWarning(RuntimeWarning):
    """Warns that a conflicting pubrun import mode was requested."""


class PubrunImportModeTooLateWarning(RuntimeWarning):
    """Warns that an import-mode request happened after pubrun.core loaded."""


# =============================================================================
# Bootstrap state (module-level singleton)
# =============================================================================

_lock = threading.Lock()

# The effective mode that was selected (first wins)
_selected_mode: Optional[str] = None
_selected_behavior: Optional[Dict[str, bool]] = None
_selected_by: Optional[str] = None
_selected_source: Optional[str] = None
_selected_at_utc: Optional[float] = None

# Whether pubrun.core has been loaded (irreversible work may have happened)
_core_loaded: bool = False

# Conflict policy (resolved once from config/env)
_conflict_policy: Optional[str] = None

# History of import-mode requests
_requests: List[Dict[str, Any]] = []
_max_requests: int = 50


# =============================================================================
# Public API for bootstrap state
# =============================================================================

def is_mode_selected() -> bool:
    """Return True if an import mode has already been selected."""
    return _selected_mode is not None


def get_selected_mode() -> Optional[str]:
    """Return the currently selected mode name, or None."""
    return _selected_mode


def get_selected_behavior() -> Optional[Dict[str, bool]]:
    """Return the effective behavior dict, or None."""
    return _selected_behavior


def mark_core_loaded() -> None:
    """Mark that pubrun.core has been imported (irreversible work started)."""
    global _core_loaded
    _core_loaded = True


def is_core_loaded() -> bool:
    """Return True if pubrun.core has been imported."""
    return _core_loaded


def get_import_metadata() -> Dict[str, Any]:
    """Return the full import provenance metadata for manifest inclusion."""
    return {
        "selected_mode": _selected_mode,
        "selected_behavior": _selected_behavior,
        "selected_by": _selected_by,
        "selected_source": _selected_source,
        "selected_at_utc": _selected_at_utc,
        "core_loaded": _core_loaded,
        "conflict_policy": _conflict_policy,
        "conflicts_detected": sum(1 for r in _requests if r.get("conflict")),
        "requests": _requests[:_max_requests],
    }


def reset_state() -> None:
    """Reset all bootstrap state. Used only for testing."""
    global _selected_mode, _selected_behavior, _selected_by
    global _selected_source, _selected_at_utc, _core_loaded
    global _conflict_policy, _requests
    _selected_mode = None
    _selected_behavior = None
    _selected_by = None
    _selected_source = None
    _selected_at_utc = None
    _core_loaded = False
    _conflict_policy = None
    _requests = []


# =============================================================================
# Mode selection and conflict detection
# =============================================================================

def _resolve_conflict_policy() -> str:
    """Resolve the conflict policy from env or config. Cached after first call."""
    global _conflict_policy
    if _conflict_policy is not None:
        return _conflict_policy

    import os
    # Check env first
    env_policy = os.environ.get("PUBRUN_IMPORT_CONFLICT", "").strip().lower()
    if env_policy in ("ignore", "warn", "error"):
        _conflict_policy = env_policy
        return _conflict_policy

    # Fall back to config (lightweight read)
    from pubrun._config_boot import _read_local_toml_key
    config_policy = _read_local_toml_key("imports", "on_conflict")
    if config_policy and config_policy.lower() in ("ignore", "warn", "error"):
        _conflict_policy = config_policy.lower()
        return _conflict_policy

    _conflict_policy = "warn"
    return _conflict_policy


def _get_caller_info(selected_by: str) -> Optional[Dict[str, Any]]:
    """Capture minimal caller info for provenance. Best-effort."""
    try:
        # Walk up the stack to find the first non-pubrun, non-importlib frame
        frame = sys._getframe(2)  # skip _get_caller_info and select_mode
        for _ in range(10):
            if frame is None:
                break
            filename = frame.f_code.co_filename
            # Skip pubrun internals and importlib machinery
            if ("pubrun" not in filename and
                "importlib" not in filename and
                "<frozen" not in filename):
                return {
                    "filename": filename,
                    "line_number": frame.f_lineno,
                    "function": frame.f_code.co_name,
                }
            frame = frame.f_back
    except (AttributeError, ValueError):
        pass
    return None


def select_mode(mode: str, selected_by: str, source: str) -> Dict[str, bool]:
    """Select an import mode. First call wins; later calls detect conflicts.

    Args:
        mode: One of "auto", "noauto", "nopatch", "minimal".
        selected_by: Identifier for who selected this mode (e.g., "pubrun",
            "pubrun.noauto", "env:PUBRUN_IMPORT_MODE").
        source: Where the selection came from (e.g., "default", "config",
            "env:PUBRUN_IMPORT_MODE").

    Returns:
        The effective behavior dict (e.g., {"auto_start": bool, ...}).
    """
    global _selected_mode, _selected_behavior, _selected_by
    global _selected_source, _selected_at_utc

    behavior = get_mode_behavior(mode)
    now = time.time()

    with _lock:
        if _selected_mode is None:
            # First selection — this wins
            _selected_mode = mode
            _selected_behavior = behavior
            _selected_by = selected_by
            _selected_source = source
            _selected_at_utc = now

            request = {
                "timestamp_utc": now,
                "requested_mode": mode,
                "selected_by": selected_by,
                "effective_behavior": behavior,
                "selected": True,
                "conflict": False,
                "core_loaded_at_request": _core_loaded,
            }
            caller = _get_caller_info(selected_by)
            if caller:
                request["caller"] = caller
            _requests.append(request)

            return behavior

        # Subsequent selection — check for conflict
        is_conflict = (behavior != _selected_behavior)

        request = {
            "timestamp_utc": now,
            "requested_mode": mode,
            "selected_by": selected_by,
            "effective_behavior": behavior,
            "selected": False,
            "conflict": is_conflict,
            "core_loaded_at_request": _core_loaded,
        }
        caller = _get_caller_info(selected_by)
        if caller:
            request["caller"] = caller

        if len(_requests) < _max_requests:
            _requests.append(request)

        if is_conflict:
            policy = _resolve_conflict_policy()
            msg = (
                f"Conflicting pubrun import modes detected. "
                f"pubrun was already initialized with mode '{_selected_mode}' "
                f"(by {_selected_by}), but '{selected_by}' requested mode '{mode}'. "
                f"The first effective behavior remains active."
            )
            if _core_loaded:
                msg += " Note: pubrun.core was already loaded; side effects cannot be undone."

            if policy == "error":
                raise PubrunImportModeConflictError(msg)
            elif policy == "warn":
                warnings.warn(msg, PubrunImportModeConflictWarning, stacklevel=3)

        # Return the ORIGINAL selected behavior (first wins)
        assert _selected_behavior is not None  # guaranteed by _selected_mode check above
        return _selected_behavior


def is_mode_submodule_import_in_progress() -> bool:
    """Detect if a pubrun mode submodule import is in progress.

    When Python processes `import pubrun.noauto`, it loads pubrun/__init__.py
    first. This function checks if the import machinery is currently loading
    one of the known mode submodules, so __init__.py can defer core loading.

    Uses sys._getframe() to inspect the import stack. Falls back to False
    if detection is unavailable (safe default: root import behavior).
    """
    _MODE_SUBMODULES = frozenset({
        "pubrun.auto", "pubrun.noauto", "pubrun.nopatch", "pubrun.minimal"
    })
    try:
        # Walk up the call stack looking for importlib._bootstrap._find_and_load
        # which will have the module name as a local variable or argument.
        frame = sys._getframe(1)
        for _ in range(20):
            if frame is None:
                break
            # importlib._bootstrap._find_and_load has 'name' as first arg
            local_name = frame.f_locals.get("name", "")
            if local_name in _MODE_SUBMODULES:
                return True
            frame = frame.f_back
    except (AttributeError, ValueError):
        pass
    return False
