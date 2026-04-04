import re
from typing import Dict, Any, List

# A robust regex for common sensitive keys
SECRET_REGEX = re.compile(r'(?i)(password|secret|token|api_key|key|auth|cred)')

def redact_value(value: str) -> Dict[str, Any]:
    """
    Destructively redacts a sensitive value.
    
    To protect against rainbow table or brute-force attacks on common passwords 
    (e.g., matching a sha256 hash of 'password123'), this function does NOT 
    compute any hash of the secret. The redaction is completely destructive.
    
    Args:
        value: The sensitive string (unused, but kept for API consistency).
        
    Returns:
        A dictionary compliant with the schema's `redacted_value` object.
        
    Example:
        >>> redact_value("my_super_secret_password")
        {'representation': 'redacted'}
    """
    return {"representation": "redacted"}

def is_secret_key(key: str) -> bool:
    """
    Determines whether a given string key represents a sensitive value.
    
    Example:
        >>> is_secret_key("AWS_SECRET_ACCESS_KEY")
        True
        >>> is_secret_key("PATH")
        False
    """
    return bool(SECRET_REGEX.search(key))

def redact_env_vars(env: Dict[str, str]) -> List[Dict[str, Any]]:
    """
    Takes an environment dictionary and returns a schema-compliant list, 
    safely redacting any keys that match standard secret patterns.
    
    Args:
        env: A dictionary of environment variables (e.g., from os.environ).
        
    Returns:
        A list of dictionaries conforming to the `environment_entry` schema.
        
    Example:
        >>> env = {"USER": "bob", "API_TOKEN": "12345"}
        >>> redact_env_vars(env)
        [
            {"name": "API_TOKEN", "value": {"representation": "redacted"}, "source": "process"},
            {"name": "USER", "value": {"representation": "plain", "value": "bob"}, "source": "process"}
        ]
    """
    result = []
    for k, v in env.items():
        if is_secret_key(k):
            # Destructively redact the value for safety
            result.append({
                "name": k, 
                "value": redact_value(v), 
                "source": "process"
            })
        else:
            # Leave safe non-secret values unmodified
            result.append({
                "name": k, 
                "value": {"representation": "plain", "value": v}, 
                "source": "process"
            })
    return result
