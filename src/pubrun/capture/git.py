import subprocess
from typing import Dict, Any

def get_git(config: Dict[str, Any]) -> Dict[str, Any]:
    """Capture git repository metadata (commit, branch, dirty status, remote URL).

    Spawns short-lived git commands with a 1-second timeout.  Returns a
    ``capture_state: suppressed`` dict if disabled, or ``unavailable`` if
    not inside a git repository.

    Args:
        config: Resolved pubrun configuration.
    """
    cfg = config.get("capture", {}).get("git", {})
    
    if not cfg.get("enabled", True):
        return {"capture_state": {"status": "suppressed"}}
        
    def _run_git(args: list) -> str:
        """Run a git command and return stripped stdout, or None on failure."""
        try:
            from pubrun.capture.subprocesses import disable_spy
            with disable_spy():
                res = subprocess.run(
                    ["git"] + args, 
                    stdout=subprocess.PIPE, 
                    stderr=subprocess.PIPE, 
                    timeout=1, 
                    text=True
                )
            if res.returncode == 0:
                return res.stdout.strip()
        except Exception:
            # Gracefully handle missing executable, permissions issues, or timeouts
            pass
        return None

    # 1. Establish we are genuinely operating inside a valid Git repository
    repo_root = _run_git(["rev-parse", "--show-toplevel"])
    if not repo_root:
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
    dirty_str = _run_git(["status", "--porcelain"])
    dirty = bool(dirty_str) if dirty_str is not None else None
    
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
