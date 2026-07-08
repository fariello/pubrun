"""Central console-output helper: one consistent, accessible prefix vocabulary.

pubrun's CLI previously used ~8 inconsistent prefix styles (`[*]`, `[OK]`, `[ERRO]`,
`[WARN]`, `[WARNING]`, `[FAIL]`, lowercase `[warn]`/`[info]`, `[dry run]`) via duplicated
helpers and scattered ``print()`` calls. This module is the single source of truth.

Canonical prefixes (fixed 6-char bracket, left-aligned label):

    [INFO ]  informational / progress   (green)
    [WARN ]  warning                     (yellow)
    [ERROR]  error                       (red)
    [DEBUG]  debug (silent unless enabled) (bright blue)
    [ OK  ]  success                     (green)
    [FAIL ]  a self-test failure          (red)   -- distinct from [ERROR]

Accessibility: the TEXTUAL label is authoritative; color is optional reinforcement,
**never DIM**, and suppressed when ``NO_COLOR`` is set, ``--no-color`` was passed
(which sets ``NO_COLOR``), or the target stream is not a TTY. DEBUG never prints unless
``PUBRUN_DEBUG`` is set (or ``set_debug(True)`` is called), so a normal run is unchanged
apart from the prefix glyphs.

This module is CLI-facing only; it is not imported by ``import pubrun`` on the host path.
"""
import os
import sys
from typing import Optional, TextIO

# level -> (label shown in the bracket, ANSI SGR color code). Bright variants only (never
# code 2/DIM). "Light blue" for DEBUG = bright blue (94), high-contrast on dark + light.
_LEVELS = {
    "info":  ("INFO ", "32"),   # green
    "warn":  ("WARN ", "33"),   # yellow
    "error": ("ERROR", "31"),   # red
    "debug": ("DEBUG", "94"),   # bright blue
    "ok":    (" OK  ", "32"),   # green
    "fail":  ("FAIL ", "31"),   # red (self-test failure; distinct from error)
}

# Default stream per level (preserves pubrun's prior behavior): status/progress + errors go
# to stderr so stdout stays clean for data; success ("ok") historically printed to stdout.
_DEFAULT_STREAM = {
    "info":  "stderr",
    "warn":  "stderr",
    "error": "stderr",
    "debug": "stderr",
    "ok":    "stdout",
    "fail":  "stdout",
}

_debug_enabled: Optional[bool] = None


def set_debug(enabled: Optional[bool]) -> None:
    """Explicitly enable/disable DEBUG output (e.g. from a --debug flag). Pass ``None`` to
    revert to env-driven (``PUBRUN_DEBUG``)."""
    global _debug_enabled
    _debug_enabled = enabled


def debug_enabled() -> bool:
    if _debug_enabled is not None:
        return _debug_enabled
    return bool(os.environ.get("PUBRUN_DEBUG", ""))


def _use_color(stream: TextIO) -> bool:
    if os.environ.get("NO_COLOR", ""):
        return False
    try:
        return bool(stream.isatty())
    except Exception:
        return False


def _prefix(level: str, stream: TextIO) -> str:
    label, color = _LEVELS[level]
    if _use_color(stream):
        return f"\033[{color}m[{label}]\033[0m"
    return f"[{label}]"


def emit(level: str, message: str, stream: Optional[TextIO] = None) -> None:
    """Print ``message`` with the canonical prefix for ``level``.

    ``level`` is one of info/warn/error/debug/ok/fail. DEBUG is suppressed unless enabled.
    ``stream`` overrides the level's default stream (stdout/stderr).
    """
    if level == "debug" and not debug_enabled():
        return
    out: TextIO = stream if stream is not None else (
        sys.stdout if _DEFAULT_STREAM.get(level) == "stdout" else sys.stderr)
    print(f"{_prefix(level, out)} {message}", file=out)


def info(message: str, stream: Optional[TextIO] = None) -> None:
    emit("info", message, stream)


def warn(message: str, stream: Optional[TextIO] = None) -> None:
    emit("warn", message, stream)


def error(message: str, stream: Optional[TextIO] = None) -> None:
    emit("error", message, stream)


def debug(message: str, stream: Optional[TextIO] = None) -> None:
    emit("debug", message, stream)


def ok(message: str, stream: Optional[TextIO] = None) -> None:
    emit("ok", message, stream)


def fail(message: str, stream: Optional[TextIO] = None) -> None:
    emit("fail", message, stream)
