"""Behavioral unit tests for shared reproducibility assessment and hydration reporting."""

import copy
import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict

import pytest

from pubrun.report import checks
from pubrun.report.reproducibility import (
    CATEGORY_ORDER,
    CATEGORY_STATUSES,
    COMPARISON_OUTCOMES,
    DEFAULT_STALE_PARENT_SECONDS,
    EVIDENCE_STATUSES,
    IMPACT_LEVELS,
    NON_GUARANTEE_DISCLAIMER,
    assess_manifest_reproducibility,
    assess_run,
    format_reproducibility_detail,
    format_reproducibility_summary,
)
from pubrun.report.utils import (
    HYDRABLE_SECTIONS,
    HydrationReport,
    hydrate_manifest,
    hydrate_manifest_with_report,
)


def _adequate_manifest(**overrides: Any) -> Dict[str, Any]:
    """Build a complete, clean manifest that should assess as adequate across all 7 categories."""
    manifest: Dict[str, Any] = {
        "schema_version": "1.0",
        "manifest_type": "pubrun-manifest",
        "run": {"run_id": "run-ok-001", "capture_state": {"status": "complete"}},
        "timing": {
            "started_at_utc": 1780250100.0,
            "ended_at_utc": 1780250160.0,
            "elapsed_seconds": 60.0,
            "capture_state": {"status": "complete"},
        },
        "status": {
            "outcome": "completed",
            "exit_code": 0,
            "capture_state": {"status": "complete"},
        },
        "invocation": {
            "argv": ["train.py", "--epochs", "10"],
            "rerun_command": "cd /work && python train.py --epochs 10",
            "entrypoint_type": "script",
            "script": {
                "path": "train.py",
                "real_path": "/work/train.py",
                "sha256": "a" * 64,
                "size": 1024,
                "mtime": 1780250050.0,
            },
            "working_directory": {"path": "/work", "real_path": "/work"},
            "inputs": [],
            "capture_state": {"status": "complete"},
        },
        "git": {
            "repo_root": "/work",
            "commit": "1234567890abcdef1234567890abcdef12345678",
            "branch": "main",
            "dirty": False,
            "capture_state": {"status": "complete"},
        },
        "python": {
            "version": "3.11.8",
            "implementation": "cpython",
            "environment_kind": "venv",
            "capture_state": {"status": "complete"},
        },
        "host": {
            "os_name": "Linux",
            "os_version": "6.8.0",
            "hostname": "compute-01",
            "capture_state": {"status": "complete"},
        },
        "hardware": {
            "cpu": {"architecture": "x86_64", "model": "EPYC"},
            "memory_total_bytes": 68719476736,
            "capture_state": {"status": "complete"},
        },
        "packages": {
            "mode": "full-environment",
            "records": [{"name": "numpy", "version": "1.26.4", "editable": False}],
            "capture_state": {"status": "complete"},
        },
        "environment": {
            "mode": "filtered",
            "variables": [
                {
                    "name": "OMP_NUM_THREADS",
                    "value": {"representation": "plain", "value": "4"},
                }
            ],
            "capture_state": {"status": "complete"},
        },
        "data_files": {
            "inputs": [
                {
                    "path": "data/input.csv",
                    "realpath": "/work/data/input.csv",
                    "size_bytes": 512,
                    "sha256": "b" * 64,
                    "evidence_source": "observed",
                    "hash_status": "completed",
                }
            ],
            "outputs": [
                {
                    "path": "out/model.bin",
                    "realpath": "/work/out/model.bin",
                    "size_bytes": 2048,
                    "sha256": "c" * 64,
                    "evidence_source": "observed",
                    "hash_status": "completed",
                }
            ],
            "mixed": [],
        },
        "resources": {
            "scope": "tree",
            "capture_state": {"status": "complete"},
        },
        "console": {"capture_mode": "standard", "capture_state": {"status": "complete"}},
        "subprocesses": [],
        "capture": {
            "subprocesses_enabled": True,
            "file_provenance_available": True,
            "capture_state": {"status": "complete"},
        },
        "pubrun_imports": {
            "selected_mode": "auto",
            "selected_behavior": {"patch_subprocesses": True},
        },
        "determinism": {
            "registered_seeds": [{"name": "numpy", "value": 42}],
            "capture_state": {"status": "complete"},
        },
        "config": {"notices": [], "capture_state": {"status": "complete"}},
        "errors": {"records": [], "capture_state": {"status": "complete"}},
        "meta_ref": None,
    }
    manifest.update(overrides)
    return manifest


def _find_by_code(assessment: Dict[str, Any], code: str) -> Dict[str, Any]:
    matches = [f for f in assessment["findings"] if f["code"] == code]
    assert matches, f"Expected finding {code!r}; got {[f['code'] for f in assessment['findings']]}"
    return matches[0]


