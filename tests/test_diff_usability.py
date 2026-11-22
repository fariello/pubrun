"""Tests for IPD-A: `pubrun diff` usability — meaningful --basic, redundant-field collapse,
list summarization, and the optional --table renderer."""
import io
import contextlib

import pytest

from pubrun.analysis.diff import compare_manifests, _normalize_manifest
from pubrun.analysis.render import print_diff
from pubrun.config import resolve_config


def _ignores(depth):
    conf = resolve_config().get("diff", {})
    return conf.get({"basic": "ignore_basic", "standard": "ignore_standard",
                     "deep": "ignore_deep"}[depth], [])


def _mk(argv, nsub=0, extra=None, **extra_top):
    subs = [{"argv": ["python", "worker.py"], "exit_code": 0} for _ in range(nsub)]
    for e in (extra or []):
        subs.append(e)
    m = {
        "invocation": {"argv": argv, "command_line": " ".join(argv),
                       "rerun_command": "cd /x && " + " ".join(argv)},
        "filesystem": {"run_dir": {"path": "/runs/whatever", "fstype": "ext4",
                                   "is_network": False}},
        "subprocesses": subs,
        "packages": {"records": [{"name": "numpy", "version": "1.0"}]},
        "python": {"version": "3.14"},
    }
    m.update(extra_top)
    return m


class TestRedundantInvocationCollapse:
    def test_argv_change_reported_once_at_basic(self):
        a = _mk(["python", "train.py"])
        b = _mk(["python", "train.py", "--max-spend", "1"])
        r = compare_manifests(a, b, _ignores("basic"), depth="basic")
        changed = list(r["modified"])
        assert changed == ["invocation.argv"]  # exactly one, not 3
        assert "invocation.command_line" not in r["modified"]
        assert "invocation.rerun_command" not in r["modified"]

    def test_deep_still_shows_derived_views(self):
        a = _mk(["python", "train.py"])
        b = _mk(["python", "train.py", "--max-spend", "1"])
        r = compare_manifests(a, b, _ignores("deep"), depth="deep")
        assert "invocation.command_line" in r["modified"]
        assert "invocation.rerun_command" in r["modified"]


class TestVolatilePathsHidden:
    def test_run_dir_path_hidden_but_fstype_visible(self):
        a = _mk(["python", "x"], filesystem={"run_dir": {"path": "/runs/A", "fstype": "ext4", "is_network": False}})
        b = _mk(["python", "x"], filesystem={"run_dir": {"path": "/runs/B", "fstype": "nfs4", "is_network": True}})
        for depth in ("basic", "standard"):
            r = compare_manifests(a, b, _ignores(depth), depth=depth)
            keys = set(r["added"]) | set(r["removed"]) | set(r["modified"])
            assert "filesystem.run_dir.path" not in keys  # volatile path hidden
            # the meaningful fstype/network change is still surfaced
            assert any("fstype" in k or "is_network" in k for k in keys), keys


class TestListBlowupCap:
    def test_basic_is_tiny_for_subprocess_heavy_runs(self):
        a = _mk(["python", "x"], nsub=300)
        b = _mk(["python", "x"], nsub=300,
                extra=[{"argv": ["bash", "-c", "echo hi"], "exit_code": 0}] * 2)
        r = compare_manifests(a, b, _ignores("basic"), depth="basic")
        total = len(r["added"]) + len(r["removed"]) + len(r["modified"])
        assert total == 0  # identical argv/env/pkgs -> basic shows nothing (subprocs hidden)

    def test_standard_summarizes_subprocesses(self):
        a = _mk(["python", "x"], nsub=300)
        b = _mk(["python", "x"], nsub=300,
                extra=[{"argv": ["bash", "-c", "echo hi"], "exit_code": 0}] * 2)
        r = compare_manifests(a, b, _ignores("standard"), depth="standard")
        keys = set(r["added"]) | set(r["modified"])
        # count delta + per-identity, NOT thousands of per-element leaves
        assert "subprocesses.count" in keys
        assert "subprocesses.by_command.bash" in keys
        assert not any(k.startswith("subprocesses.0") or k.startswith("subprocesses.1") for k in keys)
        total = len(r["added"]) + len(r["removed"]) + len(r["modified"])
        assert total < 20  # bounded, not 11,000+

    def test_deep_shows_full_subprocess_detail(self):
        a = _mk(["python", "x"], nsub=2)
        b = _mk(["python", "x"], nsub=3)
        r = compare_manifests(a, b, _ignores("deep"), depth="deep")
        keys = set(r["added"]) | set(r["modified"])
        # deep flattens element-by-element
        assert any(k.startswith("subprocesses.2") for k in keys)
        assert "subprocesses.count" not in keys  # no summary at deep


