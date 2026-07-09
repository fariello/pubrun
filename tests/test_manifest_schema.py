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


@pytest.mark.xfail(
    reason="Known pre-existing manifest-schema drift (7+ sections added without schema "
    "updates: filesystem, capture flags, host.os_release, python fields, resources "
    "fields, packages.source). Tracked for full reconciliation in a pending IPD; when "
    "that lands this flips to XPASS and becomes a hard gate.",
    strict=False,
)
def test_full_manifest_conforms_to_schema(tmp_path):
    """A complete real manifest should validate end-to-end against the shipped schema.

    Currently XFAILs due to documented pre-existing drift. This is the anti-regression
    tripwire for the schema-reconciliation IPD.
    """
    manifest = _make_manifest(tmp_path)
    jsonschema.validate(manifest, _schema())
