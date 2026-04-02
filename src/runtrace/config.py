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
            "runtrace requires 'tomli' on Python versions before 3.11 for configuration parsing."
        )


def _deep_merge(dict1: dict, dict2: dict) -> dict:
    """Recursively merge two dictionaries."""
    result = dict1.copy()
    for key, value in dict2.items():
        if isinstance(value, dict) and key in result and isinstance(result[key], dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def load_default_config() -> dict[str, Any]:
    """Load the built-in default configuration from the resources package."""
    resource_path = importlib.resources.files("runtrace").joinpath("resources", "default.toml")
    content = resource_path.read_text(encoding="utf-8")
    return tomllib.loads(content)


def load_user_config() -> Optional[dict[str, Any]]:
    """Load configuration from the user's home directory config area."""
    config_dir = os.environ.get("XDG_CONFIG_HOME", os.path.expanduser("~/.config"))
    path = Path(config_dir) / "runtrace" / "runtrace.toml"
    if path.is_file():
        return tomllib.loads(path.read_text(encoding="utf-8"))
    return None


def load_local_config(start_dir: Optional[Path] = None) -> Optional[dict[str, Any]]:
    """Load configuration from the local project `.runtrace.toml` file."""
    if start_dir is None:
        start_dir = Path.cwd()
    path = start_dir / ".runtrace.toml"
    if path.is_file():
        return tomllib.loads(path.read_text(encoding="utf-8"))
    return None


def resolve_config(overrides: Optional[dict[str, Any]] = None) -> dict[str, Any]:
    """
    Resolve and merge configuration based on precedence rules.
    1. Defaults (default.toml)
    2. User home config (~/.config/runtrace/runtrace.toml)
    3. Project local config (.runtrace.toml)
    4. Environment variables (Not heavily mapped yet, usually RUNTRACE_*)
    5. API Argument overrides (e.g., from `start(profile="deep")`)
    """
    config = load_default_config()
    
    user_conf = load_user_config()
    if user_conf:
        config = _deep_merge(config, user_conf)
        
    local_conf = load_local_config()
    if local_conf:
        config = _deep_merge(config, local_conf)
        
    # Later: Environment variables injection goes here
    
    if overrides:
        config = _deep_merge(config, overrides)
        
    return config
