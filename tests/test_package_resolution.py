"""Deterministic fixture tests for package identity resolution, caching, and edge cases."""
import importlib
import importlib.metadata
import json
import os
from pathlib import Path
import sys
import sysconfig
import threading
import types
from typing import Dict, Iterable, List, Optional

import pytest

import pubrun.capture.packages as pkgs


@pytest.fixture(autouse=True)
def _clean_package_cache():
    """Ensure every test starts and ends with a clean distribution index cache."""
    pkgs.invalidate_package_cache()
    yield
    pkgs.invalidate_package_cache()


def _write_dist(
    base_dir: Path,
    dist_name: str,
    version: str = "1.0.0",
    *,
    top_levels: Optional[Iterable[str]] = None,
    files: Optional[Dict[str, str]] = None,
    requires: Optional[Iterable[str]] = None,
    direct_url: Optional[str] = None,
    record_entries: Optional[Iterable[str]] = None,
    include_name_header: bool = True,
    write_record: bool = True,
) -> Path:
    """Create a PEP 376 ``.dist-info`` directory and module files under ``base_dir``."""
    base_dir.mkdir(parents=True, exist_ok=True)
    dist_dir_name = f"{dist_name.replace('-', '_')}-{version}.dist-info"
    dist_dir = base_dir / dist_dir_name
    dist_dir.mkdir(parents=True, exist_ok=True)

    meta_lines = ["Metadata-Version: 2.1"]
    if include_name_header:
        meta_lines.append(f"Name: {dist_name}")
    meta_lines.append(f"Version: {version}")
    for req in requires or ():
        meta_lines.append(f"Requires-Dist: {req}")
    (dist_dir / "METADATA").write_text("\n".join(meta_lines) + "\n", encoding="utf-8")

    records: List[str] = [f"{dist_dir_name}/METADATA,,"]

    if top_levels is not None:
        top_text = "\n".join(top_levels) + ("\n" if top_levels else "")
        (dist_dir / "top_level.txt").write_text(top_text, encoding="utf-8")
        records.append(f"{dist_dir_name}/top_level.txt,,")

    if direct_url is not None:
        (dist_dir / "direct_url.json").write_text(direct_url, encoding="utf-8")
        records.append(f"{dist_dir_name}/direct_url.json,,")

    for rel_path, content in (files or {}).items():
        full_path = base_dir / rel_path
        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.write_text(content, encoding="utf-8")
        records.append(f"{rel_path},,")

    for extra_entry in record_entries or ():
        records.append(f"{extra_entry},,")

    if write_record:
        records.append(f"{dist_dir_name}/RECORD,,")
        (dist_dir / "RECORD").write_text("\n".join(records) + "\n", encoding="utf-8")

    return dist_dir


def _import_tracked(monkeypatch: pytest.MonkeyPatch, module_name: str):
    """Import ``module_name`` cleanly while guaranteeing teardown removal from ``sys.modules``."""
    before = set(sys.modules.keys())
    importlib.invalidate_caches()
    mod = importlib.import_module(module_name)
    added_items = {k: sys.modules[k] for k in (set(sys.modules.keys()) - before)}
    for k in added_items:
        sys.modules.pop(k, None)
    for k, v in added_items.items():
        monkeypatch.setitem(sys.modules, k, v)
    return mod


def _find_record(result: dict, name: str) -> Optional[dict]:
    """Return the first package record matching ``name`` (case-insensitive)."""
    target = pkgs.normalize_package_name(name)
    for rec in result.get("records", []):
        if pkgs.normalize_package_name(rec.get("name") or "") == target:
            return rec
    return None


# ---------------------------------------------------------------------------
# E-01 / V-01: Normalization, caching, deduplication, Python 3.8/3.9 fallback
# ---------------------------------------------------------------------------


def test_normalize_package_name_pep503():
    assert pkgs.normalize_package_name("Scikit_Learn") == "scikit-learn"
    assert pkgs.normalize_package_name("zope.interface") == "zope-interface"
    assert pkgs.normalize_package_name("Foo__Bar--Baz..Qux") == "foo-bar-baz-qux"
    assert pkgs.normalize_package_name("Pillow") == "pillow"


