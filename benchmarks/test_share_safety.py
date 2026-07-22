"""Tests for benchmarks/share_safety.py (IPD 20260721-2255-01).

The share-safety validator is the load-bearing local privacy defense for the attach-a-file
submission flow (a public attachment uploads before the server validates, so the local
check is what actually prevents a leak). These tests pin its structural behavior.
"""
import copy
import importlib.util
import json
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("share_safety", _HERE / "share_safety.py")
assert _spec is not None and _spec.loader is not None
ss = importlib.util.module_from_spec(_spec)
sys.modules["share_safety"] = ss
_spec.loader.exec_module(ss)

# A minimal, correctly-redacted result skeleton (the shape the harness produces).
_SAFE = {
    "schema": "pubrun-benchmark/5",
    "machine": {
        "host": {"os_name": "Linux", "hostname": "<redacted>"},
        "python": {
            "executable": "<redacted>",
            "prefix": "<redacted>",
            "base_prefix": "<redacted>",
            "virtual_env": "<redacted>",
        },
        "python_executable": "<redacted>",
    },
}


def test_redacted_result_is_safe():
    ok, reasons = ss.check_share_safe(copy.deepcopy(_SAFE))
    assert ok, reasons
    assert reasons == []


def test_unredacted_hostname_rejected():
    r = copy.deepcopy(_SAFE)
    r["machine"]["host"]["hostname"] = "build-box-07"
    ok, reasons = ss.check_share_safe(r)
    assert not ok
    assert any("machine.host.hostname" in x for x in reasons)
    # The raw leaked value must NOT be echoed in the reason (do not re-leak).
    assert all("build-box-07" not in x for x in reasons)


def test_unredacted_python_executable_rejected():
    r = copy.deepcopy(_SAFE)
    r["machine"]["python"]["executable"] = "/home/alice/venv/bin/python"
    ok, reasons = ss.check_share_safe(r)
    assert not ok
    # Both the field-marker rule and the home-path scan should fire.
    assert any("machine.python.executable" in x for x in reasons)
    assert any("home or user-profile path" in x for x in reasons)


def test_home_path_anywhere_rejected():
    r = copy.deepcopy(_SAFE)
    r["notes"] = "ran from /home/bob/project"
    ok, reasons = ss.check_share_safe(r)
    assert not ok
    assert any("home or user-profile path" in x for x in reasons)


def test_windows_userprofile_path_rejected():
    r = copy.deepcopy(_SAFE)
    r["notes"] = r"output at C:\\Users\\carol\\runs"
    ok, reasons = ss.check_share_safe(r)
    assert not ok
    assert any("home or user-profile path" in x for x in reasons)


def test_missing_field_is_not_unsafe():
    # A partial/older result that simply omits a field is not, by that alone, unsafe.
    r = {"schema": "pubrun-benchmark/5", "machine": {"host": {"hostname": "<redacted>"}}}
    ok, reasons = ss.check_share_safe(r)
    assert ok, reasons


def test_text_wrapper_parse_failure():
    ok, reasons = ss.check_share_safe_text("{not valid json")
    assert not ok
    assert reasons and "not valid JSON" in reasons[0]


def test_text_wrapper_non_object():
    ok, reasons = ss.check_share_safe_text("[1, 2, 3]")
    assert not ok
    assert any("not an object" in x for x in reasons)


def test_version_is_exposed():
    assert isinstance(ss.SHARE_SAFETY_VERSION, int) and ss.SHARE_SAFETY_VERSION >= 1
