import subprocess
from typing import Dict, Any

def get_git(config: Dict[str, Any]) -> Dict[str, Any]:
    """Capture git repository metadata (commit, branch, dirty status, remote URL).

    Spawns short-lived git commands with a configurable per-command timeout
    (``[capture.git].timeout``, default 5s). Returns a ``capture_state:
    suppressed`` dict if disabled, ``unavailable`` if not inside a git
    repository, or ``timeout`` if git did not respond in time.

    Args:
        config: Resolved pubrun configuration.
    """
    cfg = config.get("capture", {}).get("git", {})

    if not cfg.get("enabled", True):
        return {"capture_state": {"status": "suppressed"}}

    try:
        git_timeout = float(cfg.get("timeout", 5))
    except (TypeError, ValueError):
        git_timeout = 5.0

    # Track whether the last _run_git failed specifically due to a timeout, so
    # the caller can distinguish a slow/large repo from a genuine non-repo.
    timed_out = {"flag": False}

    def _run_git(args: list) -> str:
        """Run a git command and return stripped stdout, or None on failure."""
        try:
            from pubrun.capture.subprocesses import disable_spy
            with disable_spy():
                res = subprocess.run(
                    ["git"] + args,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    timeout=git_timeout,
                    text=True
                )
            if res.returncode == 0:
                return res.stdout.strip()
        except subprocess.TimeoutExpired:
            # A slow/large repo or network filesystem, NOT a missing repo.
            timed_out["flag"] = True
        except Exception:
            # Gracefully handle missing executable or permissions issues.
            pass
        return None

    # 1. Establish we are genuinely operating inside a valid Git repository
    repo_root = _run_git(["rev-parse", "--show-toplevel"])
    if not repo_root:
        if timed_out["flag"]:
            # Do not falsely claim "not a git repository" when git simply timed
            # out; record a distinct, honest state. (IPD 20260705 EC-13.)
            return {
                "capture_state": {
                    "status": "timeout",
                    "detail": f"git did not respond within {git_timeout:g}s",
                }
            }
        return {
            "capture_state": {
                "status": "unavailable",
                "detail": "Not a git repository or git binary not installed"
            }
        }

    # 2. Extract commit hash and symbolic reference (branch)
    commit = _run_git(["rev-parse", "HEAD"])
    branch = _run_git(["rev-parse", "--abbrev-ref", "HEAD"])

    # 3. Check for any uncommitted changes logic ("dirty" status)
    # Skippable via config: git status --porcelain can be slow on large repos.
    check_dirty = cfg.get("check_dirty", True)
    if check_dirty:
        dirty_str = _run_git(["status", "--porcelain"])
        dirty = bool(dirty_str) if dirty_str is not None else None
    else:
        dirty = None

    # 4. Grab remote origin to document exactly where the codebase logic originates
    remote_url = _run_git(["remote", "get-url", "origin"])
    if remote_url:
        from pubrun.capture.redaction import _redact_value_string_heuristics
        remote_url = _redact_value_string_heuristics(remote_url, config)

    return {
        "repo_root": repo_root,
        "commit": commit,
        # 'HEAD' is returned by git if running detached (e.g., CI jobs)
        "branch": branch if branch != "HEAD" else None,
        "dirty": dirty,
        "remote_url": {"representation": "plain", "value": remote_url} if remote_url else {"representation": "unavailable"},
        "capture_state": {"status": "complete"}
    }