def test_cache_single_scan_and_invalidation(tmp_path, monkeypatch):
    site_a = tmp_path / "site_a"
    site_b = tmp_path / "site_b"
    _write_dist(
        site_a,
        "synth-cache-one",
        "1.0.0",
        files={"synth_cache_one/__init__.py": "VALUE = 1\n"},
    )
    site_b.mkdir()
    monkeypatch.syspath_prepend(str(site_a))

    real_distributions = importlib.metadata.distributions
    call_count = 0

    def counting_distributions():
        nonlocal call_count
        call_count += 1
        return list(real_distributions())

    monkeypatch.setattr("importlib.metadata.distributions", counting_distributions)

    # First call scans once; repeated calls with unchanged environment reuse cache.
    idx1 = pkgs._get_distribution_index(use_cache=True)
    idx2 = pkgs._get_distribution_index(use_cache=True)
    versions = pkgs.get_installed_distribution_versions(use_cache=True)
    assert idx1 is idx2
    assert call_count == 1
    assert "synth-cache-one" in versions

    # Explicit invalidation triggers a fresh scan.
    pkgs.invalidate_package_cache()
    pkgs._get_distribution_index(use_cache=True)
    assert call_count == 2

    # Deterministic directory mtime bump via os.utime invalidates cache.
    st = os.stat(site_a)
    bumped_ns = st.st_mtime_ns + 5_000_000_000
    os.utime(site_a, ns=(st.st_atime_ns, bumped_ns))
    pkgs._get_distribution_index(use_cache=True)
    assert call_count == 3

    # Changing sys.path invalidates cache.
    monkeypatch.syspath_prepend(str(site_b))
    pkgs._get_distribution_index(use_cache=True)
    assert call_count == 4

    # Monkeypatching importlib.metadata.distributions invalidates cache.
    other_calls = 0

    def other_distributions():
        nonlocal other_calls
        other_calls += 1
        return list(real_distributions())

    monkeypatch.setattr("importlib.metadata.distributions", other_distributions)
    pkgs._get_distribution_index(use_cache=True)
    assert other_calls == 1


def test_dedup_duplicate_and_symlinked_sys_path(tmp_path, monkeypatch):
    site_dir = tmp_path / "site_real"
    _write_dist(
        site_dir,
        "synth-dedup-pkg",
        "1.2.3",
        top_levels=["synth_dedup"],
        files={"synth_dedup/__init__.py": "X = 1\n"},
    )
    monkeypatch.syspath_prepend(str(site_dir))
    monkeypatch.syspath_prepend(str(site_dir))

    link_dir = tmp_path / "site_link"
    try:
        os.symlink(site_dir, link_dir)
    except (OSError, NotImplementedError):
        link_dir = None
    if link_dir is not None:
        monkeypatch.syspath_prepend(str(link_dir))

    _import_tracked(monkeypatch, "synth_dedup")

    idx = pkgs._get_distribution_index(use_cache=False)
    assert len(idx.module_to_dists["synth_dedup"]) == 1

    snap = pkgs.resolve_packages_snapshot({"capture": {"packages": {"mode": "imported-only"}}})
    rec = _find_record(snap, "synth-dedup-pkg")
    assert rec is not None
    assert rec["version"] == "1.2.3"
    assert not any(u["module"] == "synth_dedup" for u in snap["unresolved"])


def test_fallback_python38_39_parity_and_record_filtering(tmp_path, monkeypatch):
    import importlib.machinery

    site_dir = tmp_path / "env" / "site_fallback"
    bin_file = tmp_path / "env" / "bin" / "synth-cli"
    bin_file.parent.mkdir(parents=True, exist_ok=True)
    bin_file.write_text("#!/bin/sh\n", encoding="utf-8")

    ext_suffix = importlib.machinery.EXTENSION_SUFFIXES[0]
    _write_dist(
        site_dir,
        "synth-inferred-pkg",
        "3.1.0",
        top_levels=None,
        files={
            "synth_inferred/__init__.py": "X = 1\n",
            "synth_single_mod.py": "Y = 2\n",
            "synth_hook.pth": "import os\n",
            f"synth_ext{ext_suffix}": "",
            "__pycache__/synth_single_mod.pyc": "",
        },
        record_entries=[
            "../bin/synth-cli",
        ],
    )
    monkeypatch.syspath_prepend(str(site_dir))

    # Parity check against importlib.metadata.packages_distributions on Python 3.10+.
    idx = pkgs._get_distribution_index(use_cache=False)
    assert "synth_inferred" in idx.module_to_dists
    assert "synth_single_mod" in idx.module_to_dists
    assert "synth_ext" in idx.module_to_dists
    assert ".." not in idx.module_to_dists
    assert "synth_hook.pth" not in idx.module_to_dists
    assert "__pycache__" not in idx.module_to_dists

    if hasattr(importlib.metadata, "packages_distributions"):
        stdlib_map = importlib.metadata.packages_distributions()
        for mod_name in ("synth_inferred", "synth_single_mod", "synth_ext"):
            assert "synth-inferred-pkg" in stdlib_map.get(mod_name, [])

    # Verify resolution still succeeds when packages_distributions does not exist (Python 3.8/3.9).
    monkeypatch.delattr(importlib.metadata, "packages_distributions", raising=False)
    pkgs.invalidate_package_cache()
    _import_tracked(monkeypatch, "synth_inferred")
    snap = pkgs.resolve_packages_snapshot({"capture": {"packages": {"mode": "imported-only"}}})
    rec = _find_record(snap, "synth-inferred-pkg")
    assert rec is not None
    assert rec["name"] == "synth-inferred-pkg"
    assert rec["version"] == "3.1.0"
    assert rec["import_names"] == ["synth_inferred"]


