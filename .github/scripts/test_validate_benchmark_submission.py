"""Tests for the first-party benchmark submission validator (IPD 20260721-2255-01).

The validator is an Internet-facing parser; its whole security value is rejecting tampered/
unredacted/oversized/malformed payloads while accepting a genuine redacted /5 result. These
tests run it against the committed adversarial fixture corpus and pin the accept/reject
outcome AND the failing stage for each. Requires the dev-only jsonschema dependency.
"""
import importlib.util
import sys
from pathlib import Path

import pytest

_HERE = Path(__file__).resolve().parent
_FX = _HERE / "test_fixtures"


@pytest.fixture(scope="module")
def v():
    """Load validate_benchmark_submission lazily and restore sys.path/sys.modules on teardown."""
    pytest.importorskip("jsonschema")
    saved_path = list(sys.path)
    saved_modules = dict(sys.modules)
    added_keys = set()
    replaced_modules = {}
    name = "validate_benchmark_submission"
    try:
        spec = importlib.util.spec_from_file_location(
            name, _HERE / "validate_benchmark_submission.py"
        )
        assert spec is not None and spec.loader is not None
        mod = importlib.util.module_from_spec(spec)
        sys.modules[name] = mod
        spec.loader.exec_module(mod)
        added_keys = set(sys.modules) - set(saved_modules)
        replaced_modules = {
            k: val for k, val in saved_modules.items() if sys.modules.get(k) is not val
        }
        yield mod
    finally:
        sys.path[:] = saved_path
        for key in added_keys | {name, "share_safety"}:
            if key not in saved_modules:
                sys.modules.pop(key, None)
        for key, val in replaced_modules.items():
            sys.modules[key] = val
        for key in (name, "share_safety"):
            if key in saved_modules:
                sys.modules[key] = saved_modules[key]


def _verdict(v, name):
    return v.validate_file(_FX / name)


def test_valid_result_accepted(v):
    verdict = _verdict(v, "valid.json")
    assert verdict["accepted"] is True, verdict


# name -> expected failing stage
_REJECTS = {
    "not_json.json": "parse",
    "not_object.json": "parse",
    "wrong_schema.json": "schema",
    "missing_required.json": "schema",
    "negative_timing.json": "schema",       # schema's minimum:0 catches it (defense in depth)
    "unredacted_hostname.json": "share-safety",
    "home_path.json": "share-safety",
}


@pytest.mark.parametrize("name,stage", sorted(_REJECTS.items()))
def test_adversarial_rejected(v, name, stage):
    verdict = _verdict(v, name)
    assert verdict["accepted"] is False, f"{name} should be rejected: {verdict}"
    assert verdict["stage"] == stage, f"{name}: expected stage {stage}, got {verdict['stage']}"
    # A rejection reason must never echo a raw leaked value (hostname/home path).
    assert "build-box-07" not in verdict["reason"]
    assert "/home/alice" not in verdict["reason"]


def test_injection_shaped_value_is_inert_data(v):
    # A shell-injection-shaped string in an allowed field is treated as inert DATA:
    # it is neither executed nor a leak, so a schema+share-safe result is accepted.
    verdict = _verdict(v, "injection_inert.json")
    assert verdict["accepted"] is True, verdict


def test_oversized_rejected(v, tmp_path):
    big = tmp_path / "big.json"
    big.write_text("{}" + " " * (v.MAX_BYTES + 10), encoding="utf-8")
    verdict = v.validate_file(big)
    assert verdict["accepted"] is False
    assert verdict["stage"] == "shape"


def test_non_json_suffix_rejected(v, tmp_path):
    f = tmp_path / "result.txt"
    f.write_text("{}", encoding="utf-8")
    verdict = v.validate_file(f)
    assert verdict["accepted"] is False
    assert verdict["stage"] == "shape"


def test_missing_file_rejected(v, tmp_path):
    verdict = v.validate_file(tmp_path / "does-not-exist.json")
    assert verdict["accepted"] is False
    assert verdict["stage"] == "shape"


def test_download_rejects_non_allowlisted_host(v):
    # _download must fail closed on a host not in the allowlist, before any fetch.
    with pytest.raises(v.Reject) as ei:
        v._download("https://evil.example.com/x.json", Path("/tmp/x.json"))
    assert ei.value.stage == "shape"


def test_verdict_never_contains_payload(v):
    # Even the accepted verdict is a small fixed structure, not the payload.
    verdict = _verdict(v, "valid.json")
    assert set(verdict.keys()) <= {"accepted", "stage", "reason", "share_safety_version"}


def test_gist_raw_host_on_allowlist(v):
    # IPD 20260722-1930-01: gist raw host is accepted (exact match, never suffix-matched).
    assert "gist.githubusercontent.com" in v.ALLOWED_ATTACHMENT_HOSTS


def test_gist_lookalike_host_rejected(v):
    # A lookalike that merely ends with githubusercontent.com must NOT be accepted.
    with pytest.raises(v.Reject) as ei:
        v._download("https://evil-gist.githubusercontent.com.attacker.tld/x.json",
                    Path("/tmp/x.json"))
    assert ei.value.stage == "shape"
