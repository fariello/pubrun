"""Deterministic fixture tests for PEP 508 markers and recursive transitive resolution."""
import importlib
import json
import os
from pathlib import Path
import subprocess
import sys
from typing import Dict, Iterable, List, Optional

import pytest

from pubrun.capture._markers import (
    MarkerEvalResult,
    ParsedRequirement,
    default_marker_environment,
    evaluate_marker,
    parse_requirement,
)
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
) -> Path:
    """Create a PEP 376 ``.dist-info`` directory and module files under ``base_dir``."""
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
    """Import ``module_name`` while guaranteeing teardown removal from ``sys.modules``."""
    before = set(sys.modules.keys())
    importlib.invalidate_caches()
    mod = importlib.import_module(module_name)
    added = {k: sys.modules[k] for k in (set(sys.modules.keys()) - before)}
    for k in added:
        sys.modules.pop(k, None)
    for k, v in added.items():
        monkeypatch.setitem(sys.modules, k, v)
    return mod


def _find_record(result: dict, name: str) -> Optional[dict]:
    """Return the first package record matching ``name`` under PEP 503 normalization."""
    target = pkgs.normalize_package_name(name)
    for rec in result.get("records", []):
        if pkgs.normalize_package_name(rec.get("name") or "") == target:
            return rec
    return None


# ---------------------------------------------------------------------------
# E-01 / V-01: PEP 508 requirement parsing and marker evaluation
# ---------------------------------------------------------------------------


def test_parse_requirement_names_extras_direct_urls_and_malformed():
    parsed = parse_requirement(
        'Foo_Pkg[ Bar_One , baz.two , bar-one ] (>=1.0, <2.0) ; python_version >= "3.8"'
    )
    assert parsed == ParsedRequirement(
        name="Foo_Pkg",
        normalized_name="foo-pkg",
        extras=("bar-one", "baz-two"),
        marker='python_version >= "3.8"',
        raw='Foo_Pkg[ Bar_One , baz.two , bar-one ] (>=1.0, <2.0) ; python_version >= "3.8"',
    )

    # Empty extras brackets are valid PEP 508.
    empty_extras = parse_requirement("simple[]>=1.0")
    assert empty_extras is not None
    assert empty_extras.name == "simple"
    assert empty_extras.extras == ()
    assert empty_extras.marker is None

    # Direct URL containing a semicolon must not split the URL as a marker.
    url_only = parse_requirement("my_pkg @ https://example.invalid/my_pkg;param=1.whl")
    assert url_only is not None
    assert url_only.name == "my_pkg"
    assert url_only.normalized_name == "my-pkg"
    assert url_only.marker is None

    # Direct URL with semicolon followed by whitespace and a marker clause.
    url_marker = parse_requirement(
        'my_pkg[Fast_Mode] @ https://example.invalid/a;b=2.whl ; sys_platform == "linux"'
    )
    assert url_marker is not None
    assert url_marker.extras == ("fast-mode",)
    assert url_marker.marker == 'sys_platform == "linux"'

    # Semicolon inside quoted string in marker stays intact.
    quoted_semi = parse_requirement('pkg>=1.0 ; platform_version == "alpha;beta"')
    assert quoted_semi is not None
    assert quoted_semi.marker == 'platform_version == "alpha;beta"'

    # Empty/whitespace and malformed requirements return None.
    for bad in (
        "",
        "   ",
        ";;;",
        "foo[unclosed",
        "foo[bad,]",
        "foo[bad$extra]",
        "foo @",
        "foo @ https://example.invalid/a.whl trailing_junk",
        "foo >= 1.0 ;",
        "foo-",
        "foo bar",
        "foo (>=1.0",
    ):
        assert parse_requirement(bad) is None, f"Expected None for {bad!r}"

    # _parse_req_name preserves exact behavior for empty and standard strings.
    assert pkgs._parse_req_name("") == ""
    assert pkgs._parse_req_name("baz-qux.thing>=2.0") == "baz-qux.thing"
    assert pkgs._parse_req_name("pkg @ https://example.invalid/a;b.whl") == "pkg"