def test_installed_distribution_versions_helper(tmp_path, monkeypatch):
    site_dir = tmp_path / "site_versions"
    _write_dist(
        site_dir,
        "Synth_Helper_Pkg",
        "4.5.6",
        files={"synth_helper_pkg/__init__.py": "A = 1\n"},
        direct_url=json.dumps({"dir_info": {"editable": True}, "url": "file:///tmp/unused"}),
    )
    monkeypatch.syspath_prepend(str(site_dir))

    versions = pkgs.get_installed_distribution_versions(use_cache=True)
    assert "synth-helper-pkg" in versions
    entry = versions["synth-helper-pkg"]
    assert entry["name"] == "Synth_Helper_Pkg"
    assert entry["version"] == "4.5.6"
    assert entry["editable"] is True
    assert isinstance(entry["location"], str)
    assert "synth_helper_pkg" not in sys.modules


# ---------------------------------------------------------------------------
# E-02 / V-02: Resolution edge cases, concurrency, proxies, no-import invariant
# ---------------------------------------------------------------------------


def test_import_name_mismatch_resolves_canonical_distribution(tmp_path, monkeypatch):
    site_dir = tmp_path / "site_mismatch"
    _write_dist(
        site_dir,
        "synth-scikit-learn",
        "2.3.4",
        top_levels=["synth_skl"],
        files={"synth_skl/__init__.py": "MODEL = 'rf'\n"},
    )
    monkeypatch.syspath_prepend(str(site_dir))
    _import_tracked(monkeypatch, "synth_skl")

    snap = pkgs.resolve_packages_snapshot({"capture": {"packages": {"mode": "imported-only"}}})
    rec = _find_record(snap, "synth-scikit-learn")
    assert rec is not None
    assert rec["name"] == "synth-scikit-learn"
    assert rec["version"] == "2.3.4"
    assert rec["editable"] is False
    assert isinstance(rec["location"], str) and str(site_dir) in rec["location"]
    assert rec["source"] == "imported"
    assert rec["import_names"] == ["synth_skl"]


def test_namespace_package_resolves_only_loaded_submodule_distribution(tmp_path, monkeypatch):
    site_dir = tmp_path / "site_ns"
    _write_dist(
        site_dir,
        "synth-ns-a",
        "1.0.0",
        top_levels=["synth_ns"],
        files={"synth_ns/part_a/__init__.py": "PART = 'a'\n"},
    )
    _write_dist(
        site_dir,
        "synth-ns-b",
        "2.0.0",
        top_levels=["synth_ns"],
        files={"synth_ns/part_b/__init__.py": "PART = 'b'\n"},
    )
    monkeypatch.syspath_prepend(str(site_dir))
    _import_tracked(monkeypatch, "synth_ns.part_a")

    snap = pkgs.resolve_packages_snapshot({"capture": {"packages": {"mode": "imported-only"}}})
    rec_a = _find_record(snap, "synth-ns-a")
    rec_b = _find_record(snap, "synth-ns-b")

    assert rec_a is not None
    assert rec_a["version"] == "1.0.0"
    assert rec_a["import_names"] == ["synth_ns.part_a"]
    assert rec_b is None
    assert not any(u["module"].startswith("synth_ns") for u in snap["unresolved"])


