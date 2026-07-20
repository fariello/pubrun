import copy
import logging
import os
import sys
from pathlib import Path
from typing import Any, Dict, Optional
import importlib.resources

logger = logging.getLogger("pubrun")

if sys.version_info >= (3, 11):
    import tomllib
else:
    try:
        import tomli as tomllib
    except ImportError:
        raise ImportError(
            "pubrun requires 'tomli' on Python versions before 3.11 for configuration parsing."
        )


def _deep_merge(dict1: Dict[str, Any], dict2: Dict[str, Any]) -> Dict[str, Any]:
    """Recursively merge two config dicts. Values in dict2 override dict1.
    Non-dict values (including lists) are overwritten, not appended.
    Returns a new dict; originals are not mutated.
    """
    result = copy.deepcopy(dict1)
    for key, value in dict2.items():
        if isinstance(value, dict) and key in result and isinstance(result[key], dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def _read_package_resource(package: str, resource: str) -> str:
    """Read a text resource from a package, compatible with Python 3.8+."""
    if sys.version_info >= (3, 9):
        resource_path = importlib.resources.files(package).joinpath(resource)
        return resource_path.read_text(encoding="utf-8")
    else:
        # Python 3.8: use the legacy API
        return importlib.resources.read_text(package, resource, encoding="utf-8")


_DEFAULT_CONFIG_CACHE: Optional[Dict[str, Any]] = None


def load_default_config() -> Dict[str, Any]:
    """Load the built-in ``default.toml`` shipped with the package.

    The result is cached at module level since default.toml never changes
    at runtime. Returns a deep copy to prevent caller mutation of the cache.
    """
    global _DEFAULT_CONFIG_CACHE
    if _DEFAULT_CONFIG_CACHE is None:
        content = _read_package_resource("pubrun.resources", "default.toml")
        _DEFAULT_CONFIG_CACHE = tomllib.loads(content)
    return copy.deepcopy(_DEFAULT_CONFIG_CACHE)


def get_global_config_dir() -> Path:
    """Return the platform-specific global config directory for pubrun.

    - Windows: ``%APPDATA%/pubrun``
    - Linux/Mac: ``$XDG_CONFIG_HOME/pubrun`` or ``~/.config/pubrun``
    """
    if sys.platform == "win32":
        appdata = os.environ.get("APPDATA")
        if appdata:
            return Path(appdata) / "pubrun"
    config_dir = os.environ.get("XDG_CONFIG_HOME", os.path.expanduser("~/.config"))
    return Path(config_dir) / "pubrun"


def _safe_load_toml(path: Path) -> Optional[Dict[str, Any]]:
    """Parse a TOML config file, tolerating malformed content.

    A syntactically-invalid ``.pubrun.toml`` (truncated, hand-edited, wrong
    syntax) must not crash ``pubrun`` commands or the host script. On a parse
    error, log a warning and skip the file (returning None) so the remaining
    config layers still resolve. (IPD 20260705 EC-14.)
    """
    try:
        return tomllib.loads(path.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as e:
        logger.warning(f"pubrun: ignoring malformed config file {path}: {e}")
        return None
    except OSError as e:
        logger.debug(f"pubrun: could not read config file {path}: {e}")
        return None


def load_user_config() -> Optional[Dict[str, Any]]:
    """Load the user-level config from the global config directory, if it exists."""
    path = get_global_config_dir() / "config.toml"
    if path.is_file():
        return _safe_load_toml(path)
    return None


def load_local_config(start_dir: Optional[Path] = None) -> Optional[Dict[str, Any]]:
    """Load project-level config from ``.pubrun.toml`` and/or ``.config/pubrun/config.toml``.

    If both files exist, ``.pubrun.toml`` takes precedence (applied last).

    Args:
        start_dir: Directory to search. Defaults to the current working directory.
    """
    if start_dir is None:
        start_dir = Path.cwd()

    merged = {}

    # Base local configuration standard targeting explicit ecosystems
    deep_path = start_dir / ".config" / "pubrun" / "config.toml"
    if deep_path.is_file():
        deep_conf = _safe_load_toml(deep_path)
        if deep_conf:
            merged = _deep_merge(merged, deep_conf)

    # Highly explicit root footprint directly mapping local states
    root_path = start_dir / ".pubrun.toml"
    if root_path.is_file():
        root_conf = _safe_load_toml(root_path)
        if root_conf:
            merged = _deep_merge(merged, root_conf)

    return merged if merged else None


def _flatten_leaves(d: Dict[str, Any], prefix: str = "") -> Dict[str, Any]:
    """Flatten a nested dict to {dotted.key: value} for leaf (non-dict) values."""
    out: Dict[str, Any] = {}
    for k, v in d.items():
        dotted = f"{prefix}{k}"
        if isinstance(v, dict):
            out.update(_flatten_leaves(v, dotted + "."))
        else:
            out[dotted] = v
    return out


def _resolve_layers(overrides: Optional[Dict[str, Any]] = None):
    """Return the ordered list of (layer-name, layer-dict) contributing to a resolve,
    lowest-precedence first. Single source of truth for both the merge and provenance."""
    layers = [("built-in", load_default_config())]

    user_conf = load_user_config()
    if user_conf:
        layers.append(("user", user_conf))

    local_conf = load_local_config()
    if local_conf:
        layers.append(("local", local_conf))

    env_profile = os.environ.get("PUBRUN_PROFILE")
    if env_profile:
        layers.append(("env", {"core": {"profile": env_profile}}))

    env_meta_ref = os.environ.get("PUBRUN_META_REF")
    if env_meta_ref:
        layers.append(("env", {"core": {"meta_ref": env_meta_ref}}))

    if overrides:
        # Convenience flattening: allow start(profile="deep", output_dir="./x")
        # as shorthand for start(core={"profile": "deep", "output_dir": "./x"}).
        overrides = dict(overrides)
        _CORE_SHORTCUTS = {"profile", "output_dir", "auto_start", "meta_ref"}
        flat_core = {k: overrides.pop(k) for k in list(overrides) if k in _CORE_SHORTCUTS}
        if flat_core:
            overrides.setdefault("core", {}).update(flat_core)
        layers.append(("api", overrides))

    return layers


def resolve_config(overrides: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Build the final configuration by merging all sources.

    Precedence (lowest to highest):
    1. Built-in defaults (``default.toml``)
    2. User home config (``~/.config/pubrun/config.toml``)
    3. Local project config (``.config/pubrun/config.toml`` then ``.pubrun.toml``)
    4. Environment variables (``PUBRUN_PROFILE`` / ``PUBRUN_META_REF``)
    5. API overrides (this function's ``overrides`` argument)

    Args:
        overrides: Dict of config keys to merge at highest priority.
    """
    config: Dict[str, Any] = {}
    for _name, layer in _resolve_layers(overrides):
        config = _deep_merge(config, layer)
    return config


def resolve_config_with_provenance(overrides: Optional[Dict[str, Any]] = None):
    """Like ``resolve_config`` but also return per-key origin provenance.

    Returns ``(config, provenance)`` where the config is byte-identical to
    ``resolve_config(overrides)`` and provenance maps each leaf dotted-key to
    ``{"layer": <winning layer>, "value": <winning value>,
       "overrides": [{"layer","value"}, ...]}`` (lower layers it shadowed, lowest-first).
    Kept separate from ``resolve_config`` so the hot path keeps a single, non-union return type.
    """
    layers = _resolve_layers(overrides)

    config: Dict[str, Any] = {}
    for _name, layer in layers:
        config = _deep_merge(config, layer)

    provenance: Dict[str, Any] = {}
    for layer_name, layer in layers:
        for dotted, value in _flatten_leaves(layer).items():
            if dotted in provenance:
                prior = provenance[dotted]
                provenance[dotted] = {
                    "layer": layer_name,
                    "value": value,
                    "overrides": prior.get("overrides", []) + [
                        {"layer": prior["layer"], "value": prior["value"]}
                    ],
                }
            else:
                provenance[dotted] = {"layer": layer_name, "value": value, "overrides": []}

    return config, provenance


# The only profile value that is a no-op regardless of wiring; setting it never
# implied a capture change, so it does not warrant a deprecation notice.
_INERT_PROFILE_DEFAULT = "default"


def profile_deprecation_notice(config: Dict[str, Any]) -> Optional[Dict[str, str]]:
    """Return a deprecation notice if `core.profile` was set to a capture-affecting value.

    `core.profile` ("minimal"/"deep") was documented and exposed as a "master capture
    depth" dial but was never wired to any capture engine — it has no effect on what
    pubrun captures. Per the Option-D decision it is deprecated: still accepted (so no
    caller breaks), but explicitly inert. This returns a machine-readable notice to be
    recorded in the manifest (never raised, never printed here — the caller decides how
    to surface it, so an imported host script is never disrupted).

    Returns None when `profile` is unset or set to the inert default ``"default"``.
    """
    profile = config.get("core", {}).get("profile")
    if not profile or profile == _INERT_PROFILE_DEFAULT:
        return None
    return {
        "code": "profile_deprecated",
        "setting": "core.profile",
        "value": str(profile),
        "message": (
            f"core.profile={profile!r} has no effect: profile never controlled capture "
            f"depth and is deprecated. Set the specific capture.* keys instead "
            f"(e.g. capture.hardware.depth, capture.packages.mode)."
        ),
    }
