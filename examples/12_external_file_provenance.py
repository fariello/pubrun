#!/usr/bin/env python3
"""Test 12: External file provenance around an unmodified library.

Many real pipelines read and write data through a third-party library (pandas,
PyArrow, NumPy, a C extension) whose file I/O pubrun cannot and does not wrap.
pubrun never patches ``builtins.open``; instead the caller registers the files
that library touches:

- ``pubrun.register_input(path, level="hash")`` hashes the on-disk bytes, so
  the manifest records VERIFIED content.
- ``pubrun.register_input(path, digest=...)`` records a caller-supplied digest
  as ASSERTED evidence (pubrun did not read the bytes).
- ``pubrun.register_output(path, level="hash")`` may be called BEFORE the file
  exists; the pending record is completed automatically when the run ends.

The "library" below is a tiny standard-library CSV processor that uses plain
``open()``, standing in for any component you cannot modify. This example has
no third-party dependencies.
"""
import os

os.environ["PUBRUN_AUTO_START"] = "false"

import csv
import hashlib
import json
import shutil
import tempfile

import pubrun


class CsvTableLibrary:
    """Stand-in for an external library: does its own I/O with builtins.open()."""

    @staticmethod
    def read_rows(path):
        with open(path, "r", newline="", encoding="utf-8") as handle:
            return list(csv.DictReader(handle))

    @staticmethod
    def write_summary(path, rows, lookup):
        totals = {}
        for row in rows:
            key = lookup.get(row["site"], "unknown")
            totals[key] = totals.get(key, 0.0) + float(row["value"])
        with open(path, "w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(["region", "total"])
            for region in sorted(totals):
                writer.writerow([region, "%.2f" % totals[region]])


def _sha256(path):
    with open(path, "rb") as handle:
        return hashlib.sha256(handle.read()).hexdigest()


def _by_label(records):
    return {rec.get("label"): rec for rec in records}


def main():
    print("Testing 12_external_file_provenance...")
    workdir = tempfile.mkdtemp(prefix="pubrun-ex12-")
    raw_csv = os.path.join(workdir, "raw_observations.csv")
    ref_csv = os.path.join(workdir, "reference_lookup.csv")
    out_csv = os.path.join(workdir, "aggregated_summary.csv")
    try:
        with open(raw_csv, "w", newline="", encoding="utf-8") as handle:
            handle.write("site,value\nA,1.5\nB,2.0\nA,3.25\nC,4.0\n")
        with open(ref_csv, "w", newline="", encoding="utf-8") as handle:
            handle.write("site,region\nA,north\nB,south\nC,south\n")
        # A digest the caller already knows (for example from a data catalog).
        precomputed_sha = _sha256(ref_csv)

        with pubrun.tracked_run() as active:
            run_dir = getattr(getattr(active, "run_tracker", active), "run_dir", None)

            # 1. Verified input: pubrun reads and hashes the bytes itself.
            pubrun.register_input(raw_csv, label="raw_observations", level="hash")
            # 2. Asserted input: pubrun records the caller's digest without reading.
            pubrun.register_input(
                ref_csv,
                label="reference_lookup",
                digest=precomputed_sha,
                digest_algorithm="sha256",
            )
            # 3. Output registered before the library creates it.
            pubrun.register_output(out_csv, label="aggregated_summary", level="hash")

            rows = CsvTableLibrary.read_rows(raw_csv)
            lookup = {r["site"]: r["region"] for r in CsvTableLibrary.read_rows(ref_csv)}
            CsvTableLibrary.write_summary(out_csv, rows, lookup)
            expected_out_sha = _sha256(out_csv)

        manifest_path = os.path.join(str(run_dir), "manifest.json")
        with open(manifest_path, "r", encoding="utf-8") as handle:
            payload = json.load(handle)
    finally:
        shutil.rmtree(workdir, ignore_errors=True)

    data_files = payload.get("data_files", {})
    inputs = _by_label(data_files.get("inputs", []))
    outputs = _by_label(data_files.get("outputs", []))

    raw = inputs.get("raw_observations")
    ref = inputs.get("reference_lookup")
    out = outputs.get("aggregated_summary")
    assert raw is not None, "verified input missing from data_files.inputs"
    assert ref is not None, "asserted input missing from data_files.inputs"
    assert out is not None, "registered output missing from data_files.outputs"

    # Verified content: pubrun hashed the bytes at registration time.
    assert raw["hash_status"] == "completed", raw
    assert raw["evidence_source"] == "observed", raw
    assert raw["evidence_strength"] == "verified_content", raw
    assert raw["observation_time"] == "at_registration", raw
    assert raw["sha256"], raw

    # Asserted content: the digest is the caller's claim, not an observation.
    assert ref["hash_status"] == "asserted", ref
    assert ref["evidence_source"] == "asserted", ref
    assert ref["evidence_strength"] == "asserted_content", ref
    assert ref["sha256"] is None, ref
    assert ref["caller_digest"]["value"] == precomputed_sha, ref

    # Pre-creation output: completed and verified at run finalization.
    assert out["registered_before_creation"] is True, out
    assert out["hash_status"] == "completed", out
    assert out["evidence_strength"] == "verified_content", out
    assert out["observation_time"] == "at_finalization", out
    assert out["sha256"] == expected_out_sha, out

    assert not os.path.exists(workdir), "temporary dataset files were not cleaned up"

    print("  raw_observations:   %s / %s" % (raw["hash_status"], raw["evidence_strength"]))
    print("  reference_lookup:   %s / %s" % (ref["hash_status"], ref["evidence_strength"]))
    print("  aggregated_summary: %s / %s" % (out["hash_status"], out["evidence_strength"]))
    print("[PASS] PASS: 12_external_file_provenance.py")


if __name__ == "__main__":
    main()
