"""Custom Hatchling build hook for build-stamped commit identity metadata."""
import json
import os
import re
import subprocess
import tempfile
from typing import Any, Dict, Optional

try:
    from hatchling.builders.hooks.plugin.interface import (  # type: ignore[import-not-found]
        BuildHookInterface,
    )
except ImportError:

    class BuildHookInterface:  # type: ignore[no-redef]
        """Fallback base class when hatchling is not installed (e.g. unit tests)."""

        def __init__(
            self,
            root: str,
            config: Optional[Dict[str, Any]] = None,
            build_config: Optional[Any] = None,
            metadata: Optional[Any] = None,
            directory: Optional[str] = None,
            target_name: str = "wheel",
            app: Optional[Any] = None,
        ) -> None:
            self.root = root
            self.config = config if config is not None else {}
            self.build_config = build_config
            self.metadata = metadata
            self.directory = directory
            self.target_name = target_name
            self.app = app


_GIT_ENV_STRIP = ("GIT_DIR", "GIT_WORK_TREE", "GIT_COMMON_DIR", "GIT_INDEX_FILE")
_SHA_RE = re.compile(r"^[0-9a-fA-F]{40}(?:[0-9a-fA-F]{24})?$")

_TARGET_DESTS = {
    "wheel": ("pubrun/_build_meta.json", "pubrun/COMMIT"),
    "sdist": ("src/pubrun/_build_meta.json", "src/pubrun/COMMIT"),
}


def _is_valid_sha(value: Any) -> bool:
    return isinstance(value, str) and bool(_SHA_RE.fullmatch(value))


def _resolve_checkout_sha(root: str) -> Optional[str]:
    """Return verified HEAD SHA when root itself is the Git repository toplevel."""
    try:
        clean_env = {k: v for k, v in os.environ.items() if k not in _GIT_ENV_STRIP}
        proc = subprocess.run(
            ["git", "-C", root, "rev-parse", "--show-toplevel", "HEAD"],
            capture_output=True,
            text=True,
            timeout=5,
            env=clean_env,
        )
        if proc.returncode != 0:
            return None
        lines = [line.strip() for line in proc.stdout.splitlines() if line.strip()]
        if len(lines) != 2:
            return None
        toplevel, sha = lines
        if os.path.normcase(os.path.realpath(toplevel)) != os.path.normcase(
            os.path.realpath(root)
        ):
            return None
        if not _is_valid_sha(sha):
            return None
        return sha
    except Exception:
        return None


def _read_sdist_meta_sha(root: str, pkg_version: str) -> Optional[str]:
    """Reuse unpacked sdist _build_meta.json only when version and SHA match."""
    meta_path = os.path.join(root, "src", "pubrun", "_build_meta.json")
    if not os.path.isfile(meta_path):
        return None
    try:
        with open(meta_path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        if not isinstance(data, dict):
            return None
        meta_version = data.get("version")
        commit = data.get("commit")
        if not isinstance(meta_version, str) or meta_version != pkg_version:
            return None
        if not _is_valid_sha(commit):
            return None
        return commit
    except Exception:
        return None


class CustomBuildHook(BuildHookInterface):
    """Stamp ownership-verified, version-tagged commit metadata into wheel/sdist builds."""

    def initialize(self, version: str, build_data: Dict[str, Any]) -> None:
        existing_temp = getattr(self, "_temp_dir", None)
        if existing_temp is not None:
            try:
                existing_temp.cleanup()
            except Exception:
                pass
        self._temp_dir: Optional[tempfile.TemporaryDirectory] = None

        if version == "editable":
            return

        dests = _TARGET_DESTS.get(self.target_name)
        if dests is None:
            return

        pkg_version = str(self.metadata.version).strip()
        if not pkg_version:
            return

        if os.path.exists(os.path.join(self.root, ".git")):
            sha = _resolve_checkout_sha(self.root)
        else:
            sha = _read_sdist_meta_sha(self.root, pkg_version)

        if sha is None:
            return

        temp_dir = tempfile.TemporaryDirectory(prefix="pubrun-build-meta-")
        try:
            meta_file = os.path.join(temp_dir.name, "_build_meta.json")
            commit_file = os.path.join(temp_dir.name, "COMMIT")
            with open(meta_file, "w", encoding="utf-8") as fh:
                fh.write(json.dumps({"commit": sha, "version": pkg_version}) + "\n")
            with open(commit_file, "w", encoding="utf-8") as fh:
                fh.write(sha + "\n")
        except Exception:
            temp_dir.cleanup()
            return

        self._temp_dir = temp_dir
        meta_dest, commit_dest = dests
        force_include = build_data.setdefault("force_include", {})
        force_include[meta_file] = meta_dest
        force_include[commit_file] = commit_dest

    def finalize(
        self, version: str, build_data: Dict[str, Any], artifact_path: str
    ) -> None:
        temp_dir = getattr(self, "_temp_dir", None)
        if temp_dir is not None:
            try:
                temp_dir.cleanup()
            finally:
                self._temp_dir = None
