"""Behavioral tests for explicit external file registration API and lifecycle semantics.

Covers ``pubrun.register_file()``, ``pubrun.register_input()``, ``pubrun.register_output()``,
caller-supplied asserted vs. verified digests, pre-creation/deferred and post-creation output
lifecycles, deduplication without double-hashing, detail-level overrides, shared budgets with
``pubrun.open()``, thread safety, Ghost Mode, remote URIs, edge cases, and schema conformance.
"""
import builtins
import hashlib
import json
import logging
import os
import stat
import sys
import threading
import types
from pathlib import Path

import pytest

import pubrun
import pubrun.tracker

_SCHEMA_PATH = Path(__file__).resolve().parents[1] / "schemas" / "manifest.schema.json"


def _run_manifest(tmp_path, file_io_cfg, fn, *, extra_start_kwargs=None):
    """Run ``fn(tmp_path, tracker)`` inside an isolated run and return its parsed manifest."""
    pubrun.tracker._active_run = None
    try:
        start_kwargs = {
            "console": {"capture_mode": "off"},
            "capture": {"file_io": file_io_cfg},
        }
        if extra_start_kwargs:
            start_kwargs.update(extra_start_kwargs)
        tracker = pubrun.start(**start_kwargs)
        try:
            fn(tmp_path, tracker)
        finally:
            tracker.stop()
        return json.loads((Path(tracker.run_dir) / "manifest.json").read_text(encoding="utf-8"))
    finally:
        pubrun.tracker._active_run = None


class TestExternalLibraryRegistration:

    def test_library_style_io_registration_with_labels_and_metadata(self, tmp_path):
        """External library I/O using builtins.open registers inputs, outputs, and mixed roles."""
        orig_open = builtins.open
        inp_path = tmp_path / "train.csv"
        out_path = tmp_path / "predictions.csv"
        mix_path = tmp_path / "cache.bin"
        inp_path.write_text("x,y\n1,2\n3,4\n", encoding="utf-8")
        mix_path.write_bytes(b"seed-bytes")

        meta_in = {"format": "csv", "rows": 2}
        returned = {}

        def _work(_base, _run):
            assert builtins.open is orig_open

            # Simulate an external library reading with standard builtins.open.
            with builtins.open(inp_path, "r", encoding="utf-8") as fh:
                content = fh.read()
            assert "1,2" in content
            returned["in"] = pubrun.register_input(
                inp_path, label="training_data", metadata=meta_in
            )
            # Mutating caller dict after registration must not mutate stored metadata.
            meta_in["rows"] = 999

            # Simulate an external library writing with standard builtins.open.
            with builtins.open(out_path, "w", encoding="utf-8") as fh:
                fh.write("pred\n0.9\n")
            returned["out"] = pubrun.register_output(
                str(out_path), label="model_predictions"
            )

            # Mixed read/write path via register_file.
            with builtins.open(mix_path, "ab") as fh:
                fh.write(b"-extra")
            returned["mix"] = pubrun.register_file(
                mix_path, role="input_output", label="feature_cache"
            )

            # pubrun.artifact() stays a run-internal writer and never touches data_files.
            pubrun.artifact("run_note.txt", "internal-only")

        manifest = _run_manifest(tmp_path, {"level": "hash"}, _work)
        assert builtins.open is orig_open

        inputs = manifest["data_files"]["inputs"]
        outputs = manifest["data_files"]["outputs"]
        mixed = manifest["data_files"]["mixed"]
        assert len(inputs) == 1
        assert len(outputs) == 1
        assert len(mixed) == 1

        rec_in = inputs[0]
        assert rec_in["label"] == "training_data"
        assert rec_in["role"] == "input"
        assert rec_in["registration_source"] == "register_input"
        assert rec_in["hash_status"] == "completed"
        assert rec_in["evidence_source"] == "observed"
        assert rec_in["evidence_strength"] == "verified_content"
        assert rec_in["observation_time"] == "at_registration"
        assert rec_in["sha256"] == hashlib.sha256(inp_path.read_bytes()).hexdigest()
        assert rec_in["metadata"] == {"format": "csv", "rows": 2}
        assert rec_in["accessed_at_utc"] is not None
        assert returned["in"]["sha256"] == rec_in["sha256"]

        rec_out = outputs[0]
        assert rec_out["label"] == "model_predictions"
        assert rec_out["role"] == "output"
        assert rec_out["registration_source"] == "register_output"
        assert rec_out["hash_status"] == "completed"
        assert rec_out["sha256"] == hashlib.sha256(out_path.read_bytes()).hexdigest()
        assert rec_out["modified_at_utc"] is not None

        rec_mix = mixed[0]
        assert rec_mix["label"] == "feature_cache"
        assert rec_mix["role"] == "input_output"
        assert rec_mix["registration_source"] == "register_file"
        assert rec_mix["hash_status"] == "completed"
        assert rec_mix["sha256"] == hashlib.sha256(b"seed-bytes-extra").hexdigest()
        assert rec_mix["accessed_at_utc"] is not None
        assert rec_mix["modified_at_utc"] is not None


