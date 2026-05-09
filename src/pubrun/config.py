import copy
import os
import sys
from pathlib import Path
from typing import Any, Dict, Optional
import importlib.resources

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
    """
    Recursively deep-merges two configuration dictionaries cleanly.

    Args:
        dict1 (Dict[str, Any]): The strictly foundational base dictionary.
        dict2 (Dict[str, Any]): The explicit overriding dictionary payload.

    Returns:
        Dict[str, Any]: A newly instantiated dictionary with safely resolved nesting.

    Assumptions:
        - Dictionaries are deeply merged recursively.
        - Non-dictionary types (like Lists) are strictly overwritten by `dict2`, not appended.

    Example:
        >>> _deep_merge({"core": {"a": 1}}, {"core": {"b": 2}})
        {"core": {"a": 1, "b": 2}}
    """
    result = copy.deepcopy(dict1)
    for key, value in dict2.items():
        if isinstance(value, dict) and key in result and isinstance(result[key], dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def load_default_config() -> Dict[str, Any]:
    """
    Loads the native foundational TOML configuration securely embedded inside `pubrun`.

    Args:
        No arguments.

    Returns:
        Dict[str, Any]: The fully parsed canonical configuration map.

    Assumptions:
        - We assume the pip installation naturally retains the `resources/default.toml` structure natively.

    Example:
        >>> load_default_config()
        {"core": {"cache_size": 10}, "capture": {"subprocesses": { ... }}}
    """
    resource_path = importlib.resources.files("pubrun").joinpath("resources", "default.toml")
    content = resource_path.read_text(encoding="utf-8")
    return tomllib.loads(content)


def get_global_config_dir() -> Path:
    """
    Deterministically resolves the cross-platform global configuration ecosystem mapping properly.
    - Windows -> %APPDATA%/pubrun
    - Linux/Mac -> $XDG_CONFIG_HOME/pubrun or ~/.config/pubrun
    """
    if sys.platform == "win32":
        appdata = os.environ.get("APPDATA")
        if appdata:
            return Path(appdata) / "pubrun"
    config_dir = os.environ.get("XDG_CONFIG_HOME", os.path.expanduser("~/.config"))
    return Path(config_dir) / "pubrun"


def load_user_config() -> Optional[Dict[str, Any]]:
    """
    Discovers and naturally evaluates any global user configurations stored natively in the system app root.

    Args:
        No arguments.

    Returns:
        Optional[Dict[str, Any]]: The parsed configuration if the file actively exists, else None.

    Assumptions:
        - Relies on the canonical `XDG_CONFIG_HOME` convention natively or `%APPDATA%` on Windows.

    Example:
        >>> load_user_config()
        {"methods": {"format": "latex"}}
    """
    path = get_global_config_dir() / "config.toml"
    if path.is_file():
        return tomllib.loads(path.read_text(encoding="utf-8"))
    return None


def load_local_config(start_dir: Optional[Path] = None) -> Optional[Dict[str, Any]]:
    """
    Surgically explicitly isolates project-specific overrides via local `.pubrun.toml` detection.

    Args:
        start_dir (Optional[Path]): The explicit origin directory to search natively. If None, relies exclusively on the current working directory.

    Returns:
        Optional[Dict[str, Any]]: The cleanly mapped override dictionary natively returned if present.

    Assumptions:
        - We explicitly evaluate `.pubrun.toml` in the target directory without recursively jumping up trees automatically.

    Example:
        >>> load_local_config()
        None
    """
    if start_dir is None:
        start_dir = Path.cwd()
        
    merged = {}
    
    # Base local configuration standard targeting explicit ecosystems
    deep_path = start_dir / ".config" / "pubrun" / "config.toml"
    if deep_path.is_file():
        merged = _deep_merge(merged, tomllib.loads(deep_path.read_text(encoding="utf-8")))
        
    # Highly explicit root footprint directly mapping local states
    root_path = start_dir / ".pubrun.toml"
    if root_path.is_file():
        merged = _deep_merge(merged, tomllib.loads(root_path.read_text(encoding="utf-8")))
        
    return merged if merged else None


def resolve_config(overrides: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Algorithmically compiles and strictly flattens configuration overrides natively using rigorous hierarchical inheritance.

    Precedence Rules (Lowest to Highest):
    1. Defaults (default.toml)
    2. User home config (~/.config/pubrun/config.toml)
    3. Project local config (./.config/pubrun/config.toml -> ./.pubrun.toml)
    4. Environment variables (Not heavily mapped yet, usually PUBRUN_*)
    5. API Argument overrides (e.g., from `start(profile="deep")`)

    Args:
        overrides (Optional[Dict[str, Any]]): Absolute, hard-overrides provided natively via python instantiation (e.g., `pubrun.start(profile="minimal")`).

    Returns:
        Dict[str, Any]: The finalized configuration map guaranteed to possess the complete schema definition natively.

    Assumptions:
        - The resolution hierarchy enforces that explicit API overrides trump everything,
          environment variables trump config files, and local config trumps global.
        - Environment variable support: PUBRUN_AUTO_START (in boot sequence) and
          PUBRUN_META_REF (injected here as core.meta_ref).

    Example:
        >>> resolve_config({"capture": {"subprocesses": {"enabled": False}}})
        {'core': {...}, 'capture': {'subprocesses': {'enabled': False}}}
    """
    config = load_default_config()
    
    user_conf = load_user_config()
    if user_conf:
        config = _deep_merge(config, user_conf)
        
    local_conf = load_local_config()
    if local_conf:
        config = _deep_merge(config, local_conf)
        
    # Environment variable overrides (between local config and API overrides)
    env_meta_ref = os.environ.get("PUBRUN_META_REF")
    if env_meta_ref:
        config = _deep_merge(config, {"core": {"meta_ref": env_meta_ref}})
    
    if overrides:
        config = _deep_merge(config, overrides)
        
    return config
