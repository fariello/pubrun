"""Regression tests guarding the shipped manifest JSON schema against drift.

Context: `schemas/manifest.schema.json` is a published contract / documentation of the
manifest shape, but nothing validated real manifests against it, so it drifted silently
as manifest sections were added over time. A scoped documentation assessment (2026-07-09)
found 7 pre-existing conformance errors on a default-run manifest.

These tests:
  1. Guard the sections fixed in that session (notably `config`, incl. the new
     `config.notices` field) so they conform NOW and cannot regress.
  2. Track the KNOWN pre-existing whole-manifest drift with an xfail, so the day the
     full reconciliation IPD lands (`.agents/plans/pending/` schema-reconciliation),
     this flips to XPASS and we tighten it into a hard gate.

`jsonschema` is a dev/test-only dependency (never a runtime dep — pubrun stays
zero-runtime-dependency); the tests skip cleanly if it is unavailable.
"""
import json
from pathlib import Path

import pytest

jsonschema = pytest.importorskip("jsonschema")

_SCHEMA_PATH = Path(__file__).resolve().parents[1] / "schemas" / "manifest.schema.json"


def _schema():
    return json.loads(_SCHEMA_PATH.read_text(encoding="utf-8"))


def _make_manifest(tmp_path, **start_kwargs):
    """Produce a real manifest via a start/stop cycle in an isolated cwd."""
    import os
    cwd = os.getcwd()
    os.chdir(tmp_path)
    try:
        import pubrun.noauto as pubrun
        t = pubrun.start(**start_kwargs)
        pubrun.stop()
        return json.loads((t.run_dir / "manifest.json").read_text(encoding="utf-8"))
    finally:
        os.chdir(cwd)


def _config_subschema(schema):
    """Extract a standalone schema for the `config` section from $defs."""
    defs = schema.get("$defs", schema.get("definitions", {}))
    assert "config_section" in defs, "config_section missing from schema $defs"
    sub = dict(defs["config_section"])
    sub["$defs"] = defs  # keep $ref targets (capture_state) resolvable
    return sub


def test_config_section_conforms_including_notices(tmp_path):
    """The `config` manifest section (incl. the new `notices` field) must validate.

    This is the field added in the profile-deprecation work; it previously violated the
    schema's `additionalProperties: false`. Guards that fix.
    """
    manifest = _make_manifest(tmp_path, profile="minimal")  # non-default -> emits a notice
    assert manifest["config"]["notices"], "expected a deprecation notice for profile=minimal"

    jsonschema.validate(manifest["config"], _config_subschema(_schema()))


def test_config_section_conforms_without_notices(tmp_path):
    manifest = _make_manifest(tmp_path)  # default profile -> empty notices
    assert manifest["config"]["notices"] == []
    jsonschema.validate(manifest["config"], _config_subschema(_schema()))


def test_schema_is_valid_draft(tmp_path):
    """The schema document itself must be a well-formed JSON Schema."""
    schema = _schema()
    cls = jsonschema.validators.validator_for(schema)
    cls.check_schema(schema)  # raises if the schema is malformed


def test_full_manifest_conforms_to_schema(tmp_path):
    """A complete real manifest must validate end-to-end against the shipped schema.

    Hard gate (was an xfail tripwire until the 2026-07-09 schema reconciliation): any
    future manifest field added without a corresponding schema update fails here, so the
    published contract cannot silently drift again.
    """
    manifest = _make_manifest(tmp_path)
    jsonschema.validate(manifest, _schema())


