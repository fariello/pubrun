"""Tests for pubrun.analysis.render -- diff rendering (inline fallback and color control)."""
import io
import math
import time
import sys
import pytest

from pubrun.analysis.render import (
    _format_array_diff,
    _has_color,
    _render_inline,
    _render_table,
    _summarize_change,
    print_diff,
)


class _FakeTty(io.StringIO):
    def isatty(self) -> bool:
        return True


class TestHasColor:
    """Tests for TTY-aware color detection logic delegated to report.output.use_color."""

    def test_no_color_flag_disables(self, monkeypatch):
        """Explicit no_color flag returns False even with FORCE_COLOR or TTY."""
        monkeypatch.setenv("FORCE_COLOR", "1")
        assert _has_color(no_color_flag=True, stream=_FakeTty()) is False

    def test_no_color_env_var_disables(self, monkeypatch):
        """NO_COLOR overrides FORCE_COLOR and TTY."""
        monkeypatch.setenv("NO_COLOR", "1")
        monkeypatch.setenv("FORCE_COLOR", "1")
        assert _has_color(no_color_flag=False, stream=_FakeTty()) is False

    def test_default_with_no_env_var(self, monkeypatch):
        """Non-TTY returns False; TTY or FORCE_COLOR=1 returns True."""
        monkeypatch.delenv("NO_COLOR", raising=False)
        monkeypatch.delenv("FORCE_COLOR", raising=False)
        assert _has_color(no_color_flag=False, stream=io.StringIO()) is False
        assert _has_color(no_color_flag=False, stream=_FakeTty()) is True
        monkeypatch.setenv("FORCE_COLOR", "1")
        assert _has_color(no_color_flag=False, stream=io.StringIO()) is True

    def test_no_color_env_empty_string(self, monkeypatch):
        """Empty NO_COLOR string does NOT disable color on a TTY or under FORCE_COLOR."""
        monkeypatch.setenv("NO_COLOR", "")
        monkeypatch.delenv("FORCE_COLOR", raising=False)
        assert _has_color(no_color_flag=False, stream=io.StringIO()) is False
        assert _has_color(no_color_flag=False, stream=_FakeTty()) is True
        monkeypatch.setenv("FORCE_COLOR", "1")
        assert _has_color(no_color_flag=False, stream=io.StringIO()) is True


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

    def test_renders_list_diff_basic_depth(self, capsys):
        """Under basic depth, list_diff outputs line-by-line added/removed items."""
        diff = {
            "added": {}, "removed": {},
            "modified": {"python.sys_path": {
                "type": "list_diff",
                "added": ["/path/c"],
                "removed": ["/path/a"],
                "order_changed": False,
                "old": ["/path/a", "/path/b"],
                "new": ["/path/b", "/path/c"]
            }},
            "same": {}
        }
        _render_inline(diff, use_color=False, depth="basic")
        output = capsys.readouterr().out
        assert "- /path/a" in output
        assert "+ /path/c" in output
        assert "[" not in output.split("python.sys_path:")[-1]

    def test_renders_list_diff_standard_depth_no_color(self, capsys):
        """Under standard depth without color, list_diff outputs the old/new array representation with prefixes."""
        diff = {
            "added": {}, "removed": {},
            "modified": {"python.sys_path": {
                "type": "list_diff",
                "added": ["/path/c"],
                "removed": ["/path/a"],
                "order_changed": False,
                "old": ["/path/a", "/path/b"],
                "new": ["/path/b", "/path/c"]
            }},
            "same": {}
        }
        _render_inline(diff, use_color=False, depth="standard")
        output = capsys.readouterr().out
        assert "- [-'/path/a', '/path/b']" in output
        assert "+ ['/path/b', +'/path/c']" in output

    def test_renders_list_diff_standard_depth_add_delete_rearrange(self, capsys):
        """Under standard depth, verify formatting when elements are added, deleted, and rearranged simultaneously."""
        diff = {
            "added": {}, "removed": {},
            "modified": {"python.sys_path": {
                "type": "list_diff",
                "added": ["/path/added"],
                "removed": ["/path/deleted"],
                "order_changed": True,
                "old": ["/path/deleted", "/path/a", "/path/b"],
                "new": ["/path/b", "/path/a", "/path/added"]
            }},
            "same": {}
        }
        _render_inline(diff, use_color=False, depth="standard")
        output = capsys.readouterr().out
        assert "- [-'/path/deleted', ~'/path/a', ~'/path/b']" in output
        assert "+ [~'/path/b', ~'/path/a', +'/path/added']" in output

    def test_renders_list_diff_standard_depth_with_color_and_rearrange(self, capsys):
        """Under standard depth with color, list_diff formats elements with ANSI and bold/yellow for rearranged ones."""
        diff = {
            "added": {}, "removed": {},
            "modified": {"python.sys_path": {
                "type": "list_diff",
                "added": [],
                "removed": [],
                "order_changed": True,
                "old": ["/path/a", "/path/b"],
                "new": ["/path/b", "/path/a"]
            }},
            "same": {}
        }
        _render_inline(diff, use_color=True, depth="standard")
        output = capsys.readouterr().out
        assert "\033[1m\033[93m~" in output


