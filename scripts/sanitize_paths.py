#!/usr/bin/env python3
"""Sanitize absolute home paths, hostnames, and (optionally) IPs from files.

Two modes:
  --check   scan and REPORT (one consolidated summary at the end), exit non-zero on any
            un-whitelisted match. Never mutates. This is the pre-commit / CI mode.
  --fix     rewrite matches in place (and re-stage when run against staged files).

Design notes (see .agents/plans/.../20260720-2331-01-path-hostname-sanitizer-hook.md):
  - Rules are ANCHORED on the /home/<user> path prefix, so they never match a bare
    username token that legitimately appears as an author name or email. Preserving
    author identity is a hard invariant.
  - The IP ruleset is config-gated OFF by default: v4/v6 regexes false-positive on
    version numbers, timings, and hashes, which would block nearly every commit.
  - Needles (the current user's home, the machine hostname) are read at RUNTIME; no
    literal hostname/home path is baked into this tracked file.
  - stdlib only.

Config: .sanitize-local.toml (gitignored). See .sanitize-local.toml.example.
"""
from __future__ import annotations

import argparse
import fnmatch
import getpass
import os
import re
import socket
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

try:  # Python 3.11+
    import tomllib as _toml
except ModuleNotFoundError:  # pragma: no cover - exercised on 3.8-3.10
    try:
        import tomli as _toml  # type: ignore
    except ModuleNotFoundError:  # pragma: no cover
        _toml = None  # config simply unavailable; defaults apply


DEFAULT_RULESETS = ("home-user", "home-any", "hostname")
ALL_RULESETS = ("home-user", "home-any", "hostname", "ip")

# /home/<user>/... and /Users/<user>/... (macOS), anchored on the home-dir shape.
# Matches the FULL path (including subdirs) so both the replacement and any whitelist
# rule operate on the complete path, not just the /home/<user> head. The <user> label
# is required (so a bare "/home" or "/home/" alone does not match), which is what keeps
# it anchored on a real home directory. Group 1 captures the tail after the user so the
# replacement can keep it (`~` + tail).
_HOME_ANY_RE = re.compile(
    r"(?:/home|/Users)/[A-Za-z0-9_][A-Za-z0-9_.-]*((?:/[A-Za-z0-9_.+-]+)*)"
)
# IPv4 (each octet 0-255) and IPv6 (RFC 4291 full and "::"-compressed text forms).
_IPV4_RE = re.compile(
    r"\b(?:(?:25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)\.){3}(?:25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)\b"
)
_H16 = r"[0-9A-Fa-f]{1,4}"
# The look-arounds reject a match glued to an identifier or another colon, so
# `module::Symbol`, `a::b::c`, and bare `::` never match. Every alternative is either the
# full 8-group form or contains exactly one "::", so `12:34:56` timestamps never match.
_IPV6_RE = re.compile(
    r"(?<![A-Za-z0-9_:])(?:"
    rf"(?:{_H16}:){{7}}{_H16}"
    rf"|(?:{_H16}:){{1,7}}:"
    rf"|(?:{_H16}:){{1,6}}:{_H16}"
    rf"|(?:{_H16}:){{1,5}}(?::{_H16}){{1,2}}"
    rf"|(?:{_H16}:){{1,4}}(?::{_H16}){{1,3}}"
    rf"|(?:{_H16}:){{1,3}}(?::{_H16}){{1,4}}"
    rf"|(?:{_H16}:){{1,2}}(?::{_H16}){{1,5}}"
    rf"|{_H16}:(?::{_H16}){{1,6}}"
    rf"|:(?::{_H16}){{1,7}}"
    r")(?![A-Za-z0-9_:])"
)
# Inline glob translation: `*` stops at whitespace and common delimiters so a blacklist
# glob scrubs one token mid-line instead of running to the end of the line.
_GLOB_STAR = r"""[^\s"'`()\[\]{}<>,;]*"""


@dataclass
class Rule:
    name: str
    pattern: re.Pattern
    replace: str


@dataclass
class Config:
    enabled: list = field(default_factory=lambda: list(DEFAULT_RULESETS))
    ip_enabled: bool = False
    whitelist: list = field(default_factory=list)  # list of (kind, pattern, _)
    blacklist: list = field(default_factory=list)  # list of (kind, pattern, replace)
    exclude: list = field(default_factory=list)    # list of (kind, pattern, _) - skip file


