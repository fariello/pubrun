import json
import logging
import atexit
from pathlib import Path
from typing import Any

logger = logging.getLogger("runtrace")


class ArtifactWriter:
    """
    Responsibilities:
    Atomically serializes the active Run state to disk globally at script exit.
    This module must never crash the host script.
    """
    def __init__(self, run_instance: Any) -> None:
        self.run = run_instance
        self._registered = False

    def register_atexit(self) -> None:
        """Registers the finalizer to run precisely when Python shuts down."""
        if not self._registered:
            atexit.register(self.write_artifacts)
            self._registered = True

    def write_artifacts(self) -> None:
        """Called automatically at application exit or manually upon stop()."""
        try:
            # 1. Finalize temporal state (end time, outcome)
            self.run._finalize_state()

            out_dir: Path = self.run.run_dir
            out_dir.mkdir(parents=True, exist_ok=True)

            # 2. Write manifest.json
            manifest_path = out_dir / "manifest.json"
            with open(manifest_path, "w", encoding="utf-8") as f:
                json.dump(self.run.to_manifest_dict(), f, indent=2)

            # 3. Write config.resolved.json
            config_path = out_dir / "config.resolved.json"
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(self.run.config, f, indent=2)

            # 4. Write methods.md (Automated publication generation)
            try:
                from runtrace.report.generator import generate_report
                methods_path = out_dir / "methods.md"
                with open(methods_path, "w", encoding="utf-8") as f:
                    f.write(generate_report(self.run.to_manifest_dict(), "markdown"))
            except Exception as report_err:
                logger.debug(f"Methods generation failed: {report_err}")

        except Exception as e:
            # The golden rule: runtrace never crashes the host script.
            logger.debug(f"runtrace failed to write execution artifacts: {e}")
