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


def _timing_subschema(schema):
    """Extract a standalone schema for the `timing` section from $defs."""
    defs = schema.get("$defs", schema.get("definitions", {}))
    assert "timing" in defs, "timing missing from schema $defs"
    sub = dict(defs["timing"])
    sub["$defs"] = defs  # keep $ref targets (utc_datetime, capture_state) resolvable
    return sub


def _subprocess_record_subschema(schema):
    """Extract a standalone schema for `$defs.subprocess_record`."""
    defs = schema.get("$defs", schema.get("definitions", {}))
    assert "subprocess_record" in defs, "subprocess_record missing from schema $defs"
    sub = dict(defs["subprocess_record"])
    sub["$defs"] = defs
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


def test_finalized_manifest_timing_fields_conform_to_schema(tmp_path):
    """A finalized run emits monotonic timing interval fields and validates end-to-end."""
    manifest = _make_manifest(tmp_path)
    jsonschema.validate(manifest, _schema())

    timing = manifest["timing"]
    assert timing["duration_clock"] == "monotonic"
    assert timing["elapsed_basis"] == "workload"
    assert timing["interval_scope"] == "tracked_interval"
    assert timing["capture_state"] == {"status": "complete"}
    assert isinstance(timing["workload_started_at_utc"], float)
    assert isinstance(timing["finalized_at_utc"], float)
    assert timing["elapsed_seconds"] == timing["workload_seconds"]
    for key in (
        "elapsed_seconds",
        "workload_seconds",
        "startup_overhead_seconds",
        "finalization_overhead_seconds",
        "session_seconds",
    ):
        assert isinstance(timing[key], float)
        assert timing[key] >= 0.0


def test_legacy_v1_timing_manifest_without_new_fields_conforms():
    """Legacy v1.0 manifests carrying only started_at_utc, ended_at_utc,
    elapsed_seconds, and capture_state remain valid under schemas/manifest.schema.json."""
    fixture = _SCHEMA_PATH.parent.parent / "tests" / "fixtures" / "sample_manifest.json"
    manifest = json.loads(fixture.read_text(encoding="utf-8"))
    manifest["timing"] = {
        "started_at_utc": 1715280000.0,
        "ended_at_utc": 1715280045.5,
        "elapsed_seconds": 45.5,
        "capture_state": {"status": "complete"},
    }
    jsonschema.validate(manifest, _schema())


def test_ghost_run_timing_subschema_conforms(tmp_path, monkeypatch):
    """Ghost-mode runs (unwritable run_dir or startup manifest write failure)
    emit a timing section that conforms to `$defs.timing`."""
    import pubrun.writer as writer_mod
    from pubrun.tracker import Run

    schema = _schema()
    timing_schema = _timing_subschema(schema)

    # Startup output write failure ghost run (post-bootstrap rollback)
    def failing_startup(self, *args, **kwargs):
        self.last_error = "PermissionError: read-only output"
        return False

    monkeypatch.setattr(writer_mod.ArtifactWriter, "write_startup_manifest", failing_startup)
    ghost_output = Run()
    assert ghost_output._outcome == "ghost"
    timing_output = ghost_output.to_manifest_dict()["timing"]
    assert timing_output["capture_state"] == {
        "status": "partial",
        "detail": "ghost mode: startup did not complete",
    }
    assert timing_output["elapsed_seconds"] is None
    assert timing_output["workload_seconds"] is None
    assert timing_output["duration_clock"] is None
    assert timing_output["elapsed_basis"] is None
    jsonschema.validate(timing_output, timing_schema)
    ghost_output.stop()

    # Unwritable run_dir ghost run (mkdir failure)
    monkeypatch.undo()
    monkeypatch.setattr(
        Path,
        "mkdir",
        lambda self, *a, **kw: (_ for _ in ()).throw(PermissionError("read-only")),
    )
    ghost_fs = Run()
    assert ghost_fs._outcome == "ghost"
    timing_fs = ghost_fs.to_manifest_dict()["timing"]
    jsonschema.validate(timing_fs, timing_schema)
    ghost_fs.stop()