class TestPrintDiff:
    """Test that print_diff renders correctly."""

    def test_print_diff_renders_inline(self, capsys):
        """print_diff produces inline ANSI output."""
        diff = {"added": {"test.key": "value"}, "removed": {}, "modified": {}, "same": {}}
        print_diff(diff, no_color=True)
        output = capsys.readouterr().out
        assert "[ADDED] test.key: value" in output

    def test_print_diff_truncates_long_values(self, capsys):
        """Long values are truncated with [TRUNCATED] when wrap=False."""
        long_value = "x" * 500
        diff = {"added": {"key": long_value}, "removed": {}, "modified": {}, "same": {}}
        print_diff(diff, no_color=True, max_length=50, wrap=False)
        output = capsys.readouterr().out
        assert "[TRUNCATED]" in output
        assert "x" * 500 not in output

    def test_print_diff_wrap_preserves_full_value(self, capsys):
        """Long values are NOT truncated when wrap=True."""
        long_value = "x" * 500
        diff = {"added": {"key": long_value}, "removed": {}, "modified": {}, "same": {}}
        print_diff(diff, no_color=True, max_length=50, wrap=True)
        output = capsys.readouterr().out
        assert "[TRUNCATED]" not in output
        assert "x" * 500 in output

    def test_print_diff_shows_same_section(self, capsys):
        """The 'same' bucket is rendered when present."""
        diff = {"added": {}, "removed": {}, "modified": {}, "same": {"host.os": "Linux"}}
        print_diff(diff, no_color=True)
        output = capsys.readouterr().out
        assert "Unchanged" in output
        assert "host.os" in output