class TestCallerDigests:

    def test_asserted_digest_default_does_not_read_file_bytes(self, tmp_path, monkeypatch):
        """Supplying digest with default verify_digest=False records asserted evidence without I/O."""
        p = tmp_path / "catalog_dataset.parquet"
        p.write_bytes(b"large-dataset-bytes")
        supplied = "a" * 64

        def _forbid_open(*args, **kwargs):
            raise AssertionError("builtins.open must not be called when verify_digest=False")

        def _work(_base, _run):
            with monkeypatch.context() as mp:
                mp.setattr(builtins, "open", _forbid_open)
                rec = pubrun.register_input(
                    p,
                    label="catalog_table",
                    digest=supplied,
                    digest_algorithm="SHA256",
                )
            assert rec["hash_status"] == "asserted"
            assert rec["evidence_source"] == "asserted"
            assert rec["evidence_strength"] == "asserted_content"
            assert rec["observation_time"] == "caller_supplied"
            assert rec["sha256"] is None
            assert rec["hash_algorithm"] == "sha256"
            assert rec["caller_digest"] == {
                "algorithm": "sha256",
                "value": supplied,
                "verified": None,
            }
            assert rec["digest"] == {"algorithm": "sha256", "value": supplied}

        manifest = _run_manifest(tmp_path, {"level": "hash"}, _work)
        inp = manifest["data_files"]["inputs"][0]
        assert inp["hash_status"] == "asserted"
        assert inp["sha256"] is None
        assert inp["evidence_source"] == "asserted"
        assert inp["evidence_strength"] == "asserted_content"
        assert "hashing_summary" not in manifest["data_files"]

    def test_verify_digest_match_sha256_and_sha512(self, tmp_path):
        """verify_digest=True verifies on-disk bytes for sha256 and non-sha256 algorithms."""
        p256 = tmp_path / "match256.bin"
        p512 = tmp_path / "match512.bin"
        p256.write_bytes(b"verified-payload-256")
        p512.write_bytes(b"verified-payload-512")

        expected_256 = hashlib.sha256(b"verified-payload-256").hexdigest()
        expected_512 = hashlib.sha512(b"verified-payload-512").hexdigest()

        def _work(_base, _run):
            pubrun.register_input(
                p256,
                label="sha256_ok",
                digest=expected_256.upper(),
                digest_algorithm="sha256",
                verify_digest=True,
            )
            pubrun.register_input(
                p512,
                label="sha512_ok",
                digest=expected_512,
                digest_algorithm="sha512",
                verify_digest=True,
            )

        # Even when run level is "stat", verify_digest=True must verify the file.
        manifest = _run_manifest(tmp_path, {"level": "stat"}, _work)
        r256, r512 = manifest["data_files"]["inputs"]

        assert r256["hash_status"] == "completed"
        assert r256["caller_digest"] == {
            "algorithm": "sha256",
            "value": expected_256.upper(),
            "verified": True,
        }
        assert r256["digest"] == {"algorithm": "sha256", "value": expected_256}
        assert r256["sha256"] == expected_256
        assert r256["evidence_source"] == "observed"
        assert r256["evidence_strength"] == "verified_content"
        assert r256["observation_time"] == "at_registration"

        assert r512["hash_status"] == "completed"
        assert r512["caller_digest"]["verified"] is True
        assert r512["digest"] == {"algorithm": "sha512", "value": expected_512}
        assert r512["sha256"] is None
        assert r512["evidence_source"] == "observed"
        assert r512["evidence_strength"] == "verified_content"

    def test_verify_digest_mismatch_sets_failed_and_null_digest(self, tmp_path):
        """verify_digest=True mismatch records failed status, verified=False, and null digests."""
        p = tmp_path / "tampered.bin"
        p.write_bytes(b"actual-bytes")
        wrong_digest = "0" * 64

        def _work(_base, _run):
            pubrun.register_input(
                p,
                digest=wrong_digest,
                digest_algorithm="sha256",
                verify_digest=True,
            )

        manifest = _run_manifest(tmp_path, {"level": "hash"}, _work)
        rec = manifest["data_files"]["inputs"][0]
        assert rec["hash_status"] == "failed"
        assert rec["hash_status_detail"] == "caller_digest_mismatch"
        assert rec["caller_digest"] == {
            "algorithm": "sha256",
            "value": wrong_digest,
            "verified": False,
        }
        assert rec["digest"] is None
        assert rec["sha256"] is None
        assert rec["evidence_source"] == "observed"
        assert rec["evidence_strength"] == "changed_unverified"

    def test_verify_digest_unsupported_algorithm_does_not_fallback_to_sha256(self, tmp_path):
        """Unsupported digest_algorithm under verify_digest=True records unavailable honestly."""
        p = tmp_path / "custom_alg.bin"
        p.write_bytes(b"some-bytes")

        def _work(_base, _run):
            pubrun.register_input(
                p,
                digest="deadbeef",
                digest_algorithm="blake3",
                verify_digest=True,
            )

        manifest = _run_manifest(tmp_path, {"level": "hash"}, _work)
        rec = manifest["data_files"]["inputs"][0]
        assert rec["hash_status"] == "unavailable"
        assert "unsupported digest algorithm 'blake3'" in rec["hash_status_detail"]
        assert rec["hash_algorithm"] == "blake3"
        assert rec["caller_digest"] == {
            "algorithm": "blake3",
            "value": "deadbeef",
            "verified": None,
        }
        assert rec["digest"] == {"algorithm": "blake3", "value": "deadbeef"}
        assert rec["sha256"] is None
        assert rec["evidence_source"] == "asserted"
        assert rec["evidence_strength"] == "asserted_content"

    def test_verify_digest_over_budget_preserves_over_budget_status(self, tmp_path):
        """verify_digest=True respects per-file budget and records over_budget cleanly."""
        p = tmp_path / "too_big_for_verify.bin"
        p.write_bytes(b"0123456789abcdef")

        def _work(_base, _run):
            pubrun.register_input(
                p,
                digest=hashlib.sha256(b"0123456789abcdef").hexdigest(),
                verify_digest=True,
            )

        manifest = _run_manifest(tmp_path, {"level": "hash", "max_hash_bytes": 4}, _work)
        rec = manifest["data_files"]["inputs"][0]
        assert rec["hash_status"] == "over_budget"
        assert rec["caller_digest"]["verified"] is None
        assert rec["digest"] is None
        assert rec["sha256"] is None


