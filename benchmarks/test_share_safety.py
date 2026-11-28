"""Tests for benchmarks/share_safety.py (IPD 20260721-2255-01).

The share-safety validator is the load-bearing local privacy defense for the attach-a-file
submission flow (a public attachment uploads before the server validates, so the local
check is what actually prevents a leak). These tests pin its structural behavior.
"""
import copy
import getpass
import importlib.util
import json
import platform
import sys
from pathlib import Path

import pytest

_HERE = Path(__file__).resolve().parent


def _load_scoped(mod_name: str, file_path: Path):
    before_path = list(sys.path)
    before_modules = dict(sys.modules)
    spec = importlib.util.spec_from_file_location(mod_name, file_path)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules[mod_name] = mod
    try:
        spec.loader.exec_module(mod)
    except Exception:
        sys.path[:] = before_path
        for name in list(sys.modules):
            if name not in before_modules:
                sys.modules.pop(name, None)
        for name, prev in before_modules.items():
            if sys.modules.get(name) is not prev:
                sys.modules[name] = prev
        raise
    added = [name for name in sys.modules if name not in before_modules]
    overwritten = {
        name: prev
        for name, prev in before_modules.items()
        if sys.modules.get(name) is not prev
    }

    def _restore() -> None:
        sys.path[:] = before_path
        for name in added:
            sys.modules.pop(name, None)
        for name, prev in overwritten.items():
            sys.modules[name] = prev

    return mod, _restore


@pytest.fixture(scope="module")
def ss():
    mod, restore = _load_scoped("share_safety", _HERE / "share_safety.py")
    try:
        yield mod
    finally:
        restore()


@pytest.fixture(scope="module")
def scaling_bench():
    mod, restore = _load_scoped("scaling_bench", _HERE / "scaling_bench.py")
    try:
        yield mod
    finally:
        restore()


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


def test_redacted_result_is_safe(ss):
    ok, reasons = ss.check_share_safe(copy.deepcopy(_SAFE))
    assert ok, reasons
    assert reasons == []


def test_unredacted_hostname_rejected(ss):
    r = copy.deepcopy(_SAFE)
    r["machine"]["host"]["hostname"] = "build-box-07"
    ok, reasons = ss.check_share_safe(r)
    assert not ok
    assert any("machine.host.hostname" in x for x in reasons)
    # The raw leaked value must NOT be echoed in the reason (do not re-leak).
    assert all("build-box-07" not in x for x in reasons)


def test_unredacted_python_executable_rejected(ss):
    r = copy.deepcopy(_SAFE)
    r["machine"]["python"]["executable"] = "/home/alice/venv/bin/python"
    ok, reasons = ss.check_share_safe(r)
    assert not ok
    # Both the field-marker rule and the home-path scan should fire.
    assert any("machine.python.executable" in x for x in reasons)
    assert any("home or user-profile path" in x for x in reasons)


def test_home_path_anywhere_rejected(ss):
    r = copy.deepcopy(_SAFE)
    r["notes"] = "ran from /home/bob/project"
    ok, reasons = ss.check_share_safe(r)
    assert not ok
    assert any("home or user-profile path" in x for x in reasons)


def test_windows_userprofile_path_rejected(ss):
    r = copy.deepcopy(_SAFE)
    r["notes"] = r"output at C:\\Users\\carol\\runs"
    ok, reasons = ss.check_share_safe(r)
    assert not ok
    assert any("home or user-profile path" in x for x in reasons)


def test_missing_field_is_not_unsafe(ss):
    # A partial/older result that simply omits a field is not, by that alone, unsafe.
    r = {"schema": "pubrun-benchmark/5", "machine": {"host": {"hostname": "<redacted>"}}}
    ok, reasons = ss.check_share_safe(r)
    assert ok, reasons


def test_text_wrapper_parse_failure(ss):
    ok, reasons = ss.check_share_safe_text("{not valid json")
    assert not ok
    assert reasons and "not valid JSON" in reasons[0]


def test_text_wrapper_non_object(ss):
    ok, reasons = ss.check_share_safe_text("[1, 2, 3]")
    assert not ok
    assert any("not an object" in x for x in reasons)


def test_version_is_exposed(ss):
    assert isinstance(ss.SHARE_SAFETY_VERSION, int) and ss.SHARE_SAFETY_VERSION >= 1


def _sample_scaling_result(schema_version: str) -> dict:
    return {
        "schema_version": schema_version,
        "mode": "quick",
        "started_at_utc": "2026-11-27T00:00:00+00:00",
        "finished_at_utc": "2026-11-27T00:00:01+00:00",
        "environment": {
            "python_version": "3.12.0",
            "python_implementation": "CPython",
            "platform": "Linux 6.8.0",
            "cpu": {"model": "Test CPU", "logical_cores": 8, "architecture": "x86_64"},
            "pubrun_version": "1.0.0",
        },
        "git_revision": "abcdef123456",
        "workdir_fstype": "ext4",
        "workdir_is_network": False,
        "workdir_kind": "temporary",
        "scenarios": {
            "file_io": {
                "file_count": 200,
                "rounds": 3,
                "open_median_ms": 1.0,
                "open_elapsed_ms": 3.0,
                "open_ms_per_1000": 5.0,
                "open_tracked_records": 200,
                "register_input_median_ms": 1.0,
                "register_input_elapsed_ms": 3.0,
                "register_input_ms_per_1000": 5.0,
                "register_input_tracked_records": 200,
                "total_elapsed_ms": 2.0,
            },
            "run_scan_lookup": {
                "run_count": 100,
                "scanned_count": 100,
                "rounds": 3,
                "scan_median_ms": 1.0,
                "scan_elapsed_ms": 3.0,
                "scan_ms_per_1000": 10.0,
                "find_exact_id_with_runs_median_ms": 0.1,
                "find_recency_with_runs_median_ms": 0.1,
                "find_exact_id_direct_median_ms": 0.2,
                "scan_manifest_parses": 100,
                "find_with_runs_manifest_parses": 0,
                "find_direct_manifest_parses": 1,
            },
            "inactive_hot_path": {
                "call_count": 1000,
                "rounds": 3,
                "annotate_median_ms": 0.5,
                "annotate_elapsed_ms": 1.5,
                "annotate_us_per_call": 0.5,
                "print_median_ms": 0.5,
                "print_elapsed_ms": 1.5,
                "print_us_per_call": 0.5,
            },
            "large_manifest_diff": {
                "package_count": 100,
                "env_count": 100,
                "array_length": 200,
                "rounds": 3,
                "standard_diff_median_ms": 1.0,
                "standard_diff_elapsed_ms": 3.0,
                "standard_diff_changes": 10,
                "deep_diff_median_ms": 1.5,
                "deep_diff_elapsed_ms": 4.5,
                "deep_diff_changes": 10,
                "array_diff_median_ms": 0.4,
                "array_diff_elapsed_ms": 1.2,
                "array_diff_us_per_element": 2.0,
            },
        },
    }


