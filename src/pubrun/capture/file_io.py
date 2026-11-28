"""File provenance engine, hashing budgets, identity checks, and proxy hardening.

This module uses only the Python standard library (Python 3.8+) and is loaded
lazily when file provenance is requested (e.g. via ``pubrun.open()``).
"""
import builtins
import hashlib
import json
import logging
import math
import os
import re
import stat
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, Union

from pubrun.capture.signals import finalization_lock

logger = logging.getLogger("pubrun")

# Progressive file-I/O provenance detail levels (see [capture.file_io].level).
FILE_IO_LEVELS: Tuple[str, ...] = ("none", "name", "stat", "realpath", "hash")

HASH_STATUSES: Tuple[str, ...] = (
    "completed",
    "disabled",
    "over_budget",
    "unavailable",
    "failed",
    "file_changed",
    "asserted",
    "pending",
)

EVIDENCE_SOURCES: Tuple[str, ...] = ("observed", "asserted", "none")

EVIDENCE_STRENGTHS: Tuple[str, ...] = (
    "verified_content",
    "asserted_content",
    "metadata_only",
    "path_only",
    "changed_unverified",
    "unavailable",
)

OBSERVATION_TIMES: Tuple[str, ...] = (
    "during_stream",
    "at_close",
    "at_registration",
    "at_finalization",
    "caller_supplied",
    "not_observed",
)

SUPPORTED_HASH_ALGORITHMS: Tuple[str, ...] = ("sha256", "sha512", "sha1", "md5")
DEFAULT_HASH_ALGORITHM: str = "sha256"
DEFAULT_CHUNK_SIZE: int = 65536
DEFAULT_MAX_TRACKED_FILES: int = 5000
_MAX_WARNED_INVALID_ALGORITHMS: int = 256

_warn_lock = threading.Lock()
_warned_invalid_algorithms: Set[str] = set()
_fallback_data_files_lock = threading.Lock()


def _readlink_normalized(path: Union[str, os.PathLike]) -> str:
    """Return ``os.readlink(path)``, stripping Windows ``\\\\?\\`` drive prefixes."""
    target = os.readlink(os.fspath(path))
    if (
        os.name == "nt"
        and len(target) >= 6
        and target.startswith("\\\\?\\")
        and target[5] == ":"
    ):
        return target[4:]
    return target


def validate_hash_algorithm(value: Any) -> str:
    """Validate a configured digest algorithm name.

    Returns a normalized name from ``SUPPORTED_HASH_ALGORITHMS``. Invalid
    values log one warning per distinct value and fall back to ``"sha256"``.
    """
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in SUPPORTED_HASH_ALGORITHMS:
            return normalized
    key = repr(value)
    should_warn = False
    with _warn_lock:
        if (
            key not in _warned_invalid_algorithms
            and len(_warned_invalid_algorithms) < _MAX_WARNED_INVALID_ALGORITHMS
        ):
            _warned_invalid_algorithms.add(key)
            should_warn = True
    if should_warn:
        logger.warning(
            "pubrun: unsupported [capture.file_io].hash_algorithm %s; "
            "falling back to '%s' (supported: %s)",
            key,
            DEFAULT_HASH_ALGORITHM,
            ", ".join(SUPPORTED_HASH_ALGORITHMS),
        )
    return DEFAULT_HASH_ALGORITHM


def validate_non_negative_int(value: Any, default: int = 0) -> int:
    """Validate a finite non-negative integer cap, falling back safely."""
    if isinstance(value, bool) or value is None:
        return default
    try:
        if isinstance(value, int):
            return value if value >= 0 else default
        if isinstance(value, float):
            if math.isfinite(value) and value >= 0.0:
                return int(value)
            return default
        if isinstance(value, str):
            parsed = float(value.strip())
            if math.isfinite(parsed) and parsed >= 0.0:
                return int(parsed)
            return default
    except (TypeError, ValueError, OverflowError):
        return default
    return default


def validate_non_negative_float(value: Any, default: float = 0.0) -> float:
    """Validate a finite non-negative float cap, falling back safely."""
    if isinstance(value, bool) or value is None:
        return default
    try:
        parsed = float(value)
        if math.isfinite(parsed) and parsed >= 0.0:
            return parsed
    except (TypeError, ValueError, OverflowError):
        return default
    return default


def _raw_file_io_config(run_instance: Any) -> Dict[str, Any]:
    """Return the raw ``[capture.file_io]`` config dict for ``run_instance``."""
    try:
        cfg = getattr(run_instance, "config", None)
        if isinstance(cfg, dict):
            cap = cfg.get("capture")
            if isinstance(cap, dict):
                fio = cap.get("file_io")
                if isinstance(fio, dict):
                    return fio
    except Exception:
        pass
    return {}


def _resolve_max_tracked_files(run_instance: Any) -> int:
    """Resolve ``[capture.file_io].max_tracked_files`` with safe fallback."""
    raw = _raw_file_io_config(run_instance)
    return validate_non_negative_int(
        raw.get("max_tracked_files", DEFAULT_MAX_TRACKED_FILES),
        DEFAULT_MAX_TRACKED_FILES,
    )


def resolve_file_io_config(run_instance: Any) -> Dict[str, Any]:
    """Extract and validate ``[capture.file_io]`` settings from a run."""
    raw = _raw_file_io_config(run_instance)

    raw_level = raw.get("level", "stat")
    level = raw_level if isinstance(raw_level, str) and raw_level in FILE_IO_LEVELS else "stat"
    return {
        "level": level,
        "max_tracked_files": validate_non_negative_int(
            raw.get("max_tracked_files", DEFAULT_MAX_TRACKED_FILES),
            DEFAULT_MAX_TRACKED_FILES,
        ),
        "max_hash_bytes": validate_non_negative_int(raw.get("max_hash_bytes", 0), 0),
        "max_total_hash_bytes": validate_non_negative_int(
            raw.get("max_total_hash_bytes", 0), 0
        ),
        "max_total_hash_seconds": validate_non_negative_float(
            raw.get("max_total_hash_seconds", 0.0), 0.0
        ),
        "hash_algorithm": validate_hash_algorithm(
            raw.get("hash_algorithm", DEFAULT_HASH_ALGORITHM)
        ),
    }


class FileIdentity:
    """Immutable snapshot of file identity and metadata from ``os.fstat`` or ``os.stat``."""

    __slots__ = ("device", "inode", "size_bytes", "mtime", "ctime", "mtime_ns", "mode")

    def __init__(
        self,
        *,
        device: int,
        inode: int,
        size_bytes: int,
        mtime: float,
        ctime: float,
        mtime_ns: int,
        mode: int,
    ) -> None:
        self.device = int(device)
        self.inode = int(inode)
        self.size_bytes = int(size_bytes)
        self.mtime = float(mtime)
        self.ctime = float(ctime)
        self.mtime_ns = int(mtime_ns)
        self.mode = int(mode)

    @classmethod
    def from_stat_result(cls, st: os.stat_result) -> "FileIdentity":
        mtime_ns = getattr(st, "st_mtime_ns", int(st.st_mtime * 1_000_000_000))
        return cls(
            device=st.st_dev,
            inode=st.st_ino,
            size_bytes=st.st_size,
            mtime=st.st_mtime,
            ctime=st.st_ctime,
            mtime_ns=mtime_ns,
            mode=st.st_mode,
        )

    @classmethod
    def from_fd(cls, fd: int) -> Optional["FileIdentity"]:
        try:
            return cls.from_stat_result(os.fstat(fd))
        except (OSError, ValueError, TypeError):
            return None

    @classmethod
    def from_path(cls, path: Union[str, os.PathLike]) -> Optional["FileIdentity"]:
        try:
            return cls.from_stat_result(os.stat(path))
        except (OSError, ValueError, TypeError):
            return None

    def is_regular_file(self) -> bool:
        return stat.S_ISREG(self.mode)

    def entry_type(self) -> str:
        if stat.S_ISREG(self.mode):
            return "file"
        if stat.S_ISDIR(self.mode):
            return "directory"
        if stat.S_ISLNK(self.mode):
            return "symlink"
        return "special"

    def matches(self, other: "FileIdentity") -> bool:
        """Compare identity snapshots.

        Always compares ``(size_bytes, mtime_ns)``. Compares ``(device, inode)``
        only when both snapshots report non-zero ``inode`` (avoiding false
        mismatches on filesystems or platforms that report ``st_ino == 0``).
        """
        if not isinstance(other, FileIdentity):
            return False
        if self.size_bytes != other.size_bytes or self.mtime_ns != other.mtime_ns:
            return False
        if self.inode != 0 and other.inode != 0:
            if self.inode != other.inode or self.device != other.device:
                return False
        return True

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, FileIdentity):
            return NotImplemented
        return self.matches(other)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "device": self.device,
            "inode": self.inode,
            "size_bytes": self.size_bytes,
            "mtime_ns": self.mtime_ns,
        }

    def diff_details(self, other: "FileIdentity") -> Dict[str, Any]:
        reasons = []
        if self.inode != 0 and other.inode != 0:
            if self.inode != other.inode:
                reasons.append("inode_changed")
            if self.device != other.device:
                reasons.append("device_changed")
        if self.size_bytes != other.size_bytes:
            reasons.append("size_changed")
        if self.mtime_ns != other.mtime_ns:
            reasons.append("mtime_changed")
        return {
            "reasons": reasons,
            "before": self.to_dict(),
            "after": other.to_dict(),
        }


