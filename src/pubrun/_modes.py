"""
Import mode definitions for pubrun.

Each mode is a named preset controlling:
- auto_start: Whether importing pubrun automatically begins tracking.
- global_hooks: Obsolete unified flag, kept for backward compatibility.
- patch_subprocesses: Whether to patch subprocess modules (subprocess spy).
- patch_console: Whether to redirect sys.stdout/sys.stderr (console tee).
- signal_hooks: Whether to install signal/excepthook handlers.
"""
from typing import Dict, Any


# Mode presets: name -> behavior parameters
MODES: Dict[str, Dict[str, bool]] = {
    "auto": {
        "auto_start": True,
        "global_hooks": True,
        "patch_subprocesses": True,
        "patch_console": True,
        "signal_hooks": True,
    },
    "noauto": {
        "auto_start": False,
        "global_hooks": True,
        "patch_subprocesses": True,
        "patch_console": True,
        "signal_hooks": True,
    },
    "nopatch": {
        "auto_start": True,
        "global_hooks": False,
        "patch_subprocesses": False,
        "patch_console": False,
        "signal_hooks": True,
    },
    "noconsole": {
        "auto_start": True,
        "global_hooks": True,
        "patch_subprocesses": True,
        "patch_console": False,
        "signal_hooks": True,
    },
    "minimal": {
        "auto_start": False,
        "global_hooks": False,
        "patch_subprocesses": False,
        "patch_console": False,
        "signal_hooks": False,
    },
}

VALID_MODES = frozenset(MODES.keys())

# Config keys that map to mode behavior when [imports].mode is absent
_LEGACY_MODE_MAPPING = {
    # (auto_start, global_hooks) -> mode name
    (True, True): "auto",
    (False, True): "noauto",
    (True, False): "nopatch",
    (False, False): "minimal",
}


def resolve_mode_name(auto_start: bool, global_hooks: bool) -> str:
    """Derive the mode name from individual boolean settings."""
    return _LEGACY_MODE_MAPPING.get((auto_start, global_hooks), "auto")


def get_mode_behavior(mode: str) -> Dict[str, bool]:
    """Return the behavior dict for a given mode name.

    Falls back to 'auto' for unrecognized mode names.
    """
    return MODES.get(mode, MODES["auto"]).copy()
