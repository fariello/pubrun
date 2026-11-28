"""Tests for the untrusted-issue-body attachment-URL extractor (IPD 20260721-2255-01).

The issue body is attacker-controlled. The extractor must surface only a `.json` URL on an
allowlisted GitHub host, treat everything as inert data (no eval/shell), and never raise.
"""
import contextlib
import importlib.util
import sys
from pathlib import Path

import pytest

_HERE = Path(__file__).resolve().parent


@contextlib.contextmanager
def _load_script_isolated(name: str, path: Path):
    """Load a standalone script without leaking sys.path or sys.modules mutations."""
    saved_path = list(sys.path)
    saved_modules = dict(sys.modules)
    added_keys = set()
    replaced_modules = {}
    try:
        spec = importlib.util.spec_from_file_location(name, path)
        assert spec is not None and spec.loader is not None
        mod = importlib.util.module_from_spec(spec)
        sys.modules[name] = mod
        spec.loader.exec_module(mod)
        added_keys = set(sys.modules) - set(saved_modules)
        replaced_modules = {
            k: v for k, v in saved_modules.items() if sys.modules.get(k) is not v
        }
        yield mod
    finally:
        sys.path[:] = saved_path
        for key in added_keys | {name}:
            if key not in saved_modules:
                sys.modules.pop(key, None)
        for key, val in replaced_modules.items():
            sys.modules[key] = val
        if name in saved_modules:
            sys.modules[name] = saved_modules[name]


@pytest.fixture(scope="module")
def x():
    with _load_script_isolated(
        "extract_attachment_url", _HERE / "extract_attachment_url.py"
    ) as mod:
        yield mod


def test_finds_allowlisted_json_attachment(x):
    body = (
        "Here is my result.\n\n"
        "[pubrun-bench-abcd1234-x.redacted.json]"
        "(https://github.com/user-attachments/files/12345/pubrun-bench-abcd1234-x.redacted.json)\n"
    )
    url, error = x.find_attachment_url(body)
    assert error == ""
    assert url.endswith(".redacted.json")
    assert "github.com" in url


def test_objects_host_allowed(x):
    body = "https://objects.githubusercontent.com/foo/bar/result.json"
    url, error = x.find_attachment_url(body)
    assert url == body and error == ""


def test_rejects_off_allowlist_host(x):
    body = "grab this https://evil.example.com/leak.json please"
    url, error = x.find_attachment_url(body)
    assert url == ""
    assert "allowlist" in error


def test_rejects_non_json_attachment(x):
    body = "https://github.com/user-attachments/files/1/screenshot.png"
    url, error = x.find_attachment_url(body)
    assert url == ""
    assert "not a .json" in error


def test_empty_body(x):
    url, error = x.find_attachment_url("")
    assert url == "" and "empty" in error


def test_no_url_in_body(x):
    url, error = x.find_attachment_url("I forgot to attach the file, sorry!")
    assert url == "" and "no URL" in error


def test_injection_shaped_body_is_inert(x):
    # Shell-injection-shaped text must be treated as data and simply not match a valid URL.
    body = "$(rm -rf /) `curl evil` ${IFS}; echo pwned"
    url, error = x.find_attachment_url(body)
    assert url == ""  # nothing executed, nothing matched


def test_first_valid_json_wins_over_later_noise(x):
    body = (
        "notes https://github.com/foo/img.png and the file "
        "https://objects.githubusercontent.com/x/result.json trailing.text"
    )
    url, error = x.find_attachment_url(body)
    assert url == "https://objects.githubusercontent.com/x/result.json"
    assert error == ""


def test_host_allowlist_matches_validator(x):
    # The extractor's allowlist must stay in lockstep with the validator's.
    pytest.importorskip("jsonschema")
    with _load_script_isolated(
        "validate_benchmark_submission", _HERE / "validate_benchmark_submission.py"
    ) as v:
        assert set(x.ALLOWED_ATTACHMENT_HOSTS) == set(v.ALLOWED_ATTACHMENT_HOSTS)


# --- gist host + kind-based source resolution + inline extraction (IPD 20260722-1930-01) ---

def test_gist_raw_host_allowed(x):
    body = "https://gist.githubusercontent.com/user/abc/raw/xyz/result.redacted.json"
    url, error = x.find_attachment_url(body)
    assert url == body and error == ""


def test_gist_html_page_rejected_as_data_url(x):
    # The gist HTML PAGE host is not the raw host and the page path is not .json.
    body = "https://gist.github.com/user/deadbeef"
    url, error = x.find_attachment_url(body)
    assert url == ""


def test_resolve_source_url_kind(x):
    body = "see https://gist.githubusercontent.com/u/a/raw/z/r.json"
    kind, url, file, error = x.resolve_source(body)
    assert kind == "url" and url.endswith(".json") and error == ""


def test_resolve_source_inline_kind(x):
    body = (
        x.SUBMISSION_MARKER + "\n\n"
        "```json\n{\"schema\": \"pubrun-benchmark/5\"}\n```\n"
    )
    kind, url, file, error = x.resolve_source(body)
    assert kind == "inline" and file == x.INLINE_OUT and error == ""


def test_inline_requires_marker(x):
    body = "```json\n{\"schema\": \"pubrun-benchmark/5\"}\n```\n"  # no marker
    payload, error = x.find_inline_json(body)
    assert payload == "" and "marker" in error


def test_inline_rejects_multiple_blocks(x):
    body = (
        x.SUBMISSION_MARKER + "\n"
        "```json\n{\"a\":1}\n```\n"
        "```json\n{\"b\":2}\n```\n"
    )
    payload, error = x.find_inline_json(body)
    assert payload == "" and "multiple" in error


def test_inline_rejects_zero_blocks(x):
    body = x.SUBMISSION_MARKER + "\n\n(no code block here)"
    payload, error = x.find_inline_json(body)
    assert payload == "" and "no ```json" in error


def test_inline_rejects_oversize_before_parse(x):
    big = "x" * (x.MAX_INLINE_BYTES + 10)
    body = x.SUBMISSION_MARKER + "\n```json\n" + big + "\n```\n"
    payload, error = x.find_inline_json(body)
    assert payload == "" and "size cap" in error


def test_url_wins_over_inline_when_both_present(x):
    body = (
        x.SUBMISSION_MARKER + "\n"
        "link https://gist.githubusercontent.com/u/a/raw/z/r.json\n"
        "```json\n{\"schema\":\"pubrun-benchmark/5\"}\n```\n"
    )
    kind, url, file, error = x.resolve_source(body)
    assert kind == "url"


def test_resolve_source_none_when_empty(x):
    kind, url, file, error = x.resolve_source("nothing useful here")
    assert kind == "none" and error