class FileIoBudgetTracker:
    """Thread-safe tracker for per-file and run-wide hashing budgets and counters."""

    def __init__(
        self,
        *,
        max_hash_bytes: int = 0,
        max_total_hash_bytes: int = 0,
        max_total_hash_seconds: float = 0.0,
        hash_algorithm: str = DEFAULT_HASH_ALGORITHM,
    ) -> None:
        self._lock = threading.Lock()
        self.max_hash_bytes: int = validate_non_negative_int(max_hash_bytes, 0)
        self.max_total_hash_bytes: int = validate_non_negative_int(max_total_hash_bytes, 0)
        self.max_total_hash_seconds: float = validate_non_negative_float(
            max_total_hash_seconds, 0.0
        )
        self.hash_algorithm: str = validate_hash_algorithm(hash_algorithm)
        self._has_caps: bool = (
            self.max_hash_bytes > 0
            or self.max_total_hash_bytes > 0
            or self.max_total_hash_seconds > 0.0
        )

        self.total_bytes_hashed: int = 0
        self.total_hash_seconds: float = 0.0
        self.files_hashed: int = 0
        self.files_skipped_over_budget: int = 0
        self.files_changed: int = 0
        self.files_failed: int = 0

    def check_before_hash(self, size_bytes: Optional[int]) -> Optional[str]:
        """Read-only check before hashing a file of ``size_bytes``.

        Returns an over-budget reason string, or ``None`` if hashing is permitted.
        """
        with finalization_lock(self._lock, 0.25):
            if (
                self.max_hash_bytes > 0
                and size_bytes is not None
                and size_bytes > self.max_hash_bytes
            ):
                return (
                    f"file size ({size_bytes} bytes) exceeds "
                    f"max_hash_bytes ({self.max_hash_bytes})"
                )
            if self.max_total_hash_bytes > 0:
                if self.total_bytes_hashed >= self.max_total_hash_bytes:
                    return (
                        f"run total hashed bytes ({self.total_bytes_hashed}) reached "
                        f"max_total_hash_bytes ({self.max_total_hash_bytes})"
                    )
                if (
                    size_bytes is not None
                    and self.total_bytes_hashed + size_bytes > self.max_total_hash_bytes
                ):
                    return (
                        f"hashing {size_bytes} bytes would exceed "
                        f"max_total_hash_bytes ({self.max_total_hash_bytes}; "
                        f"already hashed {self.total_bytes_hashed})"
                    )
            if (
                self.max_total_hash_seconds > 0.0
                and self.total_hash_seconds >= self.max_total_hash_seconds
            ):
                return (
                    f"run total hash time ({self.total_hash_seconds:.4f}s) reached "
                    f"max_total_hash_seconds ({self.max_total_hash_seconds}s)"
                )
            return None

    def check_stream_progress(
        self, pending_bytes: int, pending_seconds: float
    ) -> Optional[str]:
        """Read-only check during streaming without committing bytes or time."""
        with finalization_lock(self._lock, 0.25):
            if self.max_hash_bytes > 0 and pending_bytes > self.max_hash_bytes:
                return (
                    f"streamed bytes ({pending_bytes}) exceeded "
                    f"max_hash_bytes ({self.max_hash_bytes})"
                )
            if (
                self.max_total_hash_bytes > 0
                and self.total_bytes_hashed + pending_bytes > self.max_total_hash_bytes
            ):
                return (
                    f"streamed bytes ({pending_bytes}) would exceed "
                    f"max_total_hash_bytes ({self.max_total_hash_bytes}; "
                    f"already hashed {self.total_bytes_hashed})"
                )
            if (
                self.max_total_hash_seconds > 0.0
                and self.total_hash_seconds + pending_seconds > self.max_total_hash_seconds
            ):
                return (
                    f"streamed hash time ({pending_seconds:.4f}s) would exceed "
                    f"max_total_hash_seconds ({self.max_total_hash_seconds}s)"
                )
            return None

    def consume_chunk(self, n_bytes: int, elapsed_seconds: float) -> Optional[str]:
        """Record a chunk read during fallback hashing and check run-wide caps."""
        with finalization_lock(self._lock, 0.25):
            self.total_bytes_hashed += max(0, int(n_bytes))
            self.total_hash_seconds += max(0.0, float(elapsed_seconds))
            if (
                self.max_total_hash_bytes > 0
                and self.total_bytes_hashed > self.max_total_hash_bytes
            ):
                return (
                    f"cumulative hashed bytes ({self.total_bytes_hashed}) exceeded "
                    f"max_total_hash_bytes ({self.max_total_hash_bytes})"
                )
            if (
                self.max_total_hash_seconds > 0.0
                and self.total_hash_seconds >= self.max_total_hash_seconds
            ):
                return (
                    f"cumulative hash time ({self.total_hash_seconds:.4f}s) reached "
                    f"max_total_hash_seconds ({self.max_total_hash_seconds}s)"
                )
            return None

    def commit_stream_hash(self, n_bytes: int, elapsed_seconds: float) -> None:
        """Commit bytes and elapsed time once when a streaming hash is accepted."""
        with finalization_lock(self._lock, 0.25):
            self.total_bytes_hashed += max(0, int(n_bytes))
            self.total_hash_seconds += max(0.0, float(elapsed_seconds))

    def record_outcome(self, status: str) -> None:
        """Increment the counter for a terminal hashing outcome."""
        with finalization_lock(self._lock, 0.25):
            if status == "completed":
                self.files_hashed += 1
            elif status == "over_budget":
                self.files_skipped_over_budget += 1
            elif status == "file_changed":
                self.files_changed += 1
            elif status == "failed":
                self.files_failed += 1

    def to_summary_dict(self) -> Dict[str, Any]:
        """Export a JSON-serializable summary matching manifest schema."""
        with finalization_lock(self._lock, 0.25):
            return {
                "max_hash_bytes": self.max_hash_bytes,
                "max_total_hash_bytes": self.max_total_hash_bytes,
                "max_total_hash_seconds": self.max_total_hash_seconds,
                "hash_algorithm": self.hash_algorithm,
                "total_bytes_hashed": self.total_bytes_hashed,
                "total_hash_seconds": round(self.total_hash_seconds, 6),
                "files_hashed": self.files_hashed,
                "files_skipped_over_budget": self.files_skipped_over_budget,
                "files_changed": self.files_changed,
                "files_failed": self.files_failed,
            }


def get_or_create_budget_tracker(run_instance: Any) -> FileIoBudgetTracker:
    """Return the run's shared ``FileIoBudgetTracker``, creating it lazily."""
    tracker = getattr(run_instance, "_file_io_budget", None)
    if tracker is not None:
        return tracker
    lock = getattr(run_instance, "_data_files_lock", _fallback_data_files_lock)
    with finalization_lock(lock, 0.25):
        tracker = getattr(run_instance, "_file_io_budget", None)
        if tracker is None:
            cfg = resolve_file_io_config(run_instance)
            tracker = FileIoBudgetTracker(
                max_hash_bytes=cfg["max_hash_bytes"],
                max_total_hash_bytes=cfg["max_total_hash_bytes"],
                max_total_hash_seconds=cfg["max_total_hash_seconds"],
                hash_algorithm=cfg["hash_algorithm"],
            )
            try:
                run_instance._file_io_budget = tracker
            except Exception:
                pass
        return tracker


def classify_open_mode(mode: str) -> Tuple[str, str]:
    """Classify a Python ``open()`` mode string into ``(role, open_disposition)``.

    Any mode containing ``"+"`` maps to ``("input_output", "read_write")``.
    Pure ``"w"`` maps to ``("output", "write")``, pure ``"a"`` to
    ``("output", "append")``, pure ``"x"`` to ``("output", "exclusive_create")``,
    and pure ``"r"`` (or default) to ``("input", "read")``.
    """
    m = mode or "r"
    if "+" in m:
        return ("input_output", "read_write")
    if "w" in m:
        return ("output", "write")
    if "a" in m:
        return ("output", "append")
    if "x" in m:
        return ("output", "exclusive_create")
    return ("input", "read")


def hash_file_checked(
    path: Union[str, os.PathLike],
    *,
    algorithm: str = DEFAULT_HASH_ALGORITHM,
    budget: Optional[FileIoBudgetTracker] = None,
    expected_identity: Optional[FileIdentity] = None,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
) -> Dict[str, Any]:
    """Hash a regular file safely with budget caps and open/close identity checks.

    Performs ``lstat``/``stat`` checks before opening so directories, FIFOs,
    sockets, and devices never hang, and checks per-file and run-wide budgets
    before opening so over-budget files perform zero content reads.
    """
    alg = validate_hash_algorithm(algorithm)

    def _result(
        *,
        hash_status: str,
        hash_status_detail: Optional[str] = None,
        digest: Optional[Dict[str, str]] = None,
        sha256: Optional[str] = None,
        change_detected: bool = False,
        change_details: Optional[Dict[str, Any]] = None,
        evidence_source: str = "none",
        evidence_strength: str = "unavailable",
        entry_type: Optional[str] = None,
        is_symlink: Optional[bool] = None,
        symlink_target: Optional[str] = None,
        hash_stats: Optional[Dict[str, Any]] = None,
        identity: Optional[FileIdentity] = None,
    ) -> Dict[str, Any]:
        out: Dict[str, Any] = {
            "hash_status": hash_status,
            "hash_status_detail": hash_status_detail,
            "hash_algorithm": alg,
            "digest": digest,
            "sha256": sha256,
            "change_detected": change_detected,
            "change_details": change_details,
            "evidence_source": evidence_source,
            "evidence_strength": evidence_strength,
            "hash_stats": hash_stats,
            "identity": identity,
        }
        if entry_type is not None:
            out["entry_type"] = entry_type
        if is_symlink is not None:
            out["is_symlink"] = is_symlink
        if symlink_target is not None:
            out["symlink_target"] = symlink_target
        return out

    is_symlink = False
    symlink_target: Optional[str] = None

    # 1. Inspect path metadata safely before calling open().
    try:
        lst = os.lstat(path)
        is_symlink = stat.S_ISLNK(lst.st_mode)
        if is_symlink:
            try:
                symlink_target = _readlink_normalized(path)
            except OSError:
                symlink_target = None
    except FileNotFoundError:
        return _result(
            hash_status="unavailable",
            hash_status_detail="file does not exist",
            entry_type="missing",
            is_symlink=False,
        )
    except OSError as exc:
        if budget is not None:
            budget.record_outcome("failed")
        return _result(
            hash_status="failed",
            hash_status_detail=f"{type(exc).__name__}: {exc}"[:300],
        )

    try:
        st = os.stat(path)
    except FileNotFoundError:
        detail = "broken symlink" if is_symlink else "file does not exist"
        return _result(
            hash_status="unavailable",
            hash_status_detail=detail,
            entry_type="missing",
            is_symlink=is_symlink,
            symlink_target=symlink_target,
        )
    except OSError as exc:
        if budget is not None:
            budget.record_outcome("failed")
        return _result(
            hash_status="failed",
            hash_status_detail=f"{type(exc).__name__}: {exc}"[:300],
            is_symlink=is_symlink,
            symlink_target=symlink_target,
        )

    st_identity = FileIdentity.from_stat_result(st)

    # Guard directories and special files BEFORE open() so FIFOs/devices never hang.
    if stat.S_ISDIR(st.st_mode):
        return _result(
            hash_status="unavailable",
            hash_status_detail="cannot hash directory",
            evidence_source="observed",
            evidence_strength="metadata_only",
            entry_type="directory",
            is_symlink=is_symlink,
            symlink_target=symlink_target,
            identity=st_identity,
        )
    if not stat.S_ISREG(st.st_mode):
        return _result(
            hash_status="unavailable",
            hash_status_detail="cannot hash non-regular file",
            evidence_source="observed",
            evidence_strength="metadata_only",
            entry_type="special",
            is_symlink=is_symlink,
            symlink_target=symlink_target,
            identity=st_identity,
        )

    # 2. Check expected_identity before reading if stat already shows a change.
    if expected_identity is not None and not st_identity.matches(expected_identity):
        if budget is not None:
            budget.record_outcome("file_changed")
        return _result(
            hash_status="file_changed",
            hash_status_detail="file identity or metadata changed before hashing",
            change_detected=True,
            change_details=expected_identity.diff_details(st_identity),
            evidence_source="observed",
            evidence_strength="changed_unverified",
            entry_type="file",
            is_symlink=is_symlink,
            symlink_target=symlink_target,
            hash_stats={
                "bytes_hashed": 0,
                "extra_read_bytes": 0,
                "hash_duration_seconds": 0.0,
            },
            identity=st_identity,
        )

    # 3. Pre-open budget check (zero content reads when over budget).
    if budget is not None:
        over_reason = budget.check_before_hash(st_identity.size_bytes)
        if over_reason is not None:
            budget.record_outcome("over_budget")
            return _result(
                hash_status="over_budget",
                hash_status_detail=over_reason,
                evidence_source="observed",
                evidence_strength="metadata_only",
                entry_type="file",
                is_symlink=is_symlink,
                symlink_target=symlink_target,
                hash_stats={
                    "bytes_hashed": 0,
                    "extra_read_bytes": 0,
                    "hash_duration_seconds": 0.0,
                },
                identity=st_identity,
            )

    # 4. Open and verify open-fd fstat before and after chunked read.
    bytes_hashed = 0
    total_elapsed = 0.0
    try:
        with builtins.open(path, "rb") as fh:
            start_id = FileIdentity.from_fd(fh.fileno())
            if start_id is None:
                if budget is not None:
                    budget.record_outcome("failed")
                return _result(
                    hash_status="failed",
                    hash_status_detail="fstat failed on open file descriptor",
                    entry_type="file",
                    is_symlink=is_symlink,
                    symlink_target=symlink_target,
                    identity=st_identity,
                )

            if not start_id.is_regular_file():
                return _result(
                    hash_status="unavailable",
                    hash_status_detail="cannot hash non-regular file",
                    evidence_source="observed",
                    evidence_strength="metadata_only",
                    entry_type=start_id.entry_type(),
                    is_symlink=is_symlink,
                    symlink_target=symlink_target,
                    identity=start_id,
                )

            if expected_identity is not None and not start_id.matches(expected_identity):
                if budget is not None:
                    budget.record_outcome("file_changed")
                return _result(
                    hash_status="file_changed",
                    hash_status_detail="file identity or metadata changed before hashing",
                    change_detected=True,
                    change_details=expected_identity.diff_details(start_id),
                    evidence_source="observed",
                    evidence_strength="changed_unverified",
                    entry_type="file",
                    is_symlink=is_symlink,
                    symlink_target=symlink_target,
                    hash_stats={
                        "bytes_hashed": 0,
                        "extra_read_bytes": 0,
                        "hash_duration_seconds": 0.0,
                    },
                    identity=start_id,
                )

            if budget is not None and start_id.size_bytes != st_identity.size_bytes:
                over_reason = budget.check_before_hash(start_id.size_bytes)
                if over_reason is not None:
                    budget.record_outcome("over_budget")
                    return _result(
                        hash_status="over_budget",
                        hash_status_detail=over_reason,
                        evidence_source="observed",
                        evidence_strength="metadata_only",
                        entry_type="file",
                        is_symlink=is_symlink,
                        symlink_target=symlink_target,
                        hash_stats={
                            "bytes_hashed": 0,
                            "extra_read_bytes": 0,
                            "hash_duration_seconds": 0.0,
                        },
                        identity=start_id,
                    )

            hasher = hashlib.new(alg)
            effective_chunk = max(1, int(chunk_size))
            while True:
                t0 = time.monotonic()
                chunk = fh.read(effective_chunk)
                if not chunk:
                    break
                hasher.update(chunk)
                dt = max(0.0, time.monotonic() - t0)
                n = len(chunk)
                bytes_hashed += n
                total_elapsed += dt
                if budget is not None:
                    over_reason = budget.consume_chunk(n, dt)
                    if (
                        over_reason is None
                        and budget.max_hash_bytes > 0
                        and bytes_hashed > budget.max_hash_bytes
                    ):
                        over_reason = (
                            f"bytes read ({bytes_hashed}) exceeded "
                            f"max_hash_bytes ({budget.max_hash_bytes})"
                        )
                    if over_reason is not None:
                        budget.record_outcome("over_budget")
                        return _result(
                            hash_status="over_budget",
                            hash_status_detail=over_reason,
                            evidence_source="observed",
                            evidence_strength="metadata_only",
                            entry_type="file",
                            is_symlink=is_symlink,
                            symlink_target=symlink_target,
                            hash_stats={
                                "bytes_hashed": bytes_hashed,
                                "extra_read_bytes": bytes_hashed,
                                "hash_duration_seconds": round(total_elapsed, 6),
                            },
                            identity=start_id,
                        )

            end_id = FileIdentity.from_fd(fh.fileno())
            if (
                end_id is None
                or not end_id.matches(start_id)
                or bytes_hashed != end_id.size_bytes
            ):
                if budget is not None:
                    budget.record_outcome("file_changed")
                details: Dict[str, Any] = (
                    start_id.diff_details(end_id)
                    if end_id is not None
                    else {"reasons": ["fstat_unavailable_after_read"], "before": start_id.to_dict()}
                )
                if end_id is not None and bytes_hashed != end_id.size_bytes:
                    details["bytes_hashed"] = bytes_hashed
                    if "size_changed" not in details.get("reasons", []):
                        details.setdefault("reasons", []).append("length_mismatch")
                return _result(
                    hash_status="file_changed",
                    hash_status_detail="file changed during hashing",
                    change_detected=True,
                    change_details=details,
                    evidence_source="observed",
                    evidence_strength="changed_unverified",
                    entry_type="file",
                    is_symlink=is_symlink,
                    symlink_target=symlink_target,
                    hash_stats={
                        "bytes_hashed": bytes_hashed,
                        "extra_read_bytes": bytes_hashed,
                        "hash_duration_seconds": round(total_elapsed, 6),
                    },
                    identity=end_id or start_id,
                )

            digest_hex = hasher.hexdigest()
            if budget is not None:
                budget.record_outcome("completed")
            return _result(
                hash_status="completed",
                hash_status_detail=None,
                digest={"algorithm": alg, "value": digest_hex},
                sha256=digest_hex if alg == "sha256" else None,
                change_detected=False,
                change_details=None,
                evidence_source="observed",
                evidence_strength="verified_content",
                entry_type="file",
                is_symlink=is_symlink,
                symlink_target=symlink_target,
                hash_stats={
                    "bytes_hashed": bytes_hashed,
                    "extra_read_bytes": bytes_hashed,
                    "hash_duration_seconds": round(total_elapsed, 6),
                },
                identity=end_id,
            )
    except FileNotFoundError:
        return _result(
            hash_status="unavailable",
            hash_status_detail="file disappeared before hashing",
            entry_type="missing",
            is_symlink=is_symlink,
            symlink_target=symlink_target,
        )
    except OSError as exc:
        if budget is not None:
            budget.record_outcome("failed")
        return _result(
            hash_status="failed",
            hash_status_detail=f"{type(exc).__name__}: {exc}"[:300],
            evidence_source="observed",
            evidence_strength="metadata_only",
            entry_type="file",
            is_symlink=is_symlink,
            symlink_target=symlink_target,
            hash_stats={
                "bytes_hashed": bytes_hashed,
                "extra_read_bytes": bytes_hashed,
                "hash_duration_seconds": round(total_elapsed, 6),
            },
            identity=st_identity,
        )


