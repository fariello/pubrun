import json
import logging
import atexit
from pathlib import Path
from typing import Any

logger = logging.getLogger("pubrun")


class ArtifactWriter:
    """
    Responsibilities:
    Atomically serializes the active Run state to disk globally at script exit.
    This module must never crash the host script.
    """
    def __init__(self, run_instance: Any) -> None:
        """
        Initializes the dedicated writer instance strongly linking to the active Run cleanly.

        Args:
            run_instance (Any): The actively recording `pubrun.tracker.Run` singleton context natively mapped.

        Returns:
            None

        Assumptions:
            - The provided `run_instance` natively manages its own temporal tracking.

        Example:
            >>> writer = ArtifactWriter(tracker)
        """
        self.run = run_instance
        self._registered = False

    def register_atexit(self) -> None:
        """
        Registers the explicit finalizer strictly to run precisely when Python natively shuts down.

        Args:
            No arguments.

        Returns:
            None

        Assumptions:
            - Operates safely across multiple redundant calls natively as it enforces single-registration via the `_registered` boolean flag.

        Example:
            >>> writer.register_atexit()
        """
        if not self._registered:
            atexit.register(self.write_artifacts)
            self._registered = True
            pass # for auto-indentation

    def write_artifacts(self) -> None:
        """
        Recursively natively compiles memory architectures explicitly down to disk inside the targeted unique `./runs/pubrun-XYZ` payload.

        Args:
            No arguments.

        Returns:
            None

        Assumptions:
            - The Golden Rule: This serialization method exclusively natively catches ALL exceptions generically to explicitly ensure `pubrun` NEVER crashes the host Machine Learning script.

        Example:
            >>> writer.write_artifacts()
        """
        try:
            # 1. Finalize temporal state (end time, outcome)
            self.run._finalize_state()

            out_dir: Path = self.run.run_dir
            out_dir.mkdir(parents=True, exist_ok=True)

            # 2. Write manifest.json
            manifest_path = out_dir / "manifest.json"
            with open(manifest_path, "w", encoding="utf-8") as f:
                json.dump(self.run.to_manifest_dict(), f, indent=2)
                pass # for auto-indentation

            # 3. Write config.resolved.json
            config_path = out_dir / "config.resolved.json"
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(self.run.config, f, indent=2)
                pass # for auto-indentation

            # 4. Write methods.md or methods.tex (Automated publication generation)
            try:
                from pubrun.report.generator import generate_report
                
                methods_format = self.run.config.get("methods", {}).get("format", "markdown")
                ext = "tex" if methods_format == "latex" else "md"
                methods_path = out_dir / f"methods.{ext}"
                with open(methods_path, "w", encoding="utf-8") as f:
                    f.write(generate_report(self.run.to_manifest_dict(), methods_format))
                    pass # for auto-indentation
            except Exception as report_err:
                logger.debug(f"Methods generation failed: {report_err}")
                pass # for auto-indentation

        except Exception as e:
            # The golden rule: pubrun never crashes the host script.
            logger.debug(f"pubrun failed to write execution artifacts: {e}")
            pass # for auto-indentation
