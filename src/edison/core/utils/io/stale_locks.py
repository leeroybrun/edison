"""Stale lock discovery and cleanup utilities.

Locking in Edison uses sidecar ``*.lock`` files (see ``acquire_file_lock``).
If a process crashes, these lock files may be left behind and block workflows.

This module provides a single, PID-aware implementation for:
- detecting stale locks by mtime
- preserving locks for live PIDs when pid metadata is present
- deleting stale locks (optionally dry-run)
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional


@dataclass(frozen=True)
class StaleLock:
    path: Path
    age_seconds: int
    pid: Optional[int]
    pid_alive: Optional[bool]


def _parse_pid(text: str) -> Optional[int]:
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith("pid="):
            value = line[len("pid=") :].strip()
        elif line.startswith("pid:"):
            value = line[len("pid:") :].strip()
        else:
            continue
        try:
            return int(value)
        except ValueError:
            return None

    # Support JSON lock metadata (Edison QA/evidence locks write JSON blobs).
    #
    # We deliberately only parse a top-level `pid` field to keep this safe and
    # deterministic (no schema coupling, no deep traversal).
    try:
        import json

        raw = text.strip()
        if not raw:
            return None
        obj = json.loads(raw)
        if isinstance(obj, dict) and "pid" in obj:
            return int(obj["pid"])
    except Exception:
        return None
    return None


def _is_pid_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
        return True
    except PermissionError:
        # Process exists but we don't have permission to signal it.
        return True
    except OSError:
        return False


def inspect_lock(lock_path: Path) -> tuple[Optional[int], Optional[bool]]:
    """Return (pid, pid_alive) when lock contains a pid line, else (None, None)."""
    try:
        text = lock_path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return None, None
    pid = _parse_pid(text)
    if pid is None:
        return None, None
    return pid, _is_pid_alive(pid)


def find_stale_locks(
    lock_files: Iterable[Path],
    *,
    max_age_seconds: int,
    now: Optional[float] = None,
) -> list[StaleLock]:
    """Return lock files older than max_age_seconds and not owned by a live PID."""
    now_ts = time.time() if now is None else float(now)
    stale: list[StaleLock] = []

    for lock_file in lock_files:
        try:
            st = lock_file.stat()
        except OSError:
            continue
        age = int(max(0, now_ts - st.st_mtime))
        if age <= int(max_age_seconds):
            continue

        pid, pid_alive = inspect_lock(lock_file)
        if pid is not None and pid_alive is True:
            # Preserve locks for active processes even if the file looks old.
            continue

        stale.append(
            StaleLock(
                path=lock_file,
                age_seconds=age,
                pid=pid,
                pid_alive=pid_alive,
            )
        )

    return sorted(stale, key=lambda s: str(s.path))


def cleanup_stale_locks(
    lock_files: Iterable[Path],
    *,
    max_age_seconds: int,
    dry_run: bool,
) -> tuple[list[StaleLock], list[Path]]:
    """Find and optionally remove stale locks.

    Returns:
        (stale, removed_paths)
    """
    stale = find_stale_locks(lock_files, max_age_seconds=max_age_seconds)
    if dry_run:
        return stale, []

    removed: list[Path] = []
    for item in stale:
        try:
            item.path.unlink()
            removed.append(item.path)
        except OSError:
            continue

    return stale, removed


__all__ = ["StaleLock", "cleanup_stale_locks", "find_stale_locks", "inspect_lock"]
