"""Regression tests for the scripts/sanitize_paths.py bugs fixed by IPD kqzd15 (Set
bugs-audit): BUG-25 (staged binary crash), BUG-26 (--repo-root and staged --fix data loss),
BUG-27 (glob blacklist and home-user matching), and BUG-58 (IPv6 matching).

The script lives outside the package, so it is loaded from its file path (the same way
tests/test_sanitize_paths.py loads it) and also driven as a real subprocess.
"""
import importlib.util
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

_SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "sanitize_paths.py"
_spec = importlib.util.spec_from_file_location("sanitize_paths", _SCRIPT)
assert _spec is not None and _spec.loader is not None
sp = importlib.util.module_from_spec(_spec)
sys.modules["sanitize_paths"] = sp
_spec.loader.exec_module(sp)

needs_git = pytest.mark.skipif(shutil.which("git") is None, reason="git not installed")

LEAK = "path /home/alice/x\n"


def _git(repo, *args):
    return subprocess.run(["git", *args], cwd=repo, capture_output=True, text=True, check=True)


@pytest.fixture
def repo(tmp_path):
    root = tmp_path / "repo"
    root.mkdir()
    _git(root, "init", "-q")
    _git(root, "config", "user.email", "t@example.invalid")
    _git(root, "config", "user.name", "t")
    _git(root, "config", "commit.gpgsign", "false")
    return root


def _run(args, cwd):
    """Run the script as a subprocess from `cwd` (never the repo root itself)."""
    return subprocess.run(
        [sys.executable, str(_SCRIPT), *args], cwd=cwd, capture_output=True, text=True,
    )


def _staged_blob(repo, path):
    return _git(repo, "show", f":{path}").stdout


def _rules(enabled, whitelist=None, blacklist=None, ip_enabled=False):
    cfg = sp.Config(enabled=list(enabled), ip_enabled=ip_enabled,
                    whitelist=whitelist or [], blacklist=blacklist or [])
    return cfg, sp.build_rules(cfg)


# ---- BUG-25: staged binary / non-UTF-8 files ------------------------------

@needs_git
@pytest.mark.parametrize("payload", [b"\x00\x01PNG /home/alice/x\x00", b"caf\xe9 \xff\xfe\n"])
def test_staged_binary_or_non_utf8_file_is_skipped(repo, payload):
    (repo / "blob.bin").write_bytes(payload)
    (repo / "leak.md").write_text(LEAK, encoding="utf-8")
    _git(repo, "add", "blob.bin", "leak.md")

    assert sp._read_staged("blob.bin", repo) is None

    out = _run(["--check", "--scrub", "home-any", "--repo-root", str(repo)], cwd=repo.parent)
    assert "Traceback" not in out.stderr
    assert "UnicodeDecodeError" not in out.stderr
    assert out.returncode == 1  # the text file is still scanned and flagged
    assert "leak.md:1" in out.stderr
    assert "blob.bin" not in out.stderr


@needs_git
def test_staged_binary_only_is_clean(repo):
    (repo / "blob.bin").write_bytes(b"\xff\xd8\xff\x00 binary")
    _git(repo, "add", "blob.bin")
    out = _run(["--check", "--scrub", "home-any", "--repo-root", str(repo)], cwd=repo.parent)
    assert out.returncode == 0, out.stderr
    assert "Traceback" not in out.stderr


# ---- BUG-26: --repo-root from another CWD ---------------------------------

@needs_git
def test_repo_root_all_mode_from_other_cwd(repo, tmp_path):
    (repo / "leak.md").write_text(LEAK, encoding="utf-8")
    _git(repo, "add", "leak.md")
    _git(repo, "commit", "-q", "-m", "init")
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()

    check = _run(["--check", "--all", "--scrub", "home-any", "--repo-root", str(repo)],
                 cwd=elsewhere)
    assert check.returncode == 1
    assert "leak.md:1" in check.stderr

    fix = _run(["--fix", "--all", "--scrub", "home-any", "--repo-root", str(repo)],
               cwd=elsewhere)
    assert fix.returncode == 0, fix.stderr
    assert (repo / "leak.md").read_text(encoding="utf-8") == "path ~/x\n"
    assert list(elsewhere.iterdir()) == []  # nothing written relative to the CWD


@needs_git
def test_repo_root_staged_mode_from_other_cwd_fixes_and_restages(repo, tmp_path):
    (repo / "leak.md").write_text(LEAK, encoding="utf-8")
    _git(repo, "add", "leak.md")
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()

    check = _run(["--check", "--scrub", "home-any", "--repo-root", str(repo)], cwd=elsewhere)
    assert check.returncode == 1
    assert "leak.md:1" in check.stderr

    fix = _run(["--fix", "--scrub", "home-any", "--repo-root", str(repo)], cwd=elsewhere)
    assert fix.returncode == 0, fix.stderr
    assert (repo / "leak.md").read_text(encoding="utf-8") == "path ~/x\n"
    assert _staged_blob(repo, "leak.md") == "path ~/x\n"
    assert list(elsewhere.iterdir()) == []


# ---- BUG-26: staged --fix must not destroy unstaged edits -----------------

@needs_git
def test_staged_fix_refuses_file_with_unstaged_edits(repo):
    (repo / "leak.md").write_text(LEAK, encoding="utf-8")
    _git(repo, "add", "leak.md")
    working = LEAK + "unstaged work in progress\n"
    (repo / "leak.md").write_text(working, encoding="utf-8")

    out = _run(["--fix", "--scrub", "home-any", "--repo-root", str(repo)], cwd=repo.parent)
    assert out.returncode == 1
    assert "refusing to --fix leak.md" in out.stderr
    assert "/home/alice" not in out.stderr  # never echo the matched value
    assert (repo / "leak.md").read_text(encoding="utf-8") == working
    assert _staged_blob(repo, "leak.md") == LEAK


