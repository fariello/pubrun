"""Tests for the untrusted-issue-body attachment-URL extractor (IPD 20260721-2255-01).

The issue body is attacker-controlled. The extractor must surface only a `.json` URL on an
allowlisted GitHub host, treat everything as inert data (no eval/shell), and never raise.
"""
import importlib.util
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location(
    "extract_attachment_url", _HERE / "extract_attachment_url.py"
)
assert _spec is not None and _spec.loader is not None
x = importlib.util.module_from_spec(_spec)
sys.modules["extract_attachment_url"] = x
_spec.loader.exec_module(x)


def test_finds_allowlisted_json_attachment():
    body = (
        "Here is my result.\n\n"
        "[pubrun-bench-abcd1234-x.redacted.json]"
        "(https://github.com/user-attachments/files/12345/pubrun-bench-abcd1234-x.redacted.json)\n"
    )
    url, error = x.find_attachment_url(body)
    assert error == ""
    assert url.endswith(".redacted.json")
    assert "github.com" in url


def test_objects_host_allowed():
    body = "https://objects.githubusercontent.com/foo/bar/result.json"
    url, error = x.find_attachment_url(body)
    assert url == body and error == ""


def test_rejects_off_allowlist_host():
    body = "grab this https://evil.example.com/leak.json please"
    url, error = x.find_attachment_url(body)
    assert url == ""
    assert "allowlist" in error


def test_rejects_non_json_attachment():
    body = "https://github.com/user-attachments/files/1/screenshot.png"
    url, error = x.find_attachment_url(body)
    assert url == ""
    assert "not a .json" in error


def test_empty_body():
    url, error = x.find_attachment_url("")
    assert url == "" and "empty" in error


def test_no_url_in_body():
    url, error = x.find_attachment_url("I forgot to attach the file, sorry!")
    assert url == "" and "no URL" in error


def test_injection_shaped_body_is_inert():
    # Shell-injection-shaped text must be treated as data and simply not match a valid URL.
    body = "$(rm -rf /) `curl evil` ${IFS}; echo pwned"
    url, error = x.find_attachment_url(body)
    assert url == ""  # nothing executed, nothing matched


def test_first_valid_json_wins_over_later_noise():
    body = (
        "notes https://github.com/foo/img.png and the file "
        "https://objects.githubusercontent.com/x/result.json trailing.text"
    )
    url, error = x.find_attachment_url(body)
    assert url == "https://objects.githubusercontent.com/x/result.json"
    assert error == ""


def test_host_allowlist_matches_validator():
    # The extractor's allowlist must stay in lockstep with the validator's.
    vspec = importlib.util.spec_from_file_location(
        "validate_benchmark_submission", _HERE / "validate_benchmark_submission.py"
    )
    assert vspec is not None and vspec.loader is not None
    import pytest
    pytest.importorskip("jsonschema")
    v = importlib.util.module_from_spec(vspec)
    sys.modules["validate_benchmark_submission"] = v
    vspec.loader.exec_module(v)
    assert set(x.ALLOWED_ATTACHMENT_HOSTS) == set(v.ALLOWED_ATTACHMENT_HOSTS)


# --- gist host + kind-based source resolution + inline extraction (IPD 20260722-1930-01) ---

def test_gist_raw_host_allowed():
    body = "https://gist.githubusercontent.com/user/abc/raw/xyz/result.redacted.json"
    url, error = x.find_attachment_url(body)
    assert url == body and error == ""


def test_gist_html_page_rejected_as_data_url():
    # The gist HTML PAGE host is not the raw host and the page path is not .json.
    body = "https://gist.github.com/user/deadbeef"
    url, error = x.find_attachment_url(body)
    assert url == ""


def test_resolve_source_url_kind():
    body = "see https://gist.githubusercontent.com/u/a/raw/z/r.json"
    kind, url, file, error = x.resolve_source(body)
    assert kind == "url" and url.endswith(".json") and error == ""


def test_resolve_source_inline_kind():
    body = (
        x.SUBMISSION_MARKER + "\n\n"
        "```json\n{\"schema\": \"pubrun-benchmark/5\"}\n```\n"
    )
    kind, url, file, error = x.resolve_source(body)
    assert kind == "inline" and file == x.INLINE_OUT and error == ""


def test_inline_requires_marker():
    body = "```json\n{\"schema\": \"pubrun-benchmark/5\"}\n```\n"  # no marker
    payload, error = x.find_inline_json(body)
    assert payload == "" and "marker" in error


def test_inline_rejects_multiple_blocks():
    body = (
        x.SUBMISSION_MARKER + "\n"
        "```json\n{\"a\":1}\n```\n"
        "```json\n{\"b\":2}\n```\n"
    )
    payload, error = x.find_inline_json(body)
    assert payload == "" and "multiple" in error


def test_inline_rejects_zero_blocks():
    body = x.SUBMISSION_MARKER + "\n\n(no code block here)"
    payload, error = x.find_inline_json(body)
    assert payload == "" and "no ```json" in error


def test_inline_rejects_oversize_before_parse():
    big = "x" * (x.MAX_INLINE_BYTES + 10)
    body = x.SUBMISSION_MARKER + "\n```json\n" + big + "\n```\n"
    payload, error = x.find_inline_json(body)
    assert payload == "" and "size cap" in error


def test_url_wins_over_inline_when_both_present():
    body = (
        x.SUBMISSION_MARKER + "\n"
        "link https://gist.githubusercontent.com/u/a/raw/z/r.json\n"
        "```json\n{\"schema\":\"pubrun-benchmark/5\"}\n```\n"
    )
    kind, url, file, error = x.resolve_source(body)
    assert kind == "url"


def test_resolve_source_none_when_empty():
    kind, url, file, error = x.resolve_source("nothing useful here")
    assert kind == "none" and error
