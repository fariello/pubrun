"""
Import mode definitions for pubrun.

Each mode is a named preset controlling two orthogonal behaviors:
- auto_start: Whether importing pubrun automatically begins tracking.
- global_hooks: Whether process-global hooks (subprocess spy, console tee,
  signal handlers) are installed.
"""
from typing import Dict, Any


# Mode presets: name -> {auto_start, global_hooks}
MODES: Dict[str, Dict[str, bool]] = {
    "auto": {"auto_start": True, "global_hooks": True},
    "noauto": {"auto_start": False, "global_hooks": True},
    "nopatch": {"auto_start": True, "global_hooks": False},
    "quiet": {"auto_start": False, "global_hooks": False},
}

VALID_MODES = frozenset(MODES.keys())

# Config keys that map to mode behavior when [imports].mode is absent
_LEGACY_MODE_MAPPING = {
    # (auto_start, global_hooks) -> mode name
    (True, True): "auto",
    (False, True): "noauto",
    (True, False): "nopatch",
    (False, False): "quiet",
}


def resolve_mode_name(auto_start: bool, global_hooks: bool) -> str:
    """Derive the mode name from individual boolean settings."""
    return _LEGACY_MODE_MAPPING.get((auto_start, global_hooks), "auto")


def get_mode_behavior(mode: str) -> Dict[str, bool]:
    """Return the behavior dict for a given mode name.

    Falls back to 'auto' for unrecognized mode names.
    """
    return MODES.get(mode, MODES["auto"]).copy()
