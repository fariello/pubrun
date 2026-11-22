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
from typing import Any, Dict, Optional, Tuple

from pubrun._modes import VALID_MODES, get_mode_behavior


def _load_local_toml() -> Optional[Dict[str, Any]]:
    """Read and parse ./.pubrun.toml once.

    Returns the parsed dictionary if present and valid, or None on missing
    file, unavailable parser, or parse error (best-effort).
    """
    try:
        from pathlib import Path

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

        return data if isinstance(data, dict) else None
    except Exception:
        return None


def _extract_toml_key(
    data: Optional[Dict[str, Any]], section: str, key: str
) -> Optional[str]:
    """Safely extract a scalar key as a non-empty string from a parsed TOML dict.

    Handles non-dict sections safely without raising AttributeError and preserves
    boolean stringification (for example False -> "False").
    """
    if not isinstance(data, dict):
        return None
    section_table = data.get(section)
    if not isinstance(section_table, dict):
        return None
    if key not in section_table or section_table[key] is None:
        return None
    return str(section_table[key]) or None


def _read_local_toml_key(section: str, key: str) -> Optional[str]:
    """Attempt to read a single key from .pubrun.toml cheaply.

    Returns the string value if found, None otherwise.
    Does not raise on any error (best-effort).
    """
    return _extract_toml_key(_load_local_toml(), section, key)


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

    # 3 & 4. Read .pubrun.toml at most once for [imports].mode and [core].auto_start
    local_toml = _load_local_toml()
    if local_toml is not None:
        config_mode = _extract_toml_key(local_toml, "imports", "mode")
        if config_mode and config_mode.lower() in VALID_MODES:
            return (config_mode.lower(), "config:[imports].mode")

        config_auto = _extract_toml_key(local_toml, "core", "auto_start")
        if config_auto is not None:
            if config_auto.lower() in ("false", "0", "no"):
                return ("noauto", "config:[core].auto_start")
            elif config_auto.lower() in ("true", "1", "yes"):
                return ("auto", "config:[core].auto_start")

    # 5. Built-in default
    return ("auto", "default")
