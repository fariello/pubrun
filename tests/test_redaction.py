"""Tests for the redaction engine (T1)."""
import json
from pathlib import Path

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


def _env_by_name(env, config=None):
    return {entry["name"]: entry["value"] for entry in redact_env_vars(env, config)}


class TestValueHeuristics:
    def test_json_object_in_env_value(self):
        payload = {
            "api_key": "k_secret",
            "nested": {"password": "pw_secret"},
            "items": [{"token": 7}, "plain"],
            "n": 3,
        }
        vals = _env_by_name({"APP_CONFIG": json.dumps(payload)})
        assert vals["APP_CONFIG"]["representation"] == "plain"
        decoded = json.loads(vals["APP_CONFIG"]["value"])
        assert decoded == {
            "api_key": "[REDACTED]",
            "nested": {"password": "[REDACTED]"},
            "items": [{"token": "[REDACTED]"}, "plain"],
            "n": 3,
        }

    def test_json_array_in_argv_value(self):
        raw_array = json.dumps(["sk-" + "a" * 24, {"secret": "s"}, 1.5, None])
        result = redact_argv(["s.py", raw_array])
        assert json.loads(result[1]) == ["[REDACTED]", {"secret": "[REDACTED]"}, 1.5, None]

    def test_invalid_json_falls_back_to_string_heuristics(self):
        raw = "{not json: postgres://u:pw@db/x Bearer abc.def}"
        vals = _env_by_name({"NOTE": raw})
        assert vals["NOTE"]["value"] == (
            "{not json: postgres://u:[REDACTED]@db/x Bearer [REDACTED]}"
        )

    def test_classic_sk_and_bearer_in_env_values(self):
        classic_key = "sk-" + "A1" * 12
        jwt_tok = "eyJhbGciOiJIUzI1NiJ9.payload.sig"
        vals = _env_by_name({
            "MSG": f"use {classic_key} today",
            "HEADER": f"Authorization: Bearer {jwt_tok}",
        })
        assert vals["MSG"]["value"] == "use [REDACTED] today"
        assert vals["HEADER"]["value"].endswith("Bearer [REDACTED]")
        assert jwt_tok not in vals["HEADER"]["value"]

    def test_uri_token_in_argv_positional(self):
        assert redact_argv(["s.py", "https://ghp_abc123@github.com/o/r.git"]) == [
            "s.py",
            "https://[REDACTED]@github.com/o/r.git",
        ]
        note_key = "sk-" + "b" * 22
        assert redact_argv(
            ["s.py", "--db=postgres://u:pw@h/db", f"--note={note_key}"]
        ) == [
            "s.py",
            "--db=postgres://u:[REDACTED]@h/db",
            "--note=[REDACTED]",
        ]

    def test_non_string_argv_entries_are_stringified(self):
        data_path = Path("data") / "x.csv"
        result = redact_argv(["s.py", data_path, 3, "--password", Path("pw.txt")])
        assert result == ["s.py", str(data_path), "3", "--password", "[REDACTED]"]

    def test_hyphenated_prefixed_key_in_values(self):
        key = "sk-" + "proj-abc123_def456-7890xyzABC"
        vals = _env_by_name({"NOTE": f"key {key} end"})
        assert vals["NOTE"]["value"] == "key [REDACTED] end"

        json_arg = json.dumps({"openai": key})
        res_json = redact_argv(["s.py", json_arg])
        assert json.loads(res_json[1]) == {"openai": "[REDACTED]"}

        res_pos = redact_argv(["s.py", key])
        assert res_pos == ["s.py", "[REDACTED]"]

    def test_short_sk_text_is_kept(self):
        text = "task-runner sk-short sk-proj-tiny"
        vals = _env_by_name({"NOTE": text})
        assert vals["NOTE"]["value"] == text
        assert redact_argv(["s.py", text]) == ["s.py", text]
