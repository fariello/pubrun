import re
import hashlib
from typing import Dict, Any, List, Optional

# Default regex for detecting sensitive variable/flag names.
# Covers: passwords, secrets, tokens, API keys, auth credentials,
# private keys, database connection strings, bearer tokens, and signing keys.
DEFAULT_SECRET_REGEX = (
    r'(?i)(password|secret|token|api_key|key|auth|cred|private'
    r'|conn_str|connection_string|database_url|dsn|signing|bearer)'
)


def _get_secret_pattern(config: Optional[Dict[str, Any]] = None) -> re.Pattern:
    """Returns the compiled secret-detection regex from config, or the default."""
    if config:
        pattern_str = config.get("redaction", {}).get(
            "sensitive_keys_regex", DEFAULT_SECRET_REGEX
        )
    else:
        pattern_str = DEFAULT_SECRET_REGEX
    return re.compile(pattern_str)


def _get_representation(config: Optional[Dict[str, Any]] = None) -> str:
    """Returns the redaction representation mode from config ('redacted' or 'hashed')."""
    if config:
        return config.get("redaction", {}).get("representation", "redacted")
    return "redacted"


def redact_value(value: str, config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Replaces a sensitive string value with a redaction payload.

    The representation mode is read from the [redaction] config section:
    - "redacted": the value is completely destroyed (default). Prevents
      rainbow-table attacks against hashes of common passwords.
    - "hashed": a one-way SHA-256 hash is stored so the user can verify
      whether a secret changed between runs without seeing it.

    Args:
        value (str): The sensitive string to redact.
        config (Optional[Dict[str, Any]]): The resolved pubrun configuration.

    Returns:
        Dict[str, Any]: A schema-compliant redacted_value dictionary.

    Example:
        >>> redact_value("my_super_secret")
        {'representation': 'redacted'}
    """
    mode = _get_representation(config)
    if mode == "hashed":
        return {
            "representation": "hashed",
            "hash_algorithm": "sha256",
            "hash_value": hashlib.sha256(value.encode("utf-8")).hexdigest()
        }
    return {"representation": "redacted"}


def is_secret_key(key: str, config: Optional[Dict[str, Any]] = None) -> bool:
    """
    Determines whether a given string key represents a sensitive value
    using the regex pattern from the [redaction] config section.

    Args:
        key (str): The environment variable or flag name to test.
        config (Optional[Dict[str, Any]]): The resolved pubrun configuration.

    Returns:
        bool: True if the key matches a known secret pattern.

    Example:
        >>> is_secret_key("AWS_SECRET_ACCESS_KEY")
        True
        >>> is_secret_key("PATH")
        False
    """
    pattern = _get_secret_pattern(config)
    return bool(pattern.search(key))


def redact_env_vars(env: Dict[str, str], config: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    """
    Takes an environment dictionary and returns a schema-compliant list,
    safely redacting any keys that match the configured secret patterns.

    Controlled by [redaction] config settings:
    - env_enabled: if False, all values are returned as plain text (default True)
    - sensitive_keys_regex: regex for detecting secret variable names
    - representation: "redacted" (destructive) or "hashed" (SHA-256)

    Args:
        env (Dict[str, str]): Raw environment variables.
        config (Optional[Dict[str, Any]]): The resolved pubrun configuration.

    Returns:
        List[Dict[str, Any]]: A list of environment_entry dicts.

    Example:
        >>> redact_env_vars({"USER": "bob", "API_TOKEN": "12345"})
        [
            {"name": "API_TOKEN", "value": {"representation": "redacted"}, "source": "process"},
            {"name": "USER", "value": {"representation": "plain", "value": "bob"}, "source": "process"}
        ]
    """
    if config:
        enabled = config.get("redaction", {}).get("env_enabled", True)
        if not enabled:
            return [
                {"name": k, "value": {"representation": "plain", "value": v}, "source": "process"}
                for k, v in env.items()
            ]

    result = []
    for k, v in env.items():
        if is_secret_key(k, config):
            result.append({
                "name": k,
                "value": redact_value(v, config),
                "source": "process"
            })
        else:
            result.append({
                "name": k,
                "value": {"representation": "plain", "value": v},
                "source": "process"
            })
    return result


def redact_argv(argv: list, config: Optional[Dict[str, Any]] = None) -> list:
    """
    Returns a copy of argv with sensitive argument values redacted.

    Detects secrets using two heuristics:
    1. --flag=value where the flag name matches the secret regex:
       the value portion is replaced with [REDACTED].
    2. --flag VALUE where the flag name matches the secret regex:
       the next positional argument is replaced with [REDACTED].

    Controlled by [redaction].argv_enabled (default True).

    Args:
        argv (list): The original argument list (e.g., sys.argv).
        config (Optional[Dict[str, Any]]): The resolved pubrun configuration.

    Returns:
        list: A new list with sensitive values replaced.

    Example:
        >>> redact_argv(["script.py", "--api-key=sk-live-xxx", "--verbose"])
        ['script.py', '--api-key=[REDACTED]', '--verbose']
    """
    if config:
        enabled = config.get("redaction", {}).get("argv_enabled", True)
        if not enabled:
            return list(argv)

    pattern = _get_secret_pattern(config)
    result = []
    redact_next = False

    for arg in argv:
        arg_str = str(arg)

        if redact_next:
            result.append("[REDACTED]")
            redact_next = False
            continue

        # Heuristic 1: --flag=value or -flag=value
        if "=" in arg_str and arg_str.startswith("-"):
            key_part = arg_str.split("=", 1)[0].lstrip("-")
            if pattern.search(key_part):
                result.append(f"{arg_str.split('=', 1)[0]}=[REDACTED]")
                continue

        # Heuristic 2: --flag (next arg is the secret value)
        if arg_str.startswith("-"):
            flag_name = arg_str.lstrip("-")
            if pattern.search(flag_name):
                result.append(arg_str)
                redact_next = True
                continue

        result.append(arg_str)

    return result
