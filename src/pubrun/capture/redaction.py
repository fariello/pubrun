import re
import hashlib
import json
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


def _redact_dict_keys(d: Dict[str, Any], config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    res = {}
    pattern = _get_secret_pattern(config)
    for k, v in d.items():
        if isinstance(k, str) and pattern.search(k):
            res[k] = "[REDACTED]"
        else:
            res[k] = _redact_any(v, config)
    return res


def _redact_any(val: Any, config: Optional[Dict[str, Any]] = None) -> Any:
    if isinstance(val, dict):
        return _redact_dict_keys(val, config)
    elif isinstance(val, list):
        return [_redact_any(item, config) for item in val]
    elif isinstance(val, str):
        return _redact_value_string_heuristics(val, config)
    return val


def _redact_value_string_heuristics(val: str, config: Optional[Dict[str, Any]] = None) -> str:
    if not isinstance(val, str) or not val:
        return val

    # 1. JSON parsing heuristic
    stripped = val.strip()
    if (stripped.startswith("{") and stripped.endswith("}")) or (stripped.startswith("[") and stripped.endswith("]")):
        try:
            data = json.loads(stripped)
            redacted_data = _redact_any(data, config)
            return json.dumps(redacted_data)
        except Exception:
            pass

    # 2. Database/URI credentials heuristic
    uri_pattern = re.compile(r"([a-zA-Z0-9+.-]+)://([^/:]+):([^/@]+)@([^/]+)")
    if uri_pattern.search(val):
        val = uri_pattern.sub(r"\1://\2:[REDACTED]@\4", val)

    # 3. Known API keys / Tokens
    openai_pattern = re.compile(r"sk-[a-zA-Z0-9]{20,}")
    val = openai_pattern.sub("[REDACTED]", val)
    
    bearer_pattern = re.compile(r"(?i)(bearer|token|auth)\s+([a-zA-Z0-9._~+/-]+=*)")
    val = bearer_pattern.sub(r"\1 [REDACTED]", val)

    return val


def redact_env_vars(env: Dict[str, str], config: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    """
    Takes an environment dictionary and returns a schema-compliant list,
    safely redacting any keys that match the configured secret patterns.
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
            heur_val = _redact_value_string_heuristics(v, config)
            result.append({
                "name": k,
                "value": {"representation": "plain", "value": heur_val},
                "source": "process"
            })
    return result


def redact_argv(argv: list, config: Optional[Dict[str, Any]] = None) -> list:
    """
    Returns a copy of argv with sensitive argument values redacted.
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
            parts = arg_str.split("=", 1)
            key_part = parts[0].lstrip("-")
            val_part = parts[1]
            if pattern.search(key_part):
                result.append(f"{parts[0]}=[REDACTED]")
                continue
            else:
                redacted_val = _redact_value_string_heuristics(val_part, config)
                result.append(f"{parts[0]}={redacted_val}")
                continue

        # Heuristic 2: --flag (next arg is the secret value)
        if arg_str.startswith("-"):
            flag_name = arg_str.lstrip("-")
            if pattern.search(flag_name):
                result.append(arg_str)
                redact_next = True
                continue

        arg_str = _redact_value_string_heuristics(arg_str, config)
        result.append(arg_str)

    return result

