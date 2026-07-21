"""Tests for scripts/sanitize_paths.py.

The sanitizer's whole job is correct match/replace PLUS the hard invariant that a
`/home/<user>`-anchored rule NEVER touches an author name or email (those are public
identity in pyproject.toml / CITATION.cff and must be preserved). These tests guard
that invariant and the ruleset behavior. See IPD 20260720-2331-01.
"""
import importlib.util
import os
import sys
from pathlib import Path

import pytest

_SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "sanitize_paths.py"
_spec = importlib.util.spec_from_file_location("sanitize_paths", _SCRIPT)
assert _spec is not None and _spec.loader is not None
sp = importlib.util.module_from_spec(_spec)
sys.modules["sanitize_paths"] = sp  # register so dataclass annotation resolution works
_spec.loader.exec_module(sp)


def _rules(enabled, ip_enabled=False, whitelist=None, blacklist=None):
    cfg = sp.Config(
        enabled=list(enabled),
        ip_enabled=ip_enabled,
        whitelist=whitelist or [],
        blacklist=blacklist or [],
    )
    return cfg, sp.build_rules(cfg)


def _scan(text, enabled=("home-any",), **kw):
    cfg, rules = _rules(enabled, **kw)
    return sp.scan_text(text, "x.md", rules, cfg)


# ---- home-any -------------------------------------------------------------

def test_home_any_rewrites_generic_home_path():
    findings, new = _scan("see /home/alice/project/foo.py now", enabled=("home-any",))
    assert findings
    assert "/home/alice" not in new
    assert "~/project/foo.py" in new


def test_home_any_catches_file_uri_form():
    findings, new = _scan("[x](file:///home/bob/VC/repo/a.py)", enabled=("home-any",))
    assert findings
    assert "/home/bob" not in new


def test_macos_users_path():
    findings, new = _scan("/Users/carol/dev/x.py", enabled=("home-any",))
    assert findings
    assert "/Users/carol" not in new


# ---- home-user (current user) --------------------------------------------

def test_home_user_rewrites_current_home(monkeypatch):
    monkeypatch.setenv("HOME", "/home/tester")
    cfg, rules = _rules(("home-user",))
    findings, new = sp.scan_text("cd /home/tester/VC/pubrun && x", "x", rules, cfg)
    assert findings
    assert "/home/tester" not in new
    assert "~/VC/pubrun" in new


# ---- THE HARD INVARIANT: never touch author identity ----------------------

def test_author_name_and_email_are_never_matched():
    """A /home/<user>-anchored rule must not touch the author name or email even when
    the username token appears inside them (this is the identity-preservation invariant)."""
    identity = 'author = { name = "Gabriele Fariello", email = "gfariello@fariel.com" }'
    for enabled in (("home-user",), ("home-any",), ("home-user", "home-any", "hostname")):
        os.environ.setdefault("HOME", "~")
        cfg, rules = _rules(enabled)
        findings, new = sp.scan_text(identity, "pyproject.toml", rules, cfg)
        assert new == identity, f"identity mutated under {enabled}: {new!r}"
        assert findings == []


def test_bare_username_without_home_prefix_is_untouched(monkeypatch):
    monkeypatch.setenv("HOME", "~")
    cfg, rules = _rules(("home-user", "home-any"))
    text = "Contact gfariello for details; see gfariello@fariel.com"
    findings, new = sp.scan_text(text, "x", rules, cfg)
    assert new == text
    assert findings == []


# ---- ip ruleset: inert unless enabled ------------------------------------

def test_ip_rule_inert_unless_enabled():
    text = "connect to 203.0.113.7 on startup"
    _, new_off = _scan(text, enabled=("ip",), ip_enabled=False)
    assert new_off == text  # ruleset present but gated off -> no change
    findings_on, new_on = _scan(text, enabled=("ip",), ip_enabled=True)
    assert findings_on
    assert "203.0.113.7" not in new_on


