import fnmatch
import os
from typing import Dict, Any, List
from pubrun.capture.redaction import redact_env_vars


def _allowlist_patterns(raw: Any) -> List[str]:
    """Return the usable allowlist patterns; anything malformed yields an empty list (fail closed)."""
    if not isinstance(raw, (list, tuple, set)):
        return []
    return [p for p in raw if isinstance(p, str) and p]


def get_environment(config: Dict[str, Any]) -> Dict[str, Any]:
    """Capture environment variables, applying redaction to sensitive keys.

    Args:
        config: Resolved pubrun configuration.
    """
    cfg = config.get("capture", {}).get("environment", {})
    mode = cfg.get("mode", "full")

    # Fast exit if disabled
    if mode == "off" or cfg.get("depth") == "off":
        return {"capture_state": {"status": "suppressed"}}

    raw_env = dict(os.environ)

    if mode == "allowlist":
        # Exact names or case-sensitive shell-style globs; an empty, omitted, or
        # malformed allowlist captures nothing.
        patterns = _allowlist_patterns(cfg.get("allowlist"))
        raw_env = {
            k: v for k, v in raw_env.items()
            if any(fnmatch.fnmatchcase(k, pat) for pat in patterns)
        }

    # Send through the engine to destructively redact matching keys
    variables = redact_env_vars(raw_env, config)

    return {
        "mode": mode,
        "variables": sorted(variables, key=lambda x: x["name"]),
        "capture_state": {"status": "complete"}
    }