VALID_ROLES: Tuple[str, ...] = ("input", "output", "input_output")
VALID_REGISTRATION_SOURCES: Tuple[str, ...] = (
    "pubrun.open",
    "register_file",
    "register_input",
    "register_output",
)

# RFC 3986 URI scheme of length 2..16 followed by "://" (explicitly excludes
# single-letter Windows drive paths such as "C:\\..." or "C:/...").
_REMOTE_URI_RE = re.compile(r"^[a-zA-Z][a-zA-Z0-9+.-]{1,15}://")


def _is_remote_uri(path_str: str) -> bool:
    """Return True when ``path_str`` begins with a remote URI scheme (2..16 chars)."""
    return bool(_REMOTE_URI_RE.match(path_str))


def _validate_registration_args(
    path: Any,
    role: Any,
    level: Any,
    digest: Any,
    digest_algorithm: Any,
    verify_digest: Any,
    metadata: Any,
    *,
    label: Any = None,
    registration_source: Optional[str] = None,
) -> Tuple[str, str, Optional[str], Optional[str], str, bool, Optional[Dict[str, Any]]]:
    """Validate programmer-error arguments for explicit external file registration.

    Raises ``TypeError`` or ``ValueError`` deterministically before inspecting
    run state or the filesystem.
    """
    raw_path = os.fspath(path)
    if isinstance(raw_path, bytes):
        path_str = os.fsdecode(raw_path)
    elif isinstance(raw_path, str):
        path_str = raw_path
    else:
        raise TypeError("path must be a string or os.PathLike")
    if not path_str or not path_str.strip():
        raise ValueError("path must be a non-empty string or os.PathLike")

    if not isinstance(role, str) or role not in VALID_ROLES:
        raise ValueError(
            f"invalid role {role!r}; expected one of {', '.join(VALID_ROLES)}"
        )

    if label is not None and not isinstance(label, str):
        raise TypeError("label must be a string or None")

    if level is not None:
        if not isinstance(level, str) or level not in FILE_IO_LEVELS:
            raise ValueError(
                f"invalid level {level!r}; expected one of {', '.join(FILE_IO_LEVELS)}"
            )

    digest_val: Optional[str] = None
    if digest is not None:
        if not isinstance(digest, str) or not digest.strip():
            raise ValueError("digest must be a non-empty string when provided")
        digest_val = digest.strip()

    if not isinstance(digest_algorithm, str) or not digest_algorithm.strip():
        raise ValueError("digest_algorithm must be a non-empty string")
    alg = digest_algorithm.strip().lower()

    verify_flag = bool(verify_digest)
    if verify_flag and digest_val is None:
        raise ValueError("verify_digest=True requires a non-empty digest")

    metadata_copy: Optional[Dict[str, Any]] = None
    if metadata is not None:
        if not isinstance(metadata, dict):
            raise ValueError("metadata must be a dict or None")
        metadata_copy = json.loads(json.dumps(metadata, allow_nan=False))

    if registration_source is not None and registration_source not in VALID_REGISTRATION_SOURCES:
        raise ValueError(
            f"invalid registration_source {registration_source!r}; "
            f"expected one of {', '.join(VALID_REGISTRATION_SOURCES)}"
        )

    return path_str, role, level, digest_val, alg, verify_flag, metadata_copy


class _PendingRegistration:
    """Internal pending-output descriptor kept outside the manifest record dict."""

    __slots__ = (
        "record_ref",
        "path_str",
        "normalized_path",
        "effective_level",
        "digest_val",
        "alg",
        "verify_digest",
        "role",
        "label",
        "registration_source",
    )

    def __init__(
        self,
        *,
        record_ref: Dict[str, Any],
        path_str: str,
        normalized_path: str,
        effective_level: str,
        digest_val: Optional[str],
        alg: str,
        verify_digest: bool,
        role: str,
        label: Optional[str],
        registration_source: str,
    ) -> None:
        self.record_ref = record_ref
        self.path_str = path_str
        self.normalized_path = normalized_path
        self.effective_level = effective_level
        self.digest_val = digest_val
        self.alg = alg
        self.verify_digest = verify_digest
        self.role = role
        self.label = label
        self.registration_source = registration_source


def _record_dedup_key(record: Dict[str, Any]) -> Tuple[Any, ...]:
    digest = record.get("digest")
    digest_key = (
        (digest.get("algorithm"), digest.get("value"))
        if isinstance(digest, dict)
        else None
    )
    caller_digest = record.get("caller_digest")
    caller_digest_key = (
        (
            caller_digest.get("algorithm"),
            caller_digest.get("value"),
            caller_digest.get("verified"),
        )
        if isinstance(caller_digest, dict)
        else None
    )
    inode = record.get("inode")
    device = record.get("device") if inode else None
    identity_key = (
        device,
        inode if inode else None,
        record.get("size_bytes"),
        record.get("mtime_ns"),
    )
    return (
        record.get("path"),
        record.get("role"),
        record.get("label"),
        identity_key,
        record.get("hash_status"),
        digest_key,
        caller_digest_key,
    )


def _bucket_for_role(role: Optional[str]) -> str:
    if role == "output":
        return "outputs"
    if role == "input_output":
        return "mixed"
    return "inputs"


def _event_type_for_role(role: Optional[str]) -> str:
    if role == "output":
        return "output_artifact"
    if role == "input_output":
        return "mixed_dataset"
    return "input_dataset"


def _ensure_data_files_buckets(run_instance: Any) -> Dict[str, Any]:
    """Return ``run_instance.data_files`` ensuring inputs/outputs/mixed lists exist."""
    data_files = getattr(run_instance, "data_files", None)
    if not isinstance(data_files, dict):
        data_files = {"inputs": [], "outputs": [], "mixed": []}
        try:
            run_instance.data_files = data_files
        except Exception:
            pass
    for key in ("inputs", "outputs", "mixed"):
        if key not in data_files or not isinstance(data_files[key], list):
            data_files[key] = []
    return data_files


def _emit_file_event(run_instance: Any, record: Dict[str, Any]) -> None:
    """Emit a file provenance event safely (no-op on closed stream or Ghost Mode)."""
    stream = getattr(run_instance, "event_stream", None)
    if stream is None:
        return
    if hasattr(stream, "_file") and getattr(stream, "_file", None) is None:
        return
    try:
        path_val = record.get("path") or ""
        name = record.get("label") or Path(path_val).name or path_val
        payload: Dict[str, Any] = {
            "path": path_val,
            "role": record.get("role"),
            "sha256": record.get("sha256"),
            "hash_status": record.get("hash_status"),
            "evidence_strength": record.get("evidence_strength"),
        }
        if record.get("label") is not None:
            payload["label"] = record["label"]
        stream.emit(_event_type_for_role(record.get("role")), name=str(name), payload=payload)
    except Exception:
        pass