def test_ip_does_not_fire_when_not_in_enabled_list():
    # Even with ip_enabled True, if 'ip' is not in enabled, no IP rule is built.
    _, new = _scan("10.0.0.1", enabled=("home-any",), ip_enabled=True)
    assert new == "10.0.0.1"


# ---- whitelist / blacklist (glob, regex, literal) -------------------------

def test_whitelist_glob_suppresses_match():
    wl = [("glob", "/home/alice*")]
    findings, new = _scan("/home/alice/x", enabled=("home-any",), whitelist=wl)
    assert findings == []
    assert new == "/home/alice/x"


def test_whitelist_regex_suppresses_match():
    wl = [("regex", r"/home/[a-z]+/docs")]
    findings, new = _scan("/home/alice/docs", enabled=("home-any",), whitelist=wl)
    assert findings == []


def test_whitelist_literal_suppresses_match():
    wl = [("literal", "/home/example")]
    findings, new = _scan("/home/example/readme", enabled=("home-any",), whitelist=wl)
    assert findings == []


def test_blacklist_adds_extra_needle():
    bl = [("literal", "SEKRET-BOX", "<host>")]
    findings, new = _scan("host SEKRET-BOX ready", enabled=("home-any",), blacklist=bl)
    assert findings
    assert "SEKRET-BOX" not in new
    assert "<host>" in new


# ---- config loading -------------------------------------------------------

def test_missing_config_uses_defaults(tmp_path):
    cfg = sp.load_config(tmp_path)  # no .sanitize-local.toml present
    assert cfg.enabled == list(sp.DEFAULT_RULESETS)
    assert cfg.ip_enabled is False


def test_config_toggles_ip_and_lists(tmp_path):
    if sp._toml is None:
        pytest.skip("no TOML parser available")
    (tmp_path / ".sanitize-local.toml").write_text(
        '[rules]\nenabled = ["home-any"]\n'
        '[ip]\nenabled = true\n'
        '[[whitelist]]\ntype = "glob"\npattern = "/home/ci*"\n',
        encoding="utf-8",
    )
    cfg = sp.load_config(tmp_path)
    assert cfg.enabled == ["home-any"]
    assert cfg.ip_enabled is True
    assert cfg.whitelist and cfg.whitelist[0][0] == "glob"


# ---- exit-code / mode semantics via main() --------------------------------

def test_check_exit_nonzero_on_match(tmp_path, monkeypatch):
    f = tmp_path / "a.md"
    f.write_text("path /home/alice/x\n", encoding="utf-8")
    rc = sp.main(["--check", "--scrub", "home-any", str(f)])
    assert rc == 1
    assert f.read_text(encoding="utf-8") == "path /home/alice/x\n"  # unchanged


def test_check_exit_zero_when_clean(tmp_path):
    f = tmp_path / "a.md"
    f.write_text("nothing to see\n", encoding="utf-8")
    assert sp.main(["--check", "--scrub", "home-any", str(f)]) == 0


def test_fix_rewrites_and_exits_zero(tmp_path):
    f = tmp_path / "a.md"
    f.write_text("path /home/alice/x\n", encoding="utf-8")
    rc = sp.main(["--fix", "--scrub", "home-any", str(f)])
    assert rc == 0
    assert "/home/alice" not in f.read_text(encoding="utf-8")


def test_dry_run_mutates_nothing(tmp_path):
    f = tmp_path / "a.md"
    original = "path /home/alice/x\n"
    f.write_text(original, encoding="utf-8")
    rc = sp.main(["--fix", "--dry-run", "--scrub", "home-any", str(f)])
    assert rc == 0
    assert f.read_text(encoding="utf-8") == original


def test_custom_match_replace(tmp_path):
    f = tmp_path / "a.md"
    f.write_text("build 12345 done\n", encoding="utf-8")
    rc = sp.main(["--fix", "--match", r"\d{5}", "--replace", "<n>", str(f)])
    assert rc == 0
    assert f.read_text(encoding="utf-8") == "build <n> done\n"