@pytest.mark.parametrize(
    "kwargs",
    [
        pytest.param({}, id="default"),
        pytest.param({"profile": "minimal"}, id="profile-notice"),
        pytest.param({"console": {"capture_mode": "standard"}}, id="console-on"),
        pytest.param({"capture": {"resources": {"scope": "tree"}}}, id="tree-scope"),
        # imported-transitive is a real packages.mode the code writes to the manifest; the
        # schema enum omitted it (a run using it would fail this gate). Covers that mode.
        pytest.param({"capture": {"packages": {"mode": "imported-transitive"}}}, id="packages-transitive"),
    ],
)
def test_manifest_variants_conform_to_schema(tmp_path, kwargs):
    """Validate several manifest shapes, not just the happy path: the profile-notice
    variant, console capture on, process-tree resource scope (which adds tree_* fields),
    and packages.mode='imported-transitive'. Guards drift a single default manifest would miss."""
    manifest = _make_manifest(tmp_path, **kwargs)
    jsonschema.validate(manifest, _schema())


def test_packages_mode_written_to_manifest_is_in_schema_enum(tmp_path):
    """Every packages.mode value the code writes to the manifest must be in the schema enum.
    Directly asserts the imported-transitive value lands as-configured and validates."""
    manifest = _make_manifest(tmp_path, capture={"packages": {"mode": "imported-transitive"}})
    assert manifest["packages"]["mode"] == "imported-transitive"
    schema = _schema()
    enum = schema["$defs"]["packages_section"]["properties"]["mode"]["enum"]
    assert manifest["packages"]["mode"] in enum


def test_committed_sample_fixture_conforms_to_schema():
    """The committed report-rendering fixture must itself be a schema-valid manifest,
    so it cannot silently drift from the real manifest shape (it did: it had the old
    git `is_dirty` and an `invocation.working_directory.basename` the code no longer
    emits, plus console streams missing `captured`)."""
    fixture = _SCHEMA_PATH.parent.parent / "tests" / "fixtures" / "sample_manifest.json"
    manifest = json.loads(fixture.read_text(encoding="utf-8"))
    jsonschema.validate(manifest, _schema())


@pytest.mark.parametrize("status", ["pending", "timeout"])
def test_transient_capture_states_are_valid(status):
    """The schema's capture-state enum must accept the transient statuses the code
    actually emits: `pending` (async hardware/host/filesystem sections at start(), which
    persist in a run that crashed before finalizing) and `timeout` (git/hardware
    external-tool timeout). Deterministic — no thread-timing dependence."""
    section = {"capture_state": {"status": status}}
    # capture_state is referenced identically across sections; validate the shared def.
    schema = _schema()
    defs = schema.get("$defs", schema.get("definitions", {}))
    sub = dict(defs["capture_state"])
    sub["$defs"] = defs
    jsonschema.validate(section["capture_state"], sub)


def test_startup_manifest_conforms_to_schema(tmp_path):
    """The STARTUP manifest (written at start(), before finalization) must validate.

    This is the on-disk shape a run that CRASHED before finalizing leaves behind — read
    by pubrun status/inspect/show. Whichever state its async hardware/host/filesystem
    sections are in when read (`pending` if the background hw thread has not finished, or
    `complete` if it has — a race we deliberately do NOT assert on), the manifest must
    conform. The `pending`-is-valid guarantee is pinned deterministically by
    test_transient_capture_states_are_valid above.
    """
    import os
    import time
    cwd = os.getcwd()
    os.chdir(tmp_path)
    manifest = None
    try:
        import pubrun.noauto as pubrun
        t = pubrun.start()
        try:
            # Read the manifest written synchronously at start(), BEFORE stop(). On Windows the
            # run's file can be transiently locked / mid-atomic-write while the run is live, so read
            # tolerantly with a few retries rather than failing on a momentary PermissionError.
            mpath = t.run_dir / "manifest.json"
            for _ in range(10):
                try:
                    manifest = json.loads(mpath.read_text(encoding="utf-8"))
                    break
                except (PermissionError, json.JSONDecodeError, FileNotFoundError):
                    time.sleep(0.05)
        finally:
            pubrun.stop()
    finally:
        os.chdir(cwd)

    if manifest is None:
        pytest.skip("startup manifest was not readable while the run was live (platform file lock)")

    jsonschema.validate(manifest, _schema())


