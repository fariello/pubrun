import json
import logging
import os
import atexit
from pathlib import Path
from typing import Any

logger = logging.getLogger("pubrun")


def _atomic_json_write(path: Path, data: Any) -> None:
    """Write JSON to a file atomically via a temporary file + os.replace().

    This prevents readers (e.g., ``pubrun status``) from seeing a partially
    written file if the process is killed mid-write.
    """
    tmp_path = path.with_suffix(".json.tmp")
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
        f.flush()
        os.fsync(f.fileno())
    os.replace(str(tmp_path), str(path))


class ArtifactWriter:
    """Serializes the active Run state to disk at script exit.
    Must never crash the host script."""
    def __init__(self, run_instance: Any) -> None:
        """Bind this writer to the given Run instance."""
        self.run = run_instance
        self._registered = False

    def register_atexit(self) -> None:
        """Register ``write_artifacts`` as a Python atexit handler (once only)."""
        if not self._registered:
            atexit.register(self.write_artifacts)
            self._registered = True

    def write_artifacts(self) -> None:
        """Write manifest.json, config.resolved.json, and methods report to disk.

        Uses atomic writes (temp file + os.replace) to prevent partial files.
        Catches all exceptions — pubrun must never crash the host script.
        """
        try:
            # Finalize has already been called by stop() — the _finalized guard
            # makes this safe even if atexit triggers write_artifacts directly.
            self.run._finalize_state()

            out_dir: Path = self.run.run_dir
            out_dir.mkdir(parents=True, exist_ok=True)

            # Build manifest once, reuse for both manifest.json and methods report.
            manifest_data = self.run.to_manifest_dict()

            # 2. Write manifest.json (atomically)
            manifest_path = out_dir / "manifest.json"
            _atomic_json_write(manifest_path, manifest_data)

            # 3. Write config.resolved.json (atomically)
            config_path = out_dir / "config.resolved.json"
            _atomic_json_write(config_path, self.run.config)

            # 4. Write methods.md or methods.tex (Automated publication generation)
            try:
                from pubrun.report.methods import generate_report
                
                methods_format = self.run.config.get("methods", {}).get("format", "markdown")
                ext = "tex" if methods_format == "latex" else "md"
                methods_path = out_dir / f"methods.{ext}"
                with open(methods_path, "w", encoding="utf-8") as f:
                    f.write(generate_report(manifest_data, methods_format))
            except Exception as report_err:
                logger.debug(f"Methods generation failed: {report_err}")

        except Exception as e:
            # The golden rule: pubrun never crashes the host script.
            logger.debug(f"pubrun failed to write execution artifacts: {e}")