def _total_stored_records(data_files: Dict[str, Any]) -> int:
    """Return total records across inputs, outputs, and mixed buckets."""
    return (
        len(data_files["inputs"])
        + len(data_files["outputs"])
        + len(data_files["mixed"])
    )


def _increment_records_truncated(data_files: Dict[str, Any]) -> None:
    """Increment ``data_files['records_truncated']`` under ``_data_files_lock``."""
    data_files["records_truncated"] = int(data_files.get("records_truncated", 0)) + 1


def _is_completed_hash_record(record: Dict[str, Any]) -> bool:
    """Return True when ``record`` is eligible for ``_completed_hash_index``."""
    return (
        record.get("hash_status") == "completed"
        and record.get("evidence_source") == "observed"
        and record.get("evidence_strength") == "verified_content"
        and record.get("caller_digest") is None
    )


def _completed_hash_key(record: Dict[str, Any]) -> Tuple[Any, ...]:
    """Return the lookup key for ``_completed_hash_index``."""
    return (
        record.get("path"),
        record.get("role"),
        record.get("label"),
        record.get("hash_algorithm"),
    )


def _index_record(
    record: Dict[str, Any],
    dedup_bucket: Dict[Tuple[Any, ...], Dict[str, Any]],
    completed_bucket: Dict[Tuple[Any, ...], List[Dict[str, Any]]],
    *,
    dedup_key: Optional[Tuple[Any, ...]] = None,
) -> None:
    """Insert ``record`` into the bucket dedup and completed-hash indexes."""
    key = dedup_key if dedup_key is not None else _record_dedup_key(record)
    if key not in dedup_bucket:
        dedup_bucket[key] = record
    if _is_completed_hash_record(record):
        c_key = _completed_hash_key(record)
        entries = completed_bucket.setdefault(c_key, [])
        if not any(existing is record for existing in entries):
            entries.append(record)


def _evict_record_from_indexes(
    record: Dict[str, Any],
    dedup_bucket: Dict[Tuple[Any, ...], Dict[str, Any]],
    completed_bucket: Dict[Tuple[Any, ...], List[Dict[str, Any]]],
) -> None:
    """Remove ``record`` from the bucket dedup and completed-hash indexes."""
    old_key = _record_dedup_key(record)
    if dedup_bucket.get(old_key) is record:
        del dedup_bucket[old_key]
    if _is_completed_hash_record(record):
        old_ckey = _completed_hash_key(record)
        entries = completed_bucket.get(old_ckey)
        if entries:
            remaining = [r for r in entries if r is not record]
            if remaining:
                completed_bucket[old_ckey] = remaining
            else:
                del completed_bucket[old_ckey]


def _set_bucket_index_meta(
    run_instance: Any, bucket_name: str, bucket: List[Any]
) -> None:
    """Record list identity and length for a ``data_files`` bucket."""
    meta = getattr(run_instance, "_data_files_index_meta", None)
    if isinstance(meta, dict):
        meta[bucket_name] = (id(bucket), len(bucket))


def _get_synced_bucket_indexes(
    run_instance: Any, bucket_name: str, bucket: List[Any]
) -> Tuple[
    Dict[Tuple[Any, ...], Dict[str, Any]],
    Dict[Tuple[Any, ...], List[Dict[str, Any]]],
]:
    """Return O(1) dedup and completed-hash indexes synced with ``bucket``.

    Caller must hold ``_data_files_lock``. Automatically rebuilds the bucket
    indexes if external code replaced or resized the list directly.
    """
    dedup_index = getattr(run_instance, "_data_files_dedup_index", None)
    if not isinstance(dedup_index, dict):
        dedup_index = {}
        try:
            run_instance._data_files_dedup_index = dedup_index
        except Exception:
            pass

    completed_index = getattr(run_instance, "_completed_hash_index", None)
    if not isinstance(completed_index, dict):
        completed_index = {}
        try:
            run_instance._completed_hash_index = completed_index
        except Exception:
            pass

    meta = getattr(run_instance, "_data_files_index_meta", None)
    if not isinstance(meta, dict):
        meta = {}
        try:
            run_instance._data_files_index_meta = meta
        except Exception:
            pass

    expected_meta = (id(bucket), len(bucket))
    if (
        meta.get(bucket_name) != expected_meta
        or bucket_name not in dedup_index
        or bucket_name not in completed_index
    ):
        dedup_bucket: Dict[Tuple[Any, ...], Dict[str, Any]] = {}
        completed_bucket: Dict[Tuple[Any, ...], List[Dict[str, Any]]] = {}
        for existing in bucket:
            if not isinstance(existing, dict):
                continue
            _index_record(existing, dedup_bucket, completed_bucket)
        dedup_index[bucket_name] = dedup_bucket
        completed_index[bucket_name] = completed_bucket
        meta[bucket_name] = expected_meta

    return dedup_index[bucket_name], completed_index[bucket_name]


def _set_pending_index_meta(run_instance: Any, pending_list: List[Any]) -> None:
    """Record list identity and length for ``_pending_file_registrations``."""
    try:
        run_instance._pending_file_index_meta = (id(pending_list), len(pending_list))
    except Exception:
        pass


def _get_synced_pending_index(
    run_instance: Any, pending_list: List[Any]
) -> Dict[Tuple[Any, ...], int]:
    """Return O(1) ``(normalized_path, role, label) -> index`` map for pending entries.

    Caller must hold ``_data_files_lock``. Automatically rebuilds the map if
    external code replaced or resized ``pending_list`` directly.
    """
    pending_index = getattr(run_instance, "_pending_file_index", None)
    meta = getattr(run_instance, "_pending_file_index_meta", None)
    expected_meta = (id(pending_list), len(pending_list))
    if not isinstance(pending_index, dict) or meta != expected_meta:
        pending_index = {}
        for idx, item in enumerate(pending_list):
            p_key = (item.normalized_path, item.role, item.label)
            if p_key not in pending_index:
                pending_index[p_key] = idx
        try:
            run_instance._pending_file_index = pending_index
            run_instance._pending_file_index_meta = expected_meta
        except Exception:
            pass
    return pending_index


def append_or_deduplicate_record(
    run_instance: Any, record: Dict[str, Any]
) -> Optional[Dict[str, Any]]:
    """Thread-safely route and append or deduplicate a file provenance record.

    Routes ``role == "input"`` to ``data_files["inputs"]``, ``"output"`` to
    ``data_files["outputs"]``, and ``"input_output"`` to ``data_files["mixed"]``.
    Identical unchanged ``(path, role, label, identity, hash_status, digest)``
    entries increment ``registration_count`` instead of appending duplicates,
    while records with changed content or identity are preserved separately.
    When total stored records reach ``[capture.file_io].max_tracked_files``,
    deduplication updates still succeed while new records are omitted,
    incrementing ``data_files["records_truncated"]`` and returning ``None``.
    """
    lock = getattr(run_instance, "_data_files_lock", _fallback_data_files_lock)
    bucket_name = _bucket_for_role(record.get("role"))
    new_key = _record_dedup_key(record)
    max_tracked = _resolve_max_tracked_files(run_instance)

    with lock:
        data_files = _ensure_data_files_buckets(run_instance)
        bucket = data_files[bucket_name]
        dedup_bucket, completed_bucket = _get_synced_bucket_indexes(
            run_instance, bucket_name, bucket
        )
        existing = dedup_bucket.get(new_key)
        if isinstance(existing, dict):
            existing["registration_count"] = int(existing.get("registration_count", 1)) + 1
            if record.get("last_observed_at_utc") is not None:
                existing["last_observed_at_utc"] = record["last_observed_at_utc"]
            if record.get("accessed_at_utc") is not None:
                existing["accessed_at_utc"] = record["accessed_at_utc"]
            if record.get("modified_at_utc") is not None:
                existing["modified_at_utc"] = record["modified_at_utc"]
            if record.get("metadata") is not None:
                if isinstance(existing.get("metadata"), dict) and isinstance(
                    record["metadata"], dict
                ):
                    merged_meta = dict(existing["metadata"])
                    merged_meta.update(record["metadata"])
                    existing["metadata"] = merged_meta
                else:
                    existing["metadata"] = record["metadata"]
            return existing

        if _total_stored_records(data_files) >= max_tracked:
            _increment_records_truncated(data_files)
            return None

        bucket.append(record)
        _index_record(record, dedup_bucket, completed_bucket, dedup_key=new_key)
        _set_bucket_index_meta(run_instance, bucket_name, bucket)
        return record


def _record_matches_identity(record: Dict[str, Any], identity: FileIdentity) -> bool:
    """Return True when ``record`` holds metadata matching ``identity``."""
    rec_size = record.get("size_bytes")
    rec_mtime_ns = record.get("mtime_ns")
    if rec_size is None or rec_mtime_ns is None:
        return False
    if int(rec_size) != identity.size_bytes or int(rec_mtime_ns) != identity.mtime_ns:
        return False
    rec_inode = record.get("inode")
    rec_device = record.get("device")
    if rec_inode and identity.inode != 0:
        if int(rec_inode) != identity.inode or int(rec_device or 0) != identity.device:
            return False
    return True


def _find_unchanged_completed_record(
    run_instance: Any,
    *,
    path: str,
    normalized_path: str,
    role: str,
    label: Optional[str],
    identity: FileIdentity,
    target_alg: str,
    now: float,
    metadata_copy: Optional[Dict[str, Any]],
) -> Optional[Dict[str, Any]]:
    """Deduplicate an unchanged already-hashed file without re-reading disk bytes."""
    lock = getattr(run_instance, "_data_files_lock", _fallback_data_files_lock)
    bucket_name = _bucket_for_role(role)
    p_key = (normalized_path, role, label)
    c_key = (path, role, label, target_alg)
    with lock:
        pending_list = getattr(run_instance, "_pending_file_registrations", None)
        if isinstance(pending_list, list) and pending_list:
            pending_index = _get_synced_pending_index(run_instance, pending_list)
            if p_key in pending_index:
                return None
        data_files = getattr(run_instance, "data_files", None)
        if not isinstance(data_files, dict):
            return None
        bucket = data_files.get(bucket_name)
        if not isinstance(bucket, list):
            return None
        _, completed_bucket = _get_synced_bucket_indexes(
            run_instance, bucket_name, bucket
        )
        candidates = completed_bucket.get(c_key)
        if not candidates:
            return None
        for existing in candidates:
            if not isinstance(existing, dict):
                continue
            if (
                existing.get("path") == path
                and existing.get("role") == role
                and existing.get("label") == label
                and existing.get("hash_status") == "completed"
                and existing.get("hash_algorithm") == target_alg
                and existing.get("evidence_source") == "observed"
                and existing.get("evidence_strength") == "verified_content"
                and existing.get("caller_digest") is None
                and _record_matches_identity(existing, identity)
            ):
                existing["registration_count"] = int(existing.get("registration_count", 1)) + 1
                existing["last_observed_at_utc"] = now
                if role in ("input", "input_output"):
                    existing["accessed_at_utc"] = now
                if role in ("output", "input_output"):
                    existing["modified_at_utc"] = now
                if metadata_copy is not None:
                    if isinstance(existing.get("metadata"), dict):
                        merged_meta = dict(existing["metadata"])
                        merged_meta.update(metadata_copy)
                        existing["metadata"] = merged_meta
                    else:
                        existing["metadata"] = metadata_copy
                return existing
    return None