def _entry_list(raw):
    out = []
    for item in raw or []:
        if isinstance(item, str):
            out.append(("glob", item, "<redacted>"))
        elif isinstance(item, dict):
            out.append(
                (item.get("type", "glob"), item.get("pattern", ""), item.get("replace", "<redacted>"))
            )
    return out


def load_config(repo_root: Path) -> Config:
    """Load config from two layers, both optional:

    - `.sanitize-allow.toml` (TRACKED): a committed baseline allow/block list that
      travels with the repo, so CI (which has no local config) shares the same
      known-legitimate exceptions, e.g. generic placeholder paths in test fixtures.
    - `.sanitize-local.toml` (GITIGNORED): machine-specific additions.

    `rules.enabled` / `ip.enabled` from the local file win; whitelist/blacklist entries
    from both files are merged (allow is a union, which is the safe direction).
    """
    cfg = Config()
    if _toml is None:
        return cfg
    for name in (".sanitize-allow.toml", ".sanitize-local.toml"):
        path = repo_root / name
        if not path.is_file():
            continue
        with path.open("rb") as fh:
            data = _toml.load(fh)
        rules = data.get("rules", {})
        if "enabled" in rules:
            cfg.enabled = list(rules["enabled"])
        if "ip" in data and "enabled" in data["ip"]:
            cfg.ip_enabled = bool(data["ip"]["enabled"])
        cfg.whitelist.extend(_entry_list(data.get("whitelist")))
        cfg.blacklist.extend(_entry_list(data.get("blacklist")))
        cfg.exclude.extend(_entry_list(data.get("exclude")))
    return cfg


def _path_excluded(path: str, cfg: Config) -> bool:
    norm = path.replace("\\", "/")
    for kind, pat, *_ in cfg.exclude:
        try:
            if kind == "regex" and re.search(pat, norm):
                return True
            if kind == "literal" and pat == norm:
                return True
            if kind == "glob" and (fnmatch.fnmatch(norm, pat)
                                   or fnmatch.fnmatch(norm, "*/" + pat)):
                return True
        except re.error:
            continue
    return False


def _hostname_needles() -> list:
    """FQDN, node name, and the short label before the first dot. Deduplicated,
    longest first (so the FQDN is replaced before its short label)."""
    seen = {}
    for h in (socket.getfqdn(), socket.gethostname()):
        if not h:
            continue
        seen[h] = None
        short = h.split(".", 1)[0]
        if short:
            seen[short] = None
    # Drop trivial/loopback labels that would over-match.
    needles = [h for h in seen if h and h.lower() not in ("localhost", "local")]
    return sorted(needles, key=len, reverse=True)


def _glob_to_regex(pat: str) -> str:
    """Translate a glob into an unanchored regex that matches within a line.

    Unlike `fnmatch.translate`, the result carries no `(?s:...)` or `\\Z`, so it does not
    swallow the rest of the line (or its newline). `*` and `?` never cross whitespace.
    """
    out = []
    i, n = 0, len(pat)
    while i < n:
        c = pat[i]
        i += 1
        if c == "*":
            out.append(_GLOB_STAR)
        elif c == "?":
            out.append(r"[^\s]")
        elif c == "[":
            j = i
            if j < n and pat[j] == "!":
                j += 1
            if j < n and pat[j] == "]":
                j += 1
            while j < n and pat[j] != "]":
                j += 1
            if j >= n:
                out.append(re.escape(c))
                continue
            body = pat[i:j]
            i = j + 1
            negate = body.startswith("!")
            if negate:
                body = body[1:]
            body = body.replace("\\", "\\\\").replace("[", "\\[").replace("^", "\\^")
            out.append("[^" + body + "\\s]" if negate else "[" + body + "]")
        else:
            out.append(re.escape(c))
    return "".join(out)