def test_ambiguous_mapping_and_bare_namespace_mark_partial(tmp_path, monkeypatch):
    site_dir = tmp_path / "site_ambig"
    # Case 1: Two distributions claim the same top-level module with no RECORD paths.
    _write_dist(
        site_dir,
        "synth-ambig-one",
        "1.0.0",
        top_levels=["synth_ambig_mod"],
        files={"synth_ambig_mod.py": "VAL = 1\n"},
        write_record=False,
    )
    _write_dist(
        site_dir,
        "synth-ambig-two",
        "2.0.0",
        top_levels=["synth_ambig_mod"],
        write_record=False,
    )
    # Case 2: Bare namespace package imported without any loaded submodule.
    _write_dist(
        site_dir,
        "synth-bare-ns-a",
        "1.0.0",
        top_levels=["synth_bare_ns"],
        files={"synth_bare_ns/sub_a.py": "A = 1\n"},
    )
    _write_dist(
        site_dir,
        "synth-bare-ns-b",
        "1.0.0",
        top_levels=["synth_bare_ns"],
        files={"synth_bare_ns/sub_b.py": "B = 2\n"},
    )
    monkeypatch.syspath_prepend(str(site_dir))
    _import_tracked(monkeypatch, "synth_ambig_mod")
    _import_tracked(monkeypatch, "synth_bare_ns")

    snap = pkgs.resolve_packages_snapshot({"capture": {"packages": {"mode": "imported-only"}}})
    assert snap["capture_state"]["status"] == "partial"
    assert snap["capture_state"].get("warnings")

    unresolved_by_mod = {u["module"]: u for u in snap["unresolved"]}
    assert "synth_ambig_mod" in unresolved_by_mod
    assert unresolved_by_mod["synth_ambig_mod"]["reason"] == "ambiguous"
    assert unresolved_by_mod["synth_ambig_mod"]["candidates"] == [
        "synth-ambig-one",
        "synth-ambig-two",
    ]

    assert "synth_bare_ns" in unresolved_by_mod
    assert unresolved_by_mod["synth_bare_ns"]["reason"] == "ambiguous"
    assert unresolved_by_mod["synth_bare_ns"]["candidates"] == [
        "synth-bare-ns-a",
        "synth-bare-ns-b",
    ]
    assert _find_record(snap, "synth-ambig-one") is None
    assert _find_record(snap, "synth-bare-ns-a") is None


def test_stdlib_and_builtin_modules_excluded_cleanly(tmp_path, monkeypatch):
    import json as _json_mod  # noqa: F401
    import math as _math_mod  # noqa: F401

    stdlib_dir = Path(sysconfig.get_paths()["stdlib"])
    fake_stdlib_mod = types.ModuleType("_synth_generated_stdlib")
    fake_stdlib_mod.__file__ = str(stdlib_dir / "_synth_generated_stdlib.py")
    monkeypatch.setitem(sys.modules, "_synth_generated_stdlib", fake_stdlib_mod)

    snap = pkgs.resolve_packages_snapshot({"capture": {"packages": {"mode": "imported-only"}}})
    record_names = {r["name"].lower() for r in snap["records"]}
    unresolved_mods = {u["module"] for u in snap["unresolved"]}
    local_mods = set(snap["local_modules"])

    for std_name in ("json", "sys", "math", "_synth_generated_stdlib"):
        assert std_name not in record_names
        assert std_name not in unresolved_mods
        assert std_name not in local_mods
    assert snap["capture_state"]["status"] == "complete"


def test_local_only_module_classified_without_partial(tmp_path, monkeypatch):
    work_dir = tmp_path / "work"
    work_dir.mkdir()
    (work_dir / "synth_local_helper.py").write_text("HELPER = True\n", encoding="utf-8")
    monkeypatch.syspath_prepend(str(work_dir))
    _import_tracked(monkeypatch, "synth_local_helper")

    snap = pkgs.resolve_packages_snapshot({"capture": {"packages": {"mode": "imported-only"}}})
    assert "synth_local_helper" in snap["local_modules"]
    assert _find_record(snap, "synth_local_helper") is None
    assert not any(u["module"] == "synth_local_helper" for u in snap["unresolved"])
    assert snap["capture_state"]["status"] == "complete"