def test_marker_environment_defaults_and_legacy_aliases():
    env = default_marker_environment()
    expected_keys = {
        "os_name",
        "sys_platform",
        "platform_machine",
        "platform_python_implementation",
        "platform_release",
        "platform_system",
        "platform_version",
        "python_version",
        "python_full_version",
        "implementation_name",
        "implementation_version",
    }
    assert expected_keys.issubset(env.keys())
    for key in expected_keys:
        assert isinstance(env[key], str)

    custom_env = {
        "os_name": "posix",
        "sys_platform": "linux",
        "platform_version": "#1 SMP",
        "platform_machine": "x86_64",
        "platform_python_implementation": "CPython",
        "python_version": "3.11",
        "python_full_version": "3.11.4",
        "implementation_version": "3.11.4",
    }
    for alias_expr in (
        'os.name == "posix"',
        'sys.platform == "linux"',
        'platform.version == "#1 SMP"',
        'platform.machine == "x86_64"',
        'platform.python_implementation == "CPython"',
        'python_implementation == "CPython"',
    ):
        res = evaluate_marker(alias_expr, env=custom_env)
        assert res == MarkerEvalResult(matched=True, error=None), alias_expr


def test_marker_pep440_version_comparisons_wildcards_and_compatible_release():
    env_39 = {"python_version": "3.9", "python_full_version": "3.9.18"}
    env_310 = {"python_version": "3.10", "python_full_version": "3.10.0"}
    env_311 = {"python_version": "3.11", "python_full_version": "3.11.4"}
    env_314_rc = {"implementation_version": "3.14.0c1"}

    # Numeric ordering ("3.9" < "3.10") and trailing-zero equivalence ("3.10" == "3.10.0").
    assert evaluate_marker('python_version < "3.10"', env=env_39).matched is True
    assert evaluate_marker('python_version >= "3.10"', env=env_39).matched is False
    assert evaluate_marker('python_version == "3.10.0"', env=env_310).matched is True
    assert evaluate_marker('"3.8" <= python_version', env=env_310).matched is True

    # Pre-release ordering including PEP 508 'c' alias for 'rc'.
    assert evaluate_marker('implementation_version < "3.14.0"', env=env_314_rc).matched is True
    assert evaluate_marker('implementation_version == "3.14.0rc1"', env=env_314_rc).matched is True
    assert evaluate_marker('implementation_version > "3.14.0b9"', env=env_314_rc).matched is True

    # Prefix wildcards .* on == and != (both operand orders).
    assert evaluate_marker('python_version == "3.11.*"', env=env_311).matched is True
    assert evaluate_marker('python_full_version == "3.11.*"', env=env_311).matched is True
    assert evaluate_marker('"3.11.*" == python_full_version', env=env_311).matched is True
    assert evaluate_marker('python_version != "3.11.*"', env=env_310).matched is True
    assert evaluate_marker('python_version == "3.11.*"', env=env_310).matched is False
    bad_wild = evaluate_marker('python_version >= "3.11.*"', env=env_311)
    assert bad_wild.matched is None and bad_wild.error

    # Compatible release ~= requires >=2 release segments.
    assert evaluate_marker('python_version ~= "3.8"', env=env_311).matched is True
    assert evaluate_marker('python_version ~= "3.12"', env=env_311).matched is False
    assert evaluate_marker('python_version ~= "3.8"', env={"python_version": "4.0"}).matched is False
    assert evaluate_marker('python_full_version ~= "3.11.2"', env=env_311).matched is True
    assert evaluate_marker('python_full_version ~= "3.11.5"', env=env_311).matched is False
    assert evaluate_marker('python_full_version ~= "3.10.2"', env=env_311).matched is False
    bad_compat = evaluate_marker('python_version ~= "3"', env=env_311)
    assert bad_compat.matched is None and bad_compat.error

    # Arbitrary equality === and substring in / not in.
    assert evaluate_marker('python_version === "3.11"', env=env_311).matched is True
    assert evaluate_marker('python_version === "3.11.0"', env=env_311).matched is False
    assert evaluate_marker('python_version in "3.8 3.9 3.10"', env=env_39).matched is True
    assert evaluate_marker('python_version in "3.8 3.9 3.10"', env=env_311).matched is False
    assert evaluate_marker('python_version not in "3.6 3.7"', env=env_311).matched is True

    # Malformed version literal degrades to matched=None rather than guessing.
    bad_ver = evaluate_marker('python_version >= "not-a-version"', env=env_311)
    assert bad_ver.matched is None and bad_ver.error
    bad_local = evaluate_marker('python_version >= "3.11+custom"', env=env_311)
    assert bad_local.matched is None and bad_local.error


