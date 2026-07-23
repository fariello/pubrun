"""Tests for the first-party benchmark submission validator (IPD 20260721-2255-01).

The validator is an Internet-facing parser; its whole security value is rejecting tampered/
unredacted/oversized/malformed payloads while accepting a genuine redacted /5 result. These
tests run it against the committed adversarial fixture corpus and pin the accept/reject
outcome AND the failing stage for each. Requires the dev-only jsonschema dependency.
"""
import importlib.util
import json
import sys
from pathlib import Path

import pytest

pytest.importorskip("jsonschema")

_HERE = Path(__file__).resolve().parent
_FX = _HERE / "test_fixtures"
_spec = importlib.util.spec_from_file_location(
    "validate_benchmark_submission", _HERE / "validate_benchmark_submission.py"
)
assert _spec is not None and _spec.loader is not None
v = importlib.util.module_from_spec(_spec)
sys.modules["validate_benchmark_submission"] = v
_spec.loader.exec_module(v)


def _verdict(name):
    return v.validate_file(_FX / name)


def test_valid_result_accepted():
    verdict = _verdict("valid.json")
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
def test_adversarial_rejected(name, stage):
    verdict = _verdict(name)
    assert verdict["accepted"] is False, f"{name} should be rejected: {verdict}"
    assert verdict["stage"] == stage, f"{name}: expected stage {stage}, got {verdict['stage']}"
    # A rejection reason must never echo a raw leaked value (hostname/home path).
    assert "build-box-07" not in verdict["reason"]
    assert "/home/alice" not in verdict["reason"]


def test_injection_shaped_value_is_inert_data():
    # A shell-injection-shaped string in an allowed field is treated as inert DATA:
    # it is neither executed nor a leak, so a schema+share-safe result is accepted.
    verdict = _verdict("injection_inert.json")
    assert verdict["accepted"] is True, verdict


def test_oversized_rejected(tmp_path):
    big = tmp_path / "big.json"
    big.write_text("{}" + " " * (v.MAX_BYTES + 10), encoding="utf-8")
    verdict = v.validate_file(big)
    assert verdict["accepted"] is False
    assert verdict["stage"] == "shape"


def test_non_json_suffix_rejected(tmp_path):
    f = tmp_path / "result.txt"
    f.write_text("{}", encoding="utf-8")
    verdict = v.validate_file(f)
    assert verdict["accepted"] is False
    assert verdict["stage"] == "shape"


def test_missing_file_rejected(tmp_path):
    verdict = v.validate_file(tmp_path / "does-not-exist.json")
    assert verdict["accepted"] is False
    assert verdict["stage"] == "shape"


def test_download_rejects_non_allowlisted_host():
    # _download must fail closed on a host not in the allowlist, before any fetch.
    with pytest.raises(v.Reject) as ei:
        v._download("https://evil.example.com/x.json", Path("/tmp/x.json"))
    assert ei.value.stage == "shape"


def test_verdict_never_contains_payload():
    # Even the accepted verdict is a small fixed structure, not the payload.
    verdict = _verdict("valid.json")
    assert set(verdict.keys()) <= {"accepted", "stage", "reason", "share_safety_version"}


def test_gist_raw_host_on_allowlist():
    # IPD 20260722-1930-01: gist raw host is accepted (exact match, never suffix-matched).
    assert "gist.githubusercontent.com" in v.ALLOWED_ATTACHMENT_HOSTS


def test_gist_lookalike_host_rejected():
    # A lookalike that merely ends with githubusercontent.com must NOT be accepted.
    with pytest.raises(v.Reject) as ei:
        v._download("https://evil-gist.githubusercontent.com.attacker.tld/x.json",
                    Path("/tmp/x.json"))
    assert ei.value.stage == "shape"