def test_unmapped_site_package_module_marks_partial(tmp_path, monkeypatch):
    sp_dir = tmp_path / "site-packages"
    sp_dir.mkdir()
    (sp_dir / "synth_orphan_lib.py").write_text("ORPHAN = 1\n", encoding="utf-8")
    monkeypatch.syspath_prepend(str(sp_dir))
    _import_tracked(monkeypatch, "synth_orphan_lib")

    snap = pkgs.resolve_packages_snapshot({"capture": {"packages": {"mode": "imported-only"}}})
    assert snap["capture_state"]["status"] == "partial"
    matches = [u for u in snap["unresolved"] if u["module"] == "synth_orphan_lib"]
    assert len(matches) == 1
    assert matches[0]["reason"] == "unmapped_site_package"
    assert "synth_orphan_lib" not in snap["local_modules"]
    assert _find_record(snap, "synth_orphan_lib") is None


def test_editable_direct_url_variants_and_no_url_leak(tmp_path, monkeypatch):
    site_dir = tmp_path / "site_editable"
    secret_url = "https://alice:top_secret_token_987@private.example.invalid/org/repo.git"

    _write_dist(
        site_dir,
        "synth-edit-true",
        "1.0.0",
        top_levels=["synth_edit_true"],
        files={"synth_edit_true/__init__.py": "E = 1\n"},
        direct_url=json.dumps({"dir_info": {"editable": True}, "url": secret_url}),
    )
    _write_dist(
        site_dir,
        "synth-edit-false",
        "1.0.0",
        top_levels=["synth_edit_false"],
        files={"synth_edit_false/__init__.py": "E = 2\n"},
        direct_url=json.dumps({"dir_info": {"editable": False}, "url": secret_url}),
    )
    _write_dist(
        site_dir,
        "synth-edit-omitted",
        "1.0.0",
        top_levels=["synth_edit_omitted"],
        files={"synth_edit_omitted/__init__.py": "E = 3\n"},
        direct_url=json.dumps({"dir_info": {}, "url": secret_url}),
    )
    _write_dist(
        site_dir,
        "synth-edit-nondict",
        "1.0.0",
        top_levels=["synth_edit_nondict"],
        files={"synth_edit_nondict/__init__.py": "E = 4\n"},
        direct_url="[]",
    )
    _write_dist(
        site_dir,
        "synth-edit-nonjson",
        "1.0.0",
        top_levels=["synth_edit_nonjson"],
        files={"synth_edit_nonjson/__init__.py": "E = 5\n"},
        direct_url=f"not-json dir_info {secret_url}",
    )

    monkeypatch.syspath_prepend(str(site_dir))
    for mod in (
        "synth_edit_true",
        "synth_edit_false",
        "synth_edit_omitted",
        "synth_edit_nondict",
        "synth_edit_nonjson",
    ):
        _import_tracked(monkeypatch, mod)

    snap = pkgs.resolve_packages_snapshot({"capture": {"packages": {"mode": "imported-only"}}})
    assert _find_record(snap, "synth-edit-true")["editable"] is True
    assert _find_record(snap, "synth-edit-false")["editable"] is False
    assert _find_record(snap, "synth-edit-omitted")["editable"] is False
    assert _find_record(snap, "synth-edit-nondict")["editable"] is False
    assert _find_record(snap, "synth-edit-nonjson")["editable"] is True

    serialized = json.dumps(snap)
    assert "top_secret_token_987" not in serialized
    assert "private.example.invalid" not in serialized


def test_missing_metadata_and_corrupt_dist_degrade_to_partial(tmp_path, monkeypatch):
    site_dir = tmp_path / "site_missing_meta"
    _write_dist(
        site_dir,
        "synth-noname-pkg",
        "1.0.0",
        top_levels=["synth_noname_mod"],
        files={"synth_noname_mod/__init__.py": "X = 1\n"},
        include_name_header=False,
    )
    monkeypatch.syspath_prepend(str(site_dir))
    _import_tracked(monkeypatch, "synth_noname_mod")

    # Imported-only mode: flags missing_metadata without emitting a None-named record.
    snap_imp = pkgs.resolve_packages_snapshot({"capture": {"packages": {"mode": "imported-only"}}})
    assert snap_imp["capture_state"]["status"] == "partial"
    assert all(isinstance(r.get("name"), str) and r["name"] for r in snap_imp["records"])
    assert any(
        u["module"] == "synth_noname_mod" and u["reason"] == "missing_metadata"
        for u in snap_imp["unresolved"]
    )

    # Full-environment mode: omits broken record and reports partial.
    snap_full = pkgs.resolve_packages_snapshot(
        {"capture": {"packages": {"mode": "full-environment"}}}
    )
    assert snap_full["capture_state"]["status"] == "partial"
    assert all(isinstance(r.get("name"), str) and r["name"] for r in snap_full["records"])
    assert any(u["reason"] == "missing_metadata" for u in snap_full["unresolved"])

    # Distribution whose metadata property raises must also degrade cleanly.
    class BrokenDist:
        _path = tmp_path / "broken-0.1.dist-info"

        @property
        def metadata(self):
            raise RuntimeError("corrupt metadata stream")

    monkeypatch.setattr("importlib.metadata.distributions", lambda: [BrokenDist()])
    snap_err = pkgs.resolve_packages_snapshot(
        {"capture": {"packages": {"mode": "full-environment"}}}
    )
    assert snap_err["records"] == []
    assert snap_err["capture_state"]["status"] == "partial"
    assert snap_err["unresolved"][0]["reason"] == "metadata_error"


