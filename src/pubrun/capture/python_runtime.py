import sys
from typing import Dict, Any

def get_python_runtime(config: Dict[str, Any]) -> Dict[str, Any]:
    """Capture Python interpreter details: executable, version, venv status, sys.path.

    Args:
        config: Resolved pubrun configuration.
    """
    
    # Determine virual_env presence by checking if prefix differs from base_prefix
    # or if the older standard 'real_prefix' exists.
    is_venv = hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix)
    
    return {
        "executable": sys.executable,
        "version": sys.version,
        "implementation": sys.implementation.name,
        "prefix": sys.prefix,
        "base_prefix": getattr(sys, 'base_prefix', None),
        "virtual_env": "venv" if is_venv else None,
        "sys_path": list(sys.path),
        "capture_state": {"status": "complete"}
    }