def test_marker_boolean_precedence_and_extra_normalization():
    env = {"sys_platform": "linux", "python_version": "3.11"}

    # `and` binds tighter than `or`.
    expr_no_paren = 'sys_platform == "linux" or sys_platform == "darwin" and python_version < "2.0"'
    expr_paren = '(sys_platform == "linux" or sys_platform == "darwin") and python_version < "2.0"'
    assert evaluate_marker(expr_no_paren, env=env).matched is True
    assert evaluate_marker(expr_paren, env=env).matched is False

    # PEP 503 normalization for `extra` comparisons.
    assert evaluate_marker('extra == "dev_tools"', active_extra="dev-tools").matched is True
    assert evaluate_marker('"Fast.Mode" == extra', active_extra="fast_mode").matched is True
    assert evaluate_marker('extra == "dev"', active_extra="").matched is False
    assert evaluate_marker('extra in "dev test"', active_extra="").matched is False
    assert evaluate_marker('extra in "dev test"', active_extra="dev").matched is True

    # active_extras frozenset evaluation.
    assert (
        evaluate_marker(
            'extra == "fast-mode"',
            active_extras=frozenset({"slow", "Fast_Mode"}),
        ).matched
        is True
    )
    assert (
        evaluate_marker(
            'extra == "gpu"',
            active_extras=frozenset({"cpu", "fast"}),
        ).matched
        is False
    )


def test_marker_unparseable_and_unknown_syntax_never_raises():
    malformed_markers = [
        "",
        "   ",
        'unknown_var == "x"',
        'not (sys_platform == "win32")',
        'sys_platform = "linux"',
        'sys_platform == "linux',
        '(sys_platform == "linux"',
        'sys_platform == "linux")',
        'sys_platform == "linux" extra_token',
        'sys_platform ~= "linux"',
        "(" * 80 + 'os_name == "posix"' + ")" * 80,
    ]
    for expr in malformed_markers:
        res = evaluate_marker(expr)
        assert res.matched is None, f"Expected matched=None for {expr!r}, got {res}"
        assert isinstance(res.error, str) and res.error


