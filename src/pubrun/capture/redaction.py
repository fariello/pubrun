import re
import hashlib
import json
import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger("pubrun")


# Default regex for detecting sensitive variable/flag names.
# Covers: passwords, secrets, tokens, API keys, auth credentials,
# private keys, database connection strings, bearer tokens, and signing keys.
DEFAULT_SECRET_REGEX = (
    r'(?i)(password|secret|token|api_key|key|auth|cred|private'
    r'|conn_str|connection_string|database_url|dsn|signing|bearer)'
)

# Compiled pattern cache: keyed by pattern string to avoid re.compile() per call.
_PATTERN_CACHE: Dict[str, re.Pattern] = {}


def _get_secret_pattern(config: Optional[Dict[str, Any]] = None) -> re.Pattern:
    """Returns the compiled secret-detection regex from config, or the default.

    Results are cached by pattern string so re.compile() is called at most once
    per unique pattern across the lifetime of the process.
    """
    if config:
        pattern_str = config.get("redaction", {}).get(
            "sensitive_keys_regex", DEFAULT_SECRET_REGEX
        )
    else:
        pattern_str = DEFAULT_SECRET_REGEX
    try:
        cached = _PATTERN_CACHE.get(pattern_str)
    except TypeError:
        # Unhashable value (e.g. a list from a malformed config).
        cached = None
    if cached is not None:
        return cached
    try:
        compiled = re.compile(pattern_str)
    except (re.error, TypeError) as e:
        # A bad user regex must never crash the host (this runs inside the
        # patched Popen); fall back to the default pattern and do not cache it.
        logger.warning(
            "pubrun: invalid [redaction].sensitive_keys_regex (%s); using the default pattern",
            type(e).__name__,
        )
        return _get_secret_pattern(None)
    _PATTERN_CACHE[pattern_str] = compiled
    return compiled


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
            "hash_value": hashlib.sha256(value.encode("utf-8", errors="replace")).hexdigest()
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


# Covers hyphenated prefixed keys such as sk-proj-...
_PREFIXED_KEY_VALUE_RE = re.compile(r"\bsk-[A-Za-z0-9_-]{20,}")


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

    # 2. Database/URI credentials heuristic. Both forms run so a string holding
    # a user:pass URI and a token URI redacts each; the whitespace-bounded
    # classes keep a match inside one URI (no spanning into adjacent text).
    val = _DIAG_URI_USERPASS_RE.sub(r"\1://\2:[REDACTED]@\4", val)
    # scheme://token@host (e.g. git tokens)
    val = _DIAG_URI_TOKEN_RE.sub(r"\1://[REDACTED]@\3", val)

    # 3. Known API keys / Tokens
    openai_pattern = re.compile(r"sk-[a-zA-Z0-9]{20,}")
    val = openai_pattern.sub("[REDACTED]", val)
    val = _PREFIXED_KEY_VALUE_RE.sub("[REDACTED]", val)

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
            return [str(arg) for arg in argv]

    pattern = _get_secret_pattern(config)
    result = []
    redact_next = False

    for arg in argv:
        arg_str = str(arg)

        if redact_next:
            redact_next = False
            if not arg_str.startswith("-"):
                result.append("[REDACTED]")
                continue
            # The previous sensitive flag was boolean (e.g. --use-auth): this
            # token is another option, so process it as a flag instead of
            # consuming it, or the value of a following --password would leak.

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

        # Heuristic 3: non-flag KEY=VALUE (e.g. env DB_PASSWORD=x, Hydra api_key=x)
        if "=" in arg_str and not any(ch.isspace() for ch in arg_str.split("=", 1)[0]):
            parts = arg_str.split("=", 1)
            key_part, val_part = parts[0], parts[1]
            if re.match(r"^[A-Za-z_][A-Za-z0-9_.-]*$", key_part):
                if pattern.search(key_part):
                    result.append(f"{key_part}=[REDACTED]")
                    continue
                redacted_val = _redact_value_string_heuristics(val_part, config)
                result.append(f"{key_part}={redacted_val}")
                continue

        if any(ch.isspace() for ch in arg_str):
            def _replace_kv(match: re.Match) -> str:
                key = match.group("key")
                if pattern.search(key.lstrip("-")):
                    return f"{match.group('prefix')}{key}{match.group('sep')}[REDACTED]"
                return match.group(0)

            arg_str = _redact_value_string_heuristics(arg_str, config)
            arg_str = _DIAG_KV_EQ_RE.sub(_replace_kv, arg_str)
            arg_str = _redact_flag_space_values(arg_str, pattern)
        else:
            arg_str = _redact_value_string_heuristics(arg_str, config)
        result.append(arg_str)

    return result


