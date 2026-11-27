"""Tests for IPD-B: the central output helper + alphabetized help command list."""
import io
import os
import sys
import subprocess

import pytest

from pubrun.report import output as out

PYTHON = sys.executable


class TestPrefixes:
    def _capture(self, level, message, monkeypatch, no_color=True, tty=False):
        buf = io.StringIO()
        buf.isatty = lambda: tty  # type: ignore[attr-defined]
        if no_color:
            monkeypatch.setenv("NO_COLOR", "1")
        else:
            monkeypatch.delenv("NO_COLOR", raising=False)
        out.emit(level, message, stream=buf)
        return buf.getvalue()

    def test_canonical_labels_no_color(self, monkeypatch):
        assert self._capture("info", "x", monkeypatch) == "[INFO ] x\n"
        assert self._capture("warn", "x", monkeypatch) == "[WARN ] x\n"
        assert self._capture("error", "x", monkeypatch) == "[ERROR] x\n"
        assert self._capture("ok", "x", monkeypatch) == "[ OK  ] x\n"
        assert self._capture("fail", "x", monkeypatch) == "[FAIL ] x\n"

    def test_no_ansi_when_no_color(self, monkeypatch):
        # NO_COLOR set + even a "tty" stream => no ANSI, but the textual label remains.
        s = self._capture("warn", "x", monkeypatch, no_color=True, tty=True)
        assert "\033[" not in s and "[WARN ]" in s

    def test_ansi_when_tty_and_color_allowed(self, monkeypatch):
        s = self._capture("info", "x", monkeypatch, no_color=False, tty=True)
        assert "\033[32m" in s and "[INFO ]" in s  # green, non-DIM

    def test_no_ansi_when_not_a_tty(self, monkeypatch):
        # Piped output (isatty False) never colors unless FORCE_COLOR is set.
        monkeypatch.delenv("FORCE_COLOR", raising=False)
        s = self._capture("info", "x", monkeypatch, no_color=False, tty=False)
        assert "\033[" not in s

    def test_debug_color_is_bright_not_dim(self, monkeypatch):
        monkeypatch.setattr(out, "_debug_enabled", True)
        s = self._capture("debug", "x", monkeypatch, no_color=False, tty=True)
        assert "\033[94m" in s  # bright blue, never code 2 (DIM)
        assert "\033[2m" not in s


class TestUseColorPolicy:
    def _stream(self, tty: bool):
        buf = io.StringIO()
        buf.isatty = lambda: tty  # type: ignore[attr-defined]
        return buf

    def test_force_no_color_wins_over_everything(self, monkeypatch):
        monkeypatch.delenv("NO_COLOR", raising=False)
        monkeypatch.setenv("FORCE_COLOR", "1")
        assert out.use_color(self._stream(True), force_no_color=True) is False

    def test_no_color_overrides_force_color_and_tty(self, monkeypatch):
        monkeypatch.setenv("NO_COLOR", "1")
        monkeypatch.setenv("FORCE_COLOR", "1")
        assert out.use_color(self._stream(True)) is False
        assert out.use_color(self._stream(False)) is False

    def test_force_color_enables_ansi_on_non_tty(self, monkeypatch):
        monkeypatch.delenv("NO_COLOR", raising=False)
        monkeypatch.setenv("FORCE_COLOR", "1")
        assert out.use_color(self._stream(False)) is True

    def test_force_color_zero_does_not_force_on_non_tty(self, monkeypatch):
        monkeypatch.delenv("NO_COLOR", raising=False)
        monkeypatch.setenv("FORCE_COLOR", "0")
        assert out.use_color(self._stream(False)) is False
        assert out.use_color(self._stream(True)) is True

    def test_isatty_default_and_error_fallback(self, monkeypatch):
        monkeypatch.delenv("NO_COLOR", raising=False)
        monkeypatch.delenv("FORCE_COLOR", raising=False)
        assert out.use_color(self._stream(True)) is True
        assert out.use_color(self._stream(False)) is False

        class BrokenStream(io.StringIO):
            def isatty(self):
                raise OSError("closed")

        assert out.use_color(BrokenStream()) is False


class TestDebugGate:
    def test_debug_silent_by_default(self, monkeypatch):
        monkeypatch.setattr(out, "_debug_enabled", None)
        monkeypatch.delenv("PUBRUN_DEBUG", raising=False)
        buf = io.StringIO()
        buf.isatty = lambda: False  # type: ignore[attr-defined]
        out.debug("should not appear", stream=buf)
        assert buf.getvalue() == ""

    def test_debug_shown_when_env_set(self, monkeypatch):
        monkeypatch.setattr(out, "_debug_enabled", None)
        monkeypatch.setenv("PUBRUN_DEBUG", "1")
        buf = io.StringIO()
        buf.isatty = lambda: False  # type: ignore[attr-defined]
        out.debug("visible", stream=buf)
        assert "[DEBUG] visible" in buf.getvalue()

    def test_set_debug_overrides_env(self, monkeypatch):
        monkeypatch.setenv("PUBRUN_DEBUG", "1")
        out.set_debug(False)
        try:
            buf = io.StringIO()
            buf.isatty = lambda: False  # type: ignore[attr-defined]
            out.debug("x", stream=buf)
            assert buf.getvalue() == ""
        finally:
            out.set_debug(None)  # reset to env-driven


class TestStreams:
    def test_default_streams_preserved(self, capsys, monkeypatch):
        # info/warn/error/debug default to stderr; ok/fail default to stdout.
        monkeypatch.setenv("NO_COLOR", "1")
        monkeypatch.setattr(out, "_debug_enabled", True)
        out.info("info-msg")
        out.warn("warn-msg")
        out.error("error-msg")
        out.debug("debug-msg")
        out.ok("ok-msg")
        out.fail("fail-msg")
        captured = capsys.readouterr()
        for msg in ("info-msg", "warn-msg", "error-msg", "debug-msg"):
            assert msg in captured.err
            assert msg not in captured.out
        for msg in ("ok-msg", "fail-msg"):
            assert msg in captured.out
            assert msg not in captured.err


class TestHelpOrdering:
    def test_command_list_is_alphabetical(self):
        res = subprocess.run([PYTHON, "-m", "pubrun", "-h"], capture_output=True, text=True, timeout=30)
        assert res.returncode == 0
        # Command lines are indented EXACTLY 4 spaces then a word; help-text continuation
        # lines are indented deeper (>=8 spaces), so match on exactly-4-space indent.
        import re
        cmds = []
        in_section = False
        for line in res.stdout.splitlines():
            if "Available core commands" in line:
                in_section = True
                continue
            if in_section and line.strip().startswith("Use '"):
                break
            m = re.match(r"^ {4}([a-z][a-z0-9-]*)(?: |$|\()", line)
            if in_section and m:
                cmds.append(m.group(1))
        assert cmds, "no commands parsed from -h"
        assert cmds == sorted(cmds), f"help commands not alphabetical: {cmds}"
        assert "report" not in cmds  # hidden alias stays hidden