class TestIgnoreMonotonicity:
    def test_basic_hides_at_least_standard(self):
        # basic must hide everything standard hides (basic >= standard in hiding).
        conf = resolve_config().get("diff", {})
        basic = set(conf.get("ignore_basic", []))
        standard = set(conf.get("ignore_standard", []))
        assert standard <= basic, standard - basic
        assert conf.get("ignore_deep", []) == []  # deep hides nothing


class TestTableRenderer:
    def _render(self, report, **kw):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            print_diff(report, no_color=True, **kw)
        return buf.getvalue()

    def _report(self):
        return {"added": {"subprocesses.by_command.bash": 2}, "removed": {},
                "modified": {"subprocesses.count": {"type": "standard", "old": 300, "new": 302}},
                "same": {}}

    def test_inline_is_default(self):
        out = self._render(self._report())
        assert "[ADDED]" in out or "[CHANGED]" in out  # git-style default

    def test_table_opt_in(self):
        out = self._render(self._report(), table=True)
        assert "Field" in out and "Change" in out
        assert "->" in out  # the A -> B cell
        assert "[ADDED]" not in out  # not the inline format

    def test_table_content_matches_inline_changeset(self):
        # Same set of changed keys appear in both renderings.
        report = self._report()
        inline = self._render(report)
        table = self._render(report, table=True)
        for key in ("subprocesses.by_command.bash", "subprocesses.count"):
            assert key in inline and key in table

    def test_note_renders_in_inline_and_table_modes(self):
        report = {
            "added": {},
            "removed": {},
            "modified": {
                "timing.elapsed_seconds": {
                    "type": "standard",
                    "old": 45.5,
                    "new": 12.0,
                    "note": "timing definition changed (wall_clock_legacy/wall_clock -> workload/monotonic)",
                }
            },
            "same": {},
        }
        inline = self._render(report)
        table = self._render(report, table=True)
        expected_note = "timing definition changed (wall_clock_legacy/wall_clock -> workload/monotonic)"
        assert f"note: {expected_note}" in inline
        assert f"[{expected_note}]" in table
        assert "\033[" not in inline and "\033[" not in table


class TestTimingSemanticsDiff:
    def test_deep_diff_surfaces_legacy_vs_monotonic_note_and_metadata(self):
        legacy = _mk(
            ["python", "train.py"],
            timing={"started_at_utc": 1780250000.0, "ended_at_utc": 1780250010.0, "elapsed_seconds": 10.0},
        )
        new_m = _mk(
            ["python", "train.py"],
            timing={
                "started_at_utc": 1780250000.0,
                "ended_at_utc": 1780250008.0,
                "elapsed_seconds": 8.0,
                "workload_seconds": 8.0,
                "duration_clock": "monotonic",
                "elapsed_basis": "workload",
            },
        )
        # Default basic/standard still ignore timing
        for depth in ("basic", "standard"):
            r_def = compare_manifests(legacy, new_m, _ignores(depth), depth=depth)
            assert not any(k.startswith("timing") for k in set(r_def["added"]) | set(r_def["removed"]) | set(r_def["modified"]))

        # Deep diff includes timing and surfaces the definition change explicitly
        r_deep = compare_manifests(legacy, new_m, _ignores("deep"), depth="deep")
        assert r_deep["modified"]["timing.elapsed_seconds"]["note"] == (
            "timing definition changed (wall_clock_legacy/wall_clock -> workload/monotonic)"
        )
        assert r_deep["modified"]["timing.duration_clock"]["old"] == "wall_clock"
        assert r_deep["modified"]["timing.duration_clock"]["new"] == "monotonic"
        assert r_deep["modified"]["timing.elapsed_basis"]["old"] == "wall_clock_legacy"
        assert r_deep["modified"]["timing.elapsed_basis"]["new"] == "workload"
