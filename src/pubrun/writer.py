import atexit
import hashlib
import inspect
import json
import logging
import os
import threading
import time
import uuid
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from pubrun.capture.signals import finalization_lock

logger = logging.getLogger("pubrun")

_VALID_DURABILITY_POLICIES = frozenset({"fsync", "finalize", "atomic", "strict"})
_DURABILITY_RANK = {"atomic": 0, "fsync": 1, "strict": 2}
_warned_invalid_durability: set = set()
_durability_warn_lock = threading.Lock()


def _resolve_durability(config: Any, *, stage: str) -> str:
    """Resolve the effective write durability mode for the given artifact stage.

    Maps ``[core].artifact_durability`` (default ``"fsync"``) and ``stage``
    (``"startup"``, ``"refresh"``, or ``"finalize"``) onto one of
    ``"atomic"``, ``"fsync"``, or ``"strict"``. Logs one bounded warning per
    distinct invalid value and falls back safely to ``"fsync"``.
    """
    raw: Any = "fsync"
    if isinstance(config, dict):
        core = config.get("core")
        if isinstance(core, dict):
            raw = core.get("artifact_durability", "fsync")

    if not isinstance(raw, str) or raw not in _VALID_DURABILITY_POLICIES:
        warn_key = raw if isinstance(raw, str) else repr(raw)
        should_warn = False
        with _durability_warn_lock:
            if warn_key not in _warned_invalid_durability:
                _warned_invalid_durability.add(warn_key)
                should_warn = True
        if should_warn:
            logger.warning(
                "pubrun: invalid core.artifact_durability %r; falling back to 'fsync' "
                "(valid options: atomic, finalize, fsync, strict)",
                raw,
            )
        policy = "fsync"
    else:
        policy = raw

    if policy == "finalize":
        return "fsync" if stage == "finalize" else "atomic"
    return policy


def _fsync_directory(dir_path: Path) -> None:
    """Synchronize a parent directory on POSIX systems (best-effort)."""
    if os.name != "posix" or not hasattr(os, "O_DIRECTORY"):
        return
    flags = os.O_RDONLY | os.O_DIRECTORY | getattr(os, "O_CLOEXEC", 0)
    fd: Optional[int] = None
    try:
        fd = os.open(str(dir_path), flags)
        os.fsync(fd)
    except OSError as exc:
        logger.debug("pubrun: parent directory fsync skipped for %s: %s", dir_path, exc)
    finally:
        if fd is not None:
            try:
                os.close(fd)
            except OSError:
                pass


def _fsync_existing_file(path: Path, *, durability: str) -> None:
    """Synchronize an existing unchanged file in place without rewriting it."""
    with open(path, "r+b") as f:
        os.fsync(f.fileno())
    if durability == "strict":
        _fsync_directory(path.parent)


def _atomic_json_write(
    path: Path,
    data: Any,
    *,
    durability: str = "fsync",
    pre_serialized: Optional[str] = None,
) -> None:
    """Write JSON atomically via a unique temporary file and ``os.replace()``.

    Atomic visibility is always enforced so concurrent readers (such as
    ``pubrun status``) never see a partially written file. Disk
    synchronization is controlled separately by ``durability``:
    ``"atomic"`` omits ``os.fsync()``, ``"fsync"`` synchronizes the file
    before replacement, and ``"strict"`` also attempts a best-effort POSIX
    parent-directory ``os.fsync()`` after replacement.
    """
    tmp_path = path.with_suffix(f".json.{os.getpid()}.{uuid.uuid4().hex[:8]}.tmp")
    try:
        with open(tmp_path, "w", encoding="utf-8") as f:
            if pre_serialized is not None:
                f.write(pre_serialized)
            else:
                json.dump(data, f, indent=2, default=str)
            f.flush()
            if durability in ("fsync", "strict"):
                os.fsync(f.fileno())
        for _attempt in range(10 if os.name == "nt" else 1):
            try:
                os.replace(str(tmp_path), str(path))
                break
            except PermissionError:
                if os.name != "nt" or _attempt == 9:
                    raise
                time.sleep(0.005 * (_attempt + 1))
        if durability == "strict":
            _fsync_directory(path.parent)
    except Exception:
        try:
            tmp_path.unlink(missing_ok=True)
        except Exception:
            pass
        raise