class TestPendingOutputLifecycles:

    def test_pre_creation_output_finalized_at_stop(self, tmp_path):
        """Output registered before creation starts pending and finalizes on pubrun.stop()."""
        out_path = tmp_path / "model.bin"
        pending_snapshot = {}

        def _work(_base, _run):
            rec = pubrun.register_output(out_path, label="trained_model")
            pending_snapshot.update(rec)
            # No internal keys may leak onto the record dict.
            assert set(rec.keys()).issubset(
                set(
                    json.loads(_SCHEMA_PATH.read_text(encoding="utf-8"))["$defs"][
                        "file_provenance_record"
                    ]["properties"].keys()
                )
            )
            # External library writes file later in the run.
            out_path.write_bytes(b"trained-weights-v1")

        manifest = _run_manifest(tmp_path, {"level": "hash"}, _work)
        assert pending_snapshot["hash_status"] == "pending"
        assert pending_snapshot["registered_before_creation"] is True
        assert pending_snapshot["sha256"] is None

        outputs = manifest["data_files"]["outputs"]
        assert len(outputs) == 1
        rec = outputs[0]
        assert rec["label"] == "trained_model"
        assert rec["registered_before_creation"] is True
        assert rec["hash_status"] == "completed"
        assert rec["observation_time"] == "at_finalization"
        assert rec["evidence_source"] == "observed"
        assert rec["evidence_strength"] == "verified_content"
        assert rec["sha256"] == hashlib.sha256(b"trained-weights-v1").hexdigest()
        assert rec["size_bytes"] == len(b"trained-weights-v1")

    def test_defer_true_overwrites_pre_existing_output(self, tmp_path):
        """defer=True on an existing output waits and hashes the overwritten file at stop."""
        out_path = tmp_path / "reused_output.bin"
        out_path.write_bytes(b"stale-previous-run-data")

        def _work(_base, _run):
            rec = pubrun.register_output(out_path, label="overwritten", defer=True)
            assert rec["hash_status"] == "pending"
            assert rec["registered_before_creation"] is True
            # Library overwrites the file after registration.
            out_path.write_bytes(b"fresh-new-run-data")

        manifest = _run_manifest(tmp_path, {"level": "hash"}, _work)
        outputs = manifest["data_files"]["outputs"]
        assert len(outputs) == 1
        rec = outputs[0]
        assert rec["hash_status"] == "completed"
        assert rec["observation_time"] == "at_finalization"
        assert rec["sha256"] == hashlib.sha256(b"fresh-new-run-data").hexdigest()
        assert manifest["data_files"]["hashing_summary"]["files_hashed"] == 1

    def test_pre_creation_upgraded_on_post_creation_call_without_double_hashing(self, tmp_path):
        """Re-registering an output after creation upgrades the pending entry without double-hashing."""
        out_path = tmp_path / "upgraded.bin"

        def _work(_base, run):
            r1 = pubrun.register_output(out_path, label="summary", metadata={"stage": "init"})
            assert r1["hash_status"] == "pending"
            # Repeated pre-creation call deduplicates into the same pending entry.
            r1_dup = pubrun.register_output(out_path, label="summary", metadata={"step": 2})
            assert r1_dup is r1
            assert r1["registration_count"] == 2
            assert len(run._pending_file_registrations) == 1

            # Create file, then register post-creation.
            out_path.write_bytes(b"final-summary-content")
            r2 = pubrun.register_output(out_path, label="summary")
            assert r2 is r1
            assert r2["hash_status"] == "completed"
            assert r2["observation_time"] == "at_registration"
            assert r2["registered_before_creation"] is True
            assert r2["registration_count"] == 3
            assert r2["metadata"] == {"stage": "init", "step": 2}
            # Pending queue must be cleared so stop() does not re-hash.
            assert run._pending_file_registrations == []

        manifest = _run_manifest(tmp_path, {"level": "hash"}, _work)
        outputs = manifest["data_files"]["outputs"]
        assert len(outputs) == 1
        assert outputs[0]["sha256"] == hashlib.sha256(b"final-summary-content").hexdigest()
        summary = manifest["data_files"]["hashing_summary"]
        assert summary["files_hashed"] == 1
        assert summary["total_bytes_hashed"] == len(b"final-summary-content")

    def test_pending_output_still_missing_at_stop(self, tmp_path):
        """Pending outputs never created before stop become unavailable (or asserted with digest)."""
        missing_plain = tmp_path / "never_created.csv"
        missing_asserted = tmp_path / "never_created_asserted.csv"
        missing_verify = tmp_path / "never_created_verify.csv"

        def _work(_base, _run):
            pubrun.register_output(missing_plain, label="plain_missing")
            pubrun.register_output(
                missing_asserted,
                label="asserted_missing",
                digest="b" * 64,
                verify_digest=False,
            )
            pubrun.register_output(
                missing_verify,
                label="verify_missing",
                digest="c" * 64,
                verify_digest=True,
            )

        manifest = _run_manifest(tmp_path, {"level": "hash"}, _work)
        outputs = {r["label"]: r for r in manifest["data_files"]["outputs"]}

        plain = outputs["plain_missing"]
        assert plain["entry_type"] == "missing"
        assert plain["hash_status"] == "unavailable"
        assert plain["evidence_source"] == "none"
        assert plain["evidence_strength"] == "unavailable"
        assert plain["sha256"] is None
        assert "finalization" in plain["hash_status_detail"]

        asserted = outputs["asserted_missing"]
        assert asserted["entry_type"] == "missing"
        assert asserted["hash_status"] == "asserted"
        assert asserted["evidence_source"] == "asserted"
        assert asserted["evidence_strength"] == "asserted_content"
        assert asserted["observation_time"] == "caller_supplied"
        assert asserted["sha256"] is None

        verify = outputs["verify_missing"]
        assert verify["entry_type"] == "missing"
        assert verify["hash_status"] == "unavailable"
        assert verify["caller_digest"]["verified"] is None
        assert verify["sha256"] is None

    def test_reregistering_pending_deferred_output_with_digest_verifies_at_finalization(
        self, tmp_path
    ):
        """Re-registering a pending deferred output with digest/verify_digest/level/metadata updates in place."""
        out_path = tmp_path / "pending_rereg_verified.bin"
        payload = b"verified-deferred-output-bytes"
        expected_sha = hashlib.sha256(payload).hexdigest()

        def _work(_base, run):
            r1 = pubrun.register_output(
                out_path,
                label="model_weights",
                defer=True,
                level="stat",
                metadata={"stage": "init", "epoch": 1},
            )
            assert r1 is not None
            assert r1["hash_status"] == "pending"
            assert r1["registration_count"] == 1
            assert r1["registered_before_creation"] is True

            # Re-register before the file exists with digest, verify_digest, level='hash', and metadata.
            r2 = pubrun.register_output(
                out_path,
                label="model_weights",
                defer=True,
                level="hash",
                digest=expected_sha,
                verify_digest=True,
                metadata={"epoch": 2, "verified_by": "caller"},
            )
            assert r2 is r1
            assert r2["hash_status"] == "pending"
            assert r2["registration_count"] == 2
            assert r2["metadata"] == {"stage": "init", "epoch": 2, "verified_by": "caller"}
            assert r2["caller_digest"] == {
                "algorithm": "sha256",
                "value": expected_sha,
                "verified": None,
            }
            assert len(run.data_files["outputs"]) == 1

            # Write the file on disk before run stop triggers finalize_pending_registrations.
            out_path.write_bytes(payload)

        manifest = _run_manifest(tmp_path, {"level": "stat"}, _work)
        outputs = manifest["data_files"]["outputs"]
        assert len(outputs) == 1
        rec = outputs[0]
        assert rec["label"] == "model_weights"
        assert rec["registration_count"] == 2
        assert rec["registered_before_creation"] is True
        assert rec["metadata"] == {"stage": "init", "epoch": 2, "verified_by": "caller"}
        assert rec["hash_status"] == "completed"
        assert rec["observation_time"] == "at_finalization"
        assert rec["caller_digest"] == {
            "algorithm": "sha256",
            "value": expected_sha,
            "verified": True,
        }
        assert rec["digest"] == {"algorithm": "sha256", "value": expected_sha}
        assert rec["sha256"] == expected_sha
        assert rec["evidence_source"] == "observed"
        assert rec["evidence_strength"] == "verified_content"

        jsonschema = pytest.importorskip("jsonschema")
        schema = json.loads(_SCHEMA_PATH.read_text(encoding="utf-8"))
        jsonschema.validate(manifest, schema)