@pytest.mark.parametrize("level", ["name", "stat", "realpath", "hash"])
def test_populated_data_files_manifest_conforms_across_levels(tmp_path, level):
    """Real manifests with populated data_files (inputs, outputs, mixed, hashing_summary)
    must validate against schemas/manifest.schema.json across every tracking level."""
    import os

    cwd = os.getcwd()
    os.chdir(tmp_path)
    try:
        import pubrun.noauto as pubrun

        inp_path = tmp_path / f"in_{level}.bin"
        inp_path.write_bytes(b"input-data-bytes")
        out_path = tmp_path / f"out_{level}.bin"
        mix_path = tmp_path / f"mix_{level}.bin"
        mix_path.write_bytes(b"mix0")

        t = pubrun.start(
            console={"capture_mode": "off"},
            capture={"file_io": {"level": level}},
        )
        try:
            with pubrun.open(inp_path, "rb") as fh:
                fh.read()
            with pubrun.open(out_path, "wb") as fh:
                fh.write(b"output-data-bytes")
            with pubrun.open(mix_path, "r+b") as fh:
                fh.read(2)
                fh.write(b"99")
        finally:
            pubrun.stop()

        manifest = json.loads((t.run_dir / "manifest.json").read_text(encoding="utf-8"))
    finally:
        os.chdir(cwd)

    assert len(manifest["data_files"]["inputs"]) == 1
    assert len(manifest["data_files"]["outputs"]) == 1
    assert len(manifest["data_files"]["mixed"]) == 1
    if level == "hash":
        assert "hashing_summary" in manifest["data_files"]
    jsonschema.validate(manifest, _schema())


def test_populated_data_files_over_budget_and_file_changed_conform(tmp_path):
    """Real manifests containing over_budget skips, file_changed records, and non-SHA-256
    digests must validate against schemas/manifest.schema.json."""
    import os

    cwd = os.getcwd()
    os.chdir(tmp_path)
    try:
        import pubrun.noauto as pubrun

        big = tmp_path / "big.bin"
        big.write_bytes(b"0123456789abcdef")
        changed = tmp_path / "changed.bin"
        changed.write_bytes(b"orig")
        small = tmp_path / "small.bin"
        small.write_bytes(b"ok")

        t = pubrun.start(
            console={"capture_mode": "off"},
            capture={
                "file_io": {
                    "level": "hash",
                    "max_hash_bytes": 8,
                    "hash_algorithm": "sha512",
                }
            },
        )
        try:
            with pubrun.open(big, "rb") as fh:
                fh.read()
            with pubrun.open(changed, "rb") as fh:
                fh.read(2)
                with open(changed, "ab") as writer:
                    writer.write(b"-mut")
            with pubrun.open(small, "rb") as fh:
                fh.read()
        finally:
            pubrun.stop()

        manifest = json.loads((t.run_dir / "manifest.json").read_text(encoding="utf-8"))
    finally:
        os.chdir(cwd)

    statuses = [rec["hash_status"] for rec in manifest["data_files"]["inputs"]]
    assert statuses == ["over_budget", "file_changed", "completed"]
    jsonschema.validate(manifest, _schema())


def test_legacy_data_files_manifest_without_mixed_or_hashing_summary_conforms():
    """Legacy manifests carrying only inputs and outputs (without mixed or hashing_summary)
    remain valid under schemas/manifest.schema.json."""
    fixture = _SCHEMA_PATH.parent.parent / "tests" / "fixtures" / "sample_manifest.json"
    manifest = json.loads(fixture.read_text(encoding="utf-8"))
    manifest["data_files"] = {
        "inputs": [
            {
                "path": "/tmp/legacy_in.csv",
                "size_bytes": 128,
                "mtime": 1715280000.0,
                "ctime": 1715280000.0,
                "sha256": None,
                "accessed_at_utc": 1715280001.0,
            }
        ],
        "outputs": [
            {
                "path": "/tmp/legacy_out.csv",
                "size_bytes": 256,
                "sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
                "modified_at_utc": 1715280002.0,
            }
        ],
    }
    jsonschema.validate(manifest, _schema())
