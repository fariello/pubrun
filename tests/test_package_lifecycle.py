"""Lifecycle, merge, schema, and consumer integration tests for package capture (IPD ijipnx)."""
from __future__ import annotations

import asyncio
import copy
import importlib
import json
import os
from pathlib import Path
import subprocess
import sys
from typing import Any, Dict, Iterable, List, Optional

import pytest

import pubrun.capture.packages as pkgs
import pubrun.tracker as tracker_mod

_REPO_ROOT = Path(__file__).resolve().parents[1]
_SCHEMA_PATH = _REPO_ROOT / "schemas" / "manifest.schema.json"


@pytest.fixture(autouse=True)
def _clean_cache_and_run_state():
    """Keep distribution cache and global active-run state isolated across tests."""
    pkgs.invalidate_package_cache()
    prev_run = tracker_mod._active_run
    tracker_mod._active_run = None
    try:
        yield
    finally:
        cur = tracker_mod._active_run
        if cur is not None:
            try:
                cur.stop()
            except Exception:
                pass
        tracker_mod._active_run = prev_run
        pkgs.invalidate_package_cache()


def _validate_manifest(manifest: Dict[str, Any]) -> None:
    """Validate a full manifest against schemas/manifest.schema.json if jsonschema is available."""
    jsonschema = pytest.importorskip("jsonschema")
    schema = json.loads(_SCHEMA_PATH.read_text(encoding="utf-8"))
    jsonschema.validate(manifest, schema)


def _validate_packages_section(section: Dict[str, Any]) -> None:
    """Validate a packages section dict against $defs.packages_section."""
    jsonschema = pytest.importorskip("jsonschema")
    schema = json.loads(_SCHEMA_PATH.read_text(encoding="utf-8"))
    defs = schema["$defs"]
    sub = dict(defs["packages_section"])
    sub["$defs"] = defs
    jsonschema.validate(section, sub)


def _write_dist(
    base_dir: Path,
    dist_name: str,
    version: str = "1.0.0",
    *,
    top_levels: Optional[Iterable[str]] = None,
    files: Optional[Dict[str, str]] = None,
    requires: Optional[Iterable[str]] = None,
) -> Path:
    """Create a PEP 376 ``.dist-info`` fixture and module files under ``base_dir``."""
    base_dir.mkdir(parents=True, exist_ok=True)
    dist_dir_name = f"{dist_name.replace('-', '_')}-{version}.dist-info"
    dist_dir = base_dir / dist_dir_name
    dist_dir.mkdir(parents=True, exist_ok=True)

    meta_lines = [
        "Metadata-Version: 2.1",
        f"Name: {dist_name}",
        f"Version: {version}",
    ]
    for req in requires or ():
        meta_lines.append(f"Requires-Dist: {req}")
    (dist_dir / "METADATA").write_text("\n".join(meta_lines) + "\n", encoding="utf-8")

    records: List[str] = [f"{dist_dir_name}/METADATA,,"]
    if top_levels is not None:
        top_text = "\n".join(top_levels) + ("\n" if top_levels else "")
        (dist_dir / "top_level.txt").write_text(top_text, encoding="utf-8")
        records.append(f"{dist_dir_name}/top_level.txt,,")

    for rel_path, content in (files or {}).items():
        full_path = base_dir / rel_path
        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.write_text(content, encoding="utf-8")
        records.append(f"{rel_path},,")

    records.append(f"{dist_dir_name}/RECORD,,")
    (dist_dir / "RECORD").write_text("\n".join(records) + "\n", encoding="utf-8")
    return dist_dir


def _import_tracked(monkeypatch: pytest.MonkeyPatch, module_name: str):
    """Import ``module_name`` and ensure automatic cleanup from ``sys.modules``."""
    before = set(sys.modules.keys())
    importlib.invalidate_caches()
    mod = importlib.import_module(module_name)
    added = {k: sys.modules[k] for k in (set(sys.modules.keys()) - before)}
    for k in added:
        sys.modules.pop(k, None)
    for k, v in added.items():
        monkeypatch.setitem(sys.modules, k, v)
    return mod


def _find_record(section: Dict[str, Any], name: str) -> Optional[Dict[str, Any]]:
    """Return the package record matching ``name`` under PEP 503 normalization."""
    target = pkgs.normalize_package_name(name)
    for rec in section.get("records") or []:
        if pkgs.normalize_package_name(rec.get("name") or "") == target:
            return rec
    return None


def _fast_overrides(tmp_path: Path, **extra: Any) -> Dict[str, Any]:
    """Minimal fast Run overrides disabling unrelated heavy capture hooks."""
    base: Dict[str, Any] = {
        "core": {"output_dir": str(tmp_path / "runs")},
        "console": {"capture_mode": "off"},
        "events": {"enabled": False},
        "capture": {
            "hardware": {"depth": "off"},
            "subprocesses": {"enabled": False},
            "resources": {"depth": "off"},
            "signals": {"enabled": False},
        },
    }
    for key, val in extra.items():
        if key == "capture" and isinstance(val, dict):
            base["capture"].update(val)
        else:
            base[key] = val
    return base