def _upgrade_pending_or_append(
    run_instance: Any,
    record: Dict[str, Any],
    *,
    normalized_path: str,
    role: str,
    label: Optional[str],
    metadata_copy: Optional[Dict[str, Any]],
) -> Optional[Dict[str, Any]]:
    """Upgrade a matching pending output record in place, or append/deduplicate."""
    lock = getattr(run_instance, "_data_files_lock", _fallback_data_files_lock)
    bucket_name = _bucket_for_role(role)
    p_key = (normalized_path, role, label)
    with lock:
        pending_list = getattr(run_instance, "_pending_file_registrations", None)
        if isinstance(pending_list, list) and pending_list:
            pending_index = _get_synced_pending_index(run_instance, pending_list)
            idx = pending_index.get(p_key)
            if idx is not None and 0 <= idx < len(pending_list):
                item = pending_list[idx]
                last_idx = len(pending_list) - 1
                if idx != last_idx:
                    last_item = pending_list[last_idx]
                    pending_list[idx] = last_item
                    pending_index[
                        (last_item.normalized_path, last_item.role, last_item.label)
                    ] = idx
                pending_list.pop()
                pending_index.pop(p_key, None)
                _set_pending_index_meta(run_instance, pending_list)

                data_files = _ensure_data_files_buckets(run_instance)
                bucket = data_files[bucket_name]
                dedup_bucket, completed_bucket = _get_synced_bucket_indexes(
                    run_instance, bucket_name, bucket
                )

                existing_rec = item.record_ref
                _evict_record_from_indexes(existing_rec, dedup_bucket, completed_bucket)

                prev_count = int(existing_rec.get("registration_count", 1))
                prev_reg_at = existing_rec.get("registered_at_utc")
                prev_meta = existing_rec.get("metadata")
                existing_rec.clear()
                existing_rec.update(record)
                existing_rec["registered_before_creation"] = True
                existing_rec["registration_count"] = prev_count + 1
                if prev_reg_at is not None:
                    existing_rec["registered_at_utc"] = prev_reg_at
                if isinstance(prev_meta, dict):
                    if metadata_copy is not None:
                        merged_meta = dict(prev_meta)
                        merged_meta.update(metadata_copy)
                        existing_rec["metadata"] = merged_meta
                    else:
                        existing_rec["metadata"] = prev_meta

                _index_record(existing_rec, dedup_bucket, completed_bucket)
                return existing_rec
    return append_or_deduplicate_record(run_instance, record)


def _populate_non_file_digest_fields(
    record: Dict[str, Any],
    *,
    entry_type: str,
    effective_level: str,
    digest_val: Optional[str],
    alg: str,
    verify_digest: bool,
    obs_time: str,
    is_finalization: bool,
    broken_symlink: bool = False,
) -> None:
    """Populate hash and evidence fields for missing, directory, or special targets."""
    record["entry_type"] = entry_type
    record["sha256"] = None

    if entry_type == "missing":
        if broken_symlink:
            reason = "broken symlink"
        elif is_finalization:
            reason = "file did not exist at run finalization"
        else:
            reason = "missing"
    else:
        reason = entry_type

    if digest_val is not None and not verify_digest:
        record["hash_status"] = "asserted"
        record["hash_algorithm"] = alg
        record["caller_digest"] = {"algorithm": alg, "value": digest_val, "verified": None}
        record["digest"] = {"algorithm": alg, "value": digest_val}
        record["observation_time"] = "caller_supplied"
        record["evidence_source"] = "asserted"
        record["evidence_strength"] = "asserted_content"
        record["hash_status_detail"] = (
            f"{reason}; caller digest asserted without local verification"
        )
    elif digest_val is not None and verify_digest:
        record["hash_status"] = "unavailable"
        record["hash_algorithm"] = alg
        record["caller_digest"] = {"algorithm": alg, "value": digest_val, "verified": None}
        record["digest"] = {"algorithm": alg, "value": digest_val}
        record["observation_time"] = "not_observed"
        record["evidence_source"] = "asserted"
        record["evidence_strength"] = "asserted_content"
        record["hash_status_detail"] = f"cannot verify caller digest: target is {reason}"
    else:
        record["hash_status"] = "unavailable"
        record["hash_algorithm"] = None
        record["digest"] = None
        if entry_type == "missing":
            record["observation_time"] = "at_finalization" if is_finalization else "not_observed"
            record["evidence_source"] = "none"
            record["evidence_strength"] = "unavailable"
            record["hash_status_detail"] = (
                reason if reason != "missing" else "file does not exist"
            )
        else:
            record["observation_time"] = obs_time
            record["evidence_source"] = "observed"
            record["evidence_strength"] = (
                "metadata_only" if effective_level != "name" else "path_only"
            )
            record["hash_status_detail"] = f"cannot hash {entry_type}"


def _populate_stat_metadata(record: Dict[str, Any], identity: FileIdentity) -> None:
    record["size_bytes"] = identity.size_bytes
    record["mtime"] = identity.mtime
    record["ctime"] = identity.ctime
    record["mtime_ns"] = identity.mtime_ns
    record["inode"] = identity.inode
    record["device"] = identity.device


def _inspect_local_target(
    run_instance: Any,
    record: Dict[str, Any],
    *,
    path_str: str,
    normalized_path: str,
    effective_level: str,
    digest_val: Optional[str],
    alg: str,
    verify_digest: bool,
    role: str,
    label: Optional[str],
    obs_time: str,
    is_finalization: bool,
    now: float,
    metadata_copy: Optional[Dict[str, Any]],
) -> Optional[Dict[str, Any]]:
    """Inspect a local filesystem target outside ``_data_files_lock``.

    Populates ``record`` in place. Returns an existing deduplicated record if
    an unchanged already-hashed observation matched without re-hashing, else
    ``None`` (meaning the caller should store ``record``).
    """
    if effective_level == "name" and not verify_digest:
        record["path"] = path_str
        record["sha256"] = None
        if digest_val is not None:
            record["hash_status"] = "asserted"
            record["hash_status_detail"] = None
            record["hash_algorithm"] = alg
            record["caller_digest"] = {"algorithm": alg, "value": digest_val, "verified": None}
            record["digest"] = {"algorithm": alg, "value": digest_val}
            record["observation_time"] = "caller_supplied"
            record["evidence_source"] = "asserted"
            record["evidence_strength"] = "asserted_content"
        else:
            record["hash_status"] = "disabled"
            record["hash_status_detail"] = "level is 'name'"
            record["hash_algorithm"] = None
            record["digest"] = None
            record["observation_time"] = obs_time
            record["evidence_source"] = "observed"
            record["evidence_strength"] = "path_only"
        return None

    record["path"] = path_str if effective_level == "name" else normalized_path

    is_symlink = False
    symlink_target: Optional[str] = None

    try:
        lst = os.lstat(path_str)
        is_symlink = stat.S_ISLNK(lst.st_mode)
        if is_symlink:
            try:
                symlink_target = _readlink_normalized(path_str)
            except OSError:
                symlink_target = None
    except FileNotFoundError:
        _populate_non_file_digest_fields(
            record,
            entry_type="missing",
            effective_level=effective_level,
            digest_val=digest_val,
            alg=alg,
            verify_digest=verify_digest,
            obs_time=obs_time,
            is_finalization=is_finalization,
            broken_symlink=False,
        )
        return None
    except OSError as exc:
        if effective_level == "hash" or verify_digest:
            get_or_create_budget_tracker(run_instance).record_outcome("failed")
        record["hash_status"] = "failed"
        record["hash_status_detail"] = f"{type(exc).__name__}: {exc}"[:300]
        record["hash_algorithm"] = alg if digest_val is not None else None
        if digest_val is not None:
            record["caller_digest"] = {"algorithm": alg, "value": digest_val, "verified": None}
        record["digest"] = None
        record["sha256"] = None
        record["observation_time"] = obs_time
        record["evidence_source"] = "none"
        record["evidence_strength"] = "unavailable"
        return None

    try:
        st = os.stat(path_str)
    except FileNotFoundError:
        if is_symlink:
            record["is_symlink"] = True
            record["symlink_target"] = symlink_target
        _populate_non_file_digest_fields(
            record,
            entry_type="missing",
            effective_level=effective_level,
            digest_val=digest_val,
            alg=alg,
            verify_digest=verify_digest,
            obs_time=obs_time,
            is_finalization=is_finalization,
            broken_symlink=is_symlink,
        )
        return None
    except OSError as exc:
        if is_symlink:
            record["is_symlink"] = True
            record["symlink_target"] = symlink_target
        if effective_level == "hash" or verify_digest:
            get_or_create_budget_tracker(run_instance).record_outcome("failed")
        record["hash_status"] = "failed"
        record["hash_status_detail"] = f"{type(exc).__name__}: {exc}"[:300]
        record["hash_algorithm"] = alg if digest_val is not None else None
        if digest_val is not None:
            record["caller_digest"] = {"algorithm": alg, "value": digest_val, "verified": None}
        record["digest"] = None
        record["sha256"] = None
        record["observation_time"] = obs_time
        record["evidence_source"] = "none"
        record["evidence_strength"] = "unavailable"
        return None

    st_identity = FileIdentity.from_stat_result(st)
    if stat.S_ISDIR(st.st_mode):
        entry_type = "directory"
    elif stat.S_ISREG(st.st_mode):
        entry_type = "file"
    else:
        entry_type = "special"

    record["entry_type"] = entry_type
    if effective_level != "name":
        _populate_stat_metadata(record, st_identity)
        if is_symlink:
            record["is_symlink"] = True
            record["symlink_target"] = symlink_target

    if effective_level in ("realpath", "hash"):
        try:
            record["realpath"] = os.path.realpath(path_str)
        except OSError:
            record["realpath"] = None
        record["is_symlink"] = is_symlink
        if is_symlink:
            record["symlink_target"] = symlink_target

    if entry_type != "file":
        _populate_non_file_digest_fields(
            record,
            entry_type=entry_type,
            effective_level=effective_level,
            digest_val=digest_val,
            alg=alg,
            verify_digest=verify_digest,
            obs_time=obs_time,
            is_finalization=is_finalization,
            broken_symlink=False,
        )
        return None

    # Regular file digest policy
    if digest_val is not None and not verify_digest:
        record["caller_digest"] = {"algorithm": alg, "value": digest_val, "verified": None}
        record["digest"] = {"algorithm": alg, "value": digest_val}
        record["hash_algorithm"] = alg
        record["sha256"] = None
        record["hash_status"] = "asserted"
        record["hash_status_detail"] = None
        record["observation_time"] = "caller_supplied"
        record["evidence_source"] = "asserted"
        record["evidence_strength"] = "asserted_content"
        return None

    if digest_val is not None and verify_digest:
        if alg not in SUPPORTED_HASH_ALGORITHMS:
            record["hash_status"] = "unavailable"
            record["hash_status_detail"] = f"unsupported digest algorithm '{alg}'"
            record["hash_algorithm"] = alg
            record["caller_digest"] = {"algorithm": alg, "value": digest_val, "verified": None}
            record["digest"] = {"algorithm": alg, "value": digest_val}
            record["sha256"] = None
            record["observation_time"] = "not_observed"
            record["evidence_source"] = "asserted"
            record["evidence_strength"] = "asserted_content"
            return None

        budget = get_or_create_budget_tracker(run_instance)
        res = hash_file_checked(
            path_str,
            algorithm=alg,
            budget=budget,
            expected_identity=st_identity,
        )
        if res.get("hash_stats") is not None:
            record["hash_stats"] = res["hash_stats"]
        if res.get("identity") is not None and effective_level != "name":
            _populate_stat_metadata(record, res["identity"])

        if res["hash_status"] == "completed" and isinstance(res.get("digest"), dict):
            computed = res["digest"]["value"]
            if computed.lower() == digest_val.lower():
                record["hash_status"] = "completed"
                record["hash_status_detail"] = None
                record["hash_algorithm"] = alg
                record["caller_digest"] = {
                    "algorithm": alg,
                    "value": digest_val,
                    "verified": True,
                }
                record["digest"] = {"algorithm": alg, "value": computed}
                record["sha256"] = computed if alg == "sha256" else None
                record["evidence_source"] = "observed"
                record["evidence_strength"] = "verified_content"
                record["observation_time"] = obs_time
            else:
                record["hash_status"] = "failed"
                record["hash_status_detail"] = "caller_digest_mismatch"
                record["hash_algorithm"] = alg
                record["caller_digest"] = {
                    "algorithm": alg,
                    "value": digest_val,
                    "verified": False,
                }
                record["digest"] = None
                record["sha256"] = None
                record["evidence_source"] = "observed"
                record["evidence_strength"] = "changed_unverified"
                record["observation_time"] = obs_time
        else:
            record["hash_status"] = res["hash_status"]
            record["hash_status_detail"] = res["hash_status_detail"]
            record["hash_algorithm"] = alg
            record["caller_digest"] = {"algorithm": alg, "value": digest_val, "verified": None}
            record["digest"] = None
            record["sha256"] = None
            record["change_detected"] = bool(res.get("change_detected", False))
            if res.get("change_details") is not None:
                record["change_details"] = res["change_details"]
            record["evidence_source"] = res["evidence_source"]
            record["evidence_strength"] = res["evidence_strength"]
            record["observation_time"] = obs_time
        return None

    # No caller digest
    if effective_level == "hash":
        budget = get_or_create_budget_tracker(run_instance)
        target_alg = budget.hash_algorithm
        if not is_finalization:
            deduped = _find_unchanged_completed_record(
                run_instance,
                path=record["path"],
                normalized_path=normalized_path,
                role=role,
                label=label,
                identity=st_identity,
                target_alg=target_alg,
                now=now,
                metadata_copy=metadata_copy,
            )
            if deduped is not None:
                return deduped

        res = hash_file_checked(
            path_str,
            algorithm=target_alg,
            budget=budget,
            expected_identity=st_identity,
        )
        record["hash_status"] = res["hash_status"]
        record["hash_status_detail"] = res["hash_status_detail"]
        record["hash_algorithm"] = res["hash_algorithm"]
        record["digest"] = res["digest"]
        record["sha256"] = res["sha256"]
        record["change_detected"] = bool(res.get("change_detected", False))
        if res.get("change_details") is not None:
            record["change_details"] = res["change_details"]
        record["evidence_source"] = res["evidence_source"]
        record["evidence_strength"] = res["evidence_strength"]
        record["observation_time"] = obs_time
        if res.get("hash_stats") is not None:
            record["hash_stats"] = res["hash_stats"]
        if res.get("entry_type") is not None:
            record["entry_type"] = res["entry_type"]
        if res.get("identity") is not None:
            _populate_stat_metadata(record, res["identity"])
        return None

    # No caller digest and effective_level in ("stat", "realpath")
    record["hash_status"] = "disabled"
    record["hash_status_detail"] = f"level is '{effective_level}'"
    record["hash_algorithm"] = None
    record["digest"] = None
    record["sha256"] = None
    record["observation_time"] = obs_time
    record["evidence_source"] = "observed"
    record["evidence_strength"] = "metadata_only"
    return None


