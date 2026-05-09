import json
import logging
import atexit
from pathlib import Path
from typing import Any

logger = logging.getLogger("pubrun")


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

        Catches all exceptions — pubrun must never crash the host script.
        """
        try:
            # Finalize has already been called by stop() — the _finalized guard
            # makes this safe even if atexit triggers write_artifacts directly.
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

            # 4. Write methods.md or methods.tex (Automated publication generation)
            try:
                from pubrun.report.methods import generate_report
                
                methods_format = self.run.config.get("methods", {}).get("format", "markdown")
                ext = "tex" if methods_format == "latex" else "md"
                methods_path = out_dir / f"methods.{ext}"
                with open(methods_path, "w", encoding="utf-8") as f:
                    f.write(generate_report(self.run.to_manifest_dict(), methods_format))
            except Exception as report_err:
                logger.debug(f"Methods generation failed: {report_err}")

        except Exception as e:
            # The golden rule: pubrun never crashes the host script.
            import traceback
            traceback.print_exc()
            logger.debug(f"pubrun failed to write execution artifacts: {e}")