# ---------------------------------------------------------------------------
# V-02: Stage-aware get_packages(), merge_package_snapshots(), mode switches
# ---------------------------------------------------------------------------


def test_stage_get_packages_emits_extended_schema_fields(tmp_path, monkeypatch):
    """get_packages() emits additive schema fields cleanly across all stages and modes."""
    site_dir = tmp_path / "site_stage"
    _write_dist(
        site_dir,
        "synth-stage-dist",
        "1.4.0",
        top_levels=["synth_stage_mod"],
        files={"synth_stage_mod/__init__.py": "V = 1\n"},
    )
    monkeypatch.syspath_prepend(str(site_dir))
    _import_tracked(monkeypatch, "synth_stage_mod")

    cfg_imp = {"capture": {"packages": {"mode": "imported-only"}}}

    snap_startup = pkgs.get_packages(cfg_imp, stage="startup")
    assert snap_startup["snapshot_stage"] == "startup"
    assert snap_startup["coverage_notes"] == []
    rec_s = _find_record(snap_startup, "synth-stage-dist")
    assert rec_s is not None
    assert rec_s["observed_at"] == "startup"
    assert rec_s["import_names"] == ["synth_stage_mod"]
    _validate_packages_section(snap_startup)

    snap_final = pkgs.get_packages(cfg_imp, stage="final")
    assert snap_final["snapshot_stage"] == "final"
    assert snap_final["coverage_notes"]
    assert "global import hook" in snap_final["coverage_notes"][0]
    rec_f = _find_record(snap_final, "synth-stage-dist")
    assert rec_f is not None
    assert rec_f["observed_at"] == "final"
    assert rec_f["import_names"] == ["synth_stage_mod"]
    _validate_packages_section(snap_final)

    snap_single = pkgs.get_packages(cfg_imp)
    assert snap_single["snapshot_stage"] == "single"
    assert snap_single["coverage_notes"] == []
    rec_one = _find_record(snap_single, "synth-stage-dist")
    assert rec_one is not None
    assert rec_one["observed_at"] is None
    assert rec_one["import_names"] == ["synth_stage_mod"]
    _validate_packages_section(snap_single)

    for non_imp_mode in ("top-level-installed", "full-environment"):
        snap_env = pkgs.get_packages(
            {"capture": {"packages": {"mode": non_imp_mode}}}, stage="final"
        )
        assert snap_env["snapshot_stage"] == "final"
        assert snap_env["coverage_notes"] == []
        rec_env = _find_record(snap_env, "synth-stage-dist")
        assert rec_env is not None
        assert rec_env["observed_at"] is None
        assert rec_env["import_names"] is None
        _validate_packages_section(snap_env)