def register_file_provenance(
    run_instance: Any,
    path: Union[str, os.PathLike],
    *,
    role: str = "input",
    label: Optional[str] = None,
    digest: Optional[str] = None,
    digest_algorithm: str = DEFAULT_HASH_ALGORITHM,
    level: Optional[str] = None,
    verify_digest: bool = False,
    defer: bool = False,
    metadata: Optional[Dict[str, Any]] = None,
    registration_source: str = "register_file",
) -> Optional[Dict[str, Any]]:
    """Explicitly register an external local input, output, or mixed-role path.

    Programmer-error arguments raise ``TypeError`` or ``ValueError`` before
    inspecting run state or the filesystem. Unexpected operating system errors
    are captured cleanly into schema-valid records without raising into host
    code.
    """
    (
        path_str,
        role_val,
        explicit_level,
        digest_val,
        alg,
        verify_flag,
        metadata_copy,
    ) = _validate_registration_args(
        path,
        role,
        level,
        digest,
        digest_algorithm,
        verify_digest,
        metadata,
        label=label,
        registration_source=registration_source,
    )

    try:
        cfg = resolve_file_io_config(run_instance)
        effective_level = explicit_level if explicit_level is not None else cfg["level"]
        if effective_level == "none":
            return None

        max_tracked = cfg["max_tracked_files"]
        if max_tracked == 0:
            lock = getattr(run_instance, "_data_files_lock", _fallback_data_files_lock)
            with lock:
                data_files = _ensure_data_files_buckets(run_instance)
                _increment_records_truncated(data_files)
            return None

        now = time.time()
        record: Dict[str, Any] = {
            "path": path_str,
            "role": role_val,
            "label": label,
            "registration_source": registration_source,
            "registration_count": 1,
            "registered_before_creation": False,
            "change_detected": False,
            "registered_at_utc": now,
            "last_observed_at_utc": now,
        }
        if role_val == "input":
            record["accessed_at_utc"] = now
        elif role_val == "output":
            record["modified_at_utc"] = now
        else:
            record["accessed_at_utc"] = now
            record["modified_at_utc"] = now

        if metadata_copy is not None:
            record["metadata"] = metadata_copy

        # 1. Remote URI branch: never touch network or local filesystem.
        if _is_remote_uri(path_str):
            record["entry_type"] = "unsupported_remote_uri"
            record["path"] = path_str
            record["sha256"] = None
            if digest_val is not None and not verify_flag:
                record["hash_status"] = "asserted"
                record["hash_algorithm"] = alg
                record["caller_digest"] = {
                    "algorithm": alg,
                    "value": digest_val,
                    "verified": None,
                }
                record["digest"] = {"algorithm": alg, "value": digest_val}
                record["observation_time"] = "caller_supplied"
                record["evidence_source"] = "asserted"
                record["evidence_strength"] = "asserted_content"
                record["hash_status_detail"] = (
                    "remote object-store URIs are out of scope; "
                    "caller digest asserted without local verification"
                )
            elif digest_val is not None and verify_flag:
                record["hash_status"] = "unavailable"
                record["hash_algorithm"] = alg
                record["caller_digest"] = {
                    "algorithm": alg,
                    "value": digest_val,
                    "verified": None,
                }
                record["digest"] = {"algorithm": alg, "value": digest_val}
                record["observation_time"] = "not_observed"
                record["evidence_source"] = "asserted"
                record["evidence_strength"] = "asserted_content"
                record["hash_status_detail"] = (
                    "remote object-store URIs are out of scope; "
                    "caller digest not verified"
                )
            else:
                record["hash_status"] = "unavailable"
                record["hash_algorithm"] = None
                record["digest"] = None
                record["observation_time"] = "not_observed"
                record["evidence_source"] = "none"
                record["evidence_strength"] = "unavailable"
                record["hash_status_detail"] = "remote object-store URIs are out of scope"

            stored = append_or_deduplicate_record(run_instance, record)
            if stored is None:
                return None
            _emit_file_event(run_instance, stored)
            return stored

        normalized_path = os.path.normpath(os.path.abspath(path_str))

        # 2. Pending-output branch (defer=True or output missing before creation).
        is_pending = False
        if role_val in ("output", "input_output"):
            if defer:
                is_pending = True
            elif effective_level != "name":
                try:
                    os.lstat(path_str)
                except FileNotFoundError:
                    is_pending = True
                except OSError:
                    # PermissionError or other OS error -> handle in local inspection.
                    is_pending = False

        if is_pending:
            lock = getattr(run_instance, "_data_files_lock", _fallback_data_files_lock)
            bucket_name = _bucket_for_role(role_val)
            p_key = (normalized_path, role_val, label)
            with lock:
                pending_list = getattr(run_instance, "_pending_file_registrations", None)
                if not isinstance(pending_list, list):
                    pending_list = []
                    try:
                        run_instance._pending_file_registrations = pending_list
                    except Exception:
                        pass

                pending_index = _get_synced_pending_index(run_instance, pending_list)
                idx = pending_index.get(p_key)
                if idx is not None and 0 <= idx < len(pending_list):
                    item = pending_list[idx]
                    rec = item.record_ref
                    dedup_bucket: Optional[Dict[Tuple[Any, ...], Dict[str, Any]]] = None
                    completed_bucket: Optional[Dict[Tuple[Any, ...], List[Dict[str, Any]]]] = None
                    if digest_val is not None:
                        data_files = _ensure_data_files_buckets(run_instance)
                        bucket = data_files[bucket_name]
                        dedup_bucket, completed_bucket = _get_synced_bucket_indexes(
                            run_instance, bucket_name, bucket
                        )
                        _evict_record_from_indexes(rec, dedup_bucket, completed_bucket)
                    rec["registration_count"] = int(rec.get("registration_count", 1)) + 1
                    rec["last_observed_at_utc"] = now
                    rec["modified_at_utc"] = now
                    if role_val == "input_output":
                        rec["accessed_at_utc"] = now
                    if explicit_level is not None:
                        item.effective_level = explicit_level
                    if metadata_copy is not None:
                        if isinstance(rec.get("metadata"), dict):
                            merged_meta = dict(rec["metadata"])
                            merged_meta.update(metadata_copy)
                            rec["metadata"] = merged_meta
                        else:
                            rec["metadata"] = metadata_copy
                    if digest_val is not None:
                        item.digest_val = digest_val
                        item.alg = alg
                        item.verify_digest = verify_flag
                        rec["hash_algorithm"] = alg
                        rec["caller_digest"] = {
                            "algorithm": alg,
                            "value": digest_val,
                            "verified": None,
                        }
                        rec["digest"] = {"algorithm": alg, "value": digest_val}
                        rec["evidence_source"] = "asserted"
                        rec["evidence_strength"] = "asserted_content"
                        if dedup_bucket is not None and completed_bucket is not None:
                            _index_record(rec, dedup_bucket, completed_bucket)
                    return rec

                data_files = _ensure_data_files_buckets(run_instance)
                if _total_stored_records(data_files) >= max_tracked:
                    _increment_records_truncated(data_files)
                    return None

                record["path"] = path_str if effective_level == "name" else normalized_path
                record["hash_status"] = "pending"
                record["hash_status_detail"] = (
                    "registered before creation; awaiting file creation or run finalization"
                )
                record["registered_before_creation"] = True
                record["observation_time"] = "not_observed"
                record["sha256"] = None
                if digest_val is not None:
                    record["hash_algorithm"] = alg
                    record["caller_digest"] = {
                        "algorithm": alg,
                        "value": digest_val,
                        "verified": None,
                    }
                    record["digest"] = {"algorithm": alg, "value": digest_val}
                    record["evidence_source"] = "asserted"
                    record["evidence_strength"] = "asserted_content"
                else:
                    record["hash_algorithm"] = None
                    record["digest"] = None
                    record["evidence_source"] = "none"
                    record["evidence_strength"] = "unavailable"

                bucket = data_files[bucket_name]
                dedup_bucket_new, completed_bucket_new = _get_synced_bucket_indexes(
                    run_instance, bucket_name, bucket
                )
                bucket.append(record)
                _index_record(record, dedup_bucket_new, completed_bucket_new)
                _set_bucket_index_meta(run_instance, bucket_name, bucket)
                pending_idx = len(pending_list)
                pending_list.append(
                    _PendingRegistration(
                        record_ref=record,
                        path_str=path_str,
                        normalized_path=normalized_path,
                        effective_level=effective_level,
                        digest_val=digest_val,
                        alg=alg,
                        verify_digest=verify_flag,
                        role=role_val,
                        label=label,
                        registration_source=registration_source,
                    )
                )
                pending_index[p_key] = pending_idx
                _set_pending_index_meta(run_instance, pending_list)
            _emit_file_event(run_instance, record)
            return record

        # 3. Local inspection (level="name" fast path or stat/realpath/hash inspection)
        #    performed completely outside _data_files_lock.
        deduped = _inspect_local_target(
            run_instance,
            record,
            path_str=path_str,
            normalized_path=normalized_path,
            effective_level=effective_level,
            digest_val=digest_val,
            alg=alg,
            verify_digest=verify_flag,
            role=role_val,
            label=label,
            obs_time="at_registration",
            is_finalization=False,
            now=now,
            metadata_copy=metadata_copy,
        )
        if deduped is not None:
            _emit_file_event(run_instance, deduped)
            return deduped

        stored = _upgrade_pending_or_append(
            run_instance,
            record,
            normalized_path=normalized_path,
            role=role_val,
            label=label,
            metadata_copy=metadata_copy,
        )
        if stored is None:
            return None
        _emit_file_event(run_instance, stored)
        return stored
    except Exception as exc:
        logger.warning(
            "pubrun: failed to register file provenance for '%s': %s",
            path_str,
            exc,
        )
        return None


