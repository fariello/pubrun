import os
import sys
from typing import Dict, Any


def environment_kind() -> Dict[str, Any]:
    """Classify the Python environment as non-identifying scalars.

    These fields survive share-redaction (they expose NO path, username, or home dir),
    yet recover the interpretive signal that redacting ``prefix``/``virtual_env``/``sys_path``
    would otherwise lose: whether the run used a venv/conda/system Python, and how long
    ``sys.path`` is (import time scales with it). Cross-platform (Linux/macOS/Windows),
    pure stdlib, never raises.

    Returns keys:
        environment_kind: "conda" | "venv" | "virtualenv" | "system" | "frozen"
        in_venv:          bool (``sys.prefix != sys.base_prefix`` — PEP 405)
        sys_path_len:     int
        pyenv:            bool (orthogonal modifier: pyenv-managed interpreter)
    """
    in_venv = bool(getattr(sys, "base_prefix", sys.prefix) != sys.prefix)
    # conda marker: CONDA_PREFIX matching the interpreter prefix, or a conda-meta dir.
    conda = False
    try:
        cp = os.environ.get("CONDA_PREFIX")
        if cp and os.path.normpath(cp) == os.path.normpath(sys.prefix):
            conda = True
        elif os.path.isdir(os.path.join(sys.prefix, "conda-meta")):
            conda = True
    except Exception:
        pass
    if getattr(sys, "frozen", False):
        kind = "frozen"
    elif conda:
        kind = "conda"
    elif hasattr(sys, "real_prefix"):
        kind = "virtualenv"  # legacy virtualenv (<20) sets sys.real_prefix
    elif in_venv:
        kind = "venv"
    else:
        kind = "system"
    pyenv = bool(os.environ.get("PYENV_VERSION") or ("pyenv" in (sys.executable or "")))
    return {
        "environment_kind": kind,
        "in_venv": in_venv,
        "sys_path_len": len(sys.path),
        "pyenv": pyenv,
    }


def get_python_runtime(config: Dict[str, Any]) -> Dict[str, Any]:
    """Capture Python interpreter details: executable, version, venv status, sys.path.

    Args:
        config: Resolved pubrun configuration.
    """

    # Determine virual_env presence by checking if prefix differs from base_prefix
    # or if the older standard 'real_prefix' exists.
    is_venv = hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix)

    out = {
        "executable": sys.executable,
        "version": sys.version,
        "implementation": sys.implementation.name,
        "prefix": sys.prefix,
        "base_prefix": getattr(sys, 'base_prefix', None),
        "virtual_env": "venv" if is_venv else None,
        "sys_path": list(sys.path),
        "capture_state": {"status": "complete"}
    }
    # Non-identifying environment classification (survives share-redaction).
    try:
        out.update(environment_kind())
    except Exception:
        pass
    return out