def test_concurrent_sys_modules_mutation_and_lazy_proxy_safety(monkeypatch):
    import time

    class ExplodingProxy:
        def __getattr__(self, name):
            raise RuntimeError(f"lazy proxy failed on {name}")

    monkeypatch.setitem(sys.modules, "synth_lazy_proxy", ExplodingProxy())

    # Warm index once so concurrent stress exercises snapshotting and resolution
    # rather than stalling cold metadata reads behind GIL contention.
    pkgs._get_distribution_index(use_cache=True)

    stop_event = threading.Event()
    mutator_errors: List[Exception] = []
    mutations = 0

    def mutator():
        nonlocal mutations
        idx = 0
        try:
            while not stop_event.is_set():
                key = f"_synth_concurrent_mod_{idx % 40}"
                sys.modules[key] = types.ModuleType(key)
                if idx >= 10:
                    sys.modules.pop(f"_synth_concurrent_mod_{(idx - 10) % 40}", None)
                idx += 1
                mutations += 1
                if idx % 20 == 0:
                    time.sleep(0.0001)
        except Exception as exc:
            mutator_errors.append(exc)
        finally:
            for i in range(40):
                sys.modules.pop(f"_synth_concurrent_mod_{i}", None)

    worker = threading.Thread(target=mutator, daemon=True)
    worker.start()
    try:
        for _ in range(25):
            result = pkgs.get_packages({"capture": {"packages": {"mode": "imported-only"}}})
            assert result["mode"] == "imported-only"
            assert isinstance(result["records"], list)
    finally:
        stop_event.set()
        worker.join(timeout=5)

    assert not mutator_errors
    assert mutations > 0
    snap = pkgs.resolve_packages_snapshot({"capture": {"packages": {"mode": "imported-only"}}})
    assert "synth_lazy_proxy" in snap["local_modules"]

    # Also verify _snapshot_sys_modules retries cleanly when sys.modules raises RuntimeError.
    class FlakyModules(dict):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.copy_calls = 0

        def copy(self):
            self.copy_calls += 1
            if self.copy_calls < 3:
                raise RuntimeError("dictionary changed size during iteration")
            return super().copy()

    flaky = FlakyModules({"json": sys.modules["json"]})
    monkeypatch.setattr(pkgs.sys, "modules", flaky)
    snap_items = pkgs._snapshot_sys_modules()
    assert flaky.copy_calls == 3
    assert any(k == "json" for k, _ in snap_items)


def test_no_import_invariant_never_executes_unloaded_module(tmp_path, monkeypatch):
    site_dir = tmp_path / "site_no_import"
    sentinel = tmp_path / "must_not_exist.sentinel"
    payload = (
        f"from pathlib import Path\n"
        f"Path({str(sentinel)!r}).write_text('imported', encoding='utf-8')\n"
        f"raise AssertionError('must not be imported')\n"
    )
    _write_dist(
        site_dir,
        "synth-never-import",
        "1.0.0",
        top_levels=["synth_never_import"],
        files={"synth_never_import/__init__.py": payload},
    )
    monkeypatch.syspath_prepend(str(site_dir))

    for mode in ("off", "imported-only", "imported-transitive", "top-level-installed", "full-environment"):
        pkgs.get_packages({"capture": {"packages": {"mode": mode}}})

    versions = pkgs.get_installed_distribution_versions(use_cache=True)
    assert "synth-never-import" in versions
    assert not sentinel.exists()
    assert "synth_never_import" not in sys.modules


