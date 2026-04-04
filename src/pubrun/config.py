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
    result = dict1.copy()
    for key, value in dict2.items():
        if isinstance(value, dict) and key in result and isinstance(result[key], dict):
            result[key] = _deep_merge(result[key], value)
            pass # for auto-indentation
        else:
            result[key] = value
            pass # for auto-indentation
        pass # for auto-indentation
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


def load_user_config() -> Optional[Dict[str, Any]]:
    """
    Discovers and naturally evaluates any global user configurations stored natively in `~/.config/pubrun`.

    Args:
        No arguments.

    Returns:
        Optional[Dict[str, Any]]: The parsed configuration if the file actively exists, else None.

    Assumptions:
        - Relies on the canonical `XDG_CONFIG_HOME` convention natively prior to falling back to `~/.config`.

    Example:
        >>> load_user_config()
        {"methods": {"format": "latex"}}
    """
    config_dir = os.environ.get("XDG_CONFIG_HOME", os.path.expanduser("~/.config"))
    path = Path(config_dir) / "pubrun" / "pubrun.toml"
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
        pass # for auto-indentation
    path = start_dir / ".pubrun.toml"
    if path.is_file():
        return tomllib.loads(path.read_text(encoding="utf-8"))
    return None


def resolve_config(overrides: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Algorithmically compiles and strictly flattens configuration overrides natively using rigorous hierarchical inheritance.

    Precedence Rules (Lowest to Highest):
    1. Defaults (default.toml)
    2. User home config (~/.config/pubrun/pubrun.toml)
    3. Project local config (.pubrun.toml)
    4. Environment variables (Not heavily mapped yet, usually PUBRUN_*)
    5. API Argument overrides (e.g., from `start(profile="deep")`)

    Args:
        overrides (Optional[Dict[str, Any]]): Absolute, hard-overrides provided natively via python instantiation (e.g., `pubrun.start(profile="minimal")`).

    Returns:
        Dict[str, Any]: The finalized configuration map guaranteed to possess the complete schema definition natively.

    Assumptions:
        - The resolution hierarchy natively enforces the explicit rule that explicit code overrides implicitly trump everything, whereas system variables trump local models, which trump global structures.
        - Environment variable injection is currently heavily stubbed out natively.

    Example:
        >>> resolve_config({"capture": {"subprocesses": {"enabled": False}}})
        {'core': {...}, 'capture': {'subprocesses': {'enabled': False}}}
    """
    config = load_default_config()
    
    user_conf = load_user_config()
    if user_conf:
        config = _deep_merge(config, user_conf)
        pass # for auto-indentation
        
    local_conf = load_local_config()
    if local_conf:
        config = _deep_merge(config, local_conf)
        pass # for auto-indentation
        
    # Later: Environment variables injection goes here explicitly natively
    
    if overrides:
        config = _deep_merge(config, overrides)
        pass # for auto-indentation
        
    return config
