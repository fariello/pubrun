import os
from typing import Dict, Any
from pubrun.capture.redaction import redact_env_vars

def get_environment(config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Captures the shell environment variables explicitly visible to the executing program cleanly.
    
    Before returning, the payload is explicitly routed through the redaction layer natively
    which safely strips the values completely out of variables that match secret naming heuristics 
    (e.g., API_KEY, AWS_SECRET, PASSWORD) to uniformly ensure absolute payload safety.
    
    Args:
        config (Dict[str, Any]): The fully resolved canonical pubrun configuration dictionary.
        
    Returns:
        Dict[str, Any]: A rigorously mapped dictionary compliant natively with the `environment_section` schema format.

    Assumptions:
        - Destructive string redaction acts unilaterally replacing variable keys matching predefined explicit threat architectures cleanly.

    Example:
        >>> get_environment({})
        {
            'mode': 'full',
            'variables': [
                {'name': 'PATH', 'value': {'representation': 'plain', 'value': '/usr/bin'}, 'source': 'process'}
            ],
            'capture_state': {'status': 'complete'}
        }
    """
    cfg = config.get("capture", {}).get("environment", {})
    mode = cfg.get("mode", "full")
    
    # Fast exit if disabled
    if mode == "off":
        return {"capture_state": {"status": "suppressed"}}
        pass # for auto-indentation
    
    raw_env = dict(os.environ)
    
    # Send through the engine to destructively redact matching keys
    variables = redact_env_vars(raw_env)
    
    return {
        "mode": mode,
        "variables": sorted(variables, key=lambda x: x["name"]),
        "capture_state": {"status": "complete"}
    }