def build_rules(cfg: Config) -> list:
    rules: list = []
    enabled = set(cfg.enabled)
    home = os.environ.get("HOME") or str(Path.home())
    user = getpass.getuser()

    if "home-user" in enabled:
        # HOME plus the canonical /home/<user> form, longest first. The prefix must end at
        # a path boundary (so HOME=/home/user never rewrites /home/users), and group 1 keeps
        # the sub-path tail so the whole path is matched, replaced, and whitelisted.
        bases = []
        for base in ((home or "").rstrip("/"), f"/home/{user}" if user else ""):
            if base and base not in ("~", "/") and base not in bases:
                bases.append(base)
        for base in sorted(bases, key=len, reverse=True):
            rx = re.compile(re.escape(base) + r"((?:/[A-Za-z0-9_.+-]+)*)(?![A-Za-z0-9_.-])")
            rules.append(Rule("home-user", rx, r"~\1"))
    if "home-any" in enabled:
        # \1 keeps the sub-path tail: /home/alice/docs -> ~/docs
        rules.append(Rule("home-any", _HOME_ANY_RE, r"~\1"))
    if "hostname" in enabled:
        for needle in _hostname_needles():
            rules.append(Rule("hostname", re.compile(re.escape(needle)), "<host>"))
    if "ip" in enabled and cfg.ip_enabled:
        rules.append(Rule("ip", _IPV4_RE, "<ip>"))
        rules.append(Rule("ip", _IPV6_RE, "<ip>"))

    # Blacklist entries are always-scrub, appended last.
    for kind, pat, repl in cfg.blacklist:
        try:
            rx = re.compile(pat if kind == "regex" else re.escape(pat) if kind == "literal"
                            else _glob_to_regex(pat))
        except re.error:
            continue
        rules.append(Rule("blacklist", rx, repl))
    return rules


def _whitelisted(text: str, cfg: Config) -> bool:
    for kind, pat in [(k, p) for (k, p, *_ ) in cfg.whitelist]:
        try:
            if kind == "regex" and re.search(pat, text):
                return True
            if kind == "literal" and pat in text:
                return True
            if kind == "glob" and fnmatch.fnmatch(text, pat):
                return True
        except re.error:
            continue
    return False


@dataclass
class Finding:
    path: str
    line: int
    rule: str
    category: str  # never the raw value in CI-facing output


def scan_text(text: str, path: str, rules: list, cfg: Config):
    """Return (findings, new_text). new_text is the fixed content."""
    findings = []
    lines = text.splitlines(keepends=True)
    new_lines = []
    for i, line in enumerate(lines, 1):
        new_line = line
        for rule in rules:
            def _sub(m, rule=rule):
                if _whitelisted(m.group(0), cfg):
                    return m.group(0)
                findings.append(Finding(path, i, rule.name, rule.name))
                return m.expand(rule.replace)
            new_line = rule.pattern.sub(_sub, new_line)
        new_lines.append(new_line)
    return findings, "".join(new_lines)


def _staged_files(repo_root=None):
    out = subprocess.run(
        ["git", "diff", "--cached", "--name-only", "--diff-filter=ACM"],
        capture_output=True, text=True, cwd=repo_root,
    )
    return [f for f in out.stdout.splitlines() if f]


def _unstaged_files(repo_root=None):
    """Paths whose working-tree copy differs from the index (unstaged edits)."""
    out = subprocess.run(
        ["git", "diff", "--name-only"], capture_output=True, text=True, cwd=repo_root,
    )
    return [f for f in out.stdout.splitlines() if f]


def _tracked_files(repo_root=None):
    out = subprocess.run(["git", "ls-files"], capture_output=True, text=True, cwd=repo_root)
    return [f for f in out.stdout.splitlines() if f]


def _read_staged(path: str, repo_root=None):
    """The staged (index) blob as text, or None when it is missing, binary, or not UTF-8."""
    out = subprocess.run(["git", "show", f":{path}"], capture_output=True, cwd=repo_root)
    if out.returncode != 0 or b"\x00" in out.stdout:
        return None
    try:
        text = out.stdout.decode("utf-8")
    except UnicodeDecodeError:
        return None
    # Universal newlines, as `text=True` gave before, so a --fix write_text() does not
    # turn a CRLF blob into CR CR LF on Windows.
    return text.replace("\r\n", "\n").replace("\r", "\n")


