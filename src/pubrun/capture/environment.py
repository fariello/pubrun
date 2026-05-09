import os
from typing import Dict, Any
from pubrun.capture.redaction import redact_env_vars

def get_environment(config: Dict[str, Any]) -> Dict[str, Any]:
    """Capture environment variables, applying redaction to sensitive keys.

    Args:
        config: Resolved pubrun configuration.
    """
    cfg = config.get("capture", {}).get("environment", {})
    mode = cfg.get("mode", "full")
    
    # Fast exit if disabled
    if mode == "off":
        return {"capture_state": {"status": "suppressed"}}
    
    raw_env = dict(os.environ)
    
    # Send through the engine to destructively redact matching keys
    variables = redact_env_vars(raw_env, config)
    
    return {
        "mode": mode,
        "variables": sorted(variables, key=lambda x: x["name"]),
        "capture_state": {"status": "complete"}
    }