def test_merge_retains_removed_startup_module_and_no_input_mutation(tmp_path, monkeypatch):
    """Startup-only removed modules stay retained with observed_at='startup', persistent
    modules union import_names with observed_at='startup_and_final', late imports get
    observed_at='final', version changes warn/degrade, and inputs are never mutated."""
    startup_snap = {
        "mode": "imported-only",
        "snapshot_stage": "startup",
        "records": [
            {
                "name": "removed-dist",
                "version": "1.0.0",
                "location": "/site",
                "editable": False,
                "source": "imported",
                "import_names": ["removed_mod"],
                "observed_at": "startup",
            },
            {
                "name": "persist-dist",
                "version": "1.0.0",
                "location": "/site",
                "editable": False,
                "source": "imported",
                "import_names": ["persist_a"],
                "observed_at": "startup",
            },
        ],
        "unresolved": [
            {
                "module": "ambig_mod",
                "reason": "ambiguous",
                "candidates": ["cand-a"],
                "observed_at": "startup",
                "detail": "startup ambiguous",
            }
        ],
        "local_modules": ["local_start"],
        "coverage_notes": [],
        "capture_state": {"status": "partial", "warnings": ["ambig_mod (ambiguous): startup ambiguous"]},
    }
    final_snap = {
        "mode": "imported-only",
        "snapshot_stage": "final",
        "records": [
            {
                "name": "persist-dist",
                "version": "2.0.0",
                "location": "/site",
                "editable": False,
                "source": "imported",
                "import_names": ["persist_b"],
                "observed_at": "final",
            },
            {
                "name": "late-dist",
                "version": "3.1.0",
                "location": "/site",
                "editable": False,
                "source": "imported",
                "import_names": ["late_mod"],
                "observed_at": "final",
            },
        ],
        "unresolved": [
            {
                "module": "ambig_mod",
                "reason": "ambiguous",
                "candidates": ["cand-b"],
                "observed_at": "final",
                "detail": "final ambiguous",
            }
        ],
        "local_modules": ["local_end"],
        "coverage_notes": [],
        "capture_state": {"status": "partial", "warnings": ["ambig_mod (ambiguous): final ambiguous"]},
    }

    startup_before = copy.deepcopy(startup_snap)
    final_before = copy.deepcopy(final_snap)

    merged = pkgs.merge_package_snapshots(
        startup_snap,
        final_snap,
        config={"capture": {"packages": {"mode": "imported-only"}}},
    )

    # Inputs were not mutated in place.
    assert startup_snap == startup_before
    assert final_snap == final_before
    _validate_packages_section(merged)

    assert merged["snapshot_stage"] == "final"
    assert merged["local_modules"] == ["local_end", "local_start"]
    assert merged["capture_state"]["status"] == "partial"
    assert any("version changed" in w for w in merged["capture_state"].get("warnings", []))

    rec_removed = _find_record(merged, "removed-dist")
    assert rec_removed is not None
    assert rec_removed["observed_at"] == "startup"
    assert rec_removed["import_names"] == ["removed_mod"]

    rec_persist = _find_record(merged, "persist-dist")
    assert rec_persist is not None
    assert rec_persist["observed_at"] == "startup_and_final"
    assert rec_persist["version"] == "2.0.0"
    assert rec_persist["import_names"] == ["persist_a", "persist_b"]

    rec_late = _find_record(merged, "late-dist")
    assert rec_late is not None
    assert rec_late["observed_at"] == "final"
    assert rec_late["import_names"] == ["late_mod"]

    assert len(merged["unresolved"]) == 1
    u = merged["unresolved"][0]
    assert u["module"] == "ambig_mod"
    assert u["reason"] == "ambiguous"
    assert u["candidates"] == ["cand-a", "cand-b"]
    assert u["observed_at"] == "startup_and_final"

    # End-to-end Run check: module imported before start(), then removed via del sys.modules.
    site_dir = tmp_path / "site_removed_e2e"
    _write_dist(
        site_dir,
        "synth-e2e-removed",
        "1.0.0",
        top_levels=["synth_e2e_removed"],
        files={"synth_e2e_removed/__init__.py": "X = 1\n"},
    )
    _write_dist(
        site_dir,
        "synth-e2e-persist",
        "1.0.0",
        top_levels=["synth_e2e_persist"],
        files={"synth_e2e_persist/__init__.py": "Y = 2\n"},
    )
    monkeypatch.syspath_prepend(str(site_dir))
    _import_tracked(monkeypatch, "synth_e2e_removed")
    _import_tracked(monkeypatch, "synth_e2e_persist")

    run = tracker_mod.Run(overrides=_fast_overrides(tmp_path))
    sys.modules.pop("synth_e2e_removed", None)
    run.stop()

    manifest = json.loads((run.run_dir / "manifest.json").read_text(encoding="utf-8"))
    _validate_manifest(manifest)
    rem = _find_record(manifest["packages"], "synth-e2e-removed")
    per = _find_record(manifest["packages"], "synth-e2e-persist")
    assert rem is not None and rem["observed_at"] == "startup"
    assert per is not None and per["observed_at"] == "startup_and_final"