class TestDetailLevelsAndDeduplication:

    def test_name_level_skips_stat_and_omits_size_bytes(self, tmp_path, monkeypatch):
        """level='name' must not invoke os.stat or os.lstat and must omit size_bytes."""
        p = tmp_path / "nostat.csv"
        p.write_text("a,b\n1,2\n", encoding="utf-8")

        def _forbid_stat(*args, **kwargs):
            raise AssertionError("stat/lstat must not be called at level='name'")

        def _work(_base, _run):
            with monkeypatch.context() as mp:
                mp.setattr(os, "stat", _forbid_stat)
                mp.setattr(os, "lstat", _forbid_stat)
                r1 = pubrun.register_input(p, label="path_only", level="name")
                r2 = pubrun.register_input(
                    p, label="name_asserted", level="name", digest="f" * 64
                )
            assert "size_bytes" not in r1
            assert r1["hash_status"] == "disabled"
            assert r1["evidence_strength"] == "path_only"
            assert r1["sha256"] is None
            assert "size_bytes" not in r2
            assert r2["hash_status"] == "asserted"
            assert r2["evidence_strength"] == "asserted_content"
            assert r2["sha256"] is None

        manifest = _run_manifest(tmp_path, {"level": "hash"}, _work)
        assert len(manifest["data_files"]["inputs"]) == 2

    def test_stat_and_realpath_levels_record_metadata_without_hashing(self, tmp_path):
        """stat omits realpath and skips hashing; realpath includes realpath and skips hashing."""
        p = tmp_path / "meta_only.bin"
        p.write_bytes(b"metadata-only-bytes")

        def _work(_base, _run):
            r_stat = pubrun.register_input(p, label="as_stat", level="stat")
            r_real = pubrun.register_input(p, label="as_realpath", level="realpath")
            assert r_stat["size_bytes"] == len(b"metadata-only-bytes")
            assert "realpath" not in r_stat
            assert r_stat["hash_status"] == "disabled"
            assert r_stat["evidence_source"] == "observed"
            assert r_stat["evidence_strength"] == "metadata_only"
            assert r_stat["sha256"] is None

            assert r_real["size_bytes"] == len(b"metadata-only-bytes")
            assert r_real["realpath"] == os.path.realpath(str(p))
            assert r_real["hash_status"] == "disabled"
            assert r_real["evidence_strength"] == "metadata_only"
            assert r_real["sha256"] is None

        manifest = _run_manifest(tmp_path, {"level": "hash"}, _work)
        assert len(manifest["data_files"]["inputs"]) == 2
        assert "hashing_summary" not in manifest["data_files"]

    def test_mixed_role_deferred_output_finalizes_in_mixed_bucket(self, tmp_path):
        """register_file(..., role='input_output', defer=True) finalizes in data_files['mixed']."""
        mix_path = tmp_path / "deferred_mixed.bin"

        def _work(_base, _run):
            rec = pubrun.register_file(
                mix_path, role="input_output", label="checkpoint_rw", defer=True
            )
            assert rec["hash_status"] == "pending"
            mix_path.write_bytes(b"checkpoint-v1")

        manifest = _run_manifest(tmp_path, {"level": "hash"}, _work)
        mixed = manifest["data_files"]["mixed"]
        assert len(mixed) == 1
        assert mixed[0]["label"] == "checkpoint_rw"
        assert mixed[0]["registered_before_creation"] is True
        assert mixed[0]["hash_status"] == "completed"
        assert mixed[0]["observation_time"] == "at_finalization"
        assert mixed[0]["sha256"] == hashlib.sha256(b"checkpoint-v1").hexdigest()

    def test_none_level_returns_none_and_records_nothing(self, tmp_path):
        p = tmp_path / "ignored.txt"
        p.write_text("ignored", encoding="utf-8")
        results = []

        def _work(_base, _run):
            results.append(pubrun.register_input(p))
            results.append(pubrun.register_output(tmp_path / "out.txt"))

        manifest = _run_manifest(tmp_path, {"level": "none"}, _work)
        assert results == [None, None]
        assert manifest["data_files"]["inputs"] == []
        assert manifest["data_files"]["outputs"] == []

        # Per-call level="none" override on an active hash-level run also returns None.
        override_results = []

        def _work_override(_base, _run):
            override_results.append(pubrun.register_input(p, level="none"))

        manifest2 = _run_manifest(tmp_path, {"level": "hash"}, _work_override)
        assert override_results == [None]
        assert manifest2["data_files"]["inputs"] == []

    def test_unchanged_deduplication_without_double_hashing_and_changed_preserves_both(
        self, tmp_path, monkeypatch
    ):
        """Repeated unchanged registrations increment registration_count without re-hashing;
        modification preserves both observations."""
        p = tmp_path / "evolving.bin"
        p.write_bytes(b"version-1")
        open_count = {"n": 0}
        orig_open = builtins.open

        def _counting_open(file, *args, **kwargs):
            try:
                if os.path.abspath(os.fspath(file)) == os.path.abspath(str(p)):
                    open_count["n"] += 1
            except Exception:
                pass
            return orig_open(file, *args, **kwargs)

        def _work(_base, _run):
            with monkeypatch.context() as mp:
                mp.setattr(builtins, "open", _counting_open)
                r1 = pubrun.register_input(p, label="dataset")
                r2 = pubrun.register_input(p, label="dataset")
                assert r1 is r2
                assert r1["registration_count"] == 2
                assert open_count["n"] == 1  # Zero double-hashing!

                # Modify file (different content and size, plus bumped mtime).
                orig_open(p, "wb").write(b"version-2-modified")
                st = os.stat(p)
                os.utime(p, ns=(st.st_atime_ns, st.st_mtime_ns + 5_000_000))

                r3 = pubrun.register_input(p, label="dataset")
                assert r3 is not r1
                assert r3["registration_count"] == 1
                assert open_count["n"] == 2

        manifest = _run_manifest(tmp_path, {"level": "hash"}, _work)
        inputs = manifest["data_files"]["inputs"]
        assert len(inputs) == 2
        assert inputs[0]["registration_count"] == 2
        assert inputs[0]["sha256"] == hashlib.sha256(b"version-1").hexdigest()
        assert inputs[1]["registration_count"] == 1
        assert inputs[1]["sha256"] == hashlib.sha256(b"version-2-modified").hexdigest()
        assert manifest["data_files"]["hashing_summary"]["files_hashed"] == 2


