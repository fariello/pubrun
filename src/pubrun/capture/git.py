import contextlib
import math
import os
import subprocess
import sys
import time
from typing import Any, Dict, Optional, Tuple

_SYS_MODULES = sys.modules


def _disable_spy_if_loaded() -> Any:
    """Return ``disable_spy()`` when ``pubrun.capture.subprocesses`` is loaded, else a no-op context."""
    modules = getattr(sys, "modules", _SYS_MODULES)
    spy_mod = modules.get("pubrun.capture.subprocesses") if modules is not None else None
    disable = getattr(spy_mod, "disable_spy", None)
    if callable(disable):
        return disable()
    return contextlib.nullcontext()


def _parse_positive_timeout(value: Any, default: float) -> float:
    """Return a finite positive timeout in seconds, or ``default`` when invalid."""
    if isinstance(value, bool) or value is None:
        return default
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return default
    if not math.isfinite(parsed) or parsed <= 0:
        return default
    return parsed


def _parse_nonnegative_timeout(value: Any, default: float) -> float:
    """Return a finite nonnegative timeout in seconds, or ``default`` when invalid."""
    if isinstance(value, bool) or value is None:
        return default
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return default
    if not math.isfinite(parsed) or parsed < 0:
        return default
    return parsed


def get_git(config: Dict[str, Any]) -> Dict[str, Any]:
    """Capture git repository metadata synchronously within a total wall-clock budget.

    Combines repository root, commit hash, and branch lookup into a single
    ``git rev-parse`` invocation on normal repositories while falling back
    safely for unborn-HEAD empty repositories and single-line mocks. Enforces
    both ``[capture.git].timeout`` (per-command, default 5s) and
    ``[capture.git].total_timeout`` (total monotonic budget, default equal to
    ``timeout``).

    Args:
        config: Resolved pubrun configuration.
    """
    cfg = config.get("capture", {}).get("git", {})

    if not cfg.get("enabled", True) or cfg.get("depth") == "off":
        return {"capture_state": {"status": "suppressed"}}

    per_cmd_timeout = _parse_positive_timeout(cfg.get("timeout", 5.0), 5.0)
    raw_total = cfg.get("total_timeout")
    total_timeout = _parse_nonnegative_timeout(raw_total, per_cmd_timeout)

    deadline = time.monotonic() + total_timeout
    any_timeout = False
    budget_exhausted = False

    def _run_git_raw(args: list) -> Tuple[Optional[int], str, str, bool, bool]:
        """Run git within the remaining budget.

        Returns ``(returncode, stdout, stderr, did_timeout, missing_binary)``.
        """
        nonlocal any_timeout, budget_exhausted
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            budget_exhausted = True
            return None, "", "", False, False

        cmd_timeout = min(per_cmd_timeout, remaining)
        try:
            with _disable_spy_if_loaded():
                res = subprocess.run(
                    ["git"] + args,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    timeout=cmd_timeout,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    env={**os.environ, "LC_ALL": "C"},
                )
            stdout_str = res.stdout if isinstance(res.stdout, str) else ""
            stderr_str = res.stderr if isinstance(res.stderr, str) else ""
            return res.returncode, stdout_str, stderr_str, False, False
        except subprocess.TimeoutExpired:
            any_timeout = True
            if deadline - time.monotonic() <= 0:
                budget_exhausted = True
            return None, "", "", True, False
        except FileNotFoundError:
            return None, "", "", False, True
        except Exception:
            return None, "", "", False, False

    def _run_git(args: list) -> Optional[str]:
        """Run a git command within remaining budget and return stripped stdout or None."""
        rc, out, _err, _did_timeout, _missing = _run_git_raw(args)
        if rc == 0:
            return out.strip()
        return None

    # 1. Combined rev-parse for repo_root, commit, and branch in one spawn.
    rc, stdout, stderr, did_timeout, missing_binary = _run_git_raw(
        ["rev-parse", "--show-toplevel", "HEAD", "--abbrev-ref", "HEAD"]
    )

    repo_root: Optional[str] = None
    commit: Optional[str] = None
    branch: Optional[str] = None

    if missing_binary:
        return {
            "capture_state": {
                "status": "unavailable",
                "detail": "Not a git repository or git binary not installed",
            }
        }

    if not did_timeout and rc is not None:
        lines = [line.strip() for line in stdout.splitlines() if line.strip()]
        if rc == 0:
            if len(lines) >= 3:
                repo_root, commit, branch = lines[0], lines[1], lines[2]
            elif len(lines) >= 1:
                # Single-line or two-line output (e.g. a simplified mock).
                repo_root = lines[0]
                commit = lines[1] if len(lines) >= 2 else _run_git(["rev-parse", "HEAD"])
                branch = _run_git(["rev-parse", "--abbrev-ref", "HEAD"])
        else:
            # Outside a repository, git exits non-zero with empty stdout and
            # "not a git repository" in stderr; return immediately in one call.
            if not lines and "not a git repository" in stderr.lower():
                return {
                    "capture_state": {
                        "status": "unavailable",
                        "detail": "Not a git repository or git binary not installed",
                    }
                }
            # Unborn-HEAD empty repositories exit 128 after printing repo_root
            # (or emitting "ambiguous argument 'HEAD'"). Fall back safely within
            # the remaining capture budget.
            if lines and os.path.isdir(lines[0]):
                repo_root = lines[0]
            else:
                repo_root = _run_git(["rev-parse", "--show-toplevel"])
            if repo_root:
                commit = _run_git(["rev-parse", "HEAD"])
                branch = _run_git(["rev-parse", "--abbrev-ref", "HEAD"])

    if not repo_root:
        if any_timeout or budget_exhausted:
            return {
                "capture_state": {
                    "status": "timeout",
                    "detail": f"git did not respond within {total_timeout:g}s budget",
                }
            }
        return {
            "capture_state": {
                "status": "unavailable",
                "detail": "Not a git repository or git binary not installed",
            }
        }

    # 2. Check for uncommitted changes ("dirty" status), skippable via config.
    check_dirty = cfg.get("check_dirty", True)
    if check_dirty:
        dirty_str = _run_git(["status", "--porcelain"])
        dirty = bool(dirty_str) if dirty_str is not None else None
    else:
        dirty = None

    # 3. Capture and redact remote origin URL within remaining budget.
    remote_url = _run_git(["remote", "get-url", "origin"])
    if remote_url:
        from pubrun.capture.redaction import _redact_value_string_heuristics
        remote_url = _redact_value_string_heuristics(remote_url, config)

    if any_timeout or budget_exhausted:
        capture_state: Dict[str, Any] = {
            "status": "partial",
            "detail": "git capture budget exhausted",
        }
    else:
        capture_state = {"status": "complete"}

    return {
        "repo_root": repo_root,
        "commit": commit,
        # 'HEAD' is returned by git when running in detached HEAD state.
        "branch": branch if branch != "HEAD" else None,
        "dirty": dirty,
        "remote_url": (
            {"representation": "plain", "value": remote_url}
            if remote_url
            else {"representation": "unavailable"}
        ),
        "capture_state": capture_state,
    }