def test_merge_transitive_closure_once_and_unresolved_dedup(tmp_path, monkeypatch):
    """In imported-transitive mode, both startup-only removed modules and late-imported
    modules resolve transitive dependencies once without duplicating transitive unresolved
    entries."""
    site_dir = tmp_path / "site_trans_lifecycle"
    _write_dist(
        site_dir,
        "synth-start-root",
        "1.0.0",
        top_levels=["synth_start_root"],
        files={"synth_start_root/__init__.py": "A = 1\n"},
        requires=["synth-start-dep>=1.0", "synth-shared-missing>=1.0"],
    )
    _write_dist(
        site_dir,
        "synth-start-dep",
        "1.1.0",
        files={"synth_start_dep/__init__.py": "B = 2\n"},
    )
    _write_dist(
        site_dir,
        "synth-late-root",
        "2.0.0",
        top_levels=["synth_late_root"],
        files={"synth_late_root/__init__.py": "C = 3\n"},
        requires=["synth-late-dep>=2.0", "synth-shared-missing>=1.0"],
    )
    _write_dist(
        site_dir,
        "synth-late-dep",
        "2.1.0",
        files={"synth_late_dep/__init__.py": "D = 4\n"},
    )
    monkeypatch.syspath_prepend(str(site_dir))
    _import_tracked(monkeypatch, "synth_start_root")

    # Track calls to _resolve_transitive_closure during finalization (must run once).
    orig_resolve_trans = pkgs._resolve_transitive_closure
    trans_calls = 0

    def counting_resolve_trans(*args, **kwargs):
        nonlocal trans_calls
        trans_calls += 1
        return orig_resolve_trans(*args, **kwargs)

    monkeypatch.setattr(pkgs, "_resolve_transitive_closure", counting_resolve_trans)

    run = tracker_mod.Run(
        overrides=_fast_overrides(
            tmp_path,
            capture={"packages": {"mode": "imported-transitive"}},
        )
    )
    assert trans_calls == 1  # Startup snapshot computed transitive closure once.

    # Delete startup module and late-import another distribution before finalization.
    sys.modules.pop("synth_start_root", None)
    _import_tracked(monkeypatch, "synth_late_root")

    trans_calls_before_stop = trans_calls
    run.stop()
    assert trans_calls - trans_calls_before_stop == 1  # Finalization recomputed closure ONCE.

    manifest = json.loads((run.run_dir / "manifest.json").read_text(encoding="utf-8"))
    _validate_manifest(manifest)

    pkg_sec = manifest["packages"]
    assert pkg_sec["mode"] == "imported-transitive"
    assert pkg_sec["snapshot_stage"] == "final"
    assert pkg_sec["capture_state"]["status"] == "partial"

    start_root = _find_record(pkg_sec, "synth-start-root")
    late_root = _find_record(pkg_sec, "synth-late-root")
    start_dep = _find_record(pkg_sec, "synth-start-dep")
    late_dep = _find_record(pkg_sec, "synth-late-dep")

    assert start_root is not None and start_root["observed_at"] == "startup"
    assert late_root is not None and late_root["observed_at"] == "final"
    assert start_dep is not None
    assert start_dep["source"] == "transitive"
    assert start_dep["required_by"] == ["synth-start-root"]
    assert start_dep["import_names"] is None
    assert start_dep["observed_at"] is None
    assert late_dep is not None
    assert late_dep["source"] == "transitive"
    assert late_dep["required_by"] == ["synth-late-root"]
    assert late_dep["import_names"] is None
    assert late_dep["observed_at"] is None

    # Transitive unresolved entries from startup were not duplicated at finalization.
    missing_for_start = [
        u
        for u in pkg_sec["unresolved"]
        if u["module"] == "synth-shared-missing"
        and "synth-start-root" in (u.get("detail") or "")
    ]
    missing_for_late = [
        u
        for u in pkg_sec["unresolved"]
        if u["module"] == "synth-shared-missing"
        and "synth-late-root" in (u.get("detail") or "")
    ]
    assert len(missing_for_start) == 1
    assert missing_for_start[0]["observed_at"] == "final"
    assert len(missing_for_late) == 1
    assert missing_for_late[0]["observed_at"] == "final"


def test_mode_switch_mid_run_and_suppressed_startup_merge(tmp_path, monkeypatch):
    """Mid-run config switches (off <-> imported-only, full-environment -> imported-only,
    imported-only -> full-environment) produce honest, schema-valid final manifests."""
    site_dir = tmp_path / "site_switch"
    _write_dist(
        site_dir,
        "synth-switch-late",
        "1.2.0",
        top_levels=["synth_switch_late"],
        files={"synth_switch_late/__init__.py": "S = 1\n"},
    )
    monkeypatch.syspath_prepend(str(site_dir))

    # 1. off -> imported-only via _merge_and_migrate()
    run1 = tracker_mod.Run(
        overrides=_fast_overrides(tmp_path / "r1", capture={"packages": {"mode": "off"}})
    )
    startup_m1 = json.loads((run1.run_dir / "manifest.json").read_text(encoding="utf-8"))
    assert startup_m1["packages"] == {"capture_state": {"status": "suppressed"}}
    assert "mode" not in startup_m1["packages"]

    _import_tracked(monkeypatch, "synth_switch_late")
    run1._merge_and_migrate({"capture": {"packages": {"mode": "imported-only"}}})
    run1.stop()

    final_m1 = json.loads((run1.run_dir / "manifest.json").read_text(encoding="utf-8"))
    _validate_manifest(final_m1)
    assert final_m1["packages"]["mode"] == "imported-only"
    assert final_m1["packages"]["snapshot_stage"] == "final"
    assert final_m1["packages"]["capture_state"]["status"] == "complete"
    rec1 = _find_record(final_m1["packages"], "synth-switch-late")
    assert rec1 is not None and rec1["observed_at"] == "final"

    # 2. imported-only -> off via _merge_and_migrate()
    run2 = tracker_mod.Run(
        overrides=_fast_overrides(
            tmp_path / "r2", capture={"packages": {"mode": "imported-only"}}
        )
    )
    run2._merge_and_migrate({"capture": {"packages": {"mode": "off"}}})
    run2.stop()

    final_m2 = json.loads((run2.run_dir / "manifest.json").read_text(encoding="utf-8"))
    _validate_manifest(final_m2)
    assert final_m2["packages"] == {"capture_state": {"status": "suppressed"}}
    assert "mode" not in final_m2["packages"]

    # 3. full-environment startup -> imported-only final must not leak non-imported records.
    full_startup = {
        "mode": "full-environment",
        "snapshot_stage": "startup",
        "records": [
            {
                "name": "unimported-env-pkg",
                "version": "9.9.9",
                "location": "/site",
                "editable": False,
                "import_names": None,
                "observed_at": None,
            }
        ],
        "unresolved": [],
        "local_modules": [],
        "coverage_notes": [],
        "capture_state": {"status": "complete"},
    }
    imp_final = {
        "mode": "imported-only",
        "snapshot_stage": "final",
        "records": [
            {
                "name": "actual-imported-pkg",
                "version": "1.0.0",
                "location": "/site",
                "editable": False,
                "source": "imported",
                "import_names": ["actual_imported"],
                "observed_at": "final",
            }
        ],
        "unresolved": [],
        "local_modules": [],
        "coverage_notes": [],
        "capture_state": {"status": "complete"},
    }
    switched = pkgs.merge_package_snapshots(
        full_startup,
        imp_final,
        config={"capture": {"packages": {"mode": "imported-only"}}},
    )
    _validate_packages_section(switched)
    assert switched["mode"] == "imported-only"
    assert _find_record(switched, "unimported-env-pkg") is None
    assert _find_record(switched, "actual-imported-pkg") is not None

    # 4. imported-only startup -> full-environment final keeps non-import records clean.
    to_full = pkgs.merge_package_snapshots(
        imp_final,
        full_startup,
        config={"capture": {"packages": {"mode": "full-environment"}}},
    )
    _validate_packages_section(to_full)
    assert to_full["mode"] == "full-environment"
    assert to_full["snapshot_stage"] == "final"
    env_rec = _find_record(to_full, "unimported-env-pkg")
    assert env_rec is not None
    assert env_rec["observed_at"] is None
    assert env_rec["import_names"] is None