_DEFAULT_ATOMIC_JSON_WRITE = _atomic_json_write


def _invoke_atomic_json_write(
    path: Path,
    data: Any,
    *,
    durability: str = "fsync",
    pre_serialized: Optional[str] = None,
) -> None:
    """Invoke ``_atomic_json_write``, tolerating 2-argument test monkeypatches."""
    fn = _atomic_json_write
    if fn is _DEFAULT_ATOMIC_JSON_WRITE:
        fn(path, data, durability=durability, pre_serialized=pre_serialized)
        return
    try:
        params = inspect.signature(fn).parameters
    except (TypeError, ValueError):
        fn(path, data, durability=durability, pre_serialized=pre_serialized)
        return
    has_var_kw = any(p.kind == inspect.Parameter.VAR_KEYWORD for p in params.values())
    call_kwargs: Dict[str, Any] = {}
    if has_var_kw or "durability" in params:
        call_kwargs["durability"] = durability
    if has_var_kw or "pre_serialized" in params:
        call_kwargs["pre_serialized"] = pre_serialized
    fn(path, data, **call_kwargs)


def _serialize_config_and_digest(config: Any) -> Tuple[str, str]:
    """Serialize config deterministically with sorted keys and return (payload, sha256)."""
    payload = json.dumps(config, indent=2, sort_keys=True, default=str)
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    return payload, digest


