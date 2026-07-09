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
    ],
)
def test_manifest_variants_conform_to_schema(tmp_path, kwargs):
    """Validate several manifest shapes, not just the happy path: the profile-notice
    variant, console capture on, and process-tree resource scope (which adds tree_*
    fields). Guards drift a single default manifest would miss."""
    manifest = _make_manifest(tmp_path, **kwargs)
    jsonschema.validate(manifest, _schema())


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
    cwd = os.getcwd()
    os.chdir(tmp_path)
    try:
        import pubrun.noauto as pubrun
        t = pubrun.start()
        try:
            # Read the manifest written synchronously at start(), BEFORE stop().
            manifest = json.loads((t.run_dir / "manifest.json").read_text(encoding="utf-8"))
        finally:
            pubrun.stop()
    finally:
        os.chdir(cwd)

    jsonschema.validate(manifest, _schema())

    jsonschema.validate(manifest, _schema())