# ---------------------------------------------------------------------------
# V-03: Tracker lifecycle, late imports, startup truthfulness, error resilience
# ---------------------------------------------------------------------------


def test_one_import_late_import_and_methods_highlight_subprocess(tmp_path):
    """A fresh script placing `import pubrun` on line 1 records late imports with
    mismatched import/distribution names in manifest.json and highlights them in methods.md."""
    site_dir = tmp_path / "site_subproc"
    _write_dist(
        site_dir,
        "scikit-learn",
        "9.8.7",
        top_levels=["sklearn"],
        files={"sklearn/__init__.py": "VERSION = '9.8.7'\n"},
    )
    _write_dist(
        site_dir,
        "synth-late-dist",
        "2.3.4",
        top_levels=["synth_late_mod"],
        files={"synth_late_mod/__init__.py": "READY = True\n"},
    )

    script_path = tmp_path / "analysis.py"
    script_path.write_text(
        "import pubrun\n"
        "import sklearn\n"
        "import synth_late_mod\n"
        "assert sklearn.VERSION == '9.8.7'\n"
        "assert synth_late_mod.READY is True\n",
        encoding="utf-8",
    )

    env = os.environ.copy()
    existing_py = env.get("PYTHONPATH", "")
    py_parts = [str(site_dir), str(_REPO_ROOT / "src")]
    if existing_py:
        py_parts.append(existing_py)
    env["PYTHONPATH"] = os.pathsep.join(py_parts)
    env.pop("PUBRUN_AUTO_START", None)

    proc = subprocess.run(
        [sys.executable, str(script_path)],
        cwd=str(tmp_path),
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert proc.returncode == 0, f"stderr={proc.stderr}\nstdout={proc.stdout}"

    runs_dir = tmp_path / "runs"
    run_dirs = [p for p in runs_dir.iterdir() if p.is_dir()]
    assert len(run_dirs) == 1
    run_dir = run_dirs[0]

    manifest = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
    _validate_manifest(manifest)

    pkg_sec = manifest["packages"]
    assert pkg_sec["snapshot_stage"] == "final"

    skl = _find_record(pkg_sec, "scikit-learn")
    assert skl is not None
    assert skl["version"] == "9.8.7"
    assert skl["source"] == "imported"
    assert skl["observed_at"] == "final"
    assert skl["import_names"] == ["sklearn"]

    late = _find_record(pkg_sec, "synth-late-dist")
    assert late is not None
    assert late["version"] == "2.3.4"
    assert late["observed_at"] == "final"
    assert late["import_names"] == ["synth_late_mod"]

    methods_md = (run_dir / "methods.md").read_text(encoding="utf-8")
    assert "scikit-learn (v9.8.7)" in methods_md


def test_startup_truthful_before_stop_and_final_after_stop(tmp_path, monkeypatch):
    """Startup manifest on disk is truthful (snapshot_stage='startup', excludes not-yet-imported
    libraries) while finalized manifest includes late imports with snapshot_stage='final'."""
    site_dir = tmp_path / "site_truthful"
    _write_dist(
        site_dir,
        "synth-pre-dist",
        "1.0.0",
        top_levels=["synth_pre_mod"],
        files={"synth_pre_mod/__init__.py": "PRE = True\n"},
    )
    _write_dist(
        site_dir,
        "synth-post-dist",
        "2.0.0",
        top_levels=["synth_post_mod"],
        files={"synth_post_mod/__init__.py": "POST = True\n"},
    )
    monkeypatch.syspath_prepend(str(site_dir))
    _import_tracked(monkeypatch, "synth_pre_mod")

    run = tracker_mod.Run(overrides=_fast_overrides(tmp_path))
    startup_manifest = json.loads((run.run_dir / "manifest.json").read_text(encoding="utf-8"))
    _validate_manifest(startup_manifest)

    assert startup_manifest["packages"]["snapshot_stage"] == "startup"
    pre_start = _find_record(startup_manifest["packages"], "synth-pre-dist")
    assert pre_start is not None
    assert pre_start["observed_at"] == "startup"
    assert _find_record(startup_manifest["packages"], "synth-post-dist") is None

    _import_tracked(monkeypatch, "synth_post_mod")
    run.stop()

    final_manifest = json.loads((run.run_dir / "manifest.json").read_text(encoding="utf-8"))
    _validate_manifest(final_manifest)
    assert final_manifest["packages"]["snapshot_stage"] == "final"

    pre_final = _find_record(final_manifest["packages"], "synth-pre-dist")
    post_final = _find_record(final_manifest["packages"], "synth-post-dist")
    assert pre_final is not None and pre_final["observed_at"] == "startup_and_final"
    assert post_final is not None and post_final["observed_at"] == "final"


def test_no_import_hook_and_transient_unload_coverage_note(tmp_path):
    """import pubrun installs no global import hook; a library imported after startup and
    removed before exit is not fabricated and coverage_notes documents the boundary."""
    site_dir = tmp_path / "site_transient"
    _write_dist(
        site_dir,
        "synth-transient-dist",
        "1.0.0",
        top_levels=["synth_transient_mod"],
        files={"synth_transient_mod/__init__.py": "TEMP = 1\n"},
    )

    script_path = tmp_path / "transient_script.py"
    script_path.write_text(
        "import builtins\n"
        "import sys\n"
        "meta_before = list(sys.meta_path)\n"
        "import_before = builtins.__import__\n"
        "import pubrun\n"
        "assert list(sys.meta_path) == meta_before, 'sys.meta_path was modified'\n"
        "assert builtins.__import__ is import_before, 'builtins.__import__ was modified'\n"
        "import synth_transient_mod\n"
        "assert synth_transient_mod.TEMP == 1\n"
        "del sys.modules['synth_transient_mod']\n",
        encoding="utf-8",
    )

    env = os.environ.copy()
    existing_py = env.get("PYTHONPATH", "")
    py_parts = [str(site_dir), str(_REPO_ROOT / "src")]
    if existing_py:
        py_parts.append(existing_py)
    env["PYTHONPATH"] = os.pathsep.join(py_parts)
    env.pop("PUBRUN_AUTO_START", None)

    proc = subprocess.run(
        [sys.executable, str(script_path)],
        cwd=str(tmp_path),
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert proc.returncode == 0, f"stderr={proc.stderr}\nstdout={proc.stdout}"

    run_dirs = [p for p in (tmp_path / "runs").iterdir() if p.is_dir()]
    assert len(run_dirs) == 1
    manifest = json.loads((run_dirs[0] / "manifest.json").read_text(encoding="utf-8"))
    _validate_manifest(manifest)

    assert _find_record(manifest["packages"], "synth-transient-dist") is None
    notes = manifest["packages"].get("coverage_notes") or []
    assert notes
    assert any("global import hook" in n and "sys.modules" in n for n in notes)


def test_finalization_error_resilience_preserves_startup_snapshot(tmp_path, monkeypatch):
    """A failure during finalization package refresh keeps startup records intact without
    mutating _startup_packages_data, degrades capture_state to schema-valid 'partial'
    (or 'failed' if startup also failed), redacts secrets, and never crashes stop()."""
    site_dir = tmp_path / "site_fin_err"
    _write_dist(
        site_dir,
        "synth-finerr-dist",
        "1.0.0",
        top_levels=["synth_finerr_mod"],
        files={"synth_finerr_mod/__init__.py": "E = 1\n"},
    )
    monkeypatch.syspath_prepend(str(site_dir))
    _import_tracked(monkeypatch, "synth_finerr_mod")

    run = tracker_mod.Run(overrides=_fast_overrides(tmp_path / "r_partial"))
    startup_snapshot_copy = copy.deepcopy(run._startup_packages_data)

    fake_token = "sk-" + "test000011112222"

    def _boom_final(*args, **kwargs):
        raise RuntimeError(f"metadata scan failed --api-key={fake_token}")

    monkeypatch.setattr(tracker_mod, "get_packages", _boom_final)
    run.stop()

    # _startup_packages_data was not mutated by finalization degradation.
    assert run._startup_packages_data == startup_snapshot_copy

    manifest = json.loads((run.run_dir / "manifest.json").read_text(encoding="utf-8"))
    _validate_manifest(manifest)

    pkg_sec = manifest["packages"]
    assert _find_record(pkg_sec, "synth-finerr-dist") is not None
    cs = pkg_sec["capture_state"]
    assert cs["status"] == "partial"
    assert isinstance(cs.get("detail"), str) and cs["detail"]
    assert fake_token not in cs["detail"]
    assert any(
        rec.get("kind") == "capture-error"
        and rec.get("section") == "packages"
        and rec.get("stage") == "finalization"
        for rec in manifest["errors"]["records"]
    )

    # When startup ALSO failed, finalization failure keeps status == "failed".
    run_failed = tracker_mod.Run(overrides=_fast_overrides(tmp_path / "r_failed"))
    run_failed.stop()
    m_failed = json.loads((run_failed.run_dir / "manifest.json").read_text(encoding="utf-8"))
    _validate_manifest(m_failed)
    assert m_failed["packages"]["capture_state"]["status"] == "failed"
    assert fake_token not in m_failed["packages"]["capture_state"].get("detail", "")


def test_mode_off_stays_suppressed_at_startup_and_finalization(tmp_path, monkeypatch):
    """mode='off' omits 'mode' and stays suppressed at both startup and finalization."""
    site_dir = tmp_path / "site_off"
    _write_dist(
        site_dir,
        "synth-off-dist",
        "1.0.0",
        top_levels=["synth_off_mod"],
        files={"synth_off_mod/__init__.py": "OFF = True\n"},
    )
    monkeypatch.syspath_prepend(str(site_dir))

    run = tracker_mod.Run(
        overrides=_fast_overrides(tmp_path, capture={"packages": {"mode": "off"}})
    )
    startup_m = json.loads((run.run_dir / "manifest.json").read_text(encoding="utf-8"))
    _validate_manifest(startup_m)
    assert startup_m["packages"] == {"capture_state": {"status": "suppressed"}}
    assert "mode" not in startup_m["packages"]

    _import_tracked(monkeypatch, "synth_off_mod")
    run.stop()

    final_m = json.loads((run.run_dir / "manifest.json").read_text(encoding="utf-8"))
    _validate_manifest(final_m)
    assert final_m["packages"] == {"capture_state": {"status": "suppressed"}}
    assert "mode" not in final_m["packages"]


# ---------------------------------------------------------------------------
# V-04: Downstream consumers (methods.py, diagnostics.py, tui/widgets/details.py)
# ---------------------------------------------------------------------------


def test_methods_pep503_highlight_matching_and_null_version():
    """extract_highlighted_packages normalizes names via PEP 503, deduplicates, and
    handles None names and None versions safely."""
    from pubrun.report.methods import extract_highlighted_packages

    manifest = {
        "packages": {
            "records": [
                {"name": "Scikit_Learn", "version": "1.5.0"},
                {"name": "scikit-learn", "version": "1.5.0"},
                {"name": "NumPy", "version": None},
                {"name": None, "version": "1.0.0"},
                {"name": "", "version": "1.0.0"},
                {"name": "some-other-lib", "version": "0.1.0"},
            ]
        }
    }
    found = extract_highlighted_packages(manifest)
    assert found == ["scikit-learn (v1.5.0)", "numpy (vunknown)"]


def test_diagnostics_show_null_version_and_unresolved_rendering(tmp_path, monkeypatch, capsys):
    """diagnostics.print_report guards None names/versions and renders unresolved entries
    in both section='packages' and depth='deep', leaving empty-unresolved output clean."""
    from pubrun.report.diagnostics import print_report

    monkeypatch.setenv("NO_COLOR", "1")
    run_dir = tmp_path / "runs" / "pubrun-diag-001"
    run_dir.mkdir(parents=True)

    manifest_with_unresolved = {
        "run": {"run_id": "diag0001"},
        "timing": {"started_at_utc": 1780250000.0, "elapsed_seconds": 12.0},
        "status": {"outcome": "completed"},
        "invocation": {"script": {"basename": "train.py"}, "argv": ["train.py"]},
        "python": {"version": "3.11.4", "executable": "/usr/bin/python3"},
        "host": {"os_name": "Linux", "hostname": "node01"},
        "hardware": {"cpu": {"model": "Xeon"}, "memory_total_bytes": 16 * 1024**3},
        "git": {"commit": "abcdef1234567890"},
        "environment": {"variables": []},
        "packages": {
            "mode": "imported-only",
            "snapshot_stage": "final",
            "records": [
                {"name": "alpha-pkg", "version": None},
                {"name": None, "version": None},
            ],
            "unresolved": [
                {
                    "module": "ambig_ns",
                    "reason": "ambiguous",
                    "candidates": ["dist-a", "dist-b"],
                    "observed_at": "final",
                    "detail": "multiple candidates",
                },
                {
                    "module": "orphan_mod",
                    "reason": "unmapped_site_package",
                    "candidates": [],
                    "observed_at": "final",
                    "detail": "no dist-info found",
                },
            ],
            "capture_state": {"status": "partial"},
        },
        "subprocesses": [],
    }
    manifest_path = run_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest_with_unresolved), encoding="utf-8")

    # 1. section="packages"
    print_report(str(manifest_path), section="packages")
    out_pkg = capsys.readouterr().out
    assert "alpha-pkg==unknown" in out_pkg
    assert "<unknown>==unknown" in out_pkg
    assert "==None" not in out_pkg
    assert "None==" not in out_pkg
    assert "Unresolved (2):" in out_pkg
    assert "ambig_ns: ambiguous (2 candidates: dist-a, dist-b)" in out_pkg
    assert "orphan_mod: unmapped_site_package (no dist-info found)" in out_pkg

    # 2. depth="standard"
    print_report(str(manifest_path), depth="standard")
    out_std = capsys.readouterr().out
    assert "Packages    : 2 recorded (2 unresolved)" in out_std

    # 3. depth="deep"
    print_report(str(manifest_path), depth="deep")
    out_deep = capsys.readouterr().out
    assert "Packages    : 2 recorded (2 unresolved)" in out_deep
    assert "alpha-pkg==unknown" in out_deep
    assert "<unknown>==unknown" in out_deep
    assert "==None" not in out_deep
    assert "Unresolved (2):" in out_deep
    assert "ambig_ns: ambiguous (2 candidates: dist-a, dist-b)" in out_deep

    # 4. End-to-end CLI `pubrun show <run_dir> packages`
    env = os.environ.copy()
    env["NO_COLOR"] = "1"
    existing_py = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = (
        f"{_REPO_ROOT / 'src'}{os.pathsep}{existing_py}"
        if existing_py
        else str(_REPO_ROOT / "src")
    )
    cli_proc = subprocess.run(
        [sys.executable, "-m", "pubrun", "show", str(run_dir), "packages"],
        cwd=str(tmp_path),
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert cli_proc.returncode == 0
    assert "alpha-pkg==unknown" in cli_proc.stdout
    assert "Unresolved (2):" in cli_proc.stdout

    # 5. Empty unresolved leaves existing output unchanged (no "(0 unresolved)" suffix).
    manifest_clean = copy.deepcopy(manifest_with_unresolved)
    manifest_clean["packages"]["unresolved"] = []
    manifest_clean["packages"]["capture_state"] = {"status": "complete"}
    clean_path = tmp_path / "clean_manifest.json"
    clean_path.write_text(json.dumps(manifest_clean), encoding="utf-8")

    print_report(str(clean_path), depth="standard")
    out_clean_std = capsys.readouterr().out
    assert "Packages    : 2 recorded\n" in out_clean_std
    assert "unresolved" not in out_clean_std.lower()

    print_report(str(clean_path), section="packages")
    out_clean_pkg = capsys.readouterr().out
    assert "Unresolved" not in out_clean_pkg


def test_tui_null_version_filter_rows_and_pilot(tmp_path):
    """_filter_package_rows handles None names/versions/locations unconditionally, and
    RunDetailsView.update_packages_pane works cleanly under Textual Pilot when installed."""
    from pubrun.tui.widgets.details import _filter_package_rows

    records = [
        {"name": "alpha-null", "version": None, "location": None, "editable": False},
        {"name": "beta-edit", "version": "2.1.0", "location": "/src/beta", "editable": True},
        {"name": None, "version": None, "location": None, "editable": None},
    ]

    all_rows = _filter_package_rows(records, "")
    assert all_rows == [
        ("alpha-null", "", "Installed"),
        ("beta-edit", "2.1.0", "Editable (/src/beta)"),
        ("", "", "Installed"),
    ]

    filtered = _filter_package_rows(records, "alpha")
    assert filtered == [("alpha-null", "", "Installed")]

    filtered_ver = _filter_package_rows(records, "2.1")
    assert filtered_ver == [("beta-edit", "2.1.0", "Editable (/src/beta)")]

    # Full Pilot integration when textual is installed.
    pytest.importorskip("textual")
    from textual.app import App, ComposeResult
    from textual.widgets import DataTable
    from pubrun.status import RunInfo
    from pubrun.tui.widgets.details import RunDetailsView

    run_dir = tmp_path / "runs" / "pubrun-tui-null"
    run_dir.mkdir(parents=True)
    (run_dir / "manifest.json").write_text(
        json.dumps(
            {
                "run": {"run_id": "tuinull1"},
                "status": {"outcome": "completed"},
                "timing": {"started_at_utc": 1780250000.0},
                "packages": {"records": records, "capture_state": {"status": "complete"}},
            }
        ),
        encoding="utf-8",
    )

    class _DetailsTestApp(App):
        def compose(self) -> ComposeResult:
            yield RunDetailsView(id="details")

    async def _drive():
        app = _DetailsTestApp()
        async with app.run_test() as pilot:
            view = app.query_one("#details", RunDetailsView)
            view.display_run(RunInfo(run_dir))
            await pilot.pause()
            table = view.query_one("#packages-table", DataTable)
            assert table.row_count == 3

            # Filtering with version=None records must not raise AttributeError.
            view.update_packages_pane("alpha")
            await pilot.pause()
            assert table.row_count == 1

            view.update_packages_pane("2.1")
            await pilot.pause()
            assert table.row_count == 1

    asyncio.run(_drive())
