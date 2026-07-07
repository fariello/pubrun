"""Filesystem-type detection for run-relevant paths.

Classifies the filesystem backing given paths (e.g. the run output dir, ``$TMPDIR``)
so a later ``pubrun inspect`` can flag when a run lived on a slow network filesystem
(NFS/Lustre/GPFS/CIFS) — a common cause of inflated I/O on HPC clusters.

CRITICAL DESIGN CONSTRAINT: this must NEVER block on a hung/stale network mount — the
very failure it is meant to detect. ``os.statvfs()``, ``df``, and ``stat`` all block
indefinitely on a wedged NFS/Lustre mount. Because this runs in the ``pubrun-hw`` startup
thread whose result the finalizer waits on with only a ~2s budget, a blocking probe would
either miss that window or wedge a subprocess. Therefore classification is done by
PARSING ``/proc/mounts`` / ``/proc/self/mountinfo`` on Linux (pure file reads that never
touch the target mount) and by reading the pre-fetched ``mount`` table (with a hard
subprocess timeout) on macOS. We never call ``statvfs``/``df``/``stat`` on the target path.
"""
import os
import sys
import time
import logging
import threading
from typing import Dict, Any, List, Optional, Tuple

logger = logging.getLogger("pubrun")

# Filesystem types considered "network" (remote / cluster) filesystems.
_NETWORK_FSTYPES = {
    "nfs", "nfs3", "nfs4", "cifs", "smb", "smbfs", "smb2", "smb3",
    "lustre", "gpfs", "beegfs", "ceph", "cephfs", "glusterfs", "fuse.glusterfs",
    "afs", "9p", "gfs", "gfs2", "ocfs2", "pvfs2", "orangefs",
    "fuse.sshfs", "sshfs", "davfs", "webdav",
}


def _is_network_fstype(fstype: str) -> bool:
    ft = (fstype or "").lower()
    if ft in _NETWORK_FSTYPES:
        return True
    # Match fuse-backed network filesystems generically (e.g. "fuse.<netfs>").
    return ft.startswith("fuse.") and any(n in ft for n in ("nfs", "smb", "sshfs", "gluster", "ceph"))


