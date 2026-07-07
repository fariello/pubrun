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
import logging
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
        if sys_plat.startswith("linux") and os.path.exists("/proc/mounts"):
            entries = _parse_proc_mounts()
        elif sys_plat == "darwin":
            entries = _mac_mount_table()
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