def _category_map(assessment: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    return {c["name"]: c for c in assessment["categories"]}


class TestParentHydrationReport:
    """Tests for hydrate_manifest_with_report and backwards-compatible hydrate_manifest."""

    def test_hydration_no_meta_ref_does_not_mutate_input(self, tmp_path: Path):
        manifest = _adequate_manifest(meta_ref=None)
        snapshot_before = copy.deepcopy(manifest)

        hydrated, warnings, report = hydrate_manifest_with_report(
            str(tmp_path / "manifest.json"), manifest
        )
        assert warnings == []
        assert isinstance(report, HydrationReport)
        assert report.status == "none"
        assert report.inherited_sections == []
        assert set(report.direct_sections) == {"hardware", "python", "packages", "environment", "git"}
        assert hydrated == snapshot_before
        assert hydrated is not manifest
        assert manifest == snapshot_before

    def test_hydration_valid_parent_separates_inherited_vs_direct_and_does_not_mutate(
        self, tmp_path: Path
    ):
        parent_meta = {
            "manifest_type": "pubrun-meta-snapshot",
            "timing": {"started_at_utc": 1780250080.0},
            "host": {"hostname": "compute-01", "os_name": "Linux"},
            "hardware": {
                "cpu": {"model": "EPYC-9654"},
                "capture_state": {"status": "complete"},
            },
            "packages": {
                "mode": "full-environment",
                "records": [{"name": "scipy", "version": "1.13.0"}],
                "capture_state": {"status": "complete"},
            },
            "python": {
                "version": "3.11.8",
                "capture_state": {"status": "complete"},
            },
            "git": {
                "commit": "1234567890abcdef1234567890abcdef12345678",
                "dirty": False,
                "capture_state": {"status": "complete"},
            },
        }
        (tmp_path / "meta.json").write_text(json.dumps(parent_meta), encoding="utf-8")

        child = _adequate_manifest(
            meta_ref="meta.json",
            timing={"started_at_utc": 1780250120.0},
            hardware={"capture_state": {"status": "suppressed"}},
            packages={"capture_state": {"status": "suppressed"}},
        )
        child_copy = copy.deepcopy(child)

        hydrated, warnings, report = hydrate_manifest_with_report(
            str(tmp_path / "manifest.json"), child
        )

        # Caller's raw manifest dict is untouched.
        assert child == child_copy
        assert "is_hydrated" not in child["hardware"]
        assert warnings == []

        assert report.status == "hydrated"
        assert report.inherited_sections == ["hardware", "packages"]
        assert "python" in report.direct_sections
        assert "git" in report.direct_sections
        assert "hardware" not in report.direct_sections
        assert "packages" not in report.direct_sections
        assert report.parent_started_at_utc == 1780250080.0
        assert report.child_started_at_utc == 1780250120.0
        assert report.age_seconds == pytest.approx(40.0)
        assert report.script_modified_after_parent is False
        assert report.identity_mismatches == []

        assert hydrated["hardware"]["is_hydrated"] is True
        assert hydrated["packages"]["is_hydrated"] is True
        assert hydrated["python"].get("is_hydrated") is None
        assert json.loads(json.dumps(report.to_dict())) == report.to_dict()

    def test_hydration_negative_age_and_script_drift_and_identity_mismatches(
        self, tmp_path: Path
    ):
        parent_meta = {
            "manifest_type": "pubrun-meta-snapshot",
            "timing": {"started_at_utc": 1780250500.0},
            "host": {
                "hostname": {"representation": "plain", "value": "head-node-01"},
                "os_name": "Linux",
            },
            "python": {"version": "3.10.12", "capture_state": {"status": "complete"}},
            "git": {"commit": "aaaaaaaaaaaaaaaa", "capture_state": {"status": "complete"}},
            "hardware": {"cpu": {"model": "Xeon"}, "capture_state": {"status": "complete"}},
        }
        (tmp_path / "meta.json").write_text(json.dumps(parent_meta), encoding="utf-8")

        child = _adequate_manifest(
            meta_ref="meta.json",
            timing={"started_at_utc": 1780250100.0},
            host={
                "hostname": {"representation": "plain", "value": "compute-node-99"},
                "os_name": "Darwin",
                "capture_state": {"status": "complete"},
            },
            python={"version": "3.11.8", "capture_state": {"status": "complete"}},
            git={"commit": "bbbbbbbbbbbbbbbb", "dirty": False, "capture_state": {"status": "complete"}},
            hardware={"capture_state": {"status": "suppressed"}},
        )
        child["invocation"]["script"]["mtime"] = 1780250600.0

        _, warnings, report = hydrate_manifest_with_report(
            str(tmp_path / "manifest.json"), child
        )

        assert report.status == "hydrated"
        assert report.age_seconds == pytest.approx(-400.0)
        assert report.script_modified_after_parent is True
        assert any("Drift Detected" in w for w in warnings)

        mismatched_fields = {m["field"]: (m["parent"], m["child"]) for m in report.identity_mismatches}
        assert mismatched_fields["host.hostname"] == ("head-node-01", "compute-node-99")
        assert mismatched_fields["host.os_name"] == ("Linux", "Darwin")
        assert mismatched_fields["python.version"] == ("3.10.12", "3.11.8")
        assert mismatched_fields["git.commit"] == ("aaaaaaaaaaaaaaaa", "bbbbbbbbbbbbbbbb")

    def test_hydration_redacted_hostname_does_not_create_false_mismatch(self, tmp_path: Path):
        parent_meta = {
            "manifest_type": "pubrun-meta-snapshot",
            "host": {"hostname": {"representation": "redacted"}, "os_name": "Linux"},
            "hardware": {"cpu": {"model": "Xeon"}, "capture_state": {"status": "complete"}},
        }
        (tmp_path / "meta.json").write_text(json.dumps(parent_meta), encoding="utf-8")

        child = _adequate_manifest(
            meta_ref="meta.json",
            host={"hostname": "compute-01", "os_name": "Linux", "capture_state": {"status": "complete"}},
            hardware={"capture_state": {"status": "suppressed"}},
        )
        _, _, report = hydrate_manifest_with_report(str(tmp_path / "manifest.json"), child)
        assert report.status == "hydrated"
        assert report.identity_mismatches == []

    def test_hydration_security_order_extension_before_policy_before_exists(self, tmp_path: Path):
        run_dir = tmp_path / "runs" / "pubrun-1"
        run_dir.mkdir(parents=True)
        manifest_path = str(run_dir / "manifest.json")

        # 1. Non-.json outside dir (does not even exist) -> invalid_extension first.
        _, w_ext, rep_ext = hydrate_manifest_with_report(
            manifest_path, {"meta_ref": "../../does_not_exist.txt"}
        )
        assert rep_ext.status == "invalid_extension"
        assert any("Security" in w for w in w_ext)

        # 2. .json outside dir (does not exist) -> blocked_by_policy BEFORE missing check.
        _, w_pol, rep_pol = hydrate_manifest_with_report(
            manifest_path, {"meta_ref": "../../does_not_exist.json"}
        )
        assert rep_pol.status == "blocked_by_policy"
        assert any("Security" in w and "outside" in w.lower() for w in w_pol)

        # 3. .json inside dir that does not exist -> missing.
        _, w_miss, rep_miss = hydrate_manifest_with_report(
            manifest_path, {"meta_ref": "absent.json"}
        )
        assert rep_miss.status == "missing"
        assert any("not found" in w.lower() for w in w_miss)

    def test_hydration_invalid_json_and_invalid_type_and_malformed_inputs(self, tmp_path: Path):
        manifest_path = str(tmp_path / "manifest.json")

        # Invalid JSON syntax.
        (tmp_path / "broken.json").write_text("{not valid json", encoding="utf-8")
        hydrated_j, warn_j, rep_j = hydrate_manifest_with_report(
            manifest_path, {"meta_ref": "broken.json", "hardware": {"capture_state": {"status": "suppressed"}}}
        )
        assert rep_j.status == "invalid_json"
        assert warn_j
        assert hydrated_j["hardware"]["capture_state"]["status"] == "suppressed"

        # JSON array instead of object.
        (tmp_path / "list.json").write_text("[1, 2, 3]", encoding="utf-8")
        _, _, rep_list = hydrate_manifest_with_report(manifest_path, {"meta_ref": "list.json"})
        assert rep_list.status == "invalid_type"

        # Wrong manifest_type (e.g. pointing to another run manifest instead of meta snapshot).
        (tmp_path / "wrong_type.json").write_text(
            json.dumps({"manifest_type": "pubrun-manifest", "hardware": {"cpu": {"model": "X"}}}),
            encoding="utf-8",
        )
        hydrated_wt, _, rep_wt = hydrate_manifest_with_report(
            manifest_path, {"meta_ref": "wrong_type.json"}
        )
        assert rep_wt.status == "invalid_type"
        assert "hardware" not in hydrated_wt

        # Non-string meta_ref.
        _, _, rep_ns = hydrate_manifest_with_report(manifest_path, {"meta_ref": 12345})
        assert rep_ns.status == "invalid_type"

        # Non-dict manifest input does not raise.
        hydrated_bad, warn_bad, rep_bad = hydrate_manifest_with_report(
            manifest_path, "not-a-dict"  # type: ignore[arg-type]
        )
        assert hydrated_bad == {}
        assert rep_bad.status == "failed"
        assert warn_bad

    def test_hydrate_manifest_backwards_compatible_wrapper(self, tmp_path: Path):
        (tmp_path / "meta.json").write_text(
            json.dumps({"hardware": {"cpu": {"model": "M3"}, "capture_state": {"status": "complete"}}}),
            encoding="utf-8",
        )
        child = {"meta_ref": "meta.json", "hardware": {"capture_state": {"status": "suppressed"}}}
        hydrated, warnings = hydrate_manifest(str(tmp_path / "manifest.json"), child)
        assert warnings == []
        assert hydrated["hardware"]["is_hydrated"] is True
        assert hydrated["hardware"]["cpu"]["model"] == "M3"
        # Caller dict remains unmutated.
        assert child["hardware"] == {"capture_state": {"status": "suppressed"}}


class TestReproducibilityAssessmentModel:
    """Behavioral tests for the shared evidence taxonomy and recorded-manifest gap engine."""

    def test_taxonomy_constants_and_adequate_manifest_with_disclaimer_and_no_score(self):
        assert EVIDENCE_STATUSES == (
            "observed",
            "inferred",
            "asserted",
            "inherited",
            "unavailable",
            "not_checked",
        )
        assert CATEGORY_STATUSES == ("adequate", "gaps", "mismatch", "uncertain", "not_checked")
        assert IMPACT_LEVELS == ("material", "portability", "incidental", "informational")
        assert COMPARISON_OUTCOMES == (
            "match",
            "mismatch",
            "portability_diff",
            "unknown",
            "not_checked",
        )
        assert DEFAULT_STALE_PARENT_SECONDS == 86400.0

        manifest = _adequate_manifest()
        result = assess_manifest_reproducibility(manifest, current_hostname="compute-01")

        assert set(result.keys()) == {
            "schema_version",
            "mode",
            "summary",
            "next_action",
            "next_actions",
            "disclaimer",
            "categories",
            "findings",
            "parent_metadata",
            "preflight",
        }
        assert result["schema_version"] == "1.0"
        assert result["mode"] == "manifest"
        assert result["disclaimer"] == NON_GUARANTEE_DISCLAIMER
        assert "not guarantee" in result["disclaimer"].lower()
        assert result["preflight"] == {
            "requested": False,
            "status": "not_checked",
            "counts": {},
            "checks": [],
        }

        # Zero numerical reproducibility scores anywhere in schema keys.
        for forbidden in ("score", "reproducibility_score", "grade", "percent", "rating"):
            assert forbidden not in result

        assert [c["name"] for c in result["categories"]] == list(CATEGORY_ORDER)
        for cat in result["categories"]:
            assert cat["status"] == "adequate", f"{cat['name']} was {cat['status']}: {cat}"
            assert cat["evidence_status"] in EVIDENCE_STATUSES

        assert [f for f in result["findings"] if f["severity"] == "warn"] == []
        assert result["next_action"]
        assert json.loads(json.dumps(result)) == result

    def test_sparse_and_legacy_manifests_never_raise_and_note_incompleteness(self):
        empty_res = assess_manifest_reproducibility({})
        assert empty_res["disclaimer"] == NON_GUARANTEE_DISCLAIMER
        sparse_f = _find_by_code(empty_res, "sparse_or_legacy_manifest")
        assert sparse_f["severity"] == "info"
        assert sparse_f["evidence_status"] == "unavailable"
        assert "absence of warnings" in sparse_f["message"].lower()

        # Garbage / malformed non-dict inputs do not raise.
        bad_res = assess_manifest_reproducibility(None)
        assert bad_res["disclaimer"] == NON_GUARANTEE_DISCLAIMER
        assert len(bad_res["categories"]) == 7

        weird_res = assess_manifest_reproducibility(
            {"git": 42, "packages": "oops", "data_files": ["bad"], "invocation": 7, "host": None}
        )
        assert len(weird_res["categories"]) == 7

    def test_source_dirty_timeout_failed_unavailable_suppressed_and_unhashed_script(self):
        # Dirty repo without diff -> warn / material / observed.
        dirty = _adequate_manifest()
        dirty["git"]["dirty"] = True
        res_dirty = assess_manifest_reproducibility(dirty, current_hostname="compute-01")
        f_dirty = _find_by_code(res_dirty, "git_dirty_unrecorded")
        assert f_dirty["severity"] == "warn"
        assert f_dirty["impact"] == "material"
        assert f_dirty["evidence_status"] == "observed"
        assert _category_map(res_dirty)["source"]["status"] == "gaps"

        # Dirty check skipped -> info / not_checked.
        unchecked = _adequate_manifest()
        unchecked["git"]["dirty"] = None
        f_unc = _find_by_code(assess_manifest_reproducibility(unchecked), "git_dirty_not_checked")
        assert f_unc["severity"] == "info"
        assert f_unc["evidence_status"] == "not_checked"

        # Timeout & failed -> warn / material / unavailable.
        for status, code in (("timeout", "git_timeout"), ("failed", "git_failed")):
            m = _adequate_manifest(git={"capture_state": {"status": status, "detail": "slow fs"}})
            f = _find_by_code(assess_manifest_reproducibility(m), code)
            assert f["severity"] == "warn"
            assert f["impact"] == "material"
            assert f["evidence_status"] == "unavailable"

        # Unavailable & suppressed -> info / unavailable (do not fail --strict).
        m_unavail = _adequate_manifest(git={"capture_state": {"status": "unavailable"}})
        f_unavail = _find_by_code(assess_manifest_reproducibility(m_unavail), "git_unavailable")
        assert f_unavail["severity"] == "info"
        assert f_unavail["evidence_status"] == "unavailable"

        m_off = _adequate_manifest(git={"capture_state": {"status": "suppressed"}})
        f_off = _find_by_code(assess_manifest_reproducibility(m_off), "git_off")
        assert f_off["severity"] == "info"
        assert f_off["evidence_status"] == "unavailable"

        # Inherited dirty git carries evidence_status == "inherited".
        inherited_dirty = _adequate_manifest()
        inherited_dirty["git"]["dirty"] = True
        inherited_dirty["git"]["is_hydrated"] = True
        f_inh = _find_by_code(assess_manifest_reproducibility(inherited_dirty), "git_dirty_unrecorded")
        assert f_inh["evidence_status"] == "inherited"

        # Unhashed script -> info / not_checked.
        unhashed_script = _adequate_manifest()
        unhashed_script["invocation"]["script"].pop("sha256")
        unhashed_script["invocation"]["script"]["sha256_skipped"] = "file exceeds 1MB"
        f_scr = _find_by_code(assess_manifest_reproducibility(unhashed_script), "script_unhashed")
        assert f_scr["severity"] == "info"
        assert f_scr["evidence_status"] == "not_checked"
        assert "1MB" in f_scr["message"]

    def test_packages_modes_editable_states_and_future_fields(self):
        # imported-only + editable + optional w4hxkh fields (unresolved, snapshot_stage).
        m = _adequate_manifest(
            packages={
                "mode": "imported-only",
                "records": [{"name": "my-pkg", "version": "0.1.0", "editable": True}],
                "unresolved": [{"module": "local_helper", "reason": "unmapped"}],
                "snapshot_stage": "startup",
                "capture_state": {"status": "complete"},
            }
        )
        res = assess_manifest_reproducibility(m, current_hostname="compute-01")
        assert _find_by_code(res, "packages_imported_only_scope")["severity"] == "info"
        f_ed = _find_by_code(res, "packages_editable_present")
        assert f_ed["severity"] == "info"
        assert f_ed["impact"] == "portability"
        assert _find_by_code(res, "packages_unresolved_modules")["evidence_status"] == "unavailable"
        assert _find_by_code(res, "packages_startup_snapshot")["severity"] == "info"

        # Empty complete packages -> info (does not fail --strict).
        m_empty = _adequate_manifest(
            packages={"mode": "imported-only", "records": [], "capture_state": {"status": "complete"}}
        )
        assert _find_by_code(assess_manifest_reproducibility(m_empty), "packages_empty")["severity"] == "info"

        # Partial and failed -> warn / material / unavailable.
        m_partial = _adequate_manifest(packages={"capture_state": {"status": "partial"}})
        f_part = _find_by_code(assess_manifest_reproducibility(m_partial), "packages_partial")
        assert f_part["severity"] == "warn"
        assert f_part["impact"] == "material"
        assert f_part["evidence_status"] == "unavailable"

        m_fail = _adequate_manifest(packages={"capture_state": {"status": "failed"}})
        f_fail = _find_by_code(assess_manifest_reproducibility(m_fail), "packages_failed")
        assert f_fail["severity"] == "warn"
        assert f_fail["impact"] == "material"

        # Suppressed -> packages_off (info).
        m_off = _adequate_manifest(packages={"capture_state": {"status": "suppressed"}})
        assert _find_by_code(assess_manifest_reproducibility(m_off), "packages_off")["severity"] == "info"

    def test_inputs_outputs_observed_asserted_inferred_stat_only_and_hash_anomalies(self):
        # 1. No data_files and no invocation.inputs -> no_file_provenance.
        m_none = _adequate_manifest(data_files={"inputs": [], "outputs": [], "mixed": []})
        f_none = _find_by_code(assess_manifest_reproducibility(m_none), "no_file_provenance")
        assert f_none["severity"] == "info"
        assert f_none["evidence_status"] == "not_checked"
        assert "pubrun.open" in (f_none["suggestion"] or "")
        assert "open()" in f_none["message"]

        # 2. Only argv-inferred inputs -> inferred + unhashed info findings.
        m_inf = _adequate_manifest(data_files={"inputs": [], "outputs": []})
        m_inf["invocation"]["inputs"] = [
            {"arg_index": 1, "path": "train.csv", "real_path": "/work/train.csv", "is_dir": False, "size": 100}
        ]
        res_inf = assess_manifest_reproducibility(m_inf)
        f_inf = _find_by_code(res_inf, "inputs_argv_inferred_only")
        assert f_inf["severity"] == "info"
        assert f_inf["evidence_status"] == "inferred"
        assert _find_by_code(res_inf, "inputs_unhashed")["evidence_status"] == "not_checked"
        assert _category_map(res_inf)["inputs_outputs"]["evidence_status"] == "inferred"

        # 3. Stat-only data_files -> file_provenance_unhashed (not_checked).
        m_stat = _adequate_manifest(
            data_files={"inputs": [{"path": "a.csv", "size_bytes": 10, "sha256": None}], "outputs": []}
        )
        f_stat = _find_by_code(assess_manifest_reproducibility(m_stat), "file_provenance_unhashed")
        assert f_stat["severity"] == "info"
        assert f_stat["evidence_status"] == "not_checked"

        # 4. Asserted caller digest -> file_provenance_asserted_only (asserted).
        m_asserted = _adequate_manifest(
            data_files={
                "inputs": [
                    {
                        "path": "ext.parquet",
                        "evidence_source": "asserted",
                        "caller_digest": {"algorithm": "sha256", "value": "d" * 64},
                        "hash_status": "asserted",
                    }
                ],
                "outputs": [],
            }
        )
        res_asrt = assess_manifest_reproducibility(m_asserted)
        f_asrt = _find_by_code(res_asrt, "file_provenance_asserted_only")
        assert f_asrt["severity"] == "info"
        assert f_asrt["evidence_status"] == "asserted"
        assert _category_map(res_asrt)["inputs_outputs"]["evidence_status"] == "asserted"

        # 5. hash_status anomalies including data_files.mixed.
        m_anom = _adequate_manifest(
            data_files={
                "inputs": [{"path": "x.bin", "hash_status": "file_changed"}],
                "outputs": [{"path": "y.bin", "hash_status": "over_budget"}],
                "mixed": [{"path": "z.bin", "hash_status": "failed"}],
            }
        )
        res_anom = assess_manifest_reproducibility(m_anom)
        assert _find_by_code(res_anom, "file_hash_changed")["severity"] == "warn"
        assert _find_by_code(res_anom, "file_hash_over_budget")["severity"] == "info"
        assert _find_by_code(res_anom, "file_hash_unavailable")["severity"] == "warn"

    def test_capture_completeness_outcomes_section_states_errors_and_determinism(self):
        m = _adequate_manifest(
            status={"outcome": "failed", "exit_code": 1, "capture_state": {"status": "complete"}},
            environment={"variables": [], "capture_state": {"status": "partial", "detail": "truncated"}},
            process={"pid": 1, "capture_state": {"status": "pending"}},
            errors={
                "records": [{"kind": "capture-error", "type": "OSError", "message": "probe failed"}],
                "capture_state": {"status": "complete"},
            },
            determinism={"registered_seeds": [], "capture_state": {"status": "complete"}},
        )
        res = assess_manifest_reproducibility(m, current_hostname="compute-01")
        assert _find_by_code(res, "run_outcome_incomplete")["severity"] == "warn"
        assert _find_by_code(res, "environment_capture_partial")["severity"] == "warn"
        assert _find_by_code(res, "process_capture_pending")["severity"] == "info"
        assert _find_by_code(res, "capture_errors_recorded")["severity"] == "warn"
        f_det = _find_by_code(res, "determinism_seeds_not_recorded")
        assert f_det["severity"] == "info"
        assert f_det["evidence_status"] == "not_checked"

    def test_invocation_redacted_argv_and_both_env_redaction_forms(self):
        m = _adequate_manifest()
        m["invocation"]["argv"] = ["train.py", "--token", "[REDACTED]"]
        m["invocation"]["rerun_command"] = "cd /work && python train.py --token [REDACTED]"
        m["environment"]["variables"] = [
            {"name": "API_KEY", "value": {"representation": "redacted"}},
            {"name": "DB_SECRET", "value": {"representation": "hashed", "hash_value": "abc"}},
            {
                "name": "CONN_URI",
                "value": {
                    "representation": "plain",
                    "value": "postgres://user:[REDACTED]@db.example/app",
                },
            },
            {"name": "SAFE_VAR", "value": {"representation": "plain", "value": "hello"}},
        ]
        res = assess_manifest_reproducibility(m, current_hostname="compute-01")

        f_cmd = _find_by_code(res, "rerun_command_redacted")
        assert f_cmd["severity"] == "warn"
        assert f_cmd["impact"] == "material"
        assert f_cmd["evidence_status"] == "observed"
        assert "not directly executable" in f_cmd["message"].lower()

        f_env = _find_by_code(res, "env_vars_redacted")
        assert f_env["severity"] == "info"
        assert f_env["evidence_status"] == "observed"
        assert set(f_env["details"]["variables"]) == {"API_KEY", "DB_SECRET", "CONN_URI"}

    def test_parent_metadata_hydrated_stale_postdated_mismatched_and_unavailable(self, tmp_path: Path):
        # 1. Valid fresh hydrated parent.
        fresh_report = HydrationReport(
            meta_ref="meta.json",
            resolved_path=str(tmp_path / "meta.json"),
            status="hydrated",
            inherited_sections=["hardware", "packages"],
            direct_sections=["python", "git"],
            parent_started_at_utc=1000.0,
            child_started_at_utc=1100.0,
            age_seconds=100.0,
            script_modified_after_parent=False,
            identity_mismatches=[],
        )
        res_fresh = assess_manifest_reproducibility(
            _adequate_manifest(meta_ref="meta.json"),
            hydration_report=fresh_report,
            current_hostname="compute-01",
        )
        f_inh = _find_by_code(res_fresh, "parent_metadata_inherited")
        assert f_inh["severity"] == "info"
        assert f_inh["evidence_status"] == "inherited"
        assert "mtime" in f_inh["message"].lower()
        assert _category_map(res_fresh)["parent_metadata"]["status"] == "adequate"
        assert _category_map(res_fresh)["parent_metadata"]["evidence_status"] == "inherited"

        # 2. Stale parent (> threshold) -> info without breaking --strict.
        stale_report = HydrationReport(
            meta_ref="meta.json",
            status="hydrated",
            inherited_sections=["packages"],
            direct_sections=["python"],
            age_seconds=100000.0,
            script_modified_after_parent=False,
        )
        res_stale = assess_manifest_reproducibility(
            _adequate_manifest(meta_ref="meta.json"),
            hydration_report=stale_report,
            stale_parent_seconds=3600.0,
            current_hostname="compute-01",
        )
        f_stale = _find_by_code(res_stale, "parent_metadata_stale")
        assert f_stale["severity"] == "info"
        assert f_stale["evidence_status"] == "inherited"
        assert _category_map(res_stale)["parent_metadata"]["status"] == "uncertain"

        # 3. Post-dated + drifted + mismatched parent -> warn / material.
        bad_report = HydrationReport(
            meta_ref="meta.json",
            status="hydrated",
            inherited_sections=["hardware"],
            direct_sections=["python", "git"],
            age_seconds=-50.0,
            script_modified_after_parent=True,
            identity_mismatches=[{"field": "python.version", "parent": "3.10.0", "child": "3.11.8"}],
        )
        res_bad = assess_manifest_reproducibility(
            _adequate_manifest(meta_ref="meta.json"),
            hydration_report=bad_report,
            current_hostname="compute-01",
        )
        assert _find_by_code(res_bad, "parent_metadata_postdated")["severity"] == "warn"
        assert _find_by_code(res_bad, "parent_metadata_script_drift")["severity"] == "warn"
        f_mm = _find_by_code(res_bad, "parent_metadata_identity_mismatch")
        assert f_mm["severity"] == "warn"
        assert f_mm["comparison"] == "mismatch"
        assert _category_map(res_bad)["parent_metadata"]["status"] == "mismatch"

        # 4. Missing / policy-blocked / invalid snapshots -> warn / unavailable.
        for bad_status in ("missing", "blocked_by_policy", "invalid_extension", "invalid_json", "invalid_type", "failed"):
            rep = HydrationReport(
                meta_ref="meta.json",
                status=bad_status,
                warnings=[f"problem: {bad_status}"],
            )
            res_u = assess_manifest_reproducibility(
                _adequate_manifest(meta_ref="meta.json"),
                hydration_report=rep,
                current_hostname="compute-01",
            )
            f_u = _find_by_code(res_u, f"parent_metadata_{bad_status}")
            assert f_u["severity"] == "warn"
            assert f_u["impact"] == "material"
            assert f_u["evidence_status"] == "unavailable"
            assert _category_map(res_u)["parent_metadata"]["status"] == "gaps"

        # 5. Raw meta_ref without HydrationReport -> not_checked.
        res_raw = assess_manifest_reproducibility(
            _adequate_manifest(meta_ref="meta.json"),
            current_hostname="compute-01",
        )
        f_raw = _find_by_code(res_raw, "parent_metadata_not_hydrated")
        assert f_raw["severity"] == "info"
        assert f_raw["evidence_status"] == "not_checked"
        assert _category_map(res_raw)["parent_metadata"]["status"] == "not_checked"

    def test_next_action_prioritization_unavailable_before_material_before_info(self):
        # Combine unavailable broken evidence (git_timeout), material gap (git_dirty / redacted cmd),
        # and informational gap (no_file_provenance).
        m = _adequate_manifest(
            git={"capture_state": {"status": "timeout", "detail": "timed out"}},
            data_files={"inputs": [], "outputs": []},
        )
        m["invocation"]["rerun_command"] = "cd /work && python train.py --key [REDACTED]"
        res = assess_manifest_reproducibility(m, current_hostname="compute-01")

        # Unavailable evidence (git_timeout) must outrank material gap (rerun_command_redacted),
        # which must outrank informational suggestion (no_file_provenance).
        assert res["next_action"] == res["next_actions"][0]
        assert "timeout" in res["next_action"].lower()
        assert len(res["next_actions"]) == len(set(res["next_actions"]))
        cmd_sugg = _find_by_code(res, "rerun_command_redacted")["suggestion"]
        file_sugg = _find_by_code(res, "no_file_provenance")["suggestion"]
        assert res["next_actions"].index(cmd_sugg) < res["next_actions"].index(file_sugg)

    def test_assess_run_and_checks_integration(self):
        m = _adequate_manifest()
        m["git"]["dirty"] = True
        direct = assess_manifest_reproducibility(m, current_hostname="login-01")
        via_facade = assess_run(m, current_hostname="login-01")
        via_checks = checks.assess_run(m, current_hostname="login-01")
        assert via_facade == direct
        assert via_checks == direct
        assert checks.manifest_findings(m, current_hostname="login-01") == direct["findings"]


class TestReproducibilityFormattersAndIsolation:
    """Tests for plain-text formatters, NO_COLOR/DIM safety, and import isolation."""

    def test_format_summary_and_detail_plain_and_no_color_and_no_dim(self, monkeypatch):
        m = _adequate_manifest(meta_ref="meta.json")
        m["git"]["dirty"] = True
        rep = HydrationReport(
            meta_ref="meta.json",
            status="hydrated",
            inherited_sections=["hardware", "packages"],
            direct_sections=["python", "git"],
            age_seconds=30.0,
            script_modified_after_parent=False,
        )
        assessment = assess_run(m, hydration_report=rep, current_hostname="compute-01")

        summary_txt = format_reproducibility_summary(assessment)
        assert "\033[" not in summary_txt
        assert "Next step:" in summary_txt
        assert NON_GUARANTEE_DISCLAIMER in summary_txt
        assert "hardware, packages" in summary_txt

        # use_color=False -> zero ANSI escapes, includes categories and -> suggestions.
        detail_plain = format_reproducibility_detail(assessment, use_color=False)
        assert "\033[" not in detail_plain
        assert "Evidence categories:" in detail_plain
        assert "[GAPS" in detail_plain
        assert "[WARN ]" in detail_plain
        assert "git_dirty_unrecorded" in detail_plain
        assert "->" in detail_plain
        assert NON_GUARANTEE_DISCLAIMER in detail_plain

        # NO_COLOR=1 suppresses ANSI escapes even if use_color=True.
        monkeypatch.setenv("NO_COLOR", "1")
        detail_no_color = format_reproducibility_detail(assessment, use_color=True)
        assert "\033[" not in detail_no_color

        # With NO_COLOR unset and use_color=True, color may appear but ANSI DIM (\033[2m) never does.
        monkeypatch.delenv("NO_COLOR", raising=False)
        detail_color = format_reproducibility_detail(assessment, use_color=True)
        assert "\033[" in detail_color
        assert "\033[2m" not in detail_color

    def test_import_pubrun_does_not_import_reproducibility_or_checks(self):
        code = (
            "import pubrun, sys; "
            "assert 'pubrun.report.checks' not in sys.modules; "
            "assert 'pubrun.report.reproducibility' not in sys.modules; "
            "print('ISOLATED')"
        )
        res = subprocess.run(
            [sys.executable, "-c", code],
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert res.returncode == 0, res.stderr
        assert res.stdout.strip() == "ISOLATED"