def _parse_proc_mounts() -> List[Tuple[str, str]]:
    """Return [(mount_point, fstype), ...] from /proc/mounts (Linux).

    Pure file read; never touches the mounted filesystems themselves.
    """
    entries: List[Tuple[str, str]] = []
    # /proc/mounts format: "device mountpoint fstype options dump pass"
    with open("/proc/mounts", "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            parts = line.split()
            if len(parts) >= 3:
                mount_point = _unescape_mount_field(parts[1])
                fstype = parts[2]
                entries.append((mount_point, fstype))
    return entries


def _parse_proc_mountinfo() -> List[Tuple[str, str]]:
    """Return [(mount_point, fstype), ...] from /proc/self/mountinfo (Linux).

    More accurate than /proc/mounts: it carries the super-block fstype and disambiguates
    bind/overlay mounts. Pure file read; never touches the mounted filesystems themselves.

    Format (man 5 proc):
        36 35 98:0 /mnt1 /mnt2 rw,noatime master:1 - ext3 /dev/root rw,errors=continue
        (0)(1)(2)  (3)   (4)   (5)         (6...)   (S) (fstype) (source) (superopts)
    Field 4 is the mount point; a variable number of optional fields (6..) end at a single
    "-" separator; the field AFTER "-" is the filesystem type.
    """
    entries: List[Tuple[str, str]] = []
    with open("/proc/self/mountinfo", "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            parts = line.split()
            if len(parts) < 5:
                continue
            try:
                sep = parts.index("-")
            except ValueError:
                continue
            if sep + 1 >= len(parts):
                continue
            mount_point = _unescape_mount_field(parts[4])
            fstype = parts[sep + 1]
            entries.append((mount_point, fstype))
    return entries


def _unescape_mount_field(field: str) -> str:
    """Decode octal escapes (\\040 space, \\011 tab, etc.) used in /proc/mounts."""
    if "\\" not in field:
        return field
    out = []
    i = 0
    while i < len(field):
        if field[i] == "\\" and i + 3 < len(field) + 1 and field[i + 1:i + 4].isdigit():
            try:
                out.append(chr(int(field[i + 1:i + 4], 8)))
                i += 4
                continue
            except ValueError:
                pass
        out.append(field[i])
        i += 1
    return "".join(out)


def _longest_prefix_fstype(resolved_path: str, entries: List[Tuple[str, str]]) -> Optional[Tuple[str, str]]:
    """Return (mount_point, fstype) of the longest mount point that prefixes the path."""
    best: Optional[Tuple[str, str]] = None
    best_len = -1
    for mount_point, fstype in entries:
        mp = mount_point.rstrip("/") or "/"
        # A mount matches if the path equals it or sits under it.
        if resolved_path == mp or resolved_path.startswith(mp + "/") or mp == "/":
            if len(mp) > best_len:
                best_len = len(mp)
                best = (mount_point, fstype)
    return best


def _classify_path_linux(path: str, entries: List[Tuple[str, str]]) -> Dict[str, Any]:
    # os.path.realpath resolves symlinks lexically on the string where possible, but
    # can stat components; to stay non-blocking we use os.path.abspath (pure string) and
    # normpath. This is sufficient for mount-prefix matching and never touches the mount.
    resolved = os.path.normpath(os.path.abspath(path))
    match = _longest_prefix_fstype(resolved, entries)
    if match is None:
        return {"path": path, "capture_state": {"status": "failed", "detail": "no matching mount"}}
    mount_point, fstype = match
    return {
        "path": path,
        "mount_point": mount_point,
        "fstype": fstype,
        "is_network": _is_network_fstype(fstype),
    }


def _mac_mount_table(timeout: float = 2.0) -> List[Tuple[str, str]]:
    """Parse `mount` output on macOS: '<dev> on <mount_point> (<fstype>, ...)'.

    Uses a hard subprocess timeout so a wedged network mount cannot hang us.
    """
    from pubrun.capture.subprocesses import disable_spy
    import subprocess
    entries: List[Tuple[str, str]] = []
    with disable_spy():
        out = subprocess.check_output(["mount"], text=True, stderr=subprocess.DEVNULL, timeout=timeout)
    for line in out.splitlines():
        # e.g. "/dev/disk1s1 on / (apfs, local, journaled)"
        if " on " not in line or "(" not in line:
            continue
        try:
            after_on = line.split(" on ", 1)[1]
            mount_point = after_on.rsplit(" (", 1)[0].strip()
            fstype = after_on.rsplit("(", 1)[1].split(",", 1)[0].strip().rstrip(")")
            entries.append((mount_point, fstype))
        except (IndexError, ValueError):
            continue
    return entries


def _classify_windows_path(path: str) -> Dict[str, Any]:
    """Classify one path on Windows via fast, local ctypes calls (never traverse a share).

    GetVolumePathNameW maps the path to its volume root; GetVolumeInformationW gives the
    filesystem name (NTFS/ReFS/FAT32/exFAT); GetDriveTypeW == DRIVE_REMOTE flags a network
    drive. All are local metadata calls, so they respect the non-blocking constraint.
    """
    import ctypes
    from ctypes import wintypes
    DRIVE_REMOTE = 4
    k32 = ctypes.windll.kernel32  # type: ignore[attr-defined]
    buf = ctypes.create_unicode_buffer(260)
    if not k32.GetVolumePathNameW(ctypes.c_wchar_p(path), buf, 260):
        return {"path": path, "capture_state": {"status": "failed", "detail": "GetVolumePathNameW failed"}}
    volume_root = buf.value
    fs_name = ctypes.create_unicode_buffer(260)
    vol_name = ctypes.create_unicode_buffer(260)
    ok = k32.GetVolumeInformationW(
        ctypes.c_wchar_p(volume_root), vol_name, 260,
        None, None, None, fs_name, 260)
    fstype = fs_name.value if ok else "unknown"
    drive_type = k32.GetDriveTypeW(ctypes.c_wchar_p(volume_root))
    is_network = (drive_type == DRIVE_REMOTE)
    return {
        "path": path,
        "mount_point": volume_root,
        "fstype": fstype,
        "is_network": bool(is_network),
    }


def _classify_windows(paths: Dict[str, str]) -> Dict[str, Any]:
    res: Dict[str, Any] = {}
    for label, path in paths.items():
        if not path:
            continue
        try:
            res[label] = _classify_windows_path(path)
        except Exception as e:  # per-path failure must not abort the rest
            res[label] = {"path": path, "capture_state": {"status": "failed", "detail": str(e)}}
    res["capture_state"] = {"status": "complete"}
    return res


def get_filesystem(config: Dict[str, Any], paths: Dict[str, str]) -> Dict[str, Any]:
    """Classify the filesystem backing each named path.

    Args:
        config: Resolved pubrun configuration.
        paths: mapping of label -> path (e.g. {"output_dir": "/scratch/runs", "tmpdir": "/tmp"}).

    Returns:
        A dict of {label: {path, mount_point, fstype, is_network}} plus a top-level
        ``capture_state``. Never raises; failures are recorded per-path and/or top-level.
    """
    res: Dict[str, Any] = {}
    try:
        sys_plat = sys.platform
        entries: List[Tuple[str, str]] = []
        if sys_plat.startswith("linux"):
            # Prefer /proc/self/mountinfo (super-block fstype, bind/overlay-aware); fall
            # back to /proc/mounts. Both are pure file reads (never touch the mount).
            if os.path.exists("/proc/self/mountinfo"):
                try:
                    entries = _parse_proc_mountinfo()
                except Exception:
                    entries = []
            if not entries and os.path.exists("/proc/mounts"):
                entries = _parse_proc_mounts()
        elif sys_plat == "darwin":
            entries = _mac_mount_table()
        elif sys_plat == "win32":
            return _classify_windows(paths)
        else:
            return {"capture_state": {"status": "failed",
                                      "detail": f"filesystem classification not supported on {sys_plat}"}}

        for label, path in paths.items():
            if not path:
                continue
            try:
                res[label] = _classify_path_linux(path, entries)
            except Exception as e:  # per-path failure must not abort the rest
                res[label] = {"path": path, "capture_state": {"status": "failed", "detail": str(e)}}

        res["capture_state"] = {"status": "complete"}
        return res
    except Exception as e:
        logger.debug(f"pubrun failed classifying filesystems: {e}")
        return {"capture_state": {"status": "failed", "detail": str(e)}}


# ---------------------------------------------------------------------------------------
# Live capacity/health probe (statvfs) — DIAGNOSTIC/BENCH ONLY.
#
# This DOES the blocking syscall the classification above carefully avoids. It is NEVER
# invoked by `import pubrun` / auto-start / the ~2s startup thread. It exists so
# `pubrun bench` / `pubrun self-check` can report free space, inode counts, read-only
# mounts, and — most valuably — that a mount is wedged (hung) or merely slow.
#
# Design (decoupled wait budget vs. probe lifetime):
#   * The syscall runs in a DAEMON thread that writes its result into a shared slot.
#   * The CALLER waits only a short responsiveness budget, then continues.
#   * The daemon keeps running; a caller can re-read the slot later (e.g. at result
#     assembly) via `LiveProbe.result()` — a NON-blocking read. So a slow-but-alive mount
#     that returns after the budget is captured (`slow: true` + measured elapsed_s) instead
#     of falsely called hung. Only a probe that never returns is `pending`/`hung`.
#   * A thread cannot be killed in Python; a daemon thread dies with the process and never
#     delays interpreter shutdown, so abandoning a wedged probe is safe.
# ---------------------------------------------------------------------------------------

# Cap on concurrent live-probe threads so a machine with many wedged mounts cannot spawn an
# unbounded number of abandoned daemons.
_MAX_LIVE_PROBES = 8
_live_probe_sem = threading.BoundedSemaphore(_MAX_LIVE_PROBES)


def _statvfs_metrics(path: str) -> Dict[str, Any]:
    """The BLOCKING probe body. POSIX statvfs / Windows GetDiskFreeSpaceExW."""
    if sys.platform == "win32":
        import ctypes
        free = ctypes.c_ulonglong(0)
        total = ctypes.c_ulonglong(0)
        avail = ctypes.c_ulonglong(0)
        ok = ctypes.windll.kernel32.GetDiskFreeSpaceExW(  # type: ignore[attr-defined]
            ctypes.c_wchar_p(path), ctypes.pointer(avail),
            ctypes.pointer(total), ctypes.pointer(free))
        if not ok:
            raise OSError("GetDiskFreeSpaceExW failed")
        return {"total_bytes": total.value, "free_bytes": free.value,
                "avail_bytes": avail.value}
    st = os.statvfs(path)
    return {
        "total_bytes": st.f_blocks * st.f_frsize,
        "free_bytes": st.f_bfree * st.f_frsize,
        "avail_bytes": st.f_bavail * st.f_frsize,
        "total_inodes": st.f_files,
        "free_inodes": st.f_ffree,
        "read_only": bool(st.f_flag & getattr(os, "ST_RDONLY", 1)),
    }


class LiveProbe:
    """Handle to a running (daemon) statvfs probe. Already waited up to the budget on init."""

    def __init__(self, path: str, wait_budget_s: float):
        self.path = path
        self._budget = wait_budget_s
        self._done = threading.Event()
        self._slot: Dict[str, Any] = {}
        self._t0 = time.monotonic()
        self._acquired = _live_probe_sem.acquire(blocking=False)
        if not self._acquired:
            # Too many probes in flight; skip rather than pile up daemons.
            self._slot = {"status": "skipped", "detail": "probe cap reached"}
            self._done.set()
            return
        self._thread = threading.Thread(target=self._run, name="pubrun-fsprobe", daemon=True)
        self._thread.start()
        # Wait only the responsiveness budget; the daemon keeps running past it.
        self._done.wait(timeout=wait_budget_s)

    def _run(self) -> None:
        try:
            metrics = _statvfs_metrics(self.path)
            elapsed = time.monotonic() - self._t0
            self._slot = {"status": "complete", "elapsed_s": round(elapsed, 3), **metrics}
        except Exception as e:
            self._slot = {"status": "error", "detail": str(e),
                          "elapsed_s": round(time.monotonic() - self._t0, 3)}
        finally:
            self._done.set()
            try:
                if self._acquired:
                    _live_probe_sem.release()
            except (ValueError, RuntimeError):
                pass

    def result(self) -> Dict[str, Any]:
        """NON-blocking read of the current state. Call once initially and, optionally,
        again later (e.g. at benchmark result assembly) to pick up a slow-but-alive return."""
        if self._done.is_set():
            out = dict(self._slot)
            # Returned after the caller's budget but before this read -> "slow".
            if out.get("status") == "complete" and out.get("elapsed_s", 0) > self._budget:
                out["slow"] = True
            return out
        # Still running: not hung yet, just not-yet-returned within our wait so far.
        return {"status": "pending", "hung": True,
                "waited_s": round(time.monotonic() - self._t0, 3)}


def probe_filesystem_live(path: str, wait_budget_s: float = 5.0) -> LiveProbe:
    """Start a live capacity/health probe (daemon thread) and wait up to ``wait_budget_s``.

    DIAGNOSTIC/BENCH ONLY — never call from the auto-start capture path. Returns a
    ``LiveProbe``; call ``.result()`` for a non-blocking snapshot (and again later to catch a
    slow-but-alive return). Never raises.
    """
    return LiveProbe(path, wait_budget_s)


def probe_paths_live(fs_data: Dict[str, Any], wait_budget_s: float = 5.0) -> Dict[str, Any]:
    """Enrich a classified fs_data dict (from ``get_filesystem``) with live probe results,
    DEDUPED by mount point so N paths on one wedged mount spawn ONE daemon, not N.

    Mutates and returns ``fs_data``: each path entry gains a ``live`` sub-dict. DIAGNOSTIC/
    BENCH ONLY. Never raises.
    """
    try:
        probes: Dict[str, LiveProbe] = {}
        # Start one probe per unique mount point (dedupe).
        for label, entry in fs_data.items():
            if label == "capture_state" or not isinstance(entry, dict):
                continue
            mp = entry.get("mount_point") or entry.get("path")
            if not mp:
                continue
            if mp not in probes:
                probes[mp] = probe_filesystem_live(entry.get("path", mp), wait_budget_s)
        # Attach results back to each path entry.
        for label, entry in fs_data.items():
            if label == "capture_state" or not isinstance(entry, dict):
                continue
            mp = entry.get("mount_point") or entry.get("path")
            if mp and mp in probes:
                entry["live"] = probes[mp].result()
    except Exception as e:
        logger.debug(f"pubrun live fs probe failed: {e}")
    return fs_data
