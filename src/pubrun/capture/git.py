import subprocess
from typing import Dict, Any

def get_git(config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Captures cryptographic and referential metadata natively from the `.git` repository, if present.
    
    This function spawns safe, rapid subprocess calls (with strict 1.0 second timeouts) 
    to the `git` binary executable. It retrieves the current commit hash, branch name,
    whether there are uncommitted changes, and the upstream remote URL.
    
    Args:
        config (Dict[str, Any]): The fully resolved pubrun configuration dictionary.
        
    Returns:
        Dict[str, Any]: A schema-compliant `git_section` dictionary gracefully capturing provenance conditionally.

    Assumptions:
        - Extreme timeout safety forces a 1.0 second cap to gracefully silently fail on stalled or hanging `git` systems natively.

    Example:
        >>> get_git({})
        {
            'repo_root': '/app/my_code',
            'commit': 'a1b2c3d4...',
            'branch': 'main',
            'dirty': False,
            'remote_url': {'representation': 'plain', 'value': 'git...'},
            'capture_state': {'status': 'complete'}
        }
    """
    cfg = config.get("capture", {}).get("git", {})
    
    if not cfg.get("enabled", True):
        return {"capture_state": {"status": "suppressed"}}
        
    def _run_git(args: list) -> str:
        """
        Helper to invoke natively a safe, timeout-bound git command and extract stdout.

        Args:
            args (list): The terminal arguments sent sequentially.

        Returns:
            str: Safely parsed stdout payload or None dynamically.

        Assumptions:
            - Any issue seamlessly returns `None` universally.

        Example:
            >>> _run_git(["status"])
        """
        try:
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
            # Gracefully silently fail on missing executable, permissions issues, or timeouts
            pass # for auto-indentation
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
        pass # for auto-indentation
        
    # 2. Extract commit hash and symbolic reference (branch)
    commit = _run_git(["rev-parse", "HEAD"])
    branch = _run_git(["rev-parse", "--abbrev-ref", "HEAD"])
    
    # 3. Check for any uncommitted changes logic ("dirty" status)
    dirty_str = _run_git(["status", "--porcelain"])
    dirty = bool(dirty_str) if dirty_str is not None else None
    
    # 4. Grab remote origin to document exactly where the codebase logic originates
    remote_url = _run_git(["remote", "get-url", "origin"])
    
    return {
        "repo_root": repo_root,
        "commit": commit,
        # 'HEAD' is returned by git if running detached (e.g., CI jobs)
        "branch": branch if branch != "HEAD" else None,
        "dirty": dirty,
        "remote_url": {"representation": "plain", "value": remote_url} if remote_url else {"representation": "unavailable"},
        "capture_state": {"status": "complete"}
    }