@pytest.mark.parametrize("username", ["ext4", "temporary"])
def test_scaling_bench_skip_keys_and_protected_schema_not_false_positive(
    scaling_bench, monkeypatch, username
):
    """BUG-E6: scaling_bench._validate_share_safety respects its own skip keys and schema literal."""
    monkeypatch.setattr(getpass, "getuser", lambda: username)
    monkeypatch.setattr(platform, "node", lambda: "bench-box-01")
    monkeypatch.setenv("USER", "ext4")
    monkeypatch.setenv("LOGNAME", "temporary")
    monkeypatch.delenv("USERNAME", raising=False)

    raw = _sample_scaling_result(scaling_bench.SCHEMA_VERSION)
    extra_needles = ["quick"]
    needles = scaling_bench._sb._collect_redaction_needles(extra_needles)
    redacted = scaling_bench._scrub_obj(
        scaling_bench._sb._redact_keys_recursive(raw), needles
    )
    redacted["schema_version"] = scaling_bench.SCHEMA_VERSION
    md_text = scaling_bench._scrub_string(scaling_bench.format_markdown(redacted), needles)
    json_text = json.dumps(redacted, indent=2) + "\n"

    ok, reasons = scaling_bench._validate_share_safety(
        redacted, json_text, md_text, extra_needles=extra_needles
    )
    assert ok is True, reasons
    assert redacted["mode"] == "quick"
    assert redacted["workdir_fstype"] == "ext4"
    assert redacted["workdir_kind"] == "temporary"
    assert redacted["schema_version"] == scaling_bench.SCHEMA_VERSION


def test_scaling_bench_bare_relative_workdir_excluded_from_raw_needles(
    scaling_bench, monkeypatch, tmp_path, capsys
):
    """BUG-E6: bare relative workdir='quick' adds only its resolved path, not raw 'quick'."""
    monkeypatch.chdir(tmp_path)
    needles_bare = scaling_bench._workdir_extra_needles("quick")
    assert "quick" not in needles_bare
    assert needles_bare == [str((tmp_path / "quick").resolve())]

    needles_slash = scaling_bench._workdir_extra_needles("sub/quick")
    assert "sub/quick" in needles_slash
    assert str((tmp_path / "sub/quick").resolve()) in needles_slash

    monkeypatch.setattr(
        scaling_bench,
        "run_benchmark",
        lambda quick=False, workdir=None: _sample_scaling_result(scaling_bench.SCHEMA_VERSION),
    )
    monkeypatch.setattr(getpass, "getuser", lambda: "cleanuser")
    monkeypatch.setattr(platform, "node", lambda: "bench-box-01")
    monkeypatch.setenv("USER", "cleanuser")
    monkeypatch.delenv("LOGNAME", raising=False)
    monkeypatch.delenv("USERNAME", raising=False)

    rc = scaling_bench.main(["--quick", "--workdir", "quick"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "# pubrun scaling benchmark (quick, local, single machine)" in out


def test_scaling_bench_validate_share_safety_still_rejects_real_leak(
    scaling_bench, monkeypatch
):
    """BUG-E6: unredacted username or hostname in a non-skipped key remains fail-closed."""
    monkeypatch.setattr(getpass, "getuser", lambda: "alice_secret")
    monkeypatch.setattr(platform, "node", lambda: "secret-hpc-node")
    monkeypatch.setenv("USER", "alice_secret")
    monkeypatch.delenv("LOGNAME", raising=False)
    monkeypatch.delenv("USERNAME", raising=False)

    leaked_user = _sample_scaling_result(scaling_bench.SCHEMA_VERSION)
    leaked_user["notes"] = "ran by alice_secret"
    ok_user, reasons_user = scaling_bench._validate_share_safety(
        leaked_user, json.dumps(leaked_user), "# clean markdown"
    )
    assert ok_user is False
    assert any("identifying substring remains in JSON payload" in r for r in reasons_user)

    leaked_host = _sample_scaling_result(scaling_bench.SCHEMA_VERSION)
    leaked_host["environment"]["cpu"]["model"] = "CPU on secret-hpc-node"
    ok_host, reasons_host = scaling_bench._validate_share_safety(
        leaked_host, json.dumps(leaked_host), "# clean markdown"
    )
    assert ok_host is False
    assert any("identifying substring remains in JSON payload" in r for r in reasons_host)
