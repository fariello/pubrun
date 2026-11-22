import json
import logging
import os
import time
import uuid
import atexit
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger("pubrun")


def _atomic_json_write(path: Path, data: Any) -> None:
    """Write JSON to a file atomically via a temporary file + os.replace().

    This prevents readers (e.g., ``pubrun status``) from seeing a partially
    written file if the process is killed mid-write.
    """
    # Use a UNIQUE temp filename (pid + random) so two concurrent writers to the same target
    # (e.g. the synchronous startup write and the hardware-thread re-write of the same file)
    # never collide on one fixed ".tmp" path — a race that could leave the target missing when
    # one writer's os.replace consumed the other's temp file. (CI-flaky config.resolved.json.)
    tmp_path = path.with_suffix(f".json.{os.getpid()}.{uuid.uuid4().hex[:8]}.tmp")
    try:
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
            f.flush()
            os.fsync(f.fileno())
        os.replace(str(tmp_path), str(path))
    except Exception:
        # Clean up temp file on failure (P2-E2)
        try:
            tmp_path.unlink(missing_ok=True)
        except Exception:
            pass
        raise


class ArtifactWriter:
    """Serializes the active Run state to disk at script exit.
    Must never crash the host script."""
    def __init__(self, run_instance: Any) -> None:
        """Bind this writer to the given Run instance."""
        self.run = run_instance
        self._registered = False
        self._artifacts_written = False
        self.last_error: Optional[str] = None
        self._write_failure_warned = False

    def register_atexit(self) -> None:
        """Register ``write_artifacts`` as a Python atexit handler (once only)."""
        if not self._registered:
            atexit.register(self.write_artifacts)
            self._registered = True

    def unregister_atexit(self) -> None:
        """Unregister ``write_artifacts`` from Python atexit hooks if registered."""
        if self._registered:
            try:
                atexit.unregister(self.write_artifacts)
            except Exception:
                pass
            self._registered = False

    def write_artifacts(self) -> bool:
        """Write config.resolved.json, manifest.json, and methods report to disk.

        Uses atomic writes (temp file + os.replace) to prevent partial files.
        Catches all exceptions and returns True when manifest.json was written
        successfully (or was already written for a finalized run), False otherwise.
        """
        if self._artifacts_written and getattr(self.run, "_finalized", False):
            return True

        try:
            write_start_mono = time.perf_counter()

            # Finalize has already been called by stop() -- the _finalized guard
            # makes this safe even if atexit triggers write_artifacts directly.
            self.run._finalize_state()

            out_dir: Path = self.run.run_dir
            out_dir.mkdir(parents=True, exist_ok=True)

            # 1. Write config.resolved.json atomically before manifest.json so
            #    its write latency is captured in pre-manifest finalization overhead.
            #    Guarded separately so a config write failure does not prevent
            #    writing manifest.json or falsely claim manifest.json failed.
            config_err_detail: Optional[str] = None
            config_path = out_dir / "config.resolved.json"
            try:
                _atomic_json_write(config_path, self.run.config)
            except Exception as cfg_err:
                from pubrun.capture.redaction import format_safe_error_detail
                config_err_detail = format_safe_error_detail(
                    cfg_err, getattr(self.run, "config", None)
                )

            # 2. Refresh t3 right before freezing finalized timing in manifest.json.
            if hasattr(self.run, "_mark_finalization_end"):
                self.run._mark_finalization_end()

            # 3. Build manifest once (freezes finalized timing) and write atomically.
            manifest_data = self.run.to_manifest_dict()
            manifest_path = out_dir / "manifest.json"
            _atomic_json_write(manifest_path, manifest_data)
            self._artifacts_written = True
            if config_err_detail is None:
                self.last_error = None
            else:
                self.last_error = config_err_detail
                if not self._write_failure_warned:
                    self._write_failure_warned = True
                    logger.warning(
                        "pubrun: failed to write config.resolved.json: %s",
                        config_err_detail,
                    )

            # 4. Write methods.md or methods.tex (non-fatal).
            try:
                from pubrun.report.methods import generate_report

                cfg = getattr(self.run, "config", None) or {}
                methods_format = cfg.get("methods", {}).get("format", "markdown")
                ext = "tex" if methods_format == "latex" else "md"
                methods_path = out_dir / f"methods.{ext}"
                with open(methods_path, "w", encoding="utf-8") as f:
                    f.write(generate_report(manifest_data, methods_format))
            except Exception as report_err:
                from pubrun.capture.redaction import format_safe_error_detail
                logger.debug(
                    "Methods generation failed: %s",
                    format_safe_error_detail(report_err, getattr(self.run, "config", None)),
                )

            self.run.writer_overhead_seconds = max(0.0, time.perf_counter() - write_start_mono)
            return True

        except Exception as e:
            # The golden rule: pubrun never crashes the host script.
            from pubrun.capture.redaction import format_safe_error_detail
            detail = format_safe_error_detail(e, getattr(self.run, "config", None))
            self.last_error = detail
            if not self._write_failure_warned:
                self._write_failure_warned = True
                logger.warning("pubrun: failed to write execution artifacts: %s", detail)
            return False

    def write_startup_manifest(self, *args: Any, **kwargs: Any) -> bool:
        """Write the initial manifest.json and config.resolved.json at startup.
        Does not finalize state.

        Returns True when startup artifacts wrote atomically, False on failure.
        """
        try:
            out_dir: Path = self.run.run_dir
            out_dir.mkdir(parents=True, exist_ok=True)

            manifest_data = self.run.to_manifest_dict()
            manifest_path = out_dir / "manifest.json"
            _atomic_json_write(manifest_path, manifest_data)

            config_path = out_dir / "config.resolved.json"
            _atomic_json_write(config_path, self.run.config)
            self.last_error = None
            return True
        except Exception as e:
            from pubrun.capture.redaction import format_safe_error_detail
            detail = format_safe_error_detail(e, getattr(self.run, "config", None))
            self.last_error = detail
            logger.debug("pubrun failed to write startup artifacts: %s", detail)
            return False