def finalize_pending_registrations(run_instance: Any) -> None:
    """Finalize deferred external file registrations during run shutdown.

    Pops all remaining pending entries under ``_data_files_lock``, performs all
    disk inspection and hashing outside the lock, and updates each referenced
    manifest record in place. Safe in Ghost Mode and with closed event streams.
    """
    lock = getattr(run_instance, "_data_files_lock", _fallback_data_files_lock)
    with finalization_lock(lock, 0.25):
        pending_list = getattr(run_instance, "_pending_file_registrations", None)
        if not isinstance(pending_list, list) or not pending_list:
            return
        items = list(pending_list)
        pending_list.clear()
        pending_index = getattr(run_instance, "_pending_file_index", None)
        if isinstance(pending_index, dict):
            pending_index.clear()
        _set_pending_index_meta(run_instance, pending_list)

    for item in items:
        try:
            now = time.time()
            updated: Dict[str, Any] = {
                "path": item.path_str,
                "role": item.role,
                "label": item.label,
                "registration_source": item.registration_source,
                "registration_count": 1,
                "registered_before_creation": True,
                "change_detected": False,
                "registered_at_utc": now,
                "last_observed_at_utc": now,
            }
            if item.role == "output":
                updated["modified_at_utc"] = now
            elif item.role == "input_output":
                updated["accessed_at_utc"] = now
                updated["modified_at_utc"] = now
            else:
                updated["accessed_at_utc"] = now

            _inspect_local_target(
                run_instance,
                updated,
                path_str=item.path_str,
                normalized_path=item.normalized_path,
                effective_level=item.effective_level,
                digest_val=item.digest_val,
                alg=item.alg,
                verify_digest=item.verify_digest,
                role=item.role,
                label=item.label,
                obs_time="at_finalization",
                is_finalization=True,
                now=now,
                metadata_copy=None,
            )

            with finalization_lock(lock, 0.25):
                bucket_name = _bucket_for_role(item.role)
                data_files = _ensure_data_files_buckets(run_instance)
                bucket = data_files[bucket_name]
                dedup_bucket, completed_bucket = _get_synced_bucket_indexes(
                    run_instance, bucket_name, bucket
                )

                existing_rec = item.record_ref
                _evict_record_from_indexes(existing_rec, dedup_bucket, completed_bucket)

                prev_count = int(existing_rec.get("registration_count", 1))
                prev_reg_at = existing_rec.get("registered_at_utc")
                prev_meta = existing_rec.get("metadata")
                existing_rec.clear()
                existing_rec.update(updated)
                existing_rec["registered_before_creation"] = True
                existing_rec["registration_count"] = prev_count
                if prev_reg_at is not None:
                    existing_rec["registered_at_utc"] = prev_reg_at
                if prev_meta is not None:
                    existing_rec["metadata"] = prev_meta

                _index_record(existing_rec, dedup_bucket, completed_bucket)

            _emit_file_event(run_instance, item.record_ref)
        except Exception as exc:
            logger.warning(
                "pubrun: failed to finalize pending registration for '%s': %s",
                getattr(item, "path_str", "<unknown>"),
                exc,
            )


