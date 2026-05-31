"""Tests for pubrun.analysis.render -- diff rendering (inline fallback and color control)."""
import os
import sys
import pytest

from pubrun.analysis.render import _has_color, _render_inline, print_diff


class TestHasColor:
    """Tests for color detection logic."""

    def test_no_color_flag_disables(self):
        """Explicit no_color flag returns False."""
        assert _has_color(no_color_flag=True) is False

    def test_no_color_env_var_disables(self, monkeypatch):
        """NO_COLOR environment variable disables color."""
        monkeypatch.setenv("NO_COLOR", "1")
        assert _has_color(no_color_flag=False) is False

    def test_default_with_no_env_var(self, monkeypatch):
        """Without NO_COLOR env var, returns True."""
        monkeypatch.delenv("NO_COLOR", raising=False)
        assert _has_color(no_color_flag=False) is True

    def test_no_color_env_empty_string(self, monkeypatch):
        """Empty NO_COLOR string does NOT disable (per spec: only non-empty)."""
        monkeypatch.setenv("NO_COLOR", "")
        assert _has_color(no_color_flag=False) is True


class TestRenderInline:
    """Tests for the plain-text diff renderer (no-rich fallback)."""

    def test_renders_added_keys(self, capsys):
        """Added keys appear with + prefix."""
        diff = {"added": {"host.hostname": "server1"}, "removed": {}, "modified": {}, "same": {}}
        _render_inline(diff, use_color=False)
        output = capsys.readouterr().out
        assert "+ [ADDED] host.hostname: server1" in output

    def test_renders_removed_keys(self, capsys):
        """Removed keys appear with - prefix."""
        diff = {"added": {}, "removed": {"git.branch": "main"}, "modified": {}, "same": {}}
        _render_inline(diff, use_color=False)
        output = capsys.readouterr().out
        assert "- [REMOVED] git.branch: main" in output

    def test_renders_modified_keys(self, capsys):
        """Modified keys show old and new values."""
        diff = {
            "added": {}, "removed": {},
            "modified": {"python.version": {"type": "value", "old": "3.10", "new": "3.11"}},
            "same": {}
        }
        _render_inline(diff, use_color=False)
        output = capsys.readouterr().out
        assert "[CHANGED] python.version" in output
        assert "- 3.10" in output
        assert "+ 3.11" in output

    def test_renders_path_split(self, capsys):
        """Path-split diffs show added/removed segments."""
        diff = {
            "added": {}, "removed": {},
            "modified": {"environment.PATH": {
                "type": "path_split",
                "added": ["/opt/new"],
                "removed": ["/opt/old"],
            }},
            "same": {}
        }
        _render_inline(diff, use_color=False)
        output = capsys.readouterr().out
        assert "+ /opt/new" in output
        assert "- /opt/old" in output

    def test_color_output_includes_ansi(self, capsys):
        """With use_color=True, output includes ANSI escape codes."""
        diff = {"added": {"x": "y"}, "removed": {}, "modified": {}, "same": {}}
        _render_inline(diff, use_color=True)
        output = capsys.readouterr().out
        assert "\033[92m" in output  # GREEN
        assert "\033[0m" in output   # RESET

    def test_empty_diff_renders_header(self, capsys):
        """An empty diff still renders the header line."""
        diff = {"added": {}, "removed": {}, "modified": {}, "same": {}}
        _render_inline(diff, use_color=False)
        output = capsys.readouterr().out
        assert "Pubrun Diagnostic Difference" in output


class TestPrintDiffFallback:
    """Test that print_diff falls back to _render_inline when rich is unavailable."""

    def test_falls_back_without_rich(self, capsys, monkeypatch):
        """When rich cannot be imported, print_diff uses inline rendering."""
        # Force ImportError for rich modules
        import builtins
        original_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if name.startswith("rich"):
                raise ImportError("mocked: rich not installed")
            return original_import(name, *args, **kwargs)

        monkeypatch.setattr(builtins, "__import__", mock_import)

        diff = {"added": {"test.key": "value"}, "removed": {}, "modified": {}, "same": {}}
        print_diff(diff, no_color=True)
        output = capsys.readouterr().out
        assert "pip install rich" in output
        assert "[ADDED] test.key: value" in output