@pytest.mark.parametrize(
    "fault_section",
    ["invocation", "git", "packages", "hardware", "console", "resources", "signals"],
)
def test_partial_manifest_under_engine_fault_conforms_to_schema(
    tmp_path, monkeypatch, fault_section
):
    """Real partial manifests produced when any capture engine fails must validate
    end-to-end against schemas/manifest.schema.json with structured capture-error records."""
    import pubrun.tracker as tracker_mod
    from pubrun.tracker import Run

    monkeypatch.setattr("pathlib.Path.cwd", lambda: tmp_path)

    def _boom(*args, **kwargs):
        raise RuntimeError(f"fault in {fault_section} api_key=secret_token_value")

    overrides = {}
    if fault_section == "invocation":
        monkeypatch.setattr(tracker_mod, "get_invocation", _boom)
    elif fault_section == "git":
        monkeypatch.setattr(tracker_mod, "get_git", _boom)
    elif fault_section == "packages":
        monkeypatch.setattr(tracker_mod, "get_packages", _boom)
    elif fault_section == "hardware":
        monkeypatch.setattr(tracker_mod, "get_hardware", _boom)
    elif fault_section == "console":
        overrides = {"console": {"capture_mode": "standard"}}
        monkeypatch.setattr(tracker_mod.ConsoleInterceptor, "start", _boom)
    elif fault_section == "resources":
        overrides = {"capture": {"resources": {"depth": "basic"}}}
        monkeypatch.setattr(tracker_mod.ResourceWatcher, "start", _boom)
    elif fault_section == "signals":
        overrides = {"capture": {"signals": {"enabled": True}}}
        monkeypatch.setattr(tracker_mod.SignalExitCapture, "install", _boom)

    run = Run(overrides=overrides)
    if run._hardware_future_done is not None:
        run._hardware_future_done.wait(timeout=2.0)
    run.stop()

    manifest = json.loads((run.run_dir / "manifest.json").read_text(encoding="utf-8"))
    jsonschema.validate(manifest, _schema())

    assert manifest["status"]["outcome"] == "completed"
    assert manifest[fault_section]["capture_state"]["status"] == "failed"
    assert "secret_token_value" not in manifest[fault_section]["capture_state"].get("detail", "")
    assert manifest["capture"]["capture_state"]["status"] == "partial"

    matching = [
        rec
        for rec in manifest["errors"]["records"]
        if rec.get("kind") == "capture-error" and rec.get("section") == fault_section
    ]
    assert matching, f"Expected capture-error record for {fault_section}"
    assert matching[0]["stage"] == "bootstrap"
    assert matching[0]["traceback"] is None
    assert "secret_token_value" not in (matching[0].get("message") or "")


def test_error_record_schema_accepts_legacy_and_extended_shapes():
    """$defs.error_record keeps required=['kind'] and accepts optional section/stage."""
    schema = _schema()
    defs = schema["$defs"]
    err_sub = dict(defs["error_record"])
    err_sub["$defs"] = defs

    # Legacy minimal record (only required field 'kind')
    jsonschema.validate({"kind": "exception"}, err_sub)
    # Extended capture-error record with section and stage
    jsonschema.validate(
        {
            "kind": "capture-error",
            "type": "RuntimeError",
            "message": "RuntimeError: git unavailable",
            "traceback": None,
            "section": "git",
            "stage": "bootstrap",
        },
        err_sub,
    )
    # Nullable section/stage
    jsonschema.validate(
        {
            "kind": "capture-error",
            "section": None,
            "stage": None,
        },
        err_sub,
    )


def test_timing_and_subprocess_schema_constraints():
    """Additive timing and subprocess_record fields validate valid values and reject
    negative durations or unknown enum strings."""
    schema = _schema()
    timing_schema = _timing_subschema(schema)
    subproc_schema = _subprocess_record_subschema(schema)

    # Valid enriched subprocess_record (used by child 8co0wy)
    jsonschema.validate(
        {
            "argv": ["python3", "-c", "print(1)"],
            "started_at_utc": 1715280000.0,
            "ended_at_utc": 1715280001.25,
            "exit_code": 0,
            "elapsed_seconds": 1.25,
            "duration_clock": "monotonic",
            "pid": 12345,
            "error": None,
            "capture_state": {"status": "complete"},
        },
        subproc_schema,
    )
    # Valid legacy subprocess_record without new fields
    jsonschema.validate(
        {
            "argv": ["echo", "ok"],
            "capture_state": {"status": "complete"},
        },
        subproc_schema,
    )

    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(
            {
                "started_at_utc": 1715280000.0,
                "workload_seconds": -0.1,
                "capture_state": {"status": "complete"},
            },
            timing_schema,
        )

    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(
            {
                "started_at_utc": 1715280000.0,
                "duration_clock": "bogus_clock",
                "capture_state": {"status": "complete"},
            },
            timing_schema,
        )

    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(
            {
                "argv": ["echo", "bad"],
                "elapsed_seconds": -1.0,
                "capture_state": {"status": "complete"},
            },
            subproc_schema,
        )


def _packages_subschema(schema):
    """Extract a standalone schema for `$defs.packages_section`."""
    defs = schema.get("$defs", schema.get("definitions", {}))
    assert "packages_section" in defs, "packages_section missing from schema $defs"
    sub = dict(defs["packages_section"])
    sub["$defs"] = defs
    return sub


