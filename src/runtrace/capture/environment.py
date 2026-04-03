import os
from typing import Dict, Any
from runtrace.capture.redaction import redact_env_vars

def get_environment(config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Captures the shell environment variables visible to the executing program.
    
    Before returning, the payload is explicitly routed through the redaction layer 
    which safely strips the values out of variables that match secret naming heuristics 
    (e.g., API_KEY, AWS_SECRET, PASSWORD) to ensure absolute safety.
    
    Args:
        config: The fully resolved runtrace configuration dictionary.
        
    Returns:
        A dictionary compliant with the `environment_section` schema format.
        
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
    
    raw_env = dict(os.environ)
    
    # Send through the engine to destructively redact matching keys
    variables = redact_env_vars(raw_env)
    
    return {
        "mode": mode,
        "variables": sorted(variables, key=lambda x: x["name"]),
        "capture_state": {"status": "complete"}
    }