class ProvenanceFileProxy:
    """Hardened proxy wrapping a stream opened via ``pubrun.open()``.

    Captures open-fd ``fstat`` metadata at ``stat``/``realpath``/``hash`` levels,
    omits ``fstat`` and ``size_bytes`` at ``name`` level, evaluates single-pass
    streaming hashing strictly for sequential binary pure reads and writes within
    budget without double-counting budgets on fallback, detects open-to-close and
    hash-time file changes, classifies mixed ``+`` modes honestly, and never
    suppresses host exceptions.
    """

    def __init__(
        self,
        file_obj: Any,
        path: Union[str, Path],
        mode: str,
        run_instance: Any,
        level: str = "stat",
    ) -> None:
        self._file_obj = file_obj
        self._raw_path: str = str(path)
        self._path: Path = Path(path)
        self._mode: str = mode or "r"
        self._run = run_instance
        self._level: str = level if level in FILE_IO_LEVELS else "stat"
        self._closed: bool = False

        self._role, self._open_disposition = classify_open_mode(self._mode)
        self._is_binary: bool = "b" in self._mode

        # Access observations
        self._bytes_read: int = 0
        self._bytes_written: int = 0
        self._read_calls: int = 0
        self._write_calls: int = 0
        self._seek_used: bool = False
        self._truncate_used: bool = False
        self._raw_or_buffer_accessed: bool = False
        self._eof_reached: bool = False

        # Open-time identity and streaming state
        self._open_identity: Optional[FileIdentity] = None
        self._budget: Optional[FileIoBudgetTracker] = None
        self._stream_hasher: Optional[Any] = None
        self._stream_algorithm: Optional[str] = None
        self._stream_valid: bool = False
        self._stream_bytes: int = 0
        self._stream_bytes_since_check: int = 0
        self._stream_elapsed: float = 0.0
        self._stream_over_budget: bool = False
        self._stream_over_budget_reason: Optional[str] = None
        self._max_tracked_files: int = _resolve_max_tracked_files(self._run)

        if self._level in ("stat", "realpath", "hash") and self._max_tracked_files > 0:
            try:
                fileno = self._file_obj.fileno()
                if isinstance(fileno, int):
                    self._open_identity = FileIdentity.from_fd(fileno)
            except Exception:
                self._open_identity = None

        if self._level == "hash" and self._max_tracked_files > 0:
            self._init_streaming()

    def _init_streaming(self) -> None:
        """Evaluate whether single-pass streaming hashing is eligible."""
        self._budget = get_or_create_budget_tracker(self._run)
        self._stream_algorithm = self._budget.hash_algorithm

        if not self._is_binary:
            return

        # Pure binary read: eligible only for regular files within budget.
        if self._role == "input":
            if self._open_identity is None or not self._open_identity.is_regular_file():
                return
            over = self._budget.check_before_hash(self._open_identity.size_bytes)
            if over is not None:
                self._stream_over_budget = True
                self._stream_over_budget_reason = over
                return
            self._stream_hasher = hashlib.new(self._stream_algorithm)
            self._stream_valid = True
            return

        # Pure binary write / exclusive create: eligible for regular files within budget.
        if self._open_disposition in ("write", "exclusive_create"):
            if self._open_identity is not None and not self._open_identity.is_regular_file():
                return
            over = self._budget.check_before_hash(0)
            if over is not None:
                self._stream_over_budget = True
                self._stream_over_budget_reason = over
                return
            self._stream_hasher = hashlib.new(self._stream_algorithm)
            self._stream_valid = True

    def _invalidate_stream(self) -> None:
        self._stream_valid = False
        self._stream_hasher = None

    def _update_stream_hash(self, data: Any) -> None:
        if not self._stream_valid or self._stream_hasher is None:
            return
        n = data.nbytes if isinstance(data, memoryview) else len(data)
        if n <= 0:
            return
        budget = self._budget
        if budget is None or not budget._has_caps:
            self._stream_hasher.update(data)
            self._stream_bytes += n
            return

        self._stream_bytes += n
        self._stream_bytes_since_check += n
        if budget.max_hash_bytes > 0 and self._stream_bytes > budget.max_hash_bytes:
            self._stream_over_budget = True
            self._stream_over_budget_reason = (
                f"streamed bytes ({self._stream_bytes}) exceeded "
                f"max_hash_bytes ({budget.max_hash_bytes})"
            )
            self._invalidate_stream()
            return

        if budget.max_total_hash_seconds > 0.0:
            t0 = time.monotonic()
            self._stream_hasher.update(data)
            dt = max(0.0, time.monotonic() - t0)
            self._stream_elapsed += dt
            if self._stream_elapsed > budget.max_total_hash_seconds:
                self._stream_over_budget = True
                self._stream_over_budget_reason = (
                    f"streamed hash time ({self._stream_elapsed:.4f}s) exceeded "
                    f"max_total_hash_seconds ({budget.max_total_hash_seconds}s)"
                )
                self._invalidate_stream()
                return
        else:
            self._stream_hasher.update(data)

        if self._stream_bytes_since_check >= DEFAULT_CHUNK_SIZE:
            self._stream_bytes_since_check = 0
            over = budget.check_stream_progress(
                self._stream_bytes, self._stream_elapsed
            )
            if over is not None:
                self._stream_over_budget = True
                self._stream_over_budget_reason = over
                self._invalidate_stream()

    def _is_read_mode(self) -> bool:
        return self._role == "input"

    # -- Intercepted I/O methods ---------------------------------------------

    def read(self, *args: Any, **kwargs: Any) -> Any:
        data = self._file_obj.read(*args, **kwargs)
        self._read_calls += 1
        if self._is_binary:
            if data:
                self._bytes_read += len(data)
                if self._role == "input":
                    self._update_stream_hash(data)
                # Unbounded read() reaches EOF.
                size_arg = args[0] if args else kwargs.get("size", -1)
                if size_arg is None or (isinstance(size_arg, int) and size_arg < 0):
                    self._eof_reached = True
            else:
                size_arg = args[0] if args else kwargs.get("size", -1)
                if size_arg != 0:
                    self._eof_reached = True
        else:
            if data:
                self._bytes_read += len(data)
        return data

    def read1(self, *args: Any, **kwargs: Any) -> Any:
        data = self._file_obj.read1(*args, **kwargs)
        self._read_calls += 1
        if self._is_binary:
            if data:
                self._bytes_read += len(data)
                if self._role == "input":
                    self._update_stream_hash(data)
            else:
                size_arg = args[0] if args else kwargs.get("size", -1)
                if size_arg != 0:
                    self._eof_reached = True
        return data

    def readline(self, *args: Any, **kwargs: Any) -> Any:
        data = self._file_obj.readline(*args, **kwargs)
        self._read_calls += 1
        if self._is_binary:
            if data:
                self._bytes_read += len(data)
                if self._role == "input":
                    self._update_stream_hash(data)
            else:
                size_arg = args[0] if args else kwargs.get("size", -1)
                if size_arg != 0:
                    self._eof_reached = True
        else:
            if data:
                self._bytes_read += len(data)
        return data

    def readlines(self, *args: Any, **kwargs: Any) -> Any:
        lines = self._file_obj.readlines(*args, **kwargs)
        self._read_calls += 1
        if self._is_binary:
            for line in lines:
                if line:
                    self._bytes_read += len(line)
                    if self._role == "input":
                        self._update_stream_hash(line)
            hint = args[0] if args else kwargs.get("hint", -1)
            if hint is None or (isinstance(hint, int) and hint <= 0):
                self._eof_reached = True
        else:
            for line in lines:
                if line:
                    self._bytes_read += len(line)
        return lines

    def readinto(self, b: Any) -> Any:
        n = self._file_obj.readinto(b)
        self._read_calls += 1
        if self._is_binary:
            if n:
                self._bytes_read += n
                if self._role == "input" and self._stream_valid:
                    if isinstance(b, bytearray) and n == len(b):
                        self._update_stream_hash(b)
                    else:
                        with memoryview(b) as mv:
                            with mv.cast("B") as bv:
                                with bv[:n] as slice_view:
                                    self._update_stream_hash(slice_view)
            elif n == 0:
                try:
                    with memoryview(b) as mv:
                        if mv.nbytes > 0:
                            self._eof_reached = True
                except TypeError:
                    pass
        return n

    def readinto1(self, b: Any) -> Any:
        n = self._file_obj.readinto1(b)
        self._read_calls += 1
        if self._is_binary:
            if n:
                self._bytes_read += n
                if self._role == "input" and self._stream_valid:
                    if isinstance(b, bytearray) and n == len(b):
                        self._update_stream_hash(b)
                    else:
                        with memoryview(b) as mv:
                            with mv.cast("B") as bv:
                                with bv[:n] as slice_view:
                                    self._update_stream_hash(slice_view)
            elif n == 0:
                try:
                    with memoryview(b) as mv:
                        if mv.nbytes > 0:
                            self._eof_reached = True
                except TypeError:
                    pass
        return n

    def write(self, data: Any) -> Any:
        n = self._file_obj.write(data)
        self._write_calls += 1
        if self._is_binary:
            if isinstance(n, int) and n > 0:
                self._bytes_written += n
                if (
                    self._open_disposition in ("write", "exclusive_create")
                    and self._stream_valid
                ):
                    if isinstance(data, (bytes, bytearray)) and n == len(data):
                        self._update_stream_hash(data)
                    else:
                        with memoryview(data) as mv:
                            with mv.cast("B") as bv:
                                with bv[:n] as slice_view:
                                    self._update_stream_hash(slice_view)
        else:
            if isinstance(n, int) and n > 0:
                self._bytes_written += n
        return n

    def writelines(self, lines: Any) -> None:
        if (
            self._is_binary
            and self._open_disposition in ("write", "exclusive_create")
            and self._stream_valid
        ):
            for chunk in lines:
                self.write(chunk)
            return
        self._write_calls += 1
        self._file_obj.writelines(lines)

    def seek(self, *args: Any, **kwargs: Any) -> Any:
        pos = self._file_obj.seek(*args, **kwargs)
        self._seek_used = True
        self._invalidate_stream()
        return pos

    def truncate(self, *args: Any, **kwargs: Any) -> Any:
        res = self._file_obj.truncate(*args, **kwargs)
        self._truncate_used = True
        self._invalidate_stream()
        return res

    # -- Lifecycle and protocol methods --------------------------------------

    def close(self) -> None:
        """Flush, capture pre-close ``fstat`` identity, close stream, and record provenance."""
        if self._closed:
            return
        self._closed = True
        close_identity: Optional[FileIdentity] = None
        try:
            if self._level in ("stat", "realpath", "hash") and self._max_tracked_files > 0:
                if self._role != "input":
                    try:
                        self._file_obj.flush()
                    except Exception:
                        pass
                try:
                    fileno = self._file_obj.fileno()
                    if isinstance(fileno, int):
                        close_identity = FileIdentity.from_fd(fileno)
                except Exception:
                    close_identity = None
        finally:
            try:
                self._file_obj.close()
            finally:
                if self._level != "none":
                    self._register_provenance(close_identity)

    def _populate_stat_fields(
        self, record: Dict[str, Any], identity: Optional[FileIdentity]
    ) -> None:
        if identity is None:
            return
        record["size_bytes"] = identity.size_bytes
        record["mtime"] = identity.mtime
        record["ctime"] = identity.ctime
        record["mtime_ns"] = identity.mtime_ns
        record["inode"] = identity.inode
        record["device"] = identity.device
        record["entry_type"] = identity.entry_type()

    def _register_provenance(self, close_identity: Optional[FileIdentity]) -> None:
        try:
            if _resolve_max_tracked_files(self._run) == 0:
                lock = getattr(self._run, "_data_files_lock", _fallback_data_files_lock)
                with lock:
                    data_files = _ensure_data_files_buckets(self._run)
                    _increment_records_truncated(data_files)
                return

            level = self._level
            now = time.time()
            record: Dict[str, Any] = {
                "path": self._raw_path,
                "role": self._role,
                "mode": self._mode,
                "open_disposition": self._open_disposition,
                "registration_source": "pubrun.open",
                "registration_count": 1,
                "registered_before_creation": False,
                "change_detected": False,
                "registered_at_utc": now,
                "last_observed_at_utc": now,
                "access_observations": {
                    "bytes_read": self._bytes_read,
                    "bytes_written": self._bytes_written,
                    "read_calls": self._read_calls,
                    "write_calls": self._write_calls,
                    "seek_used": self._seek_used,
                    "truncate_used": self._truncate_used,
                    "eof_reached": self._eof_reached,
                    "raw_or_buffer_accessed": self._raw_or_buffer_accessed,
                },
            }

            if self._role == "input":
                record["accessed_at_utc"] = now
            elif self._role == "output":
                record["modified_at_utc"] = now
            else:
                record["accessed_at_utc"] = now
                record["modified_at_utc"] = now

            if level == "name":
                record["sha256"] = None
                record["digest"] = None
                record["hash_status"] = "disabled"
                record["hash_status_detail"] = "level is 'name'"
                record["hash_algorithm"] = None
                record["observation_time"] = "at_close"
                record["evidence_source"] = "observed"
                record["evidence_strength"] = "path_only"
            else:
                record["path"] = os.path.abspath(self._raw_path)
                observed_id = close_identity or self._open_identity
                if observed_id is None:
                    observed_id = FileIdentity.from_path(self._raw_path)
                self._populate_stat_fields(record, observed_id)

                if level in ("realpath", "hash"):
                    try:
                        record["realpath"] = os.path.realpath(self._raw_path)
                    except OSError:
                        record["realpath"] = None
                    try:
                        lst = os.lstat(self._raw_path)
                        is_link = stat.S_ISLNK(lst.st_mode)
                        record["is_symlink"] = is_link
                        if is_link:
                            try:
                                record["symlink_target"] = _readlink_normalized(self._raw_path)
                            except OSError:
                                record["symlink_target"] = None
                    except OSError:
                        pass

                if level != "hash":
                    if (
                        self._role == "input"
                        and self._open_identity is not None
                        and close_identity is not None
                        and not self._open_identity.matches(close_identity)
                    ):
                        record["change_detected"] = True
                        record["change_details"] = self._open_identity.diff_details(
                            close_identity
                        )
                    record["sha256"] = None
                    record["digest"] = None
                    record["hash_status"] = "disabled"
                    record["hash_status_detail"] = f"level is '{level}'"
                    record["hash_algorithm"] = None
                    record["observation_time"] = "at_close"
                    record["evidence_source"] = "observed"
                    record["evidence_strength"] = (
                        "metadata_only" if observed_id is not None else "path_only"
                    )
                else:
                    self._populate_hash_fields(record, close_identity)

            stored = append_or_deduplicate_record(self._run, record)
            if stored is None:
                return

            if self._role == "input":
                event = "input_dataset"
            elif self._role == "output":
                event = "output_artifact"
            else:
                event = "mixed_dataset"

            if getattr(self._run, "event_stream", None):
                try:
                    self._run.event_stream.emit(
                        event,
                        name=str(self._path.name),
                        payload={
                            "path": record["path"],
                            "role": record["role"],
                            "sha256": record.get("sha256"),
                            "hash_status": record.get("hash_status"),
                            "evidence_strength": record.get("evidence_strength"),
                        },
                    )
                except Exception:
                    pass
        except Exception as exc:
            logger.warning(
                "pubrun: failed to register provenance for '%s': %s",
                self._raw_path,
                exc,
            )

    def _populate_hash_fields(
        self, record: Dict[str, Any], close_identity: Optional[FileIdentity]
    ) -> None:
        budget = self._budget or get_or_create_budget_tracker(self._run)
        alg = budget.hash_algorithm
        record["hash_algorithm"] = alg

        # 1. Pure read whose open-fd identity changed between open and close.
        if (
            self._role == "input"
            and self._open_identity is not None
            and close_identity is not None
            and not self._open_identity.matches(close_identity)
        ):
            budget.record_outcome("file_changed")
            record["hash_status"] = "file_changed"
            record["hash_status_detail"] = (
                "file identity or metadata changed between open and close"
            )
            record["change_detected"] = True
            record["change_details"] = self._open_identity.diff_details(close_identity)
            record["sha256"] = None
            record["digest"] = None
            record["observation_time"] = "at_close"
            record["evidence_source"] = "observed"
            record["evidence_strength"] = "changed_unverified"
            record["hash_stats"] = {
                "bytes_hashed": 0,
                "extra_read_bytes": 0,
                "hash_duration_seconds": 0.0,
            }
            return

        # 2. Evaluate sequential binary streaming digest.
        stream_ready = False
        if self._stream_valid and self._stream_hasher is not None and close_identity is not None:
            if (
                self._role == "input"
                and (self._eof_reached or self._bytes_read == close_identity.size_bytes)
                and self._bytes_read == close_identity.size_bytes
            ):
                stream_ready = True
            elif (
                self._open_disposition in ("write", "exclusive_create")
                and self._bytes_written == close_identity.size_bytes
            ):
                stream_ready = True

        if stream_ready and self._stream_hasher is not None:
            over_reason = (
                budget.check_stream_progress(self._stream_bytes, self._stream_elapsed)
                if budget._has_caps
                else None
            )
            if over_reason is None:
                digest_hex = self._stream_hasher.hexdigest()
                budget.commit_stream_hash(self._stream_bytes, self._stream_elapsed)
                budget.record_outcome("completed")
                record["hash_status"] = "completed"
                record["hash_status_detail"] = None
                record["digest"] = {"algorithm": alg, "value": digest_hex}
                record["sha256"] = digest_hex if alg == "sha256" else None
                record["observation_time"] = "during_stream"
                record["evidence_source"] = "observed"
                record["evidence_strength"] = "verified_content"
                record["hash_stats"] = {
                    "bytes_hashed": self._stream_bytes,
                    "extra_read_bytes": 0,
                    "hash_duration_seconds": round(self._stream_elapsed, 6),
                }
                return
            self._stream_over_budget = True
            self._stream_over_budget_reason = over_reason

        # 3. Short-circuit over-budget streams with zero fallback content reads
        #    unless seek/truncate could have shrunk the file back within budget.
        if self._stream_over_budget and not self._seek_used and not self._truncate_used:
            budget.record_outcome("over_budget")
            record["hash_status"] = "over_budget"
            record["hash_status_detail"] = (
                self._stream_over_budget_reason or "hashing budget exceeded"
            )
            record["digest"] = None
            record["sha256"] = None
            record["observation_time"] = "at_close"
            record["evidence_source"] = "observed"
            record["evidence_strength"] = "metadata_only"
            record["hash_stats"] = {
                "bytes_hashed": 0,
                "extra_read_bytes": 0,
                "hash_duration_seconds": 0.0,
            }
            return

        # 4. Fallback to checked post-close whole-file hash.
        expected_identity = (
            self._open_identity if self._role == "input" else close_identity
        )
        res = hash_file_checked(
            self._raw_path,
            algorithm=alg,
            budget=budget,
            expected_identity=expected_identity,
        )
        record["hash_status"] = res["hash_status"]
        record["hash_status_detail"] = res["hash_status_detail"]
        record["hash_algorithm"] = res["hash_algorithm"]
        record["digest"] = res["digest"]
        record["sha256"] = res["sha256"]
        record["change_detected"] = bool(res["change_detected"])
        if res.get("change_details") is not None:
            record["change_details"] = res["change_details"]
        record["evidence_source"] = res["evidence_source"]
        record["evidence_strength"] = res["evidence_strength"]
        record["observation_time"] = "at_close"
        if res.get("hash_stats") is not None:
            record["hash_stats"] = res["hash_stats"]
        if res.get("entry_type") is not None:
            record["entry_type"] = res["entry_type"]
        if res.get("identity") is not None and "size_bytes" not in record:
            self._populate_stat_fields(record, res["identity"])

    def __enter__(self) -> "ProvenanceFileProxy":
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.close()

    def __iter__(self) -> "ProvenanceFileProxy":
        return self

    def __next__(self) -> Any:
        line = self.readline()
        if not line:
            raise StopIteration
        return line

    def __getattr__(self, name: str) -> Any:
        if name in ("raw", "buffer"):
            self._raw_or_buffer_accessed = True
            self._invalidate_stream()
        return getattr(self._file_obj, name)
