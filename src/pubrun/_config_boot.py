"""
Lightweight import-mode resolver for pubrun boot sequence.

This module resolves the effective import mode from environment variables
and config files WITHOUT importing the full pubrun.config machinery (which
loads default.toml and does deep merges). This keeps the import-time cost
minimal and avoids circular imports.

Resolution order (highest to lowest):
1. PUBRUN_IMPORT_MODE environment variable
2. PUBRUN_AUTO_START environment variable (legacy alias)
3. [imports].mode from .pubrun.toml (project-local config)
4. [core].auto_start from .pubrun.toml (legacy config key)
5. Built-in default: "auto"
"""
import os
import sys
from typing import Optional, Tuple

from pubrun._modes import VALID_MODES, get_mode_behavior


def _read_local_toml_key(section: str, key: str) -> Optional[str]:
    """Attempt to read a single key from .pubrun.toml cheaply.

    Returns the string value if found, None otherwise.
    Does not raise on any error (best-effort).
    """
    try:
        from pathlib import Path
        # Check CWD for .pubrun.toml
        toml_path = Path.cwd() / ".pubrun.toml"
        if not toml_path.exists():
            return None

        if sys.version_info >= (3, 11):
            import tomllib
        else:
            try:
                import tomli as tomllib
            except ImportError:
                return None

        with open(toml_path, "rb") as f:
            data = tomllib.load(f)

        return str(data.get(section, {}).get(key, "")) or None
    except Exception:
        return None


def resolve_import_mode() -> Tuple[str, str]:
    """Resolve the effective import mode at boot time.

    Returns:
        (mode_name, source) where source describes where the mode came from.
        mode_name is one of: "auto", "noauto", "nopatch", "quiet".
        source is one of: "env:PUBRUN_IMPORT_MODE", "env:PUBRUN_AUTO_START",
            "config:[imports].mode", "config:[core].auto_start", "default".
    """
    # 1. PUBRUN_IMPORT_MODE env var (canonical, highest priority)
    env_mode = os.environ.get("PUBRUN_IMPORT_MODE", "").strip().lower()
    if env_mode in VALID_MODES:
        return (env_mode, "env:PUBRUN_IMPORT_MODE")

    # 2. PUBRUN_AUTO_START env var (legacy alias)
    env_auto = os.environ.get("PUBRUN_AUTO_START", "").strip().lower()
    if env_auto == "false":
        return ("noauto", "env:PUBRUN_AUTO_START")
    elif env_auto == "true":
        return ("auto", "env:PUBRUN_AUTO_START")

    # 3. [imports].mode from .pubrun.toml
    config_mode = _read_local_toml_key("imports", "mode")
    if config_mode and config_mode.lower() in VALID_MODES:
        return (config_mode.lower(), "config:[imports].mode")

    # 4. [core].auto_start from .pubrun.toml (legacy)
    config_auto = _read_local_toml_key("core", "auto_start")
    if config_auto is not None:
        if config_auto.lower() in ("false", "0", "no"):
            return ("noauto", "config:[core].auto_start")
        elif config_auto.lower() in ("true", "1", "yes"):
            return ("auto", "config:[core].auto_start")

    # 5. Built-in default
    return ("auto", "default")