class TestEdgeCasesBudgetsConcurrencyAndRemoteUris:

    def test_missing_directory_symlinks_special_and_permission_error(
        self, tmp_path, monkeypatch
    ):
        """Missing files, directories, valid/broken symlinks, special files, and permission
        errors all produce honest records without raising into host code."""
        missing_path = tmp_path / "does_not_exist.dat"
        dir_path = tmp_path / "subdir"
        dir_path.mkdir()

        target_file = tmp_path / "real_target.txt"
        target_file.write_text("symlink-target-data", encoding="utf-8")
        valid_link = tmp_path / "valid_link.txt"
        broken_link = tmp_path / "broken_link.txt"
        symlink_supported = True
        try:
            os.symlink(target_file, valid_link)
            os.symlink(tmp_path / "gone_target.txt", broken_link)
        except (OSError, NotImplementedError):
            symlink_supported = False

        fifo_path = tmp_path / "named_pipe"
        fifo_supported = hasattr(os, "mkfifo")
        if fifo_supported:
            try:
                os.mkfifo(fifo_path)
            except OSError:
                fifo_supported = False

        perm_path = tmp_path / "unreadable_stat.dat"
        perm_path.write_bytes(b"secret")

        def _work(_base, _run):
            pubrun.register_input(missing_path, label="missing_plain")
            pubrun.register_input(
                missing_path, label="missing_asserted", digest="a" * 64
            )
            pubrun.register_input(
                missing_path, label="missing_verify", digest="a" * 64, verify_digest=True
            )
            pubrun.register_input(dir_path, label="dir_entry")
            pubrun.register_input(
                dir_path, label="dir_verify", digest="b" * 64, verify_digest=True
            )

            if symlink_supported:
                pubrun.register_input(valid_link, label="valid_symlink")
                pubrun.register_input(broken_link, label="broken_symlink")

            if fifo_supported:
                # Must NOT open or block on FIFO.
                pubrun.register_input(fifo_path, label="fifo_special")
            else:
                # Cross-platform fallback simulating a non-regular special file.
                special_sim = tmp_path / "sim_special"
                special_sim.write_bytes(b"x")
                real_st = os.stat(special_sim)
                fake_st = types.SimpleNamespace(
                    st_dev=real_st.st_dev,
                    st_ino=real_st.st_ino,
                    st_size=0,
                    st_mtime=real_st.st_mtime,
                    st_ctime=real_st.st_ctime,
                    st_mtime_ns=real_st.st_mtime_ns,
                    st_mode=stat.S_IFIFO | 0o600,
                )
                orig_stat = os.stat
                orig_lstat = os.lstat
                with monkeypatch.context() as mp:
                    mp.setattr(
                        os,
                        "stat",
                        lambda p, *a, **kw: fake_st
                        if os.path.abspath(str(p)) == os.path.abspath(str(special_sim))
                        else orig_stat(p, *a, **kw),
                    )
                    mp.setattr(
                        os,
                        "lstat",
                        lambda p, *a, **kw: fake_st
                        if os.path.abspath(str(p)) == os.path.abspath(str(special_sim))
                        else orig_lstat(p, *a, **kw),
                    )
                    pubrun.register_input(special_sim, label="fifo_special")

            # Simulate PermissionError on lstat without raising into host code.
            orig_lstat = os.lstat
            with monkeypatch.context() as mp:
                def _deny_lstat(p, *a, **kw):
                    if os.path.abspath(str(p)) == os.path.abspath(str(perm_path)):
                        raise PermissionError("Permission denied")
                    return orig_lstat(p, *a, **kw)

                mp.setattr(os, "lstat", _deny_lstat)
                pubrun.register_input(perm_path, label="perm_err")

        manifest = _run_manifest(tmp_path, {"level": "hash"}, _work)
        by_label = {r["label"]: r for r in manifest["data_files"]["inputs"]}

        assert by_label["missing_plain"]["entry_type"] == "missing"
        assert by_label["missing_plain"]["hash_status"] == "unavailable"
        assert by_label["missing_plain"]["evidence_source"] == "none"
        assert by_label["missing_plain"]["evidence_strength"] == "unavailable"

        assert by_label["missing_asserted"]["entry_type"] == "missing"
        assert by_label["missing_asserted"]["hash_status"] == "asserted"
        assert by_label["missing_asserted"]["evidence_source"] == "asserted"
        assert by_label["missing_asserted"]["sha256"] is None

        assert by_label["missing_verify"]["entry_type"] == "missing"
        assert by_label["missing_verify"]["hash_status"] == "unavailable"
        assert by_label["missing_verify"]["caller_digest"]["verified"] is None

        assert by_label["dir_entry"]["entry_type"] == "directory"
        assert by_label["dir_entry"]["hash_status"] == "unavailable"
        assert by_label["dir_entry"]["evidence_source"] == "observed"
        assert by_label["dir_entry"]["evidence_strength"] == "metadata_only"

        assert by_label["dir_verify"]["entry_type"] == "directory"
        assert by_label["dir_verify"]["hash_status"] == "unavailable"

        if symlink_supported:
            vlink = by_label["valid_symlink"]
            assert vlink["entry_type"] == "file"
            assert vlink["is_symlink"] is True
            assert vlink["symlink_target"] == str(target_file)
            assert vlink["realpath"] == os.path.realpath(str(target_file))
            assert vlink["hash_status"] == "completed"
            assert vlink["sha256"] == hashlib.sha256(b"symlink-target-data").hexdigest()

            blink = by_label["broken_symlink"]
            assert blink["entry_type"] == "missing"
            assert blink["is_symlink"] is True
            assert blink["hash_status"] == "unavailable"
            assert "broken symlink" in blink["hash_status_detail"]

        assert by_label["fifo_special"]["entry_type"] == "special"
        assert by_label["fifo_special"]["hash_status"] == "unavailable"
        assert by_label["fifo_special"]["evidence_strength"] == "metadata_only"

        assert by_label["perm_err"]["hash_status"] == "failed"
        assert "PermissionError" in by_label["perm_err"]["hash_status_detail"]
        assert by_label["perm_err"]["sha256"] is None

    def test_remote_uris_and_windows_drive_distinction(self, tmp_path):
        """Remote URIs record unsupported_remote_uri without network/FS access; Windows drives do not."""
        from pubrun.capture.file_io import _is_remote_uri

        assert _is_remote_uri("s3://bucket/path/file.parquet") is True
        assert _is_remote_uri("https://example.com/data.csv") is True
        assert _is_remote_uri("gs://bucket/obj") is True
        assert _is_remote_uri("abfs://container@account/blob") is True
        assert _is_remote_uri(r"C:\data\file.csv") is False
        assert _is_remote_uri("C:/data/file.csv") is False
        assert _is_remote_uri("D://data/file.csv") is False
        assert _is_remote_uri("/tmp/local.csv") is False

        def _work(_base, _run):
            pubrun.register_input("s3://my-bucket/train.parquet", label="s3_plain")
            pubrun.register_input(
                "https://example.com/eval.csv",
                label="https_asserted",
                digest="e" * 64,
                verify_digest=False,
            )
            pubrun.register_input(
                "gs://my-bucket/val.parquet",
                label="gs_verify",
                digest="d" * 64,
                verify_digest=True,
            )

        manifest = _run_manifest(tmp_path, {"level": "hash"}, _work)
        by_label = {r["label"]: r for r in manifest["data_files"]["inputs"]}

        s3 = by_label["s3_plain"]
        assert s3["path"] == "s3://my-bucket/train.parquet"
        assert s3["entry_type"] == "unsupported_remote_uri"
        assert s3["hash_status"] == "unavailable"
        assert s3["evidence_source"] == "none"
        assert s3["evidence_strength"] == "unavailable"
        assert s3["sha256"] is None

        https = by_label["https_asserted"]
        assert https["entry_type"] == "unsupported_remote_uri"
        assert https["hash_status"] == "asserted"
        assert https["evidence_source"] == "asserted"
        assert https["evidence_strength"] == "asserted_content"
        assert https["observation_time"] == "caller_supplied"
        assert https["sha256"] is None

        gs = by_label["gs_verify"]
        assert gs["entry_type"] == "unsupported_remote_uri"
        assert gs["hash_status"] == "unavailable"
        assert gs["caller_digest"]["verified"] is None
        assert gs["evidence_source"] == "asserted"
        assert gs["sha256"] is None

    def test_shared_budget_across_pubrun_open_and_register(self, tmp_path):
        """pubrun.open() and pubrun.register_input()/register_output() share one FileIoBudgetTracker."""
        f1 = tmp_path / "open_10b.bin"
        f2 = tmp_path / "reg_10b.bin"
        f3 = tmp_path / "reg_over_10b.bin"
        f1.write_bytes(b"0123456789")
        f2.write_bytes(b"abcdefghij")
        f3.write_bytes(b"klmnopqrst")

        def _work(_base, _run):
            # 10 bytes via pubrun.open()
            with pubrun.open(f1, "rb") as fh:
                fh.read()
            # 10 bytes via pubrun.register_input() -> reaches 20-byte total cap
            pubrun.register_input(f2, label="within_total")
            # Next 10-byte file exceeds 20-byte shared total cap -> over_budget
            pubrun.register_input(f3, label="exceeds_total")

        manifest = _run_manifest(
            tmp_path,
            {"level": "hash", "max_total_hash_bytes": 20},
            _work,
        )
        inputs = manifest["data_files"]["inputs"]
        assert len(inputs) == 3
        assert inputs[0]["hash_status"] == "completed"
        assert inputs[1]["hash_status"] == "completed"
        assert inputs[2]["hash_status"] == "over_budget"
        assert inputs[2]["sha256"] is None

        summary = manifest["data_files"]["hashing_summary"]
        assert summary["total_bytes_hashed"] == 20
        assert summary["files_hashed"] == 2
        assert summary["files_skipped_over_budget"] == 1

    def test_concurrent_registration_thread_safety(self, tmp_path):
        """Concurrent threads registering distinct and shared files stay thread-safe."""
        shared = tmp_path / "shared.bin"
        shared.write_bytes(b"shared-content")
        distinct = []
        for idx in range(6):
            p = tmp_path / f"worker_{idx}.bin"
            p.write_bytes(f"payload-{idx}".encode("utf-8"))
            distinct.append(p)

        def _work(_base, _run):
            barrier = threading.Barrier(len(distinct))
            errors = []

            def _worker(i, p):
                try:
                    barrier.wait()
                    pubrun.register_input(p, label=f"w_{i}")
                    pubrun.register_input(shared, label="shared_lbl")
                except Exception as exc:
                    errors.append(exc)

            threads = [
                threading.Thread(target=_worker, args=(i, p))
                for i, p in enumerate(distinct)
            ]
            for t in threads:
                t.start()
            for t in threads:
                t.join(timeout=10)
            assert errors == []

        manifest = _run_manifest(tmp_path, {"level": "hash"}, _work)
        inputs = manifest["data_files"]["inputs"]
        # 6 distinct worker files + 1 deduplicated shared file
        assert len(inputs) == 7
        shared_recs = [r for r in inputs if r["label"] == "shared_lbl"]
        assert len(shared_recs) == 1
        assert shared_recs[0]["registration_count"] == len(distinct)

    def test_ghost_mode_and_closed_event_stream_safety(self, tmp_path, monkeypatch):
        """Registration in Ghost Mode and pending finalization with closed/None event_stream never crash."""
        from pubrun.capture.file_io import (
            finalize_pending_registrations,
            register_file_provenance,
        )

        # 1. Genuine Ghost Mode run (unwritable run directory)
        orig_mkdir = Path.mkdir

        def _fail_mkdir(self, *args, **kwargs):
            if "pubrun-" in str(self):
                raise PermissionError("read-only filesystem")
            return orig_mkdir(self, *args, **kwargs)

        pubrun.tracker._active_run = None
        with monkeypatch.context() as mp:
            mp.setattr(Path, "mkdir", _fail_mkdir)
            ghost_run = pubrun.start(console={"capture_mode": "off"})
        try:
            assert ghost_run._outcome == "ghost"
            assert ghost_run.is_active is False
            assert pubrun.register_input(tmp_path / "any.txt") is None
            assert pubrun.register_output(tmp_path / "any_out.txt", defer=True) is None
        finally:
            ghost_run.stop()
            pubrun.tracker._active_run = None

        # 2. Direct pending registration + finalization with closed event_stream and event_stream=None
        out_path = tmp_path / "closed_stream_out.bin"
        dummy_run = types.SimpleNamespace(
            config={"capture": {"file_io": {"level": "hash"}}},
            data_files={"inputs": [], "outputs": [], "mixed": []},
            _data_files_lock=threading.Lock(),
            _pending_file_registrations=[],
            event_stream=types.SimpleNamespace(_file=None, emit=lambda *a, **kw: (_ for _ in ()).throw(ValueError("closed"))),
        )
        register_file_provenance(dummy_run, out_path, role="output", defer=True)
        out_path.write_bytes(b"created-before-finalize")
        finalize_pending_registrations(dummy_run)
        assert dummy_run.data_files["outputs"][0]["hash_status"] == "completed"
        assert (
            dummy_run.data_files["outputs"][0]["sha256"]
            == hashlib.sha256(b"created-before-finalize").hexdigest()
        )