# ---------------------------------------------------------------------------
# E-03 / V-03: top-level-installed mode and manifest schema conformance
# ---------------------------------------------------------------------------


def test_top_level_installed_filters_dependencies_and_ignores_self_and_extras(tmp_path, monkeypatch):
    site_dir = tmp_path / "site_top_level"
    _write_dist(
        site_dir,
        "synth-root-pkg",
        "1.0.0",
        requires=[
            "synth-dep-pkg>=1.0",
            "synth_root_pkg[all]",
            'synth-extra-only>=1.0; extra == "dev"',
        ],
        files={"synth_root_pkg/__init__.py": "R = 1\n"},
    )
    _write_dist(
        site_dir,
        "synth-dep-pkg",
        "1.0.0",
        files={"synth_dep_pkg/__init__.py": "D = 1\n"},
    )
    _write_dist(
        site_dir,
        "synth-extra-only",
        "1.0.0",
        files={"synth_extra_only/__init__.py": "E = 1\n"},
    )

    monkeypatch.syspath_prepend(str(site_dir))

    top_res = pkgs.get_packages({"capture": {"packages": {"mode": "top-level-installed"}}})
    full_res = pkgs.get_packages({"capture": {"packages": {"mode": "full-environment"}}})

    assert top_res["mode"] == "top-level-installed"
    assert _find_record(top_res, "synth-root-pkg") is not None
    assert _find_record(top_res, "synth-extra-only") is not None
    assert _find_record(top_res, "synth-dep-pkg") is None

    assert _find_record(full_res, "synth-root-pkg") is not None
    assert _find_record(full_res, "synth-extra-only") is not None
    assert _find_record(full_res, "synth-dep-pkg") is not None


def test_get_packages_schema_conformance_and_default_mode(tmp_path, monkeypatch):
    schema_path = Path(__file__).resolve().parents[1] / "schemas" / "manifest.schema.json"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    defs = schema["$defs"]
    pkg_subschema = dict(defs["packages_section"])
    pkg_subschema["$defs"] = defs

    allowed_section_keys = set(defs["packages_section"]["properties"].keys())
    allowed_record_keys = set(defs["package_record"]["properties"].keys())
    allowed_state_keys = set(defs["capture_state"]["properties"].keys())

    site_dir = tmp_path / "site_schema"
    _write_dist(
        site_dir,
        "synth-schema-good",
        "1.0.0",
        top_levels=["synth_schema_mod"],
        files={"synth_schema_mod/__init__.py": "OK = 1\n"},
    )
    _write_dist(
        site_dir,
        "synth-schema-broken",
        "1.0.0",
        top_levels=["synth_schema_broken"],
        files={"synth_schema_broken/__init__.py": "BAD = 1\n"},
        include_name_header=False,
    )
    monkeypatch.syspath_prepend(str(site_dir))
    _import_tracked(monkeypatch, "synth_schema_mod")
    _import_tracked(monkeypatch, "synth_schema_broken")

    # Default config keeps mode="imported-only".
    default_res = pkgs.get_packages({})
    assert default_res["mode"] == "imported-only"

    # mode="off" suppresses cleanly without emitting "mode".
    off_res = pkgs.get_packages({"capture": {"packages": {"mode": "off"}}})
    assert off_res == {"capture_state": {"status": "suppressed"}}

    try:
        import jsonschema
    except ImportError:
        jsonschema = None

    for cfg in (
        {},
        {"capture": {"packages": {"mode": "off"}}},
        {"capture": {"packages": {"mode": "imported-only"}}},
        {"capture": {"packages": {"mode": "imported-transitive"}}},
        {"capture": {"packages": {"mode": "top-level-installed"}}},
        {"capture": {"packages": {"mode": "full-environment"}}},
    ):
        result = pkgs.get_packages(cfg)
        assert set(result.keys()).issubset(allowed_section_keys)
        state = result["capture_state"]
        assert set(state.keys()).issubset(allowed_state_keys)
        if "detail" in state:
            assert isinstance(state["detail"], str) and state["detail"]
        for rec in result.get("records", []):
            assert set(rec.keys()).issubset(allowed_record_keys)
            assert isinstance(rec["name"], str) and rec["name"]
        if jsonschema is not None:
            jsonschema.validate(result, pkg_subschema)