def test_marker_evaluator_works_without_packaging_installed():
    """Verify _markers runs with zero third-party packages even when `packaging` is blocked."""
    src_dir = str(Path(__file__).resolve().parents[1] / "src")
    script = (
        "import sys\n"
        "class BlockPackaging:\n"
        "    def find_spec(self, fullname, path, target=None):\n"
        "        if fullname == 'packaging' or fullname.startswith('packaging.'):\n"
        "            raise ImportError('packaging blocked in stdlib-only test')\n"
        "        return None\n"
        "sys.meta_path.insert(0, BlockPackaging())\n"
        "from pubrun.capture._markers import parse_requirement, evaluate_marker\n"
        "req = parse_requirement('demo[Fast_Mode]>=1.0; python_version >= \"3.8\" and extra == \"fast-mode\"')\n"
        "assert req is not None and req.extras == ('fast-mode',)\n"
        "res = evaluate_marker(req.marker, active_extra='fast_mode')\n"
        "assert res.matched is True\n"
        "assert 'packaging' not in sys.modules\n"
    )
    sub_env = dict(os.environ)
    sub_env["PUBRUN_AUTO_START"] = "false"
    existing_pp = sub_env.get("PYTHONPATH")
    sub_env["PYTHONPATH"] = (
        f"{src_dir}{os.pathsep}{existing_pp}" if existing_pp else src_dir
    )
    proc = subprocess.run(
        [sys.executable, "-c", script],
        env=sub_env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, f"stderr={proc.stderr!r}\nstdout={proc.stdout!r}"


# ---------------------------------------------------------------------------
# E-02 / V-02 / E-03 / V-03: Recursive transitive closure in packages.py
# ---------------------------------------------------------------------------


def test_transitive_multi_hop_chain_and_pep503_normalization(tmp_path, monkeypatch):
    site_dir = tmp_path / "site_chain"
    _write_dist(
        site_dir,
        "synth-app-pkg",
        "1.0.0",
        top_levels=["synth_app_mod"],
        files={"synth_app_mod/__init__.py": "APP = 1\n"},
        requires=["Synth_Mid_Pkg>=1.0", "synth-side-pkg>=1.0"],
    )
    _write_dist(
        site_dir,
        "synth-mid-pkg",
        "2.0.0",
        top_levels=["synth_mid_mod"],
        files={"synth_mid_mod/__init__.py": "MID = 2\n"},
        requires=["Synth.Leaf.Pkg>=3.0"],
    )
    _write_dist(
        site_dir,
        "synth-side-pkg",
        "1.5.0",
        top_levels=["synth_side_mod"],
        files={"synth_side_mod/__init__.py": "SIDE = 1\n"},
        requires=["synth_leaf_pkg>=3.0"],
    )
    _write_dist(
        site_dir,
        "synth-leaf-pkg",
        "3.1.0",
        top_levels=["synth_leaf_mod"],
        files={"synth_leaf_mod/__init__.py": "LEAF = 3\n"},
    )
    monkeypatch.syspath_prepend(str(site_dir))
    _import_tracked(monkeypatch, "synth_app_mod")

    snap = pkgs.resolve_packages_snapshot(
        {"capture": {"packages": {"mode": "imported-transitive"}}}
    )
    app_rec = _find_record(snap, "synth-app-pkg")
    mid_rec = _find_record(snap, "synth-mid-pkg")
    side_rec = _find_record(snap, "synth-side-pkg")
    leaf_rec = _find_record(snap, "synth-leaf-pkg")

    assert app_rec is not None and app_rec["source"] == "imported"
    assert mid_rec is not None
    assert mid_rec["source"] == "transitive"
    assert mid_rec["required_by"] == ["synth-app-pkg"]
    assert side_rec is not None
    assert side_rec["source"] == "transitive"
    assert side_rec["required_by"] == ["synth-app-pkg"]
    assert leaf_rec is not None
    assert leaf_rec["source"] == "transitive"
    assert leaf_rec["required_by"] == ["synth-mid-pkg", "synth-side-pkg"]
    assert not any(
        u["module"].lower().startswith("synth") for u in snap["unresolved"]
    )


def test_transitive_direct_and_indirect_cycles_terminate_cleanly(tmp_path, monkeypatch):
    site_dir = tmp_path / "site_cycle"
    _write_dist(
        site_dir,
        "synth-cyc-a",
        "1.0.0",
        top_levels=["synth_cyc_a"],
        files={"synth_cyc_a/__init__.py": "A = 1\n"},
        requires=["synth-cyc-b>=1.0"],
    )
    _write_dist(
        site_dir,
        "synth-cyc-b",
        "1.0.0",
        top_levels=["synth_cyc_b"],
        files={"synth_cyc_b/__init__.py": "B = 2\n"},
        requires=["synth-cyc-a>=1.0"],
    )
    _write_dist(
        site_dir,
        "synth-self-pkg",
        "1.0.0",
        top_levels=["synth_self_pkg"],
        files={"synth_self_pkg/__init__.py": "S = 1\n"},
        requires=["synth_self_pkg>=1.0", "synth-self-pkg[loop]"],
    )
    monkeypatch.syspath_prepend(str(site_dir))
    _import_tracked(monkeypatch, "synth_cyc_a")
    _import_tracked(monkeypatch, "synth_self_pkg")

    snap = pkgs.resolve_packages_snapshot(
        {"capture": {"packages": {"mode": "imported-transitive"}}}
    )
    cyc_a = _find_record(snap, "synth-cyc-a")
    cyc_b = _find_record(snap, "synth-cyc-b")
    self_rec = _find_record(snap, "synth-self-pkg")

    assert cyc_a is not None and cyc_a["source"] == "imported"
    assert cyc_b is not None
    assert cyc_b["source"] == "transitive"
    assert cyc_b["required_by"] == ["synth-cyc-a"]
    assert self_rec is not None and self_rec["source"] == "imported"


def test_transitive_environment_markers_true_and_false(tmp_path, monkeypatch):
    site_dir = tmp_path / "site_markers"
    _write_dist(
        site_dir,
        "synth-marker-root",
        "1.0.0",
        top_levels=["synth_marker_root"],
        files={"synth_marker_root/__init__.py": "M = 1\n"},
        requires=[
            'synth-false-os>=1.0; sys_platform == "nonexistent_os"',
            'synth-false-py>=1.0; python_version < "2.0"',
            'synth-true-py>=1.0; python_version >= "3.8"',
            'synth-true-legacy>=1.0; sys.platform != "nonexistent_os"',
            'synth-true-url @ https://example.invalid/a;b=1.whl ; python_version ~= "3.8"',
            'synth-true-compound>=1.0; (sys_platform == "nonexistent_os" or python_version >= "3.8") and python_version != "2.7.*"',
        ],
    )
    for dep in (
        "synth-false-os",
        "synth-false-py",
        "synth-true-py",
        "synth-true-legacy",
        "synth-true-url",
        "synth-true-compound",
    ):
        _write_dist(site_dir, dep, "1.0.0")

    monkeypatch.syspath_prepend(str(site_dir))
    _import_tracked(monkeypatch, "synth_marker_root")

    index = pkgs._get_distribution_index(use_cache=False)
    root_rec = pkgs._record_from_dist_info(
        index.by_normalized_name["synth-marker-root"], source="imported"
    )
    trans_recs, trans_unresolved = pkgs._resolve_transitive_closure([root_rec], index)
    by_name = {r["name"]: r for r in trans_recs}

    assert trans_unresolved == []
    assert "synth-false-os" not in by_name
    assert "synth-false-py" not in by_name
    for expected in (
        "synth-true-py",
        "synth-true-legacy",
        "synth-true-url",
        "synth-true-compound",
    ):
        assert expected in by_name
        assert by_name[expected]["source"] == "transitive"
        assert by_name[expected]["required_by"] == ["synth-marker-root"]


def test_transitive_extra_honesty_and_parent_requested_extra_propagation(
    tmp_path, monkeypatch
):
    site_dir = tmp_path / "site_extras"
    _write_dist(
        site_dir,
        "synth-extra-root",
        "1.0.0",
        top_levels=["synth_extra_root"],
        files={"synth_extra_root/__init__.py": "E = 1\n"},
        requires=[
            'synth-opt-dev>=1.0; extra == "dev"',
            "synth-mid-extra[Fast_Mode]>=1.0",
        ],
    )
    _write_dist(
        site_dir,
        "synth-opt-dev",
        "1.0.0",
    )
    _write_dist(
        site_dir,
        "synth-mid-extra",
        "1.0.0",
        requires=[
            "synth-base-dep>=1.0",
            'synth-fast-dep>=1.0; extra == "fast-mode"',
            'synth-slow-dep>=1.0; extra == "slow"',
        ],
    )
    _write_dist(site_dir, "synth-base-dep", "1.0.0")
    _write_dist(site_dir, "synth-fast-dep", "1.0.0")
    _write_dist(site_dir, "synth-slow-dep", "1.0.0")

    monkeypatch.syspath_prepend(str(site_dir))
    _import_tracked(monkeypatch, "synth_extra_root")

    index = pkgs._get_distribution_index(use_cache=False)
    root_rec = pkgs._record_from_dist_info(
        index.by_normalized_name["synth-extra-root"], source="imported"
    )
    trans_recs, trans_unresolved = pkgs._resolve_transitive_closure([root_rec], index)
    by_name = {r["name"]: r for r in trans_recs}

    assert trans_unresolved == []
    assert "synth-opt-dev" not in by_name
    assert "synth-slow-dep" not in by_name
    assert by_name["synth-mid-extra"]["required_by"] == ["synth-extra-root"]
    assert by_name["synth-base-dep"]["required_by"] == ["synth-mid-extra"]
    assert by_name["synth-fast-dep"]["required_by"] == ["synth-mid-extra"]

    # Also verify full resolve_packages_snapshot excludes unrequested installed extras
    # and includes both base and parent-requested extras.
    snap = pkgs.resolve_packages_snapshot(
        {"capture": {"packages": {"mode": "imported-transitive"}}}
    )
    assert _find_record(snap, "synth-opt-dev") is None
    assert _find_record(snap, "synth-slow-dep") is None
    assert _find_record(snap, "synth-base-dep") is not None
    assert _find_record(snap, "synth-fast-dep") is not None
    assert snap["capture_state"]["status"] == "complete"


def test_transitive_missing_applicable_dependency_marks_partial(tmp_path, monkeypatch):
    site_dir = tmp_path / "site_missing"
    _write_dist(
        site_dir,
        "synth-missing-root",
        "1.0.0",
        top_levels=["synth_missing_root"],
        files={"synth_missing_root/__init__.py": "M = 1\n"},
        requires=[
            "synth-missing-dep>=1.0",
            'synth-false-missing>=1.0; sys_platform == "nonexistent_os"',
            'synth-extra-missing>=1.0; extra == "dev"',
        ],
    )
    monkeypatch.syspath_prepend(str(site_dir))
    _import_tracked(monkeypatch, "synth_missing_root")

    snap = pkgs.resolve_packages_snapshot(
        {"capture": {"packages": {"mode": "imported-transitive"}}}
    )
    assert snap["capture_state"]["status"] == "partial"

    missing_entries = [
        u for u in snap["unresolved"] if u["module"] == "synth-missing-dep"
    ]
    assert len(missing_entries) == 1
    entry = missing_entries[0]
    assert entry["reason"] == "missing_transitive_dependency"
    assert entry["candidates"] == []
    assert "synth-missing-root" in (entry.get("detail") or "")
    assert set(entry.keys()).issubset(
        {"module", "reason", "candidates", "observed_at", "detail"}
    )

    # False-marker and unrequested-extra missing deps are NOT flagged.
    assert not any(u["module"] == "synth-false-missing" for u in snap["unresolved"])
    assert not any(u["module"] == "synth-extra-missing" for u in snap["unresolved"])

    # get_packages() surfaces partial status + warning and remains schema-valid.
    pkg_out = pkgs.get_packages(
        {"capture": {"packages": {"mode": "imported-transitive"}}}
    )
    assert pkg_out["capture_state"]["status"] == "partial"
    assert any(
        "synth-missing-dep" in w and "missing_transitive_dependency" in w
        for w in pkg_out["capture_state"].get("warnings", [])
    )
    assert "unresolved" not in pkg_out


def test_transitive_unparseable_marker_and_requirement_mark_partial(
    tmp_path, monkeypatch
):
    site_dir = tmp_path / "site_unparseable"
    _write_dist(
        site_dir,
        "synth-weird-root",
        "1.0.0",
        top_levels=["synth_weird_root"],
        files={"synth_weird_root/__init__.py": "W = 1\n"},
        requires=[
            'synth-weird-var>=1.0; unknown_var == "x"',
            "synth-weird-syntax>=1.0; python_version ===",
            "synth_broken_req[unclosed",
            "synth-good-dep>=1.0",
        ],
    )
    _write_dist(site_dir, "synth-good-dep", "1.2.3")

    monkeypatch.syspath_prepend(str(site_dir))
    _import_tracked(monkeypatch, "synth_weird_root")

    snap = pkgs.resolve_packages_snapshot(
        {"capture": {"packages": {"mode": "imported-transitive"}}}
    )
    assert snap["capture_state"]["status"] == "partial"
    good_rec = _find_record(snap, "synth-good-dep")
    assert good_rec is not None
    assert good_rec["source"] == "transitive"
    assert good_rec["required_by"] == ["synth-weird-root"]

    by_mod = {u["module"]: u for u in snap["unresolved"]}
    for key in ("synth-weird-var", "synth-weird-syntax", "synth_broken_req[unclosed"):
        assert key in by_mod, f"Expected {key!r} in unresolved={snap['unresolved']}"
        assert by_mod[key]["reason"] == "unparseable_marker"
        assert by_mod[key]["candidates"] == []
        assert isinstance(by_mod[key].get("detail"), str) and by_mod[key]["detail"]
        assert set(by_mod[key].keys()).issubset(
            {"module", "reason", "candidates", "observed_at", "detail"}
        )


def test_transitive_no_import_invariant_and_default_mode(tmp_path, monkeypatch):
    site_dir = tmp_path / "site_no_import"
    sentinel = tmp_path / "transitive_imported.sentinel"
    payload = (
        f"from pathlib import Path\n"
        f"Path({str(sentinel)!r}).write_text('imported', encoding='utf-8')\n"
        f"raise AssertionError('transitive dependency must never be imported')\n"
    )
    _write_dist(
        site_dir,
        "synth-noimp-root",
        "1.0.0",
        top_levels=["synth_noimp_root"],
        files={"synth_noimp_root/__init__.py": "R = 1\n"},
        requires=["synth-noimp-dep>=1.0"],
    )
    _write_dist(
        site_dir,
        "synth-noimp-dep",
        "2.0.0",
        top_levels=["synth_noimp_dep"],
        files={"synth_noimp_dep/__init__.py": payload},
    )
    monkeypatch.syspath_prepend(str(site_dir))
    _import_tracked(monkeypatch, "synth_noimp_root")

    # Default mode must remain imported-only and exclude transitive-only deps.
    default_res = pkgs.get_packages({})
    assert default_res["mode"] == "imported-only"
    assert _find_record(default_res, "synth-noimp-root") is not None
    assert _find_record(default_res, "synth-noimp-dep") is None

    # imported-transitive discovers synth-noimp-dep without importing it.
    trans_res = pkgs.get_packages(
        {"capture": {"packages": {"mode": "imported-transitive"}}}
    )
    assert trans_res["mode"] == "imported-transitive"
    dep_rec = _find_record(trans_res, "synth-noimp-dep")
    assert dep_rec is not None
    assert dep_rec["source"] == "transitive"
    assert dep_rec["required_by"] == ["synth-noimp-root"]
    assert not sentinel.exists()
    assert "synth_noimp_dep" not in sys.modules