# Pre-compiled patterns for bounded diagnostic error-message redaction.
_DIAG_URI_USERPASS_RE = re.compile(
    r"([a-zA-Z0-9+.-]+)://([^\s/:@]*):([^\s/@]+)@([^\s/]+)"
)
_DIAG_URI_TOKEN_RE = re.compile(
    r"([a-zA-Z0-9+.-]+)://([^\s/:@]+)@([^\s/]+)"
)
_DIAG_PREFIXED_KEY_RE = re.compile(r"\bsk-[A-Za-z0-9_-]{8,}")
_DIAG_KV_EQ_RE = re.compile(
    r"(?P<prefix>(?:^|[\s,(\[{;]))"
    r"(?P<key>-{0,2}[A-Za-z_][A-Za-z0-9_.-]*)"
    r"(?P<sep>\s*=\s*)"
    r"(?P<val>\"[^\"]*\"|'[^']*'|[^\s,)\];]+)"
)
_DIAG_KV_COLON_RE = re.compile(
    r"(?P<prefix>(?:^|[\s,(\[{;]))"
    r"(?P<key>[A-Za-z_][A-Za-z0-9_.-]*)"
    r"(?P<sep>:(?!//)\s*)"
    r"(?P<val>\"[^\"]*\"|'[^']*'|[^\s,)\];]+)"
)
_DIAG_FLAG_PREFIX_RE = re.compile(
    r"(?:^|(?<=[\s,(\[{;]))(-{1,2}[A-Za-z_][A-Za-z0-9_.-]*)(\s+)"
)
_DIAG_TOKEN_VAL_RE = re.compile(r"\"[^\"]*\"|'[^']*'|[^\s,)\];]+")


def _truncate_detail(text: str, max_len: int) -> str:
    """Truncate text to at most max_len characters, preserving '...' when max_len > 3."""
    if max_len <= 0:
        return ""
    if len(text) <= max_len:
        return text
    if max_len > 3:
        return text[: max_len - 3] + "..."
    return text[:max_len]


def _redact_flag_space_values(text: str, pattern: re.Pattern) -> str:
    """Redact values following sensitive '--flag value' or '-flag value' pairs."""
    out: List[str] = []
    pos = 0
    while pos < len(text):
        match = _DIAG_FLAG_PREFIX_RE.search(text, pos)
        if match is None:
            out.append(text[pos:])
            break
        key_name = match.group(1).lstrip("-")
        if pattern.search(key_name):
            val_match = _DIAG_TOKEN_VAL_RE.match(text, match.end())
            if val_match is not None:
                out.append(text[pos : match.end()])
                out.append("[REDACTED]")
                pos = val_match.end()
                continue
        out.append(text[pos : match.end()])
        pos = match.end()
    return "".join(out)


def _redact_diagnostic_message(
    message: str, config: Optional[Dict[str, Any]] = None
) -> str:
    """Apply heuristic and key-value secret redaction to a single-line error message."""
    pattern = _get_secret_pattern(config)
    redacted = _DIAG_URI_USERPASS_RE.sub(r"\1://\2:[REDACTED]@\4", message)
    redacted = _DIAG_URI_TOKEN_RE.sub(r"\1://[REDACTED]@\3", redacted)
    redacted = _redact_value_string_heuristics(redacted, config)
    redacted = _DIAG_PREFIXED_KEY_RE.sub("[REDACTED]", redacted)

    def _replace_kv(match: re.Match) -> str:
        key = match.group("key")
        if pattern.search(key.lstrip("-")):
            return f"{match.group('prefix')}{key}{match.group('sep')}[REDACTED]"
        return match.group(0)

    redacted = _DIAG_KV_EQ_RE.sub(_replace_kv, redacted)
    redacted = _DIAG_KV_COLON_RE.sub(_replace_kv, redacted)
    redacted = _redact_flag_space_values(redacted, pattern)
    return redacted


def format_safe_error_detail(
    exc: BaseException,
    config: Optional[Dict[str, Any]] = None,
    max_len: int = 240,
) -> str:
    """Format an exception as a single-line, redacted, length-bounded detail string.

    Produces ``"ExcType: redacted message"`` (or ``"ExcType"`` when the message is
    empty) with no traceback. If redaction with a custom ``config`` raises, retries
    with default patterns (``config=None``). If redaction still fails, falls back
    to ``type(exc).__name__`` so this helper never raises or leaks raw text.
    """
    exc_type = type(exc).__name__
    try:
        raw_msg = str(exc)
    except Exception:
        raw_msg = ""

    collapsed = re.sub(r"[\r\n]+", " ", raw_msg).strip()
    if not collapsed:
        return _truncate_detail(exc_type, max_len)

    redacted_msg: Optional[str] = None
    try:
        redacted_msg = _redact_diagnostic_message(collapsed, config)
    except Exception:
        if config is not None:
            try:
                redacted_msg = _redact_diagnostic_message(collapsed, None)
            except Exception:
                redacted_msg = None

    if redacted_msg is None:
        return _truncate_detail(exc_type, max_len)

    redacted_msg = re.sub(r"[\r\n]+", " ", redacted_msg).strip()
    if not redacted_msg:
        return _truncate_detail(exc_type, max_len)

    return _truncate_detail(f"{exc_type}: {redacted_msg}", max_len)
