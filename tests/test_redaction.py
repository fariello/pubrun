"""Tests for the redaction engine (T1)."""
import pytest
from pubrun.capture.redaction import (
    is_secret_key, redact_value, redact_env_vars, redact_argv,
    DEFAULT_SECRET_REGEX
)


class TestIsSecretKey:
    """Validate secret-key detection heuristics."""

    @pytest.mark.parametrize("key", [
        "AWS_SECRET_ACCESS_KEY",
        "API_TOKEN",
        "DB_PASSWORD",
        "GITHUB_AUTH_TOKEN",
        "MY_PRIVATE_KEY",
        "DATABASE_URL",
        "REDIS_DSN",
        "CONN_STR",
        "CONNECTION_STRING",
        "JWT_SIGNING_KEY",
        "BEARER_TOKEN",
        "SSH_KEY",
        "user_credentials",
    ])
    def test_detects_secrets(self, key):
        assert is_secret_key(key) is True

    @pytest.mark.parametrize("key", [
        "PATH",
        "HOME",
        "LANG",
        "TERM",
        "SHELL",
        "USER",
        "HOSTNAME",
        "PWD",
        "DISPLAY",
        "XDG_SESSION_TYPE",
    ])
    def test_ignores_safe_keys(self, key):
        assert is_secret_key(key) is False


class TestRedactValue:
    def test_default_redacted(self):
        result = redact_value("super_secret_123")
        assert result == {"representation": "redacted"}

    def test_hashed_mode(self):
        config = {"redaction": {"representation": "hashed"}}
        result = redact_value("test_password", config)
        assert result["representation"] == "hashed"
        assert result["hash_algorithm"] == "sha256"
        assert len(result["hash_value"]) == 64  # SHA-256 hex length

    def test_hashed_deterministic(self):
        config = {"redaction": {"representation": "hashed"}}
        r1 = redact_value("same_secret", config)
        r2 = redact_value("same_secret", config)
        assert r1["hash_value"] == r2["hash_value"]

    def test_hashed_different_values(self):
        config = {"redaction": {"representation": "hashed"}}
        r1 = redact_value("secret_a", config)
        r2 = redact_value("secret_b", config)
        assert r1["hash_value"] != r2["hash_value"]


class TestRedactEnvVars:
    def test_redacts_secrets_and_preserves_safe(self):
        env = {"PATH": "/usr/bin", "API_TOKEN": "sk-live-xxx", "HOME": "/home/user"}
        result = redact_env_vars(env)
        by_name = {r["name"]: r for r in result}

        assert by_name["PATH"]["value"]["representation"] == "plain"
        assert by_name["PATH"]["value"]["value"] == "/usr/bin"
        assert by_name["API_TOKEN"]["value"]["representation"] == "redacted"
        assert "value" not in by_name["API_TOKEN"]["value"]

    def test_disabled_via_config(self):
        config = {"redaction": {"env_enabled": False}}
        env = {"API_TOKEN": "sk-live-xxx"}
        result = redact_env_vars(env, config)
        assert result[0]["value"]["representation"] == "plain"
        assert result[0]["value"]["value"] == "sk-live-xxx"

    def test_custom_regex(self):
        config = {"redaction": {"sensitive_keys_regex": "(?i)(MY_CUSTOM_VAR)"}}
        env = {"MY_CUSTOM_VAR": "secret", "API_TOKEN": "visible"}
        result = redact_env_vars(env, config)
        by_name = {r["name"]: r for r in result}
        assert by_name["MY_CUSTOM_VAR"]["value"]["representation"] == "redacted"
        assert by_name["API_TOKEN"]["value"]["representation"] == "plain"


class TestRedactArgv:
    def test_flag_equals_value(self):
        argv = ["script.py", "--api-key=sk-live-xxx", "--verbose"]
        result = redact_argv(argv)
        assert result == ["script.py", "--api-key=[REDACTED]", "--verbose"]

    def test_flag_space_value(self):
        argv = ["script.py", "--password", "my_secret", "--epochs", "10"]
        result = redact_argv(argv)
        assert result == ["script.py", "--password", "[REDACTED]", "--epochs", "10"]

    def test_no_secrets(self):
        argv = ["script.py", "--epochs", "10", "data.csv"]
        result = redact_argv(argv)
        assert result == ["script.py", "--epochs", "10", "data.csv"]

    def test_disabled_via_config(self):
        config = {"redaction": {"argv_enabled": False}}
        argv = ["script.py", "--api-key=sk-live-xxx"]
        result = redact_argv(argv, config)
        assert result == ["script.py", "--api-key=sk-live-xxx"]

    def test_returns_new_list(self):
        argv = ["script.py", "--verbose"]
        result = redact_argv(argv)
        assert result is not argv
