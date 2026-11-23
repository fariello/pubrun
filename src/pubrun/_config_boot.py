"""
Lightweight import-mode resolver for pubrun boot sequence.

This module resolves the effective import mode from environment variables
and config files WITHOUT importing the full pubrun.config machinery (which
loads default.toml and does deep merges). This keeps the import-time cost
minimal and avoids circular imports.

Resolution order (highest to lowest):
1. PUBRUN_IMPORT_MODE environment variable
2. PUBRUN_AUTO_START environment variable (legacy alias)
3. Config files, searched in the same precedence order as
   ``pubrun.config.resolve_config`` (highest first): ``./.pubrun.toml``,
   ``./.config/pubrun/config.toml``, then the user global ``config.toml``.
   The first file that sets a valid ``[imports].mode`` or a recognized
   ``[core].auto_start`` (``[imports].mode`` wins within one file) decides.
4. Built-in default: "auto"

The import-conflict policy ``[imports].on_conflict`` is read from the same
config files in the same order by ``_read_boot_toml_key``.
"""
import os
import sys
from typing import Any, Collection, Dict, Optional, Tuple

from pubrun._modes import VALID_MODES, get_mode_behavior

_AUTO_START_TRUE = ("1", "true", "yes", "on")
_AUTO_START_FALSE = ("0", "false", "no", "off")


def _auto_start_mode(value: Optional[str]) -> Optional[str]:
    """Map a PUBRUN_AUTO_START / [core].auto_start value to "auto"/"noauto", or None."""
    if value is None:
        return None
    normalized = value.strip().lower()
    if normalized in _AUTO_START_TRUE:
        return "auto"
    if normalized in _AUTO_START_FALSE:
        return "noauto"
    return None


def _global_config_dir() -> Any:
    """Return the user global config dir, mirroring ``pubrun.config.get_global_config_dir``."""
    from pathlib import Path

    if sys.platform == "win32":
        appdata = os.environ.get("APPDATA", "").strip()
        if appdata:
            return Path(appdata) / "pubrun"
    xdg = os.environ.get("XDG_CONFIG_HOME", "").strip()
    base = xdg if xdg else os.path.expanduser("~/.config")
    return Path(base) / "pubrun"


def _boot_config_paths() -> list:
    """Config file candidates, highest precedence first."""
    from pathlib import Path

    paths = []
    try:
        cwd = Path.cwd()
        paths.extend([cwd / ".pubrun.toml", cwd / ".config" / "pubrun" / "config.toml"])
    except Exception:
        pass
    try:
        paths.append(_global_config_dir() / "config.toml")
    except Exception:
        pass
    return paths


def _load_toml_file(toml_path: Any) -> Optional[Dict[str, Any]]:
    """Read and parse one TOML file.

    Returns the parsed dictionary if present and valid, or None on missing
    file, unavailable parser, or parse error (best-effort).
    """
    try:
        if not toml_path.is_file():
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


def _load_local_toml() -> Optional[Dict[str, Any]]:
    """Read and parse ./.pubrun.toml once (best-effort, None on any failure)."""
    try:
        from pathlib import Path

        return _load_toml_file(Path.cwd() / ".pubrun.toml")
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


def _read_boot_toml_key(
    section: str, key: str, valid: Collection[str]
) -> Optional[str]:
    """Return the first acceptable ``[section].key`` value across the boot config files.

    Searches ``_boot_config_paths()`` highest precedence first, parsing each
    file at most once. A value is acceptable when its stripped, lowercased
    form is in ``valid``; that normalized form is returned. Missing,
    malformed, or unacceptable entries fall through to the next file.
    Returns None when no file supplies an acceptable value. Never raises.
    """
    for toml_path in _boot_config_paths():
        value = _extract_toml_key(_load_toml_file(toml_path), section, key)
        if value is None:
            continue
        normalized = value.strip().lower()
        if normalized in valid:
            return normalized
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
    env_auto = _auto_start_mode(os.environ.get("PUBRUN_AUTO_START", ""))
    if env_auto is not None:
        return (env_auto, "env:PUBRUN_AUTO_START")

    # 3. Config files, highest precedence first; each file is parsed at most once.
    for toml_path in _boot_config_paths():
        data = _load_toml_file(toml_path)
        if data is None:
            continue
        config_mode = _extract_toml_key(data, "imports", "mode")
        if config_mode and config_mode.strip().lower() in VALID_MODES:
            return (config_mode.strip().lower(), "config:[imports].mode")

        config_auto = _auto_start_mode(_extract_toml_key(data, "core", "auto_start"))
        if config_auto is not None:
            return (config_auto, "config:[core].auto_start")

    # 4. Built-in default
    return ("auto", "default")