def test_packages_extended_fields_and_legacy_v1_conform():
    """$defs.packages_section accepts startup, finalized, imported-transitive, partial,
    and legacy v1.0 package shapes while keeping existing required fields unchanged."""
    schema = _schema()
    pkg_schema = _packages_subschema(schema)

    # Legacy v1.0 manifest section without any of the new additive fields.
    jsonschema.validate(
        {
            "mode": "imported-only",
            "records": [
                {"name": "numpy", "version": "1.26.4", "location": "/site", "editable": False, "source": "imported"},
                {"name": "bare-pkg", "version": None},
            ],
            "capture_state": {"status": "complete"},
        },
        pkg_schema,
    )

    # Startup snapshot with observed_at="startup" and snapshot_stage="startup".
    jsonschema.validate(
        {
            "mode": "imported-only",
            "snapshot_stage": "startup",
            "records": [
                {
                    "name": "pubrun",
                    "version": "1.0.0",
                    "location": "/src",
                    "editable": True,
                    "source": "imported",
                    "import_names": ["pubrun"],
                    "observed_at": "startup",
                }
            ],
            "unresolved": [],
            "local_modules": ["helper"],
            "coverage_notes": [],
            "capture_state": {"status": "complete"},
        },
        pkg_schema,
    )

    # Finalized imported-transitive snapshot with all additive fields and partial state.
    jsonschema.validate(
        {
            "mode": "imported-transitive",
            "snapshot_stage": "final",
            "records": [
                {
                    "name": "scikit-learn",
                    "version": "1.5.0",
                    "location": "/site",
                    "editable": False,
                    "source": "imported",
                    "import_names": ["sklearn"],
                    "observed_at": "final",
                },
                {
                    "name": "numpy",
                    "version": "1.26.4",
                    "location": "/site",
                    "editable": False,
                    "source": "imported",
                    "import_names": ["numpy"],
                    "observed_at": "startup_and_final",
                },
                {
                    "name": "scipy",
                    "version": "1.13.0",
                    "location": "/site",
                    "editable": False,
                    "source": "transitive",
                    "required_by": ["scikit-learn"],
                    "import_names": None,
                    "observed_at": None,
                },
            ],
            "unresolved": [
                {
                    "module": "ambig_mod",
                    "reason": "ambiguous",
                    "candidates": ["pkg-a", "pkg-b"],
                    "observed_at": "startup_and_final",
                    "detail": "matches multiple distributions",
                },
                {
                    "module": "missing-dep",
                    "reason": "missing_transitive_dependency",
                    "candidates": [],
                    "observed_at": "final",
                    "detail": "required by scikit-learn",
                },
            ],
            "local_modules": ["train_utils"],
            "coverage_notes": [
                "Package capture ran at startup and finalization without a global import hook."
            ],
            "capture_state": {
                "status": "partial",
                "detail": "some modules unresolved",
                "warnings": ["missing-dep (missing_transitive_dependency): required by scikit-learn"],
            },
        },
        pkg_schema,
    )

    # Suppressed mode omits "mode" cleanly.
    jsonschema.validate({"capture_state": {"status": "suppressed"}}, pkg_schema)


@pytest.mark.parametrize(
    "bad_section",
    [
        pytest.param(
            {
                "mode": "imported-only",
                "snapshot_stage": "midrun",
                "records": [],
                "capture_state": {"status": "complete"},
            },
            id="invalid-snapshot-stage",
        ),
        pytest.param(
            {
                "mode": "imported-only",
                "snapshot_stage": "final",
                "records": [
                    {
                        "name": "numpy",
                        "version": "1.0.0",
                        "observed_at": "middle",
                    }
                ],
                "capture_state": {"status": "complete"},
            },
            id="invalid-observed-at",
        ),
        pytest.param(
            {
                "mode": "imported-only",
                "snapshot_stage": "final",
                "records": [],
                "unresolved": [
                    {
                        "module": "foo",
                        "reason": "invented_reason",
                    }
                ],
                "capture_state": {"status": "partial"},
            },
            id="invalid-unresolved-reason",
        ),
        pytest.param(
            {
                "mode": "imported-only",
                "snapshot_stage": "final",
                "records": [],
                "unexpected_section_key": True,
                "capture_state": {"status": "complete"},
            },
            id="unknown-section-key",
        ),
        pytest.param(
            {
                "mode": "imported-only",
                "snapshot_stage": "final",
                "records": [
                    {
                        "name": "numpy",
                        "version": "1.0.0",
                        "unexpected_record_key": 123,
                    }
                ],
                "capture_state": {"status": "complete"},
            },
            id="unknown-record-key",
        ),
        pytest.param(
            {
                "mode": "imported-only",
                "snapshot_stage": "final",
                "records": [],
                "unresolved": [
                    {
                        "module": "foo",
                        "reason": "ambiguous",
                        "unexpected_unresolved_key": "nope",
                    }
                ],
                "capture_state": {"status": "partial"},
            },
            id="unknown-unresolved-key",
        ),
    ],
)
def test_packages_schema_rejects_invalid_enums_and_unknown_keys(bad_section):
    """Negative conformance checks: invalid enums and unknown extra keys must fail."""
    schema = _schema()
    pkg_schema = _packages_subschema(schema)
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(bad_section, pkg_schema)