class TestRenderTableAndSummarize:
    """Tests for _summarize_change and _render_table."""

    def test_render_table_list_diff_reordered(self, capsys):
        diff = {
            "modified": {
                "pkgs": {
                    "type": "list_diff",
                    "added": ["a", "b"],
                    "removed": ["c"],
                    "order_changed": True,
                }
            }
        }
        _render_table(diff, use_color=False)
        lines = capsys.readouterr().out.splitlines()
        assert "~  pkgs   list [+2, -1, reordered]" in lines

    def test_summarize_change_truncation_and_empty_list_diff(self):
        assert _summarize_change({"type": "path_split", "added": ["a"] * 3}, 5) == "PATH  ..."
        assert _summarize_change({"type": "list_diff", "added": ["a"] * 3}, 5) == "list  ..."
        assert (
            _summarize_change({"type": "standard", "old": "abcdef", "new": "ghijkl"}, 10)
            == "abcdef  -> ..."
        )
        assert _summarize_change({"type": "list_diff"}, 300) == "list changed"

    def test_render_table_long_key_truncation_and_newline_flattening(self, capsys):
        diff = {"added": {"k" * 60: "a\nb"}}
        _render_table(diff, use_color=False)
        lines = capsys.readouterr().out.splitlines()
        assert len(lines) == 4
        assert lines[-1] == "+  " + ("k" * 47) + "\u2026  a b"

    def test_render_table_with_color(self, capsys):
        diff = {
            "added": {"y": 1},
            "removed": {"z": 0},
            "modified": {"x": {"type": "standard", "old": 1, "new": 2}},
            "same": {"w": 3},
        }
        _render_table(diff, use_color=True)
        output = capsys.readouterr().out
        lines = output.splitlines()
        assert "\x1b[1m   Field  Change\x1b[0m" in lines
        assert "\x1b[92m+\x1b[0m  y      \x1b[92m1\x1b[0m" in output
        assert "\x1b[93m~\x1b[0m  x      \x1b[93m1  ->  2\x1b[0m" in output
        assert "=  w      3" in lines
        assert "\x1b[2m" not in output

    def test_render_inline_emits_no_differences_and_zero_dim(self, capsys):
        diff_empty = {"added": {}, "removed": {}, "modified": {}, "same": {}}
        _render_inline(diff_empty, use_color=True)
        out_empty = capsys.readouterr().out
        assert "(no differences)" in out_empty.splitlines()
        assert "\x1b[2m" not in out_empty

        diff_same = {"added": {}, "removed": {}, "modified": {}, "same": {"host.os": "Linux"}}
        _render_inline(diff_same, use_color=True)
        out_same = capsys.readouterr().out
        assert "(no differences)" in out_same.splitlines()
        assert "--- Unchanged ---" in out_same
        assert "= host.os: Linux" in out_same
        assert "\x1b[2m" not in out_same

    def test_render_inline_list_diff_minus_before_plus(self, capsys):
        diff = {
            "added": {},
            "removed": {},
            "modified": {
                "python.sys_path": {
                    "type": "list_diff",
                    "added": ["/new"],
                    "removed": ["/old"],
                    "order_changed": False,
                    "old": ["/old", "/keep"],
                    "new": ["/keep", "/new"],
                }
            },
            "same": {},
        }
        for depth in ("standard", "deep"):
            _render_inline(diff, use_color=False, depth=depth)
            out = capsys.readouterr().out
            idx_minus = out.index("    - [-'/old', '/keep']")
            idx_plus = out.index("    + ['/keep', +'/new']")
            assert idx_minus < idx_plus

    def test_render_table_ascii_ellipsis_fallback(self, monkeypatch):
        raw = io.BytesIO()
        ascii_stream = io.TextIOWrapper(raw, encoding="ascii")
        monkeypatch.setattr(sys, "stdout", ascii_stream)
        diff = {"added": {"k" * 60: "val"}, "removed": {}, "modified": {}, "same": {}}
        _render_table(diff, use_color=False)
        ascii_stream.flush()
        text = raw.getvalue().decode("ascii")
        assert ("k" * 45) + "..." in text
        assert "\u2026" not in text

    def test_print_diff_suppresses_ansi_when_piped(self, capsys, monkeypatch):
        monkeypatch.delenv("NO_COLOR", raising=False)
        monkeypatch.delenv("FORCE_COLOR", raising=False)
        diff = {"added": {"k": "v"}, "removed": {}, "modified": {}, "same": {}}
        print_diff(diff, no_color=False)
        out = capsys.readouterr().out
        assert "\x1b[" not in out

    def test_format_array_diff_linear_scaling_and_nan(self):
        n = 2000
        common_a = [f"item_{i}" for i in range(n)]
        common_b = list(reversed(common_a))
        t0 = time.perf_counter()
        rendered = _format_array_diff(
            common_a + ["removed_item"],
            False,
            ["added_item"],
            ["removed_item"],
            common_a,
            common_b,
            use_color=False,
        )
        elapsed = time.perf_counter() - t0
        assert elapsed < 2.0, f"_format_array_diff took {elapsed:.2f}s for N={n}"
        assert "-'removed_item'" in rendered
        assert "~'item_0'" in rendered

        nan_val = float("nan")
        nan_out = _format_array_diff(
            [nan_val, "x"], False, [], [], [nan_val, "x"], [nan_val, "x"], use_color=False
        )
        assert "~nan" not in nan_out
        assert "nan" in nan_out