def _looks_binary(data: str) -> bool:
    return "\x00" in data


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Sanitize home paths / hostnames / IPs.")
    mode = ap.add_mutually_exclusive_group()
    mode.add_argument("--check", action="store_true", help="report only, exit non-zero on match")
    mode.add_argument("--fix", action="store_true", help="rewrite matches in place")
    ap.add_argument("files", nargs="*", help="files to scan (default: staged, or --all)")
    ap.add_argument("--all", action="store_true", help="scan all tracked files")
    ap.add_argument("--scrub", action="append", default=None,
                    help="ruleset(s) to run (repeatable); default = configured")
    ap.add_argument("--match", help="custom regex (bypasses default rulesets)")
    ap.add_argument("--replace", default="<redacted>", help="replacement for --match")
    ap.add_argument("--dry-run", action="store_true", help="show diffs, write nothing")
    ap.add_argument("--repo-root", default=".", help="repo root (for config + git)")
    args = ap.parse_args(argv)

    if not args.check and not args.fix:
        args.check = True  # default mode

    repo_root = Path(args.repo_root).resolve()
    cfg = load_config(repo_root)
    if args.scrub:
        cfg.enabled = list(args.scrub)
        if "ip" in cfg.enabled:
            cfg.ip_enabled = True

    if args.match:
        rules = [Rule("custom", re.compile(args.match), args.replace)]
    else:
        rules = build_rules(cfg)

    staged_mode = not args.files and not args.all
    writing = args.fix and not args.dry_run
    if args.files:
        targets = args.files
        read = lambda p: (Path(p).read_text(encoding="utf-8", errors="replace")
                          if Path(p).is_file() else None)
    elif args.all:
        targets = _tracked_files(repo_root)
        read = lambda p: (Path(repo_root / p).read_text(encoding="utf-8", errors="replace")
                          if (repo_root / p).is_file() else None)
    else:
        targets = _staged_files(repo_root)
        read = lambda p: _read_staged(p, repo_root)
    # A staged fix writes the fixed INDEX blob over the working tree, so it is only safe
    # when the working tree has no unstaged edits to that file.
    unstaged = set(_unstaged_files(repo_root)) if (writing and staged_mode) else set()

    all_findings = []
    fixed_paths = []
    unfixed_paths = []
    for path in targets:
        if _path_excluded(path, cfg):
            continue
        content = read(path)
        if content is None or _looks_binary(content):
            continue
        findings, new_text = scan_text(content, path, rules, cfg)
        if not findings:
            continue
        all_findings.extend(findings)
        if writing:
            if path in unstaged:
                print(
                    f"sanitize-paths: refusing to --fix {path}: it has unstaged working-tree "
                    "edits that the staged copy would overwrite. Stage or stash them, or "
                    f"run: python3 scripts/sanitize_paths.py --fix {path}",
                    file=sys.stderr,
                )
                unfixed_paths.append(path)
                continue
            fp = Path(path) if args.files else (repo_root / path)
            if new_text != content and fp.is_file():
                fp.write_text(new_text, encoding="utf-8")
                fixed_paths.append(path)
            else:
                unfixed_paths.append(path)
        elif args.dry_run and new_text != content:
            fixed_paths.append(path)

    # Consolidated summary (ONE block at the end), grouped by rule; category only.
    if all_findings:
        by_rule = {}
        for f in all_findings:
            by_rule.setdefault(f.rule, []).append(f)
        print("sanitize-paths: findings", file=sys.stderr)
        for rule in sorted(by_rule):
            print(f"  [{rule}] {len(by_rule[rule])} match(es):", file=sys.stderr)
            for f in by_rule[rule]:
                print(f"    {f.path}:{f.line}", file=sys.stderr)
        print(
            "\nTo allow a legitimate value, add it to `whitelist` in .sanitize-local.toml "
            "(type = glob|regex|literal).\n"
            "To always scrub an extra value, add it to `blacklist`.\n"
            "To auto-fix locally: python3 scripts/sanitize_paths.py --fix [files...]",
            file=sys.stderr,
        )

    if writing:
        restaged = True
        if fixed_paths and staged_mode:
            restaged = subprocess.run(["git", "add", "--"] + fixed_paths,
                                      cwd=repo_root).returncode == 0
            if not restaged:
                print("sanitize-paths: `git add` of the fixed files failed", file=sys.stderr)
        if unfixed_paths:
            print(f"sanitize-paths: {len(unfixed_paths)} file(s) left unfixed",
                  file=sys.stderr)
        return 0 if (restaged and not unfixed_paths) else 1
    if args.dry_run:
        if fixed_paths:
            print(f"\n(dry-run) would rewrite {len(fixed_paths)} file(s).", file=sys.stderr)
        return 0
    # --check
    return 1 if all_findings else 0


if __name__ == "__main__":
    raise SystemExit(main())