@needs_git
def test_staged_fix_fixes_safe_files_and_still_fails_closed(repo):
    (repo / "safe.md").write_text(LEAK, encoding="utf-8")
    (repo / "partial.md").write_text(LEAK, encoding="utf-8")
    _git(repo, "add", "safe.md", "partial.md")
    (repo / "partial.md").write_text(LEAK + "edit\n", encoding="utf-8")

    out = _run(["--fix", "--scrub", "home-any", "--repo-root", str(repo)], cwd=repo.parent)
    assert out.returncode == 1
    assert _staged_blob(repo, "safe.md") == "path ~/x\n"
    assert (repo / "partial.md").read_text(encoding="utf-8") == LEAK + "edit\n"


@needs_git
def test_staged_dry_run_with_unstaged_edits_writes_nothing(repo):
    (repo / "leak.md").write_text(LEAK, encoding="utf-8")
    _git(repo, "add", "leak.md")
    (repo / "leak.md").write_text(LEAK + "edit\n", encoding="utf-8")
    out = _run(["--fix", "--dry-run", "--scrub", "home-any", "--repo-root", str(repo)],
               cwd=repo.parent)
    assert out.returncode == 0
    assert (repo / "leak.md").read_text(encoding="utf-8") == LEAK + "edit\n"


# ---- BUG-27: glob blacklist translation -----------------------------------

def test_glob_blacklist_matches_mid_line_without_eating_newline():
    cfg, rules = _rules(("home-any",), blacklist=[("glob", "SEKRET-*", "<host>")])
    text = "host SEKRET-BOX7 ready\nnext SEKRET-X, done\nclean line\n"
    findings, new = sp.scan_text(text, "x.md", rules, cfg)
    assert new == "host <host> ready\nnext <host>, done\nclean line\n"
    assert len(findings) == 2


def test_glob_blacklist_question_mark_and_class():
    cfg, rules = _rules((), blacklist=[("glob", "node[0-9]?", "<n>"),
                                       ("glob", "gpu[!a-z]", "<g>")])
    text = "on node42 and node7x, gpu1 not gpux\n"
    _, new = sp.scan_text(text, "x.md", rules, cfg)
    assert new == "on <n> and <n>, <g> not gpux\n"


def test_glob_blacklist_escapes_regex_metacharacters():
    cfg, rules = _rules((), blacklist=[("glob", "a.b+*", "<r>")])
    _, new = sp.scan_text("a.b+c axb+c\n", "x.md", rules, cfg)
    assert new == "<r> axb+c\n"


# ---- BUG-27: home-user boundary and tail -----------------------------------

def test_home_user_prefix_does_not_corrupt_longer_username(monkeypatch):
    # HOME (/home/user) is a strict prefix of another home (/home/users).
    monkeypatch.setenv("HOME", "/home/user")
    cfg, rules = _rules(("home-user",))
    findings, new = sp.scan_text("a /home/users/work b\n", "x", rules, cfg)
    assert new == "a /home/users/work b\n"
    assert findings == []

    findings, new = sp.scan_text("a /home/user/work b\n", "x", rules, cfg)
    assert new == "a ~/work b\n"
    assert len(findings) == 1


def test_home_user_whitelist_glob_sees_full_path(monkeypatch):
    monkeypatch.setenv("HOME", "/home/user")
    text = "see /home/user/docs/x.md\n"
    for enabled in (("home-user",), ("home-any",)):
        cfg, rules = _rules(enabled)
        findings, _ = sp.scan_text(text, "x", rules, cfg)
        assert findings, enabled  # flagged without the whitelist
        cfg, rules = _rules(enabled, whitelist=[("glob", "/home/user/*")])
        findings, new = sp.scan_text(text, "x", rules, cfg)
        assert findings == [], enabled
        assert new == text


def test_home_user_ignores_degenerate_home(monkeypatch):
    for home in ("~", "/", ""):
        monkeypatch.setenv("HOME", home)
        cfg, rules = _rules(("home-user",))
        text = "x ~/a /b and /usr/lib\n"
        _, new = sp.scan_text(text, "x", rules, cfg)
        assert new == text, home


# ---- BUG-58: IPv6 matching -------------------------------------------------

@pytest.mark.parametrize("addr", [
    "::1", "fe80::1", "2001:db8::1", "2001:db8::",
    "2001:0db8:85a3:0000:0000:8a2e:0370:7334", "2001:db8:0:0:1::1",
])
def test_ipv6_matches_compressed_and_full(addr):
    m = sp._IPV6_RE.search(f"addr {addr} up")
    assert m is not None and m.group(0) == addr


@pytest.mark.parametrize("text", [
    "::", "foo::1", "os::a", "12:34:56", "a::b::c", "at 12:34:56.789 ok",
    "std::vector<int>", "1:2:3:4:5:6:7",
])
def test_ipv6_rejects_false_positives(text):
    assert sp._IPV6_RE.search(text) is None


def test_ipv6_scrubbed_through_ip_ruleset():
    cfg, rules = _rules(("ip",), ip_enabled=True)
    text = "bind ::1 and 2001:db8::1 at 12:34:56 via foo::bar\n"
    _, new = sp.scan_text(text, "x", rules, cfg)
    assert new == "bind <ip> and <ip> at 12:34:56 via foo::bar\n"