class ArtifactWriter:
    """Serializes active and finalized Run state to disk without crashing the host script."""

    def __init__(self, run_instance: Any) -> None:
        """Bind this writer to the given Run instance."""
        self.run = run_instance
        self._registered = False
        self._artifacts_written = False
        self.last_error: Optional[str] = None
        self._write_failure_warned = False
        self._write_lock = threading.RLock()
        self._last_config_target: Optional[Path] = None
        self._last_config_digest: Optional[str] = None
        self._last_config_durability: Optional[str] = None
        self._startup_included_hardware: bool = False

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

    def _write_config_if_needed(self, out_dir: Path, *, stage: str) -> bool:
        """Write ``config.resolved.json`` only when target, content, or file presence requires it.

        If the unchanged file is already on disk at a weaker durability rank than
        required for ``stage`` (for example, ``"finalize"`` upgrading an
        ``"atomic"`` startup snapshot to ``"fsync"``), synchronize the file in
        place without rewriting it, falling back to an atomic write on ``OSError``.

        Returns True when an atomic write was performed, False when skipped or
        synchronized in place.
        """
        config_path = out_dir / "config.resolved.json"
        effective_durability = _resolve_durability(self.run.config, stage=stage)
        payload, digest = _serialize_config_and_digest(self.run.config)

        if (
            self._last_config_target == config_path
            and self._last_config_digest == digest
            and config_path.exists()
        ):
            cached_rank = _DURABILITY_RANK.get(self._last_config_durability or "", -1)
            required_rank = _DURABILITY_RANK[effective_durability]
            if cached_rank >= required_rank:
                return False
            try:
                _fsync_existing_file(config_path, durability=effective_durability)
                self._last_config_durability = effective_durability
                return False
            except OSError:
                pass

        _invoke_atomic_json_write(
            config_path,
            self.run.config,
            durability=effective_durability,
            pre_serialized=payload,
        )
        self._last_config_target = config_path
        self._last_config_digest = digest
        self._last_config_durability = effective_durability
        return True

    def sync_config_if_changed(self) -> bool:
        """Persist ``config.resolved.json`` when effective configuration or ``run_dir`` changed.

        Returns True when ``config.resolved.json`` was written, False when unchanged
        or on error. Never raises into the host script.
        """
        try:
            with self._write_lock:
                out_dir: Path = self.run.run_dir
                out_dir.mkdir(parents=True, exist_ok=True)
                return self._write_config_if_needed(out_dir, stage="startup")
        except Exception as e:
            from pubrun.capture.redaction import format_safe_error_detail
            detail = format_safe_error_detail(e, getattr(self.run, "config", None))
            self.last_error = detail
            logger.debug("pubrun failed to sync config.resolved.json: %s", detail)
            return False

    def write_artifacts(self) -> bool:
        """Write config.resolved.json (when needed), manifest.json, and methods report.

        Invokes ``self.run._finalize_state()`` before acquiring ``_write_lock`` so
        lock ordering always stays ``_run_lock`` before ``_write_lock``.
        Catches all exceptions and returns True when ``manifest.json`` was written
        successfully (or was already written for a finalized run), False otherwise.
        """
        if getattr(self.run, "pid", os.getpid()) != os.getpid():
            return False
        if self._artifacts_written and getattr(self.run, "_finalized", False):
            return True

        try:
            write_start_mono = time.perf_counter()

            # Finalize OUTSIDE _write_lock so _run_lock is never acquired while
            # holding _write_lock (prevents AB-BA deadlock with pubrun-hw) and
            # _write_lock is never held across _hardware_future_done.wait(2.0).
            self.run._finalize_state()

            with finalization_lock(self._write_lock, 2.0):
                if self._artifacts_written and getattr(self.run, "_finalized", False):
                    return True

                out_dir: Path = self.run.run_dir
                out_dir.mkdir(parents=True, exist_ok=True)

                # 1. Persist or durability-upgrade config.resolved.json before
                #    manifest.json so any config I/O latency is captured in
                #    pre-manifest finalization overhead. Guarded separately so a
                #    config failure never prevents writing manifest.json.
                config_err_detail: Optional[str] = None
                try:
                    self._write_config_if_needed(out_dir, stage="finalize")
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
                durability = _resolve_durability(self.run.config, stage="finalize")
                _invoke_atomic_json_write(
                    manifest_path, manifest_data, durability=durability
                )
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

    def write_startup_manifest(self, *args: Any, is_refresh: bool = False, **kwargs: Any) -> bool:
        """Write the initial or refreshed startup ``manifest.json`` and ``config.resolved.json``.

        Does not finalize state. Latches ``_hardware_future_done.is_set()`` before
        calling ``to_manifest_dict()`` so a background hardware refresh is never
        skipped when hardware completed only after ``to_manifest_dict()`` captured
        ``"pending"``.

        Returns True when startup artifacts wrote (or refresh was already covered),
        False on failure.
        """
        try:
            with self._write_lock:
                if is_refresh and self._startup_included_hardware:
                    return True

                out_dir: Path = self.run.run_dir
                out_dir.mkdir(parents=True, exist_ok=True)

                hw_done = getattr(self.run, "_hardware_future_done", None)
                hw_was_done = bool(hw_done is not None and hw_done.is_set())

                stage = "refresh" if is_refresh else "startup"
                durability = _resolve_durability(self.run.config, stage=stage)

                manifest_data = self.run.to_manifest_dict()
                manifest_path = out_dir / "manifest.json"
                _invoke_atomic_json_write(
                    manifest_path, manifest_data, durability=durability
                )

                # Isolated so a config.resolved.json failure never demotes a run
                # whose manifest.json was already written into ghost mode.
                config_err_detail: Optional[str] = None
                try:
                    self._write_config_if_needed(out_dir, stage=stage)
                except Exception as cfg_err:
                    from pubrun.capture.redaction import format_safe_error_detail
                    config_err_detail = format_safe_error_detail(
                        cfg_err, getattr(self.run, "config", None)
                    )
                    logger.debug(
                        "pubrun failed to write startup config.resolved.json: %s",
                        config_err_detail,
                    )

                if hw_was_done:
                    self._startup_included_hardware = True
                self.last_error = config_err_detail
                return True
        except Exception as e:
            from pubrun.capture.redaction import format_safe_error_detail
            detail = format_safe_error_detail(e, getattr(self.run, "config", None))
            self.last_error = detail
            logger.debug("pubrun failed to write startup artifacts: %s", detail)
            return False