class TestValidationInactivePolicyAndSchema:

    @pytest.mark.parametrize("active", [False, True])
    def test_programmer_errors_raise_predictably_active_or_inactive(self, tmp_path, active):
        """Invalid role, level, path, digest, verify_digest, and metadata raise ValueError/TypeError."""
        p = tmp_path / "valid.txt"
        p.write_text("ok", encoding="utf-8")

        def _check():
            with pytest.raises(TypeError):
                pubrun.register_file(None)  # type: ignore[arg-type]
            with pytest.raises(TypeError):
                pubrun.register_input(12345)  # type: ignore[arg-type]
            with pytest.raises(ValueError):
                pubrun.register_input("")
            with pytest.raises(ValueError):
                pubrun.register_input("   ")
            with pytest.raises(ValueError):
                pubrun.register_file(p, role="bogus")
            with pytest.raises(ValueError):
                pubrun.register_input(p, level="invalid_level")
            with pytest.raises(ValueError):
                pubrun.register_input(p, digest="")
            with pytest.raises(ValueError):
                pubrun.register_input(p, digest="   ")
            with pytest.raises(ValueError):
                pubrun.register_input(p, digest=12345)  # type: ignore[arg-type]
            with pytest.raises(ValueError):
                pubrun.register_input(p, digest="abc", digest_algorithm="")
            with pytest.raises(ValueError, match="verify_digest=True requires"):
                pubrun.register_input(p, verify_digest=True)
            with pytest.raises(ValueError):
                pubrun.register_output(p, metadata=["not", "a", "dict"])  # type: ignore[arg-type]
            with pytest.raises((TypeError, ValueError)):
                pubrun.register_input(p, metadata={"bad": object()})
            with pytest.raises((TypeError, ValueError)):
                pubrun.register_input(p, metadata={"nan": float("nan")})

        if active:
            _run_manifest(tmp_path, {"level": "stat"}, lambda _b, _r: _check())
        else:
            pubrun.tracker._active_run = None
            _check()

    def test_inactive_run_honors_on_inactive_annotate_policy(self, tmp_path, monkeypatch, caplog):
        """Inactive calls honor ignore, warn, and error policies identically to annotate()."""
        from pubrun import config as config_module

        p = tmp_path / "file.txt"
        p.write_text("data", encoding="utf-8")
        pubrun.tracker._active_run = None

        orig_resolve = config_module.resolve_config

        def _with_policy(policy):
            def _mock(overrides=None):
                cfg = orig_resolve(overrides)
                cfg.setdefault("events", {})["on_inactive_annotate"] = policy
                return cfg
            return _mock

        # 1. ignore (default)
        with monkeypatch.context() as mp:
            mp.setattr(config_module, "resolve_config", _with_policy("ignore"))
            assert pubrun.register_file(p) is None
            assert pubrun.register_input(p) is None
            assert pubrun.register_output(p) is None

        # 2. warn
        with monkeypatch.context() as mp:
            mp.setattr(config_module, "resolve_config", _with_policy("warn"))
            with caplog.at_level(logging.WARNING, logger="pubrun"):
                assert pubrun.register_input(p) is None
            assert any("no active run" in r.message.lower() for r in caplog.records)

        # 3. error
        with monkeypatch.context() as mp:
            mp.setattr(config_module, "resolve_config", _with_policy("error"))
            with pytest.raises(RuntimeError, match="no run is active"):
                pubrun.register_file(p)
            with pytest.raises(RuntimeError, match="no run is active"):
                pubrun.register_input(p)
            with pytest.raises(RuntimeError, match="no run is active"):
                pubrun.register_output(p)

    def test_manifest_with_all_registration_variants_validates_against_schema(self, tmp_path):
        """End-to-end manifest combining pubrun.open() and every registration variant conforms."""
        jsonschema = pytest.importorskip("jsonschema")
        schema = json.loads(_SCHEMA_PATH.read_text(encoding="utf-8"))

        opened_in = tmp_path / "opened.bin"
        opened_in.write_bytes(b"via-open")
        reg_in = tmp_path / "reg_in.bin"
        reg_in.write_bytes(b"via-reg-in")
        asserted_in = tmp_path / "asserted.bin"
        asserted_in.write_bytes(b"asserted")
        mismatch_in = tmp_path / "mismatch.bin"
        mismatch_in.write_bytes(b"mismatch")
        unsupported_in = tmp_path / "unsupported.bin"
        unsupported_in.write_bytes(b"unsupported")
        name_only_in = tmp_path / "name_only.bin"
        name_only_in.write_bytes(b"name-only")
        dir_in = tmp_path / "dir_in"
        dir_in.mkdir()
        deferred_out = tmp_path / "deferred_out.bin"
        missing_out = tmp_path / "missing_out.bin"
        mixed_file = tmp_path / "mixed.bin"
        mixed_file.write_bytes(b"mixed-data")

        def _work(_base, _run):
            with pubrun.open(opened_in, "rb") as fh:
                fh.read()
            pubrun.register_input(reg_in, label="verified_auto", metadata={"split": "train"})
            pubrun.register_input(
                asserted_in, label="asserted_only", digest="1" * 64, verify_digest=False
            )
            pubrun.register_input(
                reg_in,
                label="verified_caller",
                digest=hashlib.sha256(b"via-reg-in").hexdigest(),
                verify_digest=True,
            )
            pubrun.register_input(
                mismatch_in, label="mismatched", digest="2" * 64, verify_digest=True
            )
            pubrun.register_input(
                unsupported_in,
                label="unsupported_alg",
                digest="deadbeef",
                digest_algorithm="blake3",
                verify_digest=True,
            )
            pubrun.register_input(name_only_in, label="name_lvl", level="name")
            pubrun.register_input(dir_in, label="dir_lbl")
            pubrun.register_input(tmp_path / "missing.bin", label="missing_lbl")
            pubrun.register_input("s3://bucket/remote.parquet", label="remote_lbl")
            pubrun.register_output(deferred_out, label="deferred_created")
            deferred_out.write_bytes(b"created-later")
            pubrun.register_output(missing_out, label="deferred_missing")
            pubrun.register_file(mixed_file, role="input_output", label="mixed_lbl")

        manifest = _run_manifest(tmp_path, {"level": "hash"}, _work)
        jsonschema.validate(manifest, schema)
        assert len(manifest["data_files"]["inputs"]) == 10
        assert len(manifest["data_files"]["outputs"]) == 2
        assert len(manifest["data_files"]["mixed"]) == 1
        assert "hashing_summary" in manifest["data_files"]
