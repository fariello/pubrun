"""Tests for multi-run `pubrun methods --all` (IPD 20260706-methods-multi-run).

Option C: aggregate the filtered run set into ONE representative methods
paragraph plus a variance note when fields differ; when the runs are
environment-homogeneous the output reads exactly like the single-run methods.

`TestSingleRunParity` is the Step-1 characterization gate: single-run output must
not change. Written FIRST; green before and after the feature.
"""
import json

import pytest

from pubrun.report.methods import generate_report


def _manifest(**over):
    """A representative manifest; override individual fields per test."""
    m = {
        "run": {"library_version": "1.3.1", "library_commit": "0123456789abcdef"},
        "host": {"os_name": "Ubuntu_Linux"},
        "hardware": {"cpu": {"model": "Intel Core i7"},
                     "memory_total_bytes": 16 * 1024 ** 3},
        "python": {"version": "3.11.4 final", "implementation": "cpython"},
        "git": {"commit": "abcdef1234567890"},
        "packages": {"records": [{"name": "numpy", "version": "1.21.0"}]},
    }
    for k, v in over.items():
        # shallow section override, e.g. python={"version": "..."}
        if isinstance(v, dict) and isinstance(m.get(k), dict):
            m[k] = {**m[k], **v}
        else:
            m[k] = v
    return m


# ---------------------------------------------------------------------------
# Step 1: single-run parity characterization gate
# ---------------------------------------------------------------------------

class TestSingleRunParity:
    """Single-run methods output must not change when the multi-run path lands."""

    def test_single_run_markdown_unchanged(self):
        m = _manifest()
        r = generate_report(m, "markdown")
        assert "Ubuntu_Linux" in r
        assert "Intel Core i7" in r
        assert "Python 3.11.4" in r
        assert "numpy (v1.21.0)" in r
        assert "abcdef12" in r
        assert "pubrun v1.3.1" in r
        assert "Computational Methods" in r

    def test_aggregate_of_one_equals_single(self):
        """generate_report_multi over exactly one manifest == single-run output."""
        pytest.importorskip("pubrun.report.methods")
        from pubrun.report.methods import generate_report_multi
        m = _manifest()
        assert generate_report_multi([m], "markdown") == generate_report(m, "markdown")
        assert generate_report_multi([m], "latex") == generate_report(m, "latex")


# ---------------------------------------------------------------------------
# generate_report_multi (option C)
# ---------------------------------------------------------------------------

class TestAggregateGenerator:
    def test_empty_raises(self):
        from pubrun.report.methods import generate_report_multi
        with pytest.raises(ValueError):
            generate_report_multi([], "markdown")

    def test_homogeneous_reads_like_single_plus_count(self):
        from pubrun.report.methods import generate_report_multi
        ms = [_manifest(), _manifest(), _manifest()]
        r = generate_report_multi(ms, "markdown")
        # Representative content present, run count noted, NO variance section.
        assert "Ubuntu_Linux" in r
        assert "across 3 runs" in r
        assert "Environment variation" not in r

    def test_heterogeneous_notes_variance(self):
        from pubrun.report.methods import generate_report_multi
        ms = [
            _manifest(python={"version": "3.11.7 final"}),
            _manifest(python={"version": "3.11.4 final"}),
            _manifest(host={"os_name": "Rocky_Linux"}),
        ]
        r = generate_report_multi(ms, "markdown")
        assert "Environment variation across the aggregated runs" in r
        # Python variance disclosed (sorted distinct)
        assert "Python:" in r
        assert "3.11.4" in r and "3.11.7" in r
        # OS variance disclosed
        assert "Operating system:" in r

    def test_differing_git_commit_is_noted_not_refused(self):
        from pubrun.report.methods import generate_report_multi
        ms = [
            _manifest(git={"commit": "aaaaaaaa1111"}),
            _manifest(git={"commit": "bbbbbbbb2222"}),
        ]
        r = generate_report_multi(ms, "markdown")  # must not raise
        assert "Git commit:" in r
        assert "aaaaaaaa" in r and "bbbbbbbb" in r

    def test_deterministic(self):
        from pubrun.report.methods import generate_report_multi
        ms = [
            _manifest(python={"version": "3.11.7 final"}),
            _manifest(python={"version": "3.10.2 final"}),
        ]
        assert generate_report_multi(ms, "markdown") == generate_report_multi(ms, "markdown")

    def test_latex_variance_is_commented_out(self):
        from pubrun.report.methods import generate_report_multi
        ms = [_manifest(host={"os_name": "A_Linux"}), _manifest(host={"os_name": "B_Linux"})]
        r = generate_report_multi(ms, "latex")
        # Variance note lines are LaTeX comments so they never render into the doc.
        assert "% Environment varied" in r


# ---------------------------------------------------------------------------
# CLI: methods --all end-to-end + non-methods note
# ---------------------------------------------------------------------------

class TestMethodsAllCli:
    def _make_run(self, runs_dir, name, manifest):
        d = runs_dir / name
        d.mkdir(parents=True)
        (d / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
        return d

    def test_all_aggregates_and_notes_variance(self, tmp_path, monkeypatch, capsys):
        monkeypatch.setattr("pathlib.Path.cwd", lambda: tmp_path)
        runs = tmp_path / "runs"
        self._make_run(runs, "pubrun-x-20260101T000000Z-1-aaaa1111",
                       _manifest(python={"version": "3.11.7 final"}))
        self._make_run(runs, "pubrun-x-20260101T000100Z-2-bbbb2222",
                       _manifest(python={"version": "3.11.4 final"}))
        from pubrun.__main__ import _run_methods
        _run_methods("", "markdown", aggregate=True)
        out = capsys.readouterr().out
        assert "Computational Methods" in out
        assert "across 2 runs" in out

    def test_note_is_marked_and_outside_methods_under_no_color(self, tmp_path, monkeypatch, capsys):
        monkeypatch.setenv("NO_COLOR", "1")
        monkeypatch.setattr("pathlib.Path.cwd", lambda: tmp_path)
        runs = tmp_path / "runs"
        # >25 runs to trigger the "narrow it" note; one malformed to trigger skip note
        for i in range(27):
            self._make_run(runs, f"pubrun-x-2026010{i%9}T00000{i%9}Z-{i}-id{i:04d}", _manifest())
        bad = runs / "pubrun-bad-20260101T000000Z-99-badbad99"
        bad.mkdir(parents=True)
        (bad / "manifest.json").write_text("{ not valid json", encoding="utf-8")
        from pubrun.__main__ import _run_methods
        _run_methods("", "markdown", aggregate=True)
        captured = capsys.readouterr()
        # The note is on stderr, marked, and NOT in the methods (stdout) text.
        assert "not part of the methods section" in captured.err
        assert "\033[" not in captured.err  # no ANSI codes under NO_COLOR
        assert "not part of the methods section" not in captured.out
